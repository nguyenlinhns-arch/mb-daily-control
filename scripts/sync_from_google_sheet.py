#!/usr/bin/env python3
"""Đồng bộ kết quả XSMB mới nhất từ Google Sheet sang data/current.json.

Quy trình an toàn:
- Chỉ nhận kỳ có đủ 27 giải.
- Tự tính unique, mã lặp và mức nhiễu.
- Nếu có actual_order ở trạng thái PENDING cùng ngày, tự chốt lô + xiên 2.
- Khi nguồn thay đổi, tự tính delta để không cộng lãi/lỗ hai lần.
"""
from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "current.json"
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w")
EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
VN = timezone(timedelta(hours=7))


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def code2(value):
    if value is None or value == "":
        return None
    try:
        text = str(int(float(value)))
    except (TypeError, ValueError):
        text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[-2:].zfill(2) if digits else None


def latest_draw(xlsx_path: str):
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    for name in ("Raw_Results_2024_2026", "Lo_Toan_Bang_2024_2026", "Raw_Results_IMPORT", "Raw_2Digits_IMPORT"):
        if name not in wb.sheetnames:
            continue
        ws = wb[name]
        best = None
        for row in ws.iter_rows(min_row=3, values_only=True):
            d = as_date(row[0])
            codes = [code2(v) for v in row[1:28]]
            if d and len(codes) == 27 and all(codes):
                if best is None or d > best[0]:
                    best = (d, codes)
        if best:
            return best
    raise RuntimeError("Không tìm thấy kỳ hợp lệ đủ 27 mã trong Google Sheet")


