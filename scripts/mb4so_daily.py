#!/usr/bin/env python3
"""Fail-closed 00:05 Vietnam pipeline for the private MB 4SO report.

The public website never receives the paid TOP1/TOP2 codes. This program
updates the canonical Google source, settles the previous private report in
the Linh ledger, records the new MB 4SO run in private Google Sheets, and only
then replaces ``Paid_Report`` for the new website date.

Frozen selector contract:

    MB_4SO_V1 / MB_4SO_PRIMARY_V1_20260731
    MB_4SO_TOP2_2SO_T1_V1
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from hashlib import sha256
import json
import math
import os
import re
from typing import Any, Callable, Iterable, Sequence
from zoneinfo import ZoneInfo

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ModuleNotFoundError:  # Pure selector tests do not need Google clients.
    service_account = None
    build = None

from build_public_snapshot import load_history, validate_rows


VN = ZoneInfo("Asia/Ho_Chi_Minh")
SOURCE_SHEET_ID = "1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w"
SOURCE_HISTORY_TAB = "MB_History_27"
SOURCE_HISTORY_MIRROR_TAB = "MB_History_27_IMPORT"
SOURCE_PRIVATE_CONFIG_TAB = "V32_Private_Config"
PNL_TAB = "Linh"
PAID_REPORT_TAB = "Paid_Report"

PNL_SHEET_ID_SHA256 = "c88604c7d065f2590d808bd9a0d5b58ebee49efd09573062fc7798ea0b7c9279"
PAID_REPORT_SHEET_ID_SHA256 = "8e192c641313ce78013b5c71f3b0750833dd7d08a18fc1b3dc7de252c7f0d510"

METHOD_ID = "MB_4SO_V1"
CONFIG_ID = "MB_4SO_PRIMARY_V1_20260731"
ALGORITHM_ID = "MB_4SO_TOP2_2SO_T1_V1"
POINTS_PER_CODE = 50
COST_PER_POINT_VND = 23_000
PAYOUT_PER_HIT_POINT_VND = 80_000
SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)


class DailyFourSoError(RuntimeError):
    """Raised whenever a fail-closed gate is not satisfied."""


@dataclass(frozen=True)
class PairScore:
    pair: str
    left: str
    right: str
    score: float
    hit_rate_60: float
    hit_rate_21: float
    occurrence_21: int
    occurrence_all: int
    hit_rate_365: float
    gap: int


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical_json(value)).hexdigest()


def vi_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def quote_tab(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def pad(row: Sequence[Any], width: int) -> list[Any]:
    return list(row) + [""] * max(0, width - len(row))


def rank_pct_average(values: Sequence[float | int]) -> list[float]:
    """Ascending average rank divided by N, matching pandas rank(pct=True)."""
    if not values:
        raise DailyFourSoError("Cannot rank an empty sequence")
    total = len(values)
    result: list[float] = []
    for value in values:
        lower = sum(item < value for item in values)
        equal = sum(item == value for item in values)
        result.append((lower + (equal + 1) / 2) / total)
    return result


def normalize_history(rows: Iterable[Sequence[Any]]) -> list[list[str]]:
    normalized: list[list[str]] = []
    for raw in rows:
        row = [str(value).strip() for value in raw]
        if not row or not row[0]:
            continue
        if row[0].lower() == "date":
            continue
        parsed = parse_date(row[0])
        if parsed is None:
            raise DailyFourSoError(f"Invalid history date: {row[0]!r}")
        codes = pad(row[1:], 27)[:27]
        if any(not re.fullmatch(r"\d{2}", code) for code in codes):
            raise DailyFourSoError(f"History {parsed} is not exactly 27 two-digit codes")
        normalized.append([parsed.isoformat(), *codes])
    normalized.sort(key=lambda item: item[0])
    validate_rows(normalized)
    return normalized


def score_reverse_pairs(history_rows: Sequence[Sequence[str]]) -> list[PairScore]:
    """Run the frozen MB 4SO selector over rows locked through T-1."""
    rows = normalize_history(history_rows)
    if len(rows) < 365:
        raise DailyFourSoError("MB 4SO requires at least 365 locked draws")

    pairs = [
        (f"{left}{right}", f"{right}{left}")
        for left in range(10)
        for right in range(left + 1, 10)
    ]
    metrics: list[dict[str, Any]] = []
    for left, right in pairs:
        pair_codes = {left, right}
        flags = [int(bool(pair_codes.intersection(row[1:]))) for row in rows]

        def hit_rate(window: int) -> float:
            sample = flags[-window:]
            return sum(sample) / len(sample)

        def occurrences(window: int | None) -> int:
            sample = rows if window is None else rows[-window:]
            return sum(sum(code in pair_codes for code in row[1:]) for row in sample)

        gap = next(
            (offset for offset, flag in enumerate(reversed(flags)) if flag),
            len(flags),
        )
        metrics.append(
            {
                "left": left,
                "right": right,
                "pair": f"{left}-{right}",
                "hit_rate_60": hit_rate(60),
                "hit_rate_21": hit_rate(21),
                "occurrence_21": occurrences(21),
                "occurrence_all": occurrences(None),
                "hit_rate_365": hit_rate(365),
                "gap": gap,
            }
        )

    hit60_rank = rank_pct_average([item["hit_rate_60"] for item in metrics])
    gap_rank = rank_pct_average([math.log1p(item["gap"]) for item in metrics])
    scored: list[PairScore] = []
    for item, rank_hit, rank_gap in zip(metrics, hit60_rank, gap_rank, strict=True):
        # Frozen tie hierarchy: CR60 -> CR21 -> Occ21 -> FullHistoryOcc -> CR365.
        score = (
            rank_hit
            + 0.25 * rank_gap
            + 1e-6 * item["hit_rate_60"]
            + 1e-7 * item["hit_rate_21"]
            + 1e-8 * item["occurrence_21"]
            + 1e-9 * item["occurrence_all"]
            + 1e-10 * item["hit_rate_365"]
        )
        scored.append(PairScore(score=score, **item))

    scored.sort(key=lambda item: item.score, reverse=True)
    if len(scored) != 45 or len({item.pair for item in scored}) != 45:
        raise DailyFourSoError("MB 4SO did not score exactly 45 unique reverse pairs")
    if abs(scored[1].score - scored[2].score) <= 1e-12:
        raise DailyFourSoError("TIE_REVIEW: rank 2 and rank 3 are not uniquely separated")
    selected = [scored[0].left, scored[0].right, scored[1].left, scored[1].right]
    if len(set(selected)) != 4:
        raise DailyFourSoError("TOP1/TOP2 must contain four distinct codes")
    return scored


def settlement(codes: Sequence[str], result_codes: Sequence[str]) -> dict[str, Any]:
    if len(codes) != 4 or len(set(codes)) != 4:
        raise DailyFourSoError("Settlement requires four distinct selected codes")
    if any(not re.fullmatch(r"\d{2}", code) for code in [*codes, *result_codes]):
        raise DailyFourSoError("Settlement contains an invalid two-digit code")
    counts = Counter(result_codes)
    hits = {code: counts[code] for code in codes}
    total_hits = sum(hits.values())
    points = len(codes) * POINTS_PER_CODE
    capital = points * COST_PER_POINT_VND
    payout = total_hits * POINTS_PER_CODE * PAYOUT_PER_HIT_POINT_VND
    return {
        "codes": list(codes),
        "hits": hits,
        "total_hits": total_hits,
        "points": points,
        "capital_vnd": capital,
        "payout_vnd": payout,
        "pnl_vnd": payout - capital,
    }


def load_credentials():
    if service_account is None:
        raise DailyFourSoError("Missing google-auth/google-api-python-client")
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise DailyFourSoError("Missing GOOGLE_SERVICE_ACCOUNT_JSON")
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DailyFourSoError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
    required = {"client_email", "private_key", "token_uri"}
    missing = sorted(required - set(info))
    if missing:
        raise DailyFourSoError(f"Service-account JSON is missing: {', '.join(missing)}")
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def sheets_service():
    if build is None:
        raise DailyFourSoError("Missing google-api-python-client")
    return build("sheets", "v4", credentials=load_credentials(), cache_discovery=False)


def get_values(service, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
    response = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueRenderOption="FORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING",
        )
        .execute()
    )
    return response.get("values", [])


def update_values(service, spreadsheet_id: str, range_name: str, values: list[list[Any]]) -> None:
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body={"majorDimension": "ROWS", "values": values},
        )
        .execute()
    )


def append_values(service, spreadsheet_id: str, range_name: str, values: list[list[Any]]) -> None:
    (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"majorDimension": "ROWS", "values": values},
        )
        .execute()
    )


def spreadsheet_titles(service, spreadsheet_id: str) -> set[str]:
    response = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title")
        .execute()
    )
    return {item["properties"]["title"] for item in response.get("sheets", [])}


def verified_private_id(value: str, expected_hash: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,200}", value):
        raise DailyFourSoError(f"{label} spreadsheet ID is invalid")
    if sha256(value.encode("utf-8")).hexdigest() != expected_hash:
        raise DailyFourSoError(f"{label} spreadsheet ID does not match the locked identity")
    return value


def private_sheet_ids(service) -> tuple[str, str]:
    rows = get_values(
        service, SOURCE_SHEET_ID, f"{quote_tab(SOURCE_PRIVATE_CONFIG_TAB)}!A1:C20"
    )
    config: dict[str, str] = {}
    for row in rows[1:]:
        cells = pad(row, 2)
        key, value = str(cells[0]).strip(), str(cells[1]).strip()
        if key:
            if key in config:
                raise DailyFourSoError(f"Duplicate private config key: {key}")
            config[key] = value
    if config.get("CONFIG_VERSION") != "MB_V32_PRIVATE_CONFIG_V1":
        raise DailyFourSoError("Private runtime config version mismatch")
    pnl_id = verified_private_id(
        config.get("PNL_SHEET_ID", ""), PNL_SHEET_ID_SHA256, "P/L"
    )
    paid_id = verified_private_id(
        config.get("PAID_REPORT_SHEET_ID", ""),
        PAID_REPORT_SHEET_ID_SHA256,
        "Paid report",
    )
    return pnl_id, paid_id


def local_lock_row(lock_date: date) -> list[str]:
    rows = normalize_history(load_history()["rows"])
    matches = [row for row in rows if row[0] == lock_date.isoformat()]
    if len(matches) != 1:
        raise DailyFourSoError(f"Local public audit has no unique row for {lock_date}")
    return matches[0]


def sync_source_history(service, lock_date: date, local_row: list[str]) -> list[list[str]]:
    required = {
        SOURCE_HISTORY_TAB,
        SOURCE_HISTORY_MIRROR_TAB,
        SOURCE_PRIVATE_CONFIG_TAB,
        "MB_FINAL_DECISION_CURRENT",
        "MB_RUN_LOG",
        "MB_Method_Outputs_Current",
        "MB_Top_Candidates_Current",
    }
    missing = sorted(required - spreadsheet_titles(service, SOURCE_SHEET_ID))
    if missing:
        raise DailyFourSoError(f"Canonical source is missing tabs: {missing}")

    def read(tab: str) -> list[list[str]]:
        values = get_values(service, SOURCE_SHEET_ID, f"{quote_tab(tab)}!A1:AB2500")
        return normalize_history(values)

    history = read(SOURCE_HISTORY_TAB)
    mirror = read(SOURCE_HISTORY_MIRROR_TAB)
    if history != mirror:
        raise DailyFourSoError("MB_History_27 and its import mirror differ")

    existing = [row for row in history if row[0] == lock_date.isoformat()]
    if existing:
        if len(existing) != 1 or existing[0] != local_row:
            raise DailyFourSoError("Canonical source conflicts with the cross-checked public row")
    else:
        latest = date.fromisoformat(history[-1][0])
        if latest != lock_date - timedelta(days=1):
            raise DailyFourSoError(f"Cannot append {lock_date}; canonical source ends at {latest}")
        for tab in (SOURCE_HISTORY_TAB, SOURCE_HISTORY_MIRROR_TAB):
            append_values(service, SOURCE_SHEET_ID, f"{quote_tab(tab)}!A:AB", [local_row])
        history = read(SOURCE_HISTORY_TAB)
        mirror = read(SOURCE_HISTORY_MIRROR_TAB)
        if history != mirror or history[-1] != local_row:
            raise DailyFourSoError("Source-history append readback failed")

    locked = [row for row in history if row[0] <= lock_date.isoformat()]
    if not locked or locked[-1][0] != lock_date.isoformat():
        raise DailyFourSoError("Canonical history is not locked exactly through T-1")
    return locked


def find_existing_fourso_ledger(rows: list[list[Any]], target: date) -> list[tuple[int, list[Any]]]:
    matches: list[tuple[int, list[Any]]] = []
    for row_number, raw in enumerate(rows, start=6):
        row = pad(raw, 11)
        if parse_date(row[0]) == target and str(row[1]).strip().upper() == "4SO":
            matches.append((row_number, row))
    return matches


def settle_paid_report(
    service,
    pnl_sheet_id: str,
    paid_sheet_id: str,
    lock_date: date,
    target_date: date,
    result_codes: Sequence[str],
) -> None:
    if PNL_TAB not in spreadsheet_titles(service, pnl_sheet_id):
        raise DailyFourSoError(f"P/L workbook is missing tab {PNL_TAB}")
    if PAID_REPORT_TAB not in spreadsheet_titles(service, paid_sheet_id):
        raise DailyFourSoError(f"Paid workbook is missing tab {PAID_REPORT_TAB}")

    paid_rows = get_values(service, paid_sheet_id, f"{quote_tab(PAID_REPORT_TAB)}!A1:G3")
    if len(paid_rows) < 2:
        raise DailyFourSoError("Paid_Report has no active report row")
    active = pad(paid_rows[1], 7)
    active_date = parse_date(active[0])
    if active_date not in {lock_date, target_date}:
        raise DailyFourSoError(f"Paid_Report date {active[0]!r} is neither T-1 nor T")

    ledger_rows = get_values(service, pnl_sheet_id, f"{quote_tab(PNL_TAB)}!A6:K1005")
    existing = find_existing_fourso_ledger(ledger_rows, lock_date)
    if len(existing) > 1:
        raise DailyFourSoError(f"P/L ledger has duplicate 4SO rows for {lock_date}")
    if existing:
        if active_date == lock_date:
            old_codes = [str(value).zfill(2) for value in active[2:6]]
            ledger_codes = re.findall(r"(?<!\d)\d{2}(?!\d)", str(existing[0][1][2]))
            if set(old_codes) != set(ledger_codes):
                raise DailyFourSoError("Existing P/L row conflicts with the previous paid report")
        return
    if active_date == target_date:
        raise DailyFourSoError("Paid report already advanced but previous P/L is missing")

    old_codes = [str(value).zfill(2) for value in active[2:6]]
    previous = settlement(old_codes, result_codes)
    used_rows = [
        number
        for number, raw in enumerate(ledger_rows, start=6)
        if any(str(value).strip() for value in pad(raw, 2)[:2])
    ]
    row_number = max(used_rows, default=5) + 1
    if row_number > 1005:
        raise DailyFourSoError("P/L ledger is full")

    hit_codes = [code for code in old_codes if previous["hits"][code] > 0]
    hit_text = ", ".join(hit_codes) if hit_codes else "Không trúng"
    detail = (
        "; ".join(f"{code} × {previous['hits'][code]}" for code in hit_codes)
        if hit_codes else "—"
    )
    pnl = int(previous["pnl_vnd"])
    note = (
        f"Tự động quyết toán 4SO ngày {vi_date(lock_date)} lúc 00:05. "
        f"Báo cáo đã khóa trước kết quả gồm {', '.join(old_codes)}, mỗi số "
        f"{POINTS_PER_CODE} điểm; kết quả nguồn đủ 27/27; tổng "
        f"{previous['total_hits']} nháy; vốn {previous['capital_vnd']:,}đ; "
        f"trả thưởng {previous['payout_vnd']:,}đ; P/L {pnl:+,}đ. "
        "SOURCE_METHOD=4SO; AUTO_SETTLED_00_05; outcome_known_at_selection=false."
    )
    values = [[
        vi_date(lock_date), "4SO", ", ".join(old_codes), hit_text, detail,
        previous["total_hits"], previous["points"], pnl,
        f'=IF(COUNTA(A{row_number}:C{row_number};H{row_number})=0;"";SUM($H$6:H{row_number}))',
        f'=IF(H{row_number}="";"";IF(H{row_number}>0;"Thắng";IF(H{row_number}<0;"Thua";"Hòa")))',
        note,
    ]]
    update_values(
        service, pnl_sheet_id, f"{quote_tab(PNL_TAB)}!A{row_number}:K{row_number}", values
    )
    readback = get_values(
        service, pnl_sheet_id, f"{quote_tab(PNL_TAB)}!A{row_number}:K{row_number}"
    )
    if not readback or parse_date(readback[0][0]) != lock_date:
        raise DailyFourSoError("P/L settlement readback failed")


def append_if_missing(
    service,
    tab: str,
    last_column: str,
    identity: Callable[[list[Any]], bool],
    verify: Callable[[list[Any]], bool],
    row: list[Any],
) -> None:
    values = get_values(service, SOURCE_SHEET_ID, f"{quote_tab(tab)}!A1:{last_column}")
    width = len(values[0])
    matches = [raw for raw in values[1:] if identity(pad(raw, width))]
    if len(matches) > 1:
        raise DailyFourSoError(f"{tab} contains duplicate automation identity")
    if matches:
        if not verify(pad(matches[0], width)):
            raise DailyFourSoError(f"{tab} existing row conflicts with computed MB 4SO")
        return
    append_values(service, SOURCE_SHEET_ID, f"{quote_tab(tab)}!A:{last_column}", [row])


def record_private_run(
    service,
    target_date: date,
    lock_date: date,
    ranked: Sequence[PairScore],
    history_rows: Sequence[Sequence[str]],
) -> None:
    now = datetime.now(VN).replace(microsecond=0).isoformat()
    run_id = f"MB_4SO_AUTO_{target_date:%Y%m%d}_0005"
    score_vector_id = f"MB_4SO_TOP45_{target_date:%Y%m%d}"
    top = list(ranked[:4])
    artifact_hash = digest({
        "schema": "MB_4SO_DAILY_AUTO_V1",
        "target": target_date.isoformat(),
        "lock": lock_date.isoformat(),
        "history_hash": digest(history_rows),
        "top4": [asdict(item) for item in top],
        "config": CONFIG_ID,
        "algorithm": ALGORITHM_ID,
    })

    final_row: list[Any] = [
        target_date.isoformat(), lock_date.isoformat(), now, run_id, CONFIG_ID,
        ALGORITHM_ID, "MB_4SO_V1 > TOP2_REVERSE_PAIRS > AUTO_00_05",
        "LOCKED_27_27_HASH_MATCH", "PAID_REPORT_PRIVATE_FIXED50", "FALSE", "FALSE",
        top[0].pair, top[0].score, 100, top[1].pair, top[1].score, 100,
        top[2].pair, top[2].score, 0, top[3].pair, top[3].score, 0,
        200, 4_600_000, "PAID_REPORT_READY: TOP1 + TOP2",
    ]
    append_if_missing(
        service, "MB_FINAL_DECISION_CURRENT", "Z",
        lambda row: parse_date(row[0]) == target_date and str(row[5]) == ALGORITHM_ID,
        lambda row: str(row[11]) == top[0].pair and str(row[14]) == top[1].pair,
        final_row,
    )

    method_row: list[Any] = [
        target_date.isoformat(), lock_date.isoformat(), run_id, METHOD_ID,
        "PRODUCTION_CANONICAL", f"{top[0].pair}|{top[1].pair}", score_vector_id,
        "TOP2_REVERSE_PAIRS", "TRUE", 1, CONFIG_ID, artifact_hash,
        "PUBLISHED_PASS_PRIVATE", "45/45 pairs; private paid delivery; automatic 00:05 run.",
    ]
    append_if_missing(
        service, "MB_Method_Outputs_Current", "N",
        lambda row: str(row[2]) == run_id and str(row[3]) == METHOD_ID,
        lambda row: str(row[5]) == method_row[5], method_row,
    )

    candidate_rows: list[list[Any]] = []
    for rank, item in enumerate(top, start=1):
        candidate_rows.append([
            target_date.isoformat(), lock_date.isoformat(), run_id, score_vector_id,
            rank, item.pair, item.score, "", f"RANK_{rank}", "FALSE",
            100 if rank <= 2 else 0, "FALSE",
            "TOP2_PAIR_PRIVATE" if rank <= 2 else "AUDIT_ONLY_NO_FUND",
            "Canonical automatic 00:05 ranking.",
        ])
    candidate_values = get_values(
        service, SOURCE_SHEET_ID, "'MB_Top_Candidates_Current'!A1:N500"
    )
    existing_candidates = [
        pad(row, 14) for row in candidate_values[1:] if str(pad(row, 14)[2]) == run_id
    ]
    if existing_candidates:
        if [str(row[5]) for row in existing_candidates] != [item.pair for item in top]:
            raise DailyFourSoError("Existing candidate ranking conflicts with computed output")
    else:
        append_values(
            service, SOURCE_SHEET_ID, "'MB_Top_Candidates_Current'!A:N", candidate_rows
        )

    run_row: list[Any] = [
        now, target_date.isoformat(), lock_date.isoformat(), run_id, CONFIG_ID,
        f"AUTO MB 4SO {vi_date(target_date)} AT 00:05", 27, "FALSE", METHOD_ID,
        METHOD_ID, "challengers_weight_0", 45, 45, "FALSE",
        "PAID_REPORT_READY_FIXED50", "PRIVATE_PAID_REPORT", 200, 4_600_000,
        "AUTO_00_05_PRIVATE", "PASS_27_27_TIE_NO_LOOKAHEAD_READBACK",
        artifact_hash, "Paid codes remain outside the public repository.",
    ]
    append_if_missing(
        service, "MB_RUN_LOG", "V",
        lambda row: str(row[3]) == run_id,
        lambda row: str(row[1]) == target_date.isoformat() and str(row[20]) == artifact_hash,
        run_row,
    )


def update_paid_report(
    service,
    paid_sheet_id: str,
    target_date: date,
    lock_date: date,
    ranked: Sequence[PairScore],
) -> None:
    top1, top2 = ranked[0], ranked[1]
    expected = [
        vi_date(target_date), vi_date(lock_date), top1.left, top1.right,
        top2.left, top2.right,
    ]
    current_rows = get_values(
        service, paid_sheet_id, f"{quote_tab(PAID_REPORT_TAB)}!A1:G3"
    )
    current = pad(current_rows[1] if len(current_rows) > 1 else [], 7)
    current_date = parse_date(current[0])
    if current_date == target_date:
        if [str(value) for value in current[:6]] != expected:
            raise DailyFourSoError("Existing Paid_Report target conflicts with canonical output")
        return
    if current_date != lock_date:
        raise DailyFourSoError("Paid_Report did not advance from exactly T-1")

    stamp = datetime.now(VN).strftime("%d/%m/%Y %H:%M Asia/Saigon")
    update_values(
        service, paid_sheet_id, f"{quote_tab(PAID_REPORT_TAB)}!A2:G2",
        [[*expected, stamp]],
    )
    readback = get_values(
        service, paid_sheet_id, f"{quote_tab(PAID_REPORT_TAB)}!A2:G2"
    )
    if not readback or [str(value) for value in pad(readback[0], 7)[:6]] != expected:
        raise DailyFourSoError("Paid_Report readback failed")


def sync_google(lock_date: date, target_date: date) -> None:
    if target_date != lock_date + timedelta(days=1):
        raise DailyFourSoError("Target must be exactly the day after DATA_LOCK")
    if lock_date >= datetime.now(VN).date():
        raise DailyFourSoError("DATA_LOCK must be a completed day before today")

    service = sheets_service()
    local_row = local_lock_row(lock_date)
    history = sync_source_history(service, lock_date, local_row)
    ranked = score_reverse_pairs(history)
    pnl_sheet_id, paid_sheet_id = private_sheet_ids(service)

    # Fail-closed order: settle old report, persist new run, replace Paid_Report last.
    settle_paid_report(
        service, pnl_sheet_id, paid_sheet_id, lock_date, target_date, local_row[1:]
    )
    record_private_run(service, target_date, lock_date, ranked, history)
    update_paid_report(service, paid_sheet_id, target_date, lock_date, ranked)
    print(
        "MB4SO_DAILY_SYNC_OK "
        f"lock={lock_date.isoformat()} target={target_date.isoformat()} "
        "source=27/27 pairs=45 paid_codes=PRIVATE"
    )


def self_test() -> None:
    assert rank_pct_average([1, 1, 3]) == [0.5, 0.5, 1.0]
    example = settlement(["06", "60", "38", "83"], ["60", *(["00"] * 26)])
    assert example["total_hits"] == 1
    assert example["capital_vnd"] == 4_600_000
    assert example["payout_vnd"] == 4_000_000
    assert example["pnl_vnd"] == -600_000
    rows = normalize_history(load_history()["rows"])
    locked = [row for row in rows if row[0] <= "2026-08-07"]
    ranked = score_reverse_pairs(locked)
    assert [item.pair for item in ranked[:2]] == ["19-91", "06-60"]
    print("MB4SO_SELF_TEST_OK")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    sync = sub.add_parser("sync-google")
    sync.add_argument("--lock-date", required=True)
    sync.add_argument("--target-date", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "self-test":
        self_test()
        return 0
    try:
        lock_date = date.fromisoformat(args.lock_date)
        target_date = date.fromisoformat(args.target_date)
    except ValueError as exc:
        raise DailyFourSoError("Dates must use YYYY-MM-DD") from exc
    sync_google(lock_date, target_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
