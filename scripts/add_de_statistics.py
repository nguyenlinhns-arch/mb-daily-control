#!/usr/bin/env python3
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
BASE = "https://lemienbac.com"
ROUTE = "/thong-ke-de-xsmb/"

# statistics-data.json recent_history preserves the source prize order:
# [date, special, prize1, prize2_1, ..., prize7_4].
# Therefore row[1] is the two-digit tail of the Special Prize (Đề).


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def dmy(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def load(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(path)
    return doc


def de_series(stats: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for row in stats.get("recent_history") or []:
        if not isinstance(row, list) or len(row) < 28:
            raise ValueError("recent_history row must contain date + 27 codes")
        day = str(row[0])
        date.fromisoformat(day)
        code = str(row[1]).strip().zfill(2)[-2:]
        if not re.fullmatch(r"\d{2}", code):
            raise ValueError(f"Invalid special-prize code: {row[1]}")
        out.append((day, code))
    if len(out) < 100:
        raise ValueError("Đề history too short")
    return out


def counts(series: list[tuple[str, str]], window: int) -> Counter[str]:
    return Counter(code for _, code in series[-window:])


def gaps(series: list[tuple[str, str]]) -> dict[str, dict[str, Any]]:
    last_index: dict[str, int] = {}
    last_day: dict[str, str] = {}
    for idx, (day, code) in enumerate(series):
        last_index[code] = idx
        last_day[code] = day
    end = len(series) - 1
    result: dict[str, dict[str, Any]] = {}
    for n in range(100):
        code = f"{n:02d}"
        if code in last_index:
            result[code] = {"gap": end - last_index[code], "last_seen": last_day[code]}
        else:
            result[code] = {"gap": len(series), "last_seen": None}
    return result


def top_codes(counter: Counter[str], gap_map: dict[str, dict[str, Any]], limit: int = 5) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], gap_map[item[0]]["gap"], item[0]))[:limit]


def top_gap(gap_map: dict[str, dict[str, Any]], limit: int = 5) -> list[tuple[str, int]]:
    return sorted(((code, int(data["gap"])) for code, data in gap_map.items()), key=lambda item: (-item[1], item[0]))[:limit]


def head_tail(series: list[tuple[str, str]], window: int) -> tuple[Counter[str], Counter[str]]:
    head = Counter(); tail = Counter()
    for _, code in series[-window:]:
        head[code[0]] += 1
        tail[code[1]] += 1
    return head, tail


def chips(items: list[tuple[str, int]], suffix: str) -> str:
    return "".join(f'<span class="portal-de-chip"><b>{esc(code)}</b><small>{value}{suffix}</small></span>' for code, value in items)


def home_block(stats: dict[str, Any]) -> str:
    series = de_series(stats)
    latest_day, latest_code = series[-1]
    gap_map = gaps(series)
    c30 = counts(series, 30)
    hot = top_codes(c30, gap_map, 5)
    gan = top_gap(gap_map, 5)
    heads, tails = head_tail(series, 30)
    top_head = sorted(heads.items(), key=lambda x: (-x[1], x[0]))[0]
    top_tail = sorted(tails.items(), key=lambda x: (-x[1], x[0]))[0]
    return f'''<section class="portal-section portal-de-summary" aria-labelledby="portal-de-title"><div class="portal-wrap"><div class="portal-section-title"><div><h2 id="portal-de-title">Thống kê Đề XSMB</h2><p>2 số cuối Giải Đặc Biệt · dữ liệu đến {dmy(str(stats["updated_through"]))}.</p></div><a href="{ROUTE}">Xem đầy đủ →</a></div><div class="portal-de-grid"><article class="portal-card portal-de-latest"><span>ĐỀ KỲ GẦN NHẤT</span><strong>{latest_code}</strong><small>{dmy(latest_day)}</small></article><article class="portal-card portal-de-panel"><div class="portal-de-panel-head"><b>Top Đề 30 kỳ</b><a href="{ROUTE}#tan-suat">00–99 →</a></div><div class="portal-de-chips">{chips(hot, " lần")}</div></article><article class="portal-card portal-de-panel"><div class="portal-de-panel-head"><b>Đề gan hiện tại</b><a href="{ROUTE}#de-gan">Xem gan →</a></div><div class="portal-de-chips">{chips(gan, " kỳ")}</div></article><article class="portal-card portal-de-digit"><div><span>Đầu nổi bật / 30 kỳ</span><b>{top_head[0]}</b><small>{top_head[1]}/30 kỳ</small></div><div><span>Đuôi nổi bật / 30 kỳ</span><b>{top_tail[0]}</b><small>{top_tail[1]}/30 kỳ</small></div><a href="{ROUTE}#dau-duoi">Phân bố đầu/đuôi Đề →</a></article></div></div></section>'''


