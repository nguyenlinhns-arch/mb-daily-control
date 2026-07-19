from __future__ import annotations

from datetime import date
import unittest

from scripts import v32_daily as v32


def engine_plan(codes, points):
    return {
        "source_end": "2026-07-16",
        "plan": {
            "date": "2026-07-17",
            "codes": codes,
            "N": len(codes),
            "points": points,
            "points_per_code": next(iter(points.values()), 30),
            "capital_vnd": len(codes) * next(iter(points.values()), 30) * 23_000,
            "outcome_known_at_selection": False,
            "parent_codes": codes,
            "base_codes": codes[:-4] if len(codes) > 4 else codes,
            "overlay": {
                "rule": "EMP_OVERDUE_RECENT_N_LE8_M0.75",
                "eligible_width": len(codes) <= 8,
                "proposed_remove": codes[-1] if codes else "00",
                "proposed_add": "80",
                "normalized_margin": 0.0,
                "threshold": 0.75,
                "active": False,
            },
        },
    }


class V32DailyTests(unittest.TestCase):
    def test_settlement_16_july_exact(self):
        plan = {
            "target_date": "2026-07-16",
            "codes": ["10", "13", "31", "41", "51", "91", "92"],
            "points_by_code": {code: 25 for code in (
                "10", "13", "31", "41", "51", "91", "92"
            )},
            "points_per_code": 25,
        }
        result = v32.settle(plan, ["00"] * 27)
        self.assertEqual(result["capital_vnd"], 4_025_000)
        self.assertEqual(result["payout_vnd"], 0)
        self.assertEqual(result["pnl_vnd"], -4_025_000)
        self.assertFalse(result["hit_day"])

    def test_make_plan_rejects_empty_too_wide_and_mixed_points(self):
        with self.assertRaises(v32.PipelineError):
            v32.make_plan(engine_plan([], {}), date(2026, 7, 17), date(2026, 7, 16))
        codes = [f"{i:02d}" for i in range(13)]
        with self.assertRaises(v32.PipelineError):
            v32.make_plan(
                engine_plan(codes, {code: 20 for code in codes}),
                date(2026, 7, 17), date(2026, 7, 16),
            )
        with self.assertRaises(v32.PipelineError):
            v32.make_plan(
                engine_plan(["01", "13"], {"01": 30, "13": -30}),
                date(2026, 7, 17), date(2026, 7, 16),
            )

    def test_personal_retry_is_stable_after_matching_pnl_write(self):
        entries = [
            {"name": name, "sheet_name": name, "rows": []}
            for name in v32.PEOPLE
        ]
        entries[2]["rows"] = [
            [], [], [], [], [],
            ["2026-07-16", "AI", "13;31", 40, None, None, None, "manual"],
        ]
        snapshot = {"people": entries, "draw": ["00"] * 27}
        before, blocked = v32.personal_operations(
            snapshot, date(2026, 7, 16), snapshot["draw"]
        )
        self.assertFalse(blocked)
        settled_before = [
            operation for operation in before
            if operation["kind"] == "UPDATE_PERSONAL_PNL_IF_BLANK"
        ]
        self.assertEqual(len(settled_before), 1)
        self.assertEqual(settled_before[0]["pnl_vnd"], -920_000)
        snapshot["people"][2]["rows"][5][4] = -920_000
        after, blocked = v32.personal_operations(
            snapshot, date(2026, 7, 16), snapshot["draw"]
        )
        self.assertFalse(blocked)
        self.assertEqual(before, after)

    def test_personal_fusion4_preserves_ranked_50_50_50_30_stakes(self):
        entries = [
            {"name": name, "sheet_name": name, "rows": []}
            for name in v32.PEOPLE
        ]
        entries[0]["rows"] = [[
            "2026-07-19", "MB FUSION4–180", "59, 78, 06, 10", 180,
            None, None, None, "USER_CONFIRMED_PERSONAL_ORDER",
        ]]
        snapshot = {"people": entries}
        operations, blocked = v32.personal_operations(
            snapshot, date(2026, 7, 19), ["10"] + ["00"] * 26
        )
        self.assertFalse(blocked)
        settled = [
            operation for operation in operations
            if operation["kind"] == "UPDATE_PERSONAL_PNL_IF_BLANK"
        ]
        self.assertEqual(len(settled), 1)
        self.assertEqual(
            settled[0]["points_by_code"],
            {"59": 50, "78": 50, "06": 50, "10": 30},
        )
        self.assertIsNone(settled[0]["points_per_code"])
        self.assertEqual(settled[0]["pnl_vnd"], -1_740_000)
        self.assertIn("59×50, 78×50, 06×50, 10×30", settled[0]["note"])

    def test_personal_conflict_blocks(self):
        snapshot = {
            "people": [
                {"name": name, "sheet_name": name, "rows": (
                    [["2026-07-16", "AI", "13;31", 40, 123]]
                    if name == "p3" else []
                )}
                for name in v32.PEOPLE
            ]
        }
        operations, blocked = v32.personal_operations(
            snapshot, date(2026, 7, 16), ["00"] * 27
        )
        self.assertFalse([
            operation for operation in operations
            if operation["kind"] == "UPDATE_PERSONAL_PNL_IF_BLANK"
        ])
        self.assertEqual(blocked[0]["reason"], "EXISTING_PNL_CONFLICT")

    def test_month_rollover_starts_clean_equity(self):
        empty = {
            "sessions": 0, "hit_days": 0, "profit_days": 0,
            "capital_vnd": 0, "payout_vnd": 0, "net_profit_vnd": 0,
            "equity_current_vnd": 0, "equity_peak_vnd": 0,
            "max_drawdown_vnd": 0, "gross_profit_vnd": 0,
            "gross_loss_vnd": 0,
        }
        settlement = {
            "hit_day": False, "profit_day": False,
            "capital_vnd": 690_000, "payout_vnd": 0, "pnl_vnd": -690_000,
        }
        updated = v32.update_period(empty, settlement)
        self.assertEqual(updated["sessions"], 1)
        self.assertEqual(updated["equity_current_vnd"], -690_000)
        self.assertEqual(updated["max_drawdown_vnd"], -690_000)
        self.assertEqual(updated["profit_factor"], 0.0)

    def test_month_and_year_rollover_in_state(self):
        state = {
            "settled_through": "2026-07-30",
            "current_month_id": "2026-07",
            "current_month": v32.empty_period(),
            "full": v32.empty_period(),
        }
        def loss(day):
            return {
                "date": day, "hit_day": False, "profit_day": False,
                "capital_vnd": 690_000, "payout_vnd": 0, "pnl_vnd": -690_000,
            }
        state = v32.advance_state(state, loss("2026-07-31"))
        self.assertEqual(state["current_month_id"], "2026-07")
        self.assertEqual(state["current_month"]["sessions"], 1)
        state = v32.advance_state(state, loss("2026-08-01"))
        self.assertEqual(state["current_month_id"], "2026-08")
        self.assertEqual(state["current_month"]["sessions"], 1)
        state = v32.advance_state(state, loss("2026-12-31"))
        self.assertEqual(state["current_month_id"], "2026-12")
        state = v32.advance_state(state, loss("2027-01-01"))
        self.assertEqual(state["current_month_id"], "2027-01")
        self.assertEqual(state["current_month"]["sessions"], 1)

    def test_full_pf_remains_unknown_without_seed_gross(self):
        period = v32.empty_period()
        period.pop("gross_profit_vnd")
        period.pop("gross_loss_vnd")
        updated = v32.update_period(period, {
            "hit_day": True, "profit_day": True,
            "capital_vnd": 690_000, "payout_vnd": 2_400_000,
            "pnl_vnd": 1_710_000,
        })
        self.assertIsNone(updated["profit_factor"])
        self.assertNotIn("gross_profit_vnd", updated)

    def test_strict_personal_parsers_reject_ambiguous_values(self):
        for value in ("123", "13,13", "13x31", "-1", "13/31"):
            self.assertEqual(v32.parse_person_codes(value), [])
        self.assertEqual(v32.parse_person_codes("13;31"), ["13", "31"])
        self.assertEqual(v32.parse_person_codes(31.13), ["31", "13"])
        for value in ("30,50", "50x2", "30 điểm ×2", -30, 30.5):
            self.assertIsNone(v32.parse_total_points(value))
        self.assertEqual(v32.parse_total_points("40"), 40)

    def test_sheet_payload_is_deterministic_across_retry(self):
        plan = {
            "target_date": "2026-07-17", "data_lock_date": "2026-07-16",
            "status": "LOCKED_WAITING_RESULT", "codes": ["01"],
            "points_by_code": {"01": 30}, "total_points": 30,
            "total_capital_vnd": 690_000,
        }
        settlement = {
            "date": "2026-07-16", "status": "SETTLED_VERIFIED_27_OF_27",
            "codes": ["13"], "points_by_code": {"13": 30},
            "total_points": 30, "capital_vnd": 690_000,
            "payout_vnd": 0, "pnl_vnd": -690_000, "hit_units": 0,
        }
        snapshot = {
            "draw": ["00"] * 27,
            "people": [
                {"name": key, "sheet_name": f"tab-{key}", "rows": []}
                for key in v32.PEOPLE
            ],
        }
        first = v32.build_sheet_payload(
            date(2026, 7, 17), plan, settlement, snapshot, "input"
        )
        second = v32.build_sheet_payload(
            date(2026, 7, 17), plan, settlement, snapshot, "input"
        )
        self.assertEqual(first["payload_hash"], second["payload_hash"])
        self.assertEqual(first["operations"], second["operations"])


if __name__ == "__main__":
    unittest.main()
