#!/usr/bin/env python3
"""Bundle home-page CSS and JavaScript to reduce Google Ads landing requests."""
from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path


CSS_FILES = (
    "styles.css",
    "red-white-theme.css",
    "conversion-accent.css",
    "checkout-hotfix.css",
    "conversion-v2.css",
)
JS_FILES = (
    "app.js",
    "checkout-entry.js",
    "checkout-enhance.js",
    "ads-tracking.js",
)
CSS_TAG = '<link rel="stylesheet" href="/landing.css?v=20260815-ads1">'
JS_TAG = '<script defer src="/landing.js?v=20260815-ads1"></script>'


def join_files(root: Path, names: tuple[str, ...], comment_style: str) -> str:
    chunks: list[str] = []
    for name in names:
        path = root / name
        if not path.exists():
            raise FileNotFoundError(f"Missing landing asset: {path}")
        content = path.read_text(encoding="utf-8").strip()
        if comment_style == "css":
            chunks.append(f"/* ---- {name} ---- */\n{content}")
        else:
            chunks.append(f"// ---- {name} ----\n{content}")
    return "\n\n".join(chunks) + "\n"


def remove_asset_tags(content: str) -> str:
    for name in CSS_FILES:
        content = re.sub(
            rf'\s*<link\b[^>]*href="[^"]*{re.escape(name)}(?:\?[^\"]*)?"[^>]*>',
            "",
            content,
            flags=re.IGNORECASE,
        )
    for name in JS_FILES:
        content = re.sub(
            rf'\s*<script\b[^>]*src="[^"]*{re.escape(name)}(?:\?[^\"]*)?"[^>]*></script>',
            "",
            content,
            flags=re.IGNORECASE,
        )
    return content


def bundle(root: Path) -> None:
    home = root / "index.html"
    if not home.exists():
        raise FileNotFoundError(f"Missing home page: {home}")

    (root / "landing.css").write_text(
        join_files(root, CSS_FILES, "css"),
        encoding="utf-8",
    )
    (root / "landing.js").write_text(
        join_files(root, JS_FILES, "js"),
        encoding="utf-8",
    )

    content = home.read_text(encoding="utf-8")
    content = remove_asset_tags(content)
    content = re.sub(
        r'\s*<script\s+id="direct-checkout-script">.*?</script>',
        "",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if CSS_TAG not in content:
        content = content.replace("</head>", f"  {CSS_TAG}\n</head>", 1)

    config = re.search(
        r'<script\b[^>]*src="[^\"]*config\.js[^\"]*"[^>]*></script>',
        content,
        flags=re.IGNORECASE,
    )
    if not config:
        raise AssertionError("config.js must load before the landing bundle")
    if JS_TAG not in content:
        insert_at = config.end()
        content = content[:insert_at] + f"\n  {JS_TAG}" + content[insert_at:]

    home.write_text(content, encoding="utf-8")
    validate(root)


def validate(root: Path) -> None:
    home = (root / "index.html").read_text(encoding="utf-8")
    if CSS_TAG not in home or JS_TAG not in home:
        raise AssertionError("Bundled landing assets were not linked")
    if 'id="direct-checkout-script"' in home:
        raise AssertionError("Duplicate inline checkout router remains")
    for name in CSS_FILES + JS_FILES:
        if re.search(
            rf'(?:href|src)="[^"]*{re.escape(name)}(?:\?[^\"]*)?"',
            home,
            flags=re.IGNORECASE,
        ):
            raise AssertionError(f"Unbundled home asset remains: {name}")
    if home.index("config.js") > home.index("landing.js"):
        raise AssertionError("config.js must load before landing.js")

    css = root / "landing.css"
    js = root / "landing.js"
    if css.stat().st_size < 40_000:
        raise AssertionError("landing.css is unexpectedly small")
    if js.stat().st_size < 10_000:
        raise AssertionError("landing.js is unexpectedly small")
    if "purchase_cta_click" not in js or "img.vietqr.io/image" not in js:
        raise AssertionError("Landing bundle is missing Ads tracking or VietQR")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in CSS_FILES:
            (root / name).write_text("a{" + "x:1;" * 2000 + "}", encoding="utf-8")
        for name in JS_FILES:
            marker = "purchase_cta_click" if name == "ads-tracking.js" else "img.vietqr.io/image" if name == "checkout-enhance.js" else "ok"
            (root / name).write_text(f"(()=>{{const x='{marker}';}})();" + "//x\n" * 1000, encoding="utf-8")
        (root / "index.html").write_text(
            '''<html><head><script src="./config.js?v=1"></script><script defer src="./app.js?v=1"></script><script defer src="/checkout-entry.js?v=1"></script><link rel="stylesheet" href="./styles.css?v=1"><link rel="stylesheet" href="/red-white-theme.css?v=1"><link rel="stylesheet" href="/conversion-accent.css?v=1"><link rel="stylesheet" href="/checkout-hotfix.css?v=1"><link rel="stylesheet" href="/conversion-v2.css?v=1"><script defer src="/checkout-enhance.js?v=1"></script><script defer src="/ads-tracking.js?v=1"></script></head><body><script id="direct-checkout-script">old()</script></body></html>''',
            encoding="utf-8",
        )
        bundle(root)


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
        bundle(args.output_root.resolve())


if __name__ == "__main__":
    main()
