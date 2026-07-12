#!/usr/bin/env python3
"""Runtime entry for the parallel planner.

The workflow materializes and patches the packed base engine into
`plan_next_day_base.py`.  The parallel controller source is then evaluated with
its base-engine path redirected to that preserved file, avoiding recursive
imports after `plan_next_day.py` becomes the workflow delegator.
"""
from __future__ import annotations

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
main = namespace["main"]

if __name__ == "__main__":
    main()
