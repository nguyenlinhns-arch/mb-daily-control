#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://lemienbac.com"
VERSION = "20260815-3"
NEW_PATHS = ("/thong-ke-tong-xsmb/", "/thong-ke-theo-thu-xsmb/")
STAT_PATHS = {
    "/thong-ke-xsmb/", "/tan-suat-xsmb/", "/lo-gan-xsmb/", "/cap-dao-xsmb/",
    "/tra-cuu-xsmb/", "/thong-ke-dau-duoi-xsmb/", "/thong-ke-tong-xsmb/",
    "/thong-ke-theo-thu-xsmb/",
}
NAV = [
    ("/", "Trang chủ"), ("/thong-ke-xsmb/", "Thống kê"),
    ("/tan-suat-xsmb/", "Tần suất"), ("/lo-gan-xsmb/", "Lô gan"),
    ("/cap-dao-xsmb/", "Cặp đảo"), ("/thong-ke-dau-duoi-xsmb/", "Đầu/đuôi"),
    ("/thong-ke-tong-xsmb/", "Theo tổng"), ("/tra-cuu-xsmb/", "Tra cứu"),
    ("/phuong-phap-cong-khai/", "Phương pháp"),
]
LABELS = {
    "/": "Trang chủ", "/cho-so-mien-bac-hom-nay/": "Phương pháp hôm nay",
    "/thong-ke-xsmb/": "Trung tâm thống kê", "/tan-suat-xsmb/": "Tần suất 00–99",
    "/lo-gan-xsmb/": "Lô gan", "/cap-dao-xsmb/": "45 cặp đảo",
    "/tra-cuu-xsmb/": "Tra cứu bộ số", "/thong-ke-dau-duoi-xsmb/": "Đầu/đuôi 0–9",
    "/thong-ke-tong-xsmb/": "Theo tổng 0–9", "/thong-ke-theo-thu-xsmb/": "Theo thứ",
    "/phuong-phap-cong-khai/": "Phương pháp công khai", "/phuong-phap-4so/": "4SO AI",
    "/lich-su-doi-chieu/": "Lịch sử 4SO", "/thong-ke-lo-to-mien-bac-bang-ai/": "Thống kê bằng AI",
    "/gioi-thieu/": "Giới thiệu", "/mau-bao-cao.html": "Mẫu báo cáo",
    "/legal.html": "Điều khoản", "/404.html": "Không tìm thấy trang",
}
WEEKDAY = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def esc(x: Any) -> str:
    return html.escape(str(x), quote=True)


def dmy(s: str) -> str:
    return date.fromisoformat(s).strftime("%d/%m/%Y")


