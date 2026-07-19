#!/usr/bin/env python3
"""Fail a Pages build when the rendered plan and machine data diverge."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
import math
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
    automation = payload.get("automation", {})
    fusion4 = payload.get("schema_version") == "MB_FUSION4_180_WEB_V1"

    assert method["status"] == "PRODUCTION_OFFICIAL"
    assert plan["status"] == "LOCKED_WAITING_RESULT"
    assert plan["outcome_known_at_selection"] is False
    assert plan["core_100_enabled"] is False
    assert plan["other_50_enabled"] is False
    assert automation.get("status") in {
        "MANUAL_CUTOVER_VALIDATED",
        "SHEETS_APPLIED_READBACK_VERIFIED_READY_TO_PUBLISH",
    }

    codes = plan["codes"]
    points = plan["points_by_code"]
    assert len(codes) == plan["number_of_codes"] == len(set(codes))
    assert 1 <= len(codes) <= 12
    assert all(len(code) == 2 and code.isdigit() for code in codes)
    assert set(codes) == set(points)
    if fusion4:
        assert [points[code] for code in codes] == [50, 50, 50, 30]
        assert plan["ranked_points"] == [50, 50, 50, 30]
        assert plan["number_of_codes"] == 4
        assert plan["total_points"] == 180
    else:
        expected_points = 30 if len(codes) <= 6 else 25 if len(codes) <= 8 else 20
        assert plan["points_per_code"] == expected_points
        assert all(value == expected_points for value in points.values())
    assert sum(points.values()) == plan["total_points"]
    assert plan["total_points"] * plan["cost_per_point_vnd"] == plan["total_capital_vnd"]
    assert plan["maximum_loss_vnd"] == plan["total_capital_vnd"]

    target_day = date.fromisoformat(plan["target_date"])
    lock_day = date.fromisoformat(plan["data_lock_date"])
    assert target_day == lock_day + timedelta(days=1)
    target = target_day.strftime("%d/%m/%Y")
    assert target in html
    assert vnd(plan["total_capital_vnd"]) in html
    for code in codes:
        expected = f"<b>{code}</b><span>{points[code]} ĐIỂM"
        assert expected in html, f"Missing rendered code/points: {code}"

    expected_active = (
        bool(overlay["eligible_width"])
        and overlay["normalized_margin"] >= overlay["activation_threshold"]
    )
    assert math.isfinite(overlay["normalized_margin"])
    assert math.isfinite(overlay["activation_threshold"])
    assert overlay["activation_threshold"] > 0
    assert overlay["active"] is expected_active
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

    settlement = payload.get("latest_settlement")
    if settlement is not None:
        assert settlement["date"] == plan["data_lock_date"]
        settlement_points = settlement["points_by_code"]
        assert set(settlement["codes"]) == set(settlement_points)
        assert sum(settlement_points.values()) == settlement["total_points"]
        assert settlement["capital_vnd"] == settlement["total_points"] * 23_000
        expected_payout = sum(
            settlement["hits_by_code"][code] * settlement_points[code] * 80_000
            for code in settlement["codes"]
        )
        assert settlement["payout_vnd"] == expected_payout
        assert settlement["pnl_vnd"] == expected_payout - settlement["capital_vnd"]
        expected_roi = 100 * settlement["pnl_vnd"] / settlement["capital_vnd"]
        assert abs(settlement["roi_pct"] - expected_roi) < 0.0001

    public_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for private_marker in (
        '"private"', '"people"', '"pnl_sheet_id"',
        '"blocked_personal_rows"', '"sheet_name"',
    ):
        assert private_marker not in public_text

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
