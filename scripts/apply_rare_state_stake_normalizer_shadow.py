#!/usr/bin/env python3
"""Build RARE_STATE_STAKE_NORMALIZER_V1_SHADOW.

The challenger never changes production orders, stakes, coverage, or P/L booking.
It records a same-day shadow allocation for three rare states:
1) X2 pass with H5Pair=4: X2 50-point legs -> 30 in shadow.
2) X3 pass with prior-draw repeat2=0 and max_frequency=1: X3 50-point legs -> 30.
3) A1+X2+X3 triple pass: A1 50-point legs -> 30; A1 Core100 remains 100.

Cross-method duplicate codes still use the highest shadow stake.
"""
from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURRENT = DATA / "current.json"
OUT = DATA / "rare-state-normalizer-current.json"
LEDGER = DATA / "rare-state-normalizer-shadow-ledger.json"
CSV_OUT = DATA / "sheet-rare-state-normalizer.csv"
VERSION = "RARE_STATE_STAKE_NORMALIZER_V1_SHADOW"
LO_COST = 23_000


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


def merge_points(*maps: dict[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for mapping in maps:
        for code, points in mapping.items():
            result[code] = max(result.get(code, 0), int(points))
    return result


def x2_h5pair(doc: dict[str, Any]) -> int | None:
    chunks: list[str] = []
    for group in doc.get("groups") or []:
        if str(group.get("id") or "").upper() == "X2":
            chunks.extend(str(group.get(key) or "") for key in ("reason", "summary", "status"))
            for candidate in group.get("candidates") or []:
                chunks.append(json.dumps(candidate, ensure_ascii=False))
    for method in (doc.get("top_signals") or {}).get("methods") or []:
        if "X2" in f"{method.get('id', '')} {method.get('label', '')}".upper():
            chunks.extend(str(method.get(key) or "") for key in ("reason", "method", "status"))
            for number in method.get("numbers") or []:
                chunks.append(str(number.get("role") or ""))
    text = " | ".join(chunks)
    match = re.search(r"H5\s*PAIR\s*[=:]?\s*(\d+)", text, flags=re.I)
    if not match:
        match = re.search(r"H5PAIR\s*(\d+)", text, flags=re.I)
    return int(match.group(1)) if match else None


def reduce_50_to_30(mapping: dict[str, int], *, preserve_100: bool = True) -> dict[str, int]:
    result: dict[str, int] = {}
    for code, points in mapping.items():
        value = int(points)
        if value == 50:
            result[code] = 30
        elif preserve_100 and value >= 100:
            result[code] = value
        else:
            result[code] = value
    return result


def build(doc: dict[str, Any]) -> dict[str, Any]:
    maps = method_maps(doc)
    active_standard = [key for key in ("A1", "X2", "X3") if maps[key]]
    baseline = merge_points(maps["A1"], maps["X2"], maps["X3"], maps["ROLL7"])
    shadow_maps = copy.deepcopy(maps)
    rules: list[str] = []

    h5pair = x2_h5pair(doc)
    if maps["X2"] and h5pair == 4:
        shadow_maps["X2"] = reduce_50_to_30(maps["X2"])
        rules.append("X2_H5PAIR4_50_TO_30")

    data = doc.get("data") or {}
    repeat2 = int(data.get("repeat2_count") or 0)
    maxfreq = int(data.get("max_frequency") or 0)
    if maps["X3"] and repeat2 == 0 and maxfreq == 1:
        shadow_maps["X3"] = reduce_50_to_30(maps["X3"])
        rules.append("X3_QUIET_CONTEXT_REPEAT2_0_MAXFREQ_1_50_TO_30")

    if set(active_standard) == {"A1", "X2", "X3"}:
        shadow_maps["A1"] = reduce_50_to_30(maps["A1"], preserve_100=True)
        rules.append("TRIPLE_PASS_A1_SECONDARY50_TO_30_CORE100_UNCHANGED")

    shadow = merge_points(shadow_maps["A1"], shadow_maps["X2"], shadow_maps["X3"], shadow_maps["ROLL7"])
    baseline_capital = sum(baseline.values()) * LO_COST
    shadow_capital = sum(shadow.values()) * LO_COST
    changed = baseline != shadow
    status = "ACTIVE_SHADOW" if changed else "NOT_APPLICABLE_CURRENT_DRAW"

    return {
        "schema_version": VERSION,
        "status": status,
        "target_date": doc.get("target_date"),
        "locked_through": (doc.get("data") or {}).get("locked_through"),
        "source_report_run_id": doc.get("report_run_id"),
        "active_standard_methods": active_standard,
        "observed_state": {
            "x2_h5pair": h5pair,
            "repeat2_count": repeat2,
            "max_frequency": maxfreq,
            "triple_pass": set(active_standard) == {"A1", "X2", "X3"},
        },
        "rules_applied": rules,
        "baseline_method_points": maps,
        "shadow_method_points": shadow_maps,
        "baseline_points_by_code": baseline,
        "shadow_points_by_code": shadow,
        "baseline_capital_vnd": baseline_capital,
        "shadow_capital_vnd": shadow_capital,
        "capital_saving_vnd": baseline_capital - shadow_capital,
        "coverage_effect": "NONE",
        "selection_effect": "NONE",
        "real_money_effect": False,
        "pnl_included": False,
        "promotion_gate": {
            "minimum_prospective_impacted_cases": 20,
            "minimum_operating_months": 12,
            "require_both": True,
            "delta_pnl_positive": True,
            "positive_day_rate_not_lower": True,
            "max_drawdown_not_worse": True,
            "single_quarter_delta_profit_share_max": 0.50,
        },
    }


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def csv_text(ledger: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "target_date", "locked_through", "status", "active_methods", "rules_applied",
        "x2_h5pair", "repeat2_count", "max_frequency", "baseline_points_by_code",
        "shadow_points_by_code", "baseline_capital_vnd", "shadow_capital_vnd",
        "capital_saving_vnd", "coverage_effect", "real_money_effect",
    ])
    for day, entry in sorted((ledger.get("entries") or {}).items()):
        observed = entry.get("observed_state") or {}
        writer.writerow([
            day,
            entry.get("locked_through", ""),
            entry.get("status", ""),
            "|".join(entry.get("active_standard_methods") or []),
            "|".join(entry.get("rules_applied") or []),
            observed.get("x2_h5pair", ""),
            observed.get("repeat2_count", ""),
            observed.get("max_frequency", ""),
            json_text(entry.get("baseline_points_by_code") or {}),
            json_text(entry.get("shadow_points_by_code") or {}),
            entry.get("baseline_capital_vnd", 0),
            entry.get("shadow_capital_vnd", 0),
            entry.get("capital_saving_vnd", 0),
            entry.get("coverage_effect", "NONE"),
            entry.get("real_money_effect", False),
        ])
    return output.getvalue()


def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    doc = json.loads(CURRENT.read_text(encoding="utf-8"))
    current = build(doc)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {"schema_version": VERSION, "entries": {}}
    ledger.setdefault("schema_version", VERSION)
    ledger.setdefault("entries", {})[str(current.get("target_date") or "")] = current

    out_text = json.dumps(current, ensure_ascii=False, indent=2) + "\n"
    ledger_text = json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
    csv_output = csv_text(ledger)

    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != out_text:
            raise SystemExit("rare-state-normalizer-current.json is stale")
        if not LEDGER.exists() or LEDGER.read_text(encoding="utf-8") != ledger_text:
            raise SystemExit("rare-state-normalizer-shadow-ledger.json is stale")
        if not CSV_OUT.exists() or CSV_OUT.read_text(encoding="utf-8") != csv_output:
            raise SystemExit("sheet-rare-state-normalizer.csv is stale")
        print("RARE_STATE_STAKE_NORMALIZER_SHADOW_OK")
        return

    changed: list[str] = []
    if write_if_changed(OUT, out_text):
        changed.append(OUT.name)
    if write_if_changed(LEDGER, ledger_text):
        changed.append(LEDGER.name)
    if write_if_changed(CSV_OUT, csv_output):
        changed.append(CSV_OUT.name)
    print("RARE_STATE_STAKE_NORMALIZER_CHANGED=" + ",".join(changed))


if __name__ == "__main__":
    main()
