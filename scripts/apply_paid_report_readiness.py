#!/usr/bin/env python3
"""Apply paid-report readiness to the built landing page without exposing codes.

The public method feed and the paid report are separate products. Payment may
open when the private paid-report readiness manifest is PUBLISHED for the
current Vietnam date, even if the optional public-method feed has not refreshed.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
VALID_STATUSES = {"PUBLISHED_PASS_PRIVATE", "PUBLISHED", "PUBLISHED_PASS"}


def apply_readiness(output_root: Path, manifest_path: Path) -> bool:
    index = output_root / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Missing built landing page: {index}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    today = datetime.now(VN_TZ).date()
    report_date = str(manifest.get("report_date") or manifest.get("target_date") or "")
    lock_date = str(manifest.get("data_lock") or "")
    status = str(manifest.get("status") or manifest.get("report_stage") or "")
    outcome_known = manifest.get("outcome_known_at_selection")

    expected_report = today.isoformat()
    expected_lock = (today - timedelta(days=1)).isoformat()
    ready = (
        report_date == expected_report
        and lock_date == expected_lock
        and status in VALID_STATUSES
        and outcome_known is False
    )

    content = index.read_text(encoding="utf-8")
    content, count = re.subn(
        r'(<body\b[^>]*\bdata-public-ready=")[^"]+("[^>]*>)',
        rf'\g<1>{str(ready).lower()}\g<2>',
        content,
        count=1,
        flags=re.IGNORECASE,
    )
    if count != 1:
        raise AssertionError("Landing page is missing data-public-ready")

    if ready:
        content = re.sub(
            r'(<(?:button|a)\b[^>]*\bdata-open-checkout\b[^>]*)\sdisabled(?:="disabled")?',
            r'\1',
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            r'(<(?:button|a)\b[^>]*\bdata-open-checkout\b[^>]*)\saria-disabled="true"',
            r'\1',
            content,
            flags=re.IGNORECASE,
        )
    index.write_text(content, encoding="utf-8")
    return ready


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "paid-report-ready.json",
    )
    args = parser.parse_args()
    ready = apply_readiness(args.output_root.resolve(), args.manifest.resolve())
    print(f"paid_report_ready={str(ready).lower()}")


if __name__ == "__main__":
    main()
