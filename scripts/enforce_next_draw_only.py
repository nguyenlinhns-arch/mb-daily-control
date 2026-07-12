#!/usr/bin/env python3
"""Keep the public website focused on the next draw after settlement.

Audit history remains in dated plans and settlement ledgers. Only the public
`current` payload is compacted: cumulative P/L is retained and completed-draw
orders/results are removed. All current A1/X2/X3/ROLL7/Xiên 2 cards and current
candidates remain visible, whether active or inactive.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAYLOADS = (ROOT / "data" / "current.json", ROOT / "data" / "current-override.json")


def parse_day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def write_if_changed(path: Path, doc: dict[str, Any]) -> bool:
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def compact(doc: dict[str, Any]) -> bool:
    target = parse_day(doc.get("target_date"))
    data = doc.get("data") or {}
    locked = parse_day(data.get("locked_through"))
    automation = doc.get("automation") or {}
    if target is None or locked is None or target <= locked:
        return False
    if automation and automation.get("settlement_checked") is False:
        return False

    before = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    doc["display_policy"] = {
        "mode": "NEXT_DRAW_ONLY_AFTER_SETTLEMENT",
        "show_target_date_only": True,
        "show_all_current_methods": True,
        "show_nonfunded_current_candidates": True,
        "show_roll7_current_status": True,
        "show_xien2_current_recommendation": True,
        "hide_completed_draw_details": True,
        "hide_latest_27_codes": True,
        "hide_completed_draw_method_cards": True,
        "pnl_display": "CUMULATIVE_AND_NEXT_CAPITAL_ONLY",
        "settlement_applied_through": locked.isoformat(),
    }

    for key in ("last_settlement", "settlement"):
        doc.pop(key, None)

    actual = doc.get("actual_order") or {}
    actual_day = parse_day(actual.get("date"))
    if actual_day is not None and actual_day <= locked:
        doc.pop("actual_order", None)

    for key in ("latest_27_codes", "repeat_codes", "source_tabs", "sha256"):
        data.pop(key, None)
    doc["data"] = data

    summary = doc.get("pnl_summary") or {}
    allowed = {
        "confirmed_through",
        "settlement_applied",
        "grand_total_pnl_vnd",
        "active_all_real_pnl_vnd",
        "today_pending_capital_vnd",
        "today_pending_standard_capital_vnd",
        "today_pending_xien2_capital_vnd",
        "today_pending_total_recommended_capital_vnd",
        "today_pending_order",
        "today_included",
    }
    doc["pnl_summary"] = {key: value for key, value in summary.items() if key in allowed}
    doc["pnl_summary"]["confirmed_through"] = locked.isoformat()
    doc["pnl_summary"]["settlement_applied"] = True

    # Preserve every current operational/recommendation group. Historical result
    # groups remain outside the public current payload.
    groups = doc.get("groups") or []
    doc["groups"] = [
        group for group in groups
        if str(group.get("id", "")).upper() in {"A1", "X2", "X3", "ROLL7", "XIEN", "XIEN2"}
    ]

    after = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    return before != after


def main() -> None:
    changed_paths: list[str] = []
    for path in PUBLIC_PAYLOADS:
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if compact(doc) and write_if_changed(path, doc):
            changed_paths.append(str(path.relative_to(ROOT)))
    print("NEXT_DRAW_ONLY_CHANGED=" + ",".join(changed_paths))


if __name__ == "__main__":
    main()
