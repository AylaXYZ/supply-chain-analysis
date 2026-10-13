"""供应链订单、库存与供应商绩效分析入口。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis import (
    abc_classification,
    analyze_inventory,
    build_action_list,
    calculate_kpis,
    enrich_orders,
    supplier_performance,
)
from src.data_processing import load_data
from src.visualization import generate_all_charts


def run_analysis(data_dir: str | Path, output_dir: str | Path) -> dict:
    orders, inventory = load_data(data_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    order_detail = enrich_orders(orders)
    inventory_detail = analyze_inventory(inventory)
    abc = abc_classification(orders)
    suppliers = supplier_performance(orders)
    actions = build_action_list(inventory_detail, abc)
    kpis = calculate_kpis(orders, inventory)

    order_detail.to_csv(output / "order_detail.csv", index=False, encoding="utf-8-sig")
    inventory_detail.to_csv(output / "inventory_health.csv", index=False, encoding="utf-8-sig")
    abc.to_csv(output / "abc_analysis.csv", index=False, encoding="utf-8-sig")
    suppliers.to_csv(output / "supplier_performance.csv", index=False, encoding="utf-8-sig")
    actions.to_csv(output / "action_list.csv", index=False, encoding="utf-8-sig")
    (output / "summary.json").write_text(
        json.dumps(kpis, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    charts = generate_all_charts(inventory_detail, suppliers, abc, output)

    return {"kpis": kpis, "charts": [str(path) for path in charts]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="供应链运营数据分析")
    parser.add_argument("--data-dir", default="data", help="输入 CSV 文件目录")
    parser.add_argument("--output-dir", default="outputs", help="结果输出目录")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_analysis(args.data_dir, args.output_dir)
    print("\n供应链核心指标")
    print("=" * 48)
    for name, value in result["kpis"].items():
        if "率" in name:
            print(f"{name:<18}: {value:.2%}")
        else:
            print(f"{name:<18}: {value}")
    print("\n分析结果已写入:", Path(args.output_dir).resolve())


if __name__ == "__main__":
    main()
