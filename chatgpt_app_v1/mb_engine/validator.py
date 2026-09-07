from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .hashing import sha256_file
from .io_utils import read_tsv


def validate_generated_run(runtime_root: Path, target: date) -> dict[str, Any]:
    key = target.strftime("%Y%m%d")
    cutoff = target - timedelta(days=1)
    out = runtime_root / "output" / "MB TOP2+" / target.isoformat() / "fusion67"
    summary_path = out / f"fusion67_summary_{key}.json"
    methods_path = out / f"method_results_{key}.tsv"
    ranking_path = out / f"candidate_ranking_{key}.tsv"
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    for path in (summary_path, methods_path, ranking_path):
        check(f"exists:{path.name}", path.exists())
    if any(c["status"] == "FAIL" for c in checks):
        return {"status": "FAIL", "checks": checks}

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    methods = read_tsv(methods_path)
    ranking = read_tsv(ranking_path)
    check("target_date", summary.get("target_date") == target.isoformat(), str(summary.get("target_date")))
    check("data_cutoff", summary.get("data_cutoff") == cutoff.isoformat(), str(summary.get("data_cutoff")))
    check("pre_draw_status", summary.get("status") == "PRE_DRAW_FROZEN", str(summary.get("status")))
    check("no_target_outcome", summary.get("source", {}).get("no_target_outcome_used") is True)
    check("source_width_27", summary.get("source", {}).get("cutoff_result_count") == 27)
    check("method_count_67", len(methods) == 67, str(len(methods)))
    check("method_unique_67", len({r.get("method") for r in methods}) == 67)
    check("all_success", all(r.get("status") == "SUCCESS" for r in methods))
    check("coverage_registry", int(summary.get("coverage", {}).get("registry_rows", -1)) == 67)
    check("coverage_success", int(summary.get("coverage", {}).get("methods_success", -1)) == 67)
    check("coverage_voting", int(summary.get("coverage", {}).get("methods_voting", -1)) == 64)
    check("coverage_shadow", int(summary.get("coverage", {}).get("methods_shadow_zero_vote", -1)) == 3)
    check("family_count", int(summary.get("coverage", {}).get("independent_families", -1)) == 60)

    checkpoints = sorted((out / "checkpoints").glob("method_*.json"))
    check("checkpoint_count_67", len(checkpoints) == 67, str(len(checkpoints)))
    if len(checkpoints) == 67:
        cp_ok = True
        for row, cp_path in zip(methods, checkpoints):
            cp = json.loads(cp_path.read_text(encoding="utf-8"))
            if cp.get("method") != row.get("method") or cp.get("pick") != row.get("pick") or cp.get("data_cutoff") != cutoff.isoformat():
                cp_ok = False
                break
        check("checkpoint_matches_method_rows", cp_ok)

    final_pick = [str(x).zfill(2) for x in summary.get("final_pick", [])]
    check("raw_k3", len(final_pick) == 3 and len(set(final_pick)) == 3, str(final_pick))
    ranks = [int(r["rank"]) for r in ranking]
    check("candidate_ranks_1_10", ranks == list(range(1, len(ranking) + 1)) and len(ranking) == 10, str(ranks))
    check("final_equals_top3", final_pick == [r["number"].zfill(2) for r in ranking[:3]])

    hashes = {p.name: sha256_file(p) for p in (summary_path, methods_path, ranking_path)}
    passed = sum(c["status"] == "PASS" for c in checks)
    return {
        "status": "PASS" if passed == len(checks) else "FAIL",
        "target_date": target.isoformat(),
        "data_cutoff": cutoff.isoformat(),
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "source_hashes": hashes,
    }
