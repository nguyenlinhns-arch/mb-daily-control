from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def normalize_pick_list(values: list[str] | tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for raw in values:
        text = str(raw).strip()
        if not text.isdigit():
            raise ValueError(f"invalid pick code: {raw!r}")
        n = int(text)
        if not 0 <= n <= 99:
            raise ValueError(f"pick out of range: {raw!r}")
        code = f"{n:02d}"
        if code not in out:
            out.append(code)
    return out


def parse_pick_text(text: str) -> list[str]:
    text = (text or "").strip().upper()
    if text in {"", "A0", "RUN_INVALID_NO_BET", "NO BET", "PRE_DRAW"}:
        return []
    import re
    return normalize_pick_list(re.findall(r"(?<!\d)\d{2}(?!\d)", text))
