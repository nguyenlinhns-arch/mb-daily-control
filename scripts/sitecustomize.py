"""Install the parallel planner after the packed base planner receives its A1 patch.

This hook is intentionally inert for every command except
`python scripts/patch_a1_top3_watchlist.py`.  It runs at interpreter exit so the
existing A1 Top-3 patch is applied first, preserves that fully patched engine as
`plan_next_day_base.py`, then makes the workflow entry point delegate to the
parallel A1/X2/X3 planner.
"""
from __future__ import annotations

import atexit
import sys
from pathlib import Path


def _install_parallel_entrypoint() -> None:
    root = Path(__file__).resolve().parents[1]
    scripts = root / "scripts"
    target = scripts / "plan_next_day.py"
    base = scripts / "plan_next_day_base.py"
    if not target.exists():
        raise RuntimeError(f"Missing materialized planner: {target}")
    patched = target.read_text(encoding="utf-8")
    if "A1_TOP3_WATCHLIST_V1" not in patched:
        raise RuntimeError("A1 Top-3 patch was not applied before parallel install")
    base.write_text(patched, encoding="utf-8")
    delegator = '''#!/usr/bin/env python3
"""Workflow entry point: delegate to the parallel A1/X2/X3 controller."""
from plan_next_day_parallel import main

if __name__ == "__main__":
    main()
'''
    target.write_text(delegator, encoding="utf-8")
    target.chmod(0o755)
    print("PARALLEL_PLANNER_ENTRYPOINT_INSTALLED")


if Path(sys.argv[0]).name == "patch_a1_top3_watchlist.py":
    atexit.register(_install_parallel_entrypoint)
