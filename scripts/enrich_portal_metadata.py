#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://lemienbac.com"
GA4 = "G-R9TBYP97BC"
CONSENT_KEY = "lm_analytics_consent_v1"
HOME_TITLE = "Thống kê XSMB lô tô, lô gan & AI | Lê Miền Bắc"
HOME_DESC = (
    "Thống kê XSMB lô tô từ dữ liệu 27 mã mỗi kỳ: tần suất 00–99, lô gan, "
    "45 cặp đảo, đầu đuôi, theo tổng và tra cứu lịch sử bằng hệ thống AI."
)
HOME_IMAGE_PATH = "/og-seo.svg"
HOME_IMAGE = f"{BASE}{HOME_IMAGE_PATH}"
HOME_IMAGE_ALT = "Lê Miền Bắc - Thống kê XSMB lô tô, tần suất, lô gan và phân tích AI"

TITLE_OVERRIDES = {
    "/": HOME_TITLE,
    "/phuong-phap-cong-khai/": "6 phương pháp XSMB công khai hôm nay | Lê Miền Bắc",
}
DESC_OVERRIDES = {"/": HOME_DESC}
H1_OVERRIDES = {
    "/thong-ke-xsmb/": "Thống kê XSMB: tần suất, lô gan và cặp đảo 00–99",
    "/tan-suat-xsmb/": "Tần suất XSMB 00–99 theo 7–365 kỳ",
    "/lo-gan-xsmb/": "Lô gan XSMB 00–99: khoảng vắng hiện tại",
    "/cap-dao-xsmb/": "Thống kê 45 cặp đảo XSMB",
    "/thong-ke-dau-duoi-xsmb/": "Thống kê đầu đuôi XSMB 0–9",
    "/thong-ke-tong-xsmb/": "Thống kê tổng XSMB 0–9",
    "/thong-ke-theo-thu-xsmb/": "Thống kê XSMB theo thứ trong tuần",
    "/tra-cuu-xsmb/": "Tra cứu XSMB theo bộ số 00–99",
}


def route_for(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    if rel == "index.html": return "/"
    if rel.endswith("/index.html"): return "/" + rel[:-10]
    return "/" + rel


def get_title(text: str) -> str:
    m = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else "Lê Miền Bắc"


def get_desc(text: str) -> str:
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.I)
    return html.unescape(m.group(1)).strip() if m else "Cổng dữ liệu và thống kê XSMB."


def set_title(text: str, value: str) -> str:
    tag = f"<title>{html.escape(value)}</title>"
    if re.search(r"<title>.*?</title>", text, re.I | re.S):
        return re.sub(r"<title>.*?</title>", tag, text, count=1, flags=re.I | re.S)
    return text.replace("</head>", tag + "</head>", 1)


def upsert_meta(text: str, attr: str, key: str, value: str) -> str:
    safe = html.escape(value, quote=True)
    pattern = re.compile(rf'<meta\s+{attr}="{re.escape(key)}"\s+content="[^"]*"\s*/?>', re.I)
    tag = f'<meta {attr}="{key}" content="{safe}">'
    if pattern.search(text): return pattern.sub(tag, text, count=1)
    return text.replace("</head>", tag + "</head>", 1)


def set_first_h1(text: str, value: str) -> str:
    safe = html.escape(value)
    pattern = re.compile(r"(<h1\b[^>]*>).*?(</h1>)", re.I | re.S)
    if pattern.search(text): return pattern.sub(lambda m: m.group(1) + safe + m.group(2), text, count=1)
    return text


def consent_default_js() -> str:
    return (
        "let lmAnalyticsConsent='denied';"
        f"try{{if(localStorage.getItem('{CONSENT_KEY}')==='granted')lmAnalyticsConsent='granted'}}catch(e){{}}"
        "gtag('consent','default',{analytics_storage:lmAnalyticsConsent,ad_storage:'denied',"
        "ad_user_data:'denied',ad_personalization:'denied',wait_for_update:500});"
    )


def normalize_existing_consent(text: str) -> str:
    pattern = re.compile(r"gtag\('consent','default',\{[^;]*?analytics_storage\s*:\s*'denied'[^;]*?\}\);", re.I | re.S)
    if pattern.search(text): return pattern.sub(consent_default_js(), text, count=1)
    if CONSENT_KEY not in text:
        js_call = re.search(r"gtag\('js',\s*new Date\(\)\);", text, re.I)
        if js_call: text = text[:js_call.start()] + consent_default_js() + text[js_call.start():]
    return text


