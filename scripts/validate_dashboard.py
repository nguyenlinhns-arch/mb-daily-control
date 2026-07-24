#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "MB_DAILY_CONTROL_PUBLIC_V4"
    assert payload["layout_version"] == "MB_DAILY_CONTROL_LAYOUT_V6_CONFIRMED_ORDER_NO_XIEN2"
    assert payload["status"] == "REAL_ORDER_RECORDED_WAITING_RESULT"
    assert payload["audit"]["xien2_visible"] is False
    assert payload["audit"]["live_output_available"] is True
    assert payload["audit"]["user_order_confirmed"] is True

    project = payload["project"]
    assert project["name"] == "MB CHAMPION"
    assert project["champion"] == "R39 DAILY MASTER"
    assert project["production_status"] == "CHAMPION_PAIR_LOCKED_ACTUAL_ORDER_CONFIRMED"

    plan = payload["plan"]
    assert plan["target_date"] == "2026-07-25"
    assert plan["data_lock_date"] == "2026-07-24"
    assert plan["data_status"] == "LOCKED_CROSSCHECKED_27_OF_27"
    assert plan["status"] == "CHỜ KẾT QUẢ"
    assert plan["codes"] == ["52", "83", "54", "90"]
    assert plan["points_by_code"] == {"52": 50, "83": 50, "54": 25, "90": 25}
    assert plan["total_points"] == 150
    assert plan["total_capital_vnd"] == 3_450_000
    assert plan["champion_pair"] == ["52", "83"]
    assert plan["champion_points_by_code"] == {"52": 50, "83": 50}
    assert plan["champion_total_points"] == 100
    assert plan["champion_capital_vnd"] == 2_300_000
    assert plan["capital_overlay_codes"] == ["54", "90"]
    assert plan["capital_overlay_points_by_code"] == {"54": 25, "90": 25}
    assert plan["actual_order"] is True
    assert plan["outcome_known_at_selection"] is False
    assert plan["no_martingale"] is True
    assert plan["no_reverse"] is True
    assert plan["no_extra_codes"] is True

    pending = payload["actual_order_pending"]
    assert pending["codes"] == plan["codes"]
    assert pending["points_by_code"] == plan["points_by_code"]
    assert pending["total_points"] == 150
    assert pending["capital_vnd"] == 3_450_000
    assert pending["status"] == "CHỜ KẾT QUẢ"
    assert pending["current_cumulative_vnd"] == 15_706_000

    actual = payload["latest_actual_settlement"]
    assert actual["date"] == "2026-07-24"
    assert actual["net_profit_vnd"] == 550_000
    assert actual["cumulative_net_profit_vnd"] == 15_706_000

    champion = payload["latest_champion_settlement"]
    assert champion["date"] == "2026-07-24"
    assert champion["codes"] == ["13", "55"]
    assert champion["net_profit_vnd"] == 1_700_000
    assert champion["cumulative_net_profit_vnd"] == 1_100_000

    performance = payload["actual_performance"]
    assert performance["settled_through"] == "2026-07-24"
    assert performance["total"]["sessions"] == 20
    assert performance["total"]["wins"] == 10
    assert performance["total"]["losses"] == 10
    assert performance["total_net_profit_vnd"] == 15_706_000

    required = [
        'data-static-dashboard="1"',
        "MB_STATUS_SAFE_V1",
        "MB_DAILY_CONTROL_LAYOUT_V6_CONFIRMED_ORDER_NO_XIEN2",
        "SỐ HÔM NAY",
        "25/07/2026",
        "<b>52</b>",
        "<b>83</b>",
        "<b>54</b>",
        "<b>90</b>",
        "50 điểm",
        "25 điểm",
        "150 điểm",
        "3.450.000đ",
        "CHỜ KẾT QUẢ",
        "LỆNH ĐÃ KHÓA",
        "Cặp Champion chuẩn",
        "52 – 83 × 50",
        "+550.000đ",
        "+15.706.000đ",
        "+1.700.000đ",
        "+1.100.000đ",
        "RPT_MB_20260725_CONFIRMED_52_83_54_90_150PTS",
    ]
    for marker in required:
        assert marker in html, marker

    forbidden = [
        "CHỜ DỮ LIỆU",
        "CHƯA CÓ SỐ ĐƯỢC KHÓA",
        "KHÔNG PHÁT LỆNH",
        "HẠNG 1",
        "HẠNG 2",
        "HẠNG 3",
        "SYSTEM_SIGNAL_NOT_YET_CONFIRMED",
        "Xiên 2",
    ]
    for marker in forbidden:
        assert marker not in html, marker

    print("MB_DAILY_CONTROL_CONFIRMED_ORDER_20260725_VALIDATION_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
