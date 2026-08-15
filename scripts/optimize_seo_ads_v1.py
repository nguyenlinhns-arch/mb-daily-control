#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://lemienbac.com"

DATA_PAGES = {
    "thong-ke-xsmb/index.html": "Thống kê",
    "tan-suat-xsmb/index.html": "Tần suất",
    "lo-gan-xsmb/index.html": "Lô gan",
    "cap-dao-xsmb/index.html": "Cặp đảo",
    "thong-ke-dau-duoi-xsmb/index.html": "Đầu/đuôi",
    "thong-ke-tong-xsmb/index.html": "Theo tổng",
    "thong-ke-theo-thu-xsmb/index.html": "Theo thứ",
    "tra-cuu-xsmb/index.html": "Tra cứu",
}
NEW_ROUTES = {
    "/xsmb-30-ngay/": "XSMB 30 ngày",
    "/nguon-du-lieu-xsmb/": "Nguồn dữ liệu",
}
FORBIDDEN_AD_DESTINATION = (
    "4so",
    "gợi ý số",
    "báo cáo ai",
    "báo cáo mẫu",
    "nhận báo cáo",
)
MONETIZATION_TOKENS = (
    "data-open-checkout",
    "/?checkout=1",
    "accesslanding.site",
    "effectivecpmnetwork.com",
    "highperformanceformat.com",
    "lm-adsterra",
    "affiliate-shopee",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def dmy(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def route_for(rel: str) -> str:
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[:-10]
    return "/" + rel


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def visible_text(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def data_nav(active: str = "") -> str:
    items = [
        ("/thong-ke-xsmb/", "Thống kê"),
        ("/xsmb-30-ngay/", "30 ngày"),
        ("/tan-suat-xsmb/", "Tần suất"),
        ("/lo-gan-xsmb/", "Lô gan"),
        ("/cap-dao-xsmb/", "Cặp đảo"),
        ("/thong-ke-dau-duoi-xsmb/", "Đầu/đuôi"),
        ("/thong-ke-tong-xsmb/", "Theo tổng"),
        ("/thong-ke-theo-thu-xsmb/", "Theo thứ"),
        ("/tra-cuu-xsmb/", "Tra cứu"),
        ("/nguon-du-lieu-xsmb/", "Nguồn"),
    ]
    return "".join(
        f'<a class="{"is-active" if href == active else ""}" href="{href}">{label}</a>'
        for href, label in items
    )


def header(active: str, updated: str) -> str:
    return f'''<header class="portal-site-header" data-portal-shell="v1" data-seo-cluster="statistics">
  <div class="portal-site-head">
    <a class="portal-site-brand" href="/thong-ke-xsmb/" aria-label="Lê Miền Bắc - Thống kê XSMB"><span class="portal-site-brand-mark">LM</span><span><strong>LÊ MIỀN BẮC</strong><small>DỮ LIỆU · THỐNG KÊ XSMB</small></span></a>
    <nav class="portal-site-nav" aria-label="Điều hướng dữ liệu XSMB">{data_nav(active)}</nav>
  </div>
</header>
<div class="portal-contextbar"><div class="portal-contextbar-inner"><span>Dữ liệu XSMB đã hoàn tất đến <b>{dmy(updated)}</b> · 27/27 mã mỗi kỳ</span><a href="/nguon-du-lieu-xsmb/">Nguồn & cách tính →</a></div></div>'''


def footer() -> str:
    return '''<footer class="portal-site-footer" data-portal-shell-footer="v1" data-seo-cluster="statistics">
  <div class="portal-site-footer-inner">
    <div><strong>LÊ MIỀN BẮC</strong><p>Cổng dữ liệu và thống kê XSMB. Các bảng chỉ mô tả dữ liệu đã công bố, không có chức năng mua vé, thanh toán hoặc tham gia trò chơi.</p></div>
    <nav class="portal-site-footer-nav" aria-label="Liên kết dữ liệu cuối trang"><a href="/thong-ke-xsmb/">Trung tâm thống kê</a><a href="/xsmb-30-ngay/">XSMB 30 ngày</a><a href="/tan-suat-xsmb/">Tần suất 00–99</a><a href="/lo-gan-xsmb/">Lô gan XSMB</a><a href="/cap-dao-xsmb/">45 cặp đảo</a><a href="/thong-ke-dau-duoi-xsmb/">Đầu/đuôi 0–9</a><a href="/thong-ke-tong-xsmb/">Theo tổng 0–9</a><a href="/thong-ke-theo-thu-xsmb/">Theo thứ</a><a href="/tra-cuu-xsmb/">Tra cứu bộ số</a><a href="/nguon-du-lieu-xsmb/">Nguồn dữ liệu & cách tính</a><a href="/gioi-thieu/">Giới thiệu</a><a href="/legal.html">Điều khoản & bảo mật</a></nav>
  </div>
  <div class="portal-site-footer-bottom">© 2026 Lê Miền Bắc · Dữ liệu công khai và thống kê mô tả.</div>
</footer>'''


def breadcrumb(label: str) -> str:
    return f'<nav class="portal-breadcrumbs" aria-label="Đường dẫn"><a href="/thong-ke-xsmb/">Thống kê XSMB</a><span aria-hidden="true">›</span><span aria-current="page">{esc(label)}</span></nav>'


def replace_shell(text: str, active: str, label: str, updated: str) -> str:
    text = re.sub(
        r'<header class="portal-site-header".*?</header>\s*<div class="portal-contextbar">.*?</div></div>',
        header(active, updated),
        text,
        count=1,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'<nav class="portal-breadcrumbs".*?</nav>',
        breadcrumb(label),
        text,
        count=1,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'<footer class="portal-site-footer".*?</footer>',
        footer(),
        text,
        count=1,
        flags=re.I | re.S,
    )
    if '<body class="portal-subpage"' in text and 'data-stats-cluster=' not in text:
        text = text.replace('<body class="portal-subpage"', '<body class="portal-subpage" data-stats-cluster="true"', 1)
    return text


def upsert_title_desc(text: str, title: str, desc: str) -> str:
    title_tag = f"<title>{esc(title)}</title>"
    if re.search(r"<title>.*?</title>", text, flags=re.I | re.S):
        text = re.sub(r"<title>.*?</title>", title_tag, text, count=1, flags=re.I | re.S)
    else:
        text = text.replace("</head>", title_tag + "</head>", 1)
    desc_tag = f'<meta name="description" content="{esc(desc)}">'
    pattern = re.compile(r'<meta\s+name="description"\s+content="[^"]*"\s*/?>', re.I)
    if pattern.search(text):
        text = pattern.sub(desc_tag, text, count=1)
    else:
        text = text.replace("</head>", desc_tag + "</head>", 1)
    return text


def clean_main_copy(text: str) -> str:
    replacements = (
        (
            'đây là thống kê mô tả dữ liệu đã công bố. Khoảng vắng không có nghĩa một số “đến hạn” phải xuất hiện. Các trang này không công bố Top 2 canonical, Score hay thứ hạng 4SO.',
            'đây là thống kê mô tả dữ liệu đã công bố. Khoảng vắng không có nghĩa một số “đến hạn” phải xuất hiện. Các bảng không tạo kết luận cho kỳ chưa diễn ra.',
        ),
        (
            'Mỗi cặp chỉ giữ một chiều duy nhất và loại số kép. Đây là bảng mô tả công khai, không phải thứ hạng 4SO.',
            'Mỗi cặp chỉ giữ một chiều duy nhất và loại số kép. Đây là bảng thống kê mô tả từ dữ liệu đã công bố.',
        ),
        (
            'Các trang này không công bố Top 2 canonical, Score hay thứ hạng 4SO.',
            'Các bảng không tạo kết luận cho kỳ chưa diễn ra.',
        ),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def insert_ads_trust(text: str, updated: str) -> str:
    marker = 'data-google-ads-landing="true"'
    if marker in text:
        return text
    trust = f'''<section class="panel seo-ads-trust" {marker}><div class="head"><div><p class="eyebrow">TRANG DỮ LIỆU THỐNG KÊ</p><h2>Minh bạch nguồn và phạm vi sử dụng</h2></div></div><div class="seo-ads-trust-grid"><div><b>Dữ liệu đã hoàn tất</b><span>Cập nhật đến {dmy(updated)}; mỗi kỳ đủ 27 mã.</span></div><div><b>Không có giao dịch trên trang</b><span>Không có chức năng mua vé, thanh toán hoặc tham gia trò chơi.</span></div><div><b>Thống kê mô tả</b><span>Tần suất và khoảng vắng không phải cam kết cho kỳ tiếp theo.</span></div></div><p><a href="/nguon-du-lieu-xsmb/">Xem nguồn dữ liệu và định nghĩa từng chỉ số →</a></p></section>'''
    hero_end = text.find('</section>', text.find('<section class="hero"'))
    if hero_end < 0:
        raise ValueError("Statistics landing hero not found")
    hero_end += len('</section>')
    return text[:hero_end] + trust + text[hero_end:]


def add_inline_css(text: str) -> str:
    if 'id="seo-ads-v1-style"' in text:
        return text
    css = '''<style id="seo-ads-v1-style">
.seo-ads-trust-grid,.seo-method-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.seo-ads-trust-grid>div,.seo-method-grid>div{padding:12px;border:1px solid #e1e6ea;border-radius:10px;background:#fafbfc}.seo-ads-trust-grid b,.seo-method-grid b{display:block;color:#172536}.seo-ads-trust-grid span,.seo-method-grid span{display:block;margin-top:4px;color:#63727e;font-size:12px;line-height:1.45}.seo30-list{display:grid;gap:9px}.seo30-day{display:grid;grid-template-columns:130px 1fr;gap:10px;align-items:start;padding:11px;border:1px solid #e1e6ea;border-radius:11px;background:#fff}.seo30-date b{display:block}.seo30-date span{font-size:11px;color:#74818b}.seo30-codes{display:grid;grid-template-columns:repeat(9,minmax(0,1fr));gap:5px}.seo30-codes span{display:grid;place-items:center;min-height:30px;border:1px solid #e3e7eb;border-radius:7px;background:#fafbfc;font-weight:800;font-size:12px}.seo-source-list{display:grid;gap:9px}.seo-source-card{padding:13px;border:1px solid #e1e6ea;border-radius:11px;background:#fff}.seo-source-card a{color:#a70e15;font-weight:800}.seo-source-card code{word-break:break-all;font-size:10px;color:#64727d}.seo-definition-table{width:100%;border-collapse:collapse}.seo-definition-table th,.seo-definition-table td{padding:9px;border-bottom:1px solid #e7ebee;text-align:left;vertical-align:top}.seo-definition-table th{width:160px;color:#172536}@media(max-width:700px){.seo-ads-trust-grid,.seo-method-grid{grid-template-columns:1fr}.seo30-day{grid-template-columns:1fr}.seo30-codes{grid-template-columns:repeat(6,minmax(0,1fr))}.seo-definition-table th{width:110px}}
</style>'''
    return text.replace("</head>", css + "</head>", 1)


def clean_data_cluster(root: Path, updated: str) -> dict[str, int]:
    cleaned = 0
    for rel, label in DATA_PAGES.items():
        path = root / rel
        if not path.is_file():
            continue
        route = route_for(rel)
        text = path.read_text(encoding="utf-8")
        text = replace_shell(text, route, label, updated)
        text = clean_main_copy(text)
        text = add_inline_css(text)
        if rel == "thong-ke-xsmb/index.html":
            text = upsert_title_desc(
                text,
                f"Thống kê XSMB đến {dmy(updated)}: 00–99, tần suất, lô gan | Lê Miền Bắc",
                f"Thống kê XSMB cập nhật đến {dmy(updated)}: ma trận 00–99, tần suất 7–365 kỳ, lô gan, cặp đảo và tra cứu lịch sử từ dữ liệu 27 mã mỗi kỳ.",
            )
            text = insert_ads_trust(text, updated)
        path.write_text(text, encoding="utf-8")
        validate_clean_page(path)
        cleaned += 1
    if not (root / "thong-ke-xsmb/index.html").is_file():
        raise ValueError("Missing core statistics landing")
    return {"pages_cleaned": cleaned}


def schema_block(route: str, title: str, desc: str, updated: str, start: str | None = None) -> str:
    graph: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": BASE + route + "#webpage",
            "url": BASE + route,
            "name": title,
            "description": desc,
            "inLanguage": "vi-VN",
            "dateModified": updated,
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Thống kê XSMB", "item": BASE + "/thong-ke-xsmb/"},
                {"@type": "ListItem", "position": 2, "name": title.split(" | ")[0], "item": BASE + route},
            ],
        },
    ]
    dataset: dict[str, Any] = {
        "@type": "Dataset",
        "name": title.split(" | ")[0],
        "description": desc,
        "url": BASE + route,
        "inLanguage": "vi-VN",
        "dateModified": updated,
        "isAccessibleForFree": True,
    }
    if start:
        dataset["temporalCoverage"] = f"{start}/{updated}"
    graph.append(dataset)
    doc = {"@context": "https://schema.org", "@graph": graph}
    return '<script type="application/ld+json">' + json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + '</script>'


def replace_schema(text: str, block: str) -> str:
    text = re.sub(r'<script type="application/ld\+json">.*?</script>', '', text, flags=re.I | re.S)
    return text.replace("</head>", block + "</head>", 1)


def replace_main(text: str, main: str) -> str:
    out, count = re.subn(r'<main\b[^>]*>.*?</main>', main, text, count=1, flags=re.I | re.S)
    if count != 1:
        raise ValueError("Expected exactly one main element")
    return out


def build_30_day_page(root: Path, stats: dict[str, Any]) -> Path:
    updated = str(stats["updated_through"])
    history = list(stats.get("recent_history") or [])[-30:]
    if len(history) != 30:
        raise ValueError(f"Need 30 completed draws, got {len(history)}")
    history_desc = list(reversed(history))
    numbers = list(stats.get("numbers") or [])
    top = sorted(
        numbers,
        key=lambda row: (
            -int((row.get("windows") or {}).get("30", {}).get("days_seen", 0)),
            -int((row.get("windows") or {}).get("30", {}).get("hits", 0)),
            str(row.get("code") or ""),
        ),
    )[:10]
    title = f"XSMB 30 ngày đến {dmy(updated)}: lịch sử 27 mã và tần suất | Lê Miền Bắc"
    desc = f"XSMB 30 ngày gần nhất đến {dmy(updated)}: 30 kỳ đã hoàn tất, đủ 27 mã mỗi kỳ, kèm tần suất 00–99 và giải thích cách đọc dữ liệu."
    rows = []
    for row in history_desc:
        day = str(row[0]); codes = [str(x).zfill(2)[-2:] for x in row[1:28]]
        if len(codes) != 27:
            raise ValueError(f"Invalid 27-code row: {day}")
        counts: dict[str, int] = {}
        for code in codes:
            counts[code] = counts.get(code, 0) + 1
        repeats = sum(v - 1 for v in counts.values() if v > 1)
        rows.append(
            f'<article class="seo30-day"><div class="seo30-date"><b>{dmy(day)}</b><span>27 mã · {len(counts)} mã khác nhau{f" · {repeats} nháy lặp" if repeats else ""}</span></div><div class="seo30-codes">'
            + "".join(f"<span>{esc(code)}</span>" for code in codes)
            + "</div></article>"
        )
    top_rows = "".join(
        f'<tr><td><b>{esc(row["code"])}</b></td><td>{int(row["windows"]["30"]["days_seen"])}/30</td><td>{int(row["windows"]["30"]["hits"])}</td><td>{float(row["windows"]["30"]["rate"]):.1f}%</td></tr>'
        for row in top
    )
    first = str(history[0][0])
    main = f'''<main class="main" data-seo-page="xsmb-30-ngay"><div class="source"><b>30 kỳ đã hoàn tất: {dmy(first)} – {dmy(updated)}</b><span>27/27 mã mỗi kỳ · tổng {30*27} mã trong cửa sổ</span></div><section class="hero"><p class="eyebrow">XSMB 30 NGÀY</p><h1>XSMB 30 ngày gần nhất: lịch sử 27 mã mỗi kỳ</h1><p>Trang tổng hợp đúng 30 kỳ XSMB đã hoàn tất đến {dmy(updated)}. Dữ liệu được trình bày để tra cứu lịch sử và tần suất, không tạo kết luận cho kỳ chưa diễn ra.</p><div class="actions"><a href="/thong-ke-xsmb/">Ma trận 00–99</a><a href="/tan-suat-xsmb/">Tần suất nhiều cửa sổ</a><a href="/nguon-du-lieu-xsmb/">Nguồn & cách tính</a></div></section><section class="panel"><div class="head"><div><p class="eyebrow">NHÌN NHANH 30 KỲ</p><h2>10 số có nhiều ngày xuất hiện nhất</h2></div></div><div class="table-wrap"><table><thead><tr><th>Số</th><th>Ngày có mặt</th><th>Tổng nháy</th><th>Tỷ lệ ngày</th></tr></thead><tbody>{top_rows}</tbody></table></div><p>Cùng số lần “ngày có mặt”, bảng ưu tiên số có tổng nháy cao hơn. Đây là thống kê mô tả, không phải xếp hạng dự đoán.</p></section><section class="panel"><div class="head"><div><p class="eyebrow">LỊCH SỬ 30 KỲ</p><h2>27 mã theo từng ngày</h2></div></div><div class="seo30-list">{''.join(rows)}</div></section><section class="panel"><div class="head"><div><p class="eyebrow">CÁCH ĐỌC</p><h2>“Ngày có mặt” và “nháy” khác nhau thế nào?</h2></div></div><div class="seo-method-grid"><div><b>Ngày có mặt</b><span>Một số xuất hiện ít nhất một lần trong 27 mã của ngày đó thì tính 1 ngày.</span></div><div><b>Tổng nháy</b><span>Đếm toàn bộ số lần xuất hiện, nên một ngày có thể đóng góp nhiều hơn 1 nháy.</span></div><div><b>Cửa sổ 30 kỳ</b><span>Luôn lấy đúng 30 kỳ đã hoàn tất gần nhất và tự trượt khi dữ liệu mới được khóa.</span></div></div></section></main>'''
    template = (root / "thong-ke-xsmb/index.html").read_text(encoding="utf-8")
    text = replace_main(template, main)
    text = replace_shell(text, "/xsmb-30-ngay/", "XSMB 30 ngày", updated)
    text = upsert_title_desc(text, title, desc)
    text = add_inline_css(text)
    text = replace_schema(text, schema_block("/xsmb-30-ngay/", title, desc, updated, first))
    out = root / "xsmb-30-ngay/index.html"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text, encoding="utf-8")
    validate_clean_page(out)
    return out