def enrich(path: Path, root: Path) -> bool:
    text = path.read_text(encoding="utf-8"); before = text
    route = route_for(path, root)
    if route in TITLE_OVERRIDES: text = set_title(text, TITLE_OVERRIDES[route])
    if route in DESC_OVERRIDES: text = upsert_meta(text, "name", "description", DESC_OVERRIDES[route])
    if route in H1_OVERRIDES: text = set_first_h1(text, H1_OVERRIDES[route])
    title = get_title(text); desc = get_desc(text); url = BASE + route
    robots = re.search(r'<meta\s+name="robots"\s+content="([^"]+)"', text, re.I)
    noindex = bool(robots and "noindex" in robots.group(1).lower())
    if not noindex:
        for attr, key, value in (
            ("property", "og:locale", "vi_VN"), ("property", "og:type", "website"),
            ("property", "og:site_name", "Lê Miền Bắc"), ("property", "og:url", url),
            ("property", "og:title", title), ("property", "og:description", desc),
            ("name", "twitter:title", title), ("name", "twitter:description", desc),
        ):
            text = upsert_meta(text, attr, key, value)
        if route == "/":
            for attr, key, value in (
                ("property", "og:image", HOME_IMAGE), ("property", "og:image:type", "image/svg+xml"),
                ("property", "og:image:width", "1200"), ("property", "og:image:height", "630"),
                ("property", "og:image:alt", HOME_IMAGE_ALT), ("name", "twitter:card", "summary_large_image"),
                ("name", "twitter:image", HOME_IMAGE), ("name", "twitter:image:alt", HOME_IMAGE_ALT),
            ):
                text = upsert_meta(text, attr, key, value)
        else:
            has_og = bool(re.search(r'<meta\s+property="og:image"\s+content="[^"]+"', text, re.I))
            text = upsert_meta(text, "name", "twitter:card", "summary_large_image" if has_og else "summary")
    if GA4 in text and not noindex:
        text = normalize_existing_consent(text)
    elif not noindex:
        block = (
            '<link rel="preconnect" href="https://www.googletagmanager.com" crossorigin>'
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4}"></script>'
            '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}'
            + consent_default_js() + f"gtag('js',new Date());gtag('config','{GA4}',{{allow_google_signals:false,allow_ad_personalization_signals:false}});</script>"
        )
        text = text.replace("</head>", block + "</head>", 1)
    if text != before: path.write_text(text, encoding="utf-8")
    return text != before


def publish_home_image(root: Path) -> None:
    source = ROOT / "site-v2" / "og-seo.svg"
    if not source.is_file(): raise FileNotFoundError(source)
    shutil.copy2(source, root / "og-seo.svg")


def apply(root: Path) -> dict[str, int]:
    publish_home_image(root)
    pages = changed = ga4 = consent = 0
    for path in root.rglob("*.html"):
        pages += 1; changed += int(enrich(path, root))
        text = path.read_text(encoding="utf-8")
        if GA4 in text: ga4 += 1
        if CONSENT_KEY in text: consent += 1
    if consent != ga4: raise ValueError(f"GA4 consent coverage mismatch: ga4={ga4} consent={consent}")
    for route, expected in H1_OVERRIDES.items():
        rel = route.strip("/") + "/index.html"
        path = root / rel
        if not path.is_file(): continue
        text = path.read_text(encoding="utf-8")
        m = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S)
        value = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else ""
        if value != expected: raise ValueError(f"H1 intent mismatch: {route} / {value}")
    home = root / "index.html"
    if home.is_file():
        text = home.read_text(encoding="utf-8")
        if get_title(text) != HOME_TITLE or get_desc(text) != HOME_DESC: raise ValueError("Homepage SEO mismatch")
        for marker in (HOME_IMAGE, 'content="1200"', 'content="630"', 'name="twitter:card" content="summary_large_image"'):
            if marker not in text: raise ValueError(f"Homepage social metadata missing: {marker}")
        if not (root / "og-seo.svg").is_file(): raise ValueError("Homepage SEO image not published")
    return {"pages": pages, "changed": changed, "ga4_pages": ga4, "consent_pages": consent}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); (root / "phuong-phap-cong-khai").mkdir(); (root / "thong-ke-xsmb").mkdir()
        home = root / "index.html"
        home.write_text('<html><head><title>Cũ</title><meta name="description" content="Cũ"><meta name="robots" content="index,follow"></head><body><h1>Cũ</h1></body></html>', encoding="utf-8")
        p = root / "phuong-phap-cong-khai/index.html"; p.write_text('<html><head><title>Cũ</title><meta name="description" content="Mô tả"><meta name="robots" content="index,follow"></head><body><h1>Methods</h1></body></html>', encoding="utf-8")
        s = root / "thong-ke-xsmb/index.html"; s.write_text('<html><head><title>Stats</title><meta name="description" content="Stats"><meta name="robots" content="index,follow"></head><body><h1>Cũ</h1></body></html>', encoding="utf-8")
        result = apply(root); h = home.read_text(encoding="utf-8")
        assert result["pages"] == 3 and result["ga4_pages"] == result["consent_pages"] == 3
        assert get_title(h) == HOME_TITLE and get_desc(h) == HOME_DESC and HOME_IMAGE in h
        assert (root / "og-seo.svg").is_file()
        assert '<h1>Thống kê XSMB: tần suất, lô gan và cặp đảo 00–99</h1>' in s.read_text(encoding="utf-8")
    print("PORTAL_METADATA_SELF_TEST_OK")


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--output-root", type=Path, default=ROOT / "_site"); p.add_argument("--self-test", action="store_true"); a = p.parse_args()
    if a.self_test: self_test()
    else: print(json.dumps(apply(a.output_root), ensure_ascii=False))


if __name__ == "__main__": main()
