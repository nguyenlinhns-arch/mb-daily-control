#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "MB_DAILY_CONTROL_PUBLIC_V3"
    assert payload["layout_version"] == "MB_DAILY_CONTROL_LAYOUT_V5_WAITING_DATA_NO_XIEN2"
    assert payload["status"] == "WAITING_DATA_NO_LIVE_OUTPUT"
    assert payload["audit"]["xien2_visible"] is False
    assert payload["audit"]["fail_closed"] is True
    assert payload["audit"]["live_output_available"] is False

    project = payload["project"]
    assert project["name"] == "MB CHAMPION"
    assert project["champion"] == "R39 DAILY MASTER"
    assert project["production_status"] == "NO_ORDER_FAIL_CLOSED"

    plan = payload["plan"]
    assert plan["target_date"] == "2026-07-25"
    assert plan["data_lock_date"] == "2026-07-24"
    assert plan["data_status"] == "LOCKED_CROSSCHECKED_27_OF_27"
    assert plan["status"] == "CHỜ DỮ LIỆU"
    assert plan["codes"] == []
    assert plan["points_by_code"] == {}
    assert plan["total_points"] == 0
    assert plan["total_capital_vnd"] == 0
    assert plan["production_order"] is False
    assert plan["outcome_known_at_selection"] is False
    assert plan["no_martingale"] is True
    assert plan["no_reverse"] is True
    assert plan["no_extra_codes"] is True
    assert plan["reason_code"] == "NO_VALID_TARGET_25_LIVE_OUTPUT"
    assert "R39 DAILY MASTER" in plan["missing_live_outputs"]

    actual = payload["latest_actual_settlement"]
    assert actual["date"] == "2026-07-24"
    assert actual["net_profit_vnd"] == 550_000
    assert actual["cumulative_net_profit_vnd"] == 15_706_000
    assert actual["result_label"] == "CÓ LÃI"

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
        "MB_DAILY_CONTROL_LAYOUT_V5_WAITING_DATA_NO_XIEN2",
        "SỐ HÔM NAY",
        "25/07/2026",
        "CHỜ DỮ LIỆU",
        "CHƯA CÓ SỐ ĐƯỢC KHÓA",
        "0 số",
        "0 điểm",
        "Vốn hôm nay",
        "0đ",
        "KHÔNG PHÁT LỆNH",
        "R39 DAILY MASTER",
        "24/07/2026 · 27/27",
        "Kết quả và lãi/lỗ gần nhất",
        "+550.000đ",
        "+15.706.000đ",
        "+1.700.000đ",
        "+1.100.000đ",
        "10 thắng / 10 thua",
        "RPT_MB_20260725_WAITING_DATA_NO_OUTPUT",
    ]
    for marker in required:
        assert marker in html, marker

    forbidden = [
        "CHỜ KẾT QUẢ",
        "KẾT QUẢ HÔM NAY",
        "HẠNG 1",
        "HẠNG 2",
        "HẠNG 3",
        "SYSTEM_SIGNAL_NOT_YET_CONFIRMED",
        "Xiên 2",
    ]
    for marker in forbidden:
        assert marker not in html, marker

    print("MB_DAILY_CONTROL_WAITING_DATA_20260725_VALIDATION_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
