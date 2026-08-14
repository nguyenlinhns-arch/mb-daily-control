#!/usr/bin/env python3
"""Enable checkout only for an explicitly published paid report.

The public-method output may be stale or intentionally removed from the landing
page. Checkout readiness therefore comes from a small status artifact that does
not expose the paid 4SO pairs. The source lock must still match the current
public source snapshot and the dates rendered into the landing page.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


BODY_PATTERN = re.compile(
    r'<body(?P<before>[^>]*?)data-report-date="(?P<report>\d{2}/\d{2}/\d{4})"'
    r'(?P<middle>[^>]*?)data-lock-date="(?P<lock>\d{2}/\d{2}/\d{4})"'
    r'(?P<after>[^>]*?)>',
    re.IGNORECASE,
)
BUTTON_PATTERN = re.compile(
    r'<button(?P<attrs>[^>]*\bdata-open-checkout\b[^>]*)>',
    re.IGNORECASE,
)


def iso_to_dmy(value: str) -> str:
    parsed = date.fromisoformat(value)
    return parsed.strftime("%d/%m/%Y")


def clean_button(match: re.Match[str]) -> str:
    attrs = match.group("attrs")
    attrs = re.sub(r"\s+disabled(?:=\"disabled\")?", "", attrs, flags=re.IGNORECASE)
    attrs = re.sub(
        r'\s+aria-disabled="(?:true|false)"',
        ' aria-disabled="false"',
        attrs,
        flags=re.IGNORECASE,
    )
    return f"<button{attrs}>"


def activate(output_root: Path, status_path: Path, source_path: Path) -> bool:
    status = json.loads(status_path.read_text(encoding="utf-8"))
    source = json.loads(source_path.read_text(encoding="utf-8"))

    valid = (
        status.get("schema_version") == "MB_PAID_REPORT_STATUS_V1"
        and status.get("report_stage") == "PUBLISHED"
        and int(status.get("pair_count") or 0) == 2
        and int(status.get("code_count") or 0) == 4
        and status.get("public_codes_exposed") is False
        and source.get("history_end") == status.get("data_lock")
        and source.get("status") == "LOCKED_CROSSCHECKED_PUBLIC"
    )
    if not valid:
        return False

    index = output_root / "index.html"
    content = index.read_text(encoding="utf-8")
    body = BODY_PATTERN.search(content)
    if not body:
        raise ValueError("Landing page is missing report/lock date attributes")

    report_dmy = iso_to_dmy(str(status["target_date"]))
    lock_dmy = iso_to_dmy(str(status["data_lock"]))
    if body.group("report") != report_dmy or body.group("lock") != lock_dmy:
        return False

    content = re.sub(
        r'data-public-ready="(?:true|false)"',
        'data-public-ready="true"',
        content,
        count=1,
        flags=re.IGNORECASE,
    )
    content = BUTTON_PATTERN.sub(clean_button, content)
    index.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--status", type=Path, default=Path("data/paid-report-status.json"))
    parser.add_argument("--source", type=Path, default=Path("data/source-access.json"))
    args = parser.parse_args()

    activated = activate(
        args.output_root.resolve(),
        args.status.resolve(),
        args.source.resolve(),
    )
    print("PAID_CHECKOUT_ACTIVE" if activated else "PAID_CHECKOUT_FAIL_CLOSED")


if __name__ == "__main__":
    main()
