#!/usr/bin/env python3
"""Patch the materialized daily planner so A1 always publishes a Top-3 watchlist.

The canonical engine is packed in plan_next_day.py.zlib.b64 and materialized on every
workflow run. This patch is deliberately idempotent and runs immediately after that
materialization. It preserves the production gate/selection rules and only expands the
A1 candidate payload to three ranked primary codes, each with a recalculated earliest
eligible date.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "plan_next_day.py"
START = "def a1_candidates("
END = "\ndef build_x3("
MARKER = "A1_TOP3_WATCHLIST_V1"

REPLACEMENT = r'''def a1_candidates(
    features: dict[str, dict[str, Any]], repeat2_count: int, max_frequency: int, target_date: date
) -> dict[str, Any]:
    """Select the official A1 order and publish the three strongest primary-code watches.

    Ranking is deterministic and does not change the production decision:
    official selected code -> other raw-qualified code -> earliest conditional entry ->
    projected tier -> current Gan/Gmax/Score -> smaller code.  Reverse numbers are added
    later by the separate A1 reverse post-processor and are not independent watch codes.
    """
    rule_version = "A1_TOP3_WATCHLIST_V1"
    noise_blocked = repeat2_count >= 3 or max_frequency >= 3
    core = [
        f
        for f in features.values()
        if f["gan"] >= 21
        and 0.90 <= f["score"] <= 1.60
        and f["presence5"] == 0
        and f["maxfreq5"] < 2
    ]
    volume = [
        f
        for f in features.values()
        if f["gan"] >= 12
        and 0.70 <= f["score"] <= 1.80
        and f["presence5"] == 0
        and f["maxfreq5"] < 2
    ]
    core.sort(key=lambda f: (-f["gmax"], -f["score"], -f["gan"], f["code"]))
    volume.sort(key=lambda f: (-f["gan"], -f["gmax"], -f["score"], f["code"]))
    selected_core = core[0] if core and not noise_blocked else None
    selected_volume = volume[0] if volume and not noise_blocked and selected_core is None else None
    selected = selected_core or selected_volume
    core_codes = {f["code"] for f in core}
    volume_codes = {f["code"] for f in volume}

    def clear_after_misses(feature: dict[str, Any]) -> int:
        last5 = tuple(int(v) for v in feature.get("last5_counts", (0, 0, 0, 0, 0)))
        occupied = [idx + 1 for idx, value in enumerate(last5) if value > 0]
        return max(occupied, default=0)

    def miss_path_offset(feature: dict[str, Any], tier: str) -> int:
        gan = int(feature["gan"])
        gmax = int(feature["gmax"])
        if gmax <= 0:
            return 10_000
        low_ratio, high_ratio, minimum = (0.90, 1.60, 21) if tier == "CORE" else (0.70, 1.80, 12)
        required = max(minimum, math.ceil(low_ratio * gmax - 1e-12))
        upper = math.floor(high_ratio * gmax + 1e-12)
        clear = clear_after_misses(feature)
        offset = max(required - gan, clear, 0)
        if noise_blocked and offset == 0:
            offset = 1
        if gan + offset <= upper:
            return offset
        # If the current gap has already passed the upper score bound, the earliest
        # viable route is one hit followed by a clean miss run. This remains a lower
        # bound and is recalculated after every locked draw.
        reset_gmax = max(gmax, gan)
        reset_required = max(minimum, math.ceil(low_ratio * reset_gmax - 1e-12))
        reset_upper = math.floor(high_ratio * reset_gmax + 1e-12)
        if reset_required > reset_upper:
            return 10_000
        return 1 + max(reset_required, 5)

    tracking: list[dict[str, Any]] = []
    for feature in features.values():
        if int(feature.get("gmax") or 0) <= 0:
            continue
        core_offset = miss_path_offset(feature, "CORE")
        volume_offset = miss_path_offset(feature, "VOLUME")
        if core_offset <= volume_offset:
            projected_tier, projected_offset = "CORE", core_offset
        else:
            projected_tier, projected_offset = "VOLUME", volume_offset
        raw_core = feature["code"] in core_codes
        raw_volume = feature["code"] in volume_codes
        is_selected = selected is feature
        raw_qualified = raw_core or raw_volume
        tracking.append(
            {
                "feature": feature,
                "tier": "CORE" if raw_core else "VOLUME" if raw_volume else projected_tier,
                "offset": 0 if is_selected else projected_offset,
                "selected": is_selected,
                "raw_qualified": raw_qualified,
            }
        )

    def tracking_key(item: dict[str, Any]) -> tuple[Any, ...]:
        feature = item["feature"]
        tier = item["tier"]
        # After the official choice, current raw qualifiers remain ahead of future
        # watches. Conditional watches are then ranked by their earliest lower bound.
        return (
            0 if item["selected"] else 1,
            0 if item["raw_qualified"] else 1,
            int(item["offset"]),
            0 if tier == "CORE" else 1,
            -int(feature["gan"]),
            -int(feature["gmax"]),
            -float(feature["score"]),
            str(feature["code"]),
        )

    tracking.sort(key=tracking_key)
    top_tracking = tracking[:3]
    if len(top_tracking) != 3:
        raise RuntimeError(f"A1 Top3 watchlist không đủ 3 mã: {len(top_tracking)}")

    candidates: list[dict[str, Any]] = []
    for rank, item in enumerate(top_tracking, start=1):
        feature = item["feature"]
        tier = str(item["tier"])
        earliest, condition, milestone_type = earliest_a1_date(
            feature, tier, target_date, noise_blocked
        )
        gate = bool(item["selected"])
        # A second raw-qualified code cannot be another real order on the same day.
        if not gate and earliest <= target_date:
            earliest = target_date + timedelta(days=1)
            milestone_type = "CONDITIONAL_NEXT_REVIEW"
            condition = (
                f"{tier} đang đạt cá thể nhưng A1 chỉ chọn một mã tiền thật/ngày; "
                "mốc sớm nhất là lần rà lại sau kỳ khóa kế tiếp, khi thứ hạng và toàn bộ gate vẫn còn hợp lệ."
            )
        reason = (
            f"Gan {feature['gan']}; Gmax {feature['gmax']}; Score {feature['score']:.3f}; "
            f"Presence5 {feature['presence5']}; MaxFreq5 {feature['maxfreq5']}."
        )
        if noise_blocked:
            reason += f" Phanh nhiễu: repeat2={repeat2_count}, maxfreq={max_frequency}."
        if gate:
            status = "CORE PASS" if selected_core is feature else "VOLUME PASS"
        elif item["raw_qualified"]:
            status = f"{tier} SHADOW · THEO DÕI"
        else:
            status = f"{tier} WATCH"
        candidates.append(
            {
                "code": feature["code"],
                "rank": rank,
                "watch_rank": rank,
                "gate": gate,
                "status": status,
                "tracking_tier": tier,
                "tracking_rule_version": rule_version,
                "gan": feature["gan"],
                "gmax": feature["gmax"],
                "score": round(feature["score"], 6),
                "hot21": feature["hot21"],
                "reason": reason,
                "earliest_eligible_date": iso_day(earliest),
                "earliest_condition": condition,
                "milestone_type": milestone_type,
            }
        )
    return {
        "noise_blocked": noise_blocked,
        "core": selected_core,
        "volume": selected_volume,
        "candidates": candidates,
        "watchlist_rule_version": rule_version,
        "watchlist_codes": [item["code"] for item in candidates],
    }
'''


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    start = text.index(START)
    end = text.index(END, start)
    current = text[start:end]
    if MARKER in current and current.strip() == REPLACEMENT.strip():
        print("A1_TOP3_WATCHLIST_PATCH_ALREADY_APPLIED")
        return
    patched = text[:start] + REPLACEMENT.rstrip() + "\n" + text[end:]
    TARGET.write_text(patched, encoding="utf-8")
    print("A1_TOP3_WATCHLIST_PATCH_APPLIED")


if __name__ == "__main__":
    main()
