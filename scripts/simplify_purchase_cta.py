#!/usr/bin/env python3
"""Make purchase CTAs direct, simple and consistent across built pages."""
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


def rewrite_page(page: Path, root: Path) -> None:
    content = page.read_text(encoding="utf-8")
    for old, new in TEXT_REPLACEMENTS:
        content = content.replace(old, new)

    if page != root / "index.html":
        content = re.sub(
            r'(<a\b[^>]*\bclass="[^"]*(?:top-cta|primary-cta|seo-purchase-float)[^"]*"[^>]*\bhref=")[^"]*(")',
            r'\1/?checkout=1\2',
            content,
            flags=re.IGNORECASE,
        )
        content = content.replace('href="/?buy=1"', 'href="/?checkout=1"')

    if page == root / "index.html" and SCRIPT_TAG not in content:
        app_tag = re.search(r'<script\s+defer\s+src="[^\"]*app\.js[^\"]*"></script>', content, re.IGNORECASE)
        if app_tag:
            insert_at = app_tag.end()
            content = content[:insert_at] + "\n  " + SCRIPT_TAG + content[insert_at:]
        elif "</head>" in content:
            content = content.replace("</head>", f"  {SCRIPT_TAG}\n</head>", 1)
        else:
            raise AssertionError("Unable to inject checkout-entry.js")

    page.write_text(content, encoding="utf-8")


def apply(root: Path) -> None:
    pages = list(root.rglob("*.html"))
    if not pages:
        raise FileNotFoundError(f"No HTML files found under {root}")
    for page in pages:
        rewrite_page(page, root)

    home = (root / "index.html").read_text(encoding="utf-8")
    if SCRIPT_TAG not in home:
        raise AssertionError("Checkout entry script was not injected")
    if "NHẬN BÁO CÁO HÔM NAY – 30.000Đ" not in home:
        raise AssertionError("Simple purchase CTA is missing")
    if "MỞ KẾT LUẬN" in home:
        raise AssertionError("Old complex CTA remains on home page")
    if 'data-public-ready="true"' in home:
        active = re.findall(r'<button\b[^>]*data-open-checkout[^>]*>', home, flags=re.IGNORECASE)
        if not active:
            raise AssertionError("Ready page has no checkout button")
        if all(" disabled" in tag.lower() for tag in active):
            raise AssertionError("All checkout buttons are disabled on ready page")

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
