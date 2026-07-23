#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def vnd(value: int, signed: bool = False) -> str:
    prefix = "+" if signed and value > 0 else ""
    return prefix + f"{int(value):,}đ".replace(",", ".")


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "MB_ACTUAL_LINH_WEB_V1"
    assert 'data-static-dashboard="1"' in html
    assert "MB_STATUS_SAFE_V1" in html
    assert "Đang tải kế hoạch kỳ sắp tới" not in html
    assert "SYSTEM_SIGNAL_NOT_YET_CONFIRMED" not in html
    assert "Sổ phương pháp" not in html
    assert "backtest" not in html.lower()
    assert "SONG LỘC" not in html
    assert "R39 DAILY MASTER" not in html

    latest = payload["latest_actual_settlement"]
    performance = payload["actual_performance"]
    monthly = payload["monthly_actual"]
    assert payload["scope"]["tracking_start_date"] == "2026-07-01"
    assert latest["status"] == "REAL_CONFIRMED_SETTLED"
    assert latest["source_result_units"] == 27
    assert len(latest["sources"]) >= 2
    assert latest["net_profit_vnd"] == latest["return_vnd"] - latest["capital_vnd"]
    assert performance["sessions"] == performance["wins"] + performance["losses"]
    assert performance["total_net_profit_vnd"] == latest["cumulative_net_profit_vnd"]
    assert monthly and sum(item["net_profit_vnd"] for item in monthly) == performance["total_net_profit_vnd"]
    assert all(item["sessions"] == item["wins"] + item["losses"] for item in monthly)

    required = [
        latest["date_dmy"],
        vnd(latest["net_profit_vnd"], signed=True),
        vnd(performance["total_net_profit_vnd"], signed=True),
        str(performance["wins"]),
        str(performance["losses"]),
        f'{performance["longest_winning_streak"]} ngày',
        f'{performance["longest_losing_streak"]} ngày',
        "TỔNG TỪ 01/07/2026",
    ]
    for value in required:
        assert value in html, f"Missing rendered value: {value}"
    print("LINH_ACTUAL_DASHBOARD_VALIDATION_OK", latest["date"], performance["total_net_profit_vnd"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
