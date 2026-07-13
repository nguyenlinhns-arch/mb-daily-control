#!/usr/bin/env python3
"""Build and settle coverage-preserving optimization shadows.

The production A1/X2/X3/ROLL7 plan is never changed by this script.

Shadow 1 — XIEN2_CONFLUENCE_ROUTER_V1
* A1+X2 only: keep only cross-method A1–X2 pairs.
* A1+X2+X3: exclude every pair containing an A1 leg; keep all pairs in X2∪X3.
* Every other method combination: keep the canonical all-pairs recommendation.

Shadow 2 — TRIPLE_CONFLUENCE_NORMALIZER_SHADOW
* Active only when A1, X2 and X3 all pass.
* A1 Core main100 remains 100.
* Every A1 50-point leg becomes 30 in the shadow.
* X2/X3 remain 50 and cross-method dedupe still uses the highest stake.

Outputs are separate research files and never create an actual order or P/L booking.
"""
from __future__ import annotations

import argparse
import base64
import bz2
import copy
import csv
import io
import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURRENT = DATA / "current.json"
OPT_CURRENT = DATA / "optimization-current.json"
OPT_LEDGER = DATA / "optimization-shadow-ledger.json"
OPT_CSV = DATA / "sheet-optimization-shadows.csv"
SETTLEMENT_LEDGER = DATA / "settlement-ledger.json"
HISTORY_FILE = DATA / "history-27.bz2.b64"
BOOTSTRAP_DIR = DATA / "history-bootstrap"

LO_COST = 23_000
LO_PAYOUT = 80_000
XIEN_CAPITAL = 100_000
XIEN_GROSS = 1_600_000
ROUTER_VERSION = "XIEN2_CONFLUENCE_ROUTER_V1"
NORMALIZER_VERSION = "TRIPLE_CONFLUENCE_NORMALIZER_SHADOW_V1"
SCHEMA = "MB_COVERAGE_PRESERVE_OPT_V1"


def load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else copy.deepcopy(default)


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def add_point(mapping: dict[str, int], raw_code: Any, raw_points: Any) -> None:
    code = code2(raw_code)
    try:
        points = int(raw_points or 0)
    except (TypeError, ValueError):
        points = 0
    if code and points > 0:
        mapping[code] = max(mapping.get(code, 0), points)


