#!/usr/bin/env python3
"""Apply conversion-focused, policy-conscious improvements to the built site.

This runs after the audited static build and the public-site simplification step.
It does not touch analytical data, paid-report payloads, order logic or payment
approval. It only improves message hierarchy, trust cues and purchase CTAs.
"""
from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path


STYLE_HREF = "/conversion-accent.css?v=20260814-1"

TRUST_BLOCK = '''
    <section class="conversion-trust" aria-label="Điểm tin cậy trước khi mua">
      <div class="wrap conversion-trust-grid">
        <article class="conversion-trust-item"><span class="conversion-trust-icon">T−1</span><div><strong>Dữ liệu khóa đến hôm qua</strong><small>Không sử dụng kết quả tương lai để sửa đầu ra.</small></div></article>
        <a class="conversion-trust-item" href="/mau-bao-cao.html"><span class="conversion-trust-icon">MẪU</span><div><strong>Xem mẫu trước khi mua</strong><small>Biết đúng định dạng báo cáo trước khi chuyển khoản.</small></div></a>
        <article class="conversion-trust-item"><span class="conversion-trust-icon">1 LẦN</span><div><strong>Thanh toán một lần</strong><small>Không tự gia hạn và không có phí ẩn.</small></div></article>
        <article class="conversion-trust-item"><span class="conversion-trust-icon">✓</span><div><strong>Mở sau khi xác nhận</strong><small>Báo cáo tự hiển thị khi giao dịch được đối soát.</small></div></article>
      </div>
    </section>
'''

BUY_GUARANTEES = '''
          <ul class="buy-guarantees" aria-label="Cam kết dịch vụ">
            <li>Không cần tạo tài khoản</li>
            <li>Không tự gia hạn</li>
            <li>Hoàn phí nếu lỗi bàn giao</li>
          </ul>
'''

CHECKOUT_TRUST = '''
      <div class="checkout-trust" aria-label="Thông tin trước khi thanh toán">
        <span>01 báo cáo ngày hôm nay</span>
        <span>Thanh toán một lần</span>
        <span>Hỗ trợ qua Zalo</span>
      </div>
'''


def write_if_changed(path: Path, content: str) -> None:
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    if previous != content:
        path.write_text(content, encoding="utf-8")


def inject_stylesheet(content: str) -> str:
    if STYLE_HREF in content:
        return content
    if "</head>" not in content:
        raise ValueError("HTML page is missing </head>")
    return content.replace(
        "</head>",
        f'  <link rel="stylesheet" href="{STYLE_HREF}">\n</head>',
        1,
    )


def replace_one(content: str, pattern: str, replacement: str, *, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=flags)
    if count != 1:
        raise ValueError(f"Expected exactly one match: {pattern}")
    return updated


def optimize_home(content: str) -> str:
    content = inject_stylesheet(content)

    if 'class="conversion-trust"' not in content:
        hero_pattern = re.compile(
            r'(?P<hero><section class="hero hero-simple" id="top">.*?</section>)',
            re.DOTALL,
        )
        content, count = hero_pattern.subn(
            lambda match: f'{match.group("hero")}\n{TRUST_BLOCK}',
            content,
            count=1,
        )
        if count != 1:
            raise ValueError("Home hero section was not found")

    # Only add a purchase CTA after historical evidence when today's report is
    # actually ready. A stale/fail-closed build must not invite payment.
    report_ready = 'data-public-ready="false"' not in content
    if (
        report_ready
        and 'class="history-cta"' not in content
        and 'class="historical-disclaimer"' in content
    ):
        content = replace_one(
            content,
            r'(<p class="historical-disclaimer">.*?</p>)',
            r'\1\n        <button class="history-cta" type="button" data-open-checkout>NHẬN BÁO CÁO HÔM NAY – 30.000Đ</button>',
            flags=re.DOTALL,
        )

    content = content.replace(
        '<p class="eyebrow">BÁO CÁO ĐẦY ĐỦ HÔM NAY</p>',
        '<p class="eyebrow">CHỈ 30.000Đ · BÁO CÁO AI HÔM NAY</p>',
    )

    if 'class="buy-guarantees"' not in content:
        content = replace_one(
            content,
            r'(<p class="checkout-scope" id="checkout-scope">.*?</p>)',
            lambda match: f'{match.group(1)}\n{BUY_GUARANTEES}',
            flags=re.DOTALL,
        )

    content = re.sub(
        r'<p class="buy-legal">.*?</p>',
        '<p class="buy-legal">Không cần tạo tài khoản · Thanh toán một lần · Không tự gia hạn · <a href="/legal.html#payment">Hoàn phí nếu lỗi bàn giao</a></p>',
        content,
        count=1,
        flags=re.DOTALL,
    )

    content = content.replace(
        '<h2 id="checkout-title">Chuyển khoản 30.000đ</h2>',
        '<h2 id="checkout-title">Nhận báo cáo AI ngày hôm nay</h2><p class="checkout-price">30.000đ · thanh toán một lần</p>',
    )

    if 'class="checkout-trust"' not in content:
        content = replace_one(
            content,
            r'(<p class="checkout-scope" id="checkout-modal-scope">.*?</p>)',
            lambda match: f'{match.group(1)}\n{CHECKOUT_TRUST}',
            flags=re.DOTALL,
        )

    content = re.sub(
        r'<p class="zalo-instruction">.*?</p>',
        '<p class="zalo-instruction">Sau khi chuyển khoản, bấm nút dưới đây để yêu cầu đối soát. Báo cáo sẽ tự mở khi giao dịch được xác nhận.</p>',
        content,
        count=1,
        flags=re.DOTALL,
    )
    content = content.replace(
        'Tôi đã chuyển khoản – gửi email xác nhận',
        'TÔI ĐÃ CHUYỂN KHOẢN – YÊU CẦU MỞ BÁO CÁO',
    )
    content = content.replace(
        '<span>Nhận báo cáo đầy đủ</span><strong>30.000đ</strong>',
        '<span>Nhận báo cáo hôm nay</span><strong>30.000đ</strong>',
    )

    return content


