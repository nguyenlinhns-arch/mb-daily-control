#!/usr/bin/env python3
"""Apply the final paid-traffic and checkout enhancements to the built site."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


STYLE_TAG = '<link rel="stylesheet" href="/conversion-v2.css?v=20260815-1">'
SCRIPT_TAG = '<script defer src="/checkout-enhance.js?v=20260815-1"></script>'


def inject_before_head_end(content: str, tag: str) -> str:
    if tag in content:
        return content
    if "</head>" not in content:
        raise AssertionError("HTML page is missing </head>")
    return content.replace("</head>", f"  {tag}\n</head>", 1)


def apply_home(home: Path) -> None:
    content = home.read_text(encoding="utf-8")
    content = inject_before_head_end(content, STYLE_TAG)
    content = inject_before_head_end(content, SCRIPT_TAG)

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

    # The evidence table must be visible without an extra click.
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
        "73%",
        "22/30 ngày",
        "4 số trong báo cáo",
        "Kết quả thực tế",
        "Có cả ngày trúng và không trúng",
        "có ít nhất một số trong báo cáo xuất hiện",
    )
    for marker in required:
        if marker not in content:
            raise AssertionError(f"Missing final conversion marker: {marker}")

    rows = len(re.findall(r'class="history-day-row"', content))
    if rows != 30:
        raise AssertionError(f"Expected 30 completed history rows, found {rows}")

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
        raise AssertionError("The 30-day history is not expanded by default")

    forbidden = (
        "83% trong 30 ngày",
        "25/30 ngày",
        "có số được phân tích đúng",
        "một trong bốn đầu ra",
    )
    for phrase in forbidden:
        if phrase in content:
            raise AssertionError(f"Outdated public claim remains: {phrase}")

    # The current paid numbers must remain absent from the public page.
    if re.search(r'19\s*[-–—]\s*91[\s\S]{0,120}05\s*[-–—]\s*50', content):
        raise AssertionError("Current paid report pairs leaked into public HTML")


def apply(root: Path) -> None:
    apply_home(root / "index.html")
    validate(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.output_root.resolve())


if __name__ == "__main__":
    main()
