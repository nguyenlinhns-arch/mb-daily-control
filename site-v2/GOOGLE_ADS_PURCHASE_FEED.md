# Google Ads approved-purchase feed

This project treats only an **approved payment** as the final purchase conversion.

## Ground truth

The private order spreadsheet remains the source of truth. The public website must not contain payment secrets or paid 4SO outputs.

Two private spreadsheet tabs are used for Google Ads measurement:

- `Google_Ads_Conversions`: diagnostic projection of approved orders. It extracts `gclid`, `gbraid`, and `wbraid` from the stored attribution/page URL and exposes approved time, value, currency, order id, source attribution, and readiness.
- `Google_Ads_Ready`: import-ready rows only. It includes an order only when the order is approved and at least one Google click identifier is present.

Canonical conversion label prepared for a Data Manager connection:

`LMB Purchase Approved`

Canonical value/currency for the current daily product:

- value: `30000`
- currency: `VND`
- transaction/order id: existing `order_code`
- conversion time: `approved_at` in `Asia/Ho_Chi_Minh` with explicit `+07:00`

## Required behavior

1. The website records Google click identifiers in attribution when they are present on the landing URL.
2. A customer payment claim is not a purchase.
3. `Purchase` becomes eligible only after the backend/order ledger status is `approved`.
4. Historical/direct/Facebook/Zalo orders without a Google click identifier must not enter `Google_Ads_Ready`.
5. Duplicate protection uses `order_code` as Order ID / transaction id.
6. Do not put access tokens, Google Ads credentials, bank credentials, or Apps Script secrets in this repository.

## Google Ads connection

Use Google Ads Data Manager with Google Sheets as the source and map the columns in `Google_Ads_Ready` to the corresponding conversion fields. The connection/action in Google Ads must use the same conversion label if the conversion-name field is mapped.

This feed is supplemental to the browser-side GA4 purchase event. It exists so an approved purchase can still be attributed after the buyer closes the browser before the approval completes.
