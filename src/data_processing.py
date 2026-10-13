"""数据读取、校验与清洗。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


ORDER_REQUIRED_COLUMNS = {
    "order_id",
    "product_id",
    "supplier_id",
    "order_date",
    "promised_date",
    "actual_delivery_date",
    "quantity",
    "unit_cost",
    "rejected_quantity",
}

INVENTORY_REQUIRED_COLUMNS = {
    "product_id",
    "product_name",
    "category",
    "stock_level",
    "allocated_stock",
    "in_transit",
    "reorder_point",
    "safety_stock",
    "average_daily_demand",
    "lead_time_days",
    "unit_cost",
}


def _read_csv_checked(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"文件为空: {path}")

    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"CSV 无有效内容: {path}") from exc

    if frame.empty:
        raise ValueError(f"CSV 没有数据行: {path}")
    return frame


def _require_columns(frame: pd.DataFrame, required: Iterable[str], name: str) -> None:
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{name} 缺少必要字段: {', '.join(sorted(missing))}")


def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """校验订单数据并完成类型转换、去重和基本业务检查。"""
    _require_columns(orders, ORDER_REQUIRED_COLUMNS, "订单数据")
    frame = orders.copy().drop_duplicates(subset=["order_id"], keep="last")

    date_columns = ["order_date", "promised_date", "actual_delivery_date"]
    for column in date_columns:
        frame[column] = pd.to_datetime(frame[column], errors="coerce")

    numeric_columns = ["quantity", "unit_cost", "rejected_quantity"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    invalid = frame[date_columns + numeric_columns].isna().any(axis=1)
    frame = frame.loc[~invalid].copy()
    frame = frame[(frame["quantity"] > 0) & (frame["unit_cost"] >= 0)]
    frame["rejected_quantity"] = frame["rejected_quantity"].clip(lower=0)
    frame["rejected_quantity"] = frame[["rejected_quantity", "quantity"]].min(axis=1)

    if frame.empty:
        raise ValueError("订单数据清洗后无有效记录")
    return frame.sort_values("order_date").reset_index(drop=True)


def clean_inventory(inventory: pd.DataFrame) -> pd.DataFrame:
    """校验库存快照，并确保数量、成本与需求字段可计算。"""
    _require_columns(inventory, INVENTORY_REQUIRED_COLUMNS, "库存数据")
    frame = inventory.copy().drop_duplicates(subset=["product_id"], keep="last")

    numeric_columns = [
        "stock_level",
        "allocated_stock",
        "in_transit",
        "reorder_point",
        "safety_stock",
        "average_daily_demand",
        "lead_time_days",
        "unit_cost",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=numeric_columns)
    for column in numeric_columns:
        frame[column] = frame[column].clip(lower=0)

    if frame.empty:
        raise ValueError("库存数据清洗后无有效记录")
    return frame.sort_values("product_id").reset_index(drop=True)


def load_data(data_dir: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """从指定目录加载订单与库存数据。"""
    if data_dir is None:
        base_dir = Path(__file__).resolve().parent.parent / "data"
    else:
        base_dir = Path(data_dir)

    orders = _read_csv_checked(base_dir / "orders.csv")
    inventory = _read_csv_checked(base_dir / "inventory.csv")
    return clean_orders(orders), clean_inventory(inventory)
