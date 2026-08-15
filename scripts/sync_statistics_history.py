#!/usr/bin/env python3
"""Refresh public descriptive XSMB history from the locked crosschecked mirrors.

The canonical Google Sheet remains private. This public-site mirror only accepts
sources already recorded in data/source-access.json, requires the two public
sources to match exactly, verifies the locked date/count/latest-row hash, and
rejects any rewrite of an overlapping day in the existing packed history.
"""
from __future__ import annotations

import argparse
import base64
import bz2
import csv
import hashlib
import io
import json
import re
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "data" / "history-27.bz2.b64"
DEFAULT_LOCK = ROOT / "data" / "source-access.json"
COMMIT_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/commit/([0-9a-f]{7,40})$")


def code2(value: object) -> str:
    text = "".join(ch for ch in str("" if value is None else value) if ch.isdigit())
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


def parse_rows(rows: list[list[object]]) -> list[tuple[date, list[str]]]:
    found: dict[date, list[str]] = {}
    for row in rows:
        if len(row) < 28:
            continue
        day = parse_day(row[0])
        if day is None:
            continue
        codes = [code2(value) for value in row[1:28]]
        if day in found and found[day] != codes:
            raise ValueError(f"{day}: trùng ngày nhưng khác dữ liệu")
        found[day] = codes
    return sorted(found.items())


def decode_pack(path: Path) -> list[tuple[date, list[str]]]:
    packed = "".join(path.read_text(encoding="utf-8").split())
    payload = json.loads(bz2.decompress(base64.b64decode(packed)).decode("utf-8-sig"))
    if isinstance(payload, dict):
        for key in ("values", "rows", "history", "data", "records"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise ValueError("Pack lịch sử không chứa mảng dữ liệu")
    rows: list[list[object]] = []
    for raw in payload:
        if isinstance(raw, list) and len(raw) >= 28:
            rows.append(raw[:28])
        elif isinstance(raw, dict):
            day = raw.get("date") or raw.get("draw_date") or raw.get("ngay")
            codes = raw.get("codes") or raw.get("values") or raw.get("lottery_codes")
            if isinstance(codes, list) and len(codes) == 27:
                rows.append([day, *codes])
            else:
                keys = [f"L{i:02d}" for i in range(1, 28)]
                if day and all(k in raw for k in keys):
                    rows.append([day, *[raw[k] for k in keys]])
    history = parse_rows(rows)
    if len(history) < 60:
        raise ValueError(f"Pack lịch sử quá ngắn: {len(history)}")
    return history


def raw_get(owner: str, repo: str, commit: str, path: str) -> bytes:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "MB-Public-Statistics/1.0"})
    with urllib.request.urlopen(request, timeout=75) as response:
        body = response.read()
    if len(body) < 10_000:
        raise RuntimeError(f"Nguồn {owner}/{repo}:{path} quá nhỏ: {len(body)} bytes")
    return body


def source_ref(source: dict[str, object]) -> tuple[str, str, str]:
    match = COMMIT_RE.fullmatch(str(source.get("url") or ""))
    if not match:
        raise ValueError(f"Commit URL không hợp lệ: {source.get('url')}")
    owner, repo, commit = match.groups()
    expected_name = str(source.get("name") or "").lower()
    if expected_name and expected_name != f"{owner}/{repo}".lower():
        raise ValueError(f"Tên nguồn không khớp URL: {expected_name} != {owner}/{repo}")
    return owner, repo, commit


