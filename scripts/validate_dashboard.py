#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_CODES = ["13", "97", "89", "83"]
EXPECTED_POINTS = {"13": 50, "97": 50, "89": 25, "83": 25}
EXPECTED_SETTLED_CODES = ["52", "83", "54", "90"]


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "MB_DAILY_CONTROL_PUBLIC_V6"
    assert payload["layout_version"] == "MB_DAILY_CONTROL_LAYOUT_V8_PLAN_26_NO_XIEN2"
    assert payload["status"] == "PLAN_LOCKED_WAIT_RESULT"
    assert payload["audit"]["xien2_visible"] is False
    assert payload["audit"]["outcome_known_at_selection"] is False

    project = payload["project"]
    assert project["name"] == "MB CHAMPION"
    assert project["runtime"] == "R11167"
    assert project["score_source"] == "R11168"
    assert project["scoring_policy"] == "R11157"
    assert project["carryover_policy"] == "NO_AUTO_CARRYOVER_V1"
    assert project["production_status"] == "DEFAULT_SHADOW_NATIVE_R11167"

    plan = payload["plan"]
    assert plan["target_date"] == "2026-07-26"
    assert plan["target_dmy"] == "26/07/2026"
    assert plan["data_lock_date"] == "2026-07-25"
    assert plan["data_status"] == "LOCKED_27_OF_27"
    assert plan["status"] == "ĐÃ KHÓA · CHỜ KẾT QUẢ"
    assert plan["codes"] == EXPECTED_CODES
    assert plan["points_by_code"] == EXPECTED_POINTS
    assert plan["total_points"] == 150
    assert plan["total_capital_vnd"] == 3_450_000
    assert plan["champion_pair"] == ["13", "97"]
    assert plan["capital_overlay_codes"] == ["89", "83"]
    assert plan["r11118_gate"] is True
    assert plan["r11156_shadow_gate"] is True
    assert plan["outcome_known_at_selection"] is False
    assert plan["tie_review"] is False
    assert plan["no_martingale"] is True
    assert plan["no_reverse"] is True
    assert plan["no_extra_codes"] is True

    settlement = payload["latest_actual_settlement"]
    assert settlement["date"] == "2026-07-25"
    assert settlement["codes"] == EXPECTED_SETTLED_CODES
    assert settlement["hits_by_code"] == {"52": 0, "83": 0, "54": 0, "90": 0}
    assert settlement["total_hits"] == 0
    assert settlement["total_points"] == 150
    assert settlement["capital_vnd"] == 3_450_000
    assert settlement["return_vnd"] == 0
    assert settlement["net_profit_vnd"] == -3_450_000
    assert settlement["cumulative_net_profit_vnd"] == 12_256_000
    assert settlement["status"] == "SETTLED_27_OF_27"
    assert settlement["result_label"] == "TRƯỢT"

    prospective = payload["prospective_v2"]
    assert prospective["start_date"] == "2026-07-26"
    assert prospective["sessions_completed"] == 0
    assert prospective["status"] == "WAIT_RESULT_SESSION_1"

    required = [
        'data-static-dashboard="1"',
        "MB_DAILY_CONTROL_LAYOUT_V8_PLAN_26_NO_XIEN2",
        "KẾ HOẠCH KỲ SẮP TỚI",
        "Chủ Nhật, 26/07/2026",
        "R11167 · GATE ON",
        '<b>13</b>',
        '<b>97</b>',
        '<b>89</b>',
        '<b>83</b>',
        "50 điểm",
        "25 điểm",
        "150 điểm",
        "3.450.000đ",
        "13×50 · 97×50 · 89×25 · 83×25",
        "RPT_MB_20260726_R11167_NATIVE_RUN_V01",
        "Outcome known at selection",
        "false",
    ]
    for marker in required:
        assert marker in html, marker

    # Stale public hero from the 25/07 result page must not remain deployed.
    stale_markers = [
        "KẾT QUẢ HÔM NAY",
        "Thứ Bảy, 25/07/2026",
        "ĐÃ QUYẾT TOÁN · TRƯỢT",
        "MB_DAILY_CONTROL_LAYOUT_V7_SETTLED_25_NO_XIEN2",
        "RPT_MB_20260725_SETTLED_52_83_54_90_150PTS",
        "52×50 · 83×50 · 54×25 · 90×25",
    ]
    for marker in stale_markers:
        assert marker not in html, marker

    forbidden = [
        "CHỜ DỮ LIỆU",
        "CHƯA CÓ SỐ ĐƯỢC KHÓA",
        "KHÔNG PHÁT LỆNH",
        "SYSTEM_SIGNAL_NOT_YET_CONFIRMED",
        "Xiên 2",
    ]
    for marker in forbidden:
        assert marker not in html, marker

    print("MB_DAILY_CONTROL_PLAN_20260726_VALIDATION_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
