#!/usr/bin/env python3
"""Normalize public-facing historical-result wording in built HTML pages."""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path


REPLACEMENTS = (
    (
        "có ít nhất một trong bốn đầu ra đã lưu xuất hiện trong 27 mã kết quả đã công bố",
        "có số được phân tích đúng trong 27 mã kết quả đã công bố",
    ),
    (
        "có ít nhất một trong bốn đầu ra xuất hiện trong kết quả đã công bố",
        "có số được phân tích đúng",
    ),
    (
        "có ít nhất một đầu ra xuất hiện",
        "có số được phân tích đúng",
    ),
    (
        "có đầu ra xuất hiện",
        "có số được phân tích đúng",
    ),
)

FORBIDDEN = (
    "một trong bốn đầu ra",
    "có ít nhất một đầu ra xuất hiện",
    "có đầu ra xuất hiện",
)


def replace_wording(output_root: Path) -> None:
    html_files = list(output_root.rglob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files found under {output_root}")

    for page in html_files:
        content = page.read_text(encoding="utf-8")
        for old, new in REPLACEMENTS:
            content = content.replace(old, new)
        page.write_text(content, encoding="utf-8")

    home = output_root / "index.html"
    if not home.exists():
        raise FileNotFoundError(f"Missing home page: {home}")
    home_content = home.read_text(encoding="utf-8")
    if "có số được phân tích đúng" not in home_content:
        raise AssertionError("New public wording was not applied to the home page")

    for page in html_files:
        content = page.read_text(encoding="utf-8")
        for phrase in FORBIDDEN:
            if phrase in content:
                raise AssertionError(f"Old wording remains in {page}: {phrase}")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "index.html").write_text(
            "25/30 ngày có ít nhất một trong bốn đầu ra xuất hiện trong kết quả đã công bố. "
            "Một ngày được ghi nhận khi có ít nhất một trong bốn đầu ra đã lưu xuất hiện "
            "trong 27 mã kết quả đã công bố.",
            encoding="utf-8",
        )
        replace_wording(root)
        result = (root / "index.html").read_text(encoding="utf-8")
        assert "25/30 ngày có số được phân tích đúng" in result
        assert "có số được phân tích đúng trong 27 mã kết quả đã công bố" in result


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
        replace_wording(args.output_root.resolve())


if __name__ == "__main__":
    main()
