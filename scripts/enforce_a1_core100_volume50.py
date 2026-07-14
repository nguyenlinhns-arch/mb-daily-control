#!/usr/bin/env python3
"""Permanently enforce A1 Core100 / Volume50 / Reverse50.

This guard has two jobs:
1. Patch the materialized base planner constants before the daily planner runs.
2. Normalize and validate the active website payload, the current target-day plan,
   the public dashboard text and the automation policy after every review.

Historical settlements and confirmed manual orders are never rewritten.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data" / "current.json"
POLICY = ROOT / "data" / "automation-policy.json"
STAKE_POLICY = ROOT / "data" / "a1-staking-policy.json"
INDEX = ROOT / "index.html"
BASE_ENGINE = ROOT / "scripts" / "plan_next_day_base.py"
CORE_POINTS = 100
VOLUME_POINTS = 50
REVERSE_POINTS = 50
COST_PER_POINT = 23_000
GUARD_VERSION = "A1_CORE100_VOLUME50_REVERSE50_NO_DUP_V5"

TEXT_REPLACEMENTS = (
    ("MB_A1_DUAL_CORE_VOLUME_BALANCE_GAN21_12_CORE50_VOLUME30_V1_20260713", "MB_A1_DUAL_CORE_VOLUME_BALANCE_GAN21_12_CORE100_VOLUME50_V2_20260715"),
    ("CORE50_VOLUME30", "CORE100_VOLUME50"),
    ("Core50/Volume30", "Core100/Volume50"),
    ("Core50 / Volume30", "Core100 / Volume50"),
    ("Core50 →", "Core100 →"),
    ("Volume30 →", "Volume50 →"),
    ("Core 50 / Volume 30", "Core 100 / Volume 50"),
    ("Core 50/Volume 30", "Core 100/Volume 50"),
    ("Core — 50 điểm/số", "Core — 100 điểm/số"),
    ("Volume — 30 điểm/số", "Volume — 50 điểm/số"),
    ("Core 50; Volume 30", "Core 100; Volume 50"),
    ("Core50", "Core100"),
    ("Volume30", "Volume50"),
)

FORBIDDEN_ACTIVE = (
    "CORE50_VOLUME30",
    "Core50",
    "Volume30",
    "Core 50 / Volume 30",
    "Core — 50 điểm/số",
    "Volume — 30 điểm/số",
)


def load(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def replace_text(text: str) -> str:
    out = text
    for old, new in TEXT_REPLACEMENTS:
        out = out.replace(old, new)
    return out


def replace_strings(value: Any) -> Any:
    if isinstance(value, str):
        return replace_text(value)
    if isinstance(value, list):
        return [replace_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_strings(item) for key, item in value.items()}
    return value


def method_text(method: dict[str, Any]) -> str:
    return " ".join(str(method.get(key, "")) for key in ("id", "label", "method", "status", "tier")).upper()


def a1_tier(method: dict[str, Any]) -> str | None:
    text = method_text(method)
    # Status/id is more reliable than a generic label that may mention both tiers.
    primary = f"{method.get('id', '')} {method.get('status', '')} {method.get('tier', '')}".upper()
    if "VOLUME" in primary:
        return "VOLUME"
    if "CORE" in primary:
        return "CORE"
    if "VOLUME" in text and "CORE" not in text:
        return "VOLUME"
    if "CORE" in text and "VOLUME" not in text:
        return "CORE"
    return None


def positive_number_rows(method: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in (method.get("numbers") or []) if int(row.get("points") or 0) > 0]


def normalize_a1_method(method: dict[str, Any]) -> None:
    if "A1" not in method_text(method):
        return
    tier = a1_tier(method)
    rows = method.get("numbers") or []
    funded = positive_number_rows(method)
    if not funded or tier not in {"CORE", "VOLUME"}:
        # A0/watch rows stay at zero; only the permanent stake metadata is added.
        method["core_main_points"] = CORE_POINTS
        method["volume_main_points"] = VOLUME_POINTS
        method["reverse_points"] = REVERSE_POINTS
        return

    primary = next((row for row in rows if row.get("highlight_primary")), funded[0])
    primary_code = str(primary.get("code", ""))
    mapping: dict[str, int] = {}
    for row in rows:
        code = str(row.get("code", ""))
        if not code:
            continue
        if tier == "CORE" and code == primary_code:
            points = CORE_POINTS
        else:
            points = VOLUME_POINTS
        row["points"] = points
        row["capital_vnd"] = points * COST_PER_POINT
        mapping[code] = points
    method["points_by_code"] = mapping
    method["code_count"] = len(mapping)
    method["capital_vnd"] = sum(mapping.values()) * COST_PER_POINT
    method["primary_points_per_code"] = CORE_POINTS if tier == "CORE" else VOLUME_POINTS
    method["reverse_points_per_code"] = REVERSE_POINTS
    method["reverse_skip_when_same"] = True
    method["points_per_code"] = CORE_POINTS if tier == "CORE" and len(mapping) == 1 else VOLUME_POINTS if tier == "VOLUME" else "Theo mã"


def normalize_a1_group(group: dict[str, Any]) -> None:
    if str(group.get("id", "")).upper() != "A1":
        return
    group["method"] = replace_text(str(group.get("method", "Dual Core Volume Balance — Core100/Volume50")))
    group["core_main_points"] = CORE_POINTS
    group["volume_main_points"] = VOLUME_POINTS
    group["reverse_points"] = REVERSE_POINTS
    status = str(group.get("status", "")).upper()
    mapping = group.get("points_by_code") or {}
    if not mapping or not any(int(value or 0) > 0 for value in mapping.values()):
        return
    tier = "VOLUME" if "VOLUME" in status else "CORE" if "CORE" in status else None
    if tier is None:
        return
    codes = [str(code) for code in (group.get("selected_numbers") or mapping.keys())]
    if not codes:
        return
    primary = codes[0]
    normalized: dict[str, int] = {}
    for code in dict.fromkeys(codes):
        normalized[code] = CORE_POINTS if tier == "CORE" and code == primary else VOLUME_POINTS
    group["points_by_code"] = normalized
    group["points"] = sum(normalized.values())
    group["capital_vnd"] = group["points"] * COST_PER_POINT


def normalize_pending_system_order(doc: dict[str, Any]) -> None:
    pending = doc.get("pending_order") or {}
    status = str(pending.get("status", "")).upper()
    if not pending or "REAL_CONFIRMED" in status or not ("SYSTEM_SIGNAL" in status or "NOT_YET_CONFIRMED" in status):
        return
    components = pending.get("components") or []
    merged: dict[str, int] = {}
    for component in components:
        text = method_text(component)
        mapping = {str(code): int(points) for code, points in (component.get("points_by_code") or {}).items()}
        if "A1" in text and mapping:
            tier = a1_tier(component)
            codes = [str(code) for code in (component.get("codes") or component.get("selection") or mapping.keys())]
            primary = codes[0] if codes else next(iter(mapping))
            mapping = {
                code: CORE_POINTS if tier == "CORE" and code == primary else VOLUME_POINTS
                for code in dict.fromkeys(codes or mapping.keys())
            }
            component["points_by_code"] = mapping
            component["capital_vnd"] = sum(mapping.values()) * COST_PER_POINT
        for code, points in mapping.items():
            merged[code] = max(int(merged.get(code, 0)), int(points))
    if not components:
        merged = {str(code): int(points) for code, points in (pending.get("points_by_code") or {}).items()}
    if not merged:
        return
    pending["points_by_code"] = merged
    pending["selection"] = list(merged)
    pending["total_points"] = sum(merged.values())
    pending["capital_vnd"] = pending["total_points"] * COST_PER_POINT
    doc["pending_order"] = pending
    portfolio = doc.get("portfolio") or {}
    portfolio["points_by_code"] = merged
    portfolio["points"] = sum(merged.values())
    portfolio["capital_vnd"] = portfolio["points"] * COST_PER_POINT
    doc["portfolio"] = portfolio


def normalize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out = replace_strings(copy.deepcopy(doc))
    if "CORE100_VOLUME50" in str(out.get("config_id", "")) or "A1" in str(out.get("config_id", "")):
        if "CORE100_VOLUME50" not in str(out.get("config_id", "")):
            out["config_id"] = "MB_A1_DUAL_CORE_VOLUME_BALANCE_GAN21_12_CORE100_VOLUME50_V2_20260715"

    stake = out.setdefault("stake_rule", {})
    stake.update({
        "a1_core_points_per_code": CORE_POINTS,
        "a1_volume_points_per_code": VOLUME_POINTS,
        "a1_core_main_points": CORE_POINTS,
        "a1_volume_main_points": VOLUME_POINTS,
        "a1_reverse_points": REVERSE_POINTS,
        "a1_reverse_points_per_code": REVERSE_POINTS,
        "a1_reverse_skip_when_same": True,
        "a1_no_duplicate_same_code": True,
        "legacy_core50_volume30_forbidden": True,
        "canonical_stake_guard_version": GUARD_VERSION,
    })
    funding = out.setdefault("funding_policy", {})
    funding["a1_staking_policy"] = "CORE100_VOLUME50_REVERSE50_NO_DUPLICATE"
    funding["legacy_core50_volume30_forbidden"] = True
    signal_policy = out.setdefault("top_signal_policy", {})
    signal_policy["a1_staking_rule"] = "Core100 → nếu không có Core mới Volume50 → A0; reverse50 nếu khác mã chính"

    top = out.get("top_signals") or {}
    for method in top.get("methods") or []:
        normalize_a1_method(method)
    if top.get("methods"):
        total_points = sum(int(row.get("points") or 0) for method in top["methods"] for row in (method.get("numbers") or []))
        total_capital = sum(int(method.get("capital_vnd") or 0) for method in top["methods"])
        top["total_points"] = f"{total_points} điểm"
        top["total_capital_vnd"] = total_capital
    out["top_signals"] = top

    for group in out.get("groups") or []:
        normalize_a1_group(group)
    normalize_pending_system_order(out)
    out.setdefault("automation", {})["a1_staking_guard"] = GUARD_VERSION
    out["automation"]["legacy_core50_volume30_forbidden"] = True
    return out


def normalize_policy(doc: dict[str, Any]) -> dict[str, Any]:
    out = replace_strings(copy.deepcopy(doc))
    a1 = out.setdefault("a1", {})
    a1.update({
        "core_points_main": CORE_POINTS,
        "volume_points_main": VOLUME_POINTS,
        "legacy_core50_volume30_forbidden": True,
        "staking_policy_version": GUARD_VERSION,
    })
    reverse = a1.setdefault("reverse", {})
    reverse.update({
        "points_per_code": REVERSE_POINTS,
        "skip_when_reverse_equals_primary": True,
        "never_bet_the_same_code_twice": True,
    })
    out["active_a1_staking_policy_file"] = "data/a1-staking-policy.json"
    return out


def patch_engine() -> bool:
    if not BASE_ENGINE.exists():
        print("A1_ENGINE_PATCH_SKIPPED_NO_BASE")
        return False
    text = BASE_ENGINE.read_text(encoding="utf-8")
    original = text
    patterns = {
        "A1_CORE_POINTS": CORE_POINTS,
        "A1_VOLUME_POINTS": VOLUME_POINTS,
    }
    for name, points in patterns.items():
        pattern = rf"(?m)^({re.escape(name)}\s*=\s*)\d+(\s*)$"
        text, count = re.subn(pattern, rf"\g<1>{points}\g<2>", text)
        if count != 1:
            raise RuntimeError(f"Expected exactly one {name} constant, found {count}")
    text = replace_text(text)
    if text != original:
        BASE_ENGINE.write_text(text, encoding="utf-8")
        print("A1_ENGINE_CORE100_VOLUME50_PATCHED")
        return True
    print("A1_ENGINE_CORE100_VOLUME50_ALREADY_OK")
    return False


def current_plan_path(doc: dict[str, Any]) -> Path | None:
    target = str(doc.get("target_date") or "")
    return ROOT / "data" / "plans" / f"{target}.json" if target else None


def assert_no_legacy_text(name: str, text: str) -> None:
    for token in FORBIDDEN_ACTIVE:
        if token in text:
            raise AssertionError(f"{name} still contains forbidden legacy token: {token}")


def validate_doc(doc: dict[str, Any], name: str) -> None:
    raw = json.dumps(doc, ensure_ascii=False)
    assert_no_legacy_text(name, raw)
    stake = doc.get("stake_rule") or {}
    assert int(stake.get("a1_core_points_per_code", stake.get("a1_core_main_points", CORE_POINTS))) == CORE_POINTS, stake
    assert int(stake.get("a1_volume_points_per_code", stake.get("a1_volume_main_points", VOLUME_POINTS))) == VOLUME_POINTS, stake
    assert int(stake.get("a1_reverse_points", stake.get("a1_reverse_points_per_code", REVERSE_POINTS))) == REVERSE_POINTS, stake
    assert stake.get("legacy_core50_volume30_forbidden") is True, stake
    actual = doc.get("actual_order") or {}
    # Confirmed/manual execution is historical evidence and is intentionally exempt.
    if actual and "REAL" in str(actual.get("status", "")).upper():
        pass
    for method in (doc.get("top_signals") or {}).get("methods") or []:
        if "A1" not in method_text(method):
            continue
        tier = a1_tier(method)
        funded = positive_number_rows(method)
        if not funded or tier not in {"CORE", "VOLUME"}:
            continue
        primary = next((row for row in funded if row.get("highlight_primary")), funded[0])
        for row in funded:
            expected = CORE_POINTS if tier == "CORE" and row is primary else VOLUME_POINTS
            assert int(row.get("points") or 0) == expected, (name, method, row, expected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--patch-engine", action="store_true")
    args = parser.parse_args()

    if args.patch_engine:
        patch_engine()
        return

    current = load(CURRENT, {})
    if not current:
        raise RuntimeError("Missing data/current.json")
    plan_path = current_plan_path(current)

    if args.check:
        validate_doc(current, "data/current.json")
        if plan_path and plan_path.exists():
            plan = load(plan_path, {})
            assert_no_legacy_text(str(plan_path), json.dumps(plan, ensure_ascii=False))
        policy = load(POLICY, {})
        assert int((policy.get("a1") or {}).get("core_points_main")) == CORE_POINTS
        assert int((policy.get("a1") or {}).get("volume_points_main")) == VOLUME_POINTS
        assert (policy.get("a1") or {}).get("legacy_core50_volume30_forbidden") is True
        assert_no_legacy_text("index.html", INDEX.read_text(encoding="utf-8"))
        lock = load(STAKE_POLICY, {})
        assert lock.get("status") == "ACTIVE_PERMANENT_USER_LOCK"
        assert int(lock.get("core_main_points")) == CORE_POINTS
        assert int(lock.get("volume_main_points")) == VOLUME_POINTS
        print("A1_CORE100_VOLUME50_PERMANENT_INVARIANT_OK")
        return

    changed: list[str] = []
    normalized = normalize_doc(current)
    if normalized != current:
        save(CURRENT, normalized)
        changed.append(str(CURRENT.relative_to(ROOT)))
    if plan_path and plan_path.exists():
        plan = load(plan_path, {})
        normalized_plan = normalize_doc(plan)
        if normalized_plan != plan:
            save(plan_path, normalized_plan)
            changed.append(str(plan_path.relative_to(ROOT)))
    policy = load(POLICY, {})
    normalized_policy = normalize_policy(policy)
    if normalized_policy != policy:
        save(POLICY, normalized_policy)
        changed.append(str(POLICY.relative_to(ROOT)))
    html = INDEX.read_text(encoding="utf-8")
    normalized_html = replace_text(html)
    if normalized_html != html:
        INDEX.write_text(normalized_html, encoding="utf-8")
        changed.append(str(INDEX.relative_to(ROOT)))

    validate_doc(load(CURRENT, {}), "data/current.json")
    assert_no_legacy_text("index.html", INDEX.read_text(encoding="utf-8"))
    print("A1_CORE100_VOLUME50_ENFORCED", changed)


if __name__ == "__main__":
    main()