def load_lucdz(source: dict[str, object]) -> tuple[list[tuple[date, list[str]]], str]:
    owner, repo, commit = source_ref(source)
    body = raw_get(owner, repo, commit, "data/xsmb_history.json")
    payload = json.loads(body.decode("utf-8-sig"))
    rows: list[list[object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        codes = item.get("all_last2")
        if isinstance(codes, list) and len(codes) == 27:
            rows.append([item.get("date"), *codes])
    return parse_rows(rows), f"{owner}/{repo}@{commit}"


def load_khiemdoan(source: dict[str, object]) -> tuple[list[tuple[date, list[str]]], str]:
    owner, repo, commit = source_ref(source)
    body = raw_get(owner, repo, commit, "data/xsmb-2-digits.csv")
    rows = [row for row in csv.reader(io.StringIO(body.decode("utf-8-sig"))) if len(row) >= 28]
    return parse_rows(rows), f"{owner}/{repo}@{commit}"


def load_locked_mirrors(lock: dict[str, object]) -> tuple[list[tuple[date, list[str]]], list[str]]:
    sources = lock.get("sources")
    if not isinstance(sources, list) or len(sources) < 2:
        raise ValueError("Source lock cần ít nhất hai mirror")
    luc = next((s for s in sources if isinstance(s, dict) and str(s.get("name", "")).lower() == "lucdz/xsmb"), None)
    khiem = next((s for s in sources if isinstance(s, dict) and str(s.get("name", "")).lower() == "khiemdoan/vietnam-lottery-xsmb-analysis"), None)
    if luc is None or khiem is None:
        raise ValueError("Thiếu một trong hai mirror public đã khóa")
    one, one_ref = load_lucdz(luc)
    two, two_ref = load_khiemdoan(khiem)
    return compare_sources(one, two), [one_ref, two_ref]


def compare_sources(one: list[tuple[date, list[str]]], two: list[tuple[date, list[str]]]) -> list[tuple[date, list[str]]]:
    one_map, two_map = dict(one), dict(two)
    common = sorted(set(one_map) & set(two_map))
    if len(common) < 60:
        raise ValueError(f"Hai nguồn chỉ trùng {len(common)} ngày")
    for day in common:
        if one_map[day] != two_map[day]:
            raise ValueError(f"Hai nguồn public khác nhau tại {day}")
    return [(day, one_map[day]) for day in common]


def encode_pack(history: list[tuple[date, list[str]]]) -> str:
    payload = [[day.isoformat(), *codes] for day, codes in history]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(bz2.compress(raw, compresslevel=9)).decode("ascii") + "\n"


def latest_hash(codes: list[str]) -> str:
    return hashlib.sha256("|".join(codes).encode("utf-8")).hexdigest()


def sync(pack: Path, lock_path: Path, output: Path) -> dict[str, object]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if str(lock.get("status", "")).upper() != "LOCKED_CROSSCHECKED_PUBLIC":
        raise ValueError(f"Source lock chưa PASS: {lock.get('status')}")
    if int(lock.get("source_count", 0)) < 2:
        raise ValueError("Source lock chưa đủ hai nguồn")
    expected_start = date.fromisoformat(str(lock["history_start"]))
    expected_end = date.fromisoformat(str(lock["history_end"]))
    expected_rows = int(lock["history_rows"])
    expected_latest_hash = str(lock["latest_codes_sha256"]).lower()

    old = decode_pack(pack)
    mirrors, refs = load_locked_mirrors(lock)
    remote = [(d, c) for d, c in mirrors if expected_start <= d <= expected_end]
    if not remote or remote[0][0] != expected_start or remote[-1][0] != expected_end:
        raise ValueError(f"Khoảng ngày sai: {remote[0][0] if remote else None}..{remote[-1][0] if remote else None}")
    if len(remote) != expected_rows:
        raise ValueError(f"Số dòng sai: {len(remote)} != {expected_rows}")
    actual_latest_hash = latest_hash(remote[-1][1])
    if actual_latest_hash != expected_latest_hash:
        raise ValueError(f"Hash 27 mã cuối sai: {actual_latest_hash} != {expected_latest_hash}")
    for source in lock.get("sources") or []:
        if isinstance(source, dict) and source.get("codes_sha256") and str(source["codes_sha256"]).lower() != expected_latest_hash:
            raise ValueError(f"Hash ghi trong source manifest không đồng nhất: {source.get('name')}")

    remote_map = dict(remote)
    overlap = 0
    for day, codes in old:
        if expected_start <= day <= expected_end:
            if day not in remote_map:
                raise ValueError(f"Nguồn mới thiếu ngày cũ {day}")
            if remote_map[day] != codes:
                raise ValueError(f"Lịch sử bị thay đổi tại {day}; yêu cầu review thủ công")
            overlap += 1
    if overlap < min(len(old), expected_rows) - 1:
        raise ValueError(f"Overlap lịch sử bất thường: {overlap}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encode_pack(remote), encoding="utf-8")
    if decode_pack(output) != remote:
        raise ValueError("Readback pack sau ghi không khớp")
    return {
        "schema": "MB_PUBLIC_STATS_HISTORY_SYNC_V2",
        "status": "PASS",
        "history_start": expected_start.isoformat(),
        "history_end": expected_end.isoformat(),
        "history_rows": len(remote),
        "latest_codes_sha256": actual_latest_hash,
        "overlap_rows_verified": overlap,
        "sources": refs,
        "output": str(output),
    }


def self_test() -> None:
    codes = ["78","28","24","34","46","77","18","00","87","63","33","34","81","27","27","47","83","47","35","61","90","58","28","33","66","52","04"]
    assert latest_hash(codes) == "41e396881f43e1a457fbfecf96c9df51660efae6e3476d99d554d3c93fbf3024"
    assert code2(0) == "00" and code2("004") == "04"
    assert parse_day("2026-08-15") == date(2026, 8, 15)
    assert source_ref({"name":"lucdz/xsmb","url":"https://github.com/lucdz/xsmb/commit/686eda641c99018cbeb5c16a038e60af6a54ef7a"}) == ("lucdz","xsmb","686eda641c99018cbeb5c16a038e60af6a54ef7a")
    print("STATISTICS_HISTORY_SYNC_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--output", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    print(json.dumps(sync(args.pack, args.lock, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
