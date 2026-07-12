#!/usr/bin/env python3
"""Export the latest MB settlement/plan state as CSV for Google Sheet IMPORTDATA.

The canonical Google workbook can import these two public CSV files:
- data/sheet-current.csv: latest locked settlement summary + next-draw plan.
- data/sheet-settlements.csv: append-only settlement ledger projection.

This script is deterministic and idempotent. It never invents P/L and only reads
records already present in data/current.json and data/settlement-ledger.json.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURRENT = DATA / "current.json"
LEDGER = DATA / "settlement-ledger.json"
CURRENT_CSV = DATA / "sheet-current.csv"
SETTLEMENT_CSV = DATA / "sheet-settlements.csv"


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    return json.loads(path.read_text(encoding="utf-8"))


def csv_text(rows: list[list[Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    return output.getvalue()


def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_current(doc: dict[str, Any], ledger: dict[str, Any]) -> str:
    data = doc.get("data") or {}
    portfolio = doc.get("portfolio") or {}
    pending = doc.get("pending_order") or {}
    pnl = doc.get("pnl_summary") or {}
    settlements = ledger.get("settlements") or {}
    last_date = max(settlements, default="")
    last = settlements.get(last_date) or {}
    last_lo = last.get("lo") or {}

    rows: list[list[Any]] = [["section", "key", "value"]]
    values = [
        ("meta", "config_id", doc.get("config_id", "")),
        ("meta", "report_run_id", doc.get("report_run_id", "")),
        ("meta", "generated_at", doc.get("generated_at", "")),
        ("data", "locked_through", data.get("locked_through", "")),
        ("data", "data_status", data.get("status", "")),
        ("data", "code_count", data.get("count", "")),
        ("settlement", "latest_date", last_date),
        ("settlement", "latest_result_codes", "|".join(last.get("result_codes") or [])),
        ("settlement", "latest_funded_codes", "|".join(last_lo.get("numbers") or [])),
        ("settlement", "latest_points_by_code", compact_json(last_lo.get("points_by_code") or {})),
        ("settlement", "latest_hits_by_code", compact_json(last_lo.get("hits") or {})),
        ("settlement", "latest_hits_total", last_lo.get("hits_total", "")),
        ("settlement", "latest_capital_vnd", last.get("total_capital_vnd", "")),
        ("settlement", "latest_pnl_vnd", last.get("total_pnl_vnd", "")),
        ("pnl", "confirmed_through", pnl.get("confirmed_through", "")),
        ("pnl", "grand_total_pnl_vnd", pnl.get("grand_total_pnl_vnd", "")),
        ("next", "target_date", doc.get("target_date", "")),
        ("next", "decision", portfolio.get("decision", "")),
        ("next", "selection", portfolio.get("selection", "")),
        ("next", "points_by_code", compact_json(portfolio.get("points_by_code") or pending.get("points_by_code") or {})),
        ("next", "total_points", portfolio.get("points", "")),
        ("next", "capital_vnd", portfolio.get("capital_vnd", "")),
        ("next", "execution_status", pending.get("status", "A0" if not pending else "")),
        ("next", "pnl_included", bool(pending.get("pnl_included", False))),
    ]
    rows.extend([list(item) for item in values])
    return csv_text(rows)


def build_settlements(ledger: dict[str, Any]) -> str:
    rows: list[list[Any]] = [[
        "date",
        "result_codes",
        "funded_codes",
        "points_by_code",
        "hits_by_code",
        "hits_total",
        "lo_capital_vnd",
        "lo_payout_vnd",
        "lo_pnl_vnd",
        "xien_pnl_vnd",
        "total_capital_vnd",
        "total_payout_vnd",
        "total_pnl_vnd",
        "components",
    ]]
    for day, record in sorted((ledger.get("settlements") or {}).items()):
        lo = record.get("lo") or {}
        xien = record.get("xien2") or {}
        rows.append([
            day,
            "|".join(record.get("result_codes") or []),
            "|".join(lo.get("numbers") or []),
            compact_json(lo.get("points_by_code") or {}),
            compact_json(lo.get("hits") or {}),
            lo.get("hits_total", 0),
            lo.get("capital_vnd", 0),
            lo.get("payout_vnd", 0),
            lo.get("pnl_vnd", 0),
            xien.get("pnl_vnd", 0),
            record.get("total_capital_vnd", 0),
            record.get("total_payout_vnd", 0),
            record.get("total_pnl_vnd", 0),
            compact_json(record.get("components") or []),
        ])
    return csv_text(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    doc = load_json(CURRENT, {})
    ledger = load_json(LEDGER, {"settlements": {}})
    current_text = build_current(doc, ledger)
    settlements_text = build_settlements(ledger)

    if args.check:
        if CURRENT_CSV.read_text(encoding="utf-8") != current_text:
            raise SystemExit("sheet-current.csv is stale")
        if SETTLEMENT_CSV.read_text(encoding="utf-8") != settlements_text:
            raise SystemExit("sheet-settlements.csv is stale")
        print("SHEET_SYNC_CSV_OK")
        return

    changed = []
    if write_if_changed(CURRENT_CSV, current_text):
        changed.append(CURRENT_CSV.name)
    if write_if_changed(SETTLEMENT_CSV, settlements_text):
        changed.append(SETTLEMENT_CSV.name)
    print("SHEET_SYNC_CHANGED=" + ",".join(changed))


if __name__ == "__main__":
    main()
