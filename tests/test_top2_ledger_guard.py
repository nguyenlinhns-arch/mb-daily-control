import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "chatgpt_app_v1"))

from mb_engine.ledger_guard import (
    assert_route_authority,
    google_cells,
    settle,
    signal_window,
    validate_draw_tails,
    validate_forecast,
    validate_run,
)


class LedgerGuardTests(unittest.TestCase):
    def base(self, **kw):
        row = dict(
            method_id="CUR-014",
            target_date="2026-09-07",
            data_lock="2026-09-06",
            action="A2",
            codes=["09", "00"],
            evidence="serialized path + literal executor anchor",
        )
        row.update(kw)
        return row

    def test_accept_two_strings(self): self.assertEqual(validate_forecast(self.base()).codes, ("09", "00"))
    def test_reject_float_scalar(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(codes=5.5))
    def test_reject_text_pair_scalar(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(codes="05,50"))
    def test_reject_float_list(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(codes=[5.0, 50.0]))
    def test_reject_short_code(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(codes=["5", "50"]))
    def test_reject_duplicate(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(codes=["05", "05"]))
    def test_reject_action_mismatch(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(action="A1"))
    def test_reject_same_day_lock(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(data_lock="2026-09-07"))
    def test_reject_future_lock(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(data_lock="2026-09-08"))
    def test_reject_missing_action(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(action="MISSING"))
    def test_invalid_empty(self):
        self.assertEqual(validate_forecast(self.base(action="RUN_INVALID_NO_BET", codes=[])).codes, ())
    def test_invalid_cannot_carry_code(self):
        with self.assertRaises(ValueError): validate_forecast(self.base(action="RUN_INVALID_NO_BET"))
    def test_writer_uses_string(self):
        cells = google_cells(validate_forecast(self.base()))
        self.assertEqual(cells[4]["userEnteredValue"], {"stringValue": "09"})
        self.assertEqual(cells[5]["userEnteredValue"], {"stringValue": "00"})
    def test_multi_occurrence(self):
        s = settle(validate_forecast(self.base()), date(2026, 9, 7), ["09", "09", "00"] + ["10"] * 24)
        self.assertEqual((s["occurrences"], s["pl"]), (3, 2445000))
    def test_a0_not_loss(self):
        s = settle(validate_forecast(self.base(action="A0", codes=[])), date(2026, 9, 7), ["10"] * 27)
        self.assertEqual((s["outcome"], s["signal"], s["pl"]), ("A0", False, 0))
    def test_invalid_not_zero(self):
        s = settle(validate_forecast(self.base(action="RUN_INVALID_NO_BET", codes=[])), date(2026, 9, 7), ["10"] * 27)
        self.assertIsNone(s["pl"])
    def test_result_count(self):
        with self.assertRaises(ValueError): settle(validate_forecast(self.base()), date(2026, 9, 7), ["10"] * 26)
    def test_result_date(self):
        with self.assertRaises(ValueError): settle(validate_forecast(self.base()), date(2026, 9, 8), ["10"] * 27)
    def test_window_skips_a0(self):
        r = signal_window([dict(pl=-1, signal=True), dict(pl=0, signal=False, outcome="A0"), dict(pl=3, signal=True)], 2)
        self.assertTrue(r["certified"])
        self.assertEqual(r["observed_wins"], 1)
    def test_unknown_window_blocks_certification(self):
        r = signal_window([dict(pl=-1, signal=True), dict(pl=None, signal=False, outcome="UNKNOWN"), dict(pl=3, signal=True)], 2)
        self.assertFalse(r["certified"])
        self.assertEqual(r["unknown_sessions"], 1)
    def test_unknown_before_window_does_not_invalidate(self):
        r = signal_window([dict(pl=None, signal=False), dict(pl=-1, signal=True), dict(pl=3, signal=True)], 2)
        self.assertTrue(r["certified"])
    def test_zero_signal_sample_not_certified(self):
        self.assertFalse(signal_window([dict(pl=0, signal=False, outcome="A0")], 3)["certified"])

    def test_exact_t_minus_1(self):
        with self.assertRaises(ValueError):
            validate_forecast(self.base(target_date="2026-09-07", data_lock="2026-09-05"), require_exact_t_minus_1=True)

    def test_run_requires_67(self):
        with self.assertRaises(ValueError):
            validate_run([self.base()], target_date="2026-09-07", data_lock="2026-09-06")

    def test_run_method_order(self):
        rows, ids = [], []
        for i in range(67):
            mid = f"CUR-{i + 1:03d}"
            ids.append(mid)
            rows.append(dict(method_id=mid, target_date="2026-09-07", data_lock="2026-09-06", action="A0", codes=[], evidence="x"))
        validate_run(rows, target_date="2026-09-07", data_lock="2026-09-06", expected_method_ids=ids)
        bad = ids.copy()
        bad[0], bad[1] = bad[1], bad[0]
        with self.assertRaises(ValueError):
            validate_run(rows, target_date="2026-09-07", data_lock="2026-09-06", expected_method_ids=bad)

    def test_draw_preserves_00(self):
        self.assertEqual(validate_draw_tails(["00"] + ["10"] * 26)[0], "00")

    def test_draw_rejects_ints(self):
        with self.assertRaises(ValueError): validate_draw_tails([0] + ["10"] * 26)

    def test_route_blocks_legacy_after_17(self):
        with self.assertRaises(ValueError):
            assert_route_authority(target_date="2026-09-18", engine_or_policy="ALL67_NO_META")

    def test_route_allows_historical_legacy(self):
        assert_route_authority(target_date="2026-09-16", engine_or_policy="FUSION67")

    def test_route_allows_v41(self):
        assert_route_authority(target_date="2026-09-18", engine_or_policy="V4.1 ROLE-CORE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
