#!/usr/bin/env python3
"""Apply conversion rendering without assuming historical detail is available.

The underlying optimizer keeps strict self-tests for ready pages. This wrapper
is used by the daily Pages build so a fail-closed, updating page can still be
published when the latest history block is intentionally absent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from optimize_conversion_site import inject_stylesheet, optimize_home, write_if_changed


def apply_site(output_root: Path) -> None:
    html_files = list(output_root.rglob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files found under {output_root}")

    home_path = output_root / "index.html"
    if not home_path.exists():
        raise FileNotFoundError(f"Missing home page: {home_path}")

    for page in html_files:
        content = inject_stylesheet(page.read_text(encoding="utf-8"))
        if page == home_path:
            content = optimize_home(content)
        write_if_changed(page, content)

    home = home_path.read_text(encoding="utf-8")
    required = (
        'class="conversion-trust"',
        'class="buy-value-list"',
        'class="buy-guarantees"',
        'class="checkout-value"',
        'class="checkout-trust"',
    )
    for marker in required:
        if marker not in home:
            raise AssertionError(f"Missing conversion marker: {marker}")

    ready = 'data-public-ready="true"' in home
    history_available = 'class="historical-disclaimer"' in home
    if ready:
        for marker in (
            'class="conversion-preview"',
            'class="history-cta"',
            "MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ",
        ):
            if marker not in home:
                raise AssertionError(f"Ready page missing marker: {marker}")
    else:
        if 'class="history-cta"' in home:
            raise AssertionError("Updating page must not expose a history purchase CTA")
        if "CHƯA NHẬN THANH TOÁN" not in home:
            raise AssertionError("Updating page must stay fail-closed")

    if history_available and 'class="history-disclosure"' not in home:
        raise AssertionError("Historical detail must be collapsed when available")
    if not history_available and 'class="history-disclosure"' in home:
        raise AssertionError("Updating page must not contain stale historical detail")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    apply_site(args.output_root.resolve())


if __name__ == "__main__":
    main()
