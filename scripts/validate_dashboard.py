#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "MB_DAILY_CONTROL_PUBLIC_V2"
    assert payload["layout_version"] == "MB_DAILY_CONTROL_LAYOUT_V4_SETTLED_NO_XIEN2"
    assert payload["status"] == "REAL_ORDER_SETTLED_WIN"
    assert "xien2" not in payload
    assert payload["audit"]["xien2_visible"] is False

    plan = payload["plan"]
    assert plan["target_date"] == "2026-07-24"
    assert plan["data_lock_date"] == "2026-07-23"
    assert plan["codes"] == ["13", "55", "83", "28"]
    assert plan["points_by_code"] == {"13": 50, "55": 50, "83": 25, "28": 25}
    assert plan["total_points"] == 150
    assert plan["total_capital_vnd"] == 3_450_000
    assert plan["outcome_known_at_selection"] is False
    assert plan["rbk_used"] is False

    settlement = payload["actual_order_settlement"]
    assert settlement["date"] == "2026-07-24"
    assert settlement["codes"] == plan["codes"]
    assert settlement["points_by_code"] == plan["points_by_code"]
    assert settlement["hits_by_code"] == {"13": 1, "55": 0, "83": 0, "28": 0}
    assert settlement["total_hits"] == 1
    assert settlement["capital_vnd"] == 3_450_000
    assert settlement["return_vnd"] == 4_000_000
    assert settlement["net_profit_vnd"] == 550_000
    assert settlement["cumulative_net_profit_vnd"] == 15_706_000
    assert settlement["status"] == "ĐÃ QUYẾT TOÁN"
    assert settlement["result_label"] == "CÓ LÃI"

    latest = payload["latest_settlement"]
    assert latest["result_units"] == 27
    assert len(latest["result_sequence"]) == 27
    assert latest["hits_by_code"] == settlement["hits_by_code"]
    assert latest["net_profit_vnd"] == settlement["net_profit_vnd"]

    verification = payload["source_verification"]
    assert verification["date"] == "2026-07-24"
    assert verification["independent_sources"] >= 2
    assert verification["result_units"] == 27
    assert verification["status"] == "MATCHED_EXACTLY"

    actual = payload["actual_performance"]
    assert actual["owner"] == "Linh"
    assert actual["settled_through"] == "2026-07-24"
    assert actual["total"]["sessions"] == 20
    assert actual["total"]["wins"] == 10
    assert actual["total"]["losses"] == 10
    assert actual["total_net_profit_vnd"] == 15_706_000

    required_html = [
        'data-static-dashboard="1"',
        "MB_STATUS_SAFE_V1",
        "MB_DAILY_CONTROL_LAYOUT_V4_SETTLED_NO_XIEN2",
        "KẾT QUẢ HÔM NAY",
        "24/07/2026",
        "<b>13</b>",
        "<b>55</b>",
        "<b>83</b>",
        "<b>28</b>",
        "50 điểm",
        "25 điểm",
        "150 điểm",
        "3.450.000đ",
        "4.000.000đ",
        "+550.000đ",
        "+15.706.000đ",
        "10 thắng / 10 thua",
        "Rà soát lãi/lỗ thực tế",
        "Dấu vết kiểm toán",
        "Đủ 27/27",
    ]
    for marker in required_html:
        assert marker in html, marker

    forbidden = [
        "CHỜ KẾT QUẢ",
        "KẾ HOẠCH KỲ SẮP TỚI",
        "Bảng chấm điểm công khai",
        "HẠNG 1",
        "HẠNG 2",
        "HẠNG 3",
        "SYSTEM_SIGNAL_NOT_YET_CONFIRMED",
        "Xiên 2",
    ]
    for marker in forbidden:
        assert marker not in html, marker

    print("MB_DAILY_CONTROL_SETTLED_20260724_VALIDATION_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
