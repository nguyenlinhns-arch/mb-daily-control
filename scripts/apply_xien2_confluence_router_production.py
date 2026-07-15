#!/usr/bin/env python3
"""Apply XIEN2_CONFLUENCE_ROUTER_V1 to the current next-draw plan.

Production rules:
- A1 + X2 only: keep cross-method A1-X2 pairs only.
- A1 + X2 + X3: exclude A1 legs; keep all unordered pairs in X2 union X3.
- Every other active-method combination: keep canonical all-pairs output.
- The existing two-recent-lo-loss brake remains dominant. When active, routed
  pairs are displayed as Shadow with zero real capital.

The script is deterministic and idempotent. It patches current.json, the
current override, and the matching dated plan when those files exist.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURRENT = DATA / "current.json"
OVERRIDE = DATA / "current-override.json"
ROUTER_VERSION = "XIEN2_CONFLUENCE_ROUTER_V1"
LOSS_BRAKE_VERSION = "XIEN2_TWO_LO_LOSS_BRAKE_V1"
CAPITAL_PER_PAIR_VND = 100_000
GROSS_RETURN_PER_WINNING_PAIR_VND = 1_600_000
POINTS_PER_PAIR = 100


def code2(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[-2:].zfill(2) if digits else None


def classify(value: Any) -> str | None:
    text = str(value or "").upper()
    if "XIEN" in text or "XIÊN" in text or "DE_" in text or "ĐỀ" in text:
        return None
    if "ROLL7" in text or "5-OF-7" in text:
        return "ROLL7"
    if "A1" in text:
        return "A1"
    if "X2" in text:
        return "X2"
    if "X3" in text:
        return "X3"
    return None


def add_points(target: dict[str, int], raw_code: Any, raw_points: Any) -> None:
    code = code2(raw_code)
    try:
        points = int(raw_points or 0)
    except (TypeError, ValueError):
        points = 0
    if code and points > 0:
        target[code] = max(target.get(code, 0), points)


def method_maps(doc: dict[str, Any]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {key: {} for key in ("A1", "X2", "X3", "ROLL7")}

    pending = doc.get("pending_order") or {}
    for component in pending.get("components") or []:
        key = classify(component.get("method_id"))
        if not key:
            continue
        for code, points in (component.get("points_by_code") or {}).items():
            add_points(result[key], code, points)

    for method in (doc.get("top_signals") or {}).get("methods") or []:
        key = classify(f"{method.get('id', '')} {method.get('label', '')}")
        if not key:
            continue
        for code, points in (method.get("points_by_code") or {}).items():
            add_points(result[key], code, points)
        for number in method.get("numbers") or []:
            add_points(result[key], number.get("code"), number.get("points"))

    for group in doc.get("groups") or []:
        key = classify(group.get("id"))
        if not key:
            continue
        for code, points in (group.get("points_by_code") or {}).items():
            add_points(result[key], code, points)

    return result


def ordered_codes(maps: dict[str, dict[str, int]], keys: tuple[str, ...]) -> list[str]:
    result: list[str] = []
    for key in keys:
        for code in maps.get(key, {}):
            if code not in result:
                result.append(code)
    return result


def pair_list(codes: list[str]) -> list[str]:
    return [f"{left}-{right}" for left, right in combinations(codes, 2)]


def cross_pairs(left_codes: list[str], right_codes: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[frozenset[str]] = set()
    for left in left_codes:
        for right in right_codes:
            if left == right:
                continue
            marker = frozenset((left, right))
            if marker in seen:
                continue
            seen.add(marker)
            result.append(f"{left}-{right}")
    return result


def upsert_group(doc: dict[str, Any], group: dict[str, Any]) -> None:
    groups = list(doc.get("groups") or [])
    for index, current in enumerate(groups):
        if str(current.get("id") or "").upper() in {"XIEN", "XIEN2"}:
            groups[index] = group
            doc["groups"] = groups
            return
    groups.append(group)
    doc["groups"] = groups


def routed_pairs(doc: dict[str, Any]) -> tuple[dict[str, dict[str, int]], list[str], list[str], str, list[str]]:
    maps = method_maps(doc)
    all_codes = ordered_codes(maps, ("A1", "X2", "X3", "ROLL7"))
    baseline = pair_list(all_codes)
    active_standard = [key for key in ("A1", "X2", "X3") if maps[key]]
    active_set = set(active_standard)

    if active_set == {"A1", "X2"}:
        pairs = cross_pairs(list(maps["A1"]), list(maps["X2"]))
        rule = "A1_X2_CROSS_ONLY"
    elif active_set == {"A1", "X2", "X3"}:
        allowed = ordered_codes(maps, ("X2", "X3"))
        pairs = pair_list(allowed)
        rule = "TRIPLE_PASS_EXCLUDE_A1_LEGS"
    else:
        pairs = list(baseline)
        rule = "KEEP_CANONICAL_ALL_PAIRS"

    return maps, baseline, pairs, rule, active_standard


def patch(doc: dict[str, Any]) -> dict[str, Any]:
    # Production V2 can explicitly disable every Xiên side bet.  In that
    # regime the canonical lô basket must remain untouched and the legacy
    # Confluence Router must not silently re-enable a separate ledger.
    if (doc.get("funding_policy") or {}).get("xien2_enabled") is False:
        automation = doc.setdefault("automation", {})
        automation["xien2_confluence_router_complete"] = True
        automation["xien2_confluence_router_version"] = "DISABLED_BY_METHOD"
        automation["xien2_router_rule_applied"] = "DISABLED_BY_METHOD"
        display = doc.setdefault("display_policy", {})
        display["show_xien2_current_recommendation"] = False
        display["show_xien2_loss_brake_status"] = False
        display["show_xien2_router_status"] = False
        return doc

    maps, baseline_pairs, pairs, router_rule, active_standard = routed_pairs(doc)
    existing = copy.deepcopy(doc.get("xien2_recommendation") or {})
    brake_active = bool(existing.get("brake_active")) and bool(pairs)
    brake_basis = existing.get("brake_basis") or []
    has_pairs = bool(pairs)
    excluded_pairs = [pair for pair in baseline_pairs if pair not in pairs]
    paper_capital = len(pairs) * CAPITAL_PER_PAIR_VND
    real_capital = 0 if brake_active else paper_capital

    if not has_pairs:
        status = "KHÔNG KÍCH HOẠT · CẦN TỪ 02 SỐ ĐƯỢC CẤP VỐN"
        state = "NOT_APPLICABLE_LT2_FUNDED_CODES"
        reason = "Sau Confluence Router không có đủ 02 chân hợp lệ để tạo Xiên 2."
    elif brake_active:
        status = "PHANH XIÊN · CONFLUENCE ROUTER · SHADOW 0Đ"
        state = "SHADOW_ONLY_TWO_LO_LOSS_BRAKE"
        reason = (
            f"Confluence Router áp dụng {router_rule}; giữ {len(pairs)} cặp ({', '.join(pairs)}). "
            f"Phanh hai ngày lô thua liên tiếp đang bật nên vốn Xiên thật bằng 0đ."
        )
    else:
        status = "KHUYẾN NGHỊ ĐÁNH · CONFLUENCE ROUTER · CHỜ XÁC NHẬN"
        state = "RECOMMENDED_PENDING_CONFIRMATION"
        reason = (
            f"Confluence Router áp dụng {router_rule}; khuyến nghị {len(pairs)} cặp "
            f"({', '.join(pairs)}) ở mức 100.000đ/cặp."
        )

    base_numbers = ordered_codes(maps, ("A1", "X2", "X3", "ROLL7"))
    recommendation = {
        **existing,
        "rule_version": ROUTER_VERSION,
        "loss_brake_rule_version": LOSS_BRAKE_VERSION,
        "target_date": doc.get("target_date"),
        "status": status,
        "state": state,
        "base_numbers": base_numbers,
        "pairs": pairs,
        "pair_count": len(pairs),
        "pair_generation": "CONFLUENCE_ROUTER",
        "router_rule": router_rule,
        "active_standard_methods": active_standard,
        "source_method_codes": {key: list(value) for key, value in maps.items() if value},
        "baseline_pairs": baseline_pairs,
        "baseline_pair_count": len(baseline_pairs),
        "excluded_pairs": excluded_pairs,
        "points_per_pair": POINTS_PER_PAIR,
        "reference_capital_per_pair_vnd": CAPITAL_PER_PAIR_VND,
        "capital_per_pair_vnd": 0 if brake_active else CAPITAL_PER_PAIR_VND,
        "gross_return_per_winning_pair_vnd": GROSS_RETURN_PER_WINNING_PAIR_VND,
        "paper_capital_vnd": paper_capital,
        "baseline_paper_capital_vnd": len(baseline_pairs) * CAPITAL_PER_PAIR_VND,
        "capital_saving_vnd": len(excluded_pairs) * CAPITAL_PER_PAIR_VND,
        "capital_vnd": real_capital,
        "gross_return_if_one_pair_wins_vnd": GROSS_RETURN_PER_WINNING_PAIR_VND if has_pairs and not brake_active else 0,
        "brake_active": brake_active,
        "brake_basis": brake_basis,
        "booking_allowed": has_pairs and not brake_active,
        "confirmation_required": has_pairs and not brake_active,
        "pnl_included": False,
        "reason": reason,
    }
    doc["xien2_recommendation"] = recommendation

    doc["xien2_policy"] = {
        "status": "ACTIVE_PRODUCTION_CONFLUENCE_ROUTER_WITH_TWO_LO_LOSS_BRAKE",
        "rule_version": ROUTER_VERSION,
        "loss_brake_rule_version": LOSS_BRAKE_VERSION,
        "source": "METHOD_SPECIFIC_POSITIVE_STAKE_CODES_IN_CURRENT_PLAN",
        "router_rules": {
            "A1_X2_ONLY": "CROSS_METHOD_PAIRS_ONLY",
            "A1_X2_X3": "EXCLUDE_A1_LEGS; PAIR_WITHIN_X2_UNION_X3",
            "OTHER": "KEEP_CANONICAL_ALL_PAIRS",
        },
        "points_per_pair": POINTS_PER_PAIR,
        "capital_per_pair_vnd": CAPITAL_PER_PAIR_VND,
        "gross_return_per_winning_pair_vnd": GROSS_RETURN_PER_WINNING_PAIR_VND,
        "loss_brake_trigger": "TWO_MOST_RECENT_LO_SIGNAL_DAYS_HAVE_NEGATIVE_LO_PNL",
        "loss_brake_effect": "SHOW_ROUTED_PAIRS_AS_SHADOW_ZERO_CAPITAL; NEVER_CHANGE_LO_ORDERS",
        "coverage_effect": "NONE",
        "confirmation_required_before_booking": True,
    }

    caption = "Shadow 0đ · chuẩn 100.000đ/cặp" if brake_active else "100.000đ/cặp"
    role_prefix = "Xiên Router Shadow do phanh hai ngày lô thua" if brake_active else "Xiên 2 Confluence Router · chờ xác nhận"
    method = {
        "id": "XIEN2_CONFLUENCE_ROUTER",
        "label": "Xiên 2 · Confluence Router",
        "method": f"{ROUTER_VERSION} · {router_rule}",
        "status": status,
        "visual_status": "EMPTY" if brake_active or not has_pairs else "PASS",
        "points_per_pair": POINTS_PER_PAIR,
        "reference_capital_per_pair_vnd": CAPITAL_PER_PAIR_VND,
        "capital_per_pair_vnd": 0 if brake_active else CAPITAL_PER_PAIR_VND,
        "code_count": len(pairs),
        "pair_count": len(pairs),
        "paper_capital_vnd": paper_capital,
        "baseline_pair_count": len(baseline_pairs),
        "capital_saving_vnd": len(excluded_pairs) * CAPITAL_PER_PAIR_VND,
        "capital_vnd": real_capital,
        "brake_active": brake_active,
        "numbers": [
            {
                "code": pair,
                "points": 0,
                "caption": caption,
                "capital_vnd": 0 if brake_active else CAPITAL_PER_PAIR_VND,
                "role": f"{role_prefix}: {pair}",
                "visual_status": "EMPTY" if brake_active else "PASS",
            }
            for pair in pairs
        ],
        "empty_slot": not has_pairs,
        "reason": reason,
        "confirmation_required": has_pairs and not brake_active,
        "booking_allowed": has_pairs and not brake_active,
    }

    top = doc.setdefault("top_signals", {})
    methods = [item for item in (top.get("methods") or []) if "XIEN" not in str(item.get("id") or "").upper()]
    methods.append(method)
    top["methods"] = methods
    top["displayed_blocks"] = len(methods)
    top["xien2_pair_count"] = len(pairs)
    top["xien2_paper_capital_vnd"] = paper_capital
    top["xien2_baseline_pair_count"] = len(baseline_pairs)
    top["xien2_capital_saving_vnd"] = len(excluded_pairs) * CAPITAL_PER_PAIR_VND
    top["xien2_capital_vnd"] = real_capital
    top["xien2_loss_brake_active"] = brake_active
    top["xien2_router_version"] = ROUTER_VERSION

    group = {
        "id": "XIEN",
        "label": "Xiên 2 · Confluence Router",
        "status": state,
        "role": "PRODUCTION ROUTER · SEPARATE XIEN LEDGER",
        "method": ROUTER_VERSION,
        "layer": f"{len(pairs)} cặp · vốn thật {real_capital:,}đ".replace(",", "."),
        "selected_numbers": pairs,
        "selection": "|".join(pairs),
        "points": 0,
        "points_per_pair": POINTS_PER_PAIR,
        "reference_capital_per_pair_vnd": CAPITAL_PER_PAIR_VND,
        "capital_per_pair_vnd": 0 if brake_active else CAPITAL_PER_PAIR_VND,
        "paper_capital_vnd": paper_capital,
        "capital_vnd": real_capital,
        "summary": status,
        "reason": reason,
        "router_rule": router_rule,
        "baseline_pairs": baseline_pairs,
        "excluded_pairs": excluded_pairs,
        "brake_active": brake_active,
        "confirmation_required": has_pairs and not brake_active,
        "booking_allowed": has_pairs and not brake_active,
        "candidates": [{"code": pair, "points": 0, "capital_vnd": 0 if brake_active else CAPITAL_PER_PAIR_VND} for pair in pairs],
    }
    upsert_group(doc, group)

    pending = doc.get("pending_order")
    if isinstance(pending, dict):
        pending["xien2_recommendation"] = copy.deepcopy(recommendation)
        pending["xien2_recommended_capital_vnd"] = real_capital
        pending["xien2_paper_capital_vnd"] = paper_capital
        pending["total_recommended_capital_vnd"] = int(pending.get("standard_capital_vnd") or pending.get("capital_vnd") or 0) + real_capital

    portfolio = doc.setdefault("portfolio", {})
    standard = int(portfolio.get("standard_capital_vnd") or portfolio.get("capital_vnd") or 0)
    portfolio["xien2_recommended_capital_vnd"] = real_capital
    portfolio["xien2_paper_capital_vnd"] = paper_capital
    portfolio["xien2_router_capital_saving_vnd"] = len(excluded_pairs) * CAPITAL_PER_PAIR_VND
    portfolio["total_recommended_capital_vnd"] = standard + real_capital

    pnl = doc.setdefault("pnl_summary", {})
    pnl["today_pending_xien2_capital_vnd"] = real_capital
    pnl["today_pending_xien2_paper_capital_vnd"] = paper_capital
    pnl["today_pending_total_recommended_capital_vnd"] = int(pnl.get("today_pending_standard_capital_vnd") or standard) + real_capital

    stake = doc.setdefault("stake_rule", {})
    stake["xien2_router_version"] = ROUTER_VERSION
    stake["xien2_confluence_router_active"] = True
    stake["xien2_two_lo_loss_brake"] = True

    automation = doc.setdefault("automation", {})
    automation["xien2_confluence_router_complete"] = True
    automation["xien2_confluence_router_version"] = ROUTER_VERSION
    automation["xien2_router_rule_applied"] = router_rule

    display = doc.setdefault("display_policy", {})
    display["show_xien2_current_recommendation"] = True
    display["show_xien2_loss_brake_status"] = True
    display["show_xien2_router_status"] = True
    return doc


def write_if_changed(path: Path, doc: dict[str, Any]) -> bool:
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def targets() -> list[Path]:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    result = [CURRENT]
    if OVERRIDE.exists():
        result.append(OVERRIDE)
    target = str(current.get("target_date") or "")[:10]
    plan = DATA / "plans" / f"{target}.json"
    if target and plan.exists():
        result.append(plan)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed: list[str] = []
    for path in targets():
        doc = json.loads(path.read_text(encoding="utf-8"))
        expected = patch(copy.deepcopy(doc))
        if args.check:
            if doc != expected:
                raise SystemExit(f"Xiên Confluence Router stale: {path}")
        elif write_if_changed(path, expected):
            changed.append(str(path.relative_to(ROOT)))
    print("XIEN2_CONFLUENCE_ROUTER_CHANGED=" + ",".join(changed))


if __name__ == "__main__":
    main()
