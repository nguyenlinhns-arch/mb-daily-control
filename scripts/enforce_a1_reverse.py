#!/usr/bin/env python3
"""Khóa vĩnh viễn quy tắc số đảo A1 trên payload website.

Quy tắc:
- Mã đảo của A1 luôn 50 điểm/số, áp dụng cho cả Core và Volume.
- Nếu mã chính tự đảo (00, 11, ..., 99), không tạo lệnh đảo thứ hai.
- Tuyệt đối không nhân đôi cùng một mã trong selection, vốn, điểm hoặc quyết toán.
- Số đảo là cấu phần phụ thuộc của A1, không phải tín hiệu/gate độc lập.

Script chạy idempotent sau mọi lần pipeline ghi data/current.json. Nó đồng bộ cùng
quy tắc sang snapshot kế hoạch, review ledger và automation state.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data" / "current.json"
POLICY = ROOT / "data" / "automation-policy.json"
REVIEW_LEDGER = ROOT / "data" / "review-ledger.json"
AUTOMATION_STATE = ROOT / "data" / "automation-state.json"
SETTLEMENT_LEDGER = ROOT / "data" / "settlement-ledger.json"
DEFAULT_COST_PER_POINT = 23_000
DEFAULT_PAY_PER_HIT_POINT = 80_000
REVERSE_POINTS = 50
RULE_VERSION = "A1_REVERSE50_NO_DUPLICATE_V1"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def code2(value: Any) -> str | None:
    if value is None:
        return None
    text = "".join(ch for ch in str(value) if ch.isdigit())
    if not text:
        return None
    return text[-2:].zfill(2)


def append_note(text: Any, note: str) -> str:
    base = str(text or "").strip()
    if note in base:
        return base
    return f"{base} {note}".strip()


def find_group(doc: dict[str, Any], group_id: str) -> dict[str, Any] | None:
    wanted = group_id.upper()
    for group in doc.get("groups") or []:
        if str(group.get("id", "")).upper() == wanted:
            return group
    return None


def find_a1_method(doc: dict[str, Any]) -> dict[str, Any] | None:
    for method in (doc.get("top_signals") or {}).get("methods") or []:
        if str(method.get("id", "")).upper().startswith("A1"):
            return method
    return None


def is_a1_active(doc: dict[str, Any], a1: dict[str, Any] | None) -> bool:
    decision = str((doc.get("portfolio") or {}).get("decision", "")).upper()
    if decision.startswith("A1_"):
        return True
    status = str((a1 or {}).get("status", "")).upper()
    if "PASS_CORE" in status or "PASS_VOLUME" in status:
        return True
    pending = doc.get("pending_order") or {}
    return str(pending.get("method_id", "")).upper().startswith("A1")


def primary_code(doc: dict[str, Any], a1: dict[str, Any]) -> str | None:
    existing = code2((a1.get("reverse_policy") or {}).get("primary_code"))
    if existing:
        return existing
    pending = doc.get("pending_order") or {}
    existing = code2(pending.get("primary_code"))
    if existing:
        return existing
    method = find_a1_method(doc)
    if method:
        numbers = method.get("numbers") or []
        if numbers:
            existing = code2(numbers[0].get("code"))
            if existing:
                return existing
    selected = a1.get("selected_numbers") or []
    if selected:
        existing = code2(selected[0])
        if existing:
            return existing
    for candidate in a1.get("candidates") or []:
        if candidate.get("gate"):
            existing = code2(candidate.get("code"))
            if existing:
                return existing
    candidates = a1.get("candidates") or []
    return code2(candidates[0].get("code")) if candidates else None


def configured_points(doc: dict[str, Any], a1: dict[str, Any]) -> int:
    policy = load_json(POLICY, {})
    a1_policy = policy.get("a1") or {}
    stake = doc.get("stake_rule") or {}
    decision = str((doc.get("portfolio") or {}).get("decision", "")).upper()
    status = str(a1.get("status", "")).upper()
    if "CORE" in decision or "PASS_CORE" in status:
        return int(
            a1_policy.get("core_points_per_code")
            or stake.get("a1_core_points_per_code")
            or 100
        )
    if "VOLUME" in decision or "PASS_VOLUME" in status:
        return int(
            a1_policy.get("volume_points_per_code")
            or stake.get("a1_volume_points_per_code")
            or 50
        )
    method = find_a1_method(doc)
    if method:
        numbers = method.get("numbers") or []
        if numbers and numbers[0].get("points") is not None:
            return int(numbers[0]["points"])
        if method.get("points_per_code") is not None:
            try:
                return int(method["points_per_code"])
            except (TypeError, ValueError):
                pass
    return int(a1.get("points_per_code") or a1.get("points") or 50)


def reverse_candidate(primary: dict[str, Any], reverse: str) -> dict[str, Any]:
    return {
        "code": reverse,
        "rank": 2,
        "gate": True,
        "status": "A1 REVERSE50",
        "component": "A1_REVERSE50",
        "reason": "Số đảo chính thức đi kèm mã A1 chính; 50 điểm; không xét gate độc lập.",
        "earliest_eligible_date": primary.get("earliest_eligible_date"),
        "earliest_condition": (
            "Chỉ vào cùng mã A1 chính khi mã chính đạt gate và được xác nhận. "
            "Không đánh riêng; nếu đảo trùng mã chính thì không tạo lệnh thứ hai."
        ),
        "milestone_type": "DEPENDENT_REVERSE",
    }


def ensure_a1_reverse(doc: dict[str, Any]) -> bool:
    before = copy.deepcopy(doc)
    stake = doc.setdefault("stake_rule", {})
    stake.update(
        {
            "a1_reverse_points_per_code": REVERSE_POINTS,
            "a1_reverse_apply_to_core": True,
            "a1_reverse_apply_to_volume": True,
            "a1_reverse_skip_when_same": True,
            "a1_no_duplicate_same_code": True,
            "a1_reverse_rule_version": RULE_VERSION,
        }
    )
    doc.setdefault("top_signal_policy", {})["a1_reverse_rule"] = (
        "A1 reverse=50 points; skip when reverse equals primary; never duplicate a code"
    )

    a1 = find_group(doc, "A1")
    if not a1 or not is_a1_active(doc, a1):
        automation = doc.setdefault("automation", {})
        automation["a1_reverse_rule_version"] = RULE_VERSION
        automation["a1_reverse_rule_complete"] = True
        return doc != before

    primary = primary_code(doc, a1)
    if not primary:
        raise RuntimeError("A1 active nhưng không xác định được mã chính")
    reverse = primary[::-1]
    distinct = reverse != primary
    primary_points = configured_points(doc, a1)
    cost_per_point = int(stake.get("lo_cost_per_point_vnd") or DEFAULT_COST_PER_POINT)
    points_by_code = {primary: primary_points}
    if distinct:
        points_by_code[reverse] = REVERSE_POINTS
    selection = list(points_by_code)
    total_points = sum(points_by_code.values())
    total_capital = total_points * cost_per_point

    a1["selected_numbers"] = selection
    a1["points_by_code"] = points_by_code
    a1["points"] = total_points
    a1["capital_vnd"] = total_capital
    a1["reverse_policy"] = {
        "version": RULE_VERSION,
        "primary_code": primary,
        "reverse_code": reverse,
        "configured_reverse_points": REVERSE_POINTS,
        "applied_reverse_points": REVERSE_POINTS if distinct else 0,
        "reverse_is_distinct": distinct,
        "duplicate_bet_forbidden": True,
        "status": "APPLIED_DISTINCT_REVERSE" if distinct else "SKIPPED_SAME_CODE",
    }
    if distinct:
        rule_note = f"Số đảo {reverse} đi kèm 50 điểm."
    else:
        rule_note = f"{primary} đảo vẫn là {primary}; không đánh đảo và không đánh lặp hai lần cùng mã."
    a1["summary"] = append_note(a1.get("summary"), rule_note)
    a1["reason"] = append_note(a1.get("reason"), rule_note)

    candidates = [
        c
        for c in (a1.get("candidates") or [])
        if str(c.get("component", "")).upper() != "A1_REVERSE50"
        and "A1 REVERSE50" not in str(c.get("status", "")).upper()
    ]
    primary_candidate = next(
        (c for c in candidates if code2(c.get("code")) == primary),
        candidates[0] if candidates else None,
    )
    if primary_candidate is None:
        raise RuntimeError("A1 active nhưng thiếu candidate chính để gắn mốc")
    if distinct:
        candidates.append(reverse_candidate(primary_candidate, reverse))
    else:
        primary_candidate["reason"] = append_note(
            primary_candidate.get("reason"),
            "Mã tự đảo; không tạo lệnh đảo thứ hai.",
        )
    a1["candidates"] = candidates

    method = find_a1_method(doc)
    if method is not None:
        old_numbers = method.get("numbers") or []
        old_primary = old_numbers[0] if old_numbers else {}
        method_numbers = [
            {
                "code": primary,
                "points": primary_points,
                "capital_vnd": primary_points * cost_per_point,
                "role": old_primary.get("role") or "Mã A1 chính",
            }
        ]
        if distinct:
            method_numbers.append(
                {
                    "code": reverse,
                    "points": REVERSE_POINTS,
                    "capital_vnd": REVERSE_POINTS * cost_per_point,
                    "role": "Số đảo A1 chính thức · 50 điểm",
                }
            )
        method["numbers"] = method_numbers
        method["code_count"] = len(method_numbers)
        method["capital_vnd"] = total_capital
        method["primary_points_per_code"] = primary_points
        method["reverse_points_per_code"] = REVERSE_POINTS
        method["points_by_code"] = points_by_code
        method["reverse_skip_when_same"] = True

    top = doc.setdefault("top_signals", {})
    methods = top.get("methods") or []
    all_numbers = [n for m in methods for n in (m.get("numbers") or [])]
    all_points = sum(int(n.get("points") or 0) for n in all_numbers)
    all_capital = sum(int(m.get("capital_vnd") or 0) for m in methods)
    top["total_methods"] = len(methods)
    top["total_numbers"] = f"{len(all_numbers)} mã"
    top["total_points"] = f"{all_points} điểm"
    top["total_capital_vnd"] = all_capital
    if distinct:
        top["subtitle"] = f"A1 · {primary} ×{primary_points} + đảo {reverse} ×50 điểm"
    else:
        top["subtitle"] = f"A1 · {primary} ×{primary_points} điểm · đảo trùng, không đánh lặp"
    top["note"] = append_note(
        top.get("note"),
        "Quy tắc cố định: đảo A1 50 điểm; mã tự đảo không được nhân đôi lệnh.",
    )

    portfolio = doc.setdefault("portfolio", {})
    portfolio["selection"] = "-".join(selection)
    portfolio["points"] = total_points
    portfolio["capital_vnd"] = total_capital
    portfolio["reason"] = append_note(portfolio.get("reason"), rule_note)
    if distinct:
        portfolio["title"] = f"A1 {primary} + ĐẢO {reverse} — {primary_points}+50 ĐIỂM"
    else:
        portfolio["title"] = f"A1 {primary} — {primary_points} ĐIỂM · KHÔNG ĐÁNH ĐẢO TRÙNG"

    pending = doc.get("pending_order")
    if isinstance(pending, dict) and str(pending.get("method_id", "")).upper().startswith("A1"):
        pending.update(
            {
                "primary_code": primary,
                "reverse_code": reverse,
                "selection": selection,
                "points_per_code": primary_points,
                "points_by_code": points_by_code,
                "total_points": total_points,
                "capital_vnd": total_capital,
                "pnl_included": False,
                "a1_reverse_policy": copy.deepcopy(a1["reverse_policy"]),
            }
        )
        pending["note"] = append_note(pending.get("note"), rule_note)

    order = doc.get("actual_order")
    if isinstance(order, dict) and (
        str(order.get("method_id", "")).upper().startswith("A1")
        or isinstance(order.get("a1_reverse_policy"), dict)
    ):
        order["a1_reverse_policy"] = copy.deepcopy(a1["reverse_policy"])
        lo = order.setdefault("lo", {})
        lo["numbers"] = selection
        lo["points_by_code"] = points_by_code
        lo["points_per_code"] = primary_points

    automation = doc.setdefault("automation", {})
    automation["a1_reverse_rule_version"] = RULE_VERSION
    automation["a1_reverse_rule_complete"] = True
    return doc != before


def correct_settled_a1(doc: dict[str, Any], ledger: dict[str, Any]) -> bool:
    """Sửa delta quyết toán nếu lệnh A1 dùng mức chính/đảo khác nhau."""
    before_doc = copy.deepcopy(doc)
    before_ledger = copy.deepcopy(ledger)
    order = doc.get("actual_order") or {}
    policy = order.get("a1_reverse_policy") or {}
    lo_order = order.get("lo") or {}
    points_by_code = lo_order.get("points_by_code") or {}
    settlement = doc.get("settlement") or {}
    if not policy or not points_by_code or not settlement:
        return False
    if settlement.get("date") != order.get("date"):
        return False
    result_codes = settlement.get("result_codes") or []
    if len(result_codes) != 27:
        return False

    points = {str(code2(k)): int(v) for k, v in points_by_code.items() if code2(k)}
    freq = Counter(str(code2(x)) for x in result_codes if code2(x))
    stake = doc.get("stake_rule") or {}
    cost = int(stake.get("lo_cost_per_point_vnd") or DEFAULT_COST_PER_POINT)
    pay = int(stake.get("lo_payout_per_hit_point_vnd") or DEFAULT_PAY_PER_HIT_POINT)
    hits = {code: freq.get(code, 0) for code in points}
    capital = sum(value * cost for value in points.values())
    payout = sum(hits[code] * value * pay for code, value in points.items())
    pnl = payout - capital
    old_pnl = int(settlement.get("lo_pnl_vnd") or 0)
    delta = pnl - old_pnl

    lo_order.update(
        {
            "numbers": list(points),
            "points_by_code": points,
            "hits": hits,
            "hits_total": sum(hits.values()),
            "capital_vnd": capital,
            "payout_vnd": payout,
            "pnl_vnd": pnl,
        }
    )
    xien_pnl = int(settlement.get("xien_pnl_vnd") or 0)
    xien_capital = int((order.get("xien2") or {}).get("capital_vnd") or 0)
    xien_payout = int((order.get("xien2") or {}).get("payout_vnd") or 0)
    order["total_capital_vnd"] = capital + xien_capital
    order["total_payout_vnd"] = payout + xien_payout
    order["total_pnl_vnd"] = pnl + xien_pnl
    settlement.update(
        {
            "lo_hits_total": sum(hits.values()),
            "lo_pnl_vnd": pnl,
            "total_pnl_vnd": pnl + xien_pnl,
        }
    )

    date_key = str(order.get("date") or settlement.get("date") or "")
    record = (ledger.get("settlements") or {}).get(date_key)
    if isinstance(record, dict):
        record_lo = record.setdefault("lo", {})
        record_lo.update(
            {
                "numbers": list(points),
                "points_by_code": points,
                "hits": hits,
                "hits_total": sum(hits.values()),
                "capital_vnd": capital,
                "payout_vnd": payout,
                "pnl_vnd": pnl,
            }
        )
        record["total_capital_vnd"] = capital + int((record.get("xien2") or {}).get("capital_vnd") or 0)
        record["total_payout_vnd"] = payout + int((record.get("xien2") or {}).get("payout_vnd") or 0)
        record["total_pnl_vnd"] = pnl + int((record.get("xien2") or {}).get("pnl_vnd") or 0)

    if delta:
        q = doc.setdefault("pnl_summary", {})
        for key in ("user_lo_pnl_vnd", "active_all_real_pnl_vnd", "grand_total_pnl_vnd"):
            if key in q:
                q[key] = int(q.get(key) or 0) + delta
        if q.get("yesterday_date") == date_key:
            q["yesterday_pnl_vnd"] = int(q.get("yesterday_pnl_vnd") or 0) + delta
        snapshot = doc.setdefault("ledger_snapshot", {})
        for key in ("USER_LO", "ALL_REAL", "GRAND_TOTAL"):
            if key in snapshot:
                snapshot[key] = int(snapshot.get(key) or 0) + delta
        portfolio = doc.get("portfolio") or {}
        if str(portfolio.get("pnl_status", "")).upper() == "SETTLED":
            portfolio["capital_vnd"] = order["total_capital_vnd"]
            portfolio["payout_vnd"] = order["total_payout_vnd"]
            portfolio["pnl_vnd"] = order["total_pnl_vnd"]

    return doc != before_doc or ledger != before_ledger


def plan_hash(plan: dict[str, Any]) -> str:
    payload = {
        "target_date": plan.get("target_date"),
        "locked_through": plan.get("locked_through") or (plan.get("data") or {}).get("locked_through"),
        "portfolio": plan.get("portfolio"),
        "groups": plan.get("groups"),
        "milestone_policy": plan.get("milestone_policy"),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate(doc: dict[str, Any]) -> None:
    stake = doc.get("stake_rule") or {}
    assert int(stake.get("a1_reverse_points_per_code") or 0) == REVERSE_POINTS
    assert stake.get("a1_reverse_skip_when_same") is True
    assert stake.get("a1_no_duplicate_same_code") is True
    a1 = find_group(doc, "A1")
    if not a1 or not is_a1_active(doc, a1):
        return
    policy = a1.get("reverse_policy") or {}
    primary = code2(policy.get("primary_code"))
    reverse = code2(policy.get("reverse_code"))
    assert primary and reverse
    selection = [code2(x) for x in a1.get("selected_numbers") or []]
    assert None not in selection
    assert len(selection) == len(set(selection)), "A1 selection chứa mã trùng"
    if primary == reverse:
        assert selection == [primary], "Mã tự đảo không được đánh hai lần"
        assert int(policy.get("applied_reverse_points") or 0) == 0
    else:
        assert selection == [primary, reverse]
        points = a1.get("points_by_code") or {}
        assert int(points.get(reverse) or 0) == REVERSE_POINTS
    pending = doc.get("pending_order") or {}
    if str(pending.get("method_id", "")).upper().startswith("A1"):
        pending_selection = [code2(x) for x in pending.get("selection") or []]
        assert len(pending_selection) == len(set(pending_selection))
        if primary == reverse:
            assert pending_selection == [primary]
        else:
            assert int((pending.get("points_by_code") or {}).get(reverse) or 0) == REVERSE_POINTS
    assert (doc.get("automation") or {}).get("a1_reverse_rule_complete") is True


def process(write: bool) -> bool:
    current = load_json(CURRENT, {})
    ledger = load_json(SETTLEMENT_LEDGER, {"settlements": {}})
    changed = ensure_a1_reverse(current)
    changed = correct_settled_a1(current, ledger) or changed
    validate(current)

    target_date = str(current.get("target_date") or "")
    plan_path = ROOT / "data" / "plans" / f"{target_date}.json" if target_date else None
    plan = load_json(plan_path, {}) if plan_path and plan_path.exists() else None
    if isinstance(plan, dict) and plan:
        changed_plan = ensure_a1_reverse(plan)
        validate(plan)
        new_hash = plan_hash(plan)
        if plan.get("plan_hash") != new_hash:
            plan["plan_hash"] = new_hash
            changed_plan = True
        current.setdefault("automation", {})["plan_hash"] = new_hash
        changed = changed or changed_plan
    else:
        new_hash = plan_hash(current)
        current.setdefault("automation", {})["plan_hash"] = new_hash

    review = load_json(REVIEW_LEDGER, {})
    entry = ((review.get("plans") or {}).get(target_date) if target_date else None)
    if isinstance(entry, dict) and entry.get("plan_hash") != new_hash:
        entry["plan_hash"] = new_hash
        entry["a1_reverse_rule_version"] = RULE_VERSION
        changed = True

    state = load_json(AUTOMATION_STATE, {})
    if state:
        if state.get("plan_hash") != new_hash or state.get("a1_reverse_rule_version") != RULE_VERSION:
            state["plan_hash"] = new_hash
            state["a1_reverse_rule_version"] = RULE_VERSION
            state["a1_reverse_rule_complete"] = True
            changed = True

    if write and changed:
        dump_json(CURRENT, current)
        if isinstance(plan, dict) and plan_path:
            dump_json(plan_path, plan)
        if review:
            dump_json(REVIEW_LEDGER, review)
        if state:
            dump_json(AUTOMATION_STATE, state)
        if ledger:
            dump_json(SETTLEMENT_LEDGER, ledger)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = process(write=not args.check)
    if args.check and changed:
        raise SystemExit("A1 reverse50 rule is not fully enforced")
    print("A1_REVERSE50_NO_DUPLICATE_OK" if not changed else "A1_REVERSE50_UPDATED")


if __name__ == "__main__":
    main()
