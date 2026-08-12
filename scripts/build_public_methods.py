#!/usr/bin/env python3
"""Build the public, non-canonical method recommendations for one target day.

The input is a JSON array of history rows.  Each row is either
``[YYYY-MM-DD, L01, ..., L27]`` or ``{"date": ..., "codes": [...]}``.
Only the locked history through target date minus one is accepted.  The paid
4SO conclusion is deliberately outside this payload and must never be added.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


VN = timezone(timedelta(hours=7))
SCHEMA = "MB_PUBLIC_METHOD_OUTPUTS_V2_TODAY_ONLY"


def code2(value: Any) -> str:
    text = "".join(character for character in str(value or "") if character.isdigit())
    if not text:
        raise ValueError(f"Mã rỗng hoặc không hợp lệ: {value!r}")
    code = text[-2:].zfill(2)
    if not ("00" <= code <= "99"):
        raise ValueError(f"Mã ngoài 00-99: {value!r}")
    return code


def parse_rows(payload: Any) -> list[tuple[date, list[str]]]:
    if isinstance(payload, dict):
        payload = payload.get("values", payload.get("rows", payload.get("history")))
    if not isinstance(payload, list):
        raise ValueError("History JSON phải là một mảng hàng")

    by_date: dict[date, list[str]] = {}
    for raw in payload:
        if isinstance(raw, dict):
            raw_date, raw_codes = raw.get("date"), raw.get("codes")
        elif isinstance(raw, list) and len(raw) >= 28:
            raw_date, raw_codes = raw[0], raw[1:28]
        else:
            continue
        try:
            draw_date = date.fromisoformat(str(raw_date))
        except ValueError:
            continue
        if not isinstance(raw_codes, list) or len(raw_codes) != 27:
            raise ValueError(f"{draw_date}: cần đúng 27 mã")
        codes = [code2(value) for value in raw_codes]
        if draw_date in by_date and by_date[draw_date] != codes:
            raise ValueError(f"{draw_date}: có hai bộ 27 mã khác nhau")
        by_date[draw_date] = codes
    history = sorted(by_date.items())
    if len(history) < 181:
        raise ValueError(f"Lịch sử quá ngắn: {len(history)} ngày; cần tối thiểu 181")
    return history


def day_count(counters: list[Counter[str]], code: str, window: int) -> int:
    return sum(1 for counter in counters[-window:] if counter.get(code, 0) > 0)


def occurrence_count(counters: list[Counter[str]], code: str, window: int) -> int:
    return sum(counter.get(code, 0) for counter in counters[-window:])


def build_features(history: list[tuple[date, list[str]]]) -> dict[str, dict[str, Any]]:
    counters = [Counter(codes) for _, codes in history]
    length = len(history)
    features: dict[str, dict[str, Any]] = {}
    for number in range(100):
        code = f"{number:02d}"
        positions = [index for index, counter in enumerate(counters) if counter.get(code, 0)]
        if positions:
            gan = length - 1 - positions[-1]
            gaps = [positions[index] - positions[index - 1] - 1 for index in range(1, len(positions))]
            gmax = max(gaps, default=0)
        else:
            gan, gmax = length, 0
        last5 = tuple(counter.get(code, 0) for counter in counters[-5:])
        hot21 = occurrence_count(counters, code, 21)
        feature = {
            "code": code,
            "gan": gan,
            "gmax": gmax,
            "score": gan / gmax if gmax else 0.0,
            "last5": last5,
            "presence5": sum(1 for value in last5 if value > 0),
            "maxfreq5": max(last5, default=0),
            "hot21": hot21,
            "h5": day_count(counters, code, 5),
            "h21": day_count(counters, code, 21),
            "h60": day_count(counters, code, 60),
            "h90": day_count(counters, code, 90),
            "occ60": occurrence_count(counters, code, 60),
            "in_latest": counters[-1].get(code, 0) > 0,
        }
        feature["x3_score"] = hot21 + 2 * math.sqrt(min(gan, 30))
        features[code] = feature
    return features


def a1_entry_offset(feature: dict[str, Any], tier: str, noise_blocked: bool) -> int:
    gan, gmax = int(feature["gan"]), int(feature["gmax"])
    if gmax <= 0:
        return 10_000
    low, high, minimum = (0.90, 1.60, 21) if tier == "CORE" else (0.70, 1.80, 12)
    required = max(minimum, math.ceil(low * gmax - 1e-12))
    upper = math.floor(high * gmax + 1e-12)
    occupied = [index + 1 for index, value in enumerate(feature["last5"]) if value > 0]
    offset = max(required - gan, max(occupied, default=0), 0)
    if noise_blocked and offset == 0:
        offset = 1
    if gan + offset <= upper:
        return offset
    reset_gmax = max(gmax, gan)
    reset_required = max(minimum, math.ceil(low * reset_gmax - 1e-12))
    reset_upper = math.floor(high * reset_gmax + 1e-12)
    return 10_000 if reset_required > reset_upper else 1 + max(reset_required, 5)


def a1_numbers(features: dict[str, dict[str, Any]], latest: list[str]) -> list[str]:
    latest_counts = Counter(latest)
    noise_blocked = sum(1 for value in latest_counts.values() if value >= 2) >= 3 or max(latest_counts.values()) >= 3
    core = {
        code for code, feature in features.items()
        if feature["gan"] >= 21 and 0.90 <= feature["score"] <= 1.60
        and feature["presence5"] == 0 and feature["maxfreq5"] < 2
    }
    volume = {
        code for code, feature in features.items()
        if feature["gan"] >= 12 and 0.70 <= feature["score"] <= 1.80
        and feature["presence5"] == 0 and feature["maxfreq5"] < 2
    }
    core_rank = sorted((features[code] for code in core), key=lambda item: (-item["gmax"], -item["score"], -item["gan"], item["code"]))
    volume_rank = sorted((features[code] for code in volume), key=lambda item: (-item["gan"], -item["gmax"], -item["score"], item["code"]))
    selected = None if noise_blocked else (core_rank[0] if core_rank else volume_rank[0] if volume_rank else None)
    tracking = []
    for feature in features.values():
        if feature["gmax"] <= 0:
            continue
        core_offset = a1_entry_offset(feature, "CORE", noise_blocked)
        volume_offset = a1_entry_offset(feature, "VOLUME", noise_blocked)
        projected_tier = "CORE" if core_offset <= volume_offset else "VOLUME"
        raw_core, raw_volume = feature["code"] in core, feature["code"] in volume
        tier = "CORE" if raw_core else "VOLUME" if raw_volume else projected_tier
        tracking.append({
            "feature": feature,
            "tier": tier,
            "offset": 0 if feature is selected else min(core_offset, volume_offset),
            "selected": feature is selected,
            "qualified": raw_core or raw_volume,
        })
    tracking.sort(key=lambda item: (
        0 if item["selected"] else 1,
        0 if item["qualified"] else 1,
        item["offset"],
        0 if item["tier"] == "CORE" else 1,
        -item["feature"]["gan"], -item["feature"]["gmax"],
        -item["feature"]["score"], item["feature"]["code"],
    ))
    return [item["feature"]["code"] for item in tracking[:4]]


def inverse_pairs() -> Iterable[tuple[str, str]]:
    for number in range(100):
        code = f"{number:02d}"
        reverse = code[::-1]
        if code == reverse or int(code) < int(reverse):
            continue
        yield code, reverse


def x2_numbers(features: dict[str, dict[str, Any]]) -> list[str]:
    rows = []
    for main, cover in inverse_pairs():
        left, right = features[main], features[cover]
        primary = min(left["h60"], right["h60"]) / 60 + min(left["h90"], right["h90"]) / 90
        secondary = (left["h60"] + right["h60"]) / 60 + (left["h90"] + right["h90"]) / 90
        rank_score = primary + secondary / 1000 + min(left["h21"], right["h21"]) / 100000
        rows.append((rank_score, f"{main}-{cover}", main, cover))
    _, _, main, cover = sorted(rows, key=lambda item: (-item[0], item[1]))[0]
    return [main, cover]


def x3_numbers(features: dict[str, dict[str, Any]]) -> list[str]:
    eligible = [feature for feature in features.values() if not feature["in_latest"]]
    eligible.sort(key=lambda item: (-item["x3_score"], -item["hot21"], -item["gan"], item["code"]))
    return [feature["code"] for feature in eligible[:3]]


def frequency60_numbers(features: dict[str, dict[str, Any]]) -> list[str]:
    ranked = sorted(features.values(), key=lambda item: (-item["h60"], item["code"]))
    return [feature["code"] for feature in ranked[:7]]


def transition180_numbers(history: list[tuple[date, list[str]]]) -> list[str]:
    latest_codes = sorted(set(history[-1][1]))
    transitions = history[max(0, len(history) - 181):-1]
    scores = {f"{number:02d}": 0.0 for number in range(100)}
    for source in latest_codes:
        matches = []
        start = len(history) - 1 - len(transitions)
        for offset, (_, codes) in enumerate(transitions):
            if source in set(codes):
                matches.append(set(history[start + offset + 1][1]))
        if not matches:
            continue
        denominator = len(matches)
        for candidate in scores:
            scores[candidate] += sum(candidate in following for following in matches) / denominator
    ranked = sorted(scores, key=lambda code: (-scores[code], code))
    return ranked[:7]


def double_numbers(features: dict[str, dict[str, Any]]) -> list[str]:
    doubles = [features[f"{digit}{digit}"] for digit in range(10)]
    primary = sorted(doubles, key=lambda item: (-item["score"], -item["gan"], -item["h60"], item["code"]))[0]
    frequency = sorted((item for item in doubles if item is not primary), key=lambda item: (-item["h60"], -item["occ60"], item["code"]))
    return [primary["code"], frequency[0]["code"], frequency[1]["code"]]


def snapshot_hash(history: list[tuple[date, list[str]]]) -> str:
    payload = [[draw_date.isoformat(), *codes] for draw_date, codes in history]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_payload(history: list[tuple[date, list[str]]], target_date: date) -> dict[str, Any]:
    data_lock = target_date - timedelta(days=1)
    locked = [(draw_date, codes) for draw_date, codes in history if draw_date <= data_lock]
    if not locked or locked[-1][0] != data_lock:
        raise ValueError(f"WAIT_RESULT_DATA: nguồn chưa kết thúc đúng {data_lock}")
    if history[-1][0] != data_lock:
        raise ValueError(f"NO_LOOK_AHEAD: nguồn có ngày sau data lock {data_lock}")
    if len(locked[-1][1]) != 27:
        raise ValueError("WAIT_RESULT_DATA: dòng khóa không đủ 27/27")
    features = build_features(locked)
    methods = [
        {"id": "A1", "name": "A1", "numbers": a1_numbers(features, locked[-1][1])},
        {"id": "X2_RBK", "name": "2SO / X2", "numbers": x2_numbers(features)},
        {"id": "X3_GROWTH", "name": "X3 GROWTH", "numbers": x3_numbers(features)},
        {"id": "F01_FREQUENCY60", "name": "F01 TẦN SUẤT", "numbers": frequency60_numbers(features)},
        {"id": "F06_TRANSITION180", "name": "F06 CHUYỂN TIẾP", "numbers": transition180_numbers(locked)},
        {"id": "MB_KEP_V1", "name": "KÉP V1", "numbers": double_numbers(features)},
    ]
    return {
        "schema_version": SCHEMA,
        "recommendation_scope": "TODAY_ONLY",
        "target_date": target_date.isoformat(),
        "data_lock": data_lock.isoformat(),
        "generated_at": datetime.now(VN).isoformat(timespec="seconds"),
        "source_status": "LOCKED_27_OF_27",
        "source_row_count": len(locked),
        "source_sha256": snapshot_hash(locked),
        "outcome_known_at_selection": False,
        "methods": methods,
    }


def self_test() -> None:
    start = date(2025, 1, 1)
    history = []
    for offset in range(220):
        codes = [f"{(offset * 7 + index * 13) % 100:02d}" for index in range(27)]
        history.append((start + timedelta(days=offset), codes))
    payload = build_payload(history, history[-1][0] + timedelta(days=1))
    assert payload["recommendation_scope"] == "TODAY_ONLY"
    assert payload["data_lock"] == history[-1][0].isoformat()
    assert len(payload["methods"]) == 6
    assert all(method["numbers"] and all(len(code) == 2 for code in method["numbers"]) for method in payload["methods"])
    assert not ({"final_codes", "final_pairs", "canonical_codes", "canonical_pairs"} & payload.keys())
    print("PUBLIC_METHODS_TODAY_ONLY_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-json", type=Path)
    parser.add_argument("--target-date")
    parser.add_argument("--output", type=Path, default=Path("ai-methods/public-methods.json"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.history_json or not args.target_date:
        parser.error("--history-json và --target-date là bắt buộc")
    history = parse_rows(json.loads(args.history_json.read_text(encoding="utf-8")))
    payload = build_payload(history, date.fromisoformat(args.target_date))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"target_date": payload["target_date"], "data_lock": payload["data_lock"], "methods": len(payload["methods"]), "source_sha256": payload["source_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