def settle_order(doc, draw_date, codes):
    order = doc.get("actual_order") or {}
    if order.get("date") != draw_date.isoformat():
        return False
    if "PENDING" not in str(order.get("status", "")) and order.get("pnl_included"):
        # Vẫn cho phép sửa kết quả nguồn: tính lại và áp delta.
        pass

    freq = Counter(codes)
    lo = order.setdefault("lo", {})
    numbers = [str(x).zfill(2) for x in lo.get("numbers", [])]
    points = int(lo.get("points_per_code", 50))
    cost_pp = int(doc.get("stake_rule", {}).get("lo_cost_per_point_vnd", 23000))
    pay_pp = int(doc.get("stake_rule", {}).get("lo_payout_per_hit_point_vnd", 80000))
    hits = {n: freq.get(n, 0) for n in numbers}
    lo_capital = len(numbers) * points * cost_pp
    lo_payout = sum(hits.values()) * points * pay_pp
    lo_pnl = lo_payout - lo_capital

    xien = order.setdefault("xien2", {})
    pairs = xien.get("pairs") or [f"{a}-{b}" for a, b in combinations(numbers, 2)]
    pair_capital = int(doc.get("stake_rule", {}).get("xien2_capital_per_pair_vnd", 100000))
    pair_return = int(doc.get("stake_rule", {}).get("xien2_gross_return_per_winning_pair_vnd", 1600000))
    winning = [p for p in pairs if all(freq.get(x.zfill(2), 0) > 0 for x in p.split("-"))]
    x_capital = len(pairs) * pair_capital
    x_payout = len(winning) * pair_return
    x_pnl = x_payout - x_capital
    total_pnl = lo_pnl + x_pnl

    old_total = int((doc.get("settlement") or {}).get("total_pnl_vnd", 0)) if order.get("pnl_included") else 0
    delta = total_pnl - old_total

    lo.update({"hits": hits, "code_count": len(numbers), "capital_vnd": lo_capital, "payout_vnd": lo_payout, "pnl_vnd": lo_pnl})
    xien.update({"pairs": pairs, "winning_pairs": winning, "wins": len(winning), "losses": len(pairs)-len(winning), "capital_vnd": x_capital, "payout_vnd": x_payout, "pnl_vnd": x_pnl})
    order.update({
        "status": "REAL_SETTLED_WIN" if total_pnl > 0 else "REAL_SETTLED_LOSS" if total_pnl < 0 else "REAL_SETTLED_EVEN",
        "settled_at": datetime.now(VN).isoformat(timespec="seconds"), "pnl_included": True,
        "total_capital_vnd": lo_capital + x_capital, "total_payout_vnd": lo_payout + x_payout,
        "total_pnl_vnd": total_pnl,
        "note": f"Lô {sum(hits.values())} nháy; Xiên thắng {len(winning)}/{len(pairs)} cặp."
    })

    doc["settlement"] = {"date": draw_date.isoformat(), "result_codes": codes, "lo_hits_total": sum(hits.values()), "xien_wins": len(winning), "lo_pnl_vnd": lo_pnl, "xien_pnl_vnd": x_pnl, "total_pnl_vnd": total_pnl}
    q = doc.setdefault("pnl_summary", {})
    for key in ("active_five_group_pnl_vnd", "active_all_real_pnl_vnd", "grand_total_pnl_vnd"):
        if key in q:
            q[key] = int(q[key]) + delta
    q.update({"confirmed_through": draw_date.isoformat(), "yesterday_date": draw_date.isoformat(), "yesterday_pnl_vnd": total_pnl, "yesterday_hits": sum(hits.values()), "today_pending_capital_vnd": 0, "today_pending_order": f"Đã chốt P/L ngày: {total_pnl:+,}đ".replace(",", "."), "today_included": True})

    doc["portfolio"] = {"decision":"SETTLED_ACTUAL_ORDER", "tier":"KẾT QUẢ ĐÃ KHÓA", "selection":"-".join(numbers), "title":f"KẾT QUẢ {draw_date.strftime('%d/%m')}: {total_pnl:+,}đ".replace(",", "."), "points":points*len(numbers)+100*len(pairs), "capital_vnd":lo_capital+x_capital, "payout_vnd":lo_payout+x_payout, "pnl_vnd":total_pnl, "reason":order["note"], "pnl_status":"SETTLED"}

    methods = []
    methods.append({"id":"USER_LO","label":"Lô thực chiến","method":f"{len(numbers)} số ×{points} điểm","status":order["status"],"points_per_code":points,"code_count":len(numbers),"capital_vnd":lo_capital,"numbers":[{"code":n,"points":points,"capital_vnd":points*cost_pp,"role":f"{hits[n]} nháy · {(hits[n]*points*pay_pp-points*cost_pp):+,}đ".replace(",", ".")} for n in numbers]})
    methods.append({"id":"USER_XIEN2","label":"Xiên 2 thực chiến","method":f"{len(pairs)} cặp ×100 điểm","status":"SETTLED_WIN" if winning else "SETTLED_LOSS","points_per_code":100,"code_count":len(pairs),"capital_vnd":x_capital,"numbers":[{"code":p,"points":100,"capital_vnd":pair_capital,"role":("Trúng" if p in winning else "Trượt")} for p in pairs]})
    doc["top_signals"] = {"title":"KẾT QUẢ THỰC CHIẾN ĐÃ CHỐT","subtitle":f"Lô {lo_pnl:+,}đ · Xiên 2 {x_pnl:+,}đ · Tổng {total_pnl:+,}đ".replace(",", "."),"total_methods":2,"total_numbers":f"{len(numbers)} số + {len(pairs)} cặp","total_points":f"{points*len(numbers)} lô + {100*len(pairs)} xiên","total_capital_vnd":lo_capital+x_capital,"note":order["note"],"methods":methods}
    return True


def main():
    with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
        req = urllib.request.Request(EXPORT_URL, headers={"User-Agent":"MB-Daily-Control/1.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            tmp.write(r.read())
            tmp.flush()
        draw_date, codes = latest_draw(tmp.name)

    doc = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    counts = Counter(codes)
    repeats = [f"{c}×{n}" for c, n in sorted(counts.items()) if n > 1]
    doc["target_date"] = draw_date.isoformat()
    doc["generated_at"] = datetime.now(VN).isoformat(timespec="seconds")
    doc["data_snapshot_id"] = f"AUTO_{draw_date.strftime('%Y%m%d')}_{len(counts)}U"
    doc["data"] = {"locked_through":draw_date.isoformat(),"status":"LOCKED_AUTO_GOOGLE_SHEET","count":27,"unique":len(counts),"repeat2_count":sum(1 for n in counts.values() if n>=2),"repeat_codes":repeats,"max_frequency":max(counts.values()),"noise_status":"STRONG_NOISE" if max(counts.values())>=3 or sum(1 for n in counts.values() if n>=2)>=3 else "NORMAL","latest_27_codes":codes,"source_label":f"Google Sheet XSMB · khóa tự động {draw_date.strftime('%d/%m/%Y')} · đủ 27/27"}
    settle_order(doc, draw_date, codes)
    DATA_FILE.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Synced {draw_date}: {','.join(codes)}")


if __name__ == "__main__":
    main()
