"""将分析结果输出为可直接嵌入报告的图表。"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MPL_CACHE_DIR = PROJECT_ROOT / ".matplotlib-cache"
MPL_CACHE_DIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))

import matplotlib.pyplot as plt
import pandas as pd


COLORS = {"高": "#dc2626", "中": "#f59e0b", "低": "#16a34a"}


def _prepare_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def plot_inventory_risk(inventory: pd.DataFrame, output_dir: str | Path) -> Path:
    output = _prepare_output_dir(output_dir) / "inventory_risk.png"
    frame = inventory.sort_values("days_of_supply")
    colors = frame["risk_level"].map(COLORS).fillna("#64748b")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(frame["product_name"], frame["days_of_supply"], color=colors)
    ax.set_title("Inventory Coverage and Risk")
    ax.set_xlabel("Days of Supply")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_supplier_score(suppliers: pd.DataFrame, output_dir: str | Path) -> Path:
    output = _prepare_output_dir(output_dir) / "supplier_performance.png"
    frame = suppliers.sort_values("performance_score")

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.barh(frame["supplier_id"], frame["performance_score"], color="#2563eb")
    ax.axvline(85, color="#16a34a", linestyle="--", linewidth=1, label="Excellent threshold")
    ax.axvline(70, color="#f59e0b", linestyle="--", linewidth=1, label="Qualified threshold")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Performance Score")
    ax.set_title("Supplier Delivery and Quality Score")
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_abc_distribution(abc: pd.DataFrame, output_dir: str | Path) -> Path:
    output = _prepare_output_dir(output_dir) / "abc_analysis.png"
    frame = abc.sort_values("annual_usage_value", ascending=False)

    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax1.bar(frame["product_id"], frame["annual_usage_value"], color="#0f766e")
    ax1.set_ylabel("Purchase Value")
    ax1.set_xlabel("Product")
    ax1.set_title("ABC Analysis by Purchase Value")

    ax2 = ax1.twinx()
    ax2.plot(frame["product_id"], frame["cumulative_share"] * 100, color="#db2777", marker="o")
    ax2.set_ylabel("Cumulative Share (%)")
    ax2.set_ylim(0, 110)
    ax2.axhline(80, color="#94a3b8", linestyle="--", linewidth=1)
    ax2.axhline(95, color="#94a3b8", linestyle="--", linewidth=1)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output


def generate_all_charts(
    inventory: pd.DataFrame,
    suppliers: pd.DataFrame,
    abc: pd.DataFrame,
    output_dir: str | Path,
) -> list[Path]:
    return [
        plot_inventory_risk(inventory, output_dir),
        plot_supplier_score(suppliers, output_dir),
        plot_abc_distribution(abc, output_dir),
    ]