def page_style() -> str:
    return '''<style id="portal-de-style">
.portal-de-grid{display:grid;grid-template-columns:.7fr 1.3fr 1.3fr .9fr;gap:10px}.portal-de-grid>.portal-card{min-width:0;padding:15px}.portal-de-latest{display:flex;flex-direction:column;align-items:center;justify-content:center;background:linear-gradient(145deg,#b3161b,#8f1116)!important;color:#fff!important;border-color:#a5161b!important}.portal-de-latest span{font-size:9px;font-weight:900;letter-spacing:.08em;opacity:.82}.portal-de-latest strong{font-size:50px;line-height:1;margin:8px 0 5px;letter-spacing:.02em}.portal-de-latest small{font-size:10px;opacity:.82}.portal-de-panel-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px}.portal-de-panel-head b{font-size:14px;color:#182b39}.portal-de-panel-head a,.portal-de-digit>a{font-size:10px;color:#a70e15;text-decoration:none;font-weight:900}.portal-de-chips{display:flex;gap:7px;flex-wrap:wrap}.portal-de-chip{min-width:48px;display:flex;flex-direction:column;align-items:center;padding:7px 8px;border:1px solid #ead4d5;border-radius:11px;background:#fff8f8}.portal-de-chip b{font-size:18px;line-height:1;color:#a70e15}.portal-de-chip small{margin-top:4px;color:#7c696a;font-size:8.5px}.portal-de-digit{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-content:start}.portal-de-digit>div{padding:9px;border-radius:11px;background:#f8fafb;border:1px solid #e7ebee}.portal-de-digit span{display:block;color:#71808b;font-size:9px}.portal-de-digit b{display:block;margin-top:3px;color:#a70e15;font-size:26px;line-height:1}.portal-de-digit small{font-size:9px;color:#66747f}.portal-de-digit>a{grid-column:1/-1;margin-top:2px}.portal-de-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}.portal-de-kpi{padding:14px!important}.portal-de-kpi span{display:block;color:#74818b;font-size:10px;font-weight:800}.portal-de-kpi strong{display:block;margin-top:4px;color:#a70e15;font-size:28px;line-height:1.1}.portal-de-kpi small{display:block;margin-top:4px;color:#7b8891;font-size:10px}.portal-de-recent{display:grid;grid-template-columns:repeat(10,1fr);gap:6px}.portal-de-recent a{display:flex;flex-direction:column;align-items:center;padding:7px 4px;border:1px solid #e4e8eb;border-radius:10px;background:#fff;text-decoration:none;color:#61717d}.portal-de-recent b{font-size:17px;color:#a70e15}.portal-de-recent small{margin-top:2px;font-size:8px}.portal-de-two-col{display:grid;grid-template-columns:1fr 1fr;gap:12px}.portal-de-number{font-variant-numeric:tabular-nums}
@media(max-width:900px){.portal-de-grid{grid-template-columns:1fr 1fr}.portal-de-latest{grid-row:span 1}.portal-de-digit{grid-column:1/-1}.portal-de-kpis{grid-template-columns:1fr 1fr}.portal-de-recent{grid-template-columns:repeat(6,1fr)}}
@media(max-width:700px){.portal-de-grid{grid-template-columns:1fr}.portal-de-grid>.portal-card{padding:12px}.portal-de-latest{min-height:126px}.portal-de-latest strong{font-size:48px}.portal-de-digit{grid-column:auto}.portal-de-panel-head b{font-size:13px}.portal-de-chip{min-width:46px}.portal-de-kpis{gap:7px}.portal-de-kpi{padding:11px!important}.portal-de-kpi strong{font-size:24px}.portal-de-two-col{grid-template-columns:1fr}.portal-de-recent{grid-template-columns:repeat(5,1fr);gap:5px}}
@media(max-width:390px){.portal-de-kpis{grid-template-columns:1fr 1fr}.portal-de-recent{grid-template-columns:repeat(4,1fr)}}
</style>'''


