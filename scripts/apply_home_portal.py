#!/usr/bin/env python3
"""Replace the sales-first homepage with a data-first XSMB portal.

Public method outputs are allowed for non-4SO methods only. The paid 4SO
current output stays locked: no canonical/final codes, pairs, scores or ranks
are read or embedded by this builder.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_METHODS = ROOT / "ai-methods" / "public-methods.json"
PUBLIC_PROOF = ROOT / "data" / "public-historical-proof.json"
PAID_READY = ROOT / "data" / "paid-report-ready.json"
FORBIDDEN_4SO = re.compile(r"(?:canonical|final)[_-]?(?:codes|pairs)|(?:top\s*1|top\s*2).*(?:\d{2})", re.I)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def dmy(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected object")
    return data


def balls(values: list[str], cls: str = "") -> str:
    return "".join(f'<span class="portal-ball {cls}">{esc(v)}</span>' for v in values)


def method_cards(methods: list[dict[str, Any]]) -> str:
    out = []
    for method in methods:
        mid = str(method.get("id") or "").upper()
        name = str(method.get("name") or mid)
        if "4SO" in mid or "4SO" in name.upper():
            raise ValueError("4SO must not appear in public method outputs")
        nums = [str(x).zfill(2)[-2:] for x in (method.get("numbers") or [])]
        if not nums or any(not re.fullmatch(r"\d{2}", n) for n in nums):
            raise ValueError(f"Invalid public method numbers: {mid}")
        out.append(
            f'<article class="portal-method"><div class="portal-method-head"><b>{esc(name)}</b>'
            f'<span>{len(nums)} số</span></div><div class="portal-method-numbers">{balls(nums)}</div></article>'
        )
    return "".join(out)


def latest_stats(data: dict[str, Any]) -> tuple[str, list[str], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    history = data.get("recent_history") or []
    if not history:
        raise ValueError("statistics-data.json has no recent history")
    last = history[-1]
    last_day = str(last[0])
    codes = [str(x).zfill(2)[-2:] for x in last[1:28]]
    if len(codes) != 27:
        raise ValueError("latest draw must contain 27 codes")
    numbers = data.get("numbers") or []
    pairs = data.get("pairs") or []
    hot = sorted(numbers, key=lambda r: (-int(r["windows"]["60"]["days_seen"]), -int(r["windows"]["60"]["hits"]), r["code"]))[:10]
    gan = sorted(numbers, key=lambda r: (-int(r["current_gap"]), -int(r["max_gap"]), r["code"]))[:10]
    pair_top = sorted(pairs, key=lambda r: (-int(r["windows"]["60"]["days_seen"]), -int(r["windows"]["60"]["hits"]), r["pair"]))[:8]
    return last_day, codes, hot, gan, pair_top


def mini_table(rows: list[dict[str, Any]], mode: str) -> str:
    if mode == "hot":
        body = "".join(f'<tr><td><b>{r["code"]}</b></td><td>{r["windows"]["60"]["days_seen"]}/60</td><td>{r["windows"]["60"]["hits"]}</td></tr>' for r in rows)
        head = '<tr><th>Số</th><th>Ngày/60</th><th>Nháy</th></tr>'
    elif mode == "gan":
        body = "".join(f'<tr><td><b>{r["code"]}</b></td><td>{r["current_gap"]}</td><td>{dmy(r["last_seen"]) if r.get("last_seen") else "—"}</td></tr>' for r in rows)
        head = '<tr><th>Số</th><th>Gan</th><th>Gần nhất</th></tr>'
    else:
        body = "".join(f'<tr><td><b>{r["pair"]}</b></td><td>{r["windows"]["60"]["days_seen"]}/60</td><td>{r["current_gap"]}</td></tr>' for r in rows)
        head = '<tr><th>Cặp</th><th>Ngày/60</th><th>Gan</th></tr>'
    return f'<div class="portal-table-wrap"><table class="portal-table"><thead>{head}</thead><tbody>{body}</tbody></table></div>'


CSS = r'''
<style id="portal-home-v1-style">
body.portal-home{background:#f3f4f6;color:#17202a}.portal-home .site-header{position:sticky;top:0;z-index:30;background:#fff;border-bottom:1px solid #e2e5e9;box-shadow:0 2px 10px rgba(14,28,42,.06)}
.portal-home .portal-header{max-width:1180px;margin:auto;padding:9px 16px;display:flex;align-items:center;gap:18px}.portal-home .portal-brand{display:flex;align-items:center;gap:9px;text-decoration:none;color:#b3161b;font-weight:900;white-space:nowrap}.portal-home .portal-brand-mark{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:#b3161b;color:#fff;font-size:13px}.portal-home .portal-brand small{display:block;color:#66717c;font-size:10px;letter-spacing:.08em}.portal-home .portal-nav{display:flex;align-items:center;gap:4px;overflow:auto;flex:1}.portal-home .portal-nav a{padding:8px 9px;border-radius:8px;text-decoration:none;color:#263646;white-space:nowrap;font-weight:700;font-size:13px}.portal-home .portal-nav a:hover{background:#f4ecec;color:#a50f16}.portal-home .portal-header-buy{background:#b3161b!important;color:#fff!important}
.portal-home main{padding-bottom:28px}.portal-home .portal-wrap{max-width:1180px;margin:auto;padding-left:16px;padding-right:16px}.portal-home .portal-topline{background:#b3161b;color:#fff}.portal-home .portal-topline .portal-wrap{min-height:38px;display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:13px}.portal-home .portal-topline a{color:#fff;text-decoration:none;font-weight:800}.portal-home .portal-hero{background:#fff;border-bottom:1px solid #e0e4e8;padding:22px 0}.portal-home .portal-hero-grid{display:grid;grid-template-columns:1.35fr .65fr;gap:16px}.portal-home .portal-kicker{margin:0 0 5px;color:#b3161b;font-size:12px;font-weight:900;letter-spacing:.08em}.portal-home h1{margin:0;font-size:clamp(28px,4vw,44px);line-height:1.08;color:#111d2a}.portal-home .portal-lead{max-width:760px;margin:10px 0 0;color:#526170}.portal-home .portal-status{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.portal-home .portal-status span{padding:6px 9px;border-radius:999px;background:#f3f5f7;border:1px solid #e0e4e8;font-size:12px;font-weight:800}.portal-home .portal-paid-card{border:1px solid #e8c7c8;background:#fff8f8;border-radius:14px;padding:15px}.portal-home .portal-paid-card small{color:#8a4b4e;font-weight:800}.portal-home .portal-paid-lock{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}.portal-home .portal-paid-lock div{background:#fff;border:1px solid #ead6d7;border-radius:10px;padding:9px;text-align:center}.portal-home .portal-paid-lock b{font-size:21px;letter-spacing:.08em}.portal-home .portal-paid-card button{width:100%;background:#b3161b;border:0;color:#fff;border-radius:10px;padding:11px;font-weight:900;cursor:pointer}.portal-home .portal-paid-note{margin:7px 0 0;font-size:11px;color:#735b5c}
.portal-home .portal-section{padding:18px 0}.portal-home .portal-section-title{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:10px}.portal-home .portal-section-title h2{margin:0;font-size:22px;color:#142231}.portal-home .portal-section-title p{margin:2px 0 0;color:#667480;font-size:13px}.portal-home .portal-section-title a{color:#a70e15;text-decoration:none;font-weight:800;font-size:13px}.portal-home .portal-card{background:#fff;border:1px solid #dfe4e9;border-radius:14px;box-shadow:0 2px 10px rgba(16,35,50,.04)}
.portal-home .portal-result-card{padding:14px}.portal-home .portal-result-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px}.portal-home .portal-result-head strong{font-size:17px}.portal-home .portal-result-head span{font-size:12px;color:#62717e}.portal-home .portal-results{display:grid;grid-template-columns:repeat(9,1fr);gap:6px}.portal-home .portal-result{border:1px solid #e2e6ea;border-radius:8px;padding:7px 3px;text-align:center;background:#fafbfc}.portal-home .portal-result small{display:block;color:#89949e;font-size:9px}.portal-home .portal-result b{display:block;font-size:18px;color:#182b3b}.portal-home .portal-result.is-dup{background:#fff4f4;border-color:#efc9cb}.portal-home .portal-result.is-dup b{color:#a60d14}.portal-home .portal-dup-note{margin:10px 0 0;font-size:12px;color:#687782}
.portal-home .portal-tools{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.portal-home .portal-tool{padding:14px;text-decoration:none;color:#172536;transition:.16s ease}.portal-home .portal-tool:hover{transform:translateY(-2px);border-color:#c8d0d8;box-shadow:0 6px 16px rgba(14,30,45,.08)}.portal-home .portal-tool b{display:block;font-size:16px;margin-bottom:3px}.portal-home .portal-tool span{display:block;color:#64727d;font-size:12px}.portal-home .portal-tool em{display:inline-block;margin-top:8px;color:#a70e15;font-style:normal;font-weight:900;font-size:12px}
.portal-home .portal-methods{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.portal-home .portal-method{background:#fff;border:1px solid #dfe4e9;border-radius:12px;padding:13px}.portal-home .portal-method-head{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:9px}.portal-home .portal-method-head b{font-size:14px}.portal-home .portal-method-head span{font-size:10px;color:#75828d;background:#f2f4f6;padding:3px 6px;border-radius:999px}.portal-home .portal-method-numbers{display:flex;gap:6px;flex-wrap:wrap}.portal-home .portal-ball{width:34px;height:34px;border:1px solid #d5dce2;border-radius:50%;display:inline-grid;place-items:center;background:#fff;font-weight:900;font-size:14px}.portal-home .portal-method .portal-ball{border-color:#edc7c8;color:#a70e15;background:#fff8f8}
.portal-home .portal-quick-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.portal-home .portal-quick{padding:0;overflow:hidden}.portal-home .portal-quick-head{padding:12px 13px;border-bottom:1px solid #e6e9ed;display:flex;align-items:center;justify-content:space-between}.portal-home .portal-quick-head b{font-size:15px}.portal-home .portal-quick-head a{font-size:11px;color:#a70e15;text-decoration:none;font-weight:800}.portal-home .portal-table{width:100%;border-collapse:collapse;font-size:12px}.portal-home .portal-table th,.portal-home .portal-table td{padding:7px 9px;border-bottom:1px solid #eef0f2;text-align:right}.portal-home .portal-table th:first-child,.portal-home .portal-table td:first-child{text-align:left}.portal-home .portal-table th{background:#fafbfc;color:#71808c;font-weight:800}.portal-home .portal-table tr:last-child td{border-bottom:0}
.portal-home .portal-proof{display:grid;grid-template-columns:.45fr 1.55fr;gap:12px}.portal-home .portal-proof-rate{padding:18px;background:#b3161b;color:#fff;border-radius:14px}.portal-home .portal-proof-rate small{display:block;opacity:.85}.portal-home .portal-proof-rate strong{display:block;font-size:42px;line-height:1;margin:8px 0}.portal-home .portal-proof-rate span{font-size:12px;opacity:.92}.portal-home .portal-proof-copy{padding:17px}.portal-home .portal-proof-copy h2{margin:0 0 6px}.portal-home .portal-proof-copy p{margin:5px 0;color:#5f6e79}.portal-home .portal-proof-copy a{display:inline-block;margin-top:7px;color:#a70e15;font-weight:900;text-decoration:none}.portal-home .portal-disclaimer{font-size:11px!important;color:#77838d!important}
.portal-home .portal-buy{padding:20px 0}.portal-home .buy-simple-card{border-radius:15px!important}.portal-home .buy-simple{margin:0!important}.portal-home .historical-proof-section,.portal-home .conversion-trust,.portal-home .hero-simple{display:none!important}.portal-home .public-stats-entry{display:none!important}
@media(max-width:900px){.portal-home .portal-hero-grid{grid-template-columns:1fr}.portal-home .portal-tools{grid-template-columns:repeat(2,1fr)}.portal-home .portal-methods{grid-template-columns:repeat(2,1fr)}.portal-home .portal-quick-grid{grid-template-columns:1fr}.portal-home .portal-proof{grid-template-columns:1fr}.portal-home .portal-results{grid-template-columns:repeat(6,1fr)}}
@media(max-width:620px){.portal-home .portal-header{padding:7px 10px;gap:8px}.portal-home .portal-brand span:last-child{display:none}.portal-home .portal-nav a{font-size:12px;padding:7px}.portal-home .portal-topline .portal-wrap{padding:7px 12px;align-items:flex-start;flex-direction:column;gap:2px}.portal-home .portal-wrap{padding-left:12px;padding-right:12px}.portal-home .portal-section{padding:13px 0}.portal-home .portal-tools{grid-template-columns:1fr 1fr;gap:7px}.portal-home .portal-methods{grid-template-columns:1fr 1fr;gap:7px}.portal-home .portal-results{grid-template-columns:repeat(5,1fr)}.portal-home .portal-result b{font-size:16px}.portal-home .portal-tool{padding:11px}.portal-home .portal-tool b{font-size:14px}.portal-home .portal-method{padding:10px}.portal-home .portal-ball{width:31px;height:31px;font-size:13px}.portal-home .portal-paid-card{padding:13px}}
</style>
'''


def build_home(html_text: str, stats: dict[str, Any], methods_doc: dict[str, Any], proof: dict[str, Any], ready: dict[str, Any]) -> str:
    if FORBIDDEN_4SO.search(json.dumps(methods_doc, ensure_ascii=False)):
        raise ValueError("Public methods payload contains forbidden 4SO fields")
    updated = str(stats["updated_through"])
    if str(methods_doc.get("data_lock")) != updated:
        raise ValueError(f"Public methods data lock {methods_doc.get('data_lock')} != stats {updated}")
    if str(ready.get("data_lock")) != updated:
        raise ValueError(f"Paid readiness data lock {ready.get('data_lock')} != stats {updated}")

    target = str(methods_doc.get("target_date") or ready.get("report_date"))
    last_day, codes, hot, gan, pair_top = latest_stats(stats)
    if last_day != updated:
        raise ValueError("latest public history date differs from updated_through")
    cnt = Counter(codes)
    result_cells = "".join(
        f'<div class="portal-result {"is-dup" if cnt[c] > 1 else ""}"><small>L{i:02d}</small><b>{esc(c)}</b></div>'
        for i, c in enumerate(codes, 1)
    )
    dup = [f"{c}×{n}" for c, n in sorted(cnt.items()) if n > 1]
    dup_note = " · ".join(dup) if dup else "Không có mã lặp trong 27 mã."

    validation = proof.get("validation") or {}
    rate = int(validation.get("rate_pct", 0))
    hit_days = int(validation.get("hit_days", 0))
    total_days = int(validation.get("total_days", 0))

    public_methods = methods_doc.get("methods") or []
    cards = method_cards(public_methods)

    header = f'''<header class="site-header"><div class="portal-header"><a class="portal-brand" href="/"><span class="portal-brand-mark">LMB</span><span>LÊ MIỀN BẮC<small>XSMB · THỐNG KÊ · AI</small></span></a><nav class="portal-nav" aria-label="Điều hướng chính"><a href="/">Trang chủ</a><a href="/thong-ke-xsmb/">Thống kê</a><a href="/tan-suat-xsmb/">Tần suất</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/cap-dao-xsmb/">Cặp đảo</a><a href="/tra-cuu-xsmb/">Tra cứu</a><a href="/lich-su-doi-chieu/">Lịch sử</a><a href="/?checkout=1" class="portal-header-buy">Báo cáo AI</a></nav></div></header>'''

    main = f'''<main id="main" data-home-portal="v1">
<section class="portal-topline"><div class="portal-wrap"><span>XSMB · dữ liệu 27/27 đến <b>{dmy(updated)}</b> · {stats['row_count']} kỳ</span><a href="/thong-ke-xsmb/">Mở toàn bộ công cụ →</a></div></section>
<section class="portal-hero"><div class="portal-wrap portal-hero-grid"><div><p class="portal-kicker">LÊ MIỀN BẮC HÔM NAY</p><h1>XSMB, thống kê 00–99<br>và phân tích AI</h1><p class="portal-lead">Một trang để xem dữ liệu kỳ gần nhất, tần suất, lô gan, 45 cặp đảo, tra cứu lịch sử và các phương pháp AI công khai. Dữ liệu chỉ dùng đến ngày đã hoàn tất.</p><div class="portal-status"><span>Target {dmy(target)}</span><span>Data lock {dmy(updated)}</span><span>27/27 mã</span><span>Không look-ahead</span></div></div><aside class="portal-paid-card"><small>4SO AI · BÁO CÁO RIÊNG</small><h2>Kết luận hôm nay đã khóa</h2><div class="portal-paid-lock"><div><small>TOP 1</small><b>•• — ••</b></div><div><small>TOP 2</small><b>•• — ••</b></div></div><button type="button" data-open-checkout data-cta-position="portal-hero">NHẬN BÁO CÁO 4SO – 30.000Đ</button><p class="portal-paid-note">Trang công khai không chứa số chọn, Score hay thứ hạng 4SO hôm nay.</p></aside></div></section>
<section class="portal-section"><div class="portal-wrap"><div class="portal-section-title"><div><h2>27 mã kỳ gần nhất</h2><p>Kết quả đã hoàn tất ngày {dmy(last_day)} · mỗi ô là 2 số cuối theo L01–L27.</p></div><a href="/tra-cuu-xsmb/">Dò bộ số →</a></div><div class="portal-card portal-result-card"><div class="portal-result-head"><strong>XSMB {dmy(last_day)}</strong><span>27/27 mã</span></div><div class="portal-results">{result_cells}</div><p class="portal-dup-note"><b>Mã lặp:</b> {esc(dup_note)}</p></div></div></section>
<section class="portal-section"><div class="portal-wrap"><div class="portal-section-title"><div><h2>Công cụ thống kê XSMB</h2><p>Dùng ngay trên mobile, không cần đăng nhập.</p></div></div><div class="portal-tools"><a class="portal-card portal-tool" href="/thong-ke-xsmb/"><b>Ma trận 00–99</b><span>Hồ sơ từng số, 7–365 kỳ</span><em>Mở công cụ →</em></a><a class="portal-card portal-tool" href="/tan-suat-xsmb/"><b>Tần suất XSMB</b><span>Ngày có mặt và tổng nháy</span><em>Xem bảng →</em></a><a class="portal-card portal-tool" href="/lo-gan-xsmb/"><b>Lô gan XSMB</b><span>Gan hiện tại, gan max, lần gần nhất</span><em>Xem gan →</em></a><a class="portal-card portal-tool" href="/cap-dao-xsmb/"><b>45 cặp đảo</b><span>Tần suất cặp, đồng xuất hiện, khoảng vắng</span><em>Xem cặp →</em></a><a class="portal-card portal-tool" href="/tra-cuu-xsmb/"><b>Tra cứu bộ số</b><span>Nhập bộ 00–99 và dò 30–365 kỳ</span><em>Tra cứu →</em></a><a class="portal-card portal-tool" href="/thong-ke-lo-to-mien-bac-bang-ai/"><b>Thống kê bằng AI</b><span>Giải thích các lớp phân tích công khai</span><em>Xem phương pháp →</em></a><a class="portal-card portal-tool" href="/lich-su-doi-chieu/"><b>Lịch sử đối chiếu</b><span>Có cả ngày đạt và chưa đạt</span><em>Mở lịch sử →</em></a><a class="portal-card portal-tool" href="/mau-bao-cao.html"><b>Mẫu báo cáo</b><span>Xem định dạng trước khi mua</span><em>Xem mẫu →</em></a></div></div></section>
<section class="portal-section"><div class="portal-wrap"><div class="portal-section-title"><div><h2>Phương pháp công khai hôm nay</h2><p>Số được tạo từ dữ liệu khóa đến {dmy(updated)}. 4SO không nằm trong danh sách công khai này.</p></div></div><div class="portal-methods">{cards}</div><p class="portal-disclaimer">Các phương pháp là thống kê/phân tích dữ liệu lịch sử, không phải cam kết kết quả. Không dùng kết quả ngày {dmy(target)} để tạo đầu ra.</p></div></section>
<section class="portal-section"><div class="portal-wrap"><div class="portal-section-title"><div><h2>Thống kê nhanh 60 kỳ</h2><p>Ba góc nhìn phổ biến nhất trên các website thống kê XSMB.</p></div><a href="/thong-ke-xsmb/">Xem đầy đủ →</a></div><div class="portal-quick-grid"><article class="portal-card portal-quick"><div class="portal-quick-head"><b>Xuất hiện nhiều</b><a href="/tan-suat-xsmb/">Tần suất</a></div>{mini_table(hot,'hot')}</article><article class="portal-card portal-quick"><div class="portal-quick-head"><b>Khoảng vắng dài</b><a href="/lo-gan-xsmb/">Lô gan</a></div>{mini_table(gan,'gan')}</article><article class="portal-card portal-quick"><div class="portal-quick-head"><b>Cặp đảo nổi bật</b><a href="/cap-dao-xsmb/">45 cặp</a></div>{mini_table(pair_top,'pair')}</article></div></div></section>
<section class="portal-section"><div class="portal-wrap"><div class="portal-proof"><div class="portal-proof-rate"><small>KIỂM ĐỊNH LỊCH SỬ 4SO</small><strong>{rate}%</strong><span>{hit_days}/{total_days} ngày trong cửa sổ đã hoàn tất có ít nhất một số trong báo cáo xuất hiện.</span></div><div class="portal-card portal-proof-copy"><h2>4SO chỉ công khai hiệu quả tổng hợp</h2><p>Đầu ra 4SO hôm nay, Top 1–Top 2, Score và thứ hạng được giữ sau lớp thanh toán. Trang chủ chỉ hiển thị thống kê lịch sử đã hoàn tất để người dùng tự đánh giá.</p><a href="/lich-su-doi-chieu/">Xem lịch sử đối chiếu →</a><p class="portal-disclaimer">{rate}% là mô tả lịch sử, không phải xác suất cho ngày {dmy(target)}.</p></div></div></div></section>
<section class="buy-simple portal-buy" id="buy"><div class="wrap buy-simple-card"><div><p class="eyebrow">BÁO CÁO 4SO NGÀY {dmy(target)}</p><h2>30.000đ</h2><p class="buy-copy">Mở đúng một báo cáo 4SO cho ngày {dmy(target)} sau khi giao dịch được xác nhận. Số chọn hiện tại không được lưu trong HTML công khai.</p><ul class="buy-value-list"><li><strong>Top 1–Top 2 được khóa</strong><span>Chỉ mở sau xác nhận.</span></li><li><strong>Dữ liệu khóa T−1</strong><span>Đến hết {dmy(updated)}.</span></li><li><strong>Không tự gia hạn</strong><span>Thanh toán một lần.</span></li></ul><p class="checkout-scope" id="checkout-scope">01 báo cáo ngày {dmy(target)} · dữ liệu khóa đến {dmy(updated)}.</p></div><ol><li><span>1</span>Chuyển khoản đúng nội dung</li><li><span>2</span>Bấm báo đã chuyển khoản</li><li><span>3</span>Giao dịch được xác nhận, báo cáo mở trên màn hình</li></ol><button class="button button-primary button-large" type="button" data-open-checkout data-cta-position="final">NHẬN BÁO CÁO 4SO – 30.000Đ</button></div><p class="buy-legal">Dịch vụ phân tích dữ liệu độc lập · Không nhận cược · Không cam kết kết quả · <a href="/legal.html#payment">Điều khoản & hoàn phí</a></p></section>
</main>'''

    html_text = re.sub(r'<header\b[^>]*class="[^"]*site-header[^"]*"[^>]*>.*?</header>', header, html_text, count=1, flags=re.I | re.S)
    html_text = re.sub(r'<main id="main">.*?</main>', main, html_text, count=1, flags=re.I | re.S)
    html_text = html_text.replace('<body class="', '<body class="portal-home ', 1)
    if 'id="portal-home-v1-style"' not in html_text:
        html_text = html_text.replace('</head>', CSS + '\n</head>', 1)
    return html_text


def apply(output_root: Path) -> dict[str, Any]:
    page = output_root / "index.html"
    stats_path = output_root / "statistics-data.json"
    if not page.exists() or not stats_path.exists():
        raise FileNotFoundError("Homepage or statistics-data.json missing")
    html_text = page.read_text(encoding="utf-8")
    result = build_home(html_text, load_json(stats_path), load_json(PUBLIC_METHODS), load_json(PUBLIC_PROOF), load_json(PAID_READY))
    if result.count('data-open-checkout') != 2:
        raise ValueError(f"Homepage must contain exactly two checkout buttons, found {result.count('data-open-checkout')}")
    if 'data-home-portal="v1"' not in result or 'Phương pháp công khai hôm nay' not in result:
        raise ValueError("Portal homepage markers missing")
    if re.search(r'4SO[^<]{0,200}\b\d{2}\b\s*[-–—]\s*\b\d{2}\b', result, re.I):
        raise ValueError("Potential current 4SO pair leaked in homepage")
    page.write_text(result, encoding="utf-8")
    return {"status":"PASS","homepage":"portal-v1","checkout_buttons":2,"methods":len(load_json(PUBLIC_METHODS).get("methods") or [])}


def self_test() -> None:
    stats = {"updated_through":"2026-08-15","row_count":946,"recent_history":[["2026-08-15", *[f"{i%100:02d}" for i in range(27)]]],"numbers":[],"pairs":[]}
    for i in range(100):
        stats["numbers"].append({"code":f"{i:02d}","current_gap":i%9,"max_gap":20+i%7,"last_seen":"2026-08-14","windows":{"60":{"days_seen":20+i%12,"hits":25+i%10}}})
    for a in range(10):
        for b in range(a+1,10):
            stats["pairs"].append({"pair":f"{a}{b}-{b}{a}","current_gap":a%5,"windows":{"60":{"days_seen":30+b,"hits":40+a}}})
    methods={"target_date":"2026-08-16","data_lock":"2026-08-15","methods":[{"id":"A1","name":"A1","numbers":["01","02"]}]}
    proof={"validation":{"rate_pct":70,"hit_days":21,"total_days":30}}
    ready={"report_date":"2026-08-16","data_lock":"2026-08-15"}
    base='<html><head></head><body class="landing-simple"><header class="site-header"><b>x</b></header><main id="main"><section>x</section></main><div id="checkout-modal"></div></body></html>'
    out=build_home(base,stats,methods,proof,ready)
    assert 'data-home-portal="v1"' in out and out.count('data-open-checkout')==2 and 'A1' in out
    assert '01 — 02' not in out
    print('HOME_PORTAL_SELF_TEST_OK')


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument('--output-root',type=Path,default=ROOT/'_site'); parser.add_argument('--self-test',action='store_true'); args=parser.parse_args()
    if args.self_test: self_test()
    else: print(json.dumps(apply(args.output_root),ensure_ascii=False))

if __name__=='__main__': main()
