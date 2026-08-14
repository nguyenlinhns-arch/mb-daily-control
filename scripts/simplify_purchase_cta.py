#!/usr/bin/env python3
"""Keep the purchase path direct while limiting the home page to two buy blocks.

The home page intentionally has exactly two checkout entry points:
1. the hero offer above the evidence;
2. the final purchase card below the evidence.

The full daily history is visible by default between those two blocks. Header,
mid-history and sticky-mobile purchase buttons are removed to avoid repetition.
Secondary pages still route directly to the home-page checkout.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


SCRIPT_TAG = '<script defer src="/checkout-entry.js?v=20260815-1"></script>'

TEXT_REPLACEMENTS = (
    ("MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ", "NHẬN BÁO CÁO HÔM NAY – 30.000Đ"),
    ("MỞ KẾT LUẬN AI HÔM NAY", "NHẬN BÁO CÁO HÔM NAY"),
    ("MỞ KẾT LUẬN AI · 30K", "NHẬN BÁO CÁO · 30K"),
    ("Mở kết luận AI hôm nay", "Nhận báo cáo hôm nay"),
    ("Mở kết luận AI ngày hôm nay", "Nhận báo cáo AI ngày hôm nay"),
    ("mở kết luận AI ngày hôm nay", "nhận báo cáo AI ngày hôm nay"),
    ("YÊU CẦU MỞ KẾT LUẬN", "YÊU CẦU MỞ BÁO CÁO"),
    ("Kết luận AI sẽ tự mở", "Báo cáo sẽ tự mở"),
    ("kết luận AI sẽ tự mở", "báo cáo sẽ tự mở"),
    ("MỞ KẾT LUẬN", "NHẬN BÁO CÁO"),
)


def normalize_text(content: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        content = content.replace(old, new)
    return content


def simplify_home_purchase_blocks(content: str) -> str:
    # Keep the header focused on identity and the sample report. The first
    # purchase decision should happen inside the complete hero offer.
    content = re.sub(
        r'\s*<button\b(?=[^>]*\bclass="[^"]*button-small[^"]*")'
        r'(?=[^>]*\bdata-open-checkout\b)[^>]*>.*?</button>',
        "",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # The final purchase card already follows the evidence. A separate button
    # directly under the history would create a third purchase block.
    content = re.sub(
        r'\s*<button\b[^>]*\bclass="[^"]*history-cta[^"]*"[^>]*>.*?</button>',
        "",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove the sticky mobile purchase bar so the second and final purchase
    # block remains the dedicated card at the bottom of the main content.
    content = re.sub(
        r'\s*<button\b[^>]*\bclass="[^"]*mobile-cta[^"]*"[^>]*>.*?</button>',
        "",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # History remains collapsible for accessibility, but it is expanded on
    # first load as requested.
    content = re.sub(
        r'<details\b(?=[^>]*\bclass="history-disclosure")'
        r'(?![^>]*\bopen\b)([^>]*)>',
        r'<details\1 open>',
        content,
        count=1,
        flags=re.IGNORECASE,
    )
    content = content.replace(
        "Xem đầy đủ lịch sử đối chiếu từng ngày",
        "Lịch sử đối chiếu từng ngày",
    )
    content = content.replace(
        "Xem lịch sử đối chiếu từng ngày",
        "Lịch sử đối chiếu từng ngày",
    )
    return content


def rewrite_page(page: Path, root: Path) -> None:
    content = normalize_text(page.read_text(encoding="utf-8"))

    if page == root / "index.html":
        content = simplify_home_purchase_blocks(content)
    else:
        content = re.sub(
            r'(<a\b[^>]*\bclass="[^"]*(?:top-cta|primary-cta|seo-purchase-float)[^"]*"[^>]*\bhref=")[^"]*(")',
            r'\1/?checkout=1\2',
            content,
            flags=re.IGNORECASE,
        )
        content = content.replace('href="/?buy=1"', 'href="/?checkout=1"')

    if page == root / "index.html" and SCRIPT_TAG not in content:
        app_tag = re.search(
            r'<script\s+defer\s+src="[^\"]*app\.js[^\"]*"></script>',
            content,
            re.IGNORECASE,
        )
        if app_tag:
            insert_at = app_tag.end()
            content = content[:insert_at] + "\n  " + SCRIPT_TAG + content[insert_at:]
        elif "</head>" in content:
            content = content.replace("</head>", f"  {SCRIPT_TAG}\n</head>", 1)
        else:
            raise AssertionError("Unable to inject checkout-entry.js")

    page.write_text(content, encoding="utf-8")


def validate_home(home: str) -> None:
    if SCRIPT_TAG not in home:
        raise AssertionError("Checkout entry script was not injected")
    if "NHẬN BÁO CÁO HÔM NAY – 30.000Đ" not in home:
        raise AssertionError("Simple purchase CTA is missing")
    if "MỞ KẾT LUẬN" in home:
        raise AssertionError("Old complex CTA remains on home page")

    purchase_buttons = re.findall(
        r'<button\b[^>]*\bdata-open-checkout\b[^>]*>',
        home,
        flags=re.IGNORECASE,
    )
    if len(purchase_buttons) != 2:
        raise AssertionError(
            f"Home page must contain exactly two checkout buttons, found {len(purchase_buttons)}"
        )
    if 'class="history-cta"' in home:
        raise AssertionError("Mid-history purchase CTA must be removed")
    if 'class="mobile-cta"' in home:
        raise AssertionError("Sticky mobile purchase CTA must be removed")

    header_match = re.search(
        r'<header\b[^>]*class="[^"]*site-header[^"]*"[^>]*>.*?</header>',
        home,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not header_match:
        raise AssertionError("Home header was not found")
    if "data-open-checkout" in header_match.group(0):
        raise AssertionError("Header must not contain a purchase button")

    disclosure = re.search(
        r'<details\b(?=[^>]*\bclass="history-disclosure")'
        r'(?=[^>]*\bopen\b)[^>]*>',
        home,
        flags=re.IGNORECASE,
    )
    if not disclosure:
        raise AssertionError("Daily history must be expanded by default")
    if "Lịch sử đối chiếu từng ngày" not in home:
        raise AssertionError("Daily history heading is missing")

    if 'data-public-ready="true"' in home:
        if all(" disabled" in tag.lower() for tag in purchase_buttons):
            raise AssertionError("Both checkout buttons are disabled on a ready page")


def apply(root: Path) -> None:
    pages = list(root.rglob("*.html"))
    if not pages:
        raise FileNotFoundError(f"No HTML files found under {root}")
    for page in pages:
        rewrite_page(page, root)

    validate_home((root / "index.html").read_text(encoding="utf-8"))

    for page in pages:
        if page == root / "index.html":
            continue
        content = page.read_text(encoding="utf-8")
        if 'class="seo-purchase-float"' in content and 'href="/?checkout=1"' not in content:
            raise AssertionError(f"Direct checkout route missing in {page}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.output_root.resolve())


if __name__ == "__main__":
    main()
