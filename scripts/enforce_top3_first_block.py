#!/usr/bin/env python3
"""Khóa vĩnh viễn khối đầu website thành đúng 03 số xếp hạng trong ngày.

Nguyên tắc:
- Luôn lấy ứng viên từ A1, X3 và X2 của cùng payload đã rà soát.
- Xếp theo: lệnh controller đã đạt -> gate đạt -> WR tham chiếu phương pháp
  cao hơn -> ưu tiên phương pháp -> hạng nội bộ -> mã tăng dần.
- Luôn khử trùng mã. Nếu chưa đủ 3 mã đạt, điền các vị trí còn lại bằng
  Watch/Shadow mạnh nhất và ghi đúng trạng thái, điểm/vốn thật bằng 0.
- WR hiển thị là tỷ lệ tham chiếu của phương pháp, không phải xác suất riêng
  của từng mã và không phải cam kết kết quả.

Script idempotent, chạy sau pipeline chính và sau bộ bảo vệ số đảo A1.
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
CURRENT = ROOT / "data" / "current.json"
POLICY = ROOT / "data" / "automation-policy.json"
PLANS = ROOT / "data" / "plans"
REVIEW_LEDGER = ROOT / "data" / "review-ledger.json"
AUTOMATION_STATE = ROOT / "data" / "automation-state.json"
RULE_VERSION = "TOP3_GATE_WR_DAILY_V1"
DEFAULT_COST_PER_POINT = 23_000

DEFAULT_REFERENCES: dict[str, dict[str, Any]] = {
    "A1_CORE": {
        "rate": 0.4737,
        "label": "A1 Core backtest",
        "sample": "38 lệnh Core",
    },
    "A1_VOLUME": {
        "rate": 0.2556,
        "label": "A1 Volume backtest",
        "sample": "133 lệnh Volume",
    },
    "X3_GROWTH": {
        "rate": 0.6970,
        "label": "X3 Growth32-34 OOS",
        "sample": "99 lệnh OOS",
    },
    "X2_RESCUE": {
        "rate": 0.6571,
        "label": "X2 Rescue35",
        "sample": "35 lệnh Rescue",
    },
}

METHOD_PRIORITY = {"A1": 0, "X3": 1, "X2": 2}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def code2(value: Any) -> str | None:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not text:
        return None
    return text[-2:].zfill(2)


def pair_codes(value: Any) -> list[str]:
    raw = str(value or "")
    found = re.findall(r"(?<!\d)(\d{2})(?!\d)", raw)
    if found:
        return [x.zfill(2) for x in found[:2]]
    one = code2(value)
    return [one] if one else []


def pct(rate: float) -> str:
    return f"{rate * 100:.2f}".replace(".", ",") + "%"


def hash_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def find_group(doc: dict[str, Any], group_id: str) -> dict[str, Any] | None:
    wanted = group_id.upper()
    for group in doc.get("groups") or []:
        if str(group.get("id", "")).upper() == wanted:
            return group
    return None


def pass_text(value: Any) -> bool:
    text = str(value or "").upper()
    return "PASS" in text and "FAIL" not in text and "A0" not in text


def individual_pass_text(value: Any) -> bool:
    text = str(value or "").upper()
    return "PASS" in text and "FAIL" not in text


def benchmark(policy: dict[str, Any], key: str) -> dict[str, Any]:
    configured = (
        (policy.get("top_block") or {})
        .get("method_reference_win_rates", {})
        .get(key)
    )
    base = copy.deepcopy(DEFAULT_REFERENCES[key])
    if isinstance(configured, dict):
        base.update(configured)
    base["rate"] = float(base.get("rate") or 0.0)
    return base


def active_controller_method(doc: dict[str, Any]) -> str:
    decision = str((doc.get("portfolio") or {}).get("decision", "")).upper()
    if decision.startswith("A1_"):
        return "A1"
    if decision.startswith("X3"):
        return "X3"
    if decision.startswith("X2"):
        return "X2"
    return ""


def selected_codes_for_group(doc: dict[str, Any], group: dict[str, Any], method: str) -> set[str]:
    if active_controller_method(doc) != method:
        return set()
    result: set[str] = set()
    pending = doc.get("pending_order") or {}
    for value in pending.get("selection") or []:
        result.update(pair_codes(value))
    if result:
        return result
    for value in group.get("selected_numbers") or []:
        result.update(pair_codes(value))
    return result


def status_tier(controller_selected: bool, gate_pass: bool, individual_pass: bool) -> int:
    if controller_selected and gate_pass:
        return 3
    if gate_pass:
        return 2
    if individual_pass:
        return 1
    return 0


def display_status(tier: int, confirmed: bool) -> str:
    if tier == 3:
        return "ĐẠT · ĐÃ XÁC NHẬN" if confirmed else "ĐẠT · CHỜ XÁC NHẬN"
    if tier == 2:
        return "ĐẠT · SHADOW DO ƯU TIÊN"
    if tier == 1:
        return "GẦN ĐẠT · SHADOW"
    return "WATCH · CHƯA ĐẠT"


def method_label(method: str, subtype: str = "") -> str:
    if method == "A1":
        return "A1 Core" if subtype == "CORE" else "A1 Volume"
    if method == "X3":
        return "MB X3 Growth"
    return "MB X2 Rescue"


def reference_key(method: str, subtype: str = "") -> str:
    if method == "A1":
        return "A1_CORE" if subtype == "CORE" else "A1_VOLUME"
    if method == "X3":
        return "X3_GROWTH"
    return "X2_RESCUE"


def planned_points(doc: dict[str, Any], group: dict[str, Any], method: str, code: str) -> int:
    if active_controller_method(doc) != method:
        return 0
    stake = doc.get("stake_rule") or {}
    if method == "A1":
        points_map = group.get("points_by_code") or {}
        if code in points_map:
            return int(points_map[code] or 0)
        status = str(group.get("status", "")).upper()
        if "CORE" in status:
            return int(stake.get("a1_core_points_per_code") or 100)
        return int(stake.get("a1_volume_points_per_code") or 50)
    if method == "X3":
        return int(stake.get("x3_points_per_code") or 50)
    return int(stake.get("x2_points_per_code") or 15)


def add_candidate(
    pool: list[dict[str, Any]],
    *,
    doc: dict[str, Any],
    group: dict[str, Any],
    policy: dict[str, Any],
    method: str,
    subtype: str,
    code: str,
    method_rank: int,
    gate_pass: bool,
    individual_pass: bool,
    controller_selected: bool,
    reason: str,
    source_code: str,
) -> None:
    ref = benchmark(policy, reference_key(method, subtype))
    tier = status_tier(controller_selected, gate_pass, individual_pass)
    points = planned_points(doc, group, method, code) if controller_selected else 0
    cost = int((doc.get("stake_rule") or {}).get("lo_cost_per_point_vnd") or DEFAULT_COST_PER_POINT)
    actual = doc.get("actual_order") or {}
    confirmed = bool(actual.get("pnl_included")) and str(actual.get("date")) == str(doc.get("target_date"))
    pool.append(
        {
            "code": code,
            "method_id": method,
            "method_label": method_label(method, subtype),
            "method_subtype": subtype,
            "method_rank": int(method_rank),
            "method_priority": METHOD_PRIORITY[method],
            "gate_pass": bool(gate_pass),
            "individual_pass": bool(individual_pass),
            "controller_selected": bool(controller_selected),
            "status_tier": tier,
            "status": display_status(tier, confirmed),
            "reference_win_rate": ref["rate"],
            "reference_label": ref.get("label", ""),
            "reference_sample": ref.get("sample", ""),
            "reference_scope": "METHOD_NOT_CODE",
            "points": points,
            "capital_vnd": points * cost,
            "reason": reason,
            "source_candidate": source_code,
        }
    )


def build_pool(doc: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []

    a1 = find_group(doc, "A1")
    if a1:
        group_status = str(a1.get("status", "")).upper()
        subtype = "CORE" if "CORE" in group_status or "CORE" in str((doc.get("portfolio") or {}).get("decision", "")).upper() else "VOLUME"
        group_pass = pass_text(group_status)
        selected = selected_codes_for_group(doc, a1, "A1")
        candidates = a1.get("candidates") or []
        for index, candidate in enumerate(candidates, start=1):
            code = code2(candidate.get("code"))
            if not code:
                continue
            candidate_gate = bool(candidate.get("gate")) or pass_text(candidate.get("status"))
            add_candidate(
                pool,
                doc=doc,
                group=a1,
                policy=policy,
                method="A1",
                subtype=subtype,
                code=code,
                method_rank=int(candidate.get("rank") or index),
                gate_pass=group_pass and candidate_gate,
                individual_pass=candidate_gate,
                controller_selected=code in selected and group_pass,
                reason=str(candidate.get("reason") or a1.get("reason") or ""),
                source_code=str(candidate.get("code") or code),
            )
        # Bảo đảm mã đang chọn không bị thiếu khỏi pool dù candidate payload bị rút gọn.
        existing = {item["code"] for item in pool if item["method_id"] == "A1"}
        for offset, code in enumerate(sorted(selected), start=90):
            if code in existing:
                continue
            add_candidate(
                pool,
                doc=doc,
                group=a1,
                policy=policy,
                method="A1",
                subtype=subtype,
                code=code,
                method_rank=offset,
                gate_pass=group_pass,
                individual_pass=group_pass,
                controller_selected=True,
                reason=str(a1.get("reason") or "Mã A1 đang được controller chọn."),
                source_code=code,
            )

    x3 = find_group(doc, "X3")
    if x3:
        group_pass = pass_text(x3.get("status"))
        selected = selected_codes_for_group(doc, x3, "X3")
        for index, candidate in enumerate(x3.get("candidates") or [], start=1):
            code = code2(candidate.get("code"))
            if not code:
                continue
            candidate_gate = bool(candidate.get("gate")) or pass_text(candidate.get("status"))
            add_candidate(
                pool,
                doc=doc,
                group=x3,
                policy=policy,
                method="X3",
                subtype="GROWTH",
                code=code,
                method_rank=int(candidate.get("rank") or index),
                gate_pass=group_pass and (candidate_gate or code in selected),
                individual_pass=candidate_gate,
                controller_selected=code in selected and group_pass,
                reason=str(candidate.get("reason") or x3.get("reason") or ""),
                source_code=str(candidate.get("code") or code),
            )

    x2 = find_group(doc, "X2")
    if x2:
        group_pass = pass_text(x2.get("status"))
        selected = selected_codes_for_group(doc, x2, "X2")
        for index, candidate in enumerate(x2.get("candidates") or [], start=1):
            codes = pair_codes(candidate.get("code"))
            if not codes:
                continue
            candidate_gate = bool(candidate.get("gate")) or pass_text(candidate.get("status"))
            individual = individual_pass_text(candidate.get("status"))
            pair_rank = int(candidate.get("rank") or index)
            for leg_index, code in enumerate(codes, start=1):
                add_candidate(
                    pool,
                    doc=doc,
                    group=x2,
                    policy=policy,
                    method="X2",
                    subtype="RESCUE",
                    code=code,
                    method_rank=pair_rank * 10 + leg_index,
                    gate_pass=group_pass and candidate_gate,
                    individual_pass=individual,
                    controller_selected=code in selected and group_pass,
                    reason=f"{candidate.get('code')}: {candidate.get('reason') or x2.get('reason') or ''}",
                    source_code=str(candidate.get("code") or code),
                )

    return pool


def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -int(item["status_tier"]),
        -float(item["reference_win_rate"]),
        int(item["method_priority"]),
        int(item["method_rank"]),
        str(item["code"]),
    )


def top_three(doc: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in build_pool(doc, policy):
        code = item["code"]
        if code not in best or sort_key(item) < sort_key(best[code]):
            best[code] = item
    ranked = sorted(best.values(), key=sort_key)
    if len(ranked) < 3:
        raise RuntimeError(f"Không đủ 3 mã duy nhất trong pool A1/X3/X2: {len(ranked)}")
    result = copy.deepcopy(ranked[:3])
    for index, item in enumerate(result, start=1):
        item["rank"] = index
    return result


def ranking_payload(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "ACTIVE_PERMANENT",
        "rule_version": RULE_VERSION,
        "count": 3,
        "unique_codes": True,
        "ranking_order": [
            "CONTROLLER_SELECTED_AND_GATE_PASS_DESC",
            "GATE_PASS_DESC",
            "VALIDATED_METHOD_REFERENCE_WIN_RATE_DESC",
            "METHOD_PRIORITY_A1_X3_X2",
            "WITHIN_METHOD_RANK_ASC",
            "CODE_ASC",
        ],
        "codes": [item["code"] for item in ranked],
        "items": ranked,
        "disclaimer": "WR là tỷ lệ tham chiếu lịch sử của phương pháp, không phải xác suất riêng từng mã và không bảo đảm kết quả.",
        "fill_policy": "Thiếu mã đạt thì điền Watch/Shadow xếp hạng cao nhất, ghi đúng trạng thái và vốn thật 0đ.",
        "ranking_hash": hash_json(ranked),
    }


def top_signals_payload(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    total_points = sum(int(item.get("points") or 0) for item in ranked)
    total_capital = sum(int(item.get("capital_vnd") or 0) for item in ranked)
    passed_methods = len({item["method_id"] for item in ranked if item.get("gate_pass")})
    numbers = []
    for item in ranked:
        role = (
            f"#{item['rank']} · {item['status']} · {item['method_label']} · "
            f"WR tham chiếu {pct(float(item['reference_win_rate']))}"
        )
        numbers.append(
            {
                "code": item["code"],
                "points": int(item.get("points") or 0),
                "capital_vnd": int(item.get("capital_vnd") or 0),
                "role": role,
            }
        )
    return {
        "title": "TOP 3 XẾP HẠNG HÔM NAY",
        "subtitle": " · ".join(item["code"] for item in ranked),
        "total_methods": passed_methods,
        "total_numbers": "3 mã",
        "total_points": f"{total_points} điểm",
        "total_capital_vnd": total_capital,
        "note": (
            "Xếp hạng cố định: lệnh controller đã đạt → gate đạt → WR tham chiếu phương pháp "
            "cao hơn → ưu tiên phương pháp → hạng nội bộ → mã nhỏ. Chỉ mã có điểm lớn hơn 0 "
            "mới thuộc kế hoạch tiền thật chờ xác nhận; Shadow có vốn 0đ. WR không phải xác suất riêng của mã."
        ),
        "methods": [
            {
                "id": "TOP3_DAILY_RANKING",
                "label": "03 số ưu tiên",
                "method": "ĐẠT trước · WR tham chiếu cao nhất trong cùng tầng",
                "status": "RANKED_TOP3",
                "points_per_code": "Theo hệ",
                "code_count": 3,
                "capital_vnd": total_capital,
                "numbers": numbers,
            }
        ],
        "ranking_rule_version": RULE_VERSION,
    }


def apply_to_doc(doc: dict[str, Any], policy: dict[str, Any]) -> bool:
    before = copy.deepcopy(doc)
    ranked = top_three(doc, policy)
    existing_top = doc.get("top_signals") or {}
    if existing_top.get("ranking_rule_version") != RULE_VERSION:
        doc["qualified_signal_snapshot"] = copy.deepcopy(existing_top)
    doc["top_ranked_numbers"] = ranking_payload(ranked)
    doc["top_signals"] = top_signals_payload(ranked)
    doc.setdefault("top_signal_policy", {})["first_block_rule"] = RULE_VERSION
    doc["top_signal_policy"]["first_block_count"] = 3
    doc["top_signal_policy"]["first_block_unique_codes"] = True
    automation = doc.setdefault("automation", {})
    automation["top3_ranking_rule_version"] = RULE_VERSION
    automation["top3_ranking_complete"] = True
    automation["top3_codes"] = [item["code"] for item in ranked]
    automation["top3_ranking_hash"] = doc["top_ranked_numbers"]["ranking_hash"]
    validation = doc.setdefault("validation", {})
    validation["top3_first_block_complete"] = True
    validation["top3_unique_codes"] = True
    validation["top3_reference_scope"] = "METHOD_NOT_CODE"
    return doc != before


def sync_related_files(doc: dict[str, Any]) -> list[Path]:
    changed: list[Path] = []
    target = str(doc.get("target_date") or "")
    if target:
        plan_path = PLANS / f"{target}.json"
        if plan_path.exists():
            plan = load_json(plan_path, {})
            before = copy.deepcopy(plan)
            for key in (
                "qualified_signal_snapshot",
                "top_ranked_numbers",
                "top_signals",
                "top_signal_policy",
                "validation",
            ):
                if key in doc:
                    plan[key] = copy.deepcopy(doc[key])
            plan.setdefault("validation", {})["top3_first_block_complete"] = True
            if plan != before:
                dump_json(plan_path, plan)
                changed.append(plan_path)

    if REVIEW_LEDGER.exists() and target:
        ledger = load_json(REVIEW_LEDGER, {})
        before = copy.deepcopy(ledger)
        entry = (ledger.setdefault("plans", {})).setdefault(target, {})
        entry["top3_codes"] = list((doc.get("top_ranked_numbers") or {}).get("codes") or [])
        entry["top3_rule_version"] = RULE_VERSION
        entry["top3_complete"] = True
        entry["top3_ranking_hash"] = (doc.get("top_ranked_numbers") or {}).get("ranking_hash")
        if ledger != before:
            dump_json(REVIEW_LEDGER, ledger)
            changed.append(REVIEW_LEDGER)

    if AUTOMATION_STATE.exists():
        state = load_json(AUTOMATION_STATE, {})
        before = copy.deepcopy(state)
        state["top3_rule_version"] = RULE_VERSION
        state["top3_complete"] = True
        state["top3_codes"] = list((doc.get("top_ranked_numbers") or {}).get("codes") or [])
        state["top3_ranking_hash"] = (doc.get("top_ranked_numbers") or {}).get("ranking_hash")
        if state != before:
            dump_json(AUTOMATION_STATE, state)
            changed.append(AUTOMATION_STATE)
    return changed


def validate(doc: dict[str, Any], policy: dict[str, Any]) -> None:
    top = doc.get("top_ranked_numbers") or {}
    assert top.get("status") == "ACTIVE_PERMANENT", top
    assert top.get("rule_version") == RULE_VERSION, top
    codes = top.get("codes") or []
    assert len(codes) == 3, codes
    assert len(set(codes)) == 3, codes
    items = top.get("items") or []
    assert len(items) == 3, items
    for index, item in enumerate(items, start=1):
        assert item.get("rank") == index, item
        assert item.get("code") == codes[index - 1], item
        assert item.get("method_id") in {"A1", "X3", "X2"}, item
        assert item.get("status"), item
        assert item.get("reference_win_rate") is not None, item
        assert item.get("reference_scope") == "METHOD_NOT_CODE", item
    expected = [item["code"] for item in top_three(doc, policy)]
    assert codes == expected, (codes, expected)
    display = doc.get("top_signals") or {}
    assert display.get("ranking_rule_version") == RULE_VERSION, display
    methods = display.get("methods") or []
    assert len(methods) == 1 and methods[0].get("id") == "TOP3_DAILY_RANKING", methods
    rendered = [str(n.get("code")) for n in methods[0].get("numbers") or []]
    assert rendered == codes, (rendered, codes)
    assert (doc.get("automation") or {}).get("top3_ranking_complete") is True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    policy = load_json(POLICY, {})
    doc = load_json(CURRENT, {})
    if not doc:
        raise RuntimeError("Thiếu data/current.json")
    if args.check:
        validate(doc, policy)
        print("TOP3_FIRST_BLOCK_INVARIANT_OK", (doc.get("top_ranked_numbers") or {}).get("codes"))
        return
    changed = apply_to_doc(doc, policy)
    touched: list[Path] = []
    if changed:
        dump_json(CURRENT, doc)
        touched.append(CURRENT)
    touched.extend(sync_related_files(doc))
    validate(doc, policy)
    print(
        "TOP3_FIRST_BLOCK_ENFORCED",
        (doc.get("top_ranked_numbers") or {}).get("codes"),
        "changed=",
        [str(path.relative_to(ROOT)) for path in touched],
    )


if __name__ == "__main__":
    main()
