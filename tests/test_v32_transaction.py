from __future__ import annotations

from argparse import Namespace
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import v32_daily as v32


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.data = self.base / "seed-data"
        self.plan_dir = self.data / "plans"
        self.tx_dir = self.data / "transactions"
        self.plan_dir.mkdir(parents=True)
        self.state_file = self.data / "state.json"
        previous_plan = {
            "target_date": "2026-07-01", "data_lock_date": "2026-06-30",
            "status": "LOCKED_WAITING_RESULT", "codes": ["01"],
            "number_of_codes": 1, "points_per_code": 30,
            "points_by_code": {"01": 30}, "total_points": 30,
            "cost_per_point_vnd": 23_000, "total_capital_vnd": 690_000,
            "maximum_loss_vnd": 690_000, "core_100_enabled": False,
            "other_50_enabled": False, "outcome_known_at_selection": False,
        }
        (self.plan_dir / "2026-07-01.json").write_text(
            json.dumps(previous_plan), encoding="utf-8"
        )
        empty = v32.empty_period()
        state = {
            "settled_through": "2026-06-30", "current_month_id": "2026-06",
            "current_month": empty, "full": empty,
        }
        self.state_file.write_text(json.dumps(state), encoding="utf-8")
        self.snapshot = self.base / "snapshot.json"
        self.snapshot.write_text(json.dumps({
            "source_sheet_id": "source", "pnl_sheet_id": "private-pnl",
            "source_crosscheck": "MATCHED",
            "people": [
                {"name": key, "sheet_name": f"private-{key}", "rows": []}
                for key in v32.PEOPLE
            ],
        }), encoding="utf-8")
        self.engine = {
            "source_end": "2026-07-01", "causality": {"ok": True},
            "plan": {
                "date": "2026-07-02", "codes": ["02"], "N": 1,
                "points": {"02": 30}, "points_per_code": 30,
                "capital_vnd": 690_000, "outcome_known_at_selection": False,
                "parent_codes": ["02"], "base_codes": ["02"],
                "overlay": {
                    "rule": "LOCKED", "eligible_width": True,
                    "proposed_remove": "02", "proposed_add": "80",
                    "normalized_margin": 0.0, "threshold": 0.75,
                    "active": False,
                },
            },
        }

    def tearDown(self):
        self.temp.cleanup()

    def patches(self):
        return (
            patch.object(v32, "STATE_FILE", self.state_file),
            patch.object(v32, "PLAN_DIR", self.plan_dir),
            patch.object(v32, "TX_DIR", self.tx_dir),
            patch.object(v32, "load_history", return_value={date(2026, 7, 1): ["00"] * 27}),
            patch.object(v32, "engine_manifest_hash", return_value="engine-hash"),
            patch.object(v32, "run_engine", return_value=self.engine),
        )

    def prepare(self, output: Path):
        args = Namespace(
            target_date="2026-07-02", source_xlsx=str(self.base / "source.xlsx"),
            pnl_snapshot=str(self.snapshot), output=str(output),
        )
        p = self.patches()
        with p[0], p[1], p[2], p[3], p[4], p[5]:
            v32.prepare(args)

    def test_prepare_retry_and_finalize_receipt_contract(self):
        first = self.base / "first"
        second = self.base / "second"
        self.prepare(first)
        self.prepare(second)
        one = v32.read_json(first / "private" / "sheets_payload.json")
        two = v32.read_json(second / "private" / "sheets_payload.json")
        self.assertEqual(one["payload_hash"], two["payload_hash"])
        self.assertEqual(one["operations"], two["operations"])
        prepared = v32.read_json(first / "prepared.json")
        bad_receipt = self.base / "bad.json"
        bad_receipt.write_text(json.dumps({
            "status": "APPLIED_READBACK_VERIFIED",
            "target_date": prepared["target_date"], "input_hash": prepared["input_hash"],
            "payload_hash": prepared["sheets_payload_hash"],
            "operation_ids": list(reversed(prepared["sheets_operation_ids"])),
        }), encoding="utf-8")
        root = self.base / "public-root"
        root.mkdir()
        with patch.object(v32, "ROOT", root):
            with self.assertRaises(v32.PipelineError):
                v32.finalize(Namespace(output=str(first), receipt=str(bad_receipt)))
        self.assertFalse((root / "data" / "current.json").exists())

        good_receipt = self.base / "good.json"
        good_receipt.write_text(json.dumps({
            "status": "APPLIED_READBACK_VERIFIED",
            "target_date": prepared["target_date"], "input_hash": prepared["input_hash"],
            "payload_hash": prepared["sheets_payload_hash"],
            "operation_ids": prepared["sheets_operation_ids"],
        }), encoding="utf-8")
        with patch.object(v32, "ROOT", root):
            v32.finalize(Namespace(output=str(first), receipt=str(good_receipt)))
            v32.finalize(Namespace(output=str(first), receipt=str(good_receipt)))
        current = v32.read_json(root / "data" / "current.json")
        transaction = v32.read_json(root / "data" / "v32-transactions" / "2026-07-02.json")
        self.assertEqual(
            current["automation"]["status"],
            "SHEETS_APPLIED_READBACK_VERIFIED_READY_TO_PUBLISH",
        )
        self.assertEqual(transaction["status"], "COMMITTED")
        self.assertIn("final_public_json_hash", transaction)


if __name__ == "__main__":
    unittest.main()
