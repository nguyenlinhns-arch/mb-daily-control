from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

START = date(2020, 1, 1)
END = date(2026, 8, 22)
OUT = Path("mn_data")
BASE = "https://xoso.com.vn/xsmn-{:%d-%m-%Y}.html"

CODES = {
    "TPHCM": {"TPHCM", "TP HCM", "TP.HCM", "HO CHI MINH", "TP HO CHI MINH", "THANH PHO HO CHI MINH"},
    "DONG_THAP": {"DONG THAP"},
    "CA_MAU": {"CA MAU"},
    "BEN_TRE": {"BEN TRE"},
    "VUNG_TAU": {"VUNG TAU", "BA RIA VUNG TAU", "BR VT", "BRVT"},
    "BAC_LIEU": {"BAC LIEU"},
    "DONG_NAI": {"DONG NAI"},
    "CAN_THO": {"CAN THO"},
    "SOC_TRANG": {"SOC TRANG"},
    "TAY_NINH": {"TAY NINH"},
    "AN_GIANG": {"AN GIANG"},
    "BINH_THUAN": {"BINH THUAN"},
    "VINH_LONG": {"VINH LONG"},
    "BINH_DUONG": {"BINH DUONG"},
    "TRA_VINH": {"TRA VINH"},
    "LONG_AN": {"LONG AN"},
    "BINH_PHUOC": {"BINH PHUOC"},
    "HAU_GIANG": {"HAU GIANG"},
    "TIEN_GIANG": {"TIEN GIANG"},
    "KIEN_GIANG": {"KIEN GIANG"},
    "DA_LAT": {"DA LAT", "LAM DONG", "DALAT"},
}

NAMES = {
    "TPHCM": "TP.HCM", "DONG_THAP": "Đồng Tháp", "CA_MAU": "Cà Mau", "BEN_TRE": "Bến Tre",
    "VUNG_TAU": "Vũng Tàu", "BAC_LIEU": "Bạc Liêu", "DONG_NAI": "Đồng Nai", "CAN_THO": "Cần Thơ",
    "SOC_TRANG": "Sóc Trăng", "TAY_NINH": "Tây Ninh", "AN_GIANG": "An Giang", "BINH_THUAN": "Bình Thuận",
    "VINH_LONG": "Vĩnh Long", "BINH_DUONG": "Bình Dương", "TRA_VINH": "Trà Vinh", "LONG_AN": "Long An",
    "BINH_PHUOC": "Bình Phước", "HAU_GIANG": "Hậu Giang", "TIEN_GIANG": "Tiền Giang",
    "KIEN_GIANG": "Kiên Giang", "DA_LAT": "Đà Lạt",
}

# Python weekday: Monday=0 ... Sunday=6
SCHEDULE = {
    "TPHCM": {0, 5}, "DONG_THAP": {0}, "CA_MAU": {0},
    "BEN_TRE": {1}, "VUNG_TAU": {1}, "BAC_LIEU": {1},
    "DONG_NAI": {2}, "CAN_THO": {2}, "SOC_TRANG": {2},
    "TAY_NINH": {3}, "AN_GIANG": {3}, "BINH_THUAN": {3},
    "VINH_LONG": {4}, "BINH_DUONG": {4}, "TRA_VINH": {4},
    "LONG_AN": {5}, "BINH_PHUOC": {5}, "HAU_GIANG": {5},
    "TIEN_GIANG": {6}, "KIEN_GIANG": {6}, "DA_LAT": {6},
}

PRIZES = [
    ("special", "DB", 1, 6), ("prize1", "1", 1, 5), ("prize2", "2", 1, 5),
    ("prize3", "3", 2, 5), ("prize4", "4", 7, 5), ("prize5", "5", 1, 4),
    ("prize6", "6", 3, 4), ("prize7", "7", 1, 3), ("prize8", "8", 1, 2),
]

