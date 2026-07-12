#!/usr/bin/env python3
"""Create automatic Xiên 2 recommendations from every funded daily code.

Canonical rule:
- Use only unique codes with positive real-money stake in the current next-draw plan.
- Fewer than 2 codes: Xiên 2 is not activated.
- 2 or more codes: generate every unordered 2-code combination.
- Recommend 100,000 VND per pair; one winning pair returns 1,600,000 VND gross.
- Recommendation is not booked as a real order or P/L until the user confirms execution.

The script is deterministic and idempotent. It patches data/current.json, the matching
current override and the dated next-draw plan when those files exist.
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
RULE_VERSION = "XIEN2_AUTO_FROM_FUNDED_CODES_V1"
POINTS_PER_PAIR = 100
CAPITAL_PER_PAIR_VND = 100_000
GROSS_RETURN_PER_WINNING_PAIR_VND = 1_600_000


def code2(value: Any) -> str | None:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    return text[-2:].zfill(2) if text else None


def codes_in(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            result.extend(codes_in(item))
        return result
    text = str(value or "")
    found = re.findall(r"(?<!\d)(\d{2})(?!\d)", text)
    if found:
        return [item.zfill(2) for item in found]
    one = code2(value)
    return [one] if one else []


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def positive_points_map(doc: dict[str, Any]) -> dict[str, int]:
    pending = doc.get("pending_order") or {}
    portfolio = doc.get("portfolio") or {}
    raw = pending.get("points_by_code") or portfolio.get("points_by_code") or {}
    result: dict[str, int] = {}
    for key, value in raw.items():
        code = code2(key)
        try:
            points = int(value)
        except (TypeError, ValueError):
            points = 0
        if code and points > 0:
            result[code] = max(result.get(code, 0), points)
    if result:
        return result

    for method in (doc.get("top_signals") or {}).get("methods") or []:
        if "XIEN" in str(method.get("id") or "").upper():
            continue
        for number in method.get("numbers") or []:
            code = code2(number.get("code"))
            try:
                points = int(number.get("points") or 0)
            except (TypeError, ValueError):
                points = 0
            if code and points > 0:
                result[code] = max(result.get(code, 0), points)
    return result


def funded_codes(doc: dict[str, Any]) -> list[str]:
    points = positive_points_map(doc)
    pending = doc.get("pending_order") or {}
    portfolio = doc.get("portfolio") or {}
    ordered = codes_in(pending.get("selection") or []) + codes_in(portfolio.get("selection") or "")
    ordered += list(points)
    return [code for code in dedupe(ordered) if points.get(code, 0) > 0]


def upsert_group(doc: dict[str, Any], group: dict[str, Any]) -> None:
    groups = list(doc.get("groups") or [])
    for index, current in enumerate(groups):
        if str(current.get("id") or "").upper() in {"XIEN", "XIEN2"}:
            groups[index] = group
            doc["groups"] = groups
            return
    groups.append(group)
    doc["groups"] = groups


def patch(doc: dict[str, Any]) -> dict[str, Any]:
    codes = funded_codes(doc)
    pairs = [f"{left}-{right}" for left, right in combinations(codes, 2)]
    active = len(pairs) > 0
    pair_count = len(pairs)
    capital = pair_count * CAPITAL_PER_PAIR_VND
    gross_if_one = GROSS_RETURN_PER_WINNING_PAIR_VND if active else 0
    status = (
        "KHUYẾN NGHỊ ĐÁNH · CHỜ XÁC NHẬN"
        if active
        else "KHÔNG KÍCH HOẠT · CẦN TỪ 02 SỐ ĐƯỢC CẤP VỐN"
    )
    reason = (
        f"Có {len(codes)} mã được cấp vốn ({', '.join(codes)}); tự động tạo toàn bộ {pair_count} tổ hợp Xiên 2."
        if active
        else f"Chỉ có {len(codes)} mã được cấp vốn; Xiên 2 cần tối thiểu 02 mã."
    )

    recommendation = {
        "rule_version": RULE_VERSION,
        "target_date": doc.get("target_date"),
        "status": status,
        "state": "RECOMMENDED_PENDING_CONFIRMATION" if active else "NOT_APPLICABLE_LT2_FUNDED_CODES",
        "base_numbers": codes,
        "pairs": pairs,
        "pair_count": pair_count,
        "pair_generation": "ALL_UNORDERED_2_COMBINATIONS",
        "points_per_pair": POINTS_PER_PAIR,
        "capital_per_pair_vnd": CAPITAL_PER_PAIR_VND,
        "gross_return_per_winning_pair_vnd": GROSS_RETURN_PER_WINNING_PAIR_VND,
        "capital_vnd": capital,
        "gross_return_if_one_pair_wins_vnd": gross_if_one,
        "confirmation_required": True,
        "pnl_included": False,
        "reason": reason,
    }
    doc["xien2_policy"] = {
        "status": "ACTIVE_RECOMMENDATION",
        "rule_version": RULE_VERSION,
        "source": "UNIQUE_POSITIVE_STAKE_CODES_IN_CURRENT_PLAN",
        "minimum_codes": 2,
        "pair_generation": "ALL_UNORDERED_2_COMBINATIONS",
        "formula": "n*(n-1)/2",
        "points_per_pair": POINTS_PER_PAIR,
        "capital_per_pair_vnd": CAPITAL_PER_PAIR_VND,
        "gross_return_per_winning_pair_vnd": GROSS_RETURN_PER_WINNING_PAIR_VND,
        "confirmation_required_before_booking": True,
    }
    doc["xien2_recommendation"] = recommendation

    stake = doc.setdefault("stake_rule", {})
    stake["xien2_points_per_pair"] = POINTS_PER_PAIR
    stake["xien2_capital_per_pair_vnd"] = CAPITAL_PER_PAIR_VND
    stake["xien2_gross_return_per_winning_pair_vnd"] = GROSS_RETURN_PER_WINNING_PAIR_VND

    method = {
        "id": "XIEN2_AUTO_PAIRS",
        "label": "Xiên 2 tự động",
        "method": "Ghép toàn bộ cặp từ các số được cấp vốn thật",
        "status": status,
        "visual_status": "PASS" if active else "EMPTY",
        "points_per_pair": POINTS_PER_PAIR,
        "capital_per_pair_vnd": CAPITAL_PER_PAIR_VND,
        "code_count": pair_count,
        "pair_count": pair_count,
        "capital_vnd": capital,
        "numbers": [
            {
                "code": pair,
                "points": 0,
                "caption": f"{CAPITAL_PER_PAIR_VND:,}đ/cặp".replace(",", "."),
                "capital_vnd": CAPITAL_PER_PAIR_VND,
                "role": f"Xiên 2 tự động từ {pair}; chờ xác nhận đánh",
                "visual_status": "PASS",
            }
            for pair in pairs
        ],
        "empty_slot": not active,
        "reason": reason,
        "confirmation_required": True,
    }
    top = doc.setdefault("top_signals", {})
    methods = [
        item for item in (top.get("methods") or [])
        if "XIEN" not in str(item.get("id") or "").upper()
    ]
    methods.append(method)
    top["methods"] = methods
    top["displayed_blocks"] = len(methods)
    top["xien2_pair_count"] = pair_count
    top["xien2_capital_vnd"] = capital

    group = {
        "id": "XIEN",
        "label": "Xiên 2 tự động",
        "status": "RECOMMENDED_PENDING_CONFIRMATION" if active else "A0_LT2_FUNDED_CODES",
        "role": "AUTO RECOMMENDATION · SEPARATE XIEN LEDGER",
        "method": "Toàn bộ tổ hợp 2 từ mã được cấp vốn",
        "layer": f"{pair_count} cặp × {CAPITAL_PER_PAIR_VND:,}đ".replace(",", "."),
        "selected_numbers": pairs,
        "selection": "|".join(pairs),
        "points": pair_count * POINTS_PER_PAIR,
        "points_per_pair": POINTS_PER_PAIR,
        "capital_per_pair_vnd": CAPITAL_PER_PAIR_VND,
        "capital_vnd": capital,
        "summary": status,
        "reason": reason,
        "confirmation_required": True,
        "candidates": [
            {
                "code": pair,
                "rank": index,
                "gate": True,
                "status": "KHUYẾN NGHỊ ĐÁNH",
                "capital_vnd": CAPITAL_PER_PAIR_VND,
                "reason": f"Cặp tự động từ hai mã đã được cấp vốn; chờ xác nhận trước quay.",
            }
            for index, pair in enumerate(pairs, start=1)
        ],
    }
    upsert_group(doc, group)

    pending = doc.get("pending_order")
    if isinstance(pending, dict):
        pending["xien2_recommendation"] = copy.deepcopy(recommendation)
        standard_capital = int(pending.get("capital_vnd") or 0)
        pending["standard_capital_vnd"] = standard_capital
        pending["xien2_recommended_capital_vnd"] = capital
        pending["total_recommended_capital_vnd"] = standard_capital + capital

    portfolio = doc.setdefault("portfolio", {})
    standard_capital = int(portfolio.get("capital_vnd") or 0)
    portfolio["standard_capital_vnd"] = standard_capital
    portfolio["xien2_recommended_capital_vnd"] = capital
    portfolio["total_recommended_capital_vnd"] = standard_capital + capital

    pnl = doc.setdefault("pnl_summary", {})
    standard_pending = int(pnl.get("today_pending_capital_vnd") or standard_capital)
    pnl["today_pending_standard_capital_vnd"] = standard_pending
    pnl["today_pending_xien2_capital_vnd"] = capital
    pnl["today_pending_total_recommended_capital_vnd"] = standard_pending + capital

    display = doc.setdefault("display_policy", {})
    display["show_xien2_current_recommendation"] = True

    automation = doc.setdefault("automation", {})
    automation["xien2_auto_pair_rule_version"] = RULE_VERSION
    automation["xien2_auto_pair_complete"] = True
    return doc


def write_if_changed(path: Path, doc: dict[str, Any]) -> bool:
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def target_paths(doc: dict[str, Any]) -> list[Path]:
    paths = [CURRENT]
    if OVERRIDE.exists():
        paths.append(OVERRIDE)
    target = str(doc.get("target_date") or "")[:10]
    if target:
        plan = DATA / "plans" / f"{target}.json"
        if plan.exists():
            paths.append(plan)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    changed: list[str] = []
    for path in target_paths(current):
        doc = json.loads(path.read_text(encoding="utf-8"))
        expected = patch(copy.deepcopy(doc))
        if args.check:
            if doc != expected:
                raise SystemExit(f"Xiên 2 auto recommendation is stale: {path}")
        elif write_if_changed(path, expected):
            changed.append(str(path.relative_to(ROOT)))
    print("XIEN2_AUTO_CHANGED=" + ",".join(changed))


if __name__ == "__main__":
    main()
