#!/usr/bin/env python3
"""Validate that the public dashboard and machine payload are causally aligned.

The validator intentionally supports the active MB CHAMPION schema while keeping
basic compatibility with the older SONG LỘC and generic daily schemas. A failed
assertion stops the GitHub Pages deployment instead of leaving a stale page live.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path


def vnd(value: int) -> str:
    return f"{int(value):,}đ".replace(",", ".")


def signed_vnd(value: int) -> str:
    prefix = "+" if value > 0 else ""
    return prefix + vnd(value)


def require_static_safety(html: str) -> None:
    assert 'data-static-dashboard="1"' in html
    assert "MB_STATUS_SAFE_V1" in html
    assert "Đang tải kế hoạch kỳ sắp tới" not in html
    assert "SYSTEM_SIGNAL_NOT_YET_CONFIRMED" not in html


def validate_points_and_dates(
    html: str,
    *,
    target_date: str,
    lock_date: str,
    codes: list[str],
    points_by_code: dict[str, int],
    total_points: int,
    capital_vnd: int,
    cost_per_point_vnd: int,
) -> None:
    assert len(codes) == len(set(codes)) == 2
    assert all(len(code) == 2 and code.isdigit() for code in codes)
    assert list(points_by_code) == codes
    assert all(points_by_code[code] == 50 for code in codes)
    assert sum(points_by_code.values()) == total_points == 100
    assert capital_vnd == total_points * cost_per_point_vnd == 2_300_000

    target = date.fromisoformat(target_date)
    locked = date.fromisoformat(lock_date)
    assert target == locked + timedelta(days=1)
    assert target.strftime("%d/%m/%Y") in html
    assert vnd(capital_vnd) in html
    for code in codes:
        assert f"<b>{code}</b>" in html, f"Missing rendered code: {code}"
    assert html.count("50 điểm") >= 2


def validate_mb_champion(html: str, payload: dict) -> None:
    project = payload["project"]
    order = payload["today_order"]

    assert project["name"] == "MB CHAMPION"
    assert project["champion"] == "R39 DAILY MASTER"
    assert project["status"] == "CHAMPION_ACTIVE"
    assert order["champion"] == "R39 DAILY MASTER"
    assert order["data_status"] == "LOCKED_CROSSCHECKED_27_OF_27"
    assert order["status"] in {"CHỜ KẾT QUẢ", "LOCKED_WAITING_RESULT"}
    assert order["outcome_known_at_selection"] is False
    assert order["no_martingale"] is True
    assert order["no_reverse"] is True
    assert order["no_extra_codes"] is True

    validate_points_and_dates(
        html,
        target_date=order["target_date"],
        lock_date=order["data_lock_date"],
        codes=order["codes"],
        points_by_code=order["points_by_code"],
        total_points=order["total_points"],
        capital_vnd=order["capital_vnd"],
        cost_per_point_vnd=order["cost_per_point_vnd"],
    )

    assert "MB CHAMPION" in html
    assert "R39 DAILY MASTER" in html
    assert "MB SONG LỘC" not in html
    assert "HẠNG 1" not in html and "HẠNG 2" not in html and "HẠNG 3" not in html

    settlement = payload["latest_settlement"]
    assert settlement["date"] == order["data_lock_date"]
    assert settlement["total_hits"] == sum(settlement["hits_by_code"].values())

    champion = settlement["champion_fixed_ledger"]
    champion_points = champion["points_by_code"]
    assert all(champion_points[code] == 50 for code in settlement["codes"])
    assert champion["total_points"] == sum(champion_points.values()) == 100
    assert champion["capital_vnd"] == 2_300_000
    expected_champion_return = sum(
        settlement["hits_by_code"][code] * champion_points[code] * 80_000
        for code in settlement["codes"]
    )
    assert champion["return_vnd"] == expected_champion_return
    assert champion["net_profit_vnd"] == expected_champion_return - champion["capital_vnd"]
    assert signed_vnd(champion["net_profit_vnd"]) in html

    actual = settlement["actual_real_money"]
    actual_points = actual["points_by_code"]
    assert actual["total_points"] == sum(actual_points.values())
    assert actual["capital_vnd"] == actual["total_points"] * 23_000
    expected_actual_return = sum(
        settlement["hits_by_code"][code] * actual_points[code] * 80_000
        for code in settlement["codes"]
    )
    assert actual["return_vnd"] == expected_actual_return
    assert actual["net_profit_vnd"] == expected_actual_return - actual["capital_vnd"]
    assert signed_vnd(actual["net_profit_vnd"]) in html
    assert signed_vnd(actual["cumulative_net_profit_vnd"]) in html

    performance = payload["actual_performance"]
    assert performance["sessions"] == performance["wins"] + performance["losses"]
    assert performance["settled_through"] == order["data_lock_date"]
    assert performance["total_net_profit_vnd"] == actual["cumulative_net_profit_vnd"]

    forward = payload["champion_forward_ledger"]
    assert forward["sessions"] == forward["profitable_days"] + forward["losing_days"]
    assert forward["settled_through"] == order["data_lock_date"]
    assert forward["next_session"] == order["target_date"]

    require_static_safety(html)
    print("MB_CHAMPION_DASHBOARD_VALIDATION_OK", order["target_date"], ",".join(order["codes"]))


def validate_song_loc(html: str, payload: dict) -> None:
    method = payload["method"]
    plan = payload["plan"]
    assert method["official_name"] == "SONG LỘC 100"
    assert method["status"] == "PRODUCTION_OFFICIAL"
    assert plan["status"] == "LOCKED_WAITING_RESULT"
    assert plan["data_status"] == "LOCKED_CROSSCHECKED_27_OF_27"
    assert plan["outcome_known_at_selection"] is False
    validate_points_and_dates(
        html,
        target_date=plan["target_date"],
        lock_date=plan["data_lock_date"],
        codes=plan["codes"],
        points_by_code=plan["points_by_code"],
        total_points=plan["total_points"],
        capital_vnd=plan["total_capital_vnd"],
        cost_per_point_vnd=plan["cost_per_point_vnd"],
    )
    require_static_safety(html)
    print("SONG_LOC_DASHBOARD_VALIDATION_OK", plan["target_date"], ",".join(plan["codes"]))


def validate_generic(html: str, payload: dict) -> None:
    plan = payload["plan"]
    assert plan["status"] == "LOCKED_WAITING_RESULT"
    assert plan["outcome_known_at_selection"] is False
    codes = plan["codes"]
    points = plan["points_by_code"]
    assert len(codes) == len(set(codes))
    assert set(codes) == set(points)
    assert sum(points.values()) == plan["total_points"]
    assert plan["total_capital_vnd"] == plan["total_points"] * plan["cost_per_point_vnd"]
    target = date.fromisoformat(plan["target_date"])
    locked = date.fromisoformat(plan["data_lock_date"])
    assert target == locked + timedelta(days=1)
    assert target.strftime("%d/%m/%Y") in html
    for code in codes:
        assert f"<b>{code}</b>" in html
    require_static_safety(html)
    print("DASHBOARD_VALIDATION_OK", plan["target_date"], ",".join(codes))


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    schema = payload.get("schema_version", "")
    if schema.startswith("MB_CHAMPION_WEB_V"):
        validate_mb_champion(html, payload)
    elif schema.startswith("MB_SONG_LOC_100_WEB_V"):
        validate_song_loc(html, payload)
    else:
        validate_generic(html, payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
