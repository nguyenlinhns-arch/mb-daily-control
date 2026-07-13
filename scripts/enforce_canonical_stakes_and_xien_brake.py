#!/usr/bin/env python3
"""Final canonical post-processor for current next-draw plans.

This guard runs after legacy recommendation workflows and enforces:
- A1 Core main=100; A1 Volume main=50.
- A1 reverse=50 only when reverse differs from main.
- Palindrome codes (00,11,...,99) are never funded twice.
- Cross-method duplicate codes use the highest stake once.
- Xiên recommendations are rebuilt through apply_xien2_auto_pairs.py, including
  the two-recent-lô-loss brake that moves Xiên to Shadow 0 VND.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CURRENT = DATA / "current.json"
OVERRIDE = DATA / "current-override.json"
LO_COST = 23_000

SPEC = importlib.util.spec_from_file_location("xien_auto", ROOT / "scripts" / "apply_xien2_auto_pairs.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load apply_xien2_auto_pairs.py")
xien_auto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(xien_auto)


def code2(value: Any) -> str | None:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    return text[-2:].zfill(2) if text else None


def a1_points(method_id: str, selection: list[str]) -> dict[str, int]:
    if not selection:
        return {}
    tier_core = "CORE" in method_id.upper()
    main_points = 100 if tier_core else 50
    main = code2(selection[0])
    if not main:
        return {}
    result = {main: main_points}
    reverse = main[::-1]
    if reverse != main:
        result[reverse] = 50
    return result


def normalize_components(doc: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    pending = doc.get("pending_order") or {}
    components = copy.deepcopy(pending.get("components") or [])
    if not components:
        # Reconstruct components from visible funded methods if needed.
        for method in (doc.get("top_signals") or {}).get("methods") or []:
            method_id = str(method.get("id") or "")
            if not any(token in method_id.upper() for token in ("A1", "X2", "X3", "ROLL7")):
                continue
            selection = [str(n.get("code")) for n in method.get("numbers") or [] if int(n.get("points") or 0) > 0]
            if selection:
                components.append({"method_id": method_id, "selection": selection, "points_by_code": method.get("points_by_code") or {str(n.get("code")): int(n.get("points") or 0) for n in method.get("numbers") or []}})

    aggregate: dict[str, int] = {}
    for component in components:
        method_id = str(component.get("method_id") or "")
        selection = [code for value in (component.get("selection") or []) if (code := code2(value))]
        if method_id.upper().startswith("A1"):
            points = a1_points(method_id, selection)
            component["selection"] = list(points)
            component["points_by_code"] = points
            component["capital_vnd"] = sum(points.values()) * LO_COST
        else:
            raw = component.get("points_by_code") or {}
            points = {}
            for key, value in raw.items():
                code = code2(key)
                try:
                    stake = int(value)
                except (TypeError, ValueError):
                    stake = 0
                if code and stake > 0:
                    points[code] = stake
            component["selection"] = list(points)
            component["points_by_code"] = points
            component["capital_vnd"] = sum(points.values()) * LO_COST
        for code, stake in points.items():
            aggregate[code] = max(aggregate.get(code, 0), stake)
    return components, aggregate


def patch_a1_cards(doc: dict[str, Any], aggregate: dict[str, int]) -> None:
    methods = (doc.get("top_signals") or {}).get("methods") or []
    for method in methods:
        method_id = str(method.get("id") or "")
        if "A1" not in method_id.upper():
            continue
        funded = [str(n.get("code")) for n in method.get("numbers") or [] if str(n.get("code") or "")]
        points = a1_points(method_id, funded)
        method["points_by_code"] = points
        method["points_per_code"] = next(iter(points.values()), 0) if len(set(points.values())) <= 1 else 0
        method["code_count"] = len(points)
        method["capital_vnd"] = sum(points.values()) * LO_COST
        method["primary_points_per_code"] = 100 if "CORE" in method_id.upper() else 50
        method["reverse_points_per_code"] = 50
        method["reverse_skip_when_same"] = True
        new_numbers = []
        for index, (code, stake) in enumerate(points.items()):
            role = "A1 main" if index == 0 else "A1 reverse50"
            if code == code[::-1]:
                role += " · tự đảo, chỉ cấp vốn một lần"
            new_numbers.append({"code": code, "points": stake, "capital_vnd": stake * LO_COST, "role": role, "visual_status": "PASS"})
        method["numbers"] = new_numbers

    for group in doc.get("groups") or []:
        if str(group.get("id") or "").upper() != "A1":
            continue
        selected = [code for value in (group.get("selected_numbers") or []) if (code := code2(value))]
        status_text = str(group.get("status") or "")
        method_id = "A1_CORE" if "CORE" in status_text.upper() else "A1_VOLUME"
        points = a1_points(method_id, selected)
        group["selected_numbers"] = list(points)
        group["points_by_code"] = points
        group["points"] = sum(points.values())
        group["capital_vnd"] = group["points"] * LO_COST


def patch(doc: dict[str, Any]) -> dict[str, Any]:
    pending = doc.get("pending_order")
    components, aggregate = normalize_components(doc)
    if isinstance(pending, dict):
        pending["components"] = components
        pending["selection"] = list(aggregate)
        pending["points_by_code"] = aggregate
        pending["total_points"] = sum(aggregate.values())
        pending["capital_vnd"] = pending["total_points"] * LO_COST
        pending["standard_capital_vnd"] = pending["capital_vnd"]

    portfolio = doc.setdefault("portfolio", {})
    portfolio["selection"] = " | ".join(aggregate)
    portfolio["points_by_code"] = aggregate
    portfolio["points"] = sum(aggregate.values())
    portfolio["capital_vnd"] = portfolio["points"] * LO_COST
    portfolio["standard_capital_vnd"] = portfolio["capital_vnd"]
    portfolio["title"] = " · ".join(f"{code} ×{stake}" for code, stake in aggregate.items()) if aggregate else "A0"

    patch_a1_cards(doc, aggregate)
    top = doc.setdefault("top_signals", {})
    top["total_points"] = f"{sum(aggregate.values())} điểm"
    top["total_capital_vnd"] = sum(aggregate.values()) * LO_COST
    top["total_numbers"] = f"{len(aggregate)} mã cấp vốn"
    top["subtitle"] = " · ".join(f"{code}×{stake}" for code, stake in aggregate.items()) if aggregate else "A0"

    stake = doc.setdefault("stake_rule", {})
    stake["a1_core_main_points"] = 100
    stake["a1_volume_main_points"] = 50
    stake["a1_reverse_points"] = 50
    stake["a1_reverse_skip_when_same"] = True
    stake["a1_no_duplicate_same_code"] = True
    stake["canonical_stake_guard_version"] = "A1_CORE100_VOLUME50_REVERSE50_NO_DUP_V2"

    # Rebuild Xiên after corrected lô stakes and apply the two-loss brake.
    doc = xien_auto.patch(doc)
    automation = doc.setdefault("automation", {})
    automation["canonical_stake_guard_complete"] = True
    automation["canonical_stake_guard_version"] = "A1_CORE100_VOLUME50_REVERSE50_NO_DUP_V2"
    return doc


def write_if_changed(path: Path, doc: dict[str, Any]) -> bool:
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def targets() -> list[Path]:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    paths = [CURRENT]
    if OVERRIDE.exists():
        paths.append(OVERRIDE)
    target = str(current.get("target_date") or "")[:10]
    plan = DATA / "plans" / f"{target}.json"
    if target and plan.exists():
        paths.append(plan)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = []
    for path in targets():
        doc = json.loads(path.read_text(encoding="utf-8"))
        expected = patch(copy.deepcopy(doc))
        if args.check:
            if doc != expected:
                raise SystemExit(f"Canonical stake guard stale: {path}")
        elif write_if_changed(path, expected):
            changed.append(str(path.relative_to(ROOT)))
    print("CANONICAL_STAKE_GUARD_CHANGED=" + ",".join(changed))


if __name__ == "__main__":
    main()