def load(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(path)
    return doc


def route_for(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    if rel == "index.html": return "/"
    if rel.endswith("/index.html"): return "/" + rel[:-10]
    return "/" + rel


def common_nav(route: str, home: bool = False) -> str:
    links = []
    for href, label in NAV:
        cls = " is-active" if href == route else ""
        links.append(f'<a class="{cls.strip()}" href="{href}">{label}</a>')
    if home:
        links.append('<a href="/?checkout=1" class="portal-header-buy">Báo cáo AI</a>')
    return "".join(links)


def shell(title: str, desc: str, route: str, body: str) -> str:
    canonical = BASE + route
    nav = common_nav(route)
    footer_links = "".join(f'<a href="{href}">{label}</a>' for href, label in NAV[1:])
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="theme-color" content="#b3161b"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{canonical}"><link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/portal-subpages.css?v=20260815-1"><link rel="stylesheet" href="/portal-v2.css?v={VERSION}"></head><body class="portal-subpage"><header class="portal-site-header" data-portal-shell="v1"><div class="portal-site-head"><a class="portal-site-brand" href="/"><span class="portal-site-brand-mark">LM</span><span><strong>LÊ MIỀN BẮC</strong><small>DỮ LIỆU · THỐNG KÊ XSMB</small></span></a><nav class="portal-site-nav" aria-label="Điều hướng chính">{nav}</nav><a class="portal-site-cta" href="/?checkout=1">Báo cáo 4SO</a></div></header><div class="portal-contextbar"><div class="portal-contextbar-inner"><span>Công cụ thống kê miễn phí · dữ liệu khóa T−1</span><a href="/thong-ke-xsmb/">Mở trung tâm thống kê →</a></div></div>{body}<footer class="portal-site-footer"><div class="portal-site-footer-inner"><div><strong>LÊ MIỀN BẮC</strong><p>Cổng dữ liệu và thống kê XSMB. Thống kê mô tả dữ liệu đã công bố, không phải cam kết kết quả.</p></div><nav class="portal-site-footer-nav">{footer_links}<a href="/thong-ke-theo-thu-xsmb/">Thống kê theo thứ</a><a href="/legal.html">Điều khoản &amp; bảo mật</a></nav></div><div class="portal-site-footer-bottom">© 2026 Lê Miền Bắc · Dữ liệu công khai và thống kê mô tả.</div></footer><script defer src="/portal-v2.js?v=20260815-2"></script></body></html>'''


def total_stats(stats: dict[str, Any], window: int) -> list[dict[str, Any]]:
    rows = (stats.get("recent_history") or [])[-window:]
    hit = Counter(); seen = Counter()
    for row in rows:
        per_day = set()
        for raw in row[1:28]:
            code = str(raw).zfill(2)[-2:]
            total = (int(code[0]) + int(code[1])) % 10
            hit[total] += 1; per_day.add(total)
        for total in per_day: seen[total] += 1
    return [{"total": n, "hits": hit[n], "days": seen[n], "window": len(rows)} for n in range(10)]


def build_total_page(stats: dict[str, Any]) -> str:
    tables = {w: total_stats(stats, w) for w in (30, 60, 100)}
    rows = []
    for n in range(10):
        r30, r60, r100 = (tables[w][n] for w in (30,60,100))
        share = round(r60["hits"] * 100 / max(1, 27*r60["window"]), 2)
        rows.append(f'<tr><td><b>Tổng {n}</b></td><td>{r30["hits"]}</td><td>{r60["hits"]}</td><td>{r100["hits"]}</td><td>{r60["days"]}/{r60["window"]}</td><td>{share}%</td></tr>')
    updated = dmy(str(stats["updated_through"]))
    body = f'''<main><section class="portal-page-intro"><p class="eyebrow">THỐNG KÊ THEO TỔNG 0–9</p><h1>Thống kê tổng hai chữ số XSMB</h1><p>Tổng được tính bằng (hàng chục + hàng đơn vị) lấy chữ số cuối. Bảng dùng đủ 27 mã mỗi ngày và dữ liệu đến {updated}.</p></section><div class="portal-v2-wrap"><section class="portal-v2-card"><h2>Phân bố tổng trong 30–100 kỳ</h2><div class="portal-v2-scroll"><table class="portal-v2-table"><thead><tr><th>Tổng</th><th>Nháy/30</th><th>Nháy/60</th><th>Nháy/100</th><th>Ngày có/60</th><th>Tỷ trọng/60</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class="portal-v3-note">Tỷ trọng là số nháy của tổng chia cho toàn bộ 27 × số kỳ trong cửa sổ, chỉ mô tả lịch sử.</p></section><section class="portal-v2-card"><h2>Đọc cùng các bảng khác</h2><div class="portal-related"><a href="/thong-ke-dau-duoi-xsmb/">Đầu/đuôi 0–9</a><a href="/tan-suat-xsmb/">Tần suất 00–99</a><a href="/thong-ke-theo-thu-xsmb/">Theo thứ</a><a href="/tra-cuu-xsmb/">Tra cứu bộ số</a></div></section></div></main>'''
    return shell("Thống kê tổng XSMB 0–9 theo 30–100 kỳ | Lê Miền Bắc", "Thống kê tổng hai chữ số XSMB từ 0 đến 9 theo 30, 60 và 100 kỳ, gồm tổng nháy, số ngày xuất hiện và tỷ trọng.", "/thong-ke-tong-xsmb/", body)


def weekday_groups(stats: dict[str, Any]) -> dict[int, list[list[str]]]:
    groups: dict[int, list[list[str]]] = defaultdict(list)
    for row in stats.get("recent_history") or []:
        groups[date.fromisoformat(str(row[0])).weekday()].append(row)
    return groups


def top_for_weekday(rows: list[list[str]], limit_draws: int = 52, topn: int = 12) -> list[dict[str, Any]]:
    selected = rows[-limit_draws:]
    hits = Counter(); days = Counter()
    for row in selected:
        c = Counter(str(x).zfill(2)[-2:] for x in row[1:28])
        hits.update(c)
        for code in c: days[code] += 1
    ranked = sorted(days, key=lambda code: (-days[code], -hits[code], code))[:topn]
    return [{"code": code, "days": days[code], "hits": hits[code], "draws": len(selected)} for code in ranked]


def build_weekday_page(stats: dict[str, Any]) -> str:
    groups = weekday_groups(stats)
    target = date.fromisoformat(str(stats["updated_through"])) + timedelta(days=1)
    target_wd = target.weekday()
    cards = []
    for wd in range(7):
        top = top_for_weekday(groups.get(wd, []))
        rows = "".join(f'<tr><td><b>{r["code"]}</b></td><td>{r["days"]}/{r["draws"]}</td><td>{r["hits"]}</td><td>{round(r["days"]*100/max(1,r["draws"]),1)}%</td></tr>' for r in top)
        cls = " is-target-weekday" if wd == target_wd else ""
        badge = f'<span class="portal-v3-badge">Ngày kế tiếp {dmy(target.isoformat())}</span>' if wd == target_wd else ""
        cards.append(f'<section class="portal-v2-card portal-weekday-card{cls}"><div class="portal-v3-card-head"><h2>{WEEKDAY[wd]}</h2>{badge}</div><p>Phân bố trên {len(groups.get(wd, [])[-52:])} kỳ {WEEKDAY[wd].lower()} gần nhất.</p><div class="portal-v2-scroll"><table class="portal-v2-table"><thead><tr><th>Số</th><th>Ngày có mặt</th><th>Nháy</th><th>Tỷ lệ ngày</th></tr></thead><tbody>{rows}</tbody></table></div></section>')
    body = f'''<main><section class="portal-page-intro"><p class="eyebrow">THỐNG KÊ THEO THỨ</p><h1>Tần suất 00–99 theo ngày trong tuần</h1><p>Mỗi bảng dùng tối đa 52 kỳ cùng thứ gần nhất trong 365 ngày dữ liệu công khai. Ngày kế tiếp sau data lock là {WEEKDAY[target_wd]} {dmy(target.isoformat())}.</p></section><div class="portal-v2-wrap"><div class="portal-weekday-grid">{''.join(cards)}</div><section class="portal-v2-card"><h2>Lưu ý khi đọc</h2><p>Khác biệt giữa các thứ chỉ là mô tả lịch sử. Việc một số từng xuất hiện nhiều vào một thứ không tạo nghĩa vụ phải lặp lại trong kỳ kế tiếp.</p><div class="portal-related"><a href="/tan-suat-xsmb/">Tần suất chung</a><a href="/thong-ke-tong-xsmb/">Theo tổng</a><a href="/thong-ke-dau-duoi-xsmb/">Đầu/đuôi</a><a href="/tra-cuu-xsmb/">Tra cứu</a></div></section></div></main>'''
    return shell("Thống kê XSMB theo thứ trong tuần | Lê Miền Bắc", "Tần suất số 00–99 theo Thứ Hai đến Chủ Nhật, dựa trên tối đa 52 kỳ cùng thứ gần nhất trong 365 ngày dữ liệu XSMB.", "/thong-ke-theo-thu-xsmb/", body)


def latest_headtail(stats: dict[str, Any]) -> str:
    row = (stats.get("recent_history") or [])[-1]
    codes = [str(x).zfill(2)[-2:] for x in row[1:28]]
    heads: dict[str, list[str]] = {str(i): [] for i in range(10)}
    tails: dict[str, list[str]] = {str(i): [] for i in range(10)}
    for code in codes:
        heads[code[0]].append(code[1]); tails[code[1]].append(code[0])
    left = "".join(f'<tr><td><b>{d}</b></td><td>{", ".join(heads[d]) or "—"}</td></tr>' for d in map(str, range(10)))
    right = "".join(f'<tr><td><b>{d}</b></td><td>{", ".join(tails[d]) or "—"}</td></tr>' for d in map(str, range(10)))
    return f'''<section class="portal-section portal-headtail-latest"><div class="portal-wrap"><div class="portal-section-title"><div><h2>Bảng đầu–đuôi kỳ gần nhất</h2><p>XSMB {dmy(str(row[0]))} · gom trực tiếp từ 27 mã đã công bố.</p></div><a href="/thong-ke-dau-duoi-xsmb/">Thống kê 30–100 kỳ →</a></div><div class="portal-headtail-grid"><article class="portal-card"><h3>Theo đầu</h3><table class="portal-v3-mini"><tbody>{left}</tbody></table></article><article class="portal-card"><h3>Theo đuôi</h3><table class="portal-v3-mini"><tbody>{right}</tbody></table></article></div></div></section>'''


def patch_home(path: Path, stats: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    if "portal-headtail-latest" not in text:
        marker = '<section class="portal-section"><div class="portal-wrap"><div class="portal-section-title"><div><h2>Công cụ thống kê XSMB</h2>'
        if marker not in text: raise ValueError("home tools marker missing")
        text = text.replace(marker, latest_headtail(stats) + marker, 1)
    tools = [
        ('/thong-ke-tong-xsmb/', 'Theo tổng 0–9', 'Tổng nháy, ngày có mặt, tỷ trọng', 'Xem tổng →'),
        ('/thong-ke-theo-thu-xsmb/', 'Thống kê theo thứ', 'Tần suất 00–99 theo từng ngày trong tuần', 'Xem theo thứ →'),
    ]
    anchor = '<a class="portal-card portal-tool" href="/tra-cuu-xsmb/">'
    for href, title, desc, cta in reversed(tools):
        if href not in text:
            card = f'<a class="portal-card portal-tool" href="{href}"><b>{title}</b><span>{desc}</span><em>{cta}</em></a>'
            text = text.replace(anchor, card + anchor, 1)
    text = re.sub(r'(<nav class="portal-nav"[^>]*>).*?(</nav>)', lambda m: m.group(1)+common_nav('/', True)+m.group(2), text, count=1, flags=re.S)
    text = text.replace('portal-v2.css?v=20260815-2', f'portal-v2.css?v={VERSION}')
    path.write_text(text, encoding="utf-8")


def patch_navs(text: str, route: str) -> str:
    if 'class="portal-site-nav"' in text:
        text = re.sub(r'(<nav class="portal-site-nav"[^>]*>).*?(</nav>)', lambda m: m.group(1)+common_nav(route)+m.group(2), text, count=1, flags=re.S)
    text = text.replace('portal-v2.css?v=20260815-2', f'portal-v2.css?v={VERSION}')
    return text


def breadcrumb(route: str) -> str:
    if route == "/": return ""
    label = LABELS.get(route, "Trang")
    return f'<nav class="portal-breadcrumbs" aria-label="Đường dẫn"><a href="/">Trang chủ</a><span aria-hidden="true">›</span><span aria-current="page">{esc(label)}</span></nav>'


def add_breadcrumb(text: str, route: str) -> str:
    if route == "/" or "portal-breadcrumbs" in text: return text
    crumb = breadcrumb(route)
    m = re.search(r'<div class="portal-contextbar">.*?</div></div>', text, flags=re.S)
    if m:
        return text[:m.end()] + crumb + text[m.end():]
    return text.replace('<main', crumb+'<main', 1)


def add_schema(text: str, route: str, stats: dict[str, Any]) -> str:
    marker = '"@id":"https://lemienbac.com/#portal-v3"'
    if marker in text: return text
    title_m = re.search(r'<title>(.*?)</title>', text, flags=re.I|re.S)
    desc_m = re.search(r'<meta name="description" content="([^"]*)"', text, flags=re.I)
    title = re.sub('<[^>]+>', '', title_m.group(1)).strip() if title_m else LABELS.get(route, 'Lê Miền Bắc')
    desc = html.unescape(desc_m.group(1)) if desc_m else 'Cổng dữ liệu và thống kê XSMB.'
    url = BASE + route
    graph: list[dict[str, Any]] = [{"@type":"WebPage","@id":url+"#webpage","url":url,"name":title,"description":desc,"inLanguage":"vi-VN","dateModified":stats["updated_through"]}]
    if route != "/":
        graph.append({"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Trang chủ","item":BASE+"/"},{"@type":"ListItem","position":2,"name":LABELS.get(route,"Trang"),"item":url}]})
    else:
        graph.append({"@type":"WebSite","@id":BASE+"/#website","url":BASE+"/","name":"Lê Miền Bắc","inLanguage":"vi-VN"})
    if route in STAT_PATHS:
        graph.append({"@type":"Dataset","name":"Lịch sử 27 mã XSMB cho thống kê công khai","description":"Lịch sử 27 mã hai chữ số mỗi ngày dùng cho thống kê tần suất, lô gan, cặp đảo, đầu đuôi, tổng và theo thứ.","temporalCoverage":f'{stats["first_date"]}/{stats["updated_through"]}',"dateModified":stats["updated_through"],"url":url,"measurementTechnique":"Thống kê mô tả từ 27 mã kết quả đã công bố mỗi ngày"})
    doc = {"@context":"https://schema.org","@id":"https://lemienbac.com/#portal-v3","@graph":graph}
    block = '<script type="application/ld+json">'+json.dumps(doc,ensure_ascii=False,separators=(",",":"))+'</script>'
    return text.replace('</head>', block+'</head>', 1)


def patch_all_pages(root: Path, stats: dict[str, Any]) -> int:
    count = 0
    for path in root.rglob('*.html'):
        route = route_for(path, root)
        text = path.read_text(encoding='utf-8')
        if route != '/': text = patch_navs(text, route)
        text = add_breadcrumb(text, route)
        text = add_schema(text, route, stats)
        path.write_text(text, encoding='utf-8'); count += 1
    return count


def update_sitemap(root: Path, updated: str) -> None:
    path = root/'sitemap.xml'; text = path.read_text(encoding='utf-8')
    add = ''.join(f'  <url><loc>{BASE}{route}</loc><lastmod>{updated}</lastmod></url>\n' for route in NEW_PATHS if BASE+route not in text)
    if add: text = text.replace('</urlset>', add+'</urlset>')
    path.write_text(text, encoding='utf-8')


def apply(root: Path) -> dict[str, Any]:
    stats = load(root/'statistics-data.json')
    if len(stats.get('recent_history') or []) < 100: raise ValueError('history too short')
    (root/'thong-ke-tong-xsmb').mkdir(exist_ok=True)
    (root/'thong-ke-tong-xsmb/index.html').write_text(build_total_page(stats), encoding='utf-8')
    (root/'thong-ke-theo-thu-xsmb').mkdir(exist_ok=True)
    (root/'thong-ke-theo-thu-xsmb/index.html').write_text(build_weekday_page(stats), encoding='utf-8')
    patch_home(root/'index.html', stats)
    pages = patch_all_pages(root, stats)
    update_sitemap(root, str(stats['updated_through']))
    return {'status':'PASS','new_pages':2,'html_pages':pages,'updated_through':stats['updated_through']}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rows=[]
        start=date(2026,1,1)
        for i in range(120): rows.append([(start+timedelta(days=i)).isoformat(), *[f'{(i+j)%100:02d}' for j in range(27)]])
        stats={'first_date':rows[0][0],'updated_through':rows[-1][0],'recent_history':rows}
        (root/'statistics-data.json').write_text(json.dumps(stats),encoding='utf-8')
        (root/'index.html').write_text('<html><head><title>X</title><meta name="description" content="Y"><link rel="stylesheet" href="/portal-v2.css?v=20260815-2"></head><body><nav class="portal-nav"></nav><main><section class="portal-section"><div class="portal-wrap"><div class="portal-section-title"><div><h2>Công cụ thống kê XSMB</h2></div></div><div><a class="portal-card portal-tool" href="/tra-cuu-xsmb/"></a></div></div></section></main></body></html>',encoding='utf-8')
        (root/'sitemap.xml').write_text('<?xml version="1.0"?><urlset></urlset>',encoding='utf-8')
        result=apply(root)
        assert result['new_pages']==2
        home=(root/'index.html').read_text(encoding='utf-8')
        assert 'portal-headtail-latest' in home and '/thong-ke-tong-xsmb/' in home and '/thong-ke-theo-thu-xsmb/' in home
        assert (root/'thong-ke-tong-xsmb/index.html').exists() and (root/'thong-ke-theo-thu-xsmb/index.html').exists()
    print('PORTAL_V3_SELF_TEST_OK')


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--output-root',type=Path,default=ROOT/'_site'); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    if a.self_test: self_test()
    else: print(json.dumps(apply(a.output_root),ensure_ascii=False))


if __name__=='__main__': main()
