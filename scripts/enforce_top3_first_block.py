#!/usr/bin/env python3
"""Enforce the permanent first-block rule for MB Daily Control.

Rule:
1. If A1, X2 and X3 all have qualified selections, show every qualified
   selection in method order A1 -> X2 -> X3.
2. Otherwise show exactly three unique codes with the highest validated
   method-level reference win rate.

Only the controller-selected method carries real points/capital. Other
qualified, Watch or Shadow entries remain 0 points. Reference win rate is a
method benchmark, never a per-code probability or guarantee.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data/current.json"
POLICY = ROOT / "data/automation-policy.json"
PLANS = ROOT / "data/plans"
REVIEW_LEDGER = ROOT / "data/review-ledger.json"
AUTOMATION_STATE = ROOT / "data/automation-state.json"
RULE_VERSION = "FIRST_BLOCK_ALL_PASS_ELSE_TOP3_WR_V2"
METHOD_ORDER = ("A1", "X2", "X3")
METHOD_PRIORITY = {m: i for i, m in enumerate(METHOD_ORDER)}
COST_PER_POINT = 23_000
DEFAULT_WR = {
    "A1_CORE": {"rate": 0.4737, "label": "A1 Core backtest", "sample": "38 lệnh Core"},
    "A1_VOLUME": {"rate": 0.2556, "label": "A1 Volume backtest", "sample": "133 lệnh Volume"},
    "X2_RESCUE": {"rate": 0.6571, "label": "X2 Rescue35", "sample": "35 lệnh Rescue"},
    "X3_GROWTH": {"rate": 0.6970, "label": "X3 Growth32-34 OOS", "sample": "99 lệnh OOS"},
}


def load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else copy.deepcopy(default)


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def pass_text(value: Any) -> bool:
    text = str(value or "").upper()
    return "PASS" in text and "FAIL" not in text and "A0" not in text


def codes(value: Any) -> list[str]:
    found = re.findall(r"(?<!\d)(\d{2})(?!\d)", str(value or ""))
    if found:
        return [x.zfill(2) for x in found[:2]]
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return [digits[-2:].zfill(2)] if digits else []


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    return [v for v in values if v and not (v in seen or seen.add(v))]


def group(doc: dict[str, Any], method: str) -> dict[str, Any] | None:
    return next((g for g in doc.get("groups", []) if str(g.get("id", "")).upper() == method), None)


def active_method(doc: dict[str, Any]) -> str:
    decision = str((doc.get("portfolio") or {}).get("decision", "")).upper()
    return "A1" if decision.startswith("A1_") else "X2" if decision.startswith("X2") else "X3" if decision.startswith("X3") else ""


def subtype(doc: dict[str, Any], method: str, g: dict[str, Any]) -> str:
    if method != "A1":
        return "RESCUE" if method == "X2" else "GROWTH"
    text = f"{g.get('status', '')} {(doc.get('portfolio') or {}).get('decision', '')}".upper()
    return "CORE" if "CORE" in text else "VOLUME"


def ref_key(method: str, sub: str) -> str:
    return ("A1_CORE" if sub == "CORE" else "A1_VOLUME") if method == "A1" else "X2_RESCUE" if method == "X2" else "X3_GROWTH"


def reference(policy: dict[str, Any], method: str, sub: str) -> dict[str, Any]:
    key = ref_key(method, sub)
    result = copy.deepcopy(DEFAULT_WR[key])
    configured = ((policy.get("top_block") or {}).get("method_reference_win_rates") or {}).get(key)
    if isinstance(configured, dict):
        result.update(configured)
    result["rate"] = float(result.get("rate") or 0)
    return result


def label(method: str, sub: str) -> str:
    if method == "A1":
        return "A1 Core" if sub == "CORE" else "A1 Volume"
    return "MB X2 Rescue" if method == "X2" else "MB X3 Growth"


def selected_codes(doc: dict[str, Any], method: str, g: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if active_method(doc) == method:
        for value in (doc.get("pending_order") or {}).get("selection", []):
            out.extend(codes(value))
    if not out:
        for value in g.get("selected_numbers", []):
            out.extend(codes(value))
    return unique(out)


def points(doc: dict[str, Any], method: str, g: dict[str, Any], code: str) -> int:
    if active_method(doc) != method or code not in set(selected_codes(doc, method, g)):
        return 0
    stake = doc.get("stake_rule") or {}
    if method == "A1":
        mapping = g.get("points_by_code") or {}
        if code in mapping:
            return int(mapping[code] or 0)
        return int(stake.get("a1_core_points_per_code") or 100) if subtype(doc, method, g) == "CORE" else int(stake.get("a1_volume_points_per_code") or 50)
    return int(stake.get("x2_points_per_code") or 15) if method == "X2" else int(stake.get("x3_points_per_code") or 50)


def collect(doc: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    cost = int((doc.get("stake_rule") or {}).get("lo_cost_per_point_vnd") or COST_PER_POINT)
    for method in METHOD_ORDER:
        g = group(doc, method)
        if not g:
            continue
        sub = subtype(doc, method, g)
        ref = reference(policy, method, sub)
        gpass = pass_text(g.get("status"))
        selected = selected_codes(doc, method, g)
        selected_set = set(selected)
        seen: set[str] = set()
        for index, candidate in enumerate(g.get("candidates", []), 1):
            raw = candidate.get("code")
            candidate_codes = codes(raw)
            cpass = bool(candidate.get("gate")) or pass_text(candidate.get("status"))
            near = cpass or "NEAR" in str(candidate.get("status", "")).upper() or "GẦN" in str(candidate.get("status", "")).upper()
            for leg, code in enumerate(candidate_codes, 1):
                seen.add(code)
                gate = gpass and (cpass or (method in {"A1", "X3"} and code in selected_set))
                p = points(doc, method, g, code)
                controller = p > 0
                pool.append({
                    "code": code, "method_id": method, "method_label": label(method, sub),
                    "method_subtype": sub, "method_rank": int(candidate.get("rank") or index) * (10 if method == "X2" else 1) + (leg if method == "X2" else 0),
                    "method_priority": METHOD_PRIORITY[method], "gate_pass": gate,
                    "controller_selected": controller,
                    "status": "ĐẠT · CHỜ XÁC NHẬN" if controller and gate else "ĐẠT · SHADOW DO ƯU TIÊN" if gate else "GẦN ĐẠT · SHADOW" if near else "WATCH · CHƯA ĐẠT",
                    "reference_win_rate": ref["rate"], "reference_label": ref.get("label", ""), "reference_sample": ref.get("sample", ""),
                    "reference_scope": "METHOD_NOT_CODE", "points": p, "capital_vnd": p * cost,
                    "reason": str(candidate.get("reason") or g.get("reason") or ""), "source_candidate": str(raw or code),
                })
        for order, code in enumerate(selected, 1):
            if code in seen:
                continue
            p = points(doc, method, g, code)
            pool.append({
                "code": code, "method_id": method, "method_label": label(method, sub), "method_subtype": sub,
                "method_rank": 900 + order, "method_priority": METHOD_PRIORITY[method], "gate_pass": gpass,
                "controller_selected": p > 0,
                "status": "ĐẠT · CHỜ XÁC NHẬN" if p and gpass else "ĐẠT · SHADOW DO ƯU TIÊN" if gpass else "WATCH · CHƯA ĐẠT",
                "reference_win_rate": ref["rate"], "reference_label": ref.get("label", ""), "reference_sample": ref.get("sample", ""),
                "reference_scope": "METHOD_NOT_CODE", "points": p, "capital_vnd": p * cost,
                "reason": str(g.get("reason") or "Selection của phương pháp."), "source_candidate": code,
            })
        if method == "X2" and gpass and selected and not any(x["method_id"] == "X2" and x["gate_pass"] for x in pool):
            for order, code in enumerate(selected, 1):
                p = points(doc, method, g, code)
                pool.append({
                    "code": code, "method_id": method, "method_label": label(method, sub), "method_subtype": sub,
                    "method_rank": 950 + order, "method_priority": METHOD_PRIORITY[method], "gate_pass": True,
                    "controller_selected": p > 0, "status": "ĐẠT · CHỜ XÁC NHẬN" if p else "ĐẠT · SHADOW DO ƯU TIÊN",
                    "reference_win_rate": ref["rate"], "reference_label": ref.get("label", ""), "reference_sample": ref.get("sample", ""),
                    "reference_scope": "METHOD_NOT_CODE", "points": p, "capital_vnd": p * cost,
                    "reason": str(g.get("reason") or "Cặp X2 rank-1 đạt."), "source_candidate": code,
                })
    return pool


def best_per_method(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in items:
        key = (-int(item["gate_pass"]), -int(item["controller_selected"]), int(item["method_rank"]), item["code"])
        if item["code"] not in best:
            best[item["code"]] = item
        else:
            old = best[item["code"]]
            old_key = (-int(old["gate_pass"]), -int(old["controller_selected"]), int(old["method_rank"]), old["code"])
            if key < old_key:
                best[item["code"]] = item
    return sorted(best.values(), key=lambda x: (x["method_rank"], x["code"]))


def all_pass(pool: list[dict[str, Any]]) -> tuple[bool, dict[str, list[dict[str, Any]]]]:
    result = {m: best_per_method([x for x in pool if x["method_id"] == m and x["gate_pass"]]) for m in METHOD_ORDER}
    return all(result[m] for m in METHOD_ORDER), result


def wr_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (-float(item["reference_win_rate"]), -int(item["gate_pass"]), -int(item["controller_selected"]), item["method_priority"], item["method_rank"], item["code"])


def top3(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in pool:
        if item["code"] not in best or wr_key(item) < wr_key(best[item["code"]]):
            best[item["code"]] = item
    ranked = sorted(best.values(), key=wr_key)
    if len(ranked) < 3:
        raise RuntimeError(f"Không đủ 3 mã duy nhất trong pool: {len(ranked)}")
    ranked = copy.deepcopy(ranked[:3])
    for rank, item in enumerate(ranked, 1):
        item["rank"] = rank
    return ranked


def pct(rate: float) -> str:
    return f"{rate * 100:.2f}".replace(".", ",") + "%"


def number(item: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    return {"code": item["code"], "points": int(item["points"]), "capital_vnd": int(item["capital_vnd"]), "role": f"{prefix}{item['status']} · {item['method_label']} · WR tham chiếu {pct(float(item['reference_win_rate']))}"}


def build(doc: dict[str, Any], policy: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    pool = collect(doc, policy)
    every, per_method = all_pass(pool)
    if every:
        flat: list[dict[str, Any]] = []
        methods: list[dict[str, Any]] = []
        for method in METHOD_ORDER:
            items = copy.deepcopy(per_method[method])
            flat.extend(items)
            methods.append({
                "id": f"ALL_PASS_{method}", "label": {"A1": "MB A1", "X2": "MB X2", "X3": "MB X3"}[method],
                "method": "Toàn bộ số đạt · thứ tự A1 → X2 → X3", "status": "METHOD_PASS", "points_per_code": "Theo hệ",
                "code_count": len(items), "capital_vnd": sum(int(x["capital_vnd"]) for x in items), "numbers": [number(x) for x in items],
            })
        snapshot = {"status": "ACTIVE_PERMANENT", "rule_version": RULE_VERSION, "mode": "ALL_METHODS_PASS_SHOW_ALL", "method_order": list(METHOD_ORDER), "count": len(flat), "codes": [x["code"] for x in flat], "items": flat, "reference_scope": "METHOD_NOT_CODE", "hash": digest(flat)}
        display = {"title": "TẤT CẢ PHƯƠNG PHÁP ĐỀU CÓ SỐ ĐẠT", "subtitle": "A1 → X2 → X3 · HIỂN THỊ TOÀN BỘ", "total_methods": 3, "total_numbers": f"{len(flat)} mã hiển thị", "total_points": f"{sum(int(x['points']) for x in flat)} điểm", "total_capital_vnd": sum(int(x["capital_vnd"]) for x in flat), "note": "Cả A1, X2 và X3 đều có số đạt: hiển thị toàn bộ theo đúng thứ tự A1 → X2 → X3. Chỉ phương pháp được controller chọn có điểm/vốn; các phương pháp đạt còn lại là Shadow do ưu tiên.", "methods": methods, "first_block_rule_version": RULE_VERSION, "first_block_mode": snapshot["mode"]}
        return snapshot, display
    ranked = top3(pool)
    snapshot = {"status": "ACTIVE_PERMANENT", "rule_version": RULE_VERSION, "mode": "TOP3_HIGHEST_REFERENCE_WIN_RATE", "count": 3, "unique_codes": True, "codes": [x["code"] for x in ranked], "items": ranked, "ranking_order": ["REFERENCE_WIN_RATE_DESC", "GATE_PASS_DESC", "CONTROLLER_SELECTED_DESC", "METHOD_PRIORITY_A1_X2_X3", "WITHIN_METHOD_RANK_ASC", "CODE_ASC"], "reference_scope": "METHOD_NOT_CODE", "hash": digest(ranked)}
    display = {"title": "TOP 3 TỶ LỆ THẮNG CAO NHẤT", "subtitle": " · ".join(x["code"] for x in ranked), "total_methods": len({x["method_id"] for x in ranked}), "total_numbers": "3 mã", "total_points": f"{sum(int(x['points']) for x in ranked)} điểm", "total_capital_vnd": sum(int(x["capital_vnd"]) for x in ranked), "note": "Do chưa đồng thời có số đạt ở cả A1, X2 và X3, hệ thống so sánh candidate pool và chọn đúng 03 mã có WR tham chiếu phương pháp cao nhất. Gate/trạng thái được ghi rõ; Watch/Shadow luôn 0đ.", "methods": [{"id": "TOP3_HIGHEST_REFERENCE_WIN_RATE", "label": "03 số ưu tiên theo WR", "method": "WR tham chiếu cao nhất → gate → controller → A1/X2/X3 → hạng nội bộ", "status": "RANKED_TOP3_WR", "points_per_code": "Theo hệ", "code_count": 3, "capital_vnd": sum(int(x["capital_vnd"]) for x in ranked), "numbers": [number(x, f"#{i} · ") for i, x in enumerate(ranked, 1)]}], "first_block_rule_version": RULE_VERSION, "first_block_mode": snapshot["mode"]}
    return snapshot, display


def apply(doc: dict[str, Any], policy: dict[str, Any]) -> bool:
    before = copy.deepcopy(doc)
    snapshot, display = build(doc, policy)
    if (doc.get("top_signals") or {}).get("first_block_rule_version") != RULE_VERSION:
        doc["qualified_signal_snapshot"] = copy.deepcopy(doc.get("top_signals") or {})
    doc["first_block_snapshot"] = snapshot
    doc["top_ranked_numbers"] = copy.deepcopy(snapshot)
    doc["top_signals"] = display
    tsp = doc.setdefault("top_signal_policy", {})
    tsp.update({"first_block_rule": RULE_VERSION, "first_block_mode": snapshot["mode"], "all_pass_order": list(METHOD_ORDER), "fallback_count": 3, "fallback_primary_sort": "REFERENCE_WIN_RATE_DESC"})
    auto = doc.setdefault("automation", {})
    auto.update({"first_block_rule_version": RULE_VERSION, "first_block_mode": snapshot["mode"], "first_block_complete": True, "first_block_codes": snapshot["codes"], "first_block_hash": snapshot["hash"]})
    doc.setdefault("validation", {}).update({"first_block_complete": True, "first_block_mode": snapshot["mode"], "first_block_reference_scope": "METHOD_NOT_CODE"})
    return doc != before


def sync(doc: dict[str, Any]) -> list[Path]:
    changed: list[Path] = []
    target = str(doc.get("target_date") or "")
    if target and (PLANS / f"{target}.json").exists():
        path = PLANS / f"{target}.json"
        plan = load(path, {})
        before = copy.deepcopy(plan)
        for key in ("qualified_signal_snapshot", "first_block_snapshot", "top_ranked_numbers", "top_signals", "top_signal_policy", "validation"):
            if key in doc:
                plan[key] = copy.deepcopy(doc[key])
        if plan != before:
            save(path, plan); changed.append(path)
    snapshot = doc.get("first_block_snapshot") or {}
    if target and REVIEW_LEDGER.exists():
        ledger = load(REVIEW_LEDGER, {})
        before = copy.deepcopy(ledger)
        ledger.setdefault("plans", {}).setdefault(target, {}).update({"first_block_codes": snapshot.get("codes", []), "first_block_rule_version": RULE_VERSION, "first_block_mode": snapshot.get("mode"), "first_block_complete": True, "first_block_hash": snapshot.get("hash")})
        if ledger != before:
            save(REVIEW_LEDGER, ledger); changed.append(REVIEW_LEDGER)
    if AUTOMATION_STATE.exists():
        state = load(AUTOMATION_STATE, {})
        before = copy.deepcopy(state)
        state.update({"first_block_codes": snapshot.get("codes", []), "first_block_rule_version": RULE_VERSION, "first_block_mode": snapshot.get("mode"), "first_block_complete": True, "first_block_hash": snapshot.get("hash")})
        if state != before:
            save(AUTOMATION_STATE, state); changed.append(AUTOMATION_STATE)
    return changed


def validate(doc: dict[str, Any], policy: dict[str, Any]) -> None:
    expected, expected_display = build(doc, policy)
    actual = doc.get("first_block_snapshot") or {}
    assert actual.get("rule_version") == RULE_VERSION, actual
    assert actual.get("mode") == expected.get("mode"), (actual, expected)
    assert actual.get("codes") == expected.get("codes"), (actual, expected)
    display = doc.get("top_signals") or {}
    assert display.get("first_block_rule_version") == RULE_VERSION, display
    assert display.get("subtitle") == expected_display.get("subtitle"), (display, expected_display)
    if actual["mode"] == "ALL_METHODS_PASS_SHOW_ALL":
        assert [m.get("id") for m in display.get("methods", [])] == ["ALL_PASS_A1", "ALL_PASS_X2", "ALL_PASS_X3"], display
    else:
        assert len(actual.get("codes", [])) == 3 == len(set(actual.get("codes", []))), actual
        assert (display.get("methods") or [{}])[0].get("id") == "TOP3_HIGHEST_REFERENCE_WIN_RATE", display
    assert (doc.get("automation") or {}).get("first_block_complete") is True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    policy = load(POLICY, {})
    doc = load(CURRENT, {})
    if not doc:
        raise RuntimeError("Thiếu data/current.json")
    if args.check:
        validate(doc, policy)
        print("FIRST_BLOCK_POLICY_INVARIANT_OK", (doc.get("first_block_snapshot") or {}).get("mode"), (doc.get("first_block_snapshot") or {}).get("codes"))
        return
    changed = apply(doc, policy)
    touched: list[Path] = []
    if changed:
        save(CURRENT, doc); touched.append(CURRENT)
    touched.extend(sync(doc))
    validate(doc, policy)
    print("FIRST_BLOCK_POLICY_ENFORCED", (doc.get("first_block_snapshot") or {}).get("mode"), (doc.get("first_block_snapshot") or {}).get("codes"), "changed=", [str(path.relative_to(ROOT)) for path in touched])


if __name__ == "__main__":
    main()