def frequency_rows(series: list[tuple[str, str]]) -> tuple[str, str]:
    gap_map = gaps(series)
    c30, c60, c100 = counts(series, 30), counts(series, 60), counts(series, 100)
    rows = []
    for n in range(100):
        code = f"{n:02d}"; data = gap_map[code]
        last = dmy(data["last_seen"]) if data["last_seen"] else "—"
        rows.append(f'<tr><td><b class="portal-de-number">{code}</b></td><td>{c30[code]}</td><td>{c60[code]}</td><td>{c100[code]}</td><td>{data["gap"]}</td><td>{last}</td></tr>')
    hot = sorted(range(100), key=lambda n: (-c60[f"{n:02d}"], -c30[f"{n:02d}"], gap_map[f"{n:02d}"]["gap"], n))[:15]
    hot_rows = "".join(f'<tr><td><b>{n:02d}</b></td><td>{c30[f"{n:02d}"]}</td><td>{c60[f"{n:02d}"]}</td><td>{c100[f"{n:02d}"]}</td></tr>' for n in hot)
    return "".join(rows), hot_rows


def gap_rows(series: list[tuple[str, str]]) -> str:
    gap_map = gaps(series)
    ranked = top_gap(gap_map, 20)
    return "".join(f'<tr><td><b>{code}</b></td><td>{gap}</td><td>{dmy(gap_map[code]["last_seen"]) if gap_map[code]["last_seen"] else "Chưa có trong cửa sổ"}</td></tr>' for code, gap in ranked)


def digit_rows(series: list[tuple[str, str]]) -> tuple[str, str]:
    tables = {w: head_tail(series, w) for w in (30, 60, 100)}
    head_rows=[]; tail_rows=[]
    for d in map(str, range(10)):
        head_rows.append(f'<tr><td><b>{d}</b></td><td>{tables[30][0][d]}</td><td>{tables[60][0][d]}</td><td>{tables[100][0][d]}</td></tr>')
        tail_rows.append(f'<tr><td><b>{d}</b></td><td>{tables[30][1][d]}</td><td>{tables[60][1][d]}</td><td>{tables[100][1][d]}</td></tr>')
    return "".join(head_rows), "".join(tail_rows)