def build_source_page(root: Path, stats: dict[str, Any], source: dict[str, Any]) -> Path:
    updated = str(stats["updated_through"])
    title = "Nguồn dữ liệu XSMB và cách tính thống kê | Lê Miền Bắc"
    desc = f"Nguồn dữ liệu XSMB, quy trình đối chiếu 27/27 mã và định nghĩa tần suất, nháy, lô gan, cặp đảo. Dữ liệu hiện khóa đến {dmy(updated)}."
    source_cards = []
    for item in source.get("sources") or []:
        name = esc(item.get("name") or "Nguồn công khai")
        url = str(item.get("url") or "")
        sha = esc(item.get("codes_sha256") or "")
        link = f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">Mở bản đối chiếu công khai →</a>' if url.startswith("https://") else ""
        source_cards.append(f'<article class="seo-source-card"><b>{name}</b><p>{link}</p><code>SHA-256 mã kỳ cuối: {sha}</code></article>')
    main = f'''<main class="main" data-seo-page="nguon-du-lieu"><div class="source"><b>Dữ liệu khóa đến {dmy(updated)}</b><span>{int(source.get("history_rows") or stats.get("row_count") or 0)} kỳ · {int(source.get("source_count") or 0)} nguồn đối chiếu công khai · trạng thái {esc(source.get("status") or "")}</span></div><section class="hero"><p class="eyebrow">NGUỒN DỮ LIỆU XSMB</p><h1>Nguồn dữ liệu và cách tính các bảng thống kê</h1><p>Trang này giải thích dữ liệu nào được dùng, khi nào một kỳ được chấp nhận và ý nghĩa của từng chỉ số trên Lê Miền Bắc. Mục tiêu là để người đọc có thể kiểm tra lại cách các bảng công khai được tạo.</p><div class="actions"><a href="/thong-ke-xsmb/">Trung tâm thống kê</a><a href="/xsmb-30-ngay/">XSMB 30 ngày</a></div></section><section class="panel"><div class="head"><div><p class="eyebrow">QUY TẮC KHÓA DỮ LIỆU</p><h2>Chỉ dùng kỳ đã hoàn tất và đủ 27 mã</h2></div></div><div class="seo-method-grid"><div><b>27/27 mã</b><span>Một ngày chỉ được đưa vào thống kê khi đủ 27 mã hai chữ số.</span></div><div><b>Đối chiếu nhiều nguồn</b><span>Kỳ mới được kiểm tra trên tối thiểu hai nguồn công khai trước khi khóa.</span></div><div><b>Fail-closed</b><span>Nếu nguồn không khớp hoặc thiếu dữ liệu, hệ thống không coi kỳ đó là dữ liệu hoàn tất.</span></div></div><p>Lịch sử công khai hiện từ <b>{dmy(str(source.get("history_start") or stats.get("first_date")))}</b> đến <b>{dmy(updated)}</b>.</p></section><section class="panel"><div class="head"><div><p class="eyebrow">NGUỒN ĐỐI CHIẾU</p><h2>Các bản công khai của kỳ gần nhất</h2></div></div><div class="seo-source-list">{''.join(source_cards)}</div></section><section class="panel"><div class="head"><div><p class="eyebrow">ĐỊNH NGHĨA CHỈ SỐ</p><h2>Cách đọc thống kê 00–99</h2></div></div><div class="table-wrap"><table class="seo-definition-table"><tbody><tr><th>Ngày có mặt</th><td>Một số xuất hiện ít nhất một lần trong 27 mã của một kỳ thì kỳ đó tính là 1 ngày có mặt.</td></tr><tr><th>Nháy</th><td>Tổng số lần xuất hiện của số trong toàn bộ 27 mã; một kỳ có thể có nhiều nháy của cùng số.</td></tr><tr><th>Gan hiện tại</th><td>Số kỳ đã hoàn tất liên tiếp kể từ lần gần nhất số xuất hiện.</td></tr><tr><th>Gan max</th><td>Khoảng vắng dài nhất quan sát được trong phạm vi dữ liệu của bảng.</td></tr><tr><th>Cặp đảo</th><td>Hai số đảo vị trí chữ số, ví dụ 06–60; số kép được loại khỏi tập 45 cặp đảo.</td></tr><tr><th>Cửa sổ</th><td>7, 14, 30, 60, 100 hoặc 365 kỳ đã hoàn tất gần nhất tính tại thời điểm trang được xây dựng.</td></tr></tbody></table></div><p>Những chỉ số trên mô tả lịch sử. Việc một số xuất hiện nhiều hoặc đang có khoảng vắng dài không tạo nghĩa vụ phải xuất hiện ở kỳ tiếp theo.</p></section></main>'''
    template = (root / "thong-ke-xsmb/index.html").read_text(encoding="utf-8")
    text = replace_main(template, main)
    text = replace_shell(text, "/nguon-du-lieu-xsmb/", "Nguồn dữ liệu", updated)
    text = upsert_title_desc(text, title, desc)
    text = add_inline_css(text)
    text = replace_schema(text, schema_block("/nguon-du-lieu-xsmb/", title, desc, updated, str(source.get("history_start") or stats.get("first_date"))))
    out = root / "nguon-du-lieu-xsmb/index.html"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text, encoding="utf-8")
    validate_clean_page(out)
    return out


