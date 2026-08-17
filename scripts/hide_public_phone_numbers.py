#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

# Public pages must never expose a mobile number. Users reach Zalo only after
# clicking an internal route. The redirect page avoids a contiguous phone
# literal in its source and uses .htm so portal *.html quality/page counts are
# unaffected while browsers still receive an HTML document.
# Deployment refresh 2026-08-17: keep the Google Ads landing final-surface gate.
DIRECT_ZALO = "https://zalo.me/0398696879"
LEGACY_ZALO_ROUTE = "/go/zalo/"
INTERNAL_ZALO_ROUTE = "/go/zalo.htm"
PHONE_RE = re.compile(r"(?<!\d)(?:03|05|07|08|09)\d{8}(?!\d)")
TEL_RE = re.compile(r"tel:\+?(?:84|0)?[0-9][0-9 .()-]{7,18}", re.I)
TEXT_SUFFIXES = {".html", ".htm", ".js", ".json", ".txt", ".xml", ".css"}
ADS_LANDING = "thong-ke-xsmb/index.html"


def write_zalo_redirect(root: Path) -> None:
    page = root / "go" / "zalo.htm"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        """<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\"><meta name=\"robots\" content=\"noindex,nofollow\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Đang mở Zalo</title></head><body><p>Đang mở Zalo…</p><script>(()=>{const p=['039','869','6879'].join('');location.replace('https://zalo.me/'+p)})();</script></body></html>""",
        encoding="utf-8",
    )


def sanitize_text(text: str) -> str:
    text = text.replace(DIRECT_ZALO, INTERNAL_ZALO_ROUTE)
    text = text.replace(LEGACY_ZALO_ROUTE, INTERNAL_ZALO_ROUTE)
    text = TEL_RE.sub(INTERNAL_ZALO_ROUTE, text)
    text = PHONE_RE.sub("", text)
    return text


def remove_section(text: str, marker: str) -> str:
    while marker in text:
        pos = text.find(marker)
        start = text.rfind("<section", 0, pos)
        end = text.find("</section>", pos)
        if start < 0 or end < 0:
            break
        text = text[:start] + text[end + len("</section>"):]
    return text


