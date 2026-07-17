#!/usr/bin/env python3
"""Fail a Pages build when the rendered plan and machine data diverge."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path


FORBIDDEN_PUBLIC_TEXT = (
    "Đang tải kế hoạch kỳ sắp tới",
    "SYSTEM_SIGNAL_NOT_YET_CONFIRMED",
)


def vnd(value: int) -> str:
    return f"{value:,}đ".replace(",", ".")


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    method = payload["method"]
    plan = payload["plan"]
    overlay = payload["overlay"]

    assert method["status"] == "PRODUCTION_OFFICIAL"
    assert plan["status"] == "LOCKED_WAITING_RESULT"
    assert plan["outcome_known_at_selection"] is False
    assert plan["core_100_enabled"] is False
    assert plan["other_50_enabled"] is False

    codes = plan["codes"]
    points = plan["points_by_code"]
    assert len(codes) == plan["number_of_codes"] == len(set(codes))
    assert all(len(code) == 2 and code.isdigit() for code in codes)
    assert set(codes) == set(points)
    assert sum(points.values()) == plan["total_points"]
    assert plan["total_points"] * plan["cost_per_point_vnd"] == plan["total_capital_vnd"]
    assert plan["maximum_loss_vnd"] == plan["total_capital_vnd"]

    target = date.fromisoformat(plan["target_date"]).strftime("%d/%m/%Y")
    assert target in html
    assert vnd(plan["total_capital_vnd"]) in html
    for code in codes:
        expected = f"<b>{code}</b><span>{points[code]} ĐIỂM</span>"
        assert expected in html, f"Missing rendered code/points: {code}"

    assert overlay["active"] is (overlay["normalized_margin"] >= overlay["activation_threshold"])
    assert 'data-static-dashboard="1"' in html
    assert "MB_STATUS_SAFE_V1" in html
    for forbidden in FORBIDDEN_PUBLIC_TEXT:
        assert forbidden not in html

    for period in payload["backtest"].values():
        assert period["sessions"] > 0
        assert 0 <= period["hit_days"] <= period["sessions"]
        assert 0 <= period["profit_days"] <= period["sessions"]
        expected_hit = 100 * period["hit_days"] / period["sessions"]
        expected_profit = 100 * period["profit_days"] / period["sessions"]
        assert abs(period["hit_day_rate_pct"] - expected_hit) < 0.0001
        assert abs(period["profit_day_rate_pct"] - expected_profit) < 0.0001

    print(
        "DASHBOARD_VALIDATION_OK",
        plan["target_date"],
        ",".join(codes),
        plan["total_capital_vnd"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
