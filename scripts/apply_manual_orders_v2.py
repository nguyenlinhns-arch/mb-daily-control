#!/usr/bin/env python3
"""Persist all explicitly confirmed real orders for the target date.

Supports multiple methods and per-code stakes in one idempotent actual_order payload.
The automatic system signal remains auditable; manual picks are recorded as separate
components and never silently rewritten as A1.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data/current.json"
MANUAL_DIR = ROOT / "data/manual-orders"
PLANS = ROOT / "data/plans"
REVIEW_LEDGER = ROOT / "data/review-ledger.json"
AUTOMATION_STATE = ROOT / "data/automation-state.json"
ORDER_LEDGER = ROOT / "data/actual-order-ledger.json"
COST_PER_POINT = 23_000
RULE_VERSION = "MANUAL_REAL_ORDERS_V2_PER_CODE"


def load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else copy.deepcopy(default)


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def code2(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        raise ValueError(f"Mã không hợp lệ: {value!r}")
    return digits[-2:].zfill(2)


def find_group(doc: dict[str, Any], group_id: str) -> dict[str, Any] | None:
    wanted = group_id.upper()
    return next((g for g in doc.get("groups", []) if str(g.get("id", "")).upper() == wanted), None)


def ensure_group_after(doc: dict[str, Any], group_id: str, after_id: str) -> dict[str, Any]:
    found = find_group(doc, group_id)
    if found is not None:
        return found
    group = {"id": group_id}
    groups = doc.setdefault("groups", [])
    index = next((i + 1 for i, g in enumerate(groups) if str(g.get("id", "")).upper() == after_id.upper()), len(groups))
    groups.insert(index, group)
    return group


def find_top_method(doc: dict[str, Any], token: str) -> dict[str, Any] | None:
    wanted = token.upper()
    for method in (doc.get("top_signals") or {}).get("methods") or []:
        text = f"{method.get('id', '')} {method.get('label', '')}".upper()
        if wanted in text:
            return method
    return None


def normalise_component(raw: dict[str, Any], index: int) -> dict[str, Any]:
    selection: list[str] = []
    for value in raw.get("selection") or []:
        code = code2(value)
        if code not in selection:
            selection.append(code)
    if not selection:
        raise RuntimeError(f"Thành phần #{index} không có mã")
    mapping_raw = raw.get("points_by_code") or {}
    default_points = int(raw.get("points_per_code") or 0)
    points_by_code: dict[str, int] = {}
    for code in selection:
        points = int(mapping_raw.get(code, default_points) or 0)
        if points <= 0:
            raise RuntimeError(f"Điểm không hợp lệ cho {code}: {points}")
        points_by_code[code] = points
    capital = sum(points_by_code.values()) * COST_PER_POINT
    return {
        "order_id": str(raw.get("order_id") or f"ORDER_{index}"),
        "method_id": str(raw.get("method_id") or "USER_MANUAL"),
        "label": str(raw.get("label") or raw.get("method_id") or "Lệnh thủ công"),
        "selection": selection,
        "points_by_code": points_by_code,
        "capital_vnd": capital,
        "roles": copy.deepcopy(raw.get("roles") or {}),
        "system_signal": copy.deepcopy(raw.get("system_signal") or {}),
        "stake_override": copy.deepcopy(raw.get("stake_override") or {}),
        "reverse_policy": copy.deepcopy(raw.get("reverse_policy") or {}),
        "scenario": copy.deepcopy(raw.get("scenario") or {}),
        "note": str(raw.get("note") or ""),
    }


def normalise_order(raw: dict[str, Any], target_date: str) -> dict[str, Any]:
    if str(raw.get("date")) != target_date:
        raise RuntimeError(f"Manual order date {raw.get('date')} != target {target_date}")
    if "CONFIRMED" not in str(raw.get("status", "")).upper():
        raise RuntimeError("Manual order chưa ở trạng thái CONFIRMED")
    source_components = raw.get("orders") or [raw]
    components = [normalise_component(item, i) for i, item in enumerate(source_components, 1)]
    selection: list[str] = []
    points_by_code: dict[str, int] = {}
    for component in components:
        for code in component["selection"]:
            if code in points_by_code:
                raise RuntimeError(f"Mã {code} bị cấp vốn trùng giữa nhiều phương pháp")
            selection.append(code)
            points_by_code[code] = int(component["points_by_code"][code])
    capital = sum(points_by_code.values()) * COST_PER_POINT
    uniform = len(set(points_by_code.values())) == 1
    return {
        "schema_version": "MB_ACTUAL_ORDER_V2_MULTI_METHOD",
        "rule_version": RULE_VERSION,
        "status": "REAL_PENDING_CONFIRMED",
        "date": target_date,
        "method_id": "MULTI_MANUAL" if len(components) > 1 else components[0]["method_id"],
        "selection": selection,
        "components": components,
        "confirmed_at": raw.get("confirmed_at"),
        "confirmation_source": raw.get("confirmation_source") or "USER_EXPLICIT_CHAT",
        "pnl_included": False,
        "lo": {
            "numbers": selection,
            "points_per_code": next(iter(points_by_code.values())) if uniform else 0,
            "points_mode": "UNIFORM" if uniform else "PER_CODE",
            "points_by_code": points_by_code,
            "hits": {},
            "hits_total": 0,
            "capital_vnd": capital,
            "payout_vnd": 0,
            "pnl_vnd": 0,
        },
        "xien2": {"pairs": [], "points_per_pair": 0, "capital_vnd": 0, "payout_vnd": 0, "pnl_vnd": 0},
        "total_capital_vnd": capital,
        "total_payout_vnd": 0,
        "total_pnl_vnd": 0,
        "note": str(raw.get("note") or "Các lệnh thật đã được người dùng xác nhận trước giờ quay."),
    }


def component_line(component: dict[str, Any]) -> str:
    parts = [f"{code}×{component['points_by_code'][code]}" for code in component["selection"]]
    return f"{component['label']}: " + ", ".join(parts)


def apply_a1(doc: dict[str, Any], component: dict[str, Any]) -> None:
    a1 = find_group(doc, "A1")
    if a1 is None:
        return
    selection = component["selection"]
    mapping = component["points_by_code"]
    capital = component["capital_vnd"]
    a1.update({
        "selected_numbers": selection,
        "points_by_code": mapping,
        "points": sum(mapping.values()),
        "capital_vnd": capital,
        "status": "PASS_REAL_CONFIRMED",
        "summary": "Đã xác nhận lệnh thật: " + ", ".join(f"{c} ×{mapping[c]} điểm" for c in selection) + ".",
        "reason": component.get("note") or "Người dùng xác nhận lệnh A1 thật trước quay.",
    })
    if component.get("reverse_policy"):
        a1["reverse_policy"] = copy.deepcopy(component["reverse_policy"])
    method = find_top_method(doc, "A1")
    if method is not None:
        method.update({
            "status": "REAL_CONFIRMED",
            "visual_status": "PASS",
            "points_per_code": next(iter(mapping.values())) if len(set(mapping.values())) == 1 else "Theo mã",
            "code_count": len(selection),
            "capital_vnd": capital,
            "points_by_code": mapping,
            "numbers": [
                {
                    "code": code,
                    "points": mapping[code],
                    "capital_vnd": mapping[code] * COST_PER_POINT,
                    "role": "Mã A1 đã xác nhận đánh thật" + (" · tự đảo, không đánh lặp" if code == code[::-1] else ""),
                    "visual_status": "PASS",
                    "highlight_primary": index == 0,
                    "reference_win_rate": method.get("reference_win_rate"),
                }
                for index, code in enumerate(selection)
            ],
        })


def apply_than_vo(doc: dict[str, Any], component: dict[str, Any]) -> None:
    group = ensure_group_after(doc, "THAN_VO", "A1")
    selection = component["selection"]
    mapping = component["points_by_code"]
    roles = component.get("roles") or {}
    group.update({
        "label": "Than Vo Pick",
        "status": "REAL_CONFIRMED",
        "role": "USER PICK · REAL",
        "method": "Than Vo Pick · mã chủ và cover/đảo",
        "layer": "Lệnh thủ công đã xác nhận",
        "selected_numbers": selection,
        "points_by_code": mapping,
        "points": sum(mapping.values()),
        "capital_vnd": component["capital_vnd"],
        "summary": "Đã chốt: " + ", ".join(f"{c} ×{mapping[c]} điểm" for c in selection) + ".",
        "reason": component.get("note") or "Pick do người dùng xác nhận; tách khỏi tín hiệu hệ thống A1/X2/X3.",
        "candidates": [
            {
                "code": code,
                "rank": index,
                "gate": True,
                "status": "REAL_CONFIRMED",
                "role": roles.get(code) or ("Mã chủ" if index == 1 else "Cover/đảo"),
                "reason": f"{roles.get(code) or ('Mã chủ' if index == 1 else 'Cover/đảo')} · {mapping[code]} điểm · vốn {mapping[code] * COST_PER_POINT:,}đ".replace(",", "."),
                "earliest_eligible_date": component.get("date") or doc.get("target_date"),
                "earliest_condition": "Người dùng đã xác nhận đánh thật trước quay.",
                "milestone_type": "USER_CONFIRMED_NOW",
            }
            for index, code in enumerate(selection, 1)
        ],
        "reverse_policy": copy.deepcopy(component.get("reverse_policy") or {}),
    })


def apply(doc: dict[str, Any], order: dict[str, Any]) -> bool:
    before = copy.deepcopy(doc)
    doc["actual_order"] = copy.deepcopy(order)
    selection = order["selection"]
    mapping = order["lo"]["points_by_code"]
    capital = order["total_capital_vnd"]
    components = order["components"]
    lines = [component_line(c) for c in components]

    doc["pending_order"] = {
        "status": "REAL_CONFIRMED_PENDING_RESULT",
        "date": order["date"],
        "method_id": order["method_id"],
        "selection": selection,
        "points_per_code": order["lo"]["points_per_code"],
        "points_mode": order["lo"]["points_mode"],
        "points_by_code": mapping,
        "total_points": sum(mapping.values()),
        "capital_vnd": capital,
        "pnl_included": False,
        "components": copy.deepcopy(components),
        "note": "Đã xác nhận các lệnh thật; chờ kết quả để quyết toán.",
    }
    portfolio = doc.setdefault("portfolio", {})
    portfolio.update({
        "selection": " | ".join("-".join(c["selection"]) for c in components),
        "title": "ĐÃ CHỐT: " + " · ".join(lines),
        "points": sum(mapping.values()),
        "capital_vnd": capital,
        "payout_vnd": 0,
        "pnl_vnd": 0,
        "tier": f"{len(components)} LỆNH THẬT · ĐÃ XÁC NHẬN",
        "pnl_status": "REAL_CONFIRMED_PENDING_RESULT",
        "reason": "Hai phương pháp được ghi riêng; tổng vốn chờ kết quả. Chưa cộng P/L trước khi khóa kỳ quay.",
    })

    for component in components:
        method_id = str(component.get("method_id", "")).upper()
        if method_id.startswith("A1"):
            apply_a1(doc, component)
        elif "THAN_VO" in method_id or "THAN VO" in str(component.get("label", "")).upper():
            component["date"] = order["date"]
            apply_than_vo(doc, component)

    top = doc.setdefault("top_signals", {})
    top["total_points"] = f"{sum(mapping.values())} điểm"
    top["total_capital_vnd"] = capital
    top["note"] = "Đã chốt lệnh thật: " + " · ".join(lines) + f". Tổng vốn {capital:,}đ; chưa cộng P/L.".replace(",", ".")

    summary = doc.setdefault("pnl_summary", {})
    summary["today_pending_capital_vnd"] = capital
    summary["today_pending_order"] = " · ".join(lines) + " · ĐÃ XÁC NHẬN"
    summary["today_included"] = False

    stake = doc.setdefault("stake_rule", {})
    stake["actual_order_points_by_code"] = mapping
    stake["actual_order_points_mode"] = order["lo"]["points_mode"]
    stake["manual_order_rule_version"] = RULE_VERSION

    automation = doc.setdefault("automation", {})
    automation.update({
        "actual_order_confirmed": True,
        "actual_order_date": order["date"],
        "actual_order_hash": digest(order),
        "actual_order_component_count": len(components),
        "manual_order_rule_version": RULE_VERSION,
    })
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
            save(plan_path, plan); changed.append(plan_path)

    ledger = load(ORDER_LEDGER, {"schema_version": "MB_ACTUAL_ORDER_LEDGER_V2", "orders": {}})
    before = copy.deepcopy(ledger)
    ledger["schema_version"] = "MB_ACTUAL_ORDER_LEDGER_V2"
    ledger.setdefault("orders", {})[target] = {
        "path": f"data/manual-orders/{target}.json",
        "status": order["status"],
        "method_id": order["method_id"],
        "selection": order["selection"],
        "points_by_code": order["lo"]["points_by_code"],
        "components": order["components"],
        "capital_vnd": order["total_capital_vnd"],
        "confirmed_at": order.get("confirmed_at"),
        "order_hash": digest(order),
    }
    ledger["latest_date"] = target
    if ledger != before:
        save(ORDER_LEDGER, ledger); changed.append(ORDER_LEDGER)

    if REVIEW_LEDGER.exists():
        review = load(REVIEW_LEDGER, {})
        before = copy.deepcopy(review)
        review.setdefault("plans", {}).setdefault(target, {})["actual_order"] = copy.deepcopy(ledger["orders"][target])
        if review != before:
            save(REVIEW_LEDGER, review); changed.append(REVIEW_LEDGER)

    if AUTOMATION_STATE.exists():
        state = load(AUTOMATION_STATE, {})
        before = copy.deepcopy(state)
        state.update({
            "actual_order_confirmed": True,
            "actual_order_date": target,
            "actual_order_hash": digest(order),
            "actual_order_capital_vnd": order["total_capital_vnd"],
            "actual_order_component_count": len(order["components"]),
        })
        if state != before:
            save(AUTOMATION_STATE, state); changed.append(AUTOMATION_STATE)
    return changed


def validate(doc: dict[str, Any], order: dict[str, Any]) -> None:
    actual = doc.get("actual_order") or {}
    assert actual.get("status") == "REAL_PENDING_CONFIRMED", actual
    assert actual.get("date") == order["date"]
    assert actual.get("selection") == order["selection"]
    assert (actual.get("lo") or {}).get("points_by_code") == (order.get("lo") or {}).get("points_by_code")
    assert int(actual.get("total_capital_vnd") or 0) == int(order.get("total_capital_vnd") or 0)
    assert len(actual.get("components") or []) == len(order.get("components") or [])
    assert actual.get("pnl_included") is False
    assert (doc.get("portfolio") or {}).get("pnl_status") == "REAL_CONFIRMED_PENDING_RESULT"
    assert (doc.get("automation") or {}).get("actual_order_confirmed") is True
    than_vo = next((c for c in order["components"] if "THAN_VO" in str(c.get("method_id", "")).upper()), None)
    if than_vo:
        group = find_group(doc, "THAN_VO")
        assert group and group.get("selected_numbers") == than_vo["selection"], group
        assert group.get("status") == "REAL_CONFIRMED", group


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
        print("NO_MANUAL_ORDER_FOR_TARGET", target); return
    order = normalise_order(load(manual_path, {}), target)
    if args.check:
        validate(doc, order)
        print("MANUAL_ORDERS_V2_INVARIANT_OK", target, order["selection"], order["lo"]["points_by_code"]); return
    changed = apply(doc, order)
    touched: list[Path] = []
    if changed:
        save(CURRENT, doc); touched.append(CURRENT)
    touched.extend(sync_related(doc, order))
    validate(doc, order)
    print("MANUAL_ORDERS_V2_APPLIED", target, order["selection"], order["lo"]["points_by_code"], [str(p.relative_to(ROOT)) for p in touched])


if __name__ == "__main__":
    main()
