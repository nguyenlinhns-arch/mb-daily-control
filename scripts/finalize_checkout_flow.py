#!/usr/bin/env python3
"""Make every purchase CTA simple, prominent and payment-direct."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


ROUTER_SRC = "/checkout-router.js?v=20260815-1"
TEXT_REPLACEMENTS = (
    ("MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ", "NHẬN BÁO CÁO HÔM NAY – 30.000Đ"),
    ("Mở kết luận AI hôm nay", "Nhận báo cáo hôm nay"),
    ("MỞ KẾT LUẬN AI · 30K", "NHẬN BÁO CÁO · 30K"),
    ("MỞ KẾT LUẬN AI HÔM NAY", "NHẬN BÁO CÁO HÔM NAY"),
    ("MỞ KẾT LUẬN", "NHẬN BÁO CÁO"),
    ("Mở kết luận AI ngày hôm nay", "Nhận báo cáo AI ngày hôm nay"),
    ("YÊU CẦU MỞ KẾT LUẬN", "YÊU CẦU NHẬN BÁO CÁO"),
)


def inject_router(content: str) -> str:
    if ROUTER_SRC in content:
        return content
    return content.replace(
        "</head>",
        f'  <script defer src="{ROUTER_SRC}"></script>\n</head>',
        1,
    )


def normalize_links(content: str) -> str:
    content = re.sub(
        r'href="(?:https://lemienbac\.com)?/#(?:buy|pricing|checkout)"',
        'href="/?checkout=1" data-checkout-route',
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r'href="/\?checkout=1"(?!\s+data-checkout-route)',
        'href="/?checkout=1" data-checkout-route',
        content,
        flags=re.IGNORECASE,
    )
    return content


def finalize(output_root: Path) -> None:
    html_files = list(output_root.rglob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files found under {output_root}")

    for page in html_files:
        content = page.read_text(encoding="utf-8")
        for old, new in TEXT_REPLACEMENTS:
            content = content.replace(old, new)
        content = normalize_links(content)
        content = inject_router(content)
        page.write_text(content, encoding="utf-8")

    home = output_root / "index.html"
    home_content = home.read_text(encoding="utf-8")
    if 'data-public-ready="true"' not in home_content:
        raise AssertionError("Checkout finalizer requires a published report")
    if "NHẬN BÁO CÁO HÔM NAY – 30.000Đ" not in home_content:
        raise AssertionError("Simple primary CTA is missing")
    if 'data-open-checkout' not in home_content:
        raise AssertionError("Home page has no direct checkout button")
    if re.search(r'data-open-checkout[^>]*\sdisabled', home_content, re.IGNORECASE):
        raise AssertionError("A direct checkout button is still disabled")
    if "MỞ KẾT LUẬN" in home_content or "Mở kết luận" in home_content:
        raise AssertionError("Complex conclusion wording remains on the home page")
    for page in html_files:
        content = page.read_text(encoding="utf-8")
        if '/#buy' in content or '/#pricing' in content:
            raise AssertionError(f"Indirect purchase anchor remains in {page}")
        if ROUTER_SRC not in content:
            raise AssertionError(f"Checkout router is missing in {page}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    finalize(args.output_root.resolve())


if __name__ == "__main__":
    main()
