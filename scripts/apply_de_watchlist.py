#!/usr/bin/env python3
"""Build the current Đề head/tail watchlist and conditional entry milestones.

The public card is research-only. It never creates a real order by itself.
It reads the canonical 27-code history (first code = DB last two digits), merges
locked settlement rows, then publishes the strongest current head and tail.
"""
from __future__ import annotations

import argparse
import base64
import bz2
import copy
import json
import math
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURRENT = DATA / "current.json"
OVERRIDE = DATA / "current-override.json"
LEDGER = DATA / "settlement-ledger.json"
HISTORY_FILE = DATA / "history-27.bz2.b64"
BOOTSTRAP_DIR = DATA / "history-bootstrap"
RULE_VERSION = "DE_HEAD_TAIL_WATCHLIST_V1"

HEAD_GATE = {
    "gan_min": 36,
    "gan_max": 50,
    "score_min": 0.85,
    "score_max": 1.00,
    "occ30_max": 0,
    "repeat2_min": 3,
    "repeat2_max": 6,
    "maxfreq_max": 3,
    "lead_min": 18,
}
TAIL_GATE = {
    "gan_min": 40,
    "gan_max": 60,
    "score_min": 0.90,
    "score_max": 1.40,
    "occ30_max": 0,
    "repeat2_min": 0,
    "repeat2_max": 4,
    "maxfreq_max": 2,
    "lead_min": 18,
}