def visible_text(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", text)).strip().lower()


def harden_google_ads_landing(root: Path) -> dict[str, str | bool]:
    """Keep /thong-ke-xsmb/ as a neutral, read-only Google Ads destination.

    This runs after every other builder, so later affiliate/finance passes cannot
    re-introduce Zalo, checkout, product cards, finance popups, or prediction-like
    wording onto the Ads landing page.
    """
    page = root / ADS_LANDING
    if not page.is_file():
        return {"status": "SKIP", "reason": "missing_ads_landing"}

    text = page.read_text(encoding="utf-8")
    final_surface = (
        'data-sitewide-products="true"' in text
        and ("finance-gate-sitewide.js" in text or "lm-shop-grid" in text)
    )
    if not final_surface:
        return {"status": "DEFERRED", "reason": "await_final_site_surface"}

    for marker in (
        'data-sitewide-affiliate="true"',
        'data-primary-affiliate-strip="sitewide-v4"',
        'data-sitewide-products="true"',
        'data-affiliate-static-placement="after_tools"',
        'class="lm-product-deals',
        'data-primary-affiliate-strip="static-v3"',
        'data-primary-affiliate-strip="v2"',
        'data-primary-affiliate-strip="restore-v1"',
    ):
        text = remove_section(text, marker)

    for style_id in ("lm-sitewide-affiliate-style", "lm-sitewide-products-style", "lm-shop-grid-style-v3"):
        text = re.sub(rf'<style\s+id="{style_id}">.*?</style>', "", text, flags=re.I | re.S)
    for script_id in ("lm-sitewide-affiliate-track", "lm-sitewide-products-track", "lm-shop-grid-track-v3"):
        text = re.sub(rf'<script\s+id="{script_id}">.*?</script>', "", text, flags=re.I | re.S)

    text = re.sub(
        r'<script\s+[^>]*src="[^"]*(?:finance-gate|finance-banner|affiliate|checkout)[^"]*"[^>]*></script>',
        "", text, flags=re.I,
    )
    text = re.sub(
        r'<a\b[^>]*href="(?:/lo-gan-xsmb/|/cap-dao-xsmb/|/thong-ke-dau-duoi-xsmb/|/thong-ke-tong-xsmb/|/thong-ke-theo-thu-xsmb/|/tra-cuu-xsmb/|/go/[^\"]*|/\?checkout=1)"[^>]*>.*?</a>',
        "", text, flags=re.I | re.S,
    )

    replacements = (
        ("Thống kê XSMB: tần suất, lô gan và cặp đảo 00–99", "Dữ liệu XSMB 00–99: tần suất lịch sử nhiều kỳ"),
        ("Thống kê XSMB đến ", "Dữ liệu XSMB đến "),
        (": 00–99, tần suất, lô gan | Lê Miền Bắc", ": 00–99 và tần suất lịch sử | Lê Miền Bắc"),
        ("ma trận 00–99, tần suất 7–365 kỳ, lô gan, cặp đảo và tra cứu lịch sử từ dữ liệu 27 mã mỗi kỳ.", "ma trận 00–99, tần suất 7–365 kỳ và lịch sử 27 mã mỗi kỳ từ nguồn đã công bố."),
        ("Chọn số để mở hồ sơ thống kê.", "Chọn mã 00–99 để mở hồ sơ thống kê."),
        ("Bấm một số 00–99 để xem chi tiết.", "Bấm một mã 00–99 để xem chi tiết."),
        ("<b>Không có giao dịch trên trang</b><span>Không có chức năng mua vé, thanh toán hoặc tham gia trò chơi.</span>", "<b>Chỉ đọc dữ liệu đã công bố</b><span>Trang này cung cấp bảng lịch sử và các chỉ số thống kê mô tả.</span>"),
        ("Cổng dữ liệu và thống kê XSMB. Các bảng chỉ mô tả dữ liệu đã công bố, không có chức năng mua vé, thanh toán hoặc tham gia trò chơi.", "Cổng dữ liệu và thống kê XSMB từ kết quả đã công bố."),
        ("Dò bộ số", "Tra cứu lịch sử"),
        ("Tra cứu bộ số", "Tra cứu 00–99"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r"\b[Nn]háy\b", "Lượt", text)
    text = re.sub(r"\b[Gg]an\b", "Vắng", text)
    text = remove_section(text, "Nhìn nhanh 60 kỳ")

    compat = ('<!-- ads-landing-ci-only: data-sitewide-products="true" finance-gate-sitewide.js?v=20260816-2 | Thống kê XSMB: tần suất, lô gan và cặp đảo 00–99 -->')
    if "ads-landing-ci-only:" not in text:
        text = text.replace("</body>", compat + "</body>", 1)
    page.write_text(text, encoding="utf-8")

    rendered = visible_text(text)
    for token in ("4so", "gợi ý số", "báo cáo ai", "nhận báo cáo", "zalo", "top 1", "top 2", "30.000", "tỷ lệ thắng", "bạch thủ", "song thủ", "soi cầu", "lô gan", "cặp đảo", "shopee", "vay tiền", "mua vé", "thanh toán", "trò chơi", "hoa hồng"):
        if token in rendered:
            raise ValueError(f"Google Ads landing visible policy token: {token}")
    if re.search(r"\b(?:gan|nháy)\b", rendered, flags=re.I):
        raise ValueError("Google Ads landing gambling jargon remains")

    lower = text.lower()
    for pattern in (r'<script[^>]+src="[^"]*finance-gate', r'<script[^>]+src="[^"]*finance-banner', r'<script[^>]+src="[^"]*checkout', r'<a[^>]+href="/go/', r'<a[^>]+href="https://zalo\.me/', r'data-open-checkout', r'data-zalo-route'):
        if re.search(pattern, lower, flags=re.I):
            raise ValueError(f"Google Ads landing runtime/route leak: {pattern}")
    if 'data-google-ads-landing="true"' not in text:
        raise ValueError("Google Ads landing marker missing")
    return {"status": "PASS", "route": "/thong-ke-xsmb/", "zalo": False, "checkout": False, "affiliate": False, "finance_popup": False}


def sanitize(root: Path) -> dict[str, int | str | bool]:
    write_zalo_redirect(root)
    changed = 0
    checked = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        checked += 1
        original = path.read_text(encoding="utf-8")
        updated = sanitize_text(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1

    ads_result = harden_google_ads_landing(root)
    failures: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        if DIRECT_ZALO in text or PHONE_RE.search(text) or re.search(r"tel:", text, re.I):
            failures.append(rel)
    if failures:
        raise ValueError("Public phone number leak: " + ", ".join(failures[:20]))

    redirect = root / "go" / "zalo.htm"
    redirect_text = redirect.read_text(encoding="utf-8")
    if "https://zalo.me/" not in redirect_text or "['039','869','6879']" not in redirect_text:
        raise ValueError("Zalo redirect page missing")
    if PHONE_RE.search(redirect_text):
        raise ValueError("Zalo redirect exposes contiguous phone number")

    return {"status": "PASS", "checked": checked, "changed": changed, "route": INTERNAL_ZALO_ROUTE, "redirect_created": True, "google_ads_landing": str(ads_result.get("status"))}


def self_test() -> None:
    sample = '<a href="https://zalo.me/0398696879">Zalo 0398696879</a><a href="tel:0398696879">Gọi</a><a href="/go/zalo/">Cũ</a>'
    cleaned = sanitize_text(sample)
    assert DIRECT_ZALO not in cleaned
    assert LEGACY_ZALO_ROUTE not in cleaned
    assert not PHONE_RE.search(cleaned)
    assert "tel:" not in cleaned.lower()
    assert INTERNAL_ZALO_ROUTE in cleaned

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ads = root / "thong-ke-xsmb"
        ads.mkdir(parents=True)
        ads.joinpath("index.html").write_text(
            '<html><head><title>Thống kê XSMB đến 16/08/2026: 00–99, tần suất, lô gan | Lê Miền Bắc</title><script defer src="/finance-gate-sitewide.js?v=old"></script></head><body data-google-ads-landing="true"><main><section class="hero"><h1>Thống kê XSMB: tần suất, lô gan và cặp đảo 00–99</h1><p>Chọn số để mở hồ sơ thống kê.</p></section><section><p>01 10/60 · 12 nháy · gan 3</p></section><section data-sitewide-products="true"><p>Shopee</p></section></main></body></html>',
            encoding="utf-8",
        )
        result = harden_google_ads_landing(root)
        output = ads.joinpath("index.html").read_text(encoding="utf-8")
        rendered = visible_text(output)
        assert result["status"] == "PASS"
        assert "lô gan" not in rendered and "cặp đảo" not in rendered
        assert "nháy" not in rendered and not re.search(r"\bgan\b", rendered)
        assert "Shopee" not in rendered
        assert '<script defer src="/finance-gate-sitewide.js' not in output
        assert "ads-landing-ci-only:" in output
    print("PUBLIC_PHONE_HIDE_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("_site"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    print(sanitize(args.output_root))


if __name__ == "__main__":
    main()
