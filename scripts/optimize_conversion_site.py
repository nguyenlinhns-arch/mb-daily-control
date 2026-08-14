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


STYLE_HREF = "/conversion-accent.css?v=20260814-2"

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

READY_OFFER = '''
        <div class="hero-offer simple-hero-offer conversion-offer">
          <div class="conversion-offer-copy">
            <span class="conversion-ready"><i></i>BÁO CÁO HÔM NAY ĐÃ SẴN SÀNG</span>
            <small>CHỈ 30.000Đ · THANH TOÁN MỘT LẦN</small>
            <strong>30.000đ</strong>
            <span>01 báo cáo AI cho đúng ngày hôm nay</span>
          </div>
          <div class="conversion-preview" aria-label="Định dạng kết luận được mở sau xác nhận">
            <article><small>TOP 1</small><b>•• — ••</b></article>
            <article><small>TOP 2</small><b>•• — ••</b></article>
          </div>
          <ul class="conversion-benefits">
            <li>2 cặp 4SO, 4 đầu ra theo thứ tự xếp hạng</li>
            <li>Top 3, dữ liệu khóa T−1 và hồ sơ nguồn</li>
            <li>Tự mở sau khi giao dịch được xác nhận</li>
          </ul>
          <button class="button button-primary button-large" type="button" data-open-checkout>MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ</button>
          <a class="conversion-sample-link" href="/mau-bao-cao.html">Xem mẫu báo cáo trước khi mua →</a>
        </div>
'''

STALE_OFFER = '''
        <div class="hero-offer simple-hero-offer conversion-offer conversion-offer-stale">
          <div class="conversion-offer-copy">
            <span class="conversion-ready conversion-updating"><i></i>ĐANG KIỂM TRA DỮ LIỆU T−1</span>
            <small>BÁO CÁO NGÀY HÔM NAY</small>
            <strong>Đang cập nhật</strong>
            <span>Chỉ mở thanh toán sau khi dữ liệu và báo cáo hoàn tất kiểm tra.</span>
          </div>
          <button class="button button-primary button-large" type="button" data-open-checkout disabled aria-disabled="true">CHƯA NHẬN THANH TOÁN</button>
        </div>
'''

BUY_VALUE_LIST = '''
          <ul class="buy-value-list" aria-label="Nội dung báo cáo">
            <li><strong>2 cặp 4SO Top 1–Top 2</strong><span>Bốn đầu ra theo đúng thứ tự xếp hạng.</span></li>
            <li><strong>Top 3 và chỉ số kiểm định</strong><span>Gồm dữ liệu khóa T−1 và hồ sơ nguồn.</span></li>
            <li><strong>Mở ngay sau đối soát</strong><span>Không cần tài khoản và không phải chờ gửi tệp.</span></li>
          </ul>
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

CHECKOUT_VALUE = '''
      <div class="checkout-value">
        <strong>Sau khi được xác nhận, bạn nhận:</strong>
        <span>2 cặp 4SO · 4 đầu ra xếp hạng · Top 3 và hồ sơ nguồn</span>
      </div>
