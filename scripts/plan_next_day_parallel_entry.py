#!/usr/bin/env python3
"""Runtime entry for the parallel planner plus Xiên 2 recommendation.

The workflow materializes and patches the packed base engine into
`plan_next_day_base.py`. The parallel controller source is evaluated with its
base-engine path redirected to that file. After a successful normal planning
run, the Xiên 2 engine deterministically generates every pair from the unique
positive-stake codes. Self-tests and data-failure paths never create pairs.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "plan_next_day_parallel.py"
BASE = HERE / "plan_next_day_base.py"

if not BASE.exists():
    raise RuntimeError(f"Missing patched base planner: {BASE}")

text = SOURCE.read_text(encoding="utf-8")
old = 'HERE / "plan_next_day.py"'
new = 'HERE / "plan_next_day_base.py"'
if old not in text:
    raise RuntimeError("Parallel planner base import marker not found")
text = text.replace(old, new, 1)
namespace = {
    "__name__": "mb_parallel_runtime",
    "__file__": str(SOURCE),
    "__package__": None,
}
exec(compile(text, str(SOURCE), "exec"), namespace)
_planner_main = namespace["main"]


def main() -> None:
    original_argv = list(sys.argv)
    _planner_main()
    if any(flag in original_argv for flag in ("--self-test", "--data-fail")):
        return
    from apply_xien2_auto_pairs import main as xien2_main

    try:
        sys.argv = [original_argv[0]]
        xien2_main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()
