#!/usr/bin/env python3
"""Keep the homepage free of the retired yesterday-method proof block.

This module intentionally remains as a compatibility hook because the Pages
pipeline calls it through apply_portal_v3_assets.py. It removes any legacy
markup/style/data artifact and otherwise makes no public-method settlement.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'data-yesterday-public-methods="true"'
STYLE_ID = "lm-yesterday-public-methods-style"


def apply(root: Path) -> dict[str, Any]:
    home = root / "index.html"
    if not home.is_file():
        raise FileNotFoundError(home)

    text = home.read_text(encoding="utf-8")
    before = text
    text = re.sub(
        r'<section\b[^>]*data-yesterday-public-methods="true"[^>]*>.*?</section>',
        '',
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'<style\b[^>]*id="lm-yesterday-public-methods-style"[^>]*>.*?</style>',
        '',
        text,
        flags=re.I | re.S,
    )
    if MARKER in text or STYLE_ID in text:
        raise ValueError("Retired yesterday-method block still present")
    if text != before:
        home.write_text(text, encoding="utf-8")

    legacy = root / "yesterday-public-methods.json"
    if legacy.exists():
        legacy.unlink()

    return {
        "status": "REMOVED",
        "homepage_block": False,
        "public_json": False,
        "changed": text != before,
    }


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.joinpath("index.html").write_text(
            '<html><head><style id="lm-yesterday-public-methods-style">x</style></head>'
            '<body><main><section data-yesterday-public-methods="true">old</section>'
            '<section><h2>Công cụ thống kê XSMB</h2></section></main></body></html>',
            encoding="utf-8",
        )
        root.joinpath("yesterday-public-methods.json").write_text('{}', encoding="utf-8")
        result = apply(root)
        output = root.joinpath("index.html").read_text(encoding="utf-8")
        assert result["status"] == "REMOVED"
        assert MARKER not in output and STYLE_ID not in output
        assert not root.joinpath("yesterday-public-methods.json").exists()
    print("YESTERDAY_METHOD_BLOCK_REMOVAL_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT / "_site")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(apply(args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
