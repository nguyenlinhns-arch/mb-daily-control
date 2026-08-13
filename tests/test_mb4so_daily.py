from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mb4so_daily import (  # noqa: E402
    normalize_history,
    rank_pct_average,
    score_reverse_pairs,
    settlement,
)
from build_public_snapshot import load_history  # noqa: E402


class FourSoDailyTests(unittest.TestCase):
    def test_average_percentile_rank(self) -> None:
        self.assertEqual(rank_pct_average([1, 1, 3]), [0.5, 0.5, 1.0])

    def test_settlement_fixed_50(self) -> None:
        result = settlement(
            ["06", "60", "38", "83"],
            ["60", "60", *(["00"] * 25)],
        )
        self.assertEqual(result["total_hits"], 2)
        self.assertEqual(result["capital_vnd"], 4_600_000)
        self.assertEqual(result["payout_vnd"], 8_000_000)
        self.assertEqual(result["pnl_vnd"], 3_400_000)

    def test_known_canonical_pair_order(self) -> None:
        rows = normalize_history(load_history()["rows"])
        locked = [row for row in rows if row[0] <= "2026-08-07"]
        ranked = score_reverse_pairs(locked)
        self.assertEqual(
            [item.pair for item in ranked[:4]],
            ["19-91", "06-60", "36-63", "05-50"],
        )
        self.assertEqual(len(ranked), 45)


if __name__ == "__main__":
    unittest.main()
