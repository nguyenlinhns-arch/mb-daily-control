from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .hashing import sha256_file
from .io_utils import read_tsv
from .ledger_guard import validate_run


def _ledger_guard_rows(methods: list[dict[str, str]], target: date, cutoff: date) -> list[dict[str, Any]]:
    """Translate persisted TSV rows into the typed ledger contract without coercion."""
    out: list[dict[str, Any]] = []
    for row in methods:
        method = (row.get("method") or "").strip()
        status = (row.get("status") or "").strip().upper()
        raw_pick = (row.get("pick") or "").strip()
        native_raw = (row.get("native_k") or "").strip()
        if status != "SUCCESS":
            action = "RUN_INVALID_NO_BET"
            codes: list[str] = []
        else:
            if native_raw not in {"0", "1", "2"}:
                raise ValueError(f"{method}: native_k must be exact 0/1/2 text")
            native_k = int(native_raw)
            if native_k == 0:
                if raw_pick.upper() != "A0":
                    raise ValueError(f"{method}: zero-leg SUCCESS must be explicit A0")
                action = "A0"
                codes = []
            else:
                # Full-match only. Decimal/scalar corruption such as 5.0 or 50.0 is rejected.
                if not re.fullmatch(r"[0-9]{2}(?:\\s*,\\s*[0-9]{2})?", raw_pick):
                    raise ValueError(f"{method}: malformed pick serialization {raw_pick!r}")
                codes = [part.strip() for part in raw_pick.split(",")]
                action = "A1" if native_k == 1 else "A2"
        out.append({
            "method_id": method,
            "target_date": target.isoformat(),
            "data_lock": cutoff.isoformat(),
            "action": action,
            "codes": codes,
            "evidence": f"method_results:{method}",
        })
    return out


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
    try:
        guard_rows = _ledger_guard_rows(methods, target, cutoff)
        validate_run(
            guard_rows,
            target_date=target.isoformat(),
            data_lock=cutoff.isoformat(),
            expected_method_ids=[str(r.get("method") or "").strip() for r in methods],
        )
        check("ledger_guard_67", True, "typed rows; exact T-1; 2-digit strings; A0/invalid separated")
    except Exception as exc:
        check("ledger_guard_67", False, str(exc))
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
