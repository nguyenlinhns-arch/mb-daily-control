#!/usr/bin/env python3
"""Export settlement, next-draw, Xiên 2 and Đề watchlist state as CSV."""
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


def compact_execution_status(doc: dict[str, Any], pending: dict[str, Any], portfolio: dict[str, Any]) -> str:
    """Return a stable user-facing status instead of an internal enum."""
    display = doc.get("display_policy") or {}
    explicit = (
        pending.get("display_status")
        or portfolio.get("display_status")
        or display.get("execution_status_label")
    )
    if explicit:
        return str(explicit)
    if not pending:
        return "A0"
    internal = str(pending.get("status") or "").upper()
    if internal in {"SYSTEM_SIGNAL_NOT_YET_CONFIRMED", "PASS_REAL_PENDING", "PENDING_CONFIRMATION"}:
        return "CHỜ XÁC NHẬN"
    if "CONFIRMED" in internal:
        return "ĐÃ XÁC NHẬN"
    return str(pending.get("status") or "CHỜ XÁC NHẬN")


def build_current(doc: dict[str, Any], ledger: dict[str, Any]) -> str:
    data = doc.get("data") or {}
    portfolio = doc.get("portfolio") or {}
    pending = doc.get("pending_order") or {}
    pnl = doc.get("pnl_summary") or {}
    xien = doc.get("xien2_recommendation") or {}
    de = doc.get("de_watchlist") or {}
    de_candidates = de.get("candidates") or []
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
        ("next", "standard_capital_vnd", portfolio.get("standard_capital_vnd", portfolio.get("capital_vnd", ""))),
        ("next", "xien2_recommended_capital_vnd", xien.get("capital_vnd", 0)),
        ("next", "total_recommended_capital_vnd", portfolio.get("total_recommended_capital_vnd", portfolio.get("capital_vnd", ""))),
        ("next", "execution_status", compact_execution_status(doc, pending, portfolio)),
        ("next", "pnl_included", bool(pending.get("pnl_included", False))),
        ("xien2", "rule_version", xien.get("rule_version", "")),
        ("xien2", "status", xien.get("status", "")),
        ("xien2", "base_numbers", "|".join(xien.get("base_numbers") or [])),
        ("xien2", "pairs", "|".join(xien.get("pairs") or [])),
        ("xien2", "pair_count", xien.get("pair_count", 0)),
        ("xien2", "points_per_pair", xien.get("points_per_pair", 100)),
        ("xien2", "capital_per_pair_vnd", xien.get("capital_per_pair_vnd", 100000)),
        ("xien2", "capital_vnd", xien.get("capital_vnd", 0)),
        ("xien2", "gross_return_per_winning_pair_vnd", xien.get("gross_return_per_winning_pair_vnd", 1600000)),
        ("xien2", "confirmation_required", bool(xien.get("confirmation_required", True))),
        ("xien2", "pnl_included", bool(xien.get("pnl_included", False))),
        ("de", "rule_version", de.get("rule_version", "")),
        ("de", "status", de.get("status", "")),
        ("de", "method", de.get("method", "")),
        ("de", "candidate_count", len(de_candidates)),
        ("de", "candidate_list", "|".join(str(item.get("code") or "") for item in de_candidates)),
        ("de", "earliest_dates", compact_json({str(item.get("code") or ""): item.get("earliest_eligible_date", "") for item in de_candidates})),
        ("de", "candidate_metrics", compact_json({str(item.get("code") or ""): {"gan": item.get("gan"), "gmax": item.get("gmax"), "score": item.get("score"), "occ30": item.get("occ30"), "lead": item.get("lead")} for item in de_candidates})),
        ("de", "capital_vnd", 0),
    ]
    rows.extend([list(item) for item in values])
    return csv_text(rows)


def build_settlements(ledger: dict[str, Any]) -> str:
    rows: list[list[Any]] = [[
        "date", "result_codes", "funded_codes", "points_by_code", "hits_by_code", "hits_total",
        "lo_capital_vnd", "lo_payout_vnd", "lo_pnl_vnd",
        "xien_pairs", "xien_wins", "xien_losses", "xien_capital_vnd", "xien_payout_vnd", "xien_pnl_vnd",
        "total_capital_vnd", "total_payout_vnd", "total_pnl_vnd", "components",
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
            "|".join(xien.get("pairs") or []),
            xien.get("wins", 0),
            xien.get("losses", 0),
            xien.get("capital_vnd", 0),
            xien.get("payout_vnd", 0),
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
