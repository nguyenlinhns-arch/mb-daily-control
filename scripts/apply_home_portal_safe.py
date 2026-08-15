#!/usr/bin/env python3
"""Thin finalizer around apply_home_portal that counts real button tags only."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import apply_home_portal as portal


def apply(output_root: Path) -> dict[str, object]:
    page = output_root / "index.html"
    stats_path = output_root / "statistics-data.json"
    if not page.exists() or not stats_path.exists():
        raise FileNotFoundError("Homepage or statistics-data.json missing")

    result = portal.build_home(
        page.read_text(encoding="utf-8"),
        portal.load_json(stats_path),
        portal.load_json(portal.PUBLIC_METHODS),
        portal.load_json(portal.PUBLIC_PROOF),
        portal.load_json(portal.PAID_READY),
    )
    buttons = re.findall(r'<button\b[^>]*\bdata-open-checkout\b[^>]*>', result, flags=re.I)
    if len(buttons) != 2:
        raise ValueError(f"Homepage must contain exactly two checkout buttons, found {len(buttons)}")
    if 'data-home-portal="v1"' not in result or 'Phương pháp công khai hôm nay' not in result:
        raise ValueError("Portal homepage markers missing")
    if re.search(r'4SO[^<]{0,180}\b\d{2}\b\s*[-–—]\s*\b\d{2}\b', result, flags=re.I):
        raise ValueError("Potential current 4SO pair leaked in homepage")

    page.write_text(result, encoding="utf-8")
    return {"status":"PASS","homepage":"portal-v1","checkout_buttons":2}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', type=Path, default=portal.ROOT / '_site')
    args = parser.parse_args()
    print(json.dumps(apply(args.output_root), ensure_ascii=False))


if __name__ == '__main__':
    main()
