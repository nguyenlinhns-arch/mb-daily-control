#!/usr/bin/env python3
"""Sanitize every public 4SO surface.

Public pages may show aggregate hit/miss performance only. They must not expose
current or historical 4SO selections, hit numbers, pair rankings, scores, or
algorithm details. Internal source evidence stays available to the private
operation; this script controls the GitHub Pages artifact.
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PROOF = ROOT / "data" / "public-historical-proof.json"
SOURCE_YESTERDAY = ROOT / "ai-methods" / "yesterday-proof.json"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def dmy(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def aggregate_proof(source: dict[str, Any]) -> dict[str, Any]:
    validation = source.get("validation") or {}
    recent = source.get("recent_period") or {}
    days = recent.get("days") or []
    return {
        "schema_version": "MB_PUBLIC_4SO_AGGREGATE_PROOF_V1",
        "status": "AGGREGATE_ONLY_SELECTIONS_HIDDEN",
        "validation": {
            "window_start": validation.get("window_start"),
            "window_end": validation.get("window_end"),
            "hit_days": int(validation.get("hit_days") or 0),
            "total_days": int(validation.get("total_days") or 0),
            "rate_pct": int(validation.get("rate_pct") or 0),
            "definition": "Một ngày được ghi nhận khi báo cáo 4SO đã khóa trước kết quả có ít nhất một số xuất hiện trong 27 mã. Các số đã khóa không công khai.",
        },
        "recent_period": {
            "period_start": recent.get("period_start"),
            "period_end": recent.get("period_end"),
            "hit_days": int(recent.get("hit_days") or 0),
            "total_days": int(recent.get("total_days") or 0),
            "days": [
                {"date": row.get("date"), "status": row.get("status")}
                for row in days if isinstance(row, dict)
            ],
        },
        "privacy": {
            "current_selection_hidden": True,
            "historical_selections_hidden": True,
            "scores_hidden": True,
            "rankings_hidden": True,
            "algorithm_details_hidden": True,
        },
    }


def aggregate_yesterday(source: dict[str, Any]) -> dict[str, Any]:
    validation = source.get("historical_validation") or {}
    month = source.get("month_summary") or {}
    records = month.get("daily_records") or []
    current_status = "hit" if int(source.get("unique_hit_count") or 0) > 0 else "miss"
    return {
        "schema_version": "MB_PUBLIC_4SO_AGGREGATE_STATUS_V1",
        "date": source.get("date"),
        "status": current_status,
        "selection_hidden": True,
        "historical_validation": {
            "window_start": validation.get("window_start"),
            "window_end": validation.get("window_end"),
            "hit_days": int(validation.get("hit_days") or 0),
            "total_days": int(validation.get("total_days") or 0),
            "rate_pct": int(validation.get("rate_pct") or 0),
        },
        "month_summary": {
            "month": month.get("month"),
            "period_start": month.get("period_start"),
            "period_end": month.get("period_end"),
            "observed_days": int(month.get("observed_days") or 0),
            "win_days": int(month.get("win_days") or 0),
            "miss_days": int(month.get("miss_days") or 0),
            "daily_records": [
                {"date": row.get("date"), "status": row.get("status")}
                for row in records if isinstance(row, dict)
            ],
        },
    }


STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f4f5f7;color:#172330;font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit}.top{background:#fff;border-bottom:1px solid #dfe3e7;position:sticky;top:0;z-index:10}.topin{max-width:1080px;margin:auto;padding:10px 16px;display:flex;gap:14px;align-items:center;justify-content:space-between}.brand{font-weight:900;color:#af151b;text-decoration:none}.nav{display:flex;gap:6px;overflow:auto}.nav a{padding:7px 9px;text-decoration:none;white-space:nowrap;font-weight:700;font-size:13px}.buy{background:#af151b;color:#fff!important;border-radius:8px}.main{max-width:1080px;margin:auto;padding:20px 16px}.hero,.card{background:#fff;border:1px solid #dde3e8;border-radius:15px;padding:18px;margin-bottom:14px}.kicker{color:#af151b;font-size:12px;font-weight:900;letter-spacing:.08em;margin:0 0 5px}h1{font-size:clamp(27px,4vw,40px);line-height:1.12;margin:0 0 10px}h2{margin:0 0 8px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.metric{background:#f7f8fa;border:1px solid #e4e8eb;border-radius:11px;padding:12px}.metric small{display:block;color:#687783}.metric b{font-size:25px}.history{width:100%;border-collapse:collapse}.history th,.history td{padding:9px;border-bottom:1px solid #ebedef;text-align:left}.history th{background:#f8f9fa;color:#667581}.hit{color:#16703a;font-weight:900}.miss{color:#9e2025;font-weight:900}.locked{display:inline-block;padding:5px 8px;border-radius:999px;background:#f4ecec;color:#8e1b20;font-size:12px;font-weight:900}.cta{display:inline-block;background:#af151b;color:#fff;text-decoration:none;padding:10px 13px;border-radius:9px;font-weight:900}.note{font-size:12px;color:#6b7883}.footer{text-align:center;padding:25px;color:#6d7882}@media(max-width:680px){.metrics{grid-template-columns:1fr}.topin{padding:8px 10px}.main{padding:12px}.hero,.card{padding:14px}}
"""


