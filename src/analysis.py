"""供应链核心指标、风险识别与行动建议。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def enrich_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """生成交付周期、延迟天数、质量率和订单金额等派生字段。"""
    frame = orders.copy()
    frame["lead_time_days"] = (
        frame["actual_delivery_date"] - frame["order_date"]
    ).dt.days
    frame["delay_days"] = (
        frame["actual_delivery_date"] - frame["promised_date"]
    ).dt.days.clip(lower=0)
    frame["on_time_flag"] = frame["actual_delivery_date"] <= frame["promised_date"]
    frame["order_value"] = frame["quantity"] * frame["unit_cost"]
    frame["defect_rate"] = np.where(
        frame["quantity"] > 0,
        frame["rejected_quantity"] / frame["quantity"],
        0.0,
    )
    return frame


def calculate_kpis(orders: pd.DataFrame, inventory: pd.DataFrame) -> dict[str, float | int]:
    """计算管理层可读的交付、质量、库存与资金占用指标。"""
    enriched = enrich_orders(orders)
    inv = analyze_inventory(inventory)
    total_quantity = float(enriched["quantity"].sum())
    rejected = float(enriched["rejected_quantity"].sum())

    return {
        "订单数量": int(enriched["order_id"].nunique()),
        "订单金额": round(float(enriched["order_value"].sum()), 2),
        "按时交付率": round(float(enriched["on_time_flag"].mean()), 4),
        "平均交付周期_天": round(float(enriched["lead_time_days"].mean()), 2),
        "平均延迟天数": round(float(enriched["delay_days"].mean()), 2),
        "来料不良率": round(rejected / total_quantity if total_quantity else 0.0, 4),
        "库存金额": round(float((inventory["stock_level"] * inventory["unit_cost"]).sum()), 2),
        "高风险SKU数量": int((inv["risk_level"] == "高").sum()),
        "建议补货金额": round(float((inv["recommended_order_qty"] * inv["unit_cost"]).sum()), 2),
    }


def analyze_inventory(inventory: pd.DataFrame) -> pd.DataFrame:
    """计算可用库存、库存覆盖天数、建议补货量和风险等级。"""
    frame = inventory.copy()
    frame["available_stock"] = (
        frame["stock_level"] - frame["allocated_stock"] + frame["in_transit"]
    )
    frame["days_of_supply"] = np.where(
        frame["average_daily_demand"] > 0,
        frame["available_stock"] / frame["average_daily_demand"],
        np.inf,
    )
    frame["target_stock"] = (
        frame["average_daily_demand"] * frame["lead_time_days"]
        + frame["safety_stock"]
    )
    frame["recommended_order_qty"] = (
        frame["target_stock"] - frame["available_stock"]
    ).clip(lower=0).round().astype(int)
    frame["inventory_value"] = frame["stock_level"] * frame["unit_cost"]

    high = (frame["available_stock"] <= frame["safety_stock"]) | (
        frame["days_of_supply"] < frame["lead_time_days"]
    )
    medium = (~high) & (
        (frame["available_stock"] <= frame["reorder_point"])
        | (frame["days_of_supply"] < frame["lead_time_days"] * 1.5)
    )
    frame["risk_level"] = np.select([high, medium], ["高", "中"], default="低")
    frame["risk_reason"] = np.select(
        [
            frame["available_stock"] <= frame["safety_stock"],
            frame["days_of_supply"] < frame["lead_time_days"],
            frame["available_stock"] <= frame["reorder_point"],
            frame["days_of_supply"] < frame["lead_time_days"] * 1.5,
        ],
        [
            "可用库存低于安全库存",
            "库存覆盖天数不足以覆盖采购提前期",
            "达到补货点",
            "库存缓冲不足",
        ],
        default="库存健康",
    )
    return frame


def abc_classification(orders: pd.DataFrame) -> pd.DataFrame:
    """按累计采购金额完成 ABC 分类。"""
    enriched = enrich_orders(orders)
    result = (
        enriched.groupby("product_id", as_index=False)
        .agg(annual_usage_value=("order_value", "sum"), ordered_quantity=("quantity", "sum"))
        .sort_values("annual_usage_value", ascending=False)
    )
    total = result["annual_usage_value"].sum()
    result["value_share"] = result["annual_usage_value"] / total if total else 0.0
    result["cumulative_share"] = result["value_share"].cumsum()
    result["abc_class"] = np.select(
        [result["cumulative_share"] <= 0.80, result["cumulative_share"] <= 0.95],
        ["A", "B"],
        default="C",
    )
    if not result.empty:
        result.iloc[0, result.columns.get_loc("abc_class")] = "A"
    return result.reset_index(drop=True)


def supplier_performance(orders: pd.DataFrame) -> pd.DataFrame:
    """从订单表现计算供应商交付与质量得分。"""
    enriched = enrich_orders(orders)
    result = (
        enriched.groupby("supplier_id", as_index=False)
        .agg(
            order_count=("order_id", "nunique"),
            purchase_value=("order_value", "sum"),
            on_time_delivery_rate=("on_time_flag", "mean"),
            average_delay_days=("delay_days", "mean"),
            ordered_quantity=("quantity", "sum"),
            rejected_quantity=("rejected_quantity", "sum"),
        )
    )
    result["defect_rate"] = np.where(
        result["ordered_quantity"] > 0,
        result["rejected_quantity"] / result["ordered_quantity"],
        0.0,
    )
    result["performance_score"] = (
        result["on_time_delivery_rate"] * 70
        + (1 - result["defect_rate"].clip(0, 1)) * 30
    ).round(1)
    result["performance_level"] = pd.cut(
        result["performance_score"],
        bins=[-1, 70, 85, 100],
        labels=["待改善", "合格", "优秀"],
    )
    return result.sort_values("performance_score", ascending=False).reset_index(drop=True)


def build_action_list(inventory_analysis: pd.DataFrame, abc: pd.DataFrame) -> pd.DataFrame:
    """将库存风险与 ABC 分类合并为按优先级排序的行动清单。"""
    actions = inventory_analysis.merge(
        abc[["product_id", "abc_class"]], on="product_id", how="left"
    )
    actions["abc_class"] = actions["abc_class"].fillna("C")
    actions["priority_score"] = (
        actions["risk_level"].map({"高": 60, "中": 30, "低": 0}).fillna(0)
        + actions["abc_class"].map({"A": 30, "B": 15, "C": 5}).fillna(0)
        + np.where(actions["recommended_order_qty"] > 0, 10, 0)
    )
    actions["recommended_action"] = np.select(
        [
            actions["recommended_order_qty"] > 0,
            actions["days_of_supply"] > actions["lead_time_days"] * 4,
        ],
        ["启动补货并确认供应商交期", "评估调拨、促销或暂停采购"],
        default="保持监控",
    )
    columns = [
        "product_id",
        "product_name",
        "abc_class",
        "risk_level",
        "risk_reason",
        "days_of_supply",
        "recommended_order_qty",
        "priority_score",
        "recommended_action",
    ]
    return actions[columns].sort_values(
        ["priority_score", "recommended_order_qty"], ascending=False
    ).reset_index(drop=True)
