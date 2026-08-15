#!/usr/bin/env python3
"""Keep the purchase path direct and the visible history limited to this month.

The home page intentionally has exactly two checkout entry points:
1. the hero offer above the evidence;
2. the final purchase card below the evidence.

The daily history between those two blocks is expanded by default, but only
contains completed days from the report's current calendar month. The rolling
30-day rate remains a separate summary metric above the month list.
"""
from __future__ import annotations

import argparse
import re
from datetime import date
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

HISTORY_ROW = re.compile(
    r'<div class="history-day-row" role="row">'
    r'<time datetime="(?P<date>\d{4}-\d{2}-\d{2})">.*?'
    r'</strong></div>',
    re.IGNORECASE | re.DOTALL,
)


def normalize_text(content: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        content = content.replace(old, new)
    return content


def report_month(content: str) -> tuple[int, int]:
    match = re.search(
        r'data-report-date="(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{4})"',
        content,
    )
    if not match:
        raise AssertionError("Home page is missing data-report-date")
    return int(match.group("year")), int(match.group("month"))


def filter_history_to_report_month(content: str) -> str:
    """Remove history rows outside the report month and refresh month copy."""
    year, month = report_month(content)
    prefix = f"{year:04d}-{month:02d}"
    rows = list(HISTORY_ROW.finditer(content))
    if not rows:
        return content

    kept_rows = [match for match in rows if match.group("date").startswith(prefix)]
    hit_days = sum("has-observed" in match.group(0) for match in kept_rows)

    content = HISTORY_ROW.sub(
        lambda match: match.group(0)
        if match.group("date").startswith(prefix)
        else "",
        content,
    )

    if kept_rows:
        first_day = date.fromisoformat(kept_rows[0].group("date"))
        last_day = date.fromisoformat(kept_rows[-1].group("date"))
        count = len(kept_rows)
        range_copy = (
            f"Bảng dưới chỉ hiển thị {count} ngày đã hoàn tất trong tháng "
            f"{month:02d}/{year}, từ {first_day.strftime('%d/%m/%Y')} đến "
            f"{last_day.strftime('%d/%m/%Y')}; có cả ngày trúng và không trúng."
        )
        summary = (
            f'<div><strong>{hit_days}/{count} ngày</strong>'
            '<span>trong tháng này có số trong báo cáo xuất hiện</span></div>'
        )
    else:
        range_copy = (
            f"Tháng {month:02d}/{year} chưa có ngày nào hoàn tất để đối chiếu."
        )
        summary = (
            '<div><strong>0/0 ngày</strong>'
            '<span>trong tháng này chưa có dữ liệu hoàn tất</span></div>'
        )

    content = re.sub(
        r'<p>Bảng dưới(?: chỉ)? hiển thị.*?</p>',
        f"<p>{range_copy}</p>",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    content = re.sub(
        r'<div><strong>\d+/\d+ ngày</strong><span>.*?</span></div>',
        summary,
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    month_label = f"Lịch sử đối chiếu trong tháng này ({month:02d}/{year})"
    content = content.replace(
        "Xem đầy đủ lịch sử đối chiếu từng ngày",
        month_label,
    )
    content = content.replace(
        "Xem lịch sử đối chiếu từng ngày",
        month_label,
    )
    content = content.replace(
        "Lịch sử đối chiếu từng ngày",
        month_label,
    )
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

    content = filter_history_to_report_month(content)

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
    if "Lịch sử đối chiếu trong tháng này" not in home:
        raise AssertionError("Current-month history heading is missing")

    year, month = report_month(home)
    expected_prefix = f"{year:04d}-{month:02d}"
    row_dates = [match.group("date") for match in HISTORY_ROW.finditer(home)]
    if any(not value.startswith(expected_prefix) for value in row_dates):
        raise AssertionError("History contains a day outside the report month")

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
