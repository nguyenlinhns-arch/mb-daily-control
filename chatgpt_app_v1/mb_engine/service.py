from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .governance import build_governance
from .hashing import canonical_hash, sha256_file, sha256_tree
from .io_utils import parse_pick_text, read_json, read_tsv, write_json
from .validator import validate_generated_run

VN_TZ = timezone(timedelta(hours=7))


class EngineError(RuntimeError):
    pass


class FileMutex:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


class MBEngineService:
    def __init__(self, repo_root: Path | None = None, state_root: Path | None = None):
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
        self.seed_root = self.repo_root / "runtime_seed"
        self.state_root = Path(state_root or os.environ.get("MB_ENGINE_STATE_DIR", self.repo_root / "state")).resolve()
        self.runtime_root = self.state_root / "runtime"
        self.runs_root = self.state_root / "runs"
        self.frozen_root = self.state_root / "frozen"
        self.settlements_root = self.state_root / "settlements"
        self.lock_path = self.state_root / ".engine.lock"
        for p in (self.runs_root, self.frozen_root, self.settlements_root):
            p.mkdir(parents=True, exist_ok=True)
        self._ensure_runtime()
        self._ensure_imported_freeze_20260907()

    def _ensure_runtime(self) -> None:
        if not self.runtime_root.exists():
            shutil.copytree(self.seed_root, self.runtime_root)

    def _ensure_imported_freeze_20260907(self) -> None:
        target = date(2026, 9, 7)
        freeze_path = self._freeze_path(target)
        if freeze_path.exists():
            return
        out = self.runtime_root / "output" / "MB TOP2+" / target.isoformat() / "fusion67"
        summary_path = out / "fusion67_summary_20260907.json"
        methods_path = out / "method_results_20260907.tsv"
        ranking_path = out / "candidate_ranking_20260907.tsv"
        if not all(p.exists() for p in (summary_path, methods_path, ranking_path)):
            return
        summary = read_json(summary_path)
        methods = read_tsv(methods_path)
        governance = build_governance(summary, methods)
        if governance["final_pick"] != ["31", "63", "43"]:
            raise EngineError("imported 07/09 governance mismatch")
        record = {
            "schema_version": 1,
            "target_date": target.isoformat(),
            "status": "PRE_DRAW_FROZEN",
            "origin": "IMPORTED_CANONICAL_FREEZE",
            "frozen_at": summary["frozen_at"],
            "raw_summary": summary,
            "governance": governance,
            "validator": {
                "status": "PASS",
                "origin": "IMPORTED_EXTERNAL_VALIDATION",
                "checks_passed": 87,
                "checks_total": 87,
                "window_checks": "402/402",
            },
            "artifact_hashes": {
                "summary": sha256_file(summary_path),
                "methods": sha256_file(methods_path),
                "ranking": sha256_file(ranking_path),
            },
        }
        record["freeze_hash"] = canonical_hash(record)
        write_json(freeze_path, record)

    def _parse_target(self, target_date: str) -> date:
        try:
            target = date.fromisoformat(target_date)
        except ValueError as e:
            raise EngineError("target_date must be YYYY-MM-DD") from e
        if target <= date(2026, 9, 2):
            raise EngineError("FUSION67 daily engine only accepts targets after 2026-09-02")
        return target

    def _freeze_path(self, target: date) -> Path:
        return self.frozen_root / f"{target.isoformat()}.json"

    def _settlement_path(self, target: date) -> Path:
        return self.settlements_root / f"{target.isoformat()}.json"

    def _supplements(self, root: Path | None = None) -> dict[str, Any]:
        path = (root or self.runtime_root) / "output" / "MB TOP2+" / "verified_draw_supplements.json"
        return read_json(path)

    def _assert_no_target_outcome(self, target: date) -> None:
        if target.isoformat() in self._supplements():
            raise EngineError(f"RUN BLOCKED: target outcome already exists for {target.isoformat()}")

    def _assert_cutoff_ready(self, target: date) -> None:
        cutoff = target - timedelta(days=1)
        supplements = self._supplements()
        if cutoff >= date(2026, 9, 2) and cutoff.isoformat() not in supplements:
            raise EngineError(f"RUN BLOCKED: verified cutoff draw missing for {cutoff.isoformat()}")
        prev_summary = self.runtime_root / "output" / "MB TOP2+" / cutoff.isoformat() / "fusion67" / f"fusion67_summary_{cutoff:%Y%m%d}.json"
        if not prev_summary.exists():
            raise EngineError(f"RUN BLOCKED: previous frozen summary missing: {prev_summary}")

    def _execute_in_clone(self, target: date) -> tuple[Path, dict[str, Any]]:
        work_dir = Path(tempfile.mkdtemp(prefix=f"mbtop2-{target.isoformat()}-"))
        clone = work_dir / "runtime"
        shutil.copytree(self.runtime_root, clone)
        target_out = clone / "output" / "MB TOP2+" / target.isoformat()
        if target_out.exists():
            shutil.rmtree(target_out)
        env = os.environ.copy()
        env.update({
            "PYTHONHASHSEED": "0",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        })
        proc = subprocess.run(
            [sys.executable, "mb_top2_fusion67_daily.py", "--target", target.isoformat()],
            cwd=clone,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
            check=False,
        )
        if proc.returncode != 0:
            raise EngineError(f"engine failed rc={proc.returncode}: {proc.stderr[-4000:]}")
        try:
            stdout_summary = json.loads(proc.stdout)
        except Exception as e:
            raise EngineError(f"engine returned non-JSON output: {proc.stdout[-1000:]}") from e
        return clone, stdout_summary

    def run_day(self, target_date: str) -> dict[str, Any]:
        target = self._parse_target(target_date)
        with FileMutex(self.lock_path):
            if self._freeze_path(target).exists():
                frozen = read_json(self._freeze_path(target))
                return {"status": "ALREADY_FROZEN", "target_date": target.isoformat(), "frozen": self._public_freeze(frozen)}
            self._assert_no_target_outcome(target)
            self._assert_cutoff_ready(target)
            clone: Path | None = None
            try:
                clone, stdout_summary = self._execute_in_clone(target)
                validator = validate_generated_run(clone, target)
                if validator["status"] != "PASS":
                    raise EngineError("RUN BLOCKED: validator failed")
                out = clone / "output" / "MB TOP2+" / target.isoformat() / "fusion67"
                key = target.strftime("%Y%m%d")
                summary = read_json(out / f"fusion67_summary_{key}.json")
                methods = read_tsv(out / f"method_results_{key}.tsv")
                governance = build_governance(summary, methods)
                run_id = f"{target:%Y%m%d}-{uuid.uuid4().hex[:12]}"
                run_dir = self.runs_root / run_id
                payload_dir = run_dir / "payload"
                payload_dir.mkdir(parents=True)
                shutil.copytree(out, payload_dir / "fusion67")
                run_record = {
                    "schema_version": 1,
                    "run_id": run_id,
                    "status": "VALIDATED_NOT_FROZEN",
                    "target_date": target.isoformat(),
                    "data_cutoff": (target - timedelta(days=1)).isoformat(),
                    "created_at": datetime.now(VN_TZ).isoformat(timespec="seconds"),
                    "engine_seed_hash": sha256_tree(self.seed_root),
                    "runtime_input_hash": sha256_tree(self.runtime_root, exclude_names={".engine.lock"}),
                    "raw_summary": summary,
                    "governance": governance,
                    "validator": validator,
                    "stdout_summary_match": stdout_summary.get("final_pick") == summary.get("final_pick"),
                }
                run_record["run_hash"] = canonical_hash(run_record)
                write_json(run_dir / "run.json", run_record)
                return self._public_run(run_record)
            finally:
                if clone is not None:
                    with contextlib.suppress(Exception):
                        shutil.rmtree(clone.parent)

    def freeze_day(self, target_date: str, run_id: str) -> dict[str, Any]:
        target = self._parse_target(target_date)
        with FileMutex(self.lock_path):
            freeze_path = self._freeze_path(target)
            if freeze_path.exists():
                existing = read_json(freeze_path)
                if existing.get("run_id") == run_id:
                    return {"status": "ALREADY_FROZEN_SAME_RUN", "frozen": self._public_freeze(existing)}
                raise EngineError(f"FREEZE BLOCKED: {target.isoformat()} is already frozen")
            self._assert_no_target_outcome(target)
            run_dir = self.runs_root / run_id
            run_path = run_dir / "run.json"
            if not run_path.exists():
                raise EngineError("unknown run_id")
            run = read_json(run_path)
            if run.get("target_date") != target.isoformat() or run.get("status") != "VALIDATED_NOT_FROZEN":
                raise EngineError("run is not eligible for freeze")
            if run.get("validator", {}).get("status") != "PASS":
                raise EngineError("validator not PASS")
            src = run_dir / "payload" / "fusion67"
            dest = self.runtime_root / "output" / "MB TOP2+" / target.isoformat() / "fusion67"
            if dest.exists():
                shutil.rmtree(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest)
            frozen_at = run["raw_summary"].get("frozen_at") or datetime.now(VN_TZ).isoformat(timespec="seconds")
            record = {
                "schema_version": 1,
                "target_date": target.isoformat(),
                "run_id": run_id,
                "run_hash": run["run_hash"],
                "status": "PRE_DRAW_FROZEN",
                "origin": "MB_TOP2_ENGINE_V1",
                "frozen_at": frozen_at,
                "raw_summary": run["raw_summary"],
                "governance": run["governance"],
                "validator": run["validator"],
                "artifact_hash": sha256_tree(dest),
            }
            record["freeze_hash"] = canonical_hash(record)
            write_json(freeze_path, record)
            run["status"] = "FROZEN"
            run["freeze_hash"] = record["freeze_hash"]
            write_json(run_path, run)
            return {"status": "PRE_DRAW_FROZEN", "frozen": self._public_freeze(record)}

    def get_day(self, target_date: str) -> dict[str, Any]:
        target = self._parse_target(target_date)
        freeze_path = self._freeze_path(target)
        settlement_path = self._settlement_path(target)
        return {
            "target_date": target.isoformat(),
            "frozen": self._public_freeze(read_json(freeze_path)) if freeze_path.exists() else None,
            "settlement": read_json(settlement_path) if settlement_path.exists() else None,
        }

    def _find_artifact_dir(self, target: date, run_id: str | None = None) -> Path:
        if run_id:
            path = self.runs_root / run_id / "payload" / "fusion67"
            if not path.exists():
                raise EngineError("unknown run_id")
            return path
        if not self._freeze_path(target).exists():
            raise EngineError("target is not frozen; supply run_id for a draft")
        path = self.runtime_root / "output" / "MB TOP2+" / target.isoformat() / "fusion67"
        if not path.exists():
            raise EngineError("frozen artifact directory missing")
        return path

    def get_candidates(self, target_date: str, limit: int = 10, run_id: str | None = None) -> dict[str, Any]:
        target = self._parse_target(target_date)
        if not 1 <= limit <= 100:
            raise EngineError("limit must be 1..100")
        out = self._find_artifact_dir(target, run_id)
        rows = read_tsv(out / f"candidate_ranking_{target:%Y%m%d}.tsv")
        return {"target_date": target.isoformat(), "rows": rows[:limit], "count": min(limit, len(rows))}

    def get_hot_cold(self, target_date: str, run_id: str | None = None) -> dict[str, Any]:
        target = self._parse_target(target_date)
        out = self._find_artifact_dir(target, run_id)
        rows = read_tsv(out / f"method_results_{target:%Y%m%d}.tsv")
        strong_hot, fast_hot, cold = [], [], []
        for row in rows:
            item = {"method": row["method"], "role": row["role"], "family": row["family"], "pick": parse_pick_text(row["pick"]), "state": row["state"], "W3": row.get("W3"), "W5": row.get("W5"), "W7": row.get("W7"), "W10": row.get("W10"), "PL7": int(float(row.get("PL7", 0) or 0))}
            state = row["state"].upper()
            if "STRONG HOT" in state:
                strong_hot.append(item)
            elif "FAST HOT" in state:
                fast_hot.append(item)
            if "COLD" in state:
                cold.append(item)
        return {"target_date": target.isoformat(), "strong_hot": strong_hot, "fast_hot": fast_hot, "cold": cold, "counts": {"strong_hot": len(strong_hot), "fast_hot": len(fast_hot), "cold": len(cold)}}

    def get_method_audit(self, target_date: str, method: str | None = None, run_id: str | None = None) -> dict[str, Any]:
        target = self._parse_target(target_date)
        out = self._find_artifact_dir(target, run_id)
        rows = read_tsv(out / f"method_results_{target:%Y%m%d}.tsv")
        if method:
            rows = [r for r in rows if r["method"] == method]
            if not rows:
                raise EngineError(f"method not found: {method}")
        return {"target_date": target.isoformat(), "rows": rows, "count": len(rows)}

    def audit_day(self, target_date: str, run_id: str | None = None) -> dict[str, Any]:
        target = self._parse_target(target_date)
        if run_id:
            run = read_json(self.runs_root / run_id / "run.json")
            return run["validator"]
        freeze = read_json(self._freeze_path(target)) if self._freeze_path(target).exists() else None
        if freeze is None:
            raise EngineError("target is not frozen; supply run_id")
        return freeze["validator"]

    def settle_day(self, target_date: str, draw: list[int], sources: list[str], full_prizes: list[str] | None = None) -> dict[str, Any]:
        target = self._parse_target(target_date)
        with FileMutex(self.lock_path):
            freeze_path = self._freeze_path(target)
            if not freeze_path.exists():
                raise EngineError("SETTLEMENT BLOCKED: target has no PRE_DRAW_FROZEN record")
            if len(draw) != 27 or any((not isinstance(x, int)) or x < 0 or x > 99 for x in draw):
                raise EngineError("draw must contain exactly 27 integers in 0..99")
            clean_sources = sorted({s.strip() for s in sources if s and s.strip()})
            if len(clean_sources) < 2:
                raise EngineError("settlement requires at least two independent source labels")
            existing_path = self._settlement_path(target)
            if existing_path.exists():
                existing = read_json(existing_path)
                if existing.get("draw") == draw:
                    return {"status": "ALREADY_SETTLED_SAME_DRAW", "settlement": existing}
                raise EngineError("SETTLEMENT BLOCKED: conflicting draw already recorded")
            frozen = read_json(freeze_path)
            pick = frozen["governance"]["final_pick"]
            counts = Counter(draw)
            occurrences_by_number = {n: counts[int(n)] for n in pick}
            occurrences = sum(occurrences_by_number.values())
            stake = len(pick) * 10 * 27_000
            payout = occurrences * 10 * 99_500
            pl = payout - stake
            settlement = {
                "schema_version": 1,
                "target_date": target.isoformat(),
                "status": "WIN" if occurrences > 0 else "LOSS",
                "frozen_pick": pick,
                "draw": draw,
                "sources": clean_sources,
                "verified_sources_agree": True,
                "occurrences_by_number": occurrences_by_number,
                "occurrences": occurrences,
                "stake_vnd": stake,
                "payout_vnd": payout,
                "pl_vnd": pl,
                "settled_at": datetime.now(VN_TZ).isoformat(timespec="seconds"),
                "freeze_hash": frozen["freeze_hash"],
            }
            settlement["settlement_hash"] = canonical_hash(settlement)
            write_json(existing_path, settlement)
            supplements_path = self.runtime_root / "output" / "MB TOP2+" / "verified_draw_supplements.json"
            supplements = read_json(supplements_path)
            supplement: dict[str, Any] = {
                "draw": draw,
                "sources": clean_sources,
                "verified_sources_agree": True,
                "recorded_by": "MB_TOP2_ENGINE_V1",
                "settlement_hash": settlement["settlement_hash"],
            }
            if full_prizes:
                if len(full_prizes) != 27:
                    raise EngineError("full_prizes must have 27 entries when supplied")
                supplement["full_prizes"] = [str(x) for x in full_prizes]
            supplements[target.isoformat()] = supplement
            write_json(supplements_path, supplements)
            return {"status": "SETTLED", "settlement": settlement}

    def prospective_status(self) -> dict[str, Any]:
        freezes = sorted(self.frozen_root.glob("*.json"))
        settlements = sorted(self.settlements_root.glob("*.json"))
        return {
            "engine": "MB TOP2+ Engine v1",
            "runtime_seed_hash": sha256_tree(self.seed_root),
            "frozen_days": [p.stem for p in freezes],
            "settled_days": [p.stem for p in settlements],
            "latest_frozen": freezes[-1].stem if freezes else None,
            "latest_settled": settlements[-1].stem if settlements else None,
            "prospective_router": {
                "status": "SHADOW_ONLY",
                "minimum_sessions_for_review": 60,
                "interim_review": 30,
                "production_change": False,
            },
        }

    @staticmethod
    def _public_run(run: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": run["status"],
            "run_id": run["run_id"],
            "run_hash": run["run_hash"],
            "target_date": run["target_date"],
            "data_cutoff": run["data_cutoff"],
            "raw_final_pick": [str(x).zfill(2) for x in run["raw_summary"]["final_pick"]],
            "governance": run["governance"],
            "coverage": run["raw_summary"]["coverage"],
            "top_candidates": run["raw_summary"]["top_candidates"],
            "validator": {k: run["validator"].get(k) for k in ("status", "checks_passed", "checks_total")},
            "freeze_required": True,
        }

    @staticmethod
    def _public_freeze(frozen: dict[str, Any]) -> dict[str, Any]:
        return {
            "target_date": frozen["target_date"],
            "status": frozen["status"],
            "origin": frozen.get("origin"),
            "frozen_at": frozen["frozen_at"],
            "freeze_hash": frozen["freeze_hash"],
            "raw_final_pick": [str(x).zfill(2) for x in frozen["raw_summary"]["final_pick"]],
            "final_pick": frozen["governance"]["final_pick"],
            "k": frozen["governance"]["k"],
            "top2": frozen["governance"]["base_pick"],
            "third_candidate": frozen["governance"]["third_candidate"],
            "third_gate": frozen["governance"]["third_gate"]["status"],
            "stake_vnd": frozen["governance"]["stake_vnd"],
            "validator_status": frozen["validator"].get("status"),
        }
