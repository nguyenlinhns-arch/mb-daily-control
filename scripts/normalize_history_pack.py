#!/usr/bin/env python3
"""Normalize the packed public XSMB history to the canonical {"rows": [...]} container.

The statistics mirror sync accepts/produces a compact list payload, while the
completed-draw pipeline historically consumes a mapping with a ``rows`` key.
This bridge is deliberately lossless: it validates the same date + 27-code row
shape and only wraps a legacy list container. It never changes draw values.
"""
from __future__ import annotations

import argparse
import base64
import bz2
import json
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "data" / "history-27.bz2.b64"


def decode(path: Path) -> tuple[dict[str, Any], bool]:
    packed = "".join(path.read_text(encoding="utf-8").split())
    raw = bz2.decompress(base64.b64decode(packed, validate=True))
    payload = json.loads(raw.decode("utf-8-sig"))
    if isinstance(payload, list):
        doc: dict[str, Any] = {"rows": payload}
        legacy = True
    elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        doc = payload
        legacy = False
    else:
        raise ValueError("History pack must be a row list or an object containing rows")
    validate_rows(doc["rows"])
    return doc, legacy


def validate_rows(rows: list[Any]) -> None:
    if len(rows) < 500:
        raise ValueError(f"History too short: {len(rows)}")
    previous: date | None = None
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 28:
            raise ValueError(f"Invalid history row {index}: expected date + 27 codes")
        day = date.fromisoformat(str(row[0]))
        codes = [str(value) for value in row[1:]]
        if any(re.fullmatch(r"\d{2}", code) is None for code in codes):
            raise ValueError(f"Invalid two-digit code at row {index}")
        if previous is not None and day <= previous:
            raise ValueError(f"History is not strictly increasing at {day}")
        previous = day


def encode(doc: dict[str, Any]) -> str:
    raw = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(bz2.compress(raw, compresslevel=9)).decode("ascii") + "\n"


def normalize(path: Path) -> bool:
    doc, legacy = decode(path)
    if not legacy:
        return False
    path.write_text(encode(doc), encoding="utf-8")
    check, check_legacy = decode(path)
    if check_legacy or check["rows"] != doc["rows"]:
        raise ValueError("History pack readback mismatch after normalization")
    return True


def self_test() -> None:
    rows = []
    start = date(2024, 1, 1)
    for offset in range(500):
        day = date.fromordinal(start.toordinal() + offset)
        rows.append([day.isoformat(), *[f"{value % 100:02d}" for value in range(27)]])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.bz2.b64"
        raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        path.write_text(base64.b64encode(bz2.compress(raw)).decode("ascii") + "\n", encoding="utf-8")
        assert normalize(path) is True
        doc, legacy = decode(path)
        assert legacy is False and doc["rows"] == rows
        assert normalize(path) is False
    print("HISTORY_PACK_NORMALIZER_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    changed = normalize(args.pack)
    doc, legacy = decode(args.pack)
    print(json.dumps({
        "status": "PASS",
        "normalized": changed,
        "legacy_after": legacy,
        "history_rows": len(doc["rows"]),
        "history_start": doc["rows"][0][0],
        "history_end": doc["rows"][-1][0],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
