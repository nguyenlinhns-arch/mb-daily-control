#!/usr/bin/env python3
"""Optimize the built landing page for Google Ads without changing its structure.

The script keeps the original sequence intact:
hero purchase block -> trust strip -> historical proof -> final purchase block.
It makes the first screen product-first, neutralizes gambling-like wording,
adds transparent service limits, improves checkout trust, and instruments the
two purchase CTAs for paid-traffic funnel analysis.
"""
from __future__ import annotations

import argparse
import re
import tempfile
from datetime import date
from pathlib import Path


TRACKING_TAG = '<script defer src="/ads-tracking.js?v=20260815-1"></script>'
PRECONNECT_BLOCK = '''
  <link rel="preconnect" href="https://www.googletagmanager.com">
  <link rel="dns-prefetch" href="//www.googletagmanager.com">
  <link rel="dns-prefetch" href="//img.vietqr.io">
'''.strip()


def read_vi_date(content: str, attribute: str) -> date:
    match = re.search(
        rf'{re.escape(attribute)}="(?P<day>\d{{2}})/(?P<month>\d{{2}})/(?P<year>\d{{4}})"',
        content,
    )
    if not match:
        raise AssertionError(f"Missing {attribute}")
    return date(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
    )


def vi(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def replace_meta(content: str, attribute: str, key: str, value: str) -> str:
    pattern = re.compile(
        rf'(<meta\s+{re.escape(attribute)}="{re.escape(key)}"\s+content=")[^"]*(">)',
        re.IGNORECASE,
    )
    updated, count = pattern.subn(
        lambda match: f"{match.group(1)}{value}{match.group(2)}",
        content,
        count=1,
    )
    if count != 1:
        raise AssertionError(f"Missing meta {attribute}={key}")
    return updated


def inject_head_assets(content: str) -> str:
    if PRECONNECT_BLOCK not in content:
        marker = '<link rel="canonical" href="https://lemienbac.com/">'
        if marker in content:
            content = content.replace(marker, f"{marker}\n{PRECONNECT_BLOCK}", 1)
        elif "</head>" in content:
            content = content.replace("</head>", f"{PRECONNECT_BLOCK}\n</head>", 1)
        else:
            raise AssertionError("Home page is missing </head>")

    if TRACKING_TAG not in content:
        checkout_enhance = re.search(
            r'<script\s+defer\s+src="/checkout-enhance\.js\?v=[^"]+"></script>',
            content,
            flags=re.IGNORECASE,
        )
        if checkout_enhance:
            insert_at = checkout_enhance.end()
            content = content[:insert_at] + f"\n  {TRACKING_TAG}" + content[insert_at:]
        elif "</head>" in content:
            content = content.replace("</head>", f"  {TRACKING_TAG}\n</head>", 1)
        else:
            raise AssertionError("Unable to inject ads tracking")
    return content


def history_rate(content: str) -> tuple[int, int, int]:
    match = re.search(
        r'<div class="historical-rate">.*?<strong>(\d+)%</strong>'
        r'<span>(\d+)/(\d+) ngày',
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise AssertionError("Historical rate block was not found")
    return tuple(map(int, match.groups()))


def make_product_first(content: str, report_day: date, lock_day: date) -> str:
    rate, hit_days, total_days = history_rate(content)
    report_dmy = vi(report_day)
    lock_dmy = vi(lock_day)

    title = f"Báo cáo dữ liệu AI XSMB ngày {report_dmy} – 30.000đ | Lê Miền Bắc AI"
    description = (
        f"Báo cáo dữ liệu AI XSMB ngày {report_dmy}, khóa dữ liệu đến {lock_dmy}. "
        "Giá 30.000đ, thanh toán một lần; có lịch sử đối chiếu, mẫu báo cáo và điều khoản rõ ràng."
    )
    content = re.sub(
        r"<title>.*?</title>",
        f"<title>{title}</title>",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    content = replace_meta(content, "name", "description", description)
    content = replace_meta(content, "property", "og:title", title)
    content = replace_meta(content, "property", "og:description", description)
    content = replace_meta(content, "name", "twitter:title", title)
    content = replace_meta(content, "name", "twitter:description", description)

    hero_heading = (
        f'<h1>Báo cáo dữ liệu AI XSMB<br><em>ngày {report_dmy}</em></h1>'
    )
    content, count = re.subn(
        r'(<section class="hero hero-simple" id="top">.*?'
        r'<p class="eyebrow">.*?</p>)\s*<h1>.*?</h1>',
        lambda match: f"{match.group(1)}\n        {hero_heading}",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if count != 1:
        raise AssertionError("Hero heading was not found")

    lead = (
        f'<p class="hero-lead">Dữ liệu đã công bố được khóa đến hết '
        f'<strong>{lock_dmy}</strong>, đối chiếu nguồn và tổng hợp trong một '
        'báo cáo ngắn. Xem lịch sử tháng này và báo cáo mẫu trước khi thanh toán.</p>'
    )
    content, count = re.subn(
        r'<p class="hero-lead">.*?</p>',
        lead,
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if count != 1:
        raise AssertionError("Hero lead was not found")

    proof = (
        f'<p class="hero-proof-text">Tỷ lệ {rate}% mô tả {hit_days}/{total_days} '
        f'ngày lịch sử đã hoàn tất; không phải xác suất hoặc cam kết cho ngày {report_dmy}.</p>'
    )
    content, count = re.subn(
        r'<p class="hero-proof-text">.*?</p>',
        proof,
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if count != 1:
        raise AssertionError("Hero proof was not found")

    # The first screen remains truthful but uses neutral, product-oriented copy.
    content = content.replace(
        "2 cặp 4SO, 4 đầu ra theo thứ tự xếp hạng",
        "Kết luận tổng hợp Top 1–Top 2 theo thứ tự xếp hạng",
    )

    if 'class="ads-policy-note"' not in content:
        pattern = re.compile(
            r'(<button\b(?=[^>]*\bdata-open-checkout\b)[^>]*>'
            r'NHẬN BÁO CÁO HÔM NAY – 30\.000Đ</button>)',
            flags=re.IGNORECASE,
        )
        content, count = pattern.subn(
            r'\1\n          <p class="ads-policy-note">Dịch vụ phân tích dữ liệu độc lập · Không nhận cược, đặt cược thay hoặc cam kết kết quả.</p>',
            content,
            count=1,
        )
        if count != 1:
            raise AssertionError("Hero purchase CTA was not found")

    return content


def neutralize_evidence_copy(content: str) -> str:
    replacements = (
        ("Có cả ngày trúng và không trúng", "Có cả ngày có số xuất hiện và chưa xuất hiện"),
        ("có cả ngày trúng và không trúng", "có cả ngày có số xuất hiện và chưa xuất hiện"),
        ("Không trúng", "Chưa xuất hiện"),
        ("không trúng", "chưa xuất hiện"),
    )
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def label_ctas(content: str) -> str:
    position = iter(("hero", "final"))

    def update(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        if "data-cta-position" not in attrs:
            attrs += f' data-cta-position="{next(position)}"'
        return f"<button{attrs}>"

    content, count = re.subn(
        r'<button(?P<attrs>[^>]*\bdata-open-checkout\b[^>]*)>',
        update,
        content,
        count=2,
        flags=re.IGNORECASE,
    )
    if count != 2:
        raise AssertionError(f"Expected two home purchase CTAs, found {count}")
    return content


def improve_checkout_trust(content: str) -> str:
    if 'data-account-holder="true"' not in content:
        bank_row = '<div class="pay-row"><span>Ngân hàng</span><strong>VPBank</strong></div>'
        holder_row = (
            '<div class="pay-row pay-row-holder" data-account-holder="true">'
            '<span>Chủ tài khoản</span><strong id="bank-account-holder">NGUYEN TU LINH</strong></div>'
        )
        if bank_row not in content:
            raise AssertionError("Checkout bank row was not found")
        content = content.replace(bank_row, f"{bank_row}\n        {holder_row}", 1)

    content = content.replace(
        "Chủ dịch vụ xác nhận, báo cáo mở trên màn hình",
        "Giao dịch được xác nhận, báo cáo mở trên màn hình",
    )
    content = content.replace(
        "Đã gửi email báo chủ dịch vụ",
        "Đã gửi yêu cầu đối soát",
    )
    content = content.replace(
        "Vui lòng giữ màn hình này trong khi chờ xác nhận.",
        "Bạn có thể tải lại trang hoặc quay lại sau; trạng thái đơn vẫn được giữ.",
    )
    content = content.replace(
        "Báo cáo chỉ mở sau khi chủ dịch vụ bấm xác nhận trong email.",
        "Báo cáo chỉ mở sau khi giao dịch được xác nhận.",
    )
    content = content.replace(
        "Nút “Tôi đã chuyển khoản” chỉ gửi yêu cầu đối soát, chưa tự xác nhận tiền đã vào tài khoản.",
        "Nút “Tôi đã chuyển khoản” chỉ gửi yêu cầu đối soát; chưa tự xác nhận tiền đã vào tài khoản.",
    )
    return content


def improve_footer(content: str) -> str:
    content = re.sub(
        r'<footer class="site-footer simple-footer"><div class="wrap"><p>.*?</p><nav>',
        '<footer class="site-footer simple-footer"><div class="wrap"><p><strong>Lê Miền Bắc AI</strong><br>Dịch vụ phân tích dữ liệu độc lập · Hỗ trợ qua Zalo.</p><nav>',
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return content


def update_legal(root: Path, report_day: date) -> None:
    legal = root / "legal.html"
    if not legal.exists():
        return
    content = legal.read_text(encoding="utf-8")
    report_dmy = vi(report_day)
    content = re.sub(
        r'(<div class="notice-bar"><div class="wrap">.*?<span>)Cập nhật ngày \d{2}/\d{2}/\d{4}(</span>)',
        rf'\1Cập nhật ngày {report_dmy}\2',
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    content = re.sub(
        r'<p class="eyebrow">CẬP NHẬT \d{2}/\d{2}/\d{4}</p>',
        f'<p class="eyebrow">CẬP NHẬT {report_dmy}</p>',
        content,
        count=1,
        flags=re.IGNORECASE,
    )
    content = content.replace("<h3>Đối soát thủ công qua email</h3>", "<h3>Đối soát giao dịch</h3>")
    legal.write_text(content, encoding="utf-8")


def optimize(root: Path) -> None:
    home = root / "index.html"
    if not home.exists():
        raise FileNotFoundError(f"Missing built home page: {home}")
    content = home.read_text(encoding="utf-8")
    report_day = read_vi_date(content, "data-report-date")
    lock_day = read_vi_date(content, "data-lock-date")

    content = inject_head_assets(content)
    content = make_product_first(content, report_day, lock_day)
    content = neutralize_evidence_copy(content)
    content = label_ctas(content)
    content = improve_checkout_trust(content)
    content = improve_footer(content)
    home.write_text(content, encoding="utf-8")
    update_legal(root, report_day)
    validate(root)


def validate(root: Path) -> None:
    content = (root / "index.html").read_text(encoding="utf-8")
    report_day = read_vi_date(content, "data-report-date")
    report_dmy = vi(report_day)

    required = (
        f"Báo cáo dữ liệu AI XSMB ngày {report_dmy}",
        "data-cta-position=\"hero\"",
        "data-cta-position=\"final\"",
        "ads-policy-note",
        "Dịch vụ phân tích dữ liệu độc lập",
        "Không nhận cược, đặt cược thay hoặc cam kết kết quả",
        "Có cả ngày có số xuất hiện và chưa xuất hiện",
        "Chưa xuất hiện",
        'data-account-holder="true"',
        "NGUYEN TU LINH",
        "Giao dịch được xác nhận, báo cáo mở trên màn hình",
        "Đã gửi yêu cầu đối soát",
        TRACKING_TAG,
        PRECONNECT_BLOCK,
    )
    for marker in required:
        if marker not in content:
            raise AssertionError(f"Missing Google Ads landing marker: {marker}")

    forbidden = (
        f"<title>73% trong 30 ngày",
        "Có cả ngày trúng và không trúng",
        "Không trúng",
        "Đã gửi email báo chủ dịch vụ",
        "Chủ dịch vụ xác nhận, báo cáo mở trên màn hình",
    )
    for marker in forbidden:
        if marker in content:
            raise AssertionError(f"Outdated landing copy remains: {marker}")

    buttons = re.findall(
        r'<button\b[^>]*\bdata-open-checkout\b[^>]*>',
        content,
        flags=re.IGNORECASE,
    )
    if len(buttons) != 2:
        raise AssertionError(f"Expected exactly two checkout buttons, found {len(buttons)}")

    legal = root / "legal.html"
    if legal.exists():
        legal_content = legal.read_text(encoding="utf-8")
        if f"CẬP NHẬT {report_dmy}" not in legal_content:
            raise AssertionError("Legal update date is stale")
        if "Đối soát thủ công qua email" in legal_content:
            raise AssertionError("Legal heading still exposes internal email workflow")


def self_test() -> None:
    sample = '''<!doctype html><html><head>
    <meta name="description" content="old"><meta property="og:title" content="old"><meta property="og:description" content="old"><meta name="twitter:title" content="old"><meta name="twitter:description" content="old"><link rel="canonical" href="https://lemienbac.com/"><title>Old</title><script defer src="/checkout-enhance.js?v=1"></script></head>
    <body data-report-date="15/08/2026" data-lock-date="14/08/2026">
    <section class="hero hero-simple" id="top"><p class="eyebrow">BÁO CÁO</p><h1><em>73%</em></h1><p class="hero-lead">Old</p><p class="hero-proof-text">Old</p><ul><li>2 cặp 4SO, 4 đầu ra theo thứ tự xếp hạng</li></ul><button data-open-checkout>NHẬN BÁO CÁO HÔM NAY – 30.000Đ</button></section>
    <div class="historical-rate"><strong>73%</strong><span>22/30 ngày</span></div><h2>Có cả ngày trúng và không trúng</h2><span class="history-miss">Không trúng</span>
    <button data-open-checkout>NHẬN BÁO CÁO HÔM NAY – 30.000Đ</button>
    <ol><li>Chủ dịch vụ xác nhận, báo cáo mở trên màn hình</li></ol>
    <div class="payment-card"><div class="pay-row"><span>Ngân hàng</span><strong>VPBank</strong></div></div>
    <strong id="pending-title">Đã gửi email báo chủ dịch vụ</strong><small>Vui lòng giữ màn hình này trong khi chờ xác nhận.</small>
    <p>Nút “Tôi đã chuyển khoản” chỉ gửi yêu cầu đối soát, chưa tự xác nhận tiền đã vào tài khoản. Báo cáo chỉ mở sau khi chủ dịch vụ bấm xác nhận trong email.</p>
    <footer class="site-footer simple-footer"><div class="wrap"><p>Old</p><nav></nav></div></footer>
    </body></html>'''
    legal = '''<html><body><div class="notice-bar"><div class="wrap"><span></span><strong>Thông tin</strong><span>Cập nhật ngày 13/08/2026</span></div></div><p class="eyebrow">CẬP NHẬT 13/08/2026</p><h3>Đối soát thủ công qua email</h3></body></html>'''
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "index.html").write_text(sample, encoding="utf-8")
        (root / "legal.html").write_text(legal, encoding="utf-8")
        optimize(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.output_root and not args.self_test:
        parser.error("Provide --output-root and/or --self-test")
    if args.self_test:
        self_test()
    if args.output_root:
        optimize(args.output_root.resolve())


if __name__ == "__main__":
    main()
