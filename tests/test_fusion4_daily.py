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

    def test_actual_performance_tracks_wins_losses_and_longest_streaks(self) -> None:
        period = fusion4.empty_actual_period()
        for pnl in (100_000, 200_000, -50_000, -50_000):
            period = fusion4.update_actual_period(period, {"pnl_vnd": pnl})
        self.assertEqual(period["sessions"], 4)
        self.assertEqual(period["wins"], 2)
        self.assertEqual(period["losses"], 2)
        self.assertEqual(period["longest_winning_streak"], 2)
        self.assertEqual(period["longest_losing_streak"], 2)
        self.assertEqual(period["current_winning_streak"], 0)
        self.assertEqual(period["current_losing_streak"], 2)
        self.assertEqual(period["net_profit_vnd"], 200_000)

    def test_july_performance_seed_matches_published_state(self) -> None:
        seed = json.loads(
            (ROOT / "data" / "personal-actual-seed-2026-07.json").read_text()
        )
        period = fusion4.empty_actual_period()
        for row in seed["rows"]:
            period = fusion4.update_actual_period(period, row)
        state = json.loads((ROOT / "data" / "fusion4-state.json").read_text())
        self.assertEqual(period, seed["summary"])
        self.assertEqual(period, state["actual"]["current_month"])
        self.assertEqual(period, state["actual"]["total"])
        self.assertEqual(state["actual"]["tracking_start_date"], "2026-07-01")
        self.assertEqual(
            seed["group_actual_pnl"]["net_profit_vnd"],
            state["group_actual_pnl"]["net_profit_vnd"],
        )

    def test_method_settlement_never_changes_personal_actual(self) -> None:
        state = json.loads((ROOT / "data" / "fusion4-state.json").read_text())
        before = json.loads(json.dumps(state))
        settlement = {
            "date": "2026-07-18",
            "pnl_vnd": -1,
            "capital_vnd": 1,
            "payout_vnd": 0,
            "hit_day": False,
            "profit_day": False,
        }
        advanced = fusion4.advance_state(before, settlement)
        self.assertEqual(advanced["actual"], before["actual"])

    def test_personal_actual_uses_linh_order_not_method_result(self) -> None:
        state = json.loads((ROOT / "data" / "fusion4-state.json").read_text())
        settlement = {
            "date": "2026-07-19",
            "pnl_vnd": 3_860_000,
            "capital_vnd": 4_140_000,
            "payout_vnd": 8_000_000,
            "hit_day": True,
            "profit_day": True,
        }
        method_advanced = fusion4.advance_state(state, settlement)
        operations = [{
            "kind": "UPDATE_PERSONAL_PNL_IF_BLANK",
            "name": "p1",
            "pnl_vnd": 660_000,
            "pnl_was_blank": True,
        }]
        advanced = fusion4.advance_personal_actual(
            method_advanced, date(2026, 7, 19), operations
        )
        actual = advanced["actual"]
        self.assertEqual(actual["settled_through"], "2026-07-19")
        self.assertEqual(actual["current_month"]["sessions"], 15)
        self.assertEqual(actual["current_month"]["wins"], 9)
        self.assertEqual(actual["current_month"]["current_winning_streak"], 1)
        self.assertEqual(actual["current_month"]["net_profit_vnd"], 19_326_000)
        self.assertEqual(actual["total"], actual["current_month"])

    def test_no_linh_order_advances_check_date_without_fake_result(self) -> None:
        state = json.loads((ROOT / "data" / "fusion4-state.json").read_text())
        advanced = fusion4.advance_personal_actual(
            state, date(2026, 7, 19), [
                {"kind": "LOG_PERSONAL_NO_ORDER", "name": "p1"}
            ]
        )
        self.assertEqual(advanced["actual"]["settled_through"], "2026-07-19")
        self.assertEqual(advanced["actual"]["total"], state["actual"]["total"])

    def test_group_total_adds_only_new_blank_pnl_cells(self) -> None:
        state = json.loads((ROOT / "data" / "fusion4-state.json").read_text())
        values = (18_666_000, 0, -920_000, 285_000, 0)
        snapshot = {"people": []}
        for i, value in enumerate(values, start=1):
            pnl_cell = 285_000 if i == 4 else None
            snapshot["people"].append({
                "name": f"p{i}",
                "ledger_total_pnl_vnd": value,
                "rows": [[], [], [], [], [], ["2026-07-19", "", "", "", pnl_cell]],
            })
        operations = [
            {"kind": "UPDATE_PERSONAL_PNL_IF_BLANK", "name": "p1",
             "row": 6, "pnl_vnd": 100_000},
            {"kind": "UPDATE_PERSONAL_PNL_IF_BLANK", "name": "p4",
             "row": 6, "pnl_vnd": 285_000},
        ]
        advanced = fusion4.reconcile_group_actual(
            state, date(2026, 7, 19), snapshot, operations
        )
        self.assertEqual(advanced["group_actual_pnl"]["net_profit_vnd"], 18_131_000)

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