def code2(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[-2:].zfill(2) if digits else None


def as_day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else copy.deepcopy(default)


def load_history_rows() -> list[list[str]]:
    if HISTORY_FILE.exists():
        encoded = HISTORY_FILE.read_text(encoding="utf-8").strip()
    else:
        parts = sorted(BOOTSTRAP_DIR.glob("history-27-2024.bz2.b64.part-*"))
        if not parts:
            raise RuntimeError("Thiếu history-27 bootstrap")
        encoded = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
    raw = bz2.decompress(base64.b64decode(encoded))
    doc = json.loads(raw.decode("utf-8"))
    rows: dict[str, list[str]] = {}
    for row in doc.get("rows") or []:
        if not isinstance(row, list) or len(row) != 28:
            continue
        day = as_day(row[0])
        codes = [code2(v) for v in row[1:28]]
        if day and all(codes):
            rows[day.isoformat()] = [day.isoformat(), *[str(x) for x in codes]]

    ledger = load_json(LEDGER, {"settlements": {}})
    for day_text, record in (ledger.get("settlements") or {}).items():
        day = as_day(day_text)
        codes = [code2(v) for v in (record.get("result_codes") or [])]
        if day and len(codes) == 27 and all(codes):
            rows[day.isoformat()] = [day.isoformat(), *[str(x) for x in codes]]
    return [rows[key] for key in sorted(rows)]


def digit_stats(values: list[int]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for digit in range(10):
        completed: list[int] = []
        previous: int | None = None
        for index, value in enumerate(values):
            if value != digit:
                continue
            if previous is not None:
                completed.append(index - previous - 1)
            previous = index
        gan = len(values) if previous is None else len(values) - previous - 1
        gmax = max(completed, default=0)
        score = gan / gmax if gmax > 0 else 0.0
        occ30 = sum(1 for value in values[-30:] if value == digit)
        result.append({"digit": digit, "gan": gan, "gmax": gmax, "score": score, "occ30": occ30})
    ranked = sorted(result, key=lambda item: (-int(item["gan"]), -int(item["gmax"]), int(item["digit"])))
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
        item["lead"] = int(item["gan"]) - int(ranked[1]["gan"]) if rank == 1 and len(ranked) > 1 else 0
    return ranked


def gate_text(side: str, gate: dict[str, Any]) -> str:
    label = "Đầu" if side == "HEAD" else "Đuôi"
    return (
        f"{label} top Gan; lead≥{gate['lead_min']}; Gan {gate['gan_min']}-{gate['gan_max']}; "
        f"Score {gate['score_min']:.2f}-{gate['score_max']:.2f}; Occ30≤{gate['occ30_max']}; "
        f"repeat2 {gate['repeat2_min']}-{gate['repeat2_max']}; maxfreq≤{gate['maxfreq_max']}"
    )


def candidate(side: str, item: dict[str, Any], gate: dict[str, Any], target: date, repeat2: int, maxfreq: int) -> dict[str, Any]:
    required = max(int(gate["gan_min"]), math.ceil(float(gate["score_min"]) * int(item["gmax"]) - 1e-12))
    upper = min(int(gate["gan_max"]), math.floor(float(gate["score_max"]) * int(item["gmax"]) + 1e-12))
    current_gan = int(item["gan"])
    if required <= upper:
        if current_gan <= upper:
            offset = max(required - current_gan, 0)
        else:
            offset = 1 + required
    else:
        offset = 9999
    earliest = target + timedelta(days=offset) if offset < 9999 else None
    numeric_ok = (
        int(gate["gan_min"]) <= current_gan <= int(gate["gan_max"])
        and float(gate["score_min"]) <= float(item["score"]) <= float(gate["score_max"])
        and int(item["occ30"]) <= int(gate["occ30_max"])
        and int(item["lead"]) >= int(gate["lead_min"])
    )
    context_ok = (
        int(gate["repeat2_min"]) <= repeat2 <= int(gate["repeat2_max"])
        and maxfreq <= int(gate["maxfreq_max"])
    )
    paper_pass = numeric_ok and context_ok
    side_vi = "Đầu" if side == "HEAD" else "Đuôi"
    digit = str(item["digit"])
    condition = (
        f"Nếu {side_vi.lower()} {digit} không xuất hiện đến hết ngày trước mốc, vẫn giữ top Gan/lead, "
        f"Occ30 và bối cảnh repeat2/maxfreq còn nằm trong gate. Mốc được tính lại sau mỗi kỳ khóa."
    )
    return {
        "code": f"{side_vi} {digit}",
        "side": side,
        "digit": digit,
        "rank": 1,
        "gate": False,
        "research_gate": paper_pass,
        "status": "PAPER PASS · CHỜ XÁC NHẬN RIÊNG" if paper_pass else "WATCH",
        "gan": current_gan,
        "gmax": int(item["gmax"]),
        "score": round(float(item["score"]), 6),
        "occ30": int(item["occ30"]),
        "lead": int(item["lead"]),
        "current_context": f"repeat2={repeat2}; maxfreq={maxfreq}",
        "required_gate": gate_text(side, gate),
        "earliest_eligible_date": earliest.isoformat() if earliest else "",
        "earliest_condition": condition,
        "milestone_type": "CONDITIONAL_LOWER_BOUND",
        "points": 0,
        "capital_vnd": 0,
    }


def upsert_group(doc: dict[str, Any], group: dict[str, Any]) -> None:
    groups = list(doc.get("groups") or [])
    for index, current in enumerate(groups):
        if str(current.get("id") or "").upper() in {"DE", "DE_DIGIT"}:
            groups[index] = group
            doc["groups"] = groups
            return
    groups.append(group)
    doc["groups"] = groups


def patch(doc: dict[str, Any]) -> dict[str, Any]:
    locked = as_day((doc.get("data") or {}).get("locked_through"))
    target = as_day(doc.get("target_date"))
    if not locked or not target or target <= locked:
        raise RuntimeError("Thiếu ngày khóa/target hợp lệ cho Đề watchlist")
    rows = [row for row in load_history_rows() if as_day(row[0]) and as_day(row[0]) <= locked]
    if not rows or as_day(rows[-1][0]) != locked:
        raise RuntimeError(f"History Đề chưa khóa đến {locked}; latest={rows[-1][0] if rows else 'none'}")
    db_codes = [str(row[1]).zfill(2) for row in rows]
    heads = digit_stats([int(code[0]) for code in db_codes])
    tails = digit_stats([int(code[1]) for code in db_codes])
    data = doc.get("data") or {}
    repeat2 = int(data.get("repeat2_count") or 0)
    maxfreq = int(data.get("max_frequency") or 0)
    head = candidate("HEAD", heads[0], HEAD_GATE, target, repeat2, maxfreq)
    tail = candidate("TAIL", tails[0], TAIL_GATE, target, repeat2, maxfreq)
    candidates = [head, tail]
    any_pass = any(bool(item.get("research_gate")) for item in candidates)
    status = "PAPER PASS · CHỜ XÁC NHẬN RIÊNG" if any_pass else "A0 · THEO DÕI"
    reason = (
        f"Theo dõi {head['code']} và {tail['code']}; chưa cấp vốn tự động. "
        "Mốc vào là lower bound có điều kiện, không phải cam kết."
    )
    watch = {
        "rule_version": RULE_VERSION,
        "method": "Đề Gan Lead18 / Head-Tail Strict v2",
        "status": status,
        "state": "PAPER_PASS" if any_pass else "WATCHLIST_ONLY",
        "target_date": target.isoformat(),
        "data_locked_through": locked.isoformat(),
        "candidates": candidates,
        "points": 0,
        "capital_vnd": 0,
        "confirmation_required": True,
        "real_money_default": False,
        "reason": reason,
    }
    doc["de_watchlist"] = watch
    group = {
        "id": "DE",
        "label": "MB Đề · Đầu/đuôi",
        "status": watch["state"],
        "role": "PAPER / RESEARCH · SEPARATE CONFIRMATION",
        "method": watch["method"],
        "layer": "Top Gan Head/Tail + mốc điều kiện",
        "selected_numbers": [],
        "points": 0,
        "capital_vnd": 0,
        "summary": status,
        "reason": reason,
        "candidates": candidates,
    }
    upsert_group(doc, group)
    method = {
        "id": "DE_WATCHLIST",
        "label": "MB Đề · Đầu/đuôi",
        "method": watch["method"],
        "status": status,
        "visual_status": "NEAR" if any_pass else "FAIL",
        "points_per_code": 0,
        "code_count": 0,
        "capital_vnd": 0,
        "numbers": [],
        "empty_slot": True,
        "candidates": candidates,
        "reason": reason,
    }
    top = doc.setdefault("top_signals", {})
    methods = [item for item in (top.get("methods") or []) if "DE_WATCH" not in str(item.get("id") or "").upper()]
    methods.append(method)
    top["methods"] = methods
    top["displayed_blocks"] = len(methods)
    display = doc.setdefault("display_policy", {})
    display["show_de_current_watchlist"] = True
    automation = doc.setdefault("automation", {})
    automation["de_watchlist_rule_version"] = RULE_VERSION
    automation["de_watchlist_complete"] = True
    return doc


def write_if_changed(path: Path, doc: dict[str, Any]) -> bool:
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def target_paths(current: dict[str, Any]) -> list[Path]:
    paths = [CURRENT]
    if OVERRIDE.exists():
        paths.append(OVERRIDE)
    target = str(current.get("target_date") or "")[:10]
    plan = DATA / "plans" / f"{target}.json"
    if target and plan.exists():
        paths.append(plan)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = load_json(CURRENT, {})
    changed: list[str] = []
    for path in target_paths(current):
        doc = load_json(path, {})
        expected = patch(copy.deepcopy(doc))
        if args.check:
            if doc != expected:
                raise SystemExit(f"Đề watchlist stale: {path}")
        elif write_if_changed(path, expected):
            changed.append(str(path.relative_to(ROOT)))
    print("DE_WATCHLIST_CHANGED=" + ",".join(changed))


if __name__ == "__main__":
    main()