def method_maps(doc: dict[str, Any]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {key: {} for key in ("A1", "X2", "X3", "ROLL7")}
    for method in (doc.get("top_signals") or {}).get("methods") or []:
        key = classify(f"{method.get('id', '')} {method.get('label', '')}")
        if not key:
            continue
        for code, points in (method.get("points_by_code") or {}).items():
            add_point(result[key], code, points)
        for number in method.get("numbers") or []:
            add_point(result[key], number.get("code"), number.get("points"))
    for group in doc.get("groups") or []:
        key = classify(group.get("id"))
        if not key:
            continue
        for code, points in (group.get("points_by_code") or {}).items():
            add_point(result[key], code, points)
    return result


def merge_points(*maps: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for mapping in maps:
        for code, points in mapping.items():
            merged[code] = max(merged.get(code, 0), int(points))
    return merged


def ordered_codes(maps: dict[str, dict[str, int]]) -> list[str]:
    result: list[str] = []
    for key in ("A1", "X2", "X3", "ROLL7"):
        for code in maps[key]:
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
            key = frozenset((left, right))
            if key in seen:
                continue
            seen.add(key)
            result.append(f"{left}-{right}")
    return result


def router_shadow(maps: dict[str, dict[str, int]]) -> dict[str, Any]:
    funded = merge_points(maps["A1"], maps["X2"], maps["X3"], maps["ROLL7"])
    all_codes = [code for code in ordered_codes(maps) if code in funded]
    baseline_pairs = pair_list(all_codes)
    active_standard = [key for key in ("A1", "X2", "X3") if maps[key]]
    active_set = set(active_standard)

    rule = "KEEP_CANONICAL_ALL_PAIRS"
    if active_set == {"A1", "X2"}:
        router_pairs = cross_pairs(list(maps["A1"]), list(maps["X2"]))
        rule = "A1_X2_CROSS_ONLY"
    elif active_set == {"A1", "X2", "X3"}:
        allowed: list[str] = []
        for key in ("X2", "X3"):
            for code in maps[key]:
                if code not in allowed:
                    allowed.append(code)
        router_pairs = pair_list(allowed)
        rule = "TRIPLE_PASS_EXCLUDE_A1_LEGS"
    else:
        router_pairs = list(baseline_pairs)

    return {
        "rule_version": ROUTER_VERSION,
        "status": "SAME_AS_BASELINE" if router_pairs == baseline_pairs else "ROUTED_SHADOW",
        "active_standard_methods": active_standard,
        "rule_applied": rule,
        "funded_codes": all_codes,
        "baseline_pairs": baseline_pairs,
        "router_pairs": router_pairs,
        "baseline_pair_count": len(baseline_pairs),
        "router_pair_count": len(router_pairs),
        "baseline_capital_vnd": len(baseline_pairs) * XIEN_CAPITAL,
        "router_capital_vnd": len(router_pairs) * XIEN_CAPITAL,
        "capital_saving_vnd": (len(baseline_pairs) - len(router_pairs)) * XIEN_CAPITAL,
        "real_money_effect": False,
        "coverage_effect": "NONE",
        "confirmation_required_if_promoted": True,
    }


def normalizer_shadow(maps: dict[str, dict[str, int]]) -> dict[str, Any]:
    active_standard = [key for key in ("A1", "X2", "X3") if maps[key]]
    baseline = merge_points(maps["A1"], maps["X2"], maps["X3"], maps["ROLL7"])
    triple = set(active_standard) == {"A1", "X2", "X3"}
    if not triple:
        normalized = dict(baseline)
        status = "NOT_APPLICABLE_NOT_TRIPLE_PASS"
    else:
        a1_normalized = {code: (100 if points >= 100 else 30) for code, points in maps["A1"].items()}
        normalized = merge_points(a1_normalized, maps["X2"], maps["X3"])
        status = "ACTIVE_TRIPLE_PASS_SHADOW"
    baseline_capital = sum(baseline.values()) * LO_COST
    normalized_capital = sum(normalized.values()) * LO_COST
    return {
        "rule_version": NORMALIZER_VERSION,
        "status": status,
        "active_standard_methods": active_standard,
        "baseline_points_by_code": baseline,
        "shadow_points_by_code": normalized,
        "baseline_capital_vnd": baseline_capital,
        "shadow_capital_vnd": normalized_capital,
        "capital_saving_vnd": baseline_capital - normalized_capital,
        "real_money_effect": False,
        "coverage_effect": "NONE",
    }


def load_result_map() -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    if HISTORY_FILE.exists():
        encoded = HISTORY_FILE.read_text(encoding="utf-8").strip()
    else:
        parts = sorted(BOOTSTRAP_DIR.glob("history-27-2024.bz2.b64.part-*"))
        encoded = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
    if encoded:
        raw = bz2.decompress(base64.b64decode(encoded))
        history = json.loads(raw.decode("utf-8"))
        for row in history.get("rows") or []:
            if isinstance(row, list) and len(row) == 28:
                codes = [code2(value) for value in row[1:28]]
                if all(codes):
                    results[str(row[0])[:10]] = [str(code) for code in codes]
    settlement = load(SETTLEMENT_LEDGER, {"settlements": {}})
    for day, record in (settlement.get("settlements") or {}).items():
        codes = [code2(value) for value in (record.get("result_codes") or [])]
        if len(codes) == 27 and all(codes):
            results[str(day)[:10]] = [str(code) for code in codes]
    return results


def settle_pairs(pairs: list[str], counts: Counter[str]) -> dict[str, Any]:
    wins: list[str] = []
    for pair in pairs:
        parts = re.findall(r"\d{2}", pair)
        if len(parts) == 2 and counts[parts[0]] > 0 and counts[parts[1]] > 0:
            wins.append(pair)
    capital = len(pairs) * XIEN_CAPITAL
    payout = len(wins) * XIEN_GROSS
    return {"wins": wins, "win_count": len(wins), "capital_vnd": capital, "payout_vnd": payout, "pnl_vnd": payout - capital}


def settle_points(points: dict[str, int], counts: Counter[str]) -> dict[str, Any]:
    capital = sum(int(value) for value in points.values()) * LO_COST
    hits = {code: counts[code] for code in points}
    payout = sum(int(points[code]) * LO_PAYOUT * int(hits[code]) for code in points)
    return {"hits": hits, "hits_total": sum(hits.values()), "capital_vnd": capital, "payout_vnd": payout, "pnl_vnd": payout - capital}


def settle_entries(ledger: dict[str, Any]) -> None:
    results = load_result_map()
    for day, entry in (ledger.get("entries") or {}).items():
        codes = results.get(day)
        if not codes:
            entry["settlement_status"] = "PENDING_RESULT"
            continue
        counts = Counter(codes)
        router = entry.get("xien2_router") or {}
        normalizer = entry.get("triple_normalizer") or {}
        entry["settlement"] = {
            "result_codes": codes,
            "xien2_baseline": settle_pairs(router.get("baseline_pairs") or [], counts),
            "xien2_router": settle_pairs(router.get("router_pairs") or [], counts),
            "lo_baseline": settle_points(normalizer.get("baseline_points_by_code") or {}, counts),
            "lo_normalized": settle_points(normalizer.get("shadow_points_by_code") or {}, counts),
        }
        entry["settlement_status"] = "SETTLED_SHADOW"


def csv_output(ledger: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "target_date", "locked_through", "active_methods", "router_status", "router_rule",
        "baseline_pairs", "router_pairs", "baseline_xien_capital_vnd", "router_capital_vnd", "router_saving_vnd",
        "baseline_xien_pnl_vnd", "router_pnl_vnd", "normalizer_status", "baseline_points_by_code",
        "shadow_points_by_code", "baseline_lo_capital_vnd", "shadow_lo_capital_vnd", "normalizer_saving_vnd",
        "baseline_lo_pnl_vnd", "normalized_lo_pnl_vnd", "settlement_status"
    ])
    for day, entry in sorted((ledger.get("entries") or {}).items()):
        router = entry.get("xien2_router") or {}
        normalizer = entry.get("triple_normalizer") or {}
        settlement = entry.get("settlement") or {}
        writer.writerow([
            day, entry.get("locked_through", ""), "|".join(router.get("active_standard_methods") or []),
            router.get("status", ""), router.get("rule_applied", ""), "|".join(router.get("baseline_pairs") or []),
            "|".join(router.get("router_pairs") or []), router.get("baseline_capital_vnd", 0),
            router.get("router_capital_vnd", 0), router.get("capital_saving_vnd", 0),
            (settlement.get("xien2_baseline") or {}).get("pnl_vnd", ""),
            (settlement.get("xien2_router") or {}).get("pnl_vnd", ""), normalizer.get("status", ""),
            json.dumps(normalizer.get("baseline_points_by_code") or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            json.dumps(normalizer.get("shadow_points_by_code") or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            normalizer.get("baseline_capital_vnd", 0), normalizer.get("shadow_capital_vnd", 0),
            normalizer.get("capital_saving_vnd", 0), (settlement.get("lo_baseline") or {}).get("pnl_vnd", ""),
            (settlement.get("lo_normalized") or {}).get("pnl_vnd", ""), entry.get("settlement_status", "PENDING_RESULT")
        ])
    return output.getvalue()


def build(doc: dict[str, Any], ledger: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    maps = method_maps(doc)
    router = router_shadow(maps)
    normalizer = normalizer_shadow(maps)
    target = str(doc.get("target_date") or "")[:10]
    locked = str((doc.get("data") or {}).get("locked_through") or "")[:10]
    current = {
        "schema_version": SCHEMA,
        "status": "ACTIVE_SHADOW_ONLY",
        "target_date": target,
        "locked_through": locked,
        "source_report_run_id": doc.get("report_run_id"),
        "coverage_effect": "NONE",
        "real_money_effect": "NONE_UNTIL_SEPARATE_PROMOTION",
        "xien2_router": router,
        "triple_normalizer": normalizer,
    }
    ledger.setdefault("schema_version", SCHEMA)
    ledger.setdefault("policies", {
        "xien2_router": ROUTER_VERSION,
        "triple_normalizer": NORMALIZER_VERSION,
        "status": "SHADOW_ONLY"
    })
    ledger.setdefault("entries", {})[target] = {
        "target_date": target,
        "locked_through": locked,
        "source_report_run_id": doc.get("report_run_id"),
        "xien2_router": router,
        "triple_normalizer": normalizer,
        "settlement_status": (ledger.get("entries", {}).get(target) or {}).get("settlement_status", "PENDING_RESULT"),
        "settlement": (ledger.get("entries", {}).get(target) or {}).get("settlement"),
    }
    settle_entries(ledger)
    return current, ledger, csv_output(ledger)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    doc = load(CURRENT, {})
    ledger = load(OPT_LEDGER, {"schema_version": SCHEMA, "entries": {}})
    expected_current, expected_ledger, expected_csv = build(doc, ledger)
    if args.check:
        if load(OPT_CURRENT, {}) != expected_current:
            raise SystemExit("optimization-current.json is stale")
        if load(OPT_LEDGER, {}) != expected_ledger:
            raise SystemExit("optimization-shadow-ledger.json is stale")
        if not OPT_CSV.exists() or OPT_CSV.read_text(encoding="utf-8") != expected_csv:
            raise SystemExit("sheet-optimization-shadows.csv is stale")
        print("COVERAGE_PRESERVE_OPTIMIZATIONS_OK")
        return
    save(OPT_CURRENT, expected_current)
    save(OPT_LEDGER, expected_ledger)
    OPT_CSV.write_text(expected_csv, encoding="utf-8")
    print(json.dumps(expected_current, ensure_ascii=False))


if __name__ == "__main__":
    main()
