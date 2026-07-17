from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import google_sheets_bridge as bridge


class SheetsBridgeTests(unittest.TestCase):
    def test_private_config_resolves_pnl_sheet_id(self):
        rows = [
            ["Key", "Value"],
            ["PNL_SHEET_ID", "private_sheet_id_123456789"],
            ["CONFIG_VERSION", "MB_V32_PRIVATE_CONFIG_V1"],
        ]
        with patch.dict(bridge.os.environ, {}, clear=True), patch.object(
            bridge, "get_values", return_value=rows
        ) as reader, patch.object(
            bridge, "PNL_SHEET_ID_SHA256",
            bridge.sha256(b"private_sheet_id_123456789").hexdigest(),
        ):
            value = bridge.resolve_pnl_sheet_id(object(), "source-id")
        self.assertEqual(value, "private_sheet_id_123456789")
        self.assertIn("V32_Private_Config", reader.call_args.args[2])

    def test_private_config_duplicate_key_blocks(self):
        rows = [
            ["PNL_SHEET_ID", "private_sheet_id_123456789"],
            ["PNL_SHEET_ID", "other_private_sheet_987654321"],
            ["CONFIG_VERSION", "MB_V32_PRIVATE_CONFIG_V1"],
        ]
        with patch.dict(bridge.os.environ, {}, clear=True), patch.object(
            bridge, "get_values", return_value=rows
        ):
            with self.assertRaises(bridge.BridgeError):
                bridge.resolve_pnl_sheet_id(object(), "source-id")

    def test_private_config_wrong_identity_blocks(self):
        rows = [
            ["PNL_SHEET_ID", "wrong_private_sheet_123456789"],
            ["CONFIG_VERSION", "MB_V32_PRIVATE_CONFIG_V1"],
        ]
        with patch.dict(bridge.os.environ, {}, clear=True), patch.object(
            bridge, "get_values", return_value=rows
        ):
            with self.assertRaises(bridge.BridgeError):
                bridge.resolve_pnl_sheet_id(object(), "source-id")

    def test_source_operation_retry_does_not_append_twice(self):
        record = {
            "date": "2026-07-17", "status": "LOCKED_WAITING_RESULT",
            "method": "V32", "codes": ["01"], "points_by_code": {"01": 30},
            "total_points": 30, "capital_vnd": 690_000,
            "source_date": "2026-07-16", "input_hash": "input",
            "created_at": "2026-07-17T06:00:00+07:00",
        }
        operation = {
            "kind": "UPSERT_SOURCE_PLAN", "operation_id": "op-1",
            "row_hash": bridge.digest(record), "record": record,
        }
        rows = [["date", "status"]]
        appends = []

        def fake_get(*_args, **_kwargs):
            return rows

        def fake_append(_service, _sid, _tab, row):
            appends.append(row)
            rows.append(row)

        with patch.object(bridge, "get_values", side_effect=fake_get), patch.object(
            bridge, "append_row", side_effect=fake_append
        ):
            bridge.apply_source_operation(object(), "source", operation)
            bridge.apply_source_operation(object(), "source", operation)
        self.assertEqual(len(appends), 1)

    def test_personal_retry_preserves_note_and_marker_once(self):
        operation = {
            "sheet_name": "private-tab-p3", "row": 6, "pnl_vnd": -920_000,
            "expected_a_to_d_hash": bridge.digest(
                ["2026-07-16", "AI", "13;31", 40]
            ),
            "operation_id": "abcdef0123456789", "note": "auto settlement",
        }
        row = ["2026-07-16", "AI", "13;31", 40, None, None, None, "manual"]

        def fake_get(*_args, **_kwargs):
            return [list(row)]

        def fake_update(_service, _sid, range_name, values):
            if "!E6:E6" in range_name:
                row[4] = values[0][0]
            elif "!H6:H6" in range_name:
                row[7] = values[0][0]

        with patch.object(bridge, "get_values", side_effect=fake_get), patch.object(
            bridge, "update_range", side_effect=fake_update
        ):
            bridge.apply_personal_operation(object(), "pnl", operation)
            bridge.apply_personal_operation(object(), "pnl", operation)
        self.assertEqual(row[4], -920_000)
        self.assertTrue(row[7].startswith("manual | "))
        self.assertEqual(row[7].count("[V32:abcdef012345]"), 1)

    def test_parse_serial_date(self):
        self.assertEqual(bridge.parse_date(46219), "2026-07-16")


if __name__ == "__main__":
    unittest.main()