def optimize_site(output_root: Path) -> None:
    html_files = list(output_root.rglob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files found under {output_root}")

    for page in html_files:
        content = page.read_text(encoding="utf-8")
        content = inject_stylesheet(content)
        if page == output_root / "index.html":
            content = optimize_home(content)
        write_if_changed(page, content)

    home = (output_root / "index.html").read_text(encoding="utf-8")
    report_ready = 'data-public-ready="false"' not in home
    checks = {
        "conversion stylesheet": STYLE_HREF,
        "trust strip": 'class="conversion-trust"',
        "purchase guarantees": 'class="buy-guarantees"',
        "checkout trust": 'class="checkout-trust"',
    }
    if report_ready:
        checks.update(
            {
                "history CTA": 'class="history-cta"',
                "today CTA": "NHẬN BÁO CÁO HÔM NAY – 30.000Đ",
            }
        )
    for label, marker in checks.items():
        if marker not in home:
            raise AssertionError(f"Missing {label}: {marker}")
    if home.count('class="conversion-trust"') != 1:
        raise AssertionError("Conversion trust strip must occur exactly once")
    if report_ready and home.count('class="history-cta"') != 1:
        raise AssertionError("Ready page must contain exactly one history CTA")
    if not report_ready and 'class="history-cta"' in home:
        raise AssertionError("Fail-closed page must not contain a history purchase CTA")


def self_test() -> None:
    ready_sample = '''<!doctype html><html><head><title>Test</title></head><body data-public-ready="true">
    <section class="hero hero-simple" id="top"><div>Hero</div></section>
    <section><p class="historical-disclaimer">Historical disclaimer</p></section>
    <section class="buy-simple"><p class="eyebrow">BÁO CÁO ĐẦY ĐỦ HÔM NAY</p><p class="checkout-scope" id="checkout-scope">Scope</p><p class="buy-legal">Old</p></section>
    <div><h2 id="checkout-title">Chuyển khoản 30.000đ</h2><p class="checkout-scope" id="checkout-modal-scope">Modal scope</p><p class="zalo-instruction">Old</p><button>Tôi đã chuyển khoản – gửi email xác nhận</button></div>
    <button class="mobile-cta"><span>Nhận báo cáo đầy đủ</span><strong>30.000đ</strong></button>
    </body></html>'''
    stale_sample = ready_sample.replace('data-public-ready="true"', 'data-public-ready="false"').replace(
        '<p class="historical-disclaimer">Historical disclaimer</p>',
        '<p>Historical data is updating</p>',
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        index = root / "index.html"
        index.write_text(ready_sample, encoding="utf-8")
        optimize_site(root)
        first = index.read_text(encoding="utf-8")
        optimize_site(root)
        second = index.read_text(encoding="utf-8")
        if first != second:
            raise AssertionError("Conversion optimizer must be idempotent")
        index.write_text(stale_sample, encoding="utf-8")
        optimize_site(root)
        if 'class="history-cta"' in index.read_text(encoding="utf-8"):
            raise AssertionError("Stale self-test page exposed a purchase CTA")


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
        optimize_site(args.output_root.resolve())


if __name__ == "__main__":
    main()