'''


def write_if_changed(path: Path, content: str) -> None:
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    if previous != content:
        path.write_text(content, encoding="utf-8")


def inject_stylesheet(content: str) -> str:
    # Replace an older conversion stylesheet version to force cache refresh.
    content = re.sub(
        r'<link rel="stylesheet" href="/conversion-accent\.css\?v=[^"]+">',
        f'<link rel="stylesheet" href="{STYLE_HREF}">',
        content,
        count=1,
    )
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


def collapse_history(content: str) -> str:
    if 'class="history-disclosure"' in content:
        return content
    start_marker = '<div class="history-days"'
    end_marker = '<p class="historical-disclaimer"'
    start = content.find(start_marker)
    end = content.find(end_marker, start)
    if start < 0 or end < 0:
        return content
    history = content[start:end].rstrip()
    disclosure = (
        '<details class="history-disclosure">'
        '<summary>Xem đầy đủ lịch sử đối chiếu từng ngày <span>▾</span></summary>'
        f'{history}'
        '</details>\n        '
    )
    return content[:start] + disclosure + content[end:]


def optimize_home(content: str) -> str:
    content = inject_stylesheet(content)
    report_ready = 'data-public-ready="false"' not in content

    content = content.replace("Nhận báo cáo hôm nay · 30K", "MỞ KẾT LUẬN AI · 30K")
    content = content.replace("Nhận báo cáo đầy đủ", "MỞ KẾT LUẬN AI · 30K")

    offer_pattern = (
        r'<div class="hero-offer simple-hero-offer(?: conversion-offer(?: conversion-offer-stale)?)?">'
        r'.*?</div>\s*(?=</div>\s*</section>)'
    )
    content, offer_count = re.subn(
        offer_pattern,
        READY_OFFER.strip() if report_ready else STALE_OFFER.strip(),
        content,
        count=1,
        flags=re.DOTALL,
    )
    if offer_count != 1:
        raise ValueError("Hero offer was not found")

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

    content = collapse_history(content)

    # Only add a purchase CTA after historical evidence when today's report is
    # actually ready. A stale/fail-closed build must not invite payment.
    if (
        report_ready
        and 'class="history-cta"' not in content
        and 'class="historical-disclaimer"' in content
    ):
        content = replace_one(
            content,
            r'(<p class="historical-disclaimer">.*?</p>)',
            r'\1\n        <button class="history-cta" type="button" data-open-checkout>MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ</button>',
            flags=re.DOTALL,
        )

    content = content.replace(
        '<p class="eyebrow">BÁO CÁO ĐẦY ĐỦ HÔM NAY</p>',
        '<p class="eyebrow">CHỈ 30.000Đ · MỞ KẾT LUẬN AI HÔM NAY</p>',
    )
    content = content.replace(
        '<p class="eyebrow">CHỈ 30.000Đ · BÁO CÁO AI HÔM NAY</p>',
        '<p class="eyebrow">CHỈ 30.000Đ · MỞ KẾT LUẬN AI HÔM NAY</p>',
    )

    if 'class="buy-value-list"' not in content:
        content = replace_one(
            content,
            r'(<p class="buy-copy">.*?</p>)',
            lambda match: f'{match.group(1)}\n{BUY_VALUE_LIST}',
            flags=re.DOTALL,
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
        ">NHẬN BÁO CÁO HÔM NAY – 30.000Đ</button>",
        ">MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ</button>",
    )
    content = content.replace(
        ">Hiện thông tin chuyển khoản</button>",
        ">MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ</button>",
    )

    content = content.replace(
        '<h2 id="checkout-title">Chuyển khoản 30.000đ</h2>',
        '<h2 id="checkout-title">Mở kết luận AI ngày hôm nay</h2><p class="checkout-price">30.000đ · thanh toán một lần</p>',
    )
    content = content.replace(
        '<h2 id="checkout-title">Nhận báo cáo AI ngày hôm nay</h2>',
        '<h2 id="checkout-title">Mở kết luận AI ngày hôm nay</h2>',
    )

    if 'class="checkout-value"' not in content:
        content = replace_one(
            content,
            r'(<p class="checkout-scope" id="checkout-modal-scope">.*?</p>)',
            lambda match: f'{match.group(1)}\n{CHECKOUT_VALUE}',
            flags=re.DOTALL,
        )

    if 'class="checkout-trust"' not in content:
        content = replace_one(
            content,
            r'(<div class="checkout-value">.*?</div>)',
            lambda match: f'{match.group(1)}\n{CHECKOUT_TRUST}',
            flags=re.DOTALL,
        )

    content = re.sub(
        r'<p class="zalo-instruction">.*?</p>',
        '<p class="zalo-instruction">Sau khi chuyển khoản, bấm nút dưới đây để yêu cầu đối soát. Kết luận AI sẽ tự mở trên màn hình khi giao dịch được xác nhận.</p>',
        content,
        count=1,
        flags=re.DOTALL,
    )
    content = content.replace(
        'Tôi đã chuyển khoản – gửi email xác nhận',
        'TÔI ĐÃ CHUYỂN KHOẢN – YÊU CẦU MỞ KẾT LUẬN',
    )
    content = content.replace(
        'TÔI ĐÃ CHUYỂN KHOẢN – YÊU CẦU MỞ BÁO CÁO',
        'TÔI ĐÃ CHUYỂN KHOẢN – YÊU CẦU MỞ KẾT LUẬN',
    )
    content = content.replace(
        '<span>Nhận báo cáo hôm nay</span><strong>30.000đ</strong>',
        '<span>Mở kết luận AI hôm nay</span><strong>30.000đ</strong>',
    )
    content = content.replace(
        '<span>MỞ KẾT LUẬN AI · 30K</span><strong>30.000đ</strong>',
        '<span>Mở kết luận AI hôm nay</span><strong>30.000đ</strong>',
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
        "history disclosure": 'class="history-disclosure"',
        "purchase value list": 'class="buy-value-list"',
        "purchase guarantees": 'class="buy-guarantees"',
        "checkout value": 'class="checkout-value"',
        "checkout trust": 'class="checkout-trust"',
    }
    if report_ready:
        checks.update(
            {
                "ready offer": 'class="conversion-ready"',
                "masked preview": 'class="conversion-preview"',
                "history CTA": 'class="history-cta"',
                "today CTA": "MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ",
            }
        )
    for label, marker in checks.items():
        if marker not in home:
            raise AssertionError(f"Missing {label}: {marker}")
    if home.count('class="conversion-trust"') != 1:
        raise AssertionError("Conversion trust strip must occur exactly once")
    if home.count('class="history-disclosure"') != 1:
        raise AssertionError("History disclosure must occur exactly once")
    if report_ready and home.count('class="history-cta"') != 1:
        raise AssertionError("Ready page must contain exactly one history CTA")
    if not report_ready and 'class="history-cta"' in home:
        raise AssertionError("Fail-closed page must not contain a history purchase CTA")


def self_test() -> None:
    ready_sample = '''<!doctype html><html><head><title>Test</title></head><body data-public-ready="true">
    <header><button>Nhận báo cáo đầy đủ</button></header>
    <section class="hero hero-simple" id="top"><div><div class="hero-offer simple-hero-offer"><div><small>Old</small><strong>30.000đ</strong><span>Old</span></div><button class="button button-primary button-large" type="button" data-open-checkout>Old</button></div></div></section>
    <section><div class="history-days"><div>History</div></div><p class="historical-disclaimer">Historical disclaimer</p></section>
    <section class="buy-simple"><p class="eyebrow">BÁO CÁO ĐẦY ĐỦ HÔM NAY</p><p class="buy-copy">Buy copy</p><p class="checkout-scope" id="checkout-scope">Scope</p><p class="buy-legal">Old</p><button>Hiện thông tin chuyển khoản</button></section>
    <div><h2 id="checkout-title">Chuyển khoản 30.000đ</h2><p class="checkout-scope" id="checkout-modal-scope">Modal scope</p><p class="zalo-instruction">Old</p><button>Tôi đã chuyển khoản – gửi email xác nhận</button></div>
    <button class="mobile-cta"><span>Nhận báo cáo đầy đủ</span><strong>30.000đ</strong></button>
    </body></html>'''
    stale_sample = ready_sample.replace('data-public-ready="true"', 'data-public-ready="false"').replace(
        '<p class="historical-disclaimer">Historical disclaimer</p>',
        '<p class="historical-disclaimer">Historical data is updating</p>',
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
        stale = index.read_text(encoding="utf-8")
        if 'class="history-cta"' in stale:
            raise AssertionError("Stale self-test page exposed a purchase CTA")
        if "CHƯA NHẬN THANH TOÁN" not in stale:
            raise AssertionError("Stale self-test page is missing fail-closed offer")


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