def shell(title: str, desc: str, body: str) -> str:
    return f'''<!doctype html><html lang="vi" data-4so-sanitized="true"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><style>{STYLE}</style></head><body><header class="top"><div class="topin"><a class="brand" href="/">LÊ MIỀN BẮC</a><nav class="nav"><a href="/thong-ke-xsmb/">Thống kê</a><a href="/tan-suat-xsmb/">Tần suất</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/lich-su-doi-chieu/">Lịch sử 4SO</a><a class="buy" href="/?checkout=1">Báo cáo AI</a></nav></div></header><main class="main">{body}</main><footer class="footer">Lê Miền Bắc · Thống kê dữ liệu XSMB</footer></body></html>'''


def history_page(proof: dict[str, Any]) -> str:
    v = proof["validation"]
    r = proof["recent_period"]
    rows = "".join(
        f'<tr><td>{dmy(str(row["date"]))}</td><td><span class="{row["status"]}">{"Đạt" if row["status"]=="hit" else "Chưa đạt"}</span></td><td><span class="locked">4SO đã khóa · không công khai số</span></td></tr>'
        for row in r["days"]
    )
    body = f'''<section class="hero"><p class="kicker">LỊCH SỬ 4SO · AGGREGATE ONLY</p><h1>Đối chiếu 4SO không công khai dãy số</h1><p>Trang này chỉ cho biết trạng thái từng ngày và tỷ lệ tổng hợp. Toàn bộ dãy 4SO đã chọn, số trúng, Score, thứ hạng và chi tiết thuật toán đều được ẩn.</p></section><section class="card"><div class="metrics"><div class="metric"><small>Giai đoạn gần nhất</small><b>{r['hit_days']}/{r['total_days']}</b></div><div class="metric"><small>Cửa sổ kiểm định</small><b>{v['hit_days']}/{v['total_days']}</b></div><div class="metric"><small>Tỷ lệ lịch sử</small><b>{v['rate_pct']}%</b></div></div><p class="note">Tỷ lệ lịch sử chỉ mô tả dữ liệu đã hoàn tất, không phải xác suất cho kỳ tiếp theo.</p></section><section class="card"><h2>Trạng thái theo ngày</h2><div style="overflow:auto"><table class="history"><thead><tr><th>Ngày</th><th>Trạng thái</th><th>Dãy 4SO</th></tr></thead><tbody>{rows}</tbody></table></div></section><section class="card"><h2>Báo cáo 4SO hiện tại</h2><p>Kết luận hiện tại được giữ sau lớp thanh toán; public HTML không chứa cặp số.</p><a class="cta" href="/?checkout=1">Nhận báo cáo 4SO →</a></section>'''
    return shell("Lịch sử 4SO – chỉ thống kê tổng hợp | Lê Miền Bắc", "Lịch sử trạng thái 4SO theo ngày; không công khai dãy số, Score hay thứ hạng.", body)


