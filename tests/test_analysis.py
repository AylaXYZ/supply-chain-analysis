import pandas as pd

from src.analysis import (
    abc_classification,
    analyze_inventory,
    enrich_orders,
    supplier_performance,
)


def _orders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": ["O1", "O2"],
            "product_id": ["P1", "P2"],
            "supplier_id": ["S1", "S2"],
            "order_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
            "promised_date": pd.to_datetime(["2024-01-05", "2024-01-05"]),
            "actual_delivery_date": pd.to_datetime(["2024-01-04", "2024-01-08"]),
            "quantity": [100, 50],
            "unit_cost": [10, 5],
            "rejected_quantity": [1, 5],
        }
    )


def test_enrich_orders_calculates_delivery_metrics():
    result = enrich_orders(_orders())
    assert result["on_time_flag"].tolist() == [True, False]
    assert result["delay_days"].tolist() == [0, 3]
    assert result["order_value"].tolist() == [1000, 250]


def test_inventory_analysis_flags_shortage_and_replenishment():
    inventory = pd.DataFrame(
        {
            "stock_level": [30],
            "allocated_stock": [20],
            "in_transit": [0],
            "reorder_point": [50],
            "safety_stock": [20],
            "average_daily_demand": [10],
            "lead_time_days": [5],
            "unit_cost": [8],
        }
    )
    result = analyze_inventory(inventory)
    assert result.loc[0, "risk_level"] == "高"
    assert result.loc[0, "recommended_order_qty"] == 60


def test_abc_classification_keeps_highest_value_in_class_a():
    result = abc_classification(_orders())
    assert result.iloc[0]["product_id"] == "P1"
    assert result.iloc[0]["abc_class"] == "A"


def test_supplier_performance_penalizes_delay_and_defects():
    result = supplier_performance(_orders()).set_index("supplier_id")
    assert result.loc["S1", "performance_score"] > result.loc["S2", "performance_score"]
