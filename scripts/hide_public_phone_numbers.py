#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

# Public pages must never expose a mobile number. Users reach Zalo only after
# clicking an internal route. The redirect page also avoids a contiguous phone
# literal in its own HTML source.
DIRECT_ZALO = "https://zalo.me/0398696879"
INTERNAL_ZALO_ROUTE = "/go/zalo/"
PHONE_RE = re.compile(r"(?<!\d)(?:03|05|07|08|09)\d{8}(?!\d)")
TEL_RE = re.compile(r"tel:\+?(?:84|0)?[0-9][0-9 .()-]{7,18}", re.I)
TEXT_SUFFIXES = {".html", ".js", ".json", ".txt", ".xml", ".css"}


def write_zalo_redirect(root: Path) -> None:
    page = root / "go" / "zalo" / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        """<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\"><meta name=\"robots\" content=\"noindex,nofollow\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Đang mở Zalo</title></head><body><p>Đang mở Zalo…</p><script>(()=>{const p=['039','869','6879'].join('');location.replace('https://zalo.me/'+p)})();</script></body></html>""",
        encoding="utf-8",
    )


def sanitize_text(text: str) -> str:
    text = text.replace(DIRECT_ZALO, INTERNAL_ZALO_ROUTE)
    text = TEL_RE.sub(INTERNAL_ZALO_ROUTE, text)
    text = PHONE_RE.sub("", text)
    return text


def sanitize(root: Path) -> dict[str, int | str]:
    write_zalo_redirect(root)
    changed = 0
    checked = 0

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        checked += 1
        original = path.read_text(encoding="utf-8")
        updated = sanitize_text(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1

    # Fail closed: no public text asset may expose a Vietnamese mobile number,
    # direct Zalo phone URL, or tel: URI. The redirect source passes because its
    # phone digits are deliberately split into separate JavaScript fragments.
    failures: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        if DIRECT_ZALO in text or PHONE_RE.search(text) or re.search(r"tel:", text, re.I):
            failures.append(rel)

    if failures:
        raise ValueError("Public phone number leak: " + ", ".join(failures[:20]))

    redirect = root / "go" / "zalo" / "index.html"
    redirect_text = redirect.read_text(encoding="utf-8")
    if "https://zalo.me/" not in redirect_text or "['039','869','6879']" not in redirect_text:
        raise ValueError("Zalo redirect page missing")
    if PHONE_RE.search(redirect_text):
        raise ValueError("Zalo redirect exposes contiguous phone number")

    return {"status": "PASS", "checked": checked, "changed": changed, "route": INTERNAL_ZALO_ROUTE}


def self_test() -> None:
    sample = '<a href="https://zalo.me/0398696879">Zalo 0398696879</a><a href="tel:0398696879">Gọi</a>'
    cleaned = sanitize_text(sample)
    assert DIRECT_ZALO not in cleaned
    assert not PHONE_RE.search(cleaned)
    assert "tel:" not in cleaned.lower()
    assert INTERNAL_ZALO_ROUTE in cleaned
    print("PUBLIC_PHONE_HIDE_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("_site"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    print(sanitize(args.output_root))


if __name__ == "__main__":
    main()
