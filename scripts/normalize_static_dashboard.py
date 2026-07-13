#!/usr/bin/env python3
"""Normalize the public static dashboard before GitHub Pages deployment.

The public page must never expose long internal execution enums or allow a stale
A1 Volume card to display 100 points for a palindrome. This post-processor is
small, deterministic, and safe to run on every Pages build.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

STATUS_MAP = {
    "SYSTEM_SIGNAL_NOT_YET_CONFIRMED": "CHỜ XÁC NHẬN",
    "CONFIRMED_REAL": "ĐÃ XÁC NHẬN",
    "REAL_SETTLED_WIN": "ĐÃ QUYẾT TOÁN · TRÚNG",
    "REAL_SETTLED_LOSS": "ĐÃ QUYẾT TOÁN · TRƯỢT",
}

SAFE_CSS = """
/* MB_STATUS_SAFE_V1 */
.stat{min-width:0;overflow:hidden}
.stat b{max-width:100%;overflow-wrap:anywhere;word-break:break-word;white-space:normal;line-height:1.22;font-size:clamp(12px,2.1vw,18px)}
.status{max-width:100%;overflow-wrap:anywhere;word-break:break-word;white-space:normal;line-height:1.2}
@media(max-width:430px){.stat b{font-size:13px}.status{font-size:11px}}
""".strip()


def _fix_a1_volume_card(text: str) -> str:
    """Defensively enforce Volume50 in the rendered A1 Volume card only."""
    pattern = re.compile(
        r"(<article[^>]*>.*?<h3>MB A1 Volume</h3>.*?</article>)",
        flags=re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return text
    block = match.group(1)
    # Every funded leg of A1 Volume is 50 points. Palindromes have one leg only.
    block = re.sub(
        r"(<div class=\"num(?:ber)? pass\"[^>]*>\s*<strong>[^<]+</strong>\s*<span>)\d+ điểm(</span>)",
        r"\g<1>50 điểm\g<2>",
        block,
    )
    block = re.sub(
        r"(<div class=\"num(?:ber)? pass\"[^>]*>.*?<small>)[\d.]+đ(</small>)",
        r"\g<1>1.150.000đ\g<2>",
        block,
        flags=re.DOTALL,
    )
    block = re.sub(r"(Điểm(?: thật|/số)?\s*<b>)\d+(</b>)", r"\g<1>50\g<2>", block)
    funded_tiles = len(re.findall(r"<div class=\"num(?:ber)? pass\"", block))
    if funded_tiles:
        capital = funded_tiles * 1_150_000
        capital_text = f"{capital:,}đ".replace(",", ".")
        block = re.sub(r"(Vốn\s*<b>)[\d.]+đ(</b>)", rf"\g<1>{capital_text}\g<2>", block)
    return text[: match.start()] + block + text[match.end() :]


def normalize(text: str) -> str:
    for raw, short in STATUS_MAP.items():
        text = text.replace(raw, short)

    if "data-static-dashboard=" not in text:
        text = text.replace("<body>", '<body data-static-dashboard="1">', 1)

    if "MB_STATUS_SAFE_V1" not in text:
        text = text.replace("</style>", SAFE_CSS + "\n</style>", 1)

    text = _fix_a1_volume_card(text)
    # Known stale hero wording from the 14/07 legacy payload.
    text = text.replace(
        "A1 88 — 100 ĐIỂM · KHÔNG ĐÁNH ĐẢO TRÙNG",
        "88 ×50 · 54 ×50 · 45 ×50",
    )
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    src = Path(args.input)
    dst = Path(args.output)
    expected = normalize(src.read_text(encoding="utf-8"))
    if args.check:
        if not dst.exists() or dst.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"Static dashboard normalization is stale: {dst}")
        print("STATIC_DASHBOARD_NORMALIZATION_OK")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(expected, encoding="utf-8")
    print(f"STATIC_DASHBOARD_NORMALIZED={dst}")


if __name__ == "__main__":
    main()
