from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fusion4_daily as fusion4


class Fusion4DailyTests(unittest.TestCase):
    def test_locked_seed_plan_has_fixed_180_point_stakes(self) -> None:
        plan = fusion4.load_plan(date(2026, 7, 19))
        self.assertEqual(plan["codes"], ["59", "78", "06", "10"])
        self.assertEqual(
            [plan["points_by_code"][code] for code in plan["codes"]],
            [50, 50, 50, 30],
        )
        self.assertEqual(plan["total_capital_vnd"], 4_140_000)

    def test_rank_four_single_hit_settlement(self) -> None:
        plan = {
            "target_date": "2026-07-18",
            "codes": ["57", "55", "91", "54"],
            "points_by_code": {"57": 50, "55": 50, "91": 50, "54": 30},
        }
        draw = ["54"] + [f"{value:02d}" for value in range(1, 27)]
        settlement = fusion4.settle(plan, draw)
        self.assertEqual(settlement["hit_units"], 1)
        self.assertEqual(settlement["payout_vnd"], 2_400_000)
        self.assertEqual(settlement["pnl_vnd"], -1_740_000)

    def test_rendered_dashboard_matches_machine_payload(self) -> None:
        current = json.loads((ROOT / "data" / "current.json").read_text())
        rendered = fusion4.render(current)
        self.assertEqual(rendered, (ROOT / "index.html").read_text())
        self.assertNotIn("{{", rendered)

    def test_sheet_records_use_settlement_run_date(self) -> None:
        plan = fusion4.load_plan(date(2026, 7, 19))
        settlement = json.loads(
            (ROOT / "data" / "fusion4-settlements" / "2026-07-18.json").read_text()
        )
        snapshot = {
            "draw": ["00"] * 27,
            "people": [
                {"name": name, "sheet_name": name, "rows": []}
                for name in ("p1", "p2", "p3", "p4", "p5")
            ],
        }
        payload = fusion4.build_sheet_payload(
            date(2026, 7, 19), plan, settlement, snapshot, "input-hash"
        )
        source_records = [
            operation["record"] for operation in payload["operations"]
            if operation["kind"].startswith("UPSERT_SOURCE_")
        ]
        self.assertTrue(source_records)
        self.assertTrue(all(
            record["created_at"] == "2026-07-18T19:15:00+07:00"
            for record in source_records
        ))


if __name__ == "__main__":
    unittest.main()
