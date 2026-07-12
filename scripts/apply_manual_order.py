#!/usr/bin/env python3
"""Apply an explicit, user-confirmed real order to the website payload.

Manual confirmations live in data/manual-orders/YYYY-MM-DD.json and are authoritative
for stake/selection on that date.  The automatic planner may continue to publish its
system stake, but this post-processor restores the confirmed real order after every
pipeline run and keeps settlement idempotent.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data" / "current.json"
MANUAL_DIR = ROOT / "data" / "manual-orders"
PLANS = ROOT / "data" / "plans"
REVIEW_LEDGER = ROOT / "data" / "review-ledger.json"
AUTOMATION_STATE = ROOT / "data" / "automation-state.json"
ORDER_LEDGER = ROOT / "data" / "actual-order-ledger.json"
COST_PER_POINT = 23_000
PAY_PER_HIT_POINT = 80_000
RULE_VERSION = "MANUAL_REAL_ORDER_V1"


def load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else copy.deepcopy(default)


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def code2(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        raise ValueError(f"Mã không hợp lệ: {value!r}")
    return digits[-2:].zfill(2)


def find_group(doc: dict[str, Any], group_id: str) -> dict[str, Any] | None:
    wanted = group_id.upper()
    return next((g for g in doc.get("groups", []) if str(g.get("id", "")).upper() == wanted), None)


def a1_method(doc: dict[str, Any]) -> dict[str, Any] | None:
    for method in (doc.get("top_signals") or {}).get("methods") or []:
        text = f"{method.get('id', '')} {method.get('label', '')}".upper()
        if "A1" in text:
            return method
    return None


def scenario(points: int, count: int) -> str:
    capital = points * count * COST_PER_POINT
    values = []
    for hits in range(0, count + 1):
        pnl = hits * points * PAY_PER_HIT_POINT - capital
        sign = "+" if pnl > 0 else "−" if pnl < 0 else ""
        values.append(f"{hits} nháy {sign}{abs(pnl):,}đ".replace(",", "."))
    return " · ".join(values)


def normalise_order(raw: dict[str, Any], target_date: str) -> dict[str, Any]:
    if str(raw.get("date")) != target_date:
        raise RuntimeError(f"Manual order date {raw.get('date')} != target {target_date}")
    status = str(raw.get("status", "")).upper()
    if "CONFIRMED" not in status:
        raise RuntimeError("Manual order chưa ở trạng thái CONFIRMED")
    selection = []
    for value in raw.get("selection") or []:
        code = code2(value)
        if code not in selection:
            selection.append(code)
    if not selection:
        raise RuntimeError("Manual order không có mã")
    mapping_raw = raw.get("points_by_code") or {}
    points_by_code: dict[str, int] = {}
    for code in selection:
        points = int(mapping_raw.get(code, raw.get("points_per_code", 0)) or 0)
        if points <= 0:
            raise RuntimeError(f"Điểm không hợp lệ cho {code}: {points}")
        points_by_code[code] = points
    if len(set(points_by_code.values())) != 1:
        raise RuntimeError("Settlement hiện yêu cầu cùng mức điểm cho các mã trong một lệnh lô")
    points_per_code = next(iter(points_by_code.values()))
    capital = sum(points_by_code.values()) * COST_PER_POINT
    return {
        "schema_version": "MB_ACTUAL_ORDER_V1",
        "rule_version": RULE_VERSION,
        "status": "REAL_PENDING_CONFIRMED",
        "date": target_date,
        "method_id": str(raw.get("method_id") or "A1_MANUAL"),
        "selection": selection,
        "confirmed_at": raw.get("confirmed_at"),
        "confirmation_source": raw.get("confirmation_source") or "USER_EXPLICIT_CHAT",
        "system_signal": copy.deepcopy(raw.get("system_signal") or {}),
        "stake_override": copy.deepcopy(raw.get("stake_override") or {}),
        "pnl_included": False,
        "lo": {
            "numbers": selection,
            "points_per_code": points_per_code,
            "points_by_code": points_by_code,
            "hits": {},
            "hits_total": 0,
            "capital_vnd": capital,
            "payout_vnd": 0,
            "pnl_vnd": 0,
        },
        "xien2": {
            "pairs": [],
            "points_per_pair": 0,
            "capital_vnd": 0,
            "payout_vnd": 0,
            "pnl_vnd": 0,
        },
        "total_capital_vnd": capital,
        "total_payout_vnd": 0,
        "total_pnl_vnd": 0,
        "note": str(raw.get("note") or "Người dùng đã xác nhận lệnh thật trước giờ quay."),
    }


def apply(doc: dict[str, Any], order: dict[str, Any]) -> bool:
    before = copy.deepcopy(doc)
    date = order["date"]
    selection = order["selection"]
    points_by_code = order["lo"]["points_by_code"]
    points = int(order["lo"]["points_per_code"])
    capital = int(order["total_capital_vnd"])
    method_id = str(order.get("method_id") or "A1_MANUAL")
    system_points = int((order.get("system_signal") or {}).get("points_per_code") or 0)

    doc["actual_order"] = copy.deepcopy(order)
    pending = doc.setdefault("pending_order", {})
    pending.update({
        "status": "REAL_CONFIRMED_PENDING_RESULT",
        "date": date,
        "method_id": method_id,
        "selection": selection,
        "points_per_code": points,
        "points_by_code": points_by_code,
        "total_points": sum(points_by_code.values()),
        "capital_vnd": capital,
        "pnl_included": False,
        "note": "Đã xác nhận đánh thật; chờ kết quả để quyết toán.",
    })

    portfolio = doc.setdefault("portfolio", {})
    portfolio.update({
        "selection": "-".join(selection),
        "title": f"A1 {'-'.join(selection)} — ĐÃ CHỐT {points} ĐIỂM/SỐ",
        "points": sum(points_by_code.values()),
        "capital_vnd": capital,
        "payout_vnd": 0,
        "pnl_vnd": 0,
        "tier": "A1 · ĐÃ XÁC NHẬN ĐÁNH THẬT",
        "pnl_status": "REAL_CONFIRMED_PENDING_RESULT",
        "reason": (
            f"Người dùng xác nhận lệnh thật {'-'.join(selection)} ×{points} điểm. "
            + (f"Mức hệ thống {system_points} điểm; đây là override thủ công. " if system_points and system_points != points else "")
            + "Chưa cộng P/L trước khi khóa kết quả."
        ),
    })

    a1 = find_group(doc, "A1")
    if a1 is not None:
        a1["selected_numbers"] = selection
        a1["points_by_code"] = points_by_code
        a1["points"] = sum(points_by_code.values())
        a1["capital_vnd"] = capital
        a1["status"] = "PASS_REAL_CONFIRMED"
        a1["summary"] = f"Đã xác nhận lệnh thật: {'-'.join(selection)} ×{points} điểm."
        a1["reason"] = portfolio["reason"]
        primary = selection[0]
        reverse = primary[::-1]
        a1["reverse_policy"] = {
            "version": "A1_REVERSE50_NO_DUPLICATE_V1",
            "primary_code": primary,
            "reverse_code": reverse,
            "configured_reverse_points": 50,
            "applied_reverse_points": 0 if reverse == primary else int(points_by_code.get(reverse, 0)),
            "reverse_is_distinct": reverse != primary,
            "duplicate_bet_forbidden": True,
            "status": "SKIPPED_SAME_CODE" if reverse == primary else "MANUAL_SELECTION_RECORDED",
        }

    method = a1_method(doc)
    if method is not None:
        old_numbers = method.get("numbers") or []
        old_by_code = {code2(n.get("code")): n for n in old_numbers if n.get("code") is not None}
        method["status"] = "REAL_CONFIRMED"
        method["visual_status"] = "PASS"
        method["points_per_code"] = points
        method["code_count"] = len(selection)
        method["capital_vnd"] = capital
        method["points_by_code"] = points_by_code
        method["numbers"] = [
            {
                "code": code,
                "points": points_by_code[code],
                "capital_vnd": points_by_code[code] * COST_PER_POINT,
                "role": "Mã A1 đã xác nhận đánh thật" + (" · tự đảo, không đánh lặp" if code == code[::-1] else ""),
                "visual_status": "PASS",
                "highlight_primary": index == 0,
                "reference_win_rate": old_by_code.get(code, {}).get("reference_win_rate", method.get("reference_win_rate")),
            }
            for index, code in enumerate(selection)
        ]

    top = doc.setdefault("top_signals", {})
    methods = top.get("methods") or []
    total_points = sum(int(n.get("points") or 0) for m in methods for n in (m.get("numbers") or []))
    total_capital = sum(int(m.get("capital_vnd") or 0) for m in methods)
    top["total_points"] = f"{total_points} điểm"
    top["total_capital_vnd"] = total_capital
    top["note"] = (
        f"A1 {'-'.join(selection)} đã chốt {points} điểm/số, vốn {capital:,}đ. ".replace(",", ".")
        + "X2/X3 tiếp tục hiển thị theo dõi độc lập; chưa cộng P/L trước kết quả."
    )

    summary = doc.setdefault("pnl_summary", {})
    summary["today_pending_capital_vnd"] = capital
    summary["today_pending_order"] = f"A1 {'-'.join(selection)} ×{points} điểm · ĐÃ XÁC NHẬN"
    summary["today_included"] = False

    stake = doc.setdefault("stake_rule", {})
    stake["actual_order_points_per_code"] = points
    stake["manual_stake_override_active"] = bool(system_points and system_points != points)
    stake["manual_order_rule_version"] = RULE_VERSION

    automation = doc.setdefault("automation", {})
    automation["actual_order_confirmed"] = True
    automation["actual_order_date"] = date
    automation["actual_order_hash"] = digest(order)
    automation["manual_order_rule_version"] = RULE_VERSION
    return doc != before


def sync_related(doc: dict[str, Any], order: dict[str, Any]) -> list[Path]:
    changed: list[Path] = []
    target = order["date"]
    plan_path = PLANS / f"{target}.json"
    if plan_path.exists():
        plan = load(plan_path, {})
        before = copy.deepcopy(plan)
        for key in ("actual_order", "pending_order", "portfolio", "top_signals", "stake_rule", "pnl_summary", "automation", "groups"):
            if key in doc:
                plan[key] = copy.deepcopy(doc[key])
        plan.setdefault("validation", {})["actual_order_confirmed"] = True
        plan["actual_order_hash"] = digest(order)
        if plan != before:
            save(plan_path, plan)
            changed.append(plan_path)

    ledger = load(ORDER_LEDGER, {"schema_version": "MB_ACTUAL_ORDER_LEDGER_V1", "orders": {}})
    before_ledger = copy.deepcopy(ledger)
    ledger.setdefault("orders", {})[target] = {
        "path": f"data/manual-orders/{target}.json",
        "status": order["status"],
        "method_id": order["method_id"],
        "selection": order["selection"],
        "points_by_code": order["lo"]["points_by_code"],
        "capital_vnd": order["total_capital_vnd"],
        "confirmed_at": order.get("confirmed_at"),
        "order_hash": digest(order),
    }
    ledger["latest_date"] = target
    if ledger != before_ledger:
        save(ORDER_LEDGER, ledger)
        changed.append(ORDER_LEDGER)

    if REVIEW_LEDGER.exists():
        review = load(REVIEW_LEDGER, {})
        before = copy.deepcopy(review)
        review.setdefault("plans", {}).setdefault(target, {})["actual_order"] = copy.deepcopy(ledger["orders"][target])
        if review != before:
            save(REVIEW_LEDGER, review)
            changed.append(REVIEW_LEDGER)

    if AUTOMATION_STATE.exists():
        state = load(AUTOMATION_STATE, {})
        before = copy.deepcopy(state)
        state.update({
            "actual_order_confirmed": True,
            "actual_order_date": target,
            "actual_order_hash": digest(order),
            "actual_order_capital_vnd": order["total_capital_vnd"],
        })
        if state != before:
            save(AUTOMATION_STATE, state)
            changed.append(AUTOMATION_STATE)
    return changed


def validate(doc: dict[str, Any], order: dict[str, Any]) -> None:
    actual = doc.get("actual_order") or {}
    assert actual.get("status") == "REAL_PENDING_CONFIRMED", actual
    assert actual.get("date") == order["date"]
    assert actual.get("selection") == order["selection"]
    assert (actual.get("lo") or {}).get("points_by_code") == (order.get("lo") or {}).get("points_by_code")
    assert int(actual.get("total_capital_vnd") or 0) == int(order.get("total_capital_vnd") or 0)
    assert actual.get("pnl_included") is False
    assert (doc.get("portfolio") or {}).get("pnl_status") == "REAL_CONFIRMED_PENDING_RESULT"
    assert (doc.get("automation") or {}).get("actual_order_confirmed") is True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    doc = load(CURRENT, {})
    if not doc:
        raise RuntimeError("Thiếu data/current.json")
    target = str(doc.get("target_date") or "")
    manual_path = MANUAL_DIR / f"{target}.json"
    if not manual_path.exists():
        print("NO_MANUAL_ORDER_FOR_TARGET", target)
        return
    raw = load(manual_path, {})
    order = normalise_order(raw, target)
    if args.check:
        validate(doc, order)
        print("MANUAL_ORDER_INVARIANT_OK", target, order["selection"], order["lo"]["points_per_code"])
        return
    changed = apply(doc, order)
    touched: list[Path] = []
    if changed:
        save(CURRENT, doc)
        touched.append(CURRENT)
    touched.extend(sync_related(doc, order))
    validate(doc, order)
    print("MANUAL_ORDER_APPLIED", target, order["selection"], order["lo"]["points_per_code"], [str(p.relative_to(ROOT)) for p in touched])


if __name__ == "__main__":
    main()
