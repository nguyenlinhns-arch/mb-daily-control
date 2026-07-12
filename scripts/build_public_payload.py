#!/usr/bin/env python3
"""Build the website-safe payload without the owner's private P/L totals.

The operational data/current.json remains available to the settlement engine inside the
repository checkout.  GitHub Pages must publish only the output of this script.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "current.json"
DEFAULT_OUTPUT = ROOT / "data" / "public.json"
RULE_VERSION = "OWNER_ONLY_FINANCE_V1"

DROP_EXACT = {
    "ledger_snapshot",
    "pnl_summary",
    "pnl_vnd",
    "pnl_units",
    "pnl_status",
    "pnl_included",
    "lo_pnl_vnd",
    "xien_pnl_vnd",
    "total_pnl_vnd",
    "yesterday_pnl_vnd",
    "five_group_pnl_vnd",
    "user_lo_pnl_vnd",
    "active_five_group_pnl_vnd",
    "active_all_real_pnl_vnd",
    "archive_pnl_vnd",
    "grand_total_pnl_vnd",
    "total_payout_vnd",
    "payout_vnd",
}

PRIVATE_GROUP_IDS = {"USER_REAL"}
SENSITIVE_TEXT = re.compile(r"(?:p\s*/\s*l|lãi\s*/?\s*lỗ|tổng\s+lãi|tổng\s+lỗ)", re.I)
MONEY_TEXT = re.compile(r"(?:[+−-]?\d[\d.\s,]*\s*đ)", re.I)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def redact_text(text: str) -> str:
    if SENSITIVE_TEXT.search(text) and (MONEY_TEXT.search(text) or any(ch.isdigit() for ch in text)):
        return "Số liệu lãi/lỗ đã chuyển sang sổ riêng của chủ sở hữu."
    return text


def clean(value: Any, *, parent_group: str = "") -> Any:
    if isinstance(value, list):
        return [clean(item, parent_group=parent_group) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    if not isinstance(value, dict):
        return value

    group_id = str(value.get("id") or parent_group).upper()
    result: dict[str, Any] = {}
    for key, item in value.items():
        low = str(key).lower()
        if key in DROP_EXACT or low in DROP_EXACT or "pnl" in low:
            continue
        if group_id in PRIVATE_GROUP_IDS and key in {"historical_profile", "quality_benchmark"}:
            continue
        result[key] = clean(item, parent_group=group_id)
    return result


def build(source: dict[str, Any]) -> dict[str, Any]:
    public = clean(copy.deepcopy(source))
    public["finance_privacy"] = {
        "status": "OWNER_ONLY",
        "rule_version": RULE_VERSION,
        "public_visible": False,
        "message": "Sổ lãi/lỗ cá nhân không được xuất bản trên website công khai.",
    }
    public["pnl_summary"] = {
        "privacy_status": "OWNER_ONLY",
        "public_visible": False,
    }
    public.pop("ledger_snapshot", None)

    portfolio = public.get("portfolio") or {}
    if str(portfolio.get("decision", "")).upper() == "SETTLED_ACTUAL_ORDER":
        portfolio["title"] = "KẾT QUẢ ĐÃ KHÓA · SỔ RIÊNG"
        portfolio["reason"] = "Kết quả đã được khóa; số liệu tài chính chỉ hiển thị trong sổ riêng của chủ sở hữu."
        portfolio.pop("payout_vnd", None)
    public["portfolio"] = portfolio

    top = public.get("top_signals") or {}
    if "KẾT QUẢ" in str(top.get("title", "")).upper():
        top["subtitle"] = "Kết quả đã khóa · tài chính riêng tư"
        top["note"] = "Thông tin lãi/lỗ chỉ được lưu trong sổ riêng của chủ sở hữu."
    public["top_signals"] = top

    automation = public.setdefault("automation", {})
    automation["public_finance_sanitized"] = True
    automation["public_finance_rule_version"] = RULE_VERSION
    return public


def validate(doc: dict[str, Any]) -> None:
    raw = json.dumps(doc, ensure_ascii=False).lower()
    assert (doc.get("finance_privacy") or {}).get("status") == "OWNER_ONLY"
    assert (doc.get("finance_privacy") or {}).get("public_visible") is False
    assert "ledger_snapshot" not in doc
    for forbidden in (
        '"grand_total_pnl_vnd"', '"active_all_real_pnl_vnd"', '"archive_pnl_vnd"',
        '"five_group_pnl_vnd"', '"user_lo_pnl_vnd"', '"total_pnl_vnd"',
        '"lo_pnl_vnd"', '"xien_pnl_vnd"', '"payout_vnd"'
    ):
        assert forbidden not in raw, forbidden
    assert (doc.get("automation") or {}).get("public_finance_sanitized") is True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = load(Path(args.input))
    public = build(source)
    validate(public)
    if not args.check:
        write(Path(args.output), public)
    print("PUBLIC_FINANCE_PAYLOAD_OK", args.output)


if __name__ == "__main__":
    main()
