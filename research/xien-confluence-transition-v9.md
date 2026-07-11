# Xiên 2 Confluence & Previous-Draw Transition Audit V9

**Run ID:** `RPT_MB_20260711_XIEN_X2_CONFLUENCE_TRANSITION_V9`  
**Data locked through:** 2026-07-10  
**Source:** `XSMB_Source_2024_2026_MB_v1.3`  
**Protocol:** warm-up 2020; train 2021–2023; validation 2024; OOS 2025–2026; no look-ahead.

**Reproducibility note:** the deterministic X2 reconstruction reproduced 128 of 130 recorded X2 signals in the 2024–2026 audit window. The two remaining discrepancies appear to come from historical tie/feature definitions. The results below are therefore a strong research reconstruction and are kept Shadow pending forward verification, not claimed as a mathematically exact replay of every historical X2 row.

## 1. Promoted Xiên method: XIEN2_X2_CONFLUENCE_V1

The reconstructed rank-1 pair from X2 Fusion is used only after X2 independently passes Core or Balanced. The Xiên overlay then requires:

- prior-draw `repeat2_count <= 4`;
- pair co-hit count over the previous 21 draws from 1 to 3;
- pair co-hit count over the previous 60 draws from 5 to 6;
- one pair per day; no rank-2 fallback.

Economics: 100,000 VND per pair; net +1,500,000 VND when both legs hit, -100,000 VND otherwise.

| Split | Orders | Wins | WR | P/L | Max DD | Longest loss |
|---|---:|---:|---:|---:|---:|---:|
| Train 2021–2023 | 35 | 5 | 14.29% | +4.50M | -1.40M | 14 |
| Validation 2024 | 15 | 4 | 26.67% | +4.90M | -0.50M | 5 |
| OOS 2025–2026 | 33 | 6 | 18.18% | +6.30M | -1.20M | 12 |
| Full | 83 | 15 | 18.07% | +15.70M | -1.40M | 14 |

## 2. Comparison with the former primary Xiên method

The former independent `XIEN2_HOT90_PAIR21_V2` produced 109 orders, 15 wins, 13.76% WR, +13.10M P/L, -1.80M MaxDD and an 18-order longest loss streak.

The new X2-confluence reconstruction has the same 15 wins with 26 fewer orders, improves WR by 4.31 percentage points, adds 2.60M P/L, improves MaxDD by 0.40M and shortens the longest losing streak by four orders. It therefore replaces HOT90 as the preferred Xiên Shadow research method. HOT90 remains a secondary benchmark only.

## 3. Current state for 11/07/2026

The current X2 rank-1 pair is `32-23`.

- X2 itself fails because the cover leg 23 has `H21=3`, below the minimum 5.
- The Xiên overlay is already in range: `PairCount21=2`, `PairCount60=6`, prior `repeat2_count=1`.
- Overall Xiên decision remains A0 because the source X2 signal has not passed.
- Earliest theoretical date: 16/07/2026, conditional on the pair remaining rank 1 and all X2 plus overlay gates passing after recalculation.

## 4. X3 internal Xiên overlay

A secondary Quality Shadow was tested: X3 Growth must pass, and the maximum PairCount60 among its three internal pairs must be between 8 and 9. All three pairs are paper-tracked only. The training segment uses a reconstructed X3 generator; validation and OOS use the audited X3 Growth baskets.

| Split | Days | Win days | WR | P/L | Max DD |
|---|---:|---:|---:|---:|---:|
| Train | 71 | 14 | 19.72% | +7.50M | -4.80M |
| Validation | 22 | 5 | 22.73% | +1.40M | -2.10M |
| OOS | 38 | 11 | 28.95% | +9.40M | -2.10M |

The OOS profile is attractive, but drawdown is materially higher than X2-confluence. It remains secondary research and is not the primary Xiên engine.

## 5. A1 and cross-method pair tests

A1 main–reverse Xiên produced 157 pairs, 15 wins, 9.55% WR and +8.30M P/L. It is positive but materially weaker than X2-confluence and remains research only.

Cross-method pairs had only five validation dates. OOS had 58 dates, six wins, 10.34% WR and +3.80M P/L. The validation sample is too small for promotion.

## 6. Previous-draw to next-draw transition audit

Ten thousand exact ordered number edges were tested, together with same-number repeat, reverse-number effects, pair-state transitions, Head/Tail Markov tables and logistic models.

- Train-to-validation edge-lift correlation: 0.00445.
- Train-to-OOS edge-lift correlation: -0.0242.
- Top-decile train-edge realized lift: 0.990 on validation and 0.999 on OOS.
- Logistic transition model AUC: 0.497 on validation and 0.493 on OOS.
- When both pair legs appeared yesterday, next-day joint rate was 5.70% in train, 5.42% in validation and 5.32% in OOS, so the apparent effect reversed.

Conclusion: a fixed table of “number yesterday pulls number tomorrow,” reverse-number transitions or Head/Tail Markov transitions is not stable enough for direct selection or staking.

## 7. Approved uses of the previous draw

The previous draw is still useful as structural context:

- `repeat2_count`;
- maximum multiplicity (`maxfreq`);
- rolling pair co-hit counts over 21, 60 and 180 draws.

These features may qualify or veto a method. They must not override A1, X2 or X3, create a new real order, or increase stake by themselves.

## 8. Forward lock

The promoted Xiên method remains Shadow. Review for real money only after at least 30 new prospective signals with frozen parameters, WR at least 14%, positive P/L, MaxDD no worse than -1.80M and longest loss streak no more than 18. The two unresolved historical reconstruction mismatches must also be audited before any real-money promotion.
