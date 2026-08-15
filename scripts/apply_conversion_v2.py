#!/usr/bin/env python3
"""Apply final paid-traffic and checkout enhancements to the built site."""
from __future__ import annotations

import argparse
import re
import shutil
from datetime import date
from pathlib import Path

from optimize_google_ads_landing import optimize as optimize_google_ads_landing


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLE_TAG = '<link rel="stylesheet" href="/conversion-v2.css?v=20260815-1">'
SCRIPT_TAG = '<script defer src="/checkout-enhance.js?v=20260815-4"></script>'
FINANCE_SCRIPT_TAG = '<script defer src="/finance-banner.js?v=20260815-3"></script>'


def inject_before_head_end(content: str, tag: str) -> str:
    if tag in content:
        return content
    if "</head>" not in content:
        raise AssertionError("HTML page is missing </head>")
    return content.replace("</head>", f"  {tag}\n</head>", 1)


def parse_vi_date(content: str, attribute: str) -> date:
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


def apply_home(home: Path) -> None:
    content = home.read_text(encoding="utf-8")
    content = inject_before_head_end(content, STYLE_TAG)
    content = inject_before_head_end(content, SCRIPT_TAG)
    content = inject_before_head_end(content, FINANCE_SCRIPT_TAG)

    replacements = (
        ("Có cả ngày xuất hiện và không xuất hiện", "Có cả ngày trúng và không trúng"),
        ("4 đầu ra đã lưu", "4 số trong báo cáo"),
        ("Đối chiếu thực tế", "Kết quả thực tế"),
        ("Không xuất hiện", "Không trúng"),
        (
            "Một ngày được ghi nhận khi có số trong báo cáo xuất hiện trong 27 mã kết quả đã công bố.",
            "Một ngày được ghi nhận khi có ít nhất một số trong báo cáo xuất hiện trong 27 mã kết quả đã công bố.",
        ),
    )
    for old, new in replacements:
        content = content.replace(old, new)

    content = re.sub(
        r'<details\b(?=[^>]*\bclass="history-disclosure")'
        r'(?![^>]*\bopen\b)([^>]*)>',
        r'<details\1 open>',
        content,
        count=1,
        flags=re.IGNORECASE,
    )

    home.write_text(content, encoding="utf-8")


def validate(root: Path) -> None:
    home = root / "index.html"
    if not home.exists():
        raise FileNotFoundError(f"Missing built home page: {home}")
    content = home.read_text(encoding="utf-8")

    required = (
        STYLE_TAG,
        SCRIPT_TAG,
        FINANCE_SCRIPT_TAG,
        "4 số trong báo cáo",
        "Kết quả thực tế",
        "Có cả ngày trúng và không trúng",
        "có ít nhất một số trong báo cáo xuất hiện",
        "Lịch sử đối chiếu trong tháng này",
    )
    for marker in required:
        if marker not in content:
            raise AssertionError(f"Missing final conversion marker: {marker}")

    # Historical rate is data, not a design constant.
    metric = re.search(
        r'<div class="historical-rate">\s*<p>.*?</p>\s*'
        r'<strong>(\d+)%</strong>\s*<span>\s*(\d+)\s*/\s*(\d+)\s+ngày',
        content,
        flags=re.DOTALL,
    )
    if not metric:
        raise AssertionError("Historical rate block is missing")
    rate_pct, hit_days, total_days = map(int, metric.groups())
    if total_days != 30:
        raise AssertionError(f"Historical validation must cover 30 days, found {total_days}")
    if round(hit_days * 100 / total_days) != rate_pct:
        raise AssertionError(
            f"Historical rate mismatch: {hit_days}/{total_days} does not round to {rate_pct}%"
        )

    report_day = parse_vi_date(content, "data-report-date")
    lock_day = parse_vi_date(content, "data-lock-date")
    row_dates = [
        date.fromisoformat(value)
        for value in re.findall(
            r'class="history-day-row"[^>]*>\s*<time datetime="(\d{4}-\d{2}-\d{2})"',
            content,
            flags=re.IGNORECASE,
        )
    ]
    if any((value.year, value.month) != (report_day.year, report_day.month) for value in row_dates):
        raise AssertionError("History contains a day outside the report month")

    expected_rows = lock_day.day if (lock_day.year, lock_day.month) == (report_day.year, report_day.month) else 0
    if len(row_dates) != expected_rows:
        raise AssertionError(
            f"Expected {expected_rows} completed rows for the report month, found {len(row_dates)}"
        )

    checkout_buttons = re.findall(
        r'<button\b[^>]*\bdata-open-checkout\b[^>]*>',
        content,
        flags=re.IGNORECASE,
    )
    if len(checkout_buttons) != 2:
        raise AssertionError(
            f"Home page must keep exactly two checkout buttons, found {len(checkout_buttons)}"
        )
    if all(" disabled" in button.lower() for button in checkout_buttons):
        raise AssertionError("Both checkout buttons are disabled")

    if not re.search(
        r'<details\b(?=[^>]*class="history-disclosure")(?=[^>]*\bopen\b)[^>]*>',
        content,
        flags=re.IGNORECASE,
    ):
        raise AssertionError("The current-month history is not expanded by default")

    forbidden = (
        "83% trong 30 ngày",
        "25/30 ngày",
        "có số được phân tích đúng",
        "một trong bốn đầu ra",
    )
    for phrase in forbidden:
        if phrase in content:
            raise AssertionError(f"Outdated public claim remains: {phrase}")

    if re.search(r'19\s*[-–—]\s*91[\s\S]{0,120}05\s*[-–—]\s*50', content):
        raise AssertionError("Current paid report pairs leaked into public HTML")


def apply(root: Path) -> None:
    apply_home(root / "index.html")
    validate(root)

    tracking_source = REPO_ROOT / "site-v2" / "ads-tracking.js"
    if not tracking_source.exists():
        raise FileNotFoundError(f"Missing Ads tracker source: {tracking_source}")
    shutil.copy2(tracking_source, root / "ads-tracking.js")

    finance_source = REPO_ROOT / "site-v2" / "finance-banner.js"
    if not finance_source.exists():
        raise FileNotFoundError(f"Missing finance banner source: {finance_source}")
    shutil.copy2(finance_source, root / "finance-banner.js")

    optimize_google_ads_landing(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.output_root.resolve())


if __name__ == "__main__":
    main()