def build_page(stats: dict[str, Any]) -> str:
    import optimize_portal_v3 as portal
    series = de_series(stats)
    latest_day, latest_code = series[-1]
    gap_map = gaps(series)
    c30 = counts(series, 30)
    head30, tail30 = head_tail(series, 30)
    top30 = top_codes(c30, gap_map, 1)[0]
    gan = top_gap(gap_map, 1)[0]
    top_head = sorted(head30.items(), key=lambda x: (-x[1], x[0]))[0]
    top_tail = sorted(tail30.items(), key=lambda x: (-x[1], x[0]))[0]
    all_rows, hot_rows = frequency_rows(series)
    gan_rows = gap_rows(series)
    head_rows, tail_rows = digit_rows(series)
    recent = "".join(f'<a href="#" aria-label="Đề {dmy(day)} là {code}"><b>{code}</b><small>{dmy(day)[:5]}</small></a>' for day, code in reversed(series[-30:]))
    breadcrumb = '<nav class="portal-breadcrumbs" aria-label="Đường dẫn"><a href="/">Trang chủ</a><span aria-hidden="true">›</span><span aria-current="page">Thống kê Đề</span></nav>'
    body = f'''{breadcrumb}<main><section class="portal-page-intro"><p class="eyebrow">THỐNG KÊ ĐỀ XSMB</p><h1>Thống kê Đề miền Bắc 00–99</h1><p>Đề được tính theo <strong>2 số cuối Giải Đặc Biệt</strong>. Mỗi kỳ chỉ có một số Đề; dữ liệu sử dụng đến {dmy(str(stats["updated_through"]))}.</p></section><div class="portal-v2-wrap"><section class="portal-de-kpis"><article class="portal-v2-card portal-de-kpi"><span>ĐỀ GẦN NHẤT</span><strong>{latest_code}</strong><small>{dmy(latest_day)}</small></article><article class="portal-v2-card portal-de-kpi"><span>TOP 30 KỲ</span><strong>{top30[0]}</strong><small>{top30[1]}/30 lần</small></article><article class="portal-v2-card portal-de-kpi"><span>GAN DÀI NHẤT</span><strong>{gan[0]}</strong><small>{gan[1]} kỳ</small></article><article class="portal-v2-card portal-de-kpi"><span>ĐẦU / ĐUÔI 30</span><strong>{top_head[0]} · {top_tail[0]}</strong><small>{top_head[1]}/30 · {top_tail[1]}/30</small></article></section><div class="portal-de-two-col"><section class="portal-v2-card"><h2>Đề xuất hiện nhiều</h2><p>Top theo số lần xuất hiện trong 60 kỳ, kèm đối chiếu 30 và 100 kỳ.</p><div class="portal-v2-scroll"><table class="portal-v2-table"><thead><tr><th>Đề</th><th>30 kỳ</th><th>60 kỳ</th><th>100 kỳ</th></tr></thead><tbody>{hot_rows}</tbody></table></div></section><section class="portal-v2-card" id="de-gan"><h2>Đề gan hiện tại</h2><p>Số kỳ đã hoàn tất kể từ lần gần nhất số đó xuất hiện ở 2 số cuối Giải Đặc Biệt.</p><div class="portal-v2-scroll"><table class="portal-v2-table"><thead><tr><th>Đề</th><th>Gan</th><th>Lần gần nhất</th></tr></thead><tbody>{gan_rows}</tbody></table></div></section></div><section class="portal-v2-card" id="dau-duoi"><h2>Đầu – đuôi Đề</h2><div class="portal-de-two-col"><div><h3>Theo đầu</h3><div class="portal-v2-scroll"><table class="portal-v2-table"><thead><tr><th>Đầu</th><th>30</th><th>60</th><th>100</th></tr></thead><tbody>{head_rows}</tbody></table></div></div><div><h3>Theo đuôi</h3><div class="portal-v2-scroll"><table class="portal-v2-table"><thead><tr><th>Đuôi</th><th>30</th><th>60</th><th>100</th></tr></thead><tbody>{tail_rows}</tbody></table></div></div></div></section><section class="portal-v2-card"><h2>30 kỳ Đề gần nhất</h2><div class="portal-de-recent">{recent}</div></section><section class="portal-v2-card" id="tan-suat"><h2>Bảng thống kê Đề 00–99</h2><p>Đủ 100 số, gồm tần suất 30/60/100 kỳ, gan hiện tại và ngày xuất hiện gần nhất.</p><div class="portal-v2-scroll"><table class="portal-v2-table"><thead><tr><th>Đề</th><th>30</th><th>60</th><th>100</th><th>Gan</th><th>Gần nhất</th></tr></thead><tbody>{all_rows}</tbody></table></div><p class="portal-v3-note">Tần suất và gan chỉ mô tả dữ liệu lịch sử; không phải cam kết số sẽ xuất hiện ở kỳ tiếp theo.</p></section><section class="portal-v2-card"><h2>Thống kê liên quan</h2><div class="portal-related"><a href="/thong-ke-xsmb/">Thống kê lô tô 00–99</a><a href="/thong-ke-dau-duoi-xsmb/">Đầu/đuôi lô tô</a><a href="/thong-ke-tong-xsmb/">Theo tổng</a><a href="/thong-ke-theo-thu-xsmb/">Theo thứ</a></div></section></div></main>'''
    text = portal.shell("Thống kê Đề XSMB 00–99: tần suất, gan, đầu đuôi | Lê Miền Bắc", "Thống kê Đề miền Bắc theo 2 số cuối Giải Đặc Biệt: tần suất 00–99 trong 30, 60, 100 kỳ, Đề gan, đầu đuôi và lịch sử Đề gần nhất.", ROUTE, body)
    style = page_style()
    text = text.replace("</head>", style + schema_block(stats) + "</head>", 1)
    return text


