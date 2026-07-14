#!/usr/bin/env python3
"""Final active-payload scrub for the permanent A1 Core100/Volume50 lock.

Runs after the primary stake guard. It removes every case variant of the retired
Core50/Volume30 wording from active files and removes A1-only metadata that may
have leaked into non-A1 method cards. Historical ledgers are not touched.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data/current.json"
POLICY = ROOT / "data/automation-policy.json"
INDEX = ROOT / "index.html"
CORE = 100
VOLUME = 50
REVERSE = 50


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def scrub_text(text: str) -> str:
    replacements = (
        (r"(?i)CORE50_VOLUME30", "CORE100_VOLUME50"),
        (r"(?i)core\s*50\s*/\s*volume\s*30", "Core100/Volume50"),
        (r"(?i)core\s*50", "Core100"),
        (r"(?i)volume\s*30", "Volume50"),
    )
    out = text
    for pattern, replacement in replacements:
        out = re.sub(pattern, replacement, out)
    return out


def scrub(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    return value


def is_a1_method(method: dict[str, Any]) -> bool:
    ident = str(method.get("id", "")).upper()
    label = str(method.get("label", "")).upper()
    method_name = str(method.get("method", "")).upper()
    return ident.startswith("A1") or label.startswith("MB A1") or method_name.startswith("A1 ") or "DUAL CORE VOLUME" in method_name


def clean_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out = scrub(doc)
    out["config_id"] = scrub_text(str(out.get("config_id", "")))
    stake = out.setdefault("stake_rule", {})
    stake.update({
        "a1_core_points_per_code": CORE,
        "a1_volume_points_per_code": VOLUME,
        "a1_core_main_points": CORE,
        "a1_volume_main_points": VOLUME,
        "a1_reverse_points": REVERSE,
        "a1_reverse_points_per_code": REVERSE,
        "a1_reverse_skip_when_same": True,
        "a1_no_duplicate_same_code": True,
        "legacy_core50_volume30_forbidden": True,
        "canonical_stake_guard_version": "A1_CORE100_VOLUME50_REVERSE50_NO_DUP_V6",
    })
    out.setdefault("top_signal_policy", {})["controller"] = "DATA_GATE > CORE100 > VOLUME50 > A0"
    out["top_signal_policy"]["a1_staking_rule"] = "Core100 → nếu không có Core mới Volume50 → A0; reverse50 nếu khác mã chính"
    for method in (out.get("top_signals") or {}).get("methods") or []:
        if not is_a1_method(method):
            for key in ("core_main_points", "volume_main_points", "reverse_points", "primary_points_per_code", "reverse_points_per_code", "reverse_skip_when_same"):
                method.pop(key, None)
    for group in out.get("groups") or []:
        if str(group.get("id", "")).upper() != "A1":
            for key in ("core_main_points", "volume_main_points", "reverse_points"):
                group.pop(key, None)
    out.setdefault("automation", {})["a1_staking_guard"] = "A1_CORE100_VOLUME50_REVERSE50_NO_DUP_V6"
    return out


def assert_clean(name: str, text: str) -> None:
    forbidden = (
        r"(?i)CORE50_VOLUME30",
        r"(?i)core\s*50(?!0)",
        r"(?i)volume\s*30",
    )
    for pattern in forbidden:
        if re.search(pattern, text):
            raise AssertionError(f"{name} contains retired A1 stake wording: {pattern}")


def target_plan(doc: dict[str, Any]) -> Path | None:
    target = str(doc.get("target_date") or "")
    return ROOT / "data/plans" / f"{target}.json" if target else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = load(CURRENT)
    plan_path = target_plan(current)
    if args.check:
        assert_clean("data/current.json", CURRENT.read_text(encoding="utf-8"))
        assert_clean("index.html", INDEX.read_text(encoding="utf-8"))
        if plan_path and plan_path.exists():
            assert_clean(str(plan_path), plan_path.read_text(encoding="utf-8"))
        stake = current.get("stake_rule") or {}
        assert int(stake.get("a1_core_points_per_code")) == CORE
        assert int(stake.get("a1_volume_points_per_code")) == VOLUME
        assert int(stake.get("a1_reverse_points")) == REVERSE
        assert (current.get("top_signal_policy") or {}).get("controller") == "DATA_GATE > CORE100 > VOLUME50 > A0"
        print("A1_CORE100_VOLUME50_FINAL_ACTIVE_CHECK_OK")
        return

    changed: list[str] = []
    cleaned = clean_doc(current)
    if cleaned != current:
        save(CURRENT, cleaned); changed.append("data/current.json")
    if plan_path and plan_path.exists():
        plan = load(plan_path)
        cleaned_plan = clean_doc(plan)
        if cleaned_plan != plan:
            save(plan_path, cleaned_plan); changed.append(str(plan_path.relative_to(ROOT)))
    policy = load(POLICY)
    cleaned_policy = scrub(policy)
    a1 = cleaned_policy.setdefault("a1", {})
    a1.update({"core_points_main": CORE, "volume_points_main": VOLUME, "legacy_core50_volume30_forbidden": True})
    if cleaned_policy != policy:
        save(POLICY, cleaned_policy); changed.append("data/automation-policy.json")
    html = INDEX.read_text(encoding="utf-8")
    cleaned_html = scrub_text(html)
    if cleaned_html != html:
        INDEX.write_text(cleaned_html, encoding="utf-8"); changed.append("index.html")
    print("A1_CORE100_VOLUME50_FINALIZED", changed)


if __name__ == "__main__":
    main()
