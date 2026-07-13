#!/usr/bin/env python3
"""Persist all explicitly confirmed real orders for the target date.

Supports multiple lô methods, per-code stakes and an optional Xiên 2 order in one
idempotent actual_order payload. Automatic system signals remain auditable; manual
confirmations are recorded without silently rewriting their source method.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
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
XIEN_CAPITAL_PER_PAIR = 100_000
XIEN_GROSS_RETURN_PER_WIN = 1_600_000
RULE_VERSION = "MANUAL_REAL_ORDERS_V3_LO_XIEN2"


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


def pair2(value: Any) -> str:
    parts = [p for p in re.split(r"[-–—/|,\s]+", str(value or "").strip()) if p]
    if len(parts) != 2:
        raise ValueError(f"Cặp Xiên 2 không hợp lệ: {value!r}")
    left, right = code2(parts[0]), code2(parts[1])
    if left == right:
        raise ValueError("Xiên 2 phải gồm hai mã khác nhau")
    return f"{left}-{right}"


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
    return {
        "order_id": str(raw.get("order_id") or f"ORDER_{index}"),
        "method_id": str(raw.get("method_id") or "USER_MANUAL"),
        "label": str(raw.get("label") or raw.get("method_id") or "Lệnh thủ công"),
        "selection": selection,
        "points_by_code": points_by_code,
        "capital_vnd": sum(points_by_code.values()) * COST_PER_POINT,
        "roles": copy.deepcopy(raw.get("roles") or {}),
        "system_signal": copy.deepcopy(raw.get("system_signal") or {}),
        "stake_override": copy.deepcopy(raw.get("stake_override") or {}),
        "reverse_policy": copy.deepcopy(raw.get("reverse_policy") or {}),
        "scenario": copy.deepcopy(raw.get("scenario") or {}),
        "note": str(raw.get("note") or ""),
    }


def normalise_xien(raw: dict[str, Any]) -> dict[str, Any]:
    pairs: list[str] = []
    for value in raw.get("pairs") or []:
        pair = pair2(value)
        if pair not in pairs:
            pairs.append(pair)
    points = int(raw.get("points_per_pair") or 0) if pairs else 0
    if pairs and points <= 0:
        raise RuntimeError("Xiên 2 có cặp nhưng thiếu mức điểm")
    capital_per_pair = int(raw.get("capital_per_pair_vnd") or XIEN_CAPITAL_PER_PAIR)
    gross_return = int(raw.get("gross_return_per_winning_pair_vnd") or XIEN_GROSS_RETURN_PER_WIN)
    return {
        "pairs": pairs,
        "points_per_pair": points,
        "capital_per_pair_vnd": capital_per_pair,
        "gross_return_per_winning_pair_vnd": gross_return,
        "winning_pairs": [],
        "wins": 0,
        "losses": 0,
        "capital_vnd": len(pairs) * capital_per_pair,
        "payout_vnd": 0,
        "pnl_vnd": 0,
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
    xien = normalise_xien(raw.get("xien2") or {})
    lo_capital = sum(points_by_code.values()) * COST_PER_POINT
    total_capital = lo_capital + int(xien["capital_vnd"])
    uniform = len(set(points_by_code.values())) == 1
    return {
        "schema_version": "MB_ACTUAL_ORDER_V3_LO_XIEN2",
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
            "capital_vnd": lo_capital,
            "payout_vnd": 0,
            "pnl_vnd": 0,
        },
        "xien2": xien,
        "total_capital_vnd": total_capital,
        "total_payout_vnd": 0,
        "total_pnl_vnd": 0,
        "note": str(raw.get("note") or "Các lệnh thật đã được người dùng xác nhận trước giờ quay."),
    }


def component_line(component: dict[str, Any]) -> str:
    return f"{component['label']}: " + ", ".join(f"{code}×{component['points_by_code'][code]}" for code in component["selection"])


def apply_method_group(doc: dict[str, Any], component: dict[str, Any], group_id: str, token: str, label: str) -> None:
    group = find_group(doc, group_id)
    if group is None:
        return
    selection, mapping = component["selection"], component["points_by_code"]
    group.update({
        "selected_numbers": selection,
        "points_by_code": mapping,
        "points": sum(mapping.values()),
        "capital_vnd": component["capital_vnd"],
        "status": "PASS_REAL_CONFIRMED",
        "summary": "Đã xác nhận lệnh thật: " + ", ".join(f"{c} ×{mapping[c]} điểm" for c in selection) + ".",
        "reason": component.get("note") or f"Người dùng xác nhận lệnh {label} thật trước quay.",
    })
    method = find_top_method(doc, token)
    if method is not None:
        method.update({
            "status": "REAL_CONFIRMED",
            "visual_status": "PASS",
            "points_per_code": next(iter(mapping.values())) if len(set(mapping.values())) == 1 else "Theo mã",
            "code_count": len(selection),
            "capital_vnd": component["capital_vnd"],
            "points_by_code": mapping,
            "numbers": [
                {
                    "code": code,
                    "points": mapping[code],
                    "capital_vnd": mapping[code] * COST_PER_POINT,
                    "role": f"{label} đã xác nhận đánh thật",
                    "visual_status": "PASS",
                    "highlight_primary": False,
                    "reference_win_rate": method.get("reference_win_rate"),
                }
                for code in selection
            ],
        })


def apply_a1(doc: dict[str, Any], component: dict[str, Any]) -> None:
    apply_method_group(doc, component, "A1", "A1", "A1")
    group = find_group(doc, "A1")
    if group is not None and component.get("reverse_policy"):
        group["reverse_policy"] = copy.deepcopy(component["reverse_policy"])
    method = find_top_method(doc, "A1")
    if method is not None and method.get("numbers"):
        method["numbers"][0]["highlight_primary"] = True


def apply_x2(doc: dict[str, Any], component: dict[str, Any]) -> None:
    apply_method_group(doc, component, "X2", "X2", "X2 Core Exact")


def apply_than_vo(doc: dict[str, Any], component: dict[str, Any], target_date: str) -> None:
    group = ensure_group_after(doc, "THAN_VO", "A1")
    selection, mapping, roles = component["selection"], component["points_by_code"], component.get("roles") or {}
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
        "reason": component.get("note") or "Pick do người dùng xác nhận; tách khỏi tín hiệu hệ thống.",
        "candidates": [
            {
                "code": code,
                "rank": index,
                "gate": True,
                "status": "REAL_CONFIRMED",
                "role": roles.get(code) or ("Mã chủ" if index == 1 else "Cover/đảo"),
                "reason": f"{mapping[code]} điểm · vốn {mapping[code] * COST_PER_POINT:,}đ".replace(",", "."),
                "earliest_eligible_date": target_date,
                "earliest_condition": "Người dùng đã xác nhận đánh thật trước quay.",
                "milestone_type": "USER_CONFIRMED_NOW",
            }
            for index, code in enumerate(selection, 1)
        ],
        "reverse_policy": copy.deepcopy(component.get("reverse_policy") or {}),
    })


def apply_xien(doc: dict[str, Any], xien: dict[str, Any], target_date: str) -> None:
    if not xien.get("pairs"):
        return
    group = ensure_group_after(doc, "XIEN", "X2")
    pairs = xien["pairs"]
    group.update({
        "label": "Xiên 2 thực chiến",
        "status": "REAL_PENDING_CONFIRMED",
        "role": "SỔ XIÊN RIÊNG · REAL",
        "method": "Xiên 2 do người dùng xác nhận",
        "layer": f"{len(pairs)} cặp ×{xien['points_per_pair']} điểm",
        "selected_numbers": pairs,
        "selection": "|".join(pairs),
        "points": len(pairs) * int(xien["points_per_pair"]),
        "points_per_pair": int(xien["points_per_pair"]),
        "capital_vnd": int(xien["capital_vnd"]),
        "summary": "Đã chốt: " + ", ".join(f"{pair} ×{xien['points_per_pair']}" for pair in pairs) + ".",
        "reason": xien.get("note") or "Người dùng xác nhận Xiên 2 trước quay.",
        "candidates": [
            {
                "code": pair,
                "rank": index,
                "gate": True,
                "status": "REAL_CONFIRMED",
                "reason": f"Vốn {xien['capital_per_pair_vnd']:,}đ · trúng nhận {xien['gross_return_per_winning_pair_vnd']:,}đ".replace(",", "."),
                "earliest_eligible_date": target_date,
                "earliest_condition": "Người dùng đã xác nhận đánh thật trước quay.",
                "milestone_type": "USER_CONFIRMED_NOW",
            }
            for index, pair in enumerate(pairs, 1)
        ],
    })


def apply(doc: dict[str, Any], order: dict[str, Any]) -> bool:
    before = copy.deepcopy(doc)
    doc["actual_order"] = copy.deepcopy(order)
    mapping, components, xien = order["lo"]["points_by_code"], order["components"], order["xien2"]
    lines = [component_line(c) for c in components]
    if xien.get("pairs"):
        lines.append("Xiên 2: " + ", ".join(f"{pair}×{xien['points_per_pair']}" for pair in xien["pairs"]))

    doc["pending_order"] = {
        "status": "REAL_CONFIRMED_PENDING_RESULT",
        "date": order["date"],
        "method_id": order["method_id"],
        "selection": order["selection"],
        "points_per_code": order["lo"]["points_per_code"],
        "points_mode": order["lo"]["points_mode"],
        "points_by_code": mapping,
        "total_points": sum(mapping.values()) + len(xien.get("pairs") or []) * int(xien.get("points_per_pair") or 0),
        "capital_vnd": order["total_capital_vnd"],
        "xien2": copy.deepcopy(xien),
        "pnl_included": False,
        "components": copy.deepcopy(components),
        "note": "Đã xác nhận lô và Xiên 2; chờ kết quả để quyết toán.",
    }
    portfolio = doc.setdefault("portfolio", {})
    portfolio.update({
        "decision": str(components[0].get("method_id") or "MANUAL_CONFIRMED"),
        "selection": " | ".join(["-".join(c["selection"]) for c in components] + list(xien.get("pairs") or [])),
        "title": "ĐÃ CHỐT: " + " · ".join(lines),
        "points": sum(mapping.values()) + len(xien.get("pairs") or []) * int(xien.get("points_per_pair") or 0),
        "points_by_code": mapping,
        "capital_vnd": order["total_capital_vnd"],
        "payout_vnd": 0,
        "pnl_vnd": 0,
        "tier": f"{len(components)} LỆNH LÔ + {len(xien.get('pairs') or [])} XIÊN · ĐÃ XÁC NHẬN",
        "pnl_status": "REAL_CONFIRMED_PENDING_RESULT",
        "reason": "Các lệnh được ghi riêng; tổng vốn chờ kết quả. Chưa cộng P/L trước khi khóa kỳ quay.",
    })

    for component in components:
        method_id = str(component.get("method_id", "")).upper()
        if method_id.startswith("A1"):
            apply_a1(doc, component)
        elif method_id.startswith("X2") or "X2" in method_id:
            apply_x2(doc, component)
        elif "THAN_VO" in method_id or "THAN VO" in str(component.get("label", "")).upper():
            apply_than_vo(doc, component, order["date"])
    apply_xien(doc, xien, order["date"])

    top = doc.setdefault("top_signals", {})
    top["total_points"] = f"{portfolio['points']} điểm"
    top["total_capital_vnd"] = order["total_capital_vnd"]
    top["note"] = "Đã chốt lệnh thật: " + " · ".join(lines) + f". Tổng vốn {order['total_capital_vnd']:,}đ; chưa cộng P/L.".replace(",", ".")

    summary = doc.setdefault("pnl_summary", {})
    summary["today_pending_capital_vnd"] = order["total_capital_vnd"]
    summary["today_pending_order"] = " · ".join(lines) + " · ĐÃ XÁC NHẬN"
    summary["today_included"] = False

    stake = doc.setdefault("stake_rule", {})
    stake.update({
        "actual_order_points_by_code": mapping,
        "actual_order_points_mode": order["lo"]["points_mode"],
        "xien2_points_per_pair": xien.get("points_per_pair", 0),
        "xien2_capital_per_pair_vnd": xien.get("capital_per_pair_vnd", XIEN_CAPITAL_PER_PAIR),
        "xien2_gross_return_per_winning_pair_vnd": xien.get("gross_return_per_winning_pair_vnd", XIEN_GROSS_RETURN_PER_WIN),
        "manual_order_rule_version": RULE_VERSION,
    })
    doc.setdefault("automation", {}).update({
        "actual_order_confirmed": True,
        "actual_order_date": order["date"],
        "actual_order_hash": digest(order),
        "actual_order_component_count": len(components),
        "actual_order_xien_pair_count": len(xien.get("pairs") or []),
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
            save(plan_path, plan)
            changed.append(plan_path)

    ledger = load(ORDER_LEDGER, {"schema_version": "MB_ACTUAL_ORDER_LEDGER_V3", "orders": {}})
    before = copy.deepcopy(ledger)
    ledger["schema_version"] = "MB_ACTUAL_ORDER_LEDGER_V3"
    ledger.setdefault("orders", {})[target] = {
        "path": f"data/manual-orders/{target}.json",
        "status": order["status"],
        "method_id": order["method_id"],
        "selection": order["selection"],
        "points_by_code": order["lo"]["points_by_code"],
        "xien2": order["xien2"],
        "components": order["components"],
        "capital_vnd": order["total_capital_vnd"],
        "confirmed_at": order.get("confirmed_at"),
        "order_hash": digest(order),
    }
    ledger["latest_date"] = target
    if ledger != before:
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
            "actual_order_component_count": len(order["components"]),
            "actual_order_xien_pair_count": len(order["xien2"].get("pairs") or []),
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
    assert (actual.get("xien2") or {}).get("pairs") == (order.get("xien2") or {}).get("pairs")
    assert int(actual.get("total_capital_vnd") or 0) == int(order.get("total_capital_vnd") or 0)
    assert actual.get("pnl_included") is False
    assert (doc.get("portfolio") or {}).get("pnl_status") == "REAL_CONFIRMED_PENDING_RESULT"
    assert (doc.get("automation") or {}).get("actual_order_confirmed") is True
    if order["xien2"].get("pairs"):
        group = find_group(doc, "XIEN")
        assert group and group.get("selected_numbers") == order["xien2"]["pairs"], group
        assert group.get("status") == "REAL_PENDING_CONFIRMED", group


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
    order = normalise_order(load(manual_path, {}), target)
    if args.check:
        validate(doc, order)
        print("MANUAL_ORDERS_V3_INVARIANT_OK", target, order["selection"], order["xien2"].get("pairs"))
        return
    changed = apply(doc, order)
    touched: list[Path] = []
    if changed:
        save(CURRENT, doc)
        touched.append(CURRENT)
    touched.extend(sync_related(doc, order))
    validate(doc, order)
    print("MANUAL_ORDERS_V3_APPLIED", target, order["selection"], order["xien2"].get("pairs"), [str(p.relative_to(ROOT)) for p in touched])


if __name__ == "__main__":
    main()