FIELDS = ["date", "weekday", "province_code"] + [
    "special", "prize1", "prize2", "prize3_1", "prize3_2",
    "prize4_1", "prize4_2", "prize4_3", "prize4_4", "prize4_5", "prize4_6", "prize4_7",
    "prize5", "prize6_1", "prize6_2", "prize6_3", "prize7", "prize8",
] + ["signature", "source_url", "qc_status"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def ascii_key(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("Đ", "D").replace("đ", "d").upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s).strip()
    return re.sub(r"\s+", " ", s)


def province_code(name: str) -> str | None:
    k = ascii_key(name)
    for code, aliases in CODES.items():
        if k in aliases:
            return code
    # tolerant contains checks for headers with company words
    for code, aliases in CODES.items():
        if any(a in k for a in aliases if len(a) >= 6):
            return code
    return None


def prize_key(text: str) -> str | None:
    k = ascii_key(text).replace("GIAI ", "").replace("G ", "").strip()
    if "DB" in k or "DAC BIET" in k:
        return "DB"
    m = re.search(r"([1-8])", k)
    return m.group(1) if m else None


def nums(cell) -> List[str]:
    text = cell.get_text(" ", strip=True)
    return re.findall(r"\d+", text)


def fetch_day(d: date) -> Tuple[date, List[dict], List[str]]:
    url = BASE.format(d)
    errors: List[str] = []
    html = None
    for attempt in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200 and len(r.text) > 3000:
                html = r.text
                break
            errors.append(f"HTTP {r.status_code} attempt={attempt+1}")
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")
        time.sleep(0.5 * (attempt + 1))
    if not html:
        return d, [], errors or ["NO_HTML"]

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="table-result")
    if table is None:
        # fallback for slight class variations
        table = soup.find("table", class_=lambda c: c and "result" in str(c).lower())
    if table is None:
        return d, [], errors + ["NO_RESULT_TABLE"]

    trs = table.find_all("tr")
    if not trs:
        return d, [], errors + ["EMPTY_TABLE"]

    header_cells = trs[0].find_all(["th", "td"])
    if len(header_cells) < 2:
        return d, [], errors + ["NO_PROVINCE_HEADER"]
    raw_provinces = [c.get_text(" ", strip=True) for c in header_cells[1:]]
    codes = [province_code(x) for x in raw_provinces]
    if not any(codes):
        return d, [], errors + ["UNKNOWN_PROVINCES:" + "|".join(raw_provinces)]

    by_code: Dict[str, Dict[str, List[str]]] = {c: {} for c in codes if c}
    for tr in trs[1:]:
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        pk = prize_key(cells[0].get_text(" ", strip=True))
        if not pk:
            continue
        for i, code in enumerate(codes):
            if not code or i + 1 >= len(cells):
                continue
            by_code.setdefault(code, {})[pk] = nums(cells[i + 1])

    out: List[dict] = []
    for code, p in by_code.items():
        flat: List[str] = []
        bad: List[str] = []
        rowvals: Dict[str, str] = {}
        for base_name, pk, count, width in PRIZES:
            values = p.get(pk, [])
            if len(values) != count:
                bad.append(f"{pk}:{len(values)}/{count}")
                values = values[:count]
            values = [v.zfill(width)[-width:] for v in values]
            if base_name in ("prize3", "prize4", "prize6"):
                for j, v in enumerate(values, 1):
                    rowvals[f"{base_name}_{j}"] = v
            elif values:
                rowvals[base_name] = values[0]
            flat.extend(values)
        if len(flat) != 18:
            errors.append(f"{code}:INCOMPLETE:{','.join(bad)}")
            continue
        signature = hashlib.sha1("|".join(flat).encode("utf-8")).hexdigest()[:16]
        qc = "OK" if d.weekday() in SCHEDULE[code] else "WARN_WEEKDAY"
        rec = {"date": d.isoformat(), "weekday": d.strftime("%A"), "province_code": code,
               **rowvals, "signature": signature, "source_url": url, "qc_status": qc}
        out.append(rec)
    return d, out, errors


def daterange(a: date, b: date):
    cur = a
    while cur <= b:
        yield cur
        cur += timedelta(days=1)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "provinces").mkdir(parents=True, exist_ok=True)
    dates = list(daterange(START, END))
    records: List[dict] = []
    issues: List[Tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(fetch_day, d): d for d in dates}
        for idx, fut in enumerate(as_completed(futs), 1):
            d, rows, errs = fut.result()
            records.extend(rows)
            for e in errs:
                issues.append((d.isoformat(), e))
            if idx % 100 == 0:
                print(f"processed {idx}/{len(dates)} dates; records={len(records)} issues={len(issues)}", flush=True)

    # exact duplicate date+province protection
    unique: Dict[Tuple[str, str], dict] = {}
    dup_conflicts: List[Tuple[str, str]] = []
    for r in records:
        k = (r["date"], r["province_code"])
        if k in unique and unique[k]["signature"] != r["signature"]:
            dup_conflicts.append(("|".join(k), f"{unique[k]['signature']} != {r['signature']}"))
        unique[k] = r
    records = sorted(unique.values(), key=lambda r: (r["date"], r["province_code"]))

    # remove carry-forward exact signatures on consecutive draws for same province only when date/page parser produced duplicate signature
    # Keep duplicate signatures because random identical full 18 draw is astronomically unlikely; flag but do not silently delete.
    last_sig: Dict[str, Tuple[str, str]] = {}
    carry_flags = []
    for r in records:
        code = r["province_code"]
        if code in last_sig and last_sig[code][1] == r["signature"]:
            carry_flags.append((r["date"], code, r["signature"], last_sig[code][0]))
            r["qc_status"] = "WARN_REPEAT_SIGNATURE"
        last_sig[code] = (r["date"], r["signature"])

    with (OUT / "xsmn_all_20200101_20260822.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(records)

    per_counts = {}
    for code in NAMES:
        rs = [r for r in records if r["province_code"] == code]
        per_counts[code] = len(rs)
        with (OUT / "provinces" / f"{code}.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader(); w.writerows(rs)

    with (OUT / "qc_issues.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["date", "issue"]); w.writerows(issues)
    with (OUT / "qc_repeat_signatures.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["date", "province_code", "signature", "previous_date"]); w.writerows(carry_flags)
    with (OUT / "qc_duplicate_conflicts.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["key", "issue"]); w.writerows(dup_conflicts)

    summary = []
    quality_ok = True
    for code in NAMES:
        rs = [r for r in records if r["province_code"] == code]
        min_date = rs[0]["date"] if rs else ""
        max_date = rs[-1]["date"] if rs else ""
        min_required = 600 if code == "TPHCM" else 300
        status = "OK" if len(rs) >= min_required and min_date <= "2020-02-01" else "FAIL"
        if status != "OK": quality_ok = False
        summary.append({"province_code": code, "province": NAMES[code], "rows": len(rs),
                        "min_date": min_date, "max_date": max_date, "status": status})
    with (OUT / "qc_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["province_code", "province", "rows", "min_date", "max_date", "status"])
        w.writeheader(); w.writerows(summary)

    manifest = {
        "source": "xoso.com.vn date-specific XSMN archive",
        "period": [START.isoformat(), END.isoformat()],
        "rows": len(records),
        "counts": per_counts,
        "issues": len(issues),
        "repeat_signatures": len(carry_flags),
        "duplicate_conflicts": len(dup_conflicts),
        "quality_ok": quality_ok,
        "schema": FIELDS,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)

    if not quality_ok:
        print("QUALITY GATE FAILED", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
