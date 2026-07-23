#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(index_path: Path, data_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "MB_PUBLIC_PRIVACY_V1"
    assert payload["status"] == "PRIVATE_FINANCIAL_DATA_REDACTED"
    assert payload["source_verification"]["independent_sources"] >= 2
    assert payload["source_verification"]["result_units"] == 27
    assert payload["source_verification"]["status"] == "MATCHED_EXACTLY"
    assert 'data-static-dashboard="1"' in html
    assert "MB_STATUS_SAFE_V1" in html
    assert "Dữ liệu tài chính riêng tư đã được ẩn" in html
    assert "23/07/2026" in html
    assert "2 nguồn · đủ 27/27" in html
    assert "Đang tải kế hoạch kỳ sắp tới" not in html
    assert "SYSTEM_SIGNAL_NOT_YET_CONFIRMED" not in html
    assert "SONG LỘC" not in html
    assert "R39 DAILY MASTER" not in html
    assert "Linh" not in html
    assert "điểm" not in html
    assert "₫" not in html and ".000đ" not in html
    print("MB_PUBLIC_PRIVACY_VALIDATION_OK", payload["reviewed_through"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("data", type=Path)
    args = parser.parse_args()
    validate(args.index, args.data)


if __name__ == "__main__":
    main()
