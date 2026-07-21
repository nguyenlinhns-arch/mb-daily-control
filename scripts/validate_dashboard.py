#!/usr/bin/env python3
"""Fail a Pages build when the rendered plan and machine data diverge."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_POLICY = ROOT / "data" / "website-layout-policy.json"

FORBIDDEN_PUBLIC_TEXT = (
    "Đang tải kế hoạch kỳ sắp tới",
    "SYSTEM_SIGNAL_NOT_YET_CONFIRMED",
    "Lãi/lỗ tổng",
    "Backtest",
    "P/L phương pháp",
)

REQUIRED_LAYOUT_TEXT = (
    "Kế hoạch kỳ sắp tới",
    "Thống kê thực tế",
    "Số ngày thắng",
    "Số ngày thua",
    "Chuỗi thắng dài nhất",
    "Chuỗi thua dài nhất",
    "Lãi/lỗ thực tế",
    "Tổng thực tế",
)


def vnd(value: int) -> str:
    return f"{value:,}đ".replace(",", ".")


def signed_vnd(value: int) -> str:
    prefix = "+" if value > 0 else ""
    return prefix + vnd(value)


def validate_song_loc(html: str, payload: dict, data_path: Path) -> None:
    method = payload["method"]
    plan = payload["plan"]
    assert method["official_name"] == "SONG LỘC 100"
    assert method["technical_code"] == "FUSION2–100 R23 OPT"
    assert method["status"] == "PRODUCTION_OFFICIAL"
    assert plan["status"] == "LOCKED_WAITING_RESULT"
    assert plan["data_status"] == "LOCKED_CROSSCHECKED_27_OF_27"
    assert plan["outcome_known_at_selection"] is False
    codes = plan["codes"]
    points = plan["points_by_code"]
    assert len(codes) == len(set(codes)) == 2
    assert plan["ranks"] == [2, 3]
    assert plan["rank_1_excluded"] not in codes
    assert list(points) == codes
    assert [points[code] for code in codes] == [50, 50]
    assert plan["total_points"] == 100
    assert sum(points.values()) == 100
    assert plan["total_capital_vnd"] == 2_300_000
    assert plan["maximum_loss_vnd"] == 2_300_000
    assert plan["total_points"] * plan["cost_per_point_vnd"] == 2_300_000
    target_day = date.fromisoformat(plan["target_date"])
    lock_day = date.fromisoformat(plan["data_lock_date"])
    assert target_day == lock_day + timedelta(days=1)
    assert target_day.strftime("%d/%m/%Y") in html
    assert vnd(plan["total_capital_vnd"]) in html
    for code in codes:
        assert f"<b>{code}</b>" in html
        assert "<strong>50 điểm</strong>" in html
    assert "MB SONG LỘC" in html
    assert "SONG LỘC 100" in html
    assert "FUSION4" not in html
    assert "180 điểm" not in html
    assert "method_performance" not in payload
    assert "Sổ phương pháp" not in html
    assert "Lãi/lỗ phương pháp" not in html
    actual = payload["actual_performance"]
    monthly = actual["monthly"]
    assert monthly
    assert sum(period["net_profit_vnd"] for period in monthly) == actual["total_net_profit_vnd"]
    for period in monthly:
        assert period["label"] in html
        assert signed_vnd(period["net_profit_vnd"]) in html
    assert "Tổng lãi/lỗ" in html
    assert signed_vnd(actual["total_net_profit_vnd"]) in html
    de_path = data_path.parent / "de-head-current.json"
    de = json.loads(de_path.read_text(encoding="utf-8"))
    assert de["target_date"] == plan["target_date"]
    assert de["data_lock_date"] == plan["data_lock_date"]
    assert de["decision"] in {"NO_TRADE", "PLAY"}
    assert de["watch_head"] is not None and de["watch_tail"] is not None
    assert de["capital_vnd"] >= 0
    assert 'data-static-dashboard="1"' in html
    assert "MB_STATUS_SAFE_V1" in html
    print("SONG_LOC_DASHBOARD_VALIDATION_OK", plan["target_date"], ",".join(codes))


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") == "MB_SONG_LOC_100_WEB_V1":
        validate_song_loc(html, payload, data_path)
        return
    layout = json.loads(LAYOUT_POLICY.read_text(encoding="utf-8"))
    method = payload["method"]
    plan = payload["plan"]
    overlay = payload["overlay"]
    automation = payload.get("automation", {})
    fusion4 = payload.get("schema_version") == "MB_FUSION4_180_WEB_V1"

    assert layout["schema_version"] == "MB_DAILY_WEBSITE_LAYOUT_V1"
    assert layout["fail_closed"] is True
    assert layout["top_section"]["source"] == "plan"
    assert layout["bottom_section"]["source"] == "actual_performance"
    assert layout["bottom_section"]["owner"] == "Linh"
    assert layout["bottom_section"]["tracking_start_date"] == "2026-07-01"
    assert layout["forbidden_visible_sources"] == [
        "backtest", "group_actual_pnl", "latest_settlement",
    ]

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
        assert f"<b>{code}</b>" in html, f"Missing rendered code: {code}"
        if fusion4:
            assert f"<strong>{points[code]} điểm</strong>" in html
        else:
            assert f"<span>{points[code]} ĐIỂM</span>" in html

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
    for required in REQUIRED_LAYOUT_TEXT:
        assert required in html, f"Thiếu thành phần bố cục bắt buộc: {required}"

    for period in payload["backtest"].values():
        assert period["sessions"] > 0
        assert 0 <= period["hit_days"] <= period["sessions"]
        assert 0 <= period["profit_days"] <= period["sessions"]
        expected_hit = 100 * period["hit_days"] / period["sessions"]
        expected_profit = 100 * period["profit_days"] / period["sessions"]
        assert abs(period["hit_day_rate_pct"] - expected_hit) < 0.0001
        assert abs(period["profit_day_rate_pct"] - expected_profit) < 0.0001

    if fusion4:
        actual = payload["actual_performance"]
        tracking_start = date.fromisoformat(actual["tracking_start_date"])
        actual_settled = date.fromisoformat(actual["settled_through"])
        assert actual["source"] == "LINH_ACTUAL_GOOGLE_SHEETS_LEDGER"
        assert tracking_start <= actual_settled
        assert actual_settled <= lock_day
        assert actual["current_month_id"] == actual_settled.strftime("%Y-%m")
        for period_name in ("current_month", "total"):
            period = actual[period_name]
            sessions = period["sessions"]
            assert sessions >= 0
            assert period["wins"] + period["losses"] == sessions
            for streak in (
                "current_winning_streak", "current_losing_streak",
                "longest_winning_streak", "longest_losing_streak",
            ):
                assert 0 <= period[streak] <= sessions
            assert period["current_winning_streak"] <= period["longest_winning_streak"]
            assert period["current_losing_streak"] <= period["longest_losing_streak"]
            assert signed_vnd(period["net_profit_vnd"]) in html
        assert tracking_start.strftime("%d/%m/%Y") in html
        assert "Lệnh thực tế của Linh" in html
        assert actual_settled.strftime("%d/%m/%Y") in html
        assert html.index("Kế hoạch kỳ sắp tới") < html.index("Thống kê thực tế")

        group = payload["group_actual_pnl"]
        assert group["source"] == "AGGREGATE_5_PERSON_GOOGLE_SHEETS_LEDGERS"
        assert group["people_count"] == 5
        assert date.fromisoformat(group["settled_through"]) <= lock_day

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