def update_sitemap(root: Path, updated: str) -> dict[str, int]:
    path = root / "sitemap.xml"
    tree = ET.parse(path)
    urlset = tree.getroot(); ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    existing = {str(node.find(ns + "loc").text) for node in urlset.findall(ns + "url") if node.find(ns + "loc") is not None}
    added = 0
    for route in NEW_ROUTES:
        loc_value = BASE + route
        if loc_value in existing:
            continue
        node = ET.SubElement(urlset, ns + "url")
        ET.SubElement(node, ns + "loc").text = loc_value
        ET.SubElement(node, ns + "lastmod").text = updated
        added += 1
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return {"sitemap_added": added}


def validate_clean_page(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    visible = visible_text(text).lower()
    for token in FORBIDDEN_AD_DESTINATION:
        if token in visible:
            raise ValueError(f"Ads-clean visible token in {path}: {token}")
    lower = text.lower()
    for token in MONETIZATION_TOKENS:
        if token in lower:
            raise ValueError(f"Monetization token in data page {path}: {token}")
    if "portal-site-cta" in lower:
        raise ValueError(f"Paid CTA remains in data page {path}")


def apply(root: Path) -> dict[str, Any]:
    stats = load_json(root / "statistics-data.json")
    source = load_json(root / "source-access.json")
    updated = str(stats.get("updated_through") or "")
    date.fromisoformat(updated)
    if updated != str(source.get("history_end") or ""):
        raise ValueError("Statistics/source date mismatch")
    clean = clean_data_cluster(root, updated)
    build_30_day_page(root, stats)
    build_source_page(root, stats, source)
    sitemap = update_sitemap(root, updated)
    validate_clean_page(root / "thong-ke-xsmb/index.html")
    return {"status": "PASS", **clean, **sitemap, "new_pages": 2, "ads_landing": "/thong-ke-xsmb/", "updated_through": updated}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); (root / "thong-ke-xsmb").mkdir(parents=True)
        base = '''<!doctype html><html><head><title>Cũ</title><meta name="description" content="Cũ"><meta name="robots" content="index,follow"><link rel="stylesheet" href="/bundle.css"><script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"Cũ"}</script></head><body class="portal-subpage"><header class="portal-site-header"><div class="portal-site-head"><a href="/">Home</a><a class="portal-site-cta" href="/?checkout=1">Báo cáo 4SO</a></div></header><div class="portal-contextbar"><div class="portal-contextbar-inner"><span>x</span><a href="/">x</a></div></div><nav class="portal-breadcrumbs"><a href="/">Trang chủ</a></nav><main class="main"><section class="hero"><h1>Thống kê</h1></section><p>đây là thống kê mô tả dữ liệu đã công bố. Khoảng vắng không có nghĩa một số “đến hạn” phải xuất hiện. Các trang này không công bố Top 2 canonical, Score hay thứ hạng 4SO.</p></main><footer class="portal-site-footer"><p>Đầu ra 4SO</p></footer><script defer src="/portal-v2.js?v=x"></script></body></html>'''
        (root / "thong-ke-xsmb/index.html").write_text(base, encoding="utf-8")
        history = []
        for day in range(1, 31):
            history.append([f"2026-07-{day:02d}", *[f"{(day+i)%100:02d}" for i in range(27)]])
        numbers = [{"code": f"{i:02d}", "windows": {"30": {"days_seen": i % 20 + 1, "hits": i % 25 + 1, "rate": float(i % 20 + 1) / 30 * 100}}} for i in range(100)]
        stats = {"updated_through": "2026-07-30", "first_date": "2024-01-01", "row_count": 900, "recent_history": history, "numbers": numbers}
        source = {"history_end": "2026-07-30", "history_start": "2024-01-01", "history_rows": 900, "source_count": 2, "status": "LOCKED_CROSSCHECKED_PUBLIC", "sources": [{"name": "source-a", "url": "https://example.com/a", "codes_sha256": "abc"}, {"name": "source-b", "url": "https://example.com/b", "codes_sha256": "abc"}]}
        (root / "statistics-data.json").write_text(json.dumps(stats), encoding="utf-8")
        (root / "source-access.json").write_text(json.dumps(source), encoding="utf-8")
        (root / "sitemap.xml").write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://lemienbac.com/thong-ke-xsmb/</loc><lastmod>2026-07-30</lastmod></url></urlset>', encoding="utf-8")
        result = apply(root)
        landing = (root / "thong-ke-xsmb/index.html").read_text(encoding="utf-8")
        page30 = (root / "xsmb-30-ngay/index.html").read_text(encoding="utf-8")
        source_page = (root / "nguon-du-lieu-xsmb/index.html").read_text(encoding="utf-8")
        assert result["status"] == "PASS" and result["new_pages"] == 2
        assert 'data-google-ads-landing="true"' in landing and "Báo cáo 4SO" not in visible_text(landing)
        assert page30.count('class="seo30-day"') == 30 and "XSMB 30 ngày" in page30
        assert "Nguồn dữ liệu và cách tính" in source_page and "source-a" in source_page
        sitemap = (root / "sitemap.xml").read_text(encoding="utf-8")
        assert "https://lemienbac.com/xsmb-30-ngay/" in sitemap and "https://lemienbac.com/nguon-du-lieu-xsmb/" in sitemap
    print("SEO_ADS_V1_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT / "_site")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(apply(args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
