from __future__ import annotations

from collections import defaultdict
from typing import Any

from .io_utils import parse_pick_text

GOVERNANCE_ID = "MB_TOP2PLUS_GOVERNANCE_OVERLAY_V1"


def _is_cold(state: str) -> bool:
    return "COLD" in (state or "").upper()


def _is_hot(state: str) -> bool:
    return "HOT" in (state or "").upper()


def build_governance(summary: dict[str, Any], method_rows: list[dict[str, str]]) -> dict[str, Any]:
    """Apply the frozen TOP2 + third-number governance overlay.

    This overlay intentionally does not alter the raw FUSION67 ranking.  The
    current v1 base is the first two raw ranks because no separately frozen
    FUSION67 K0/K1 threshold exists in the imported engine.  K0/K1 activation
    therefore remains explicitly unavailable rather than invented.
    """
    raw_pick = [str(x).zfill(2) for x in summary["final_pick"]]
    if len(raw_pick) != 3:
        raise ValueError("raw FUSION67 output must contain exactly 3 numbers")
    top2 = raw_pick[:2]
    third = raw_pick[2]

    supporters: list[dict[str, Any]] = []
    cold_families: set[str] = set()
    for row in method_rows:
        picks = parse_pick_text(row.get("pick", ""))
        if third not in picks:
            continue
        fam = row.get("family", row.get("method", ""))
        state = row.get("state", "NEUTRAL")
        native_k = int(row.get("native_k", "0") or 0)
        pl7 = int(float(row.get("PL7", "0") or 0))
        status = row.get("status", "")
        if _is_cold(state):
            cold_families.add(fam)
        qualifies = status == "SUCCESS" and native_k == 1 and not _is_cold(state) and pl7 > 0
        supporters.append({
            "method": row.get("method", ""),
            "family": fam,
            "state": state,
            "native_k": native_k,
            "pl7_vnd": pl7,
            "qualifies_k1": qualifies,
        })

    qualifying_by_family: dict[str, list[str]] = defaultdict(list)
    for item in supporters:
        if item["qualifies_k1"]:
            qualifying_by_family[item["family"]].append(item["method"])

    independent_qualifying_families = sorted(qualifying_by_family)
    candidate_non_cold = len(cold_families) == 0
    gate_pass = candidate_non_cold and len(independent_qualifying_families) >= 2
    final_pick = top2 + ([third] if gate_pass else [])
    return {
        "governance_id": GOVERNANCE_ID,
        "raw_policy_id": summary.get("policy_id", "ALL67_NO_META"),
        "raw_rank_top3": raw_pick,
        "base_policy": "RAW_RANK_1_2",
        "base_k": 2,
        "base_pick": top2,
        "dynamic_k0_k1_status": "RESERVED_NOT_ENABLED_NO_FROZEN_FUSION67_THRESHOLD",
        "third_candidate": third,
        "third_gate": {
            "status": "PASS" if gate_pass else "FAIL",
            "candidate_non_cold": candidate_non_cold,
            "cold_families": sorted(cold_families),
            "supporters": supporters,
            "qualifying_independent_families": independent_qualifying_families,
            "qualifying_family_count": len(independent_qualifying_families),
            "required_family_count": 2,
        },
        "final_pick": final_pick,
        "k": len(final_pick),
        "points_per_number": 10,
        "stake_vnd": len(final_pick) * 10 * 27_000,
        "note": "Raw FUSION67 ranking is preserved; overlay cannot rewrite a prior PRE_DRAW_FROZEN pick.",
    }
