#!/usr/bin/env python3
"""Refresh the public statistics history from MB_History_27, fail closed.

This script is deliberately separate from the canonical MB 4SO executor. It
only mirrors completed 27-code draw history for descriptive public statistics.
The existing packed history must match every overlapping day; historical
rewrites require manual review instead of being silently accepted.
"""
from __future__ import annotations

import argparse
import base64
import bz2
import csv
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "data" / "history-27.bz2.b64"
DEFAULT_LOCK = ROOT / "data" / "source-access.json"
SHEET_ID = "1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w"
SHEET_NAME = "MB_History_27"
SHEET_GID = "2026070407"


def code2(value: object) -> str:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not text:
        raise ValueError(f"Mã không hợp lệ: {value!r}")
    return text[-2:].zfill(2)


def parse_day(value: object) -> date | None:
    text = str(value or "").strip()
    for candidate in (text[:10], text):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            pass
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                pass
    return None


def parse_rows(rows: list[list[str]]) -> list[tuple[date, list[str]]]:
    found: dict[date, list[str]] = {}
    for row in rows:
        if len(row) < 28:
            continue
        day = parse_day(row[0])
        if day is None:
            continue
        codes = [code2(value) for value in row[1:28]]
        if len(codes) != 27:
            raise ValueError(f"{day}: cần đúng 27 mã")
        if day in found and found[day] != codes:
            raise ValueError(f"{day}: trùng ngày nhưng khác dữ liệu")
        found[day] = codes
    return sorted(found.items())


def decode_pack(path: Path) -> list[tuple[date, list[str]]]:
    packed = "".join(path.read_text(encoding="utf-8").split())
    text = bz2.decompress(base64.b64decode(packed)).decode("utf-8-sig")
    payload = json.loads(text)
    if isinstance(payload, dict):
        for key in ("values", "rows", "history", "data", "records"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise ValueError("Pack lịch sử không chứa mảng dữ liệu")
    rows: list[list[str]] = []
    for raw in payload:
        if isinstance(raw, list) and len(raw) >= 28:
            rows.append([str(x) for x in raw[:28]])
        elif isinstance(raw, dict):
            day = raw.get("date") or raw.get("draw_date") or raw.get("ngay")
            codes = raw.get("codes") or raw.get("values") or raw.get("lottery_codes")
            if isinstance(codes, list) and len(codes) == 27:
                rows.append([str(day), *[str(x) for x in codes]])
            else:
                keys = [f"L{i:02d}" for i in range(1, 28)]
                if day and all(k in raw for k in keys):
                    rows.append([str(day), *[str(raw[k]) for k in keys]])
    history = parse_rows(rows)
    if len(history) < 60:
        raise ValueError(f"Pack lịch sử quá ngắn: {len(history)}")
    return history


def fetch_csv(sheet_id: str) -> tuple[list[tuple[date, list[str]]], str]:
    quoted = urllib.parse.quote(SHEET_NAME)
    urls = [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={quoted}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={SHEET_GID}",
    ]
    errors: list[str] = []
    for url in urls:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MB-Public-Statistics/1.0"})
            with urllib.request.urlopen(request, timeout=75) as response:
                body = response.read()
            if len(body) < 10_000:
                raise RuntimeError(f"CSV quá nhỏ: {len(body)} bytes")
            text = body.decode("utf-8-sig")
            rows = list(csv.reader(io.StringIO(text)))
            history = parse_rows(rows)
            if len(history) < 60:
                raise RuntimeError(f"CSV chỉ có {len(history)} kỳ")
            return history, url
        except Exception as exc:  # fail over to the second official export URL
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
    raise RuntimeError("Không đọc được MB_History_27: " + " | ".join(errors))


def encode_pack(history: list[tuple[date, list[str]]]) -> str:
    payload = [[day.isoformat(), *codes] for day, codes in history]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(bz2.compress(raw, compresslevel=9)).decode("ascii") + "\n"


def latest_hash(codes: list[str]) -> str:
    return hashlib.sha256("|".join(codes).encode("utf-8")).hexdigest()


def sync(pack: Path, lock_path: Path, output: Path, sheet_id: str) -> dict[str, object]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if str(lock.get("status", "")).upper() not in {"LOCKED_CROSSCHECKED_PUBLIC", "OK"}:
        raise ValueError(f"Source lock chưa PASS: {lock.get('status')}")
    expected_start = date.fromisoformat(str(lock["history_start"]))
    expected_end = date.fromisoformat(str(lock["history_end"]))
    expected_rows = int(lock["history_rows"])
    expected_latest_hash = str(lock["latest_codes_sha256"]).lower()

    old = decode_pack(pack)
    remote_all, source_url = fetch_csv(sheet_id)
    remote = [(d, c) for d, c in remote_all if expected_start <= d <= expected_end]

    if not remote:
        raise ValueError("Không có dữ liệu trong khoảng source lock")
    if remote[0][0] != expected_start:
        raise ValueError(f"Ngày đầu sai: {remote[0][0]} != {expected_start}")
    if remote[-1][0] != expected_end:
        raise ValueError(f"Ngày cuối sai: {remote[-1][0]} != {expected_end}")
    if len(remote) != expected_rows:
        raise ValueError(f"Số dòng sai: {len(remote)} != {expected_rows}")
    actual_latest_hash = latest_hash(remote[-1][1])
    if actual_latest_hash != expected_latest_hash:
        raise ValueError(f"Hash 27 mã cuối sai: {actual_latest_hash} != {expected_latest_hash}")

    remote_map = dict(remote)
    overlap = 0
    for day, codes in old:
        if day < expected_start or day > expected_end:
            continue
        if day not in remote_map:
            raise ValueError(f"Nguồn mới thiếu ngày cũ {day}")
        if remote_map[day] != codes:
            raise ValueError(f"Lịch sử bị thay đổi tại {day}; yêu cầu review thủ công")
        overlap += 1
    if overlap < min(len(old), expected_rows) - 1:
        raise ValueError(f"Overlap lịch sử bất thường: {overlap}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encode_pack(remote), encoding="utf-8")
    check = decode_pack(output)
    if check != remote:
        raise ValueError("Readback pack sau ghi không khớp")

    return {
        "schema": "MB_PUBLIC_STATS_HISTORY_SYNC_V1",
        "status": "PASS",
        "history_start": expected_start.isoformat(),
        "history_end": expected_end.isoformat(),
        "history_rows": len(remote),
        "latest_codes_sha256": actual_latest_hash,
        "overlap_rows_verified": overlap,
        "source": source_url,
        "output": str(output),
    }


def self_test() -> None:
    assert latest_hash(["78","28","24","34","46","77","18","00","87","63","33","34","81","27","27","47","83","47","35","61","90","58","28","33","66","52","04"]) == "41e396881f43e1a457fbfecf96c9df51660efae6e3476d99d554d3c93fbf3024"
    assert code2(0) == "00" and code2("004") == "04"
    assert parse_day("2026-08-15") == date(2026, 8, 15)
    print("STATISTICS_HISTORY_SYNC_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--output", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--sheet-id", default=os.environ.get("GOOGLE_SHEET_ID", SHEET_ID))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    print(json.dumps(sync(args.pack, args.lock, args.output, args.sheet_id), ensure_ascii=False))


if __name__ == "__main__":
    main()
