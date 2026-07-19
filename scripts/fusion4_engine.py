#!/usr/bin/env python3
"""Generate the next MB FUSION4–180 plan from a t-1 source workbook.

The private V32 engine supplies the locked Max4/Max10 source features.  This
public wrapper only applies the frozen Fusion4 ranking and stake policy.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine_v32"
START = date(2024, 1, 1)
COST_PER_POINT = 23_000
CONFIG_ID = "MB_FUSION4_180_PROD_V1_20260719"

STATIC_VOTER_PATHS = (
    "base", "rows", "rows_v10", "v11_path.rows", "rows_v11",
    "v15_base100", "v15_model.rows_a_mixed", "v15_model.rows_b_mixed",
    "v15_model.rows_a100", "v15_model.rows_model_mixed",
    "v15_model.rows_model100", "v15_port841.eq_bal.rows",
    "v15_port841.ridge.rows", "v15_port841.rows_mixed",
    "v15_port841.rows100", "v15_rows_joint", "rows_v15",
    "v16_port842.eq_win.rows", "v16_port842.rows_mixed",
    "v16_port842.rows100", "v16_s1_rows", "v16_rows_win849", "rows_v16",
    "v17_base_rows", "v17_base.rows", "v17_v16.rows", "v17_l854.rows",
    "v17_l854.left.rows", "v17_l854.left.left.rows",
    "v17_l854.left.left.left.rows", "v17_l854.left.left.right.rows",
    "v17_l854.left.left.right.left.rows",
    "v17_l854.left.left.right.right.rows", "v17_l854.left.right.rows",
    "v17_l854.left.right.right.rows", "v17_l854.right.rows",
    "v17_l854.right.left.rows", "v17_l854.right.left.left.rows",
    "v17_l854.right.left.left.left.rows", "v17_profit857.rows",
    "v17_profit857.right.rows", "v17_maxwin862.rows",
    "v17_maxwin862.right.rows", "v17_c864.rows", "v17_p865.rows",
    "v17_p865.right.rows", "v17_e867.rows", "v17_e867.right.rows",
    "v17_official.rows", "v17_official.right.rows", "rows_v17",
    "V11.PATHS.EQ4_WIN240", "V11.PATHS.EQ4_BAL240",
    "V11.PATHS.EQ4_BAL180", "V11.PATHS.RIDGE_WIN",
    "V11.PATHS.EQ4_PNL30", "V11.PATHS.TREE3_PNL30",
    "V13.WIN_A.inner", "V13.WIN_A.outer", "V13.WIN_B.inner",
    "V13.WIN_B.outer", "V13.WIN_C.inner", "V13.WIN_C.outer",
    "V13.WIN_D.inner", "V13.WIN_D.outer", "V13.PROFIT_A.inner",
    "V13.PROFIT_A.outer", "V15.MODEL_DIRECT_A", "V15.MODEL_DIRECT_B",
    "V17.PORT840", "V12.rows_v12(selection_alias)",
)
STATIC_MANIFEST_SHA256 = sha256(
    json.dumps(STATIC_VOTER_PATHS, separators=(",", ":")).encode()
).hexdigest()


class FusionEngineError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical(value)).hexdigest()


def zrow(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    mean = values.mean(axis=1, keepdims=True)
    std = values.std(axis=1, keepdims=True)
    std[std == 0] = 1.0
    return ((values - mean) / std).astype(np.float32)


def rank01(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values)
    n, p = values.shape
    codes = np.arange(p)
    out = np.empty((n, p), np.float32)
    for i, row in enumerate(values):
        order = np.lexsort((codes, -row))
        ranks = np.empty(p, np.int16)
        ranks[order] = np.arange(p)
        out[i] = 1.0 - ranks / (p - 1)
    return out


def walkforward_models(
    days: np.ndarray,
    x: np.ndarray,
    y_count: np.ndarray,
    y_presence: np.ndarray,
) -> tuple[dict[str, np.ndarray], list[list[Any]]]:
    days = np.asarray(days).astype(str)
    parsed = [date.fromisoformat(value) for value in days]
    n = len(days)
    count = np.zeros((n, 100), np.float32)
    presence = np.zeros((n, 100), np.float32)
    count[:] = x[:, :, 0]
    presence[:] = x[:, :, 2]
    fit_log: list[list[Any]] = []
    months: list[tuple[int, int]] = []
    for day in parsed:
        key = (day.year, day.month)
        if not months or months[-1] != key:
            months.append(key)
    for fold, (year, month) in enumerate(months):
        current = np.asarray([(d.year, d.month) == (year, month) for d in parsed])
        first = int(np.flatnonzero(current)[0])
        lo = max(0, first - 365)
        if first - lo < 60:
            fit_log.append([f"{year:04d}-{month:02d}", None, None, int((first-lo)*100)])
            continue
        train_x = x[lo:first].reshape(-1, x.shape[2])
        current_x = x[current].reshape(-1, x.shape[2])
        reg = HistGradientBoostingRegressor(
            loss="poisson", learning_rate=0.08, max_iter=40,
            max_leaf_nodes=15, min_samples_leaf=160, l2_regularization=2.0,
            early_stopping=False, random_state=20260717 + fold,
        ).fit(train_x, y_count[lo:first].reshape(-1))
        clf = HistGradientBoostingClassifier(
            loss="log_loss", learning_rate=0.08, max_iter=40,
            max_leaf_nodes=15, min_samples_leaf=160, l2_regularization=2.0,
            early_stopping=False, random_state=20260718 + fold,
        ).fit(train_x, y_presence[lo:first].reshape(-1))
        count[current] = reg.predict(current_x).reshape(current.sum(), 100)
        presence[current] = clf.predict_proba(current_x)[:, 1].reshape(current.sum(), 100)
        fit_log.append([
            f"{year:04d}-{month:02d}", str(days[lo]), str(days[first-1]),
            int(len(train_x)),
        ])
    return {"STACK_HGB_COUNT": count, "STACK_HGB_PRES": presence}, fit_log


def static_votes(inventory, h: dict, days: list[date]) -> np.ndarray:
    wanted = set(days)
    raw = inventory.discover_row_sets(h)
    inventory.add_named_exposed_paths(h, raw)
    catalog: dict[str, dict[date, dict]] = {}
    for raw_path, rows in raw:
        path = raw_path.lstrip(".")
        if path not in STATIC_VOTER_PATHS:
            continue
        by_day = {row["date"]: row for row in rows if row["date"] in wanted}
        if len(by_day) != len(days):
            raise FusionEngineError(f"Static voter thiếu ngày: {path}")
        if path in catalog:
            raise FusionEngineError(f"Static voter trùng ID: {path}")
        catalog[path] = by_day
    if set(catalog) != set(STATIC_VOTER_PATHS):
        missing = sorted(set(STATIC_VOTER_PATHS) - set(catalog))
        raise FusionEngineError(f"Thiếu static voter: {missing}")
    votes = np.zeros((len(days), 100), np.float32)
    for path in STATIC_VOTER_PATHS:
        for i, day in enumerate(days):
            votes[i, sorted({int(code) for code in catalog[path][day]["points"]})] += 1
    return votes


def v32_cap10(raw: tuple[int, ...], base: set[int], overdue: np.ndarray):
    raw_set = set(map(int, raw))
    if not base.issubset(raw_set) or len(base) > 10:
        raise FusionEngineError("V32 base/cap10 không hợp lệ")
    online = sorted(raw_set - base, key=lambda code: (-float(overdue[code]), code))
    keep_online = online[:10-len(base)]
    priority_selected = sorted(base) + online
    capped = sorted(base | set(keep_online))
    return capped, priority_selected


def build_plan(source_xlsx: Path, source_end: date) -> dict:
    os.environ["MB_V32_SOURCE_XLSX"] = str(source_xlsx.resolve())
    sys.path.insert(0, str(ENGINE))
    previous_cwd = Path.cwd()
    os.chdir(ENGINE)
    try:
        import production_branch_c_residual_gate315_r868 as parent
        import production_v32_empirical_overdue_swap_r868 as v32_live
        import research_v18_a6b8_portfolio_inventory as inventory
        import research_v32_empirical_digit_swap_a6b8 as empirical

        source_days, source_counts, source_mode = parent.settled_history_through(source_end)
        built, generation_log, _, frozen_end = parent.extend_upstream_to_target(
            source_days, source_counts
        )
        result = parent.build_live_gate(built, source_end)
        h, cube = result["h"], result["h"]["cube"]
        result_days = list(result["days"])
        target = result_days[-1]
        if target <= source_end:
            raise FusionEngineError("Engine không sinh được kỳ kế tiếp")
        eval_days = [day for day in result_days if START <= day <= target]
        result_index = {day: i for i, day in enumerate(result_days)}
        result_take = [result_index[day] for day in eval_days]
        cube_index = {day: i for i, day in enumerate(cube.days)}
        cube_take = [cube_index[day] for day in eval_days]

        model_count = result["count"][result_take].astype(np.float32)
        model_presence = result["presence"][result_take].astype(np.float32)
        empirical_scores = empirical.score_tensor(cube, cube_take)
        votes = static_votes(inventory, h, eval_days)
        raw = {
            "MODEL_COUNT": model_count,
            "MODEL_PRES": model_presence,
            **{f"EMP_{name}": value.astype(np.float32)
               for name, value in empirical_scores.items()},
            "VOTE": (votes / len(STATIC_VOTER_PATHS)).astype(np.float32),
        }
        features = []
        for name, value in raw.items():
            features.append(zrow(value))
            if name in ("MODEL_COUNT", "MODEL_PRES", "VOTE"):
                features.append(rank01(value))
        x = np.stack(features, axis=2)
        y_count = cube.counts[cube_take].astype(np.int8)
        y_presence = (y_count > 0).astype(np.int8)
        day_strings = np.asarray([str(day) for day in eval_days])
        stacks, fit_log = walkforward_models(day_strings, x, y_count, y_presence)
        hgb_score = (
            rank01(stacks["STACK_HGB_COUNT"])
            + 0.25 * rank01(stacks["STACK_HGB_PRES"])
            + 0.25 * rank01(votes)
        ) / 1.5

        control = [tuple(sorted(row)) for row in result["port"].codes]
        base_map = {
            row["date"]: set(map(int, row["points"])) for row in h["v17_base_rows"]
        }
        base_sets = [base_map[day] for day in result_days]
        all_cube_take = [cube_index[day] for day in result_days]
        overdue_all = empirical.score_tensor(cube, all_cube_take)[v32_live.LOCKED_RULE.score]
        proposal = empirical.proposals(
            cube, all_cube_take, control, base_sets, overdue_all,
            v32_live.LOCKED_RULE.pool,
        )
        v32_raw_all, _ = empirical.apply_rule(v32_live.LOCKED_RULE, control, proposal)
        j = result_index[target]
        raw_codes = tuple(map(int, v32_raw_all[j]))
        capped, priority_selected = v32_cap10(raw_codes, base_sets[j], overdue_all[j])
        outside = sorted(
            set(range(100)) - set(raw_codes),
            key=lambda code: (-float(overdue_all[j, code]), code),
        )
        total_order = priority_selected + outside
        priority_rank = np.empty(100, np.int16)
        priority_rank[total_order] = np.arange(1, 101, dtype=np.int16)
        max10_member = np.zeros(100, np.float32)
        max10_member[capped] = 1.0

        r4 = rank01(hgb_score[-1:])[0]
        r10 = 1.0 - (priority_rank.astype(np.float32) - 1) / 99
        fused = 0.75 * r4 + 0.25 * r10 + 0.50 * max10_member
        codes = np.arange(100)
        order = np.lexsort((codes, -fused))[:4]
        code_strings = [f"{int(code):02d}" for code in order]
        points = [50, 50, 50, 30]
        points_by_code = dict(zip(code_strings, points))
        if len(set(code_strings)) != 4 or sum(points_by_code.values()) != 180:
            raise FusionEngineError("Fusion4 plan invariant failed")
        if int(y_count[-1].sum()) != 0:
            raise FusionEngineError("Kết quả kỳ mục tiêu đã lộ vào engine")
        selection_material = {
            "target": str(target), "data_lock": str(source_end),
            "config": CONFIG_ID,
            "hgb": {f"{i:02d}": float(hgb_score[-1, i]) for i in range(100)},
            "v32_rank": {f"{i:02d}": int(priority_rank[i]) for i in range(100)},
            "v32_cap10": [f"{i:02d}" for i in capped],
            "codes": code_strings, "points": points_by_code,
        }
        return {
            "schema_version": "MB_FUSION4_ENGINE_PLAN_V1",
            "source_end": str(source_end),
            "target_date": str(target),
            "config_id": CONFIG_ID,
            "codes": code_strings,
            "points_by_code": points_by_code,
            "total_points": 180,
            "capital_vnd": 180 * COST_PER_POINT,
            "outcome_known_at_selection": False,
            "selection_input_hash": digest(selection_material),
            "ranking": {
                "formula": "0.75*Max4_rank + 0.25*Max10_priority_rank + 0.50*I(code_in_Max10)",
                "top10": [
                    {
                        "rank": rank + 1,
                        "code": f"{int(code):02d}",
                        "fusion_score": float(fused[code]),
                        "max4_rank_score": float(r4[code]),
                        "max10_rank_score": float(r10[code]),
                        "in_max10": bool(max10_member[code]),
                    }
                    for rank, code in enumerate(np.lexsort((codes, -fused))[:10])
                ],
                "a1_role": "AUDIT_CONFIRMATION_ONLY_IN_FIXED_K4",
                "static_voter_manifest_sha256": STATIC_MANIFEST_SHA256,
            },
            "causality": {
                "source_mode": source_mode,
                "source_end": str(source_end),
                "frozen_upstream_end": str(frozen_end),
                "target_outcome_sum": int(y_count[-1].sum()),
                "fit_log_last": fit_log[-1],
                "generation_log_last": generation_log[-1],
            },
        }
    finally:
        os.chdir(previous_cwd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-xlsx", type=Path, required=True)
    parser.add_argument("--source-end", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan = build_plan(args.source_xlsx, args.source_end)
    except (AssertionError, KeyError, ValueError, FusionEngineError) as exc:
        print(f"FUSION4_ENGINE_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "target_date": plan["target_date"], "codes": plan["codes"],
        "points_by_code": plan["points_by_code"],
        "selection_input_hash": plan["selection_input_hash"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
