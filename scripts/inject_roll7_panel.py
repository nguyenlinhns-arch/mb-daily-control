#!/usr/bin/env python3
"""Keep a permanent ROLL7 status card in the public next-draw payload.

ROLL7 is a conditional real-money rescue layer, not a fourth standard method:
- it is funded at 50 points/code only when A1, X2 and X3 are all A0 and the
  rolling 5-of-7 floor requires a signal day;
- otherwise the card remains visible with zero capital and the exact reason it
  is not activated.

The script is deterministic and idempotent. It updates current.json and the
optional current-override.json without touching settlement history.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PAYLOADS = (DATA / "current.json", DATA / "current-override.json")
LEDGER = DATA / "review-ledger.json"
ROLL7_ID = "ROLL7_STATUS"
COST_PER_POINT = 23_000
ROLL7_POINTS = 50


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def upper(value: Any) -> str:
    return str(value or "").upper()


def method_is_standard_pass(method: dict[str, Any]) -> bool:
    ident = upper(method.get("id"))
    is_standard = any(token in ident for token in ("A1", "X2", "X3"))
    return is_standard and int(method.get("capital_vnd") or 0) > 0


def review_roll7_status(target_date: str) -> str:
    ledger = load_json(LEDGER, {"plans": {}})
    plan = (ledger.get("plans") or {}).get(target_date) or {}
    return upper((plan.get("method_status") or {}).get("ROLL7"))


def active_roll7_component(doc: dict[str, Any]) -> dict[str, Any] | None:
    pending = doc.get("pending_order") or {}
    for component in pending.get("components") or []:
        if upper(component.get("id")).startswith("ROLL7"):
            return component
    if upper(pending.get("method_id")).startswith("ROLL7"):
        points = pending.get("points_by_code") or {}
        return {
            "id": pending.get("method_id"),
            "codes": list(points),
            "points_by_code": points,
        }
    if upper((doc.get("portfolio") or {}).get("decision")).startswith("ROLL7"):
        points = (doc.get("portfolio") or {}).get("points_by_code") or {}
        return {"id": "ROLL7_RESCUE50", "codes": list(points), "points_by_code": points}
    return None


def build_panel(doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    target_date = str(doc.get("target_date") or "")
    methods = (doc.get("top_signals") or {}).get("methods") or []
    active = active_roll7_component(doc)
    ledger_status = review_roll7_status(target_date)
    standard_pass = any(method_is_standard_pass(m) for m in methods)

    if active:
        raw_points = active.get("points_by_code") or {}
        codes = [str(code).zfill(2) for code in (active.get("codes") or list(raw_points))]
        points_by_code = {code: int(raw_points.get(code, ROLL7_POINTS) or ROLL7_POINTS) for code in codes}
        numbers = [
            {
                "code": code,
                "points": points_by_code[code],
                "capital_vnd": points_by_code[code] * COST_PER_POINT,
                "role": "ROLL7 rescue50 · kích hoạt để giữ floor 5-of-7",
                "visual_status": "PASS",
            }
            for code in codes
        ]
        status = "ĐẠT · CHỜ XÁC NHẬN"
        visual = "PASS"
        reason = "A1, X2 và X3 đều A0; cửa sổ 5-of-7 yêu cầu cứu hôm nay."
        state = "ACTIVE_RESCUE30"
        capital = sum(number["capital_vnd"] for number in numbers)
        code_count = len(numbers)
        selected = codes
        total_points = sum(points_by_code.values())
    else:
        points_by_code = {}
        numbers = []
        capital = 0
        code_count = 0
        selected = []
        total_points = 0
        visual = "EMPTY"
        if standard_pass or "STANDARD_PASS" in ledger_status:
            status = "KHÔNG KÍCH HOẠT · ĐÃ CÓ TÍN HIỆU CHUẨN"
            reason = "ROLL7 chỉ dùng khi A1, X2 và X3 đều A0; kỳ này đã có phương pháp chuẩn đạt."
            state = "NOT_APPLICABLE_STANDARD_PASS"
        elif "DATA" in ledger_status and ("FAIL" in ledger_status or "A0" in ledger_status):
            status = "A0 · DỮ LIỆU KHÔNG ĐỦ"
            reason = "Không được dùng ROLL7 khi dữ liệu thiếu, lệch hoặc chưa khóa."
            state = "A0_DATA_GATE"
        else:
            status = "CHƯA CẦN CỨU"
            reason = "Cả ba phương pháp chuẩn A0 nhưng cửa sổ 5-of-7 hiện chưa bắt buộc kích hoạt cứu."
            state = ledger_status or "NOT_REQUIRED_BY_ROLLING_FLOOR"

    panel = {
        "id": ROLL7_ID,
        "label": "MB ROLL7 · 5-of-7",
        "method": "ROLL7 rescue50 · chỉ khi A1/X2/X3 đều A0",
        "status": status,
        "visual_status": visual,
        "points_per_code": ROLL7_POINTS,
        "points_by_code": points_by_code,
        "code_count": code_count,
        "capital_vnd": capital,
        "numbers": numbers,
        "empty_slot": not bool(numbers),
        "target": "Ít nhất 5 ngày phát số trong mọi 7 phiên liên tiếp",
        "reason": reason,
        "state": state,
    }
    group = {
        "id": "ROLL7",
        "label": "MB ROLL7 · 5-of-7",
        "status": state,
        "role": "OTHER50 CONDITIONAL RESCUE",
        "method": "ROLL7 Rescue50",
        "layer": "Chỉ xét khi A1, X2, X3 đều A0",
        "selected_numbers": selected,
        "points": total_points,
        "points_by_code": points_by_code,
        "capital_vnd": capital,
        "summary": status,
        "reason": reason,
        "candidates": [],
    }
    return panel, group


def inject(doc: dict[str, Any]) -> bool:
    before = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    panel, group = build_panel(doc)

    top = doc.setdefault("top_signals", {})
    methods = [m for m in (top.get("methods") or []) if upper(m.get("id")) != ROLL7_ID]
    # Keep current A1/X2/X3 order and place ROLL7 last.
    methods.append(panel)
    top["methods"] = methods
    top["displayed_blocks"] = len(methods)
    top["roll7_note"] = panel["reason"]

    groups = [g for g in (doc.get("groups") or []) if upper(g.get("id")) != "ROLL7"]
    groups.append(group)
    doc["groups"] = groups

    display = doc.setdefault("display_policy", {})
    display["show_all_current_methods"] = True
    display["show_roll7_current_status"] = True
    display["hide_completed_draw_details"] = True

    doc["roll7_status"] = {
        "target_date": doc.get("target_date"),
        "state": panel["state"],
        "status": panel["status"],
        "points_per_code": ROLL7_POINTS,
        "selected_numbers": group["selected_numbers"],
        "points_by_code": group["points_by_code"],
        "capital_vnd": group["capital_vnd"],
        "reason": panel["reason"],
    }

    after = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    return before != after


def check(doc: dict[str, Any]) -> None:
    methods = (doc.get("top_signals") or {}).get("methods") or []
    panels = [m for m in methods if upper(m.get("id")) == ROLL7_ID]
    assert len(panels) == 1, panels
    panel = panels[0]
    assert int(panel.get("points_per_code") or 0) == ROLL7_POINTS, panel
    assert doc.get("roll7_status"), "roll7_status missing"
    group_ids = {upper(g.get("id")) for g in (doc.get("groups") or [])}
    assert "ROLL7" in group_ids, group_ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed: list[str] = []
    for path in PAYLOADS:
        if not path.exists():
            continue
        doc = load_json(path, {})
        if args.check:
            check(doc)
            continue
        if inject(doc):
            dump_json(path, doc)
            changed.append(str(path.relative_to(ROOT)))
    if args.check:
        print("ROLL7_PANEL_OK")
    else:
        print("ROLL7_PANEL_CHANGED=" + ",".join(changed))


if __name__ == "__main__":
    main()
