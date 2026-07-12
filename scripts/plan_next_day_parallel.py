#!/usr/bin/env python3
"""Parallel A1/X2/X3 funding wrapper for the permanent MB planner.

Canonical rule:
- Evaluate A1, X2 Exact and X3 Exact independently.
- Fund every method that passes on the same draw day.
- Dedupe the same two-digit code across methods at the highest stake.
- Use ROLL7 rescue30 only when no standard method passes and the rolling
  5-of-7 floor requires a signal day.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
from datetime import date, timedelta
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("mb_base_planner", HERE / "plan_next_day.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load plan_next_day.py")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

CONFIG_ID = "MB_PARALLEL_EXACT_ROLL7_REAL30_V1_20260712"
CONTROLLER_RULE = ["A1_INDEPENDENT", "X2_EXACT_INDEPENDENT", "X3_EXACT_INDEPENDENT", "ROLL7_IF_NONE", "A0"]
X2_POINTS = 50
ROLL7_POINTS = 30


def _fund(points_by_code: dict[str, int], code: str, points: int) -> None:
    points_by_code[code] = max(int(points_by_code.get(code, 0)), int(points))


def _method_number(code: str, points: int, label: str) -> dict[str, Any]:
    return {
        "code": code,
        "points": points,
        "capital_vnd": points * base.LO_COST_PER_POINT,
        "role": label,
    }


def _prior6_a0(target: date) -> tuple[int, int]:
    ledger = base.load_json(base.PLAN_LEDGER_FILE, {"plans": {}})
    plans = ledger.get("plans") or {}
    known = 0
    a0 = 0
    for offset in range(1, 7):
        day = (target - timedelta(days=offset)).isoformat()
        entry = plans.get(day)
        if not entry:
            continue
        known += 1
        decision = str(entry.get("decision", "")).upper()
        if decision.startswith("A0"):
            a0 += 1
    return a0, known


def _rescue_codes(features: dict[str, dict[str, Any]], x3: dict[str, Any]) -> tuple[list[str], str]:
    rows = base.x2_pair_stats(features)
    pool = [
        row for row in rows
        if max(int(row["gan_main"]), int(row["gan_cover"])) <= 7
        and int(row["dgan"]) <= 2
        and int(row["h5_pair"]) <= 5
        and float(row["primary"]) >= 0.58
    ]
    pool.sort(key=lambda row: (-float(row["tv21"]), str(row["pair"])))
    if pool:
        row = pool[0]
        legs = [
            (str(row["main"]), int(row["gan_main"]), int(row["h21_main"])),
            (str(row["cover"]), int(row["gan_cover"]), int(row["h21_cover"])),
        ]
        legs.sort(key=lambda x: (x[1], -x[2], x[0]))
        selected = [legs[0][0]]
        if legs[1][2] >= 6:
            selected.append(legs[1][0])
        return selected, f"ROLL7 X2 Cover58 pair {row['pair']} TV21={row['tv21']:.4f}"
    basket = x3.get("basket") or []
    if basket:
        return [str(basket[0]["code"])], "ROLL7 X3 top1 fallback"
    return [], "ROLL7 no valid rescue candidate"


def make_parallel_plan(
    doc: dict[str, Any],
    history: list[tuple[date, list[str]]],
    history_source: str,
    brake: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    out, _ = base.make_plan(doc, history, history_source, brake)
    locked_date, latest_codes = history[-1]
    target_date = locked_date + timedelta(days=1)
    latest_counts = base.Counter(latest_codes)
    repeat2_count = sum(1 for count in latest_counts.values() if count >= 2)
    max_frequency = max(latest_counts.values())
    features = base.build_features(history)
    a1 = base.a1_candidates(features, repeat2_count, max_frequency, target_date)
    x2 = base.build_x2(features, brake, target_date)
    x3 = base.build_x3(features, repeat2_count, max_frequency, target_date)

    methods: list[dict[str, Any]] = []
    points_by_code: dict[str, int] = {}

    a1_pick = a1.get("core") or a1.get("volume")
    if a1_pick is not None:
        code = str(a1_pick["code"])
        tier = "CORE" if a1.get("core") is not None else "VOLUME"
        main_points = base.A1_CORE_POINTS if tier == "CORE" else base.A1_VOLUME_POINTS
        codes = [code]
        _fund(points_by_code, code, main_points)
        reverse = code[::-1]
        if reverse != code:
            codes.append(reverse)
            _fund(points_by_code, reverse, 50)
        methods.append({
            "id": f"A1_{tier}",
            "label": f"A1 {tier.title()}",
            "status": "PASS_REAL_PENDING",
            "codes": codes,
            "points_by_code": {c: (main_points if c == code else 50) for c in codes},
        })

    # X2 standard Exact ignores the legacy rescue-pilot brake; exact gates decide.
    x2_selected = None
    x2_tier = None
    if bool(x2["core_rank"]["core_gate"]):
        x2_selected, x2_tier = x2["core_rank"], "CORE_EXACT"
    elif bool(x2["balanced_rank"]["balanced_gate"]):
        x2_selected, x2_tier = x2["balanced_rank"], "BALANCED_EXACT"
    if x2_selected is not None:
        codes = [str(x2_selected["main"]), str(x2_selected["cover"])]
        for code in codes:
            _fund(points_by_code, code, X2_POINTS)
        methods.append({
            "id": f"X2_{x2_tier}",
            "label": f"X2 {x2_tier.replace('_', ' ').title()}",
            "status": "PASS_REAL_PENDING",
            "codes": codes,
            "points_by_code": {c: X2_POINTS for c in codes},
        })

    if bool(x3.get("gate")):
        codes = [str(item["code"]) for item in x3["basket"]]
        for code in codes:
            _fund(points_by_code, code, base.X3_POINTS)
        methods.append({
            "id": "X3_GROWTH_EXACT",
            "label": "X3 Growth Exact",
            "status": "PASS_REAL_PENDING",
            "codes": codes,
            "points_by_code": {c: base.X3_POINTS for c in codes},
        })

    rescue_required = False
    rescue_reason = ""
    if not methods:
        prior_a0, known = _prior6_a0(target_date)
        rescue_required = known == 6 and prior_a0 >= 2
        if rescue_required:
            rescue, rescue_reason = _rescue_codes(features, x3)
            if rescue:
                for code in rescue:
                    _fund(points_by_code, code, ROLL7_POINTS)
                methods.append({
                    "id": "ROLL7_RESCUE30",
                    "label": "ROLL7 5-of-7 Rescue",
                    "status": "PASS_REAL_PENDING",
                    "codes": rescue,
                    "points_by_code": {c: ROLL7_POINTS for c in rescue},
                })

    selection = list(points_by_code)
    total_points = sum(points_by_code.values())
    capital = total_points * base.LO_COST_PER_POINT
    pending = bool(selection)
    standard_count = sum(1 for method in methods if not method["id"].startswith("ROLL7"))
    decision = (
        "A0" if not pending
        else "ROLL7_RESCUE30" if methods[0]["id"].startswith("ROLL7")
        else "PARALLEL_EXACT" if standard_count > 1
        else methods[0]["id"]
    )
    method_labels = " + ".join(method["label"] for method in methods)

    out["schema_version"] = "MB_DAILY_WEB_V8_PARALLEL_PLAN"
    out["config_id"] = CONFIG_ID
    out["funding_policy"] = {
        "mode": "PARALLEL_INDEPENDENT_ALL_EXACT_PASS",
        "methods": ["A1", "X2", "X3"],
        "no_cross_method_blocking": True,
        "dedupe_same_code_by_max_stake": True,
        "roll7_only_when_no_standard_pass": True,
    }
    out["stake_rule"] = {
        "a1_core_main_points": 100,
        "a1_volume_main_points": 50,
        "a1_reverse_points": 50,
        "x2_exact_points_per_code": 50,
        "x3_exact_points_per_code": 50,
        "roll7_rescue_points_per_code": 30,
        "lo_cost_per_point_vnd": base.LO_COST_PER_POINT,
        "lo_payout_per_hit_point_vnd": base.LO_PAYOUT_PER_HIT_POINT,
        "controller_rule": CONTROLLER_RULE,
        "note": "Fund every passing A1/X2/X3 method; duplicate code funded once at highest stake.",
    }
    out["top_signal_policy"] = {
        "mode": "PARALLEL_EXACT_AUTO_PLAN",
        "controller": " | ".join(CONTROLLER_RULE),
        "system_signals_preserved_in_groups": True,
        "pnl_rule": "No P/L until explicit pre-draw execution confirmation.",
    }
    out["portfolio"] = {
        "decision": decision,
        "tier": "A0" if not pending else f"{method_labels} - CHO XAC NHAN",
        "selection": "-".join(selection) if selection else "A0",
        "title": "A0 - KHONG CO LENH" if not pending else f"PARALLEL: {method_labels}",
        "points": total_points,
        "points_by_code": points_by_code,
        "capital_vnd": capital,
        "payout_vnd": 0,
        "pnl_vnd": 0,
        "reason": (
            "Fund all standard methods that pass independently."
            if standard_count
            else rescue_reason if rescue_required
            else "No standard method passes and ROLL7 rescue is not required."
        ),
        "pnl_status": "NOT_INCLUDED_UNTIL_CONFIRMED",
    }
    if pending:
        out["pending_order"] = {
            "status": "SYSTEM_SIGNAL_NOT_YET_CONFIRMED",
            "date": base.iso_day(target_date),
            "method_id": decision,
            "selection": selection,
            "points_by_code": points_by_code,
            "capital_vnd": capital,
            "components": copy.deepcopy(methods),
            "pnl_included": False,
            "note": "Convert to actual_order only after explicit pre-draw confirmation.",
        }
    else:
        out.pop("pending_order", None)

    web_methods = []
    for method in methods:
        numbers = [_method_number(code, int(method["points_by_code"][code]), "System signal; unconfirmed") for code in method["codes"]]
        method_capital = sum(n["capital_vnd"] for n in numbers)
        web_methods.append({
            "id": method["id"],
            "label": method["label"],
            "method": method["id"],
            "status": method["status"],
            "points_per_code": 0 if len(set(method["points_by_code"].values())) > 1 else next(iter(method["points_by_code"].values())),
            "points_by_code": method["points_by_code"],
            "code_count": len(method["codes"]),
            "capital_vnd": method_capital,
            "numbers": numbers,
        })
    out["top_signals"] = {
        "title": f"KE HOACH PARALLEL {target_date.strftime('%d/%m/%Y')}",
        "subtitle": "A0" if not pending else method_labels,
        "total_methods": len(methods),
        "total_numbers": f"{len(selection)} ma",
        "total_points": f"{total_points} diem",
        "total_capital_vnd": capital,
        "note": "A1/X2/X3 pass methods are all funded; same code is deduped at max stake.",
        "methods": web_methods,
    }

    # Correct method-group funding displays.
    a1_group = base.find_group(out, "A1") or {}
    if a1_pick is not None:
        a1_codes = methods[0]["codes"] if methods and methods[0]["id"].startswith("A1") else [str(a1_pick["code"])]
        a1_group["selected_numbers"] = a1_codes
        a1_group["points_by_code"] = {c: points_by_code[c] for c in a1_codes}
        a1_group["points"] = sum(a1_group["points_by_code"].values())
        a1_group["capital_vnd"] = a1_group["points"] * base.LO_COST_PER_POINT
        a1_group["role"] = "PRODUCTION INDEPENDENT"
    else:
        a1_group["points"] = 0
        a1_group["capital_vnd"] = 0
    base.replace_group(out, a1_group)

    x2_group = base.find_group(out, "X2") or {}
    if x2_selected is not None:
        x2_codes = [str(x2_selected["main"]), str(x2_selected["cover"])]
        x2_group["status"] = f"PASS_{x2_tier}"
        x2_group["role"] = "PRODUCTION INDEPENDENT"
        x2_group["selected_numbers"] = x2_codes
        x2_group["points"] = X2_POINTS * 2
        x2_group["capital_vnd"] = X2_POINTS * 2 * base.LO_COST_PER_POINT
        x2_group["summary"] = f"Qualified pair {x2_selected['pair']} ({x2_tier})."
    else:
        x2_group["points"] = 0
        x2_group["capital_vnd"] = 0
    base.replace_group(out, x2_group)

    x3_group = base.find_group(out, "X3") or {}
    if x3.get("gate"):
        x3_group["role"] = "PRODUCTION INDEPENDENT"
        x3_group["points"] = base.X3_POINTS * len(x3["basket"])
        x3_group["capital_vnd"] = x3_group["points"] * base.LO_COST_PER_POINT
    else:
        x3_group["points"] = 0
        x3_group["capital_vnd"] = 0
    base.replace_group(out, x3_group)

    q = out.setdefault("pnl_summary", {})
    q["today_pending_capital_vnd"] = capital
    q["today_pending_order"] = "A0" if not pending else f"{method_labels}; {points_by_code}"
    q["today_included"] = False

    plan_core = {
        "target_date": base.iso_day(target_date),
        "locked_through": base.iso_day(locked_date),
        "data_hash": base.json_hash(latest_codes),
        "controller": CONTROLLER_RULE,
        "portfolio": out["portfolio"],
        "top_signals": out["top_signals"],
        "groups": [base.find_group(out, group_id) for group_id in base.MILESTONE_GROUPS],
        "milestone_policy": out["milestone_policy"],
    }
    plan_hash = base.json_hash(plan_core)
    run_id = f"RPT_MB_{target_date.strftime('%Y%m%d')}_PARALLEL_{plan_hash[:12].upper()}"
    generated = base.now_vn().isoformat(timespec="seconds")
    out["report_run_id"] = run_id
    out["source_run_id"] = f"LOCK_{locked_date.strftime('%Y%m%d')}_{base.json_hash(latest_codes)[:10].upper()}"
    out["generated_at"] = generated
    out["automation"] = {
        "status": "PARALLEL_PLAN_READY_FOR_WEB",
        "pipeline_version": "MB_DAILY_PIPELINE_PARALLEL_V1",
        "source": f"GOOGLE_SHEET_XLSX:{history_source}",
        "last_updated_at": generated,
        "locked_through": base.iso_day(locked_date),
        "target_date": base.iso_day(target_date),
        "settlement_checked": True,
        "signal_review_complete": True,
        "milestones_complete": True,
        "plan_hash": plan_hash,
        "website_refresh_seconds": 120,
    }
    snapshot = {
        "schema_version": "MB_DAILY_PLAN_SNAPSHOT_PARALLEL_V1",
        "report_run_id": run_id,
        "plan_hash": plan_hash,
        "generated_at": generated,
        "locked_through": base.iso_day(locked_date),
        "target_date": base.iso_day(target_date),
        "data_snapshot": out.get("data"),
        "controller_order": CONTROLLER_RULE,
        "portfolio": out["portfolio"],
        "top_signals": out["top_signals"],
        "groups": [base.find_group(out, group_id) for group_id in ("A1", "X2", "X3", "XIEN", "DE")],
        "milestone_policy": out["milestone_policy"],
        "validation": {
            "data_27_ok": len(latest_codes) == 27,
            "milestones_complete": True,
            "x2_performance_metrics_absent": True,
            "pnl_not_included_without_confirmation": True,
            "parallel_all_pass_funding": True,
        },
    }
    base.validate_plan(out)
    return out, snapshot


def self_test() -> None:
    base.self_test()
    points: dict[str, int] = {}
    _fund(points, "54", 50)
    _fund(points, "54", 30)
    assert points == {"54": 50}
    print("PARALLEL_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--data-fail")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.data_fail:
        changed = base.data_fail(args.data_fail)
        print(f"DATA_FAIL_A0 written={changed}")
        return
    if not base.DATA_FILE.exists():
        raise RuntimeError(f"Missing {base.DATA_FILE}")
    doc = base.load_json(base.DATA_FILE, {})
    xlsx_path, temp_handle = base.obtain_xlsx()
    try:
        history, source, brake = base.load_history_and_brake(xlsx_path, doc)
        planned, snapshot = make_parallel_plan(doc, history, source, brake)
        changed = base.persist_plan(planned, snapshot)
        print(f"PARALLEL_PLAN_OK target={snapshot['target_date']} decision={snapshot['portfolio']['decision']} selection={snapshot['portfolio']['selection']} changed={changed}")
    finally:
        if temp_handle is not None:
            temp_handle.close()


if __name__ == "__main__":
    main()
