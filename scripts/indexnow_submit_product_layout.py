#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply(root: Path) -> dict[str, object]:
    import sitewide_product_surface
    result = sitewide_product_surface.apply(root)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', type=Path, default=ROOT / '_site')
    args = parser.parse_args()
    print(json.dumps(apply(args.output_root), ensure_ascii=False))

if __name__ == '__main__':
    main()
