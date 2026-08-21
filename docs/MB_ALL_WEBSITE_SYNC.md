# MB ALL → Website daily sync

Canonical website source: `XSMB_Source_2024_2026_MB_v1.3`.

Production row source: `MAX2_Daily_Plan` with `Method_ID = MAX2_V1_R4268_P0072_HR60`.

Rules:

1. Target date `T` must have data lock exactly `T-1`.
2. `Source_Status` must start with `PASS_27_LOCKED`.
3. `Run_Status` must be `PUBLISHED_PROSPECTIVE`.
4. `Outcome_Known_At_Selection` must be false.
5. Current Production codes are never written to public JSON.
6. Public method cards are recomputed from `MB_History_27` through `T-1`.
7. Completed-history proof is extended only after a draw is settled; MAX2 official live history starts 19/08/2026.
8. Payment delivery remains private. The owner receives the approval email; after approval the browser opens the private Production output for that report date.
9. During the legacy Apps Script payload transition, `Paid_Report` may carry the same MAX2 pair in both legacy pair slots. `site-v2/config.js` collapses the duplicate to one Production pair for the customer.
10. If any invariant fails, the sync workflow exits without publishing a false current-day snapshot.

Automation: `.github/workflows/sync-max2-website.yml` runs hourly from 07:07 through 00:07 Vietnam time and can also be run manually. When a new valid daily review is found it updates the public snapshot and commits it, which triggers the existing GitHub Pages deployment.