def schema_block(stats: dict[str, Any]) -> str:
    graph = [
        {"@type":"WebPage","@id":BASE+ROUTE+"#webpage","url":BASE+ROUTE,"name":"Thống kê Đề XSMB 00–99","description":"Thống kê 2 số cuối Giải Đặc Biệt XSMB theo 30, 60 và 100 kỳ.","inLanguage":"vi-VN","dateModified":stats["updated_through"]},
        {"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Trang chủ","item":BASE+"/"},{"@type":"ListItem","position":2,"name":"Thống kê Đề","item":BASE+ROUTE}]},
        {"@type":"Dataset","name":"Lịch sử Đề XSMB","description":"Hai số cuối Giải Đặc Biệt theo từng kỳ dùng cho thống kê tần suất, gan và đầu đuôi Đề.","temporalCoverage":f'{stats["first_date"]}/{stats["updated_through"]}',"dateModified":stats["updated_through"],"url":BASE+ROUTE,"measurementTechnique":"Thống kê mô tả từ 2 số cuối Giải Đặc Biệt đã công bố"},
    ]
    return '<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@graph":graph},ensure_ascii=False,separators=(",",":"))+'</script>'


def section_around(text: str, needle: str) -> tuple[int, int] | None:
    pos = text.find(needle)
    if pos < 0: return None
    start = text.rfind("<section", 0, pos)
    end = text.find("</section>", pos)
    if start < 0 or end < 0: return None
    return start, end + len("</section>")


def patch_home(path: Path, stats: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    if "portal-de-style" not in text:
        text = text.replace("</head>", page_style() + "</head>", 1)
    if "portal-de-summary" not in text:
        result = section_around(text, '<h2>27 mã kỳ gần nhất</h2>')
        if not result:
            raise ValueError("Homepage latest-result section not found")
        _, end = result
        text = text[:end] + home_block(stats) + text[end:]
    if ROUTE not in text:
        anchor = '<a class="portal-card portal-tool" href="/tra-cuu-xsmb/">'
        card = f'<a class="portal-card portal-tool" href="{ROUTE}"><b>Thống kê Đề</b><span>2 số cuối Giải Đặc Biệt · tần suất và gan</span><em>Xem Đề →</em></a>'
        if anchor in text:
            text = text.replace(anchor, card + anchor, 1)
    path.write_text(text, encoding="utf-8")


def update_sitemap(root: Path, updated: str) -> None:
    path = root / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    if BASE + ROUTE not in text:
        entry = f'  <url><loc>{BASE}{ROUTE}</loc><lastmod>{updated}</lastmod></url>\n'
        text = text.replace("</urlset>", entry + "</urlset>")
        path.write_text(text, encoding="utf-8")


def apply(root: Path) -> dict[str, Any]:
    stats = load(root / "statistics-data.json")
    de_series(stats)
    target = root / "thong-ke-de-xsmb"
    target.mkdir(exist_ok=True)
    (target / "index.html").write_text(build_page(stats), encoding="utf-8")
    patch_home(root / "index.html", stats)
    update_sitemap(root, str(stats["updated_through"]))
    return {"status":"PASS","route":ROUTE,"latest_de":de_series(stats)[-1][1],"history_rows":len(de_series(stats))}


def self_test() -> None:
    import tempfile
    from datetime import timedelta
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); rows=[]; start=date(2026,1,1)
        for i in range(120):
            special=f"{(i*7)%100:02d}"
            rows.append([(start+timedelta(days=i)).isoformat(), special, *[f"{(i+j+1)%100:02d}" for j in range(26)]])
        stats={"first_date":rows[0][0],"updated_through":rows[-1][0],"recent_history":rows}
        (root/"statistics-data.json").write_text(json.dumps(stats),encoding="utf-8")
        (root/"index.html").write_text('<html><head></head><body><main><section class="portal-section"><div><h2>27 mã kỳ gần nhất</h2></div></section><section><a class="portal-card portal-tool" href="/tra-cuu-xsmb/"></a></section></main></body></html>',encoding="utf-8")
        (root/"sitemap.xml").write_text('<?xml version="1.0"?><urlset></urlset>',encoding="utf-8")
        result=apply(root)
        assert result["status"]=="PASS"
        home=(root/"index.html").read_text(encoding="utf-8")
        page=(root/"thong-ke-de-xsmb/index.html").read_text(encoding="utf-8")
        assert "portal-de-summary" in home and ROUTE in home
        assert "Thống kê Đề miền Bắc 00–99" in page and "Bảng thống kê Đề 00–99" in page
        assert BASE+ROUTE in (root/"sitemap.xml").read_text(encoding="utf-8")
    print("DE_STATISTICS_SELF_TEST_OK")


def main() -> None:
    p=argparse.ArgumentParser();p.add_argument("--output-root",type=Path,default=ROOT/"_site");p.add_argument("--self-test",action="store_true");a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))


if __name__=="__main__":main()
