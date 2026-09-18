"""Typed fail-closed ledger contract for MB TOP2+ production.

This module is deliberately policy-neutral: it does not choose numbers, tune weights,
or change HOT/COLD/THIRD thresholds. It only validates causal, reproducible input
before score/freeze/settlement so malformed or incomplete rows cannot silently become A0.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal, Sequence

Action = Literal["A0", "A1", "A2", "RUN_INVALID_NO_BET"]
VALID_ACTIONS = ("A0", "A1", "A2", "RUN_INVALID_NO_BET")


@dataclass(frozen=True)
class Forecast:
    method_id: str
    target_date: date
    data_lock: date
    action: Action
    codes: tuple[str, ...]
    evidence: str


def _parse_iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be ISO YYYY-MM-DD text")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO YYYY-MM-DD text") from exc


def _validate_code(value: Any) -> str:
    if not (isinstance(value, str) and len(value) == 2 and value.isascii() and value.isdigit()):
        raise ValueError("Each code must be an exact two-digit ASCII string; preserve 00")
    return value


def validate_forecast(obj: dict[str, Any], *, require_exact_t_minus_1: bool = False) -> Forecast:
    """Validate one natural method output without guessing or coercion."""
    required = {"method_id", "target_date", "data_lock", "action", "codes", "evidence"}
    if not required.issubset(obj):
        raise ValueError(f"Missing fields: {sorted(required - set(obj))}")
    target = _parse_iso_date(obj["target_date"], "target_date")
    lock = _parse_iso_date(obj["data_lock"], "data_lock")
    if lock >= target:
        raise ValueError("Data lock must precede target")
    if require_exact_t_minus_1 and lock != target - timedelta(days=1):
        raise ValueError("Production Data Lock must equal T-1")

    action = obj["action"]
    if action not in VALID_ACTIONS:
        raise ValueError("Missing/unknown is not A0; use RUN_INVALID_NO_BET with evidence")
    codes = obj["codes"]
    if not isinstance(codes, list):
        raise ValueError("Codes must be a list, never a scalar/decimal or comma-separated display string")
    clean_codes = tuple(_validate_code(v) for v in codes)
    if len(set(clean_codes)) != len(clean_codes):
        raise ValueError("Duplicate codes; executor must settle its own documented dedupe rule")
    expected = {"A0": 0, "A1": 1, "A2": 2, "RUN_INVALID_NO_BET": 0}[action]
    if len(clean_codes) != expected:
        raise ValueError("Action / leg-count mismatch")
    if not isinstance(obj["method_id"], str) or not obj["method_id"].strip():
        raise ValueError("Method identity is required")
    if not isinstance(obj["evidence"], str) or not obj["evidence"].strip():
        raise ValueError("Provenance evidence is required")
    return Forecast(obj["method_id"].strip(), target, lock, action, clean_codes, obj["evidence"].strip())


def validate_run(
    rows: Sequence[dict[str, Any]],
    *,
    target_date: str,
    data_lock: str,
    expected_method_ids: Sequence[str] | None = None,
    expected_count: int = 67,
) -> list[Forecast]:
    """Validate the complete 67-row daily ledger before scoring/freeze."""
    target = _parse_iso_date(target_date, "target_date")
    lock = _parse_iso_date(data_lock, "data_lock")
    if lock != target - timedelta(days=1):
        raise ValueError("Production Data Lock must equal T-1")
    if len(rows) != expected_count:
        raise ValueError(f"Expected exactly {expected_count} method rows, got {len(rows)}")

    forecasts = [validate_forecast(dict(row), require_exact_t_minus_1=True) for row in rows]
    ids = [f.method_id for f in forecasts]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate method_id in daily run")
    if any(f.target_date != target or f.data_lock != lock for f in forecasts):
        raise ValueError("Run rows disagree on target/data lock")

    if expected_method_ids is not None:
        expected = list(expected_method_ids)
        if len(expected) != expected_count or len(set(expected)) != expected_count:
            raise ValueError("Authority method list must contain exactly 67 unique ids")
        if ids != expected:
            raise ValueError("Method order/identity mismatch against authority registry")
    return forecasts


def google_cells(f: Forecast) -> list[dict[str, Any]]:
    """Safe Google updateCells values; never locale-sensitive USER_ENTERED CSV."""
    return [
        {"userEnteredValue": {"stringValue": f.method_id}},
        {"userEnteredValue": {"stringValue": f.target_date.isoformat()}},
        {"userEnteredValue": {"stringValue": f.data_lock.isoformat()}},
        {"userEnteredValue": {"stringValue": f.action}},
        {"userEnteredValue": {"stringValue": f.codes[0] if f.codes else ""}},
        {"userEnteredValue": {"stringValue": f.codes[1] if len(f.codes) > 1 else ""}},
        {"userEnteredValue": {"numberValue": len(f.codes)}},
        {"userEnteredValue": {"stringValue": ", ".join(f.codes) if f.codes else f.action}},
        {"userEnteredValue": {"stringValue": f.evidence}},
    ]


def validate_draw_tails(tails: Sequence[Any]) -> tuple[str, ...]:
    if len(tails) != 27:
        raise ValueError("Settlement requires exactly 27 result tails")
    return tuple(_validate_code(v) for v in tails)


def settle(
    f: Forecast,
    result_date: date,
    tails: list[str],
    *,
    points: int = 10,
    cost_per_point: int = 27000,
    payout_per_point: int = 99500,
) -> dict[str, Any]:
    if result_date != f.target_date:
        raise ValueError("Settlement date mismatch")
    clean_tails = validate_draw_tails(tails)
    if points <= 0 or cost_per_point < 0 or payout_per_point < 0:
        raise ValueError("Invalid economics")
    if f.action == "RUN_INVALID_NO_BET":
        return dict(outcome="UNAVAILABLE", signal=False, pl=None, occurrences=None)
    if f.action == "A0":
        return dict(outcome="A0", signal=False, pl=0, occurrences=0)
    ct = Counter(clean_tails)
    occ = sum(ct[n] for n in f.codes)
    stake = len(f.codes) * points * cost_per_point
    pay = occ * points * payout_per_point
    return dict(
        outcome="WIN" if pay > stake else ("LOSS" if pay < stake else "BREAKEVEN"),
        signal=True,
        stake=stake,
        payout=pay,
        pl=pay - stake,
        occurrences=occ,
    )


def signal_window(records: list[dict[str, Any]], n: int) -> dict[str, Any]:
    """Use last N actual signal sessions; A0 does not consume a slot."""
    if n < 1:
        raise ValueError("n must be positive")
    selected: list[dict[str, Any]] = []
    unknown = 0
    for r in reversed(records):
        if r.get("pl") is None or r.get("outcome") in ("UNKNOWN", "UNAVAILABLE"):
            unknown += 1
            continue
        if not r.get("signal"):
            continue
        selected.append(r)
        if len(selected) == n:
            break
    return dict(
        observed_signals=len(selected),
        observed_wins=sum(r["pl"] > 0 for r in selected),
        observed_pl=sum(r["pl"] for r in selected),
        unknown_sessions=unknown,
        certified=unknown == 0 and len(selected) == n,
    )


def assert_route_authority(*, target_date: str, engine_or_policy: str) -> None:
    """Hard stop for superseded FUSION67/R6 production route from 17/09/2026."""
    target = _parse_iso_date(target_date, "target_date")
    policy = (engine_or_policy or "").upper()
    if target >= date(2026, 9, 17) and any(token in policy for token in ("FUSION67", "ALL67_NO_META", "R6")):
        raise ValueError(
            "RUN_CONTROL_FAIL: FUSION67/R6 ALL67_NO_META is SHADOW/AUDIT only from target 2026-09-17; "
            "production authority is V4.1 ROLE-CORE"
        )
