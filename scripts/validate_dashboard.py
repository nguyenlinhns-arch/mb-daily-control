#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "MB_DAILY_CONTROL_PUBLIC_V2"
    assert payload["layout_version"] == "MB_DAILY_CONTROL_LAYOUT_V3_NO_XIEN2"
    assert payload["status"] == "PLAN_PUBLISHED"
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

    verification = payload["source_verification"]
    assert verification["independent_sources"] >= 2
    assert verification["result_units"] == 27
    assert verification["status"] == "MATCHED_EXACTLY"

    de = payload["de_head_tail"]
    assert de["target_date"] == "2026-07-24"
    assert de["watch_head"] == "8"
    assert de["watch_tail"] == "6"
    assert de["tail_metrics"]["gate_met"] is True

    actual = payload["actual_performance"]
    assert actual["owner"] == "Linh"
    assert actual["settled_through"] == "2026-07-23"
    assert actual["total"]["wins"] == 9
    assert actual["total"]["losses"] == 10
    assert actual["total"]["longest_winning_streak"] == 3
    assert actual["total"]["longest_losing_streak"] == 4
    assert actual["total_net_profit_vnd"] == 15_156_000

    required_html = [
        'data-static-dashboard="1"',
        "MB_STATUS_SAFE_V1",
        "MB_DAILY_CONTROL_LAYOUT_V3_NO_XIEN2",
        "KẾ HOẠCH KỲ SẮP TỚI",
        "24/07/2026",
        "<b>13</b>",
        "<b>55</b>",
        "<b>83</b>",
        "<b>28</b>",
        "150 điểm",
        "3.450.000đ",
        "Bảng chấm điểm công khai",
        "Đề đầu/đuôi hôm nay",
        "Lãi/lỗ thực tế của Linh",
        "+15.156.000đ",
        "Dấu vết kiểm toán",
        "2 nguồn · đủ 27/27",
    ]
    for marker in required_html:
        assert marker in html, marker

    section_order = [
        "KẾ HOẠCH KỲ SẮP TỚI",
        "Bảng chấm điểm công khai",
        "Đề đầu/đuôi hôm nay",
        "Lãi/lỗ thực tế của Linh",
        "Dấu vết kiểm toán",
    ]
    positions = [html.index(marker) for marker in section_order]
    assert positions == sorted(positions), positions

    forbidden = [
        "Dữ liệu tài chính riêng tư đã được ẩn",
        "Mở kế hoạch 24/07",
        "Đang tải kế hoạch kỳ sắp tới",
        "SYSTEM_SIGNAL_NOT_YET_CONFIRMED",
        "Khối thực chiến Xiên 2",
        "Xiên 2",
        "52–32",
        "52–91",
        "32–91",
    ]
    for marker in forbidden:
        assert marker not in html, marker

    print("MB_DAILY_CONTROL_LAYOUT_V3_NO_XIEN2_VALIDATION_OK", payload["reviewed_through"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
