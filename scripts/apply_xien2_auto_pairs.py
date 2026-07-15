#!/usr/bin/env python3
"""Create automatic Xiên 2 recommendations from every funded daily code.

Canonical rule:
- Use only unique codes with positive real-money stake in the current next-draw plan.
- Fewer than 2 codes: Xiên 2 is not activated.
- 2 or more codes: generate every unordered 2-code combination.
- Recommend 100,000 VND per pair; one winning pair returns 1,600,000 VND gross.
- Recommendation is not booked as a real order or P/L until the user confirms execution.
- If the two most recent *lô signal days* both settled with negative lô P/L,
  keep every Xiên pair visible but move the whole Xiên block to Shadow 0 VND.
  A1/X2/X3/ROLL7 codes and stakes are never changed by this Xiên-only brake.

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
LEDGER = DATA / "settlement-ledger.json"
RULE_VERSION = "XIEN2_AUTO_FROM_FUNDED_CODES_V2_LOSS_BRAKE"
LOSS_BRAKE_VERSION = "XIEN2_TWO_LO_LOSS_BRAKE_V1"
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
    # MB ROLL30 30/30 Production has one canonical lô basket only.
    # When the method explicitly disables Xiên 2, never derive side bets from
    # otherwise funded lô codes.
    if (doc.get("funding_policy") or {}).get("xien2_enabled") is False:
        return {}
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


def recent_lo_signal_settlements(limit: int = 2) -> list[dict[str, Any]]:
    if not LEDGER.exists():
        return []
    try:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    result: list[dict[str, Any]] = []
    for day, record in sorted((ledger.get("settlements") or {}).items(), reverse=True):
        lo = record.get("lo") or {}
        numbers = lo.get("numbers") or []
        capital = int(lo.get("capital_vnd") or 0)
        if not numbers and capital <= 0:
            continue
        result.append({
            "date": day,
            "pnl_vnd": int(lo.get("pnl_vnd") or 0),
            "capital_vnd": capital,
            "numbers": [str(code) for code in numbers],
        })
        if len(result) >= limit:
            break
    return result


def two_lo_loss_brake() -> tuple[bool, list[dict[str, Any]]]:
    recent = recent_lo_signal_settlements(2)
    active = len(recent) == 2 and all(int(item["pnl_vnd"]) < 0 for item in recent)
    return active, recent


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
    disabled = (doc.get("funding_policy") or {}).get("xien2_enabled") is False
    codes = funded_codes(doc)
    pairs = [f"{left}-{right}" for left, right in combinations(codes, 2)]
    pair_count = len(pairs)
    has_pairs = pair_count > 0
    brake_active, brake_days = two_lo_loss_brake()
    brake_applies = has_pairs and brake_active

    paper_capital = pair_count * CAPITAL_PER_PAIR_VND
    real_capital = 0 if brake_applies else paper_capital
    gross_if_one = GROSS_RETURN_PER_WINNING_PAIR_VND if has_pairs and not brake_applies else 0

    if disabled:
        status = "TẮT · KHÔNG CẤP VỐN"
        state = "DISABLED_BY_METHOD"
        reason = "MB ROLL30 30/30 chỉ có một giỏ lô canonical; không cộng Xiên 2."
    elif brake_applies:
        status = "PHANH XIÊN · 2 NGÀY LÔ THUA LIÊN TIẾP · SHADOW 0Đ"
        state = "SHADOW_ONLY_TWO_LO_LOSS_BRAKE"
        loss_text = "; ".join(
            f"{item['date']} {int(item['pnl_vnd']):+,}đ".replace(",", ".")
            for item in reversed(brake_days)
        )
        reason = (
            f"Hai ngày lô có lệnh gần nhất đều âm ({loss_text}). "
            f"Vẫn hiển thị {pair_count} cặp ({', '.join(pairs)}) để theo dõi nhưng vốn Xiên thật bằng 0đ; "
            "A1/X2/X3/ROLL7 không bị thay đổi."
        )
    elif has_pairs:
        status = "KHUYẾN NGHỊ ĐÁNH · CHỜ XÁC NHẬN"
        state = "RECOMMENDED_PENDING_CONFIRMATION"
        reason = f"Có {len(codes)} mã được cấp vốn ({', '.join(codes)}); tự động tạo toàn bộ {pair_count} tổ hợp Xiên 2."
    else:
        status = "KHÔNG KÍCH HOẠT · CẦN TỪ 02 SỐ ĐƯỢC CẤP VỐN"
        state = "NOT_APPLICABLE_LT2_FUNDED_CODES"
        reason = f"Chỉ có {len(codes)} mã được cấp vốn; Xiên 2 cần tối thiểu 02 mã."

    recommendation = {
        "rule_version": RULE_VERSION,
        "loss_brake_rule_version": LOSS_BRAKE_VERSION,
        "target_date": doc.get("target_date"),
        "status": status,
        "state": state,
        "base_numbers": codes,
        "pairs": pairs,
        "pair_count": pair_count,
        "pair_generation": "ALL_UNORDERED_2_COMBINATIONS",
        "points_per_pair": 0 if disabled else POINTS_PER_PAIR,
        "reference_capital_per_pair_vnd": 0 if disabled else CAPITAL_PER_PAIR_VND,
        "capital_per_pair_vnd": 0 if disabled or brake_applies else CAPITAL_PER_PAIR_VND,
        "gross_return_per_winning_pair_vnd": 0 if disabled else GROSS_RETURN_PER_WINNING_PAIR_VND,
        "paper_capital_vnd": paper_capital,
        "capital_vnd": real_capital,
        "gross_return_if_one_pair_wins_vnd": gross_if_one,
        "brake_active": brake_applies,
        "brake_basis": brake_days,
        "booking_allowed": has_pairs and not brake_applies and not disabled,
        "confirmation_required": has_pairs and not brake_applies and not disabled,
        "pnl_included": False,
        "reason": reason,
    }
    doc["xien2_policy"] = {
        "status": "DISABLED_BY_MB_ROLL30_METHOD" if disabled else "ACTIVE_RECOMMENDATION_WITH_TWO_LO_LOSS_BRAKE",
        "rule_version": RULE_VERSION,
        "loss_brake_rule_version": LOSS_BRAKE_VERSION,
        "source": "UNIQUE_POSITIVE_STAKE_CODES_IN_CURRENT_PLAN",
        "minimum_codes": 2,
        "pair_generation": "ALL_UNORDERED_2_COMBINATIONS",
        "formula": "n*(n-1)/2",
        "points_per_pair": 0 if disabled else POINTS_PER_PAIR,
        "capital_per_pair_vnd": 0 if disabled else CAPITAL_PER_PAIR_VND,
        "gross_return_per_winning_pair_vnd": 0 if disabled else GROSS_RETURN_PER_WINNING_PAIR_VND,
        "loss_brake_trigger": "TWO_MOST_RECENT_LO_SIGNAL_DAYS_HAVE_NEGATIVE_LO_PNL",
        "loss_brake_effect": "SHOW_PAIRS_AS_SHADOW_ZERO_CAPITAL; NEVER_CHANGE_LO_ORDERS",
        "confirmation_required_before_booking": not disabled,
    }
    doc["xien2_recommendation"] = recommendation

    stake = doc.setdefault("stake_rule", {})
    stake["xien2_points_per_pair"] = 0 if disabled else POINTS_PER_PAIR
    stake["xien2_capital_per_pair_vnd"] = 0 if disabled else CAPITAL_PER_PAIR_VND
    stake["xien2_gross_return_per_winning_pair_vnd"] = 0 if disabled else GROSS_RETURN_PER_WINNING_PAIR_VND
    stake["xien2_two_lo_loss_brake"] = not disabled

    number_caption = "Shadow 0đ · chuẩn 100.000đ/cặp" if brake_applies else f"{CAPITAL_PER_PAIR_VND:,}đ/cặp".replace(",", ".")
    number_role = (
        "Xiên 2 Shadow do phanh hai ngày lô thua; không được đặt tiền thật"
        if brake_applies
        else "Xiên 2 tự động; chờ xác nhận đánh"
    )
    method = {
        "id": "XIEN2_AUTO_PAIRS",
        "label": "Xiên 2 tự động",
        "method": "Ghép toàn bộ cặp từ các số được cấp vốn thật",
        "status": status,
        "visual_status": "EMPTY" if brake_applies or not has_pairs else "PASS",
        "points_per_pair": 0 if disabled else POINTS_PER_PAIR,
        "reference_capital_per_pair_vnd": 0 if disabled else CAPITAL_PER_PAIR_VND,
        "capital_per_pair_vnd": 0 if disabled or brake_applies else CAPITAL_PER_PAIR_VND,
        "code_count": pair_count,
        "pair_count": pair_count,
        "paper_capital_vnd": paper_capital,
        "capital_vnd": real_capital,
        "brake_active": brake_applies,
        "numbers": [
            {
                "code": pair,
                "points": 0,
                "caption": number_caption,
                "capital_vnd": 0 if disabled or brake_applies else CAPITAL_PER_PAIR_VND,
                "role": f"{number_role}: {pair}",
                "visual_status": "EMPTY" if disabled or brake_applies else "PASS",
            }
            for pair in pairs
        ],
        "empty_slot": not has_pairs,
        "reason": reason,
        "confirmation_required": has_pairs and not brake_applies and not disabled,
        "booking_allowed": has_pairs and not brake_applies and not disabled,
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
    top["xien2_paper_capital_vnd"] = paper_capital
    top["xien2_capital_vnd"] = real_capital
    top["xien2_loss_brake_active"] = brake_applies

    group = {
        "id": "XIEN",
        "label": "Xiên 2 tự động",
        "status": state,
        "role": "AUTO RECOMMENDATION · SEPARATE XIEN LEDGER",
        "method": "Toàn bộ tổ hợp 2 từ mã được cấp vốn",
        "layer": f"{pair_count} cặp · vốn thật {real_capital:,}đ".replace(",", "."),
        "selected_numbers": pairs,
        "selection": "|".join(pairs),
        "points": 0 if disabled or brake_applies else pair_count * POINTS_PER_PAIR,
        "points_per_pair": 0 if disabled else POINTS_PER_PAIR,
        "reference_capital_per_pair_vnd": 0 if disabled else CAPITAL_PER_PAIR_VND,
        "capital_per_pair_vnd": 0 if disabled or brake_applies else CAPITAL_PER_PAIR_VND,
        "paper_capital_vnd": paper_capital,
        "capital_vnd": real_capital,
        "summary": status,
        "reason": reason,
        "brake_active": brake_applies,
        "confirmation_required": has_pairs and not brake_applies and not disabled,
        "booking_allowed": has_pairs and not brake_applies and not disabled,
        "candidates": [
            {
                "code": pair,
                "rank": index,
                "gate": not disabled and not brake_applies,
                "status": "TẮT · KHÔNG CẤP VỐN" if disabled else "SHADOW · PHANH XIÊN" if brake_applies else "KHUYẾN NGHỊ ĐÁNH",
                "capital_vnd": 0 if disabled or brake_applies else CAPITAL_PER_PAIR_VND,
                "paper_capital_vnd": 0 if disabled else CAPITAL_PER_PAIR_VND,
                "reason": (
                    "Cặp vẫn được theo dõi nhưng không cấp vốn vì hai ngày lô có lệnh gần nhất đều âm."
                    if brake_applies
                    else "Cặp tự động từ hai mã đã được cấp vốn; chờ xác nhận trước quay."
                ),
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
        pending["xien2_recommended_capital_vnd"] = real_capital
        pending["xien2_paper_capital_vnd"] = paper_capital
        pending["total_recommended_capital_vnd"] = standard_capital + real_capital

    portfolio = doc.setdefault("portfolio", {})
    standard_capital = int(portfolio.get("capital_vnd") or 0)
    portfolio["standard_capital_vnd"] = standard_capital
    portfolio["xien2_recommended_capital_vnd"] = real_capital
    portfolio["xien2_paper_capital_vnd"] = paper_capital
    portfolio["total_recommended_capital_vnd"] = standard_capital + real_capital

    pnl = doc.setdefault("pnl_summary", {})
    standard_pending = int(pnl.get("today_pending_standard_capital_vnd") or pnl.get("today_pending_capital_vnd") or standard_capital)
    pnl["today_pending_standard_capital_vnd"] = standard_pending
    pnl["today_pending_xien2_capital_vnd"] = real_capital
    pnl["today_pending_xien2_paper_capital_vnd"] = paper_capital
    pnl["today_pending_total_recommended_capital_vnd"] = standard_pending + real_capital

    display = doc.setdefault("display_policy", {})
    display["show_xien2_current_recommendation"] = not disabled
    display["show_xien2_loss_brake_status"] = not disabled

    automation = doc.setdefault("automation", {})
    automation["xien2_auto_pair_rule_version"] = RULE_VERSION
    automation["xien2_loss_brake_rule_version"] = LOSS_BRAKE_VERSION
    automation["xien2_loss_brake_active"] = brake_applies
    automation["xien2_auto_pair_complete"] = True
    automation["xien2_disabled_by_method"] = disabled
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