def method_page() -> str:
    body = '''<section class="hero"><p class="kicker">4SO AI · PHƯƠNG PHÁP RIÊNG</p><h1>4SO là lớp phân tích không công khai</h1><p>Website không công bố công thức chấm điểm, biến đầu vào, cách xếp hạng, tie-break, số đang chọn hoặc các dãy 4SO trong quá khứ.</p></section><section class="card"><h2>Những gì được công khai</h2><p><span class="locked">Dữ liệu khóa T−1</span> <span class="locked">Audit trước kết quả</span> <span class="locked">Hiệu quả lịch sử tổng hợp</span></p><p>Người dùng có thể kiểm tra nguồn dữ liệu, trạng thái khóa, lịch sử đạt/chưa đạt và các công cụ thống kê XSMB độc lập. Chi tiết 4SO là tài sản phương pháp riêng.</p></section><section class="card"><h2>Những gì được giữ kín</h2><p>✓ Số/cặp đang chọn &nbsp; ✓ Dãy 4SO lịch sử &nbsp; ✓ Score/xếp hạng &nbsp; ✓ Công thức và tham số &nbsp; ✓ Tie-break và logic nội bộ.</p><a class="cta" href="/?checkout=1">Nhận báo cáo 4SO hôm nay →</a></section>'''
    return shell("4SO AI – lớp phân tích riêng | Lê Miền Bắc", "4SO là lớp phân tích riêng; website chỉ công khai audit và hiệu quả tổng hợp, không công khai số hoặc thuật toán.", body)


def sanitize(root: Path) -> dict[str, Any]:
    source = load(SOURCE_PROOF)
    yesterday = load(SOURCE_YESTERDAY)
    proof = aggregate_proof(source)
    yday = aggregate_yesterday(yesterday)

    (root / "historical-proof.json").write_text(json.dumps(proof, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    yp = root / "ai-methods" / "yesterday-proof.json"
    yp.parent.mkdir(parents=True, exist_ok=True)
    yp.write_text(json.dumps(yday, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    hp = root / "lich-su-doi-chieu" / "index.html"
    hp.parent.mkdir(parents=True, exist_ok=True)
    hp.write_text(history_page(proof), encoding="utf-8")

    mp = root / "phuong-phap-4so" / "index.html"
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(method_page(), encoding="utf-8")

    forbidden = ("recommended_numbers", '"outputs"', '"observed"', "canonical_codes", "canonical_pairs", "final_codes", "final_pairs")
    for target in (root / "historical-proof.json", yp):
        text = target.read_text(encoding="utf-8").lower()
        for token in forbidden:
            if token.lower() in text:
                raise ValueError(f"Forbidden 4SO field remains in {target}: {token}")
    history_text = hp.read_text(encoding="utf-8")
    if "4 số đã khóa" in history_text or "history-outputs" in history_text:
        raise ValueError("Historical 4SO selection markup remains")
    method_text = mp.read_text(encoding="utf-8")
    for token in ("HitRate60", "Score(pair)", "45 cặp đảo", "tie-break được khóa"):
        if token.lower() in method_text.lower():
            raise ValueError(f"4SO algorithm detail remains: {token}")
    return {"status":"PASS","mode":"4SO_AGGREGATE_ONLY","days":len(proof["recent_period"]["days"])}


def self_test() -> None:
    source={"validation":{"window_start":"2026-01-01","window_end":"2026-01-30","hit_days":20,"total_days":30,"rate_pct":67},"recent_period":{"period_start":"2026-01-01","period_end":"2026-01-02","hit_days":1,"total_days":2,"days":[{"date":"2026-01-01","outputs":["01","10","02","20"],"observed":["01"],"status":"hit"},{"date":"2026-01-02","outputs":["03","30","04","40"],"observed":[],"status":"miss"}]}}
    clean=aggregate_proof(source); raw=json.dumps(clean)
    assert "outputs" not in raw and "01" not in raw and clean["recent_period"]["days"][0]["status"]=="hit"
    print("PUBLIC_4SO_SANITIZER_SELF_TEST_OK")


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--output-root",type=Path,default=ROOT/"_site"); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    if a.self_test: self_test()
    else: print(json.dumps(sanitize(a.output_root),ensure_ascii=False))

if __name__=="__main__": main()
