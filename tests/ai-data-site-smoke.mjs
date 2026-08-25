import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const repoRoot = process.cwd();
const siteRoot = resolve(repoRoot, "site-v2");
const readSite = (name) => readFile(resolve(siteRoot, name), "utf8");
const readRepo = (name) => readFile(resolve(repoRoot, name), "utf8");

const [
  index,
  styles,
  app,
  config,
  approvalBackend,
  legal,
  sample,
  conversionAccent,
  conversionV2,
  checkoutEnhance,
  checkoutEntry,
  workflow,
  publicProofRaw,
  yesterdayProofRaw,
  sourceAccessRaw,
  paidReadyRaw,
  applyConversionV2,
  simplifyPurchaseCta
] = await Promise.all([
  readSite("index.html"),
  readSite("styles.css"),
  readSite("app.js"),
  readSite("config.js"),
  readSite("approval-backend.gs"),
  readSite("legal.html"),
  readSite("mau-bao-cao.html"),
  readSite("conversion-accent.css"),
  readSite("conversion-v2.css"),
  readSite("checkout-enhance.js"),
  readSite("checkout-entry.js"),
  readRepo(".github/workflows/pages.yml"),
  readRepo("data/public-historical-proof.json"),
  readRepo("ai-methods/yesterday-proof.json"),
  readRepo("data/source-access.json"),
  readRepo("data/paid-report-ready.json"),
  readRepo("scripts/apply_conversion_v2.py"),
  readRepo("scripts/simplify_purchase_cta.py")
]);

const publicProof = JSON.parse(publicProofRaw);
const yesterdayProof = JSON.parse(yesterdayProofRaw);
const sourceAccess = JSON.parse(sourceAccessRaw);
const paidReady = JSON.parse(paidReadyRaw);

for (const file of [
  "styles.css",
  "app.js",
  "config.js",
  "mau-bao-cao.html",
  "legal.html",
  "robots.txt",
  "sitemap.xml",
  "404.html",
  "favicon.svg",
  "conversion-accent.css",
  "conversion-v2.css",
  "checkout-enhance.js",
  "checkout-entry.js"
]) {
  assert.ok(await readSite(file), `${file} must not be empty`);
}
assert.ok((await stat(resolve(siteRoot, "og.png"))).size > 100_000, "og.png must be a real social preview image");

const isoNextDay = (iso) => {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().slice(0, 10);
};
const isoPreviousDay = (iso) => {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - 1);
  return date.toISOString().slice(0, 10);
};
const isoDistanceDays = (start, end) => (
  (Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / 86_400_000
);

// Historical validation may stay frozen as an audited 30-day benchmark, while
// the visible current-month proof must advance through the latest completed draw.
assert.equal(publicProof.schema_version, "MB_PUBLIC_HISTORICAL_PROOF_V2_PRODUCTION_AWARE");
assert.equal(publicProof.status, "COMPLETED_DATES_ONLY");
assert.equal(publicProof.validation.total_days, 30);
assert.equal(isoDistanceDays(publicProof.validation.window_start, publicProof.validation.window_end), 29);
assert.ok(publicProof.validation.window_end <= sourceAccess.history_end);
assert.equal(
  Math.round(publicProof.validation.hit_days * 100 / publicProof.validation.total_days),
  publicProof.validation.rate_pct
);

assert.equal(publicProof.recent_period.period_end, sourceAccess.history_end);
assert.equal(
  isoDistanceDays(publicProof.recent_period.period_start, publicProof.recent_period.period_end) + 1,
  publicProof.recent_period.total_days
);
assert.equal(publicProof.recent_period.days.length, publicProof.recent_period.total_days);
assert.equal(
  publicProof.recent_period.days.filter((day) => day.observed.length > 0).length,
  publicProof.recent_period.hit_days
);

for (let index = 0; index < publicProof.recent_period.days.length; index += 1) {
  const day = publicProof.recent_period.days[index];
  assert.equal(day.date, new Date(Date.parse(`${publicProof.recent_period.period_start}T00:00:00Z`) + index * 86_400_000).toISOString().slice(0, 10));
  assert.ok([2, 4].includes(day.outputs.length), `${day.date} must contain the official Production output count`);
  assert.equal(new Set(day.outputs).size, day.outputs.length, `${day.date} report numbers must be unique`);
  assert.ok(day.outputs.every((value) => /^\d{2}$/.test(value)), `${day.date} contains an invalid report number`);
  if (day.date >= "2026-08-19") assert.equal(day.outputs.length, 2, `${day.date} must use MAX2 Production output`);
  assert.equal(day.status, day.observed.length ? "hit" : "miss");
}

assert.equal(yesterdayProof.schema_version, "MB_PUBLIC_YESTERDAY_PROOF_V3_PRODUCTION_AWARE");
assert.equal(yesterdayProof.date, sourceAccess.history_end);
assert.deepEqual(yesterdayProof.historical_validation, publicProof.validation);
assert.equal(yesterdayProof.month_summary.period_end, sourceAccess.history_end);
assert.equal(
  yesterdayProof.month_summary.daily_records.length,
  yesterdayProof.month_summary.observed_days
);
assert.equal(
  yesterdayProof.month_summary.win_days + yesterdayProof.month_summary.miss_days,
  yesterdayProof.month_summary.observed_days
);
assert.equal(
  yesterdayProof.month_summary.daily_records.filter((record) => record.hits.length > 0).length,
  yesterdayProof.month_summary.win_days
);
assert.deepEqual(
  yesterdayProof.month_summary.daily_records.map((record) => ({
    date: record.date,
    outputs: record.recommended_numbers,
    observed: record.hits.map((hit) => `${hit.number}${hit.count > 1 ? ` × ${hit.count}` : ""}`),
    status: record.status
  })),
  publicProof.recent_period.days
);

// Current paid readiness may be public, but the current paid Production codes must not be.
assert.equal(paidReady.schema_version, "MB_PAID_REPORT_READINESS_V3_MB_ALL_31");
assert.equal(paidReady.report_date, isoNextDay(paidReady.data_lock));
assert.equal(paidReady.data_lock, sourceAccess.history_end);
assert.equal(paidReady.outcome_known_at_selection, false);
assert.equal(publicProof.method_snapshot.target_date, paidReady.report_date);
assert.equal(publicProof.method_snapshot.data_lock, sourceAccess.history_end);
assert.equal(publicProof.method_snapshot.target_date, isoNextDay(publicProof.method_snapshot.data_lock));
assert.equal(publicProof.method_snapshot.layers.length, 6);
assert.deepEqual(publicProof.method_snapshot.layers.map((layer) => layer.index), [1, 2, 3, 4, 5, 6]);
assert.equal(publicProof.method_snapshot.paid_output_hidden, true);
assert.doesNotMatch(publicProofRaw, /"final_(?:codes|pairs)"|"top1"|"top2"/i);
assert.doesNotMatch(paidReadyRaw, /"final_(?:codes|pairs)"|"top1"|"top2"|"slot1_r4268"|"slot2_selected"/i);

// The source template remains a single daily report with a protected checkout.
assert.match(index, /BÁO CÁO DỮ LIỆU AI NGÀY/i);
assert.match(index, /30\.000đ/);
assert.match(index, /id="bank-account">1128091987/);
assert.match(index, /data-open-checkout/);
assert.match(index, /id="copy-payment"/);
assert.match(index, /id="payment-self-confirm"/);
assert.match(index, /id="payment-pending"/);
assert.match(index, /id="delivery-view"/);
assert.match(index, /id="delivery-pairs"/);
assert.match(index, /COMPLETED_DRAW_REPORT:START/);
assert.ok(index.indexOf('src="./config.js') < index.indexOf('src="./app.js'), "public endpoint config must load before app.js");
assert.doesNotMatch(index, /type="email"|name="email"|type="tel"|name="phone"/i);
assert.doesNotMatch(index, /200\.000đ|800\.000đ|07 BÁO CÁO HẰNG NGÀY|30 BÁO CÁO HẰNG NGÀY/);

const publicCopy = `${index}\n${sample}\n${legal}`;
assert.doesNotMatch(publicCopy, /hôm nay đánh|chốt số|số đẹp|bao lô|cam kết trúng/i);
assert.doesNotMatch(publicCopy, /15\.000/i);
assert.doesNotMatch(publicCopy, /MB THANG/i);
assert.match(publicCopy, /không bán số/i);

// Checkout state survives a reload and purchase is tracked only after approval.
assert.match(app, /const PRICE = 30000/);
assert.match(app, /localStorage\.getItem\(ORDER_KEY\)/);
assert.match(app, /localStorage\.setItem\(ORDER_KEY/);
assert.match(app, /sessionStorage\.getItem\(ORDER_KEY\)/);
assert.match(app, /begin_checkout/);
assert.match(app, /add_payment_info/);
assert.match(app, /payment_submitted/);
assert.match(app, /generate_lead/);
assert.match(app, /result\.status === "approved"/);
assert.match(app, /const DELIVERY_SCHEMA = "fourso-top2-v1"/);
assert.match(app, /delivery\.pairs\.length === 2/);
assert.match(app, /pair\.numbers\.length === 2/);
assert.match(app, /track\("purchase"/);
assert.match(app, /track\("manual_event_PURCHASE"/);
const submitPaymentClaim = app.slice(app.indexOf("function submitPaymentClaim"), app.indexOf("function jsonp"));
assert.doesNotMatch(submitPaymentClaim, /track\("purchase"/);
assert.doesNotMatch(submitPaymentClaim, /track\("manual_event_PURCHASE"/);

// VietQR and paid-search mode must reduce checkout friction without changing the amount.
assert.match(checkoutEnhance, /const ACCOUNT_HOLDER = "NGUYEN TU LINH"/);
assert.match(checkoutEnhance, /const ACCOUNT_NUMBER = "1128091987"/);
assert.match(checkoutEnhance, /const BANK_ID = "VPB"/);
assert.match(checkoutEnhance, /const AMOUNT = 30000/);
assert.match(checkoutEnhance, /img\.vietqr\.io\/image/);
assert.match(checkoutEnhance, /gclid/);
assert.match(checkoutEnhance, /gbraid/);
assert.match(checkoutEnhance, /wbraid/);
assert.match(checkoutEnhance, /ads-landing/);
assert.match(conversionV2, /\.vietqr-panel/);
assert.match(conversionV2, /\.ads-landing \.floating-zalo/);
assert.match(conversionV2, /history-disclosure/);

// Build pipeline must enforce the current final conversion contract.
assert.match(workflow, /find site-v2 -maxdepth 1 -type f/);
assert.match(workflow, /python scripts\/finalize_live_mball\.py --output-root _site/);
assert.match(workflow, /python scripts\/fix_home_blank\.py --output-root _site/);
assert.match(workflow, /python scripts\/sitewide_product_surface\.py --output-root _site/);
assert.match(workflow, /page\.count\('data-open-checkout'\)>=2/);
assert.match(applyConversionV2, /History contains a day outside the report month/);
assert.match(applyConversionV2, /completed rows for the report month/);
assert.match(applyConversionV2, /Historical rate is data/);
assert.match(applyConversionV2, /round\(hit_days \* 100 \/ total_days\)/);
assert.match(simplifyPurchaseCta, /filter_history_to_report_month/);
assert.match(simplifyPurchaseCta, /Lịch sử đối chiếu trong tháng này/);
assert.match(simplifyPurchaseCta, /exactly two checkout buttons/i);

// Approval credentials remain server-side and the deployed artifact excludes them.
assert.match(config, /window\.ORDER_CONFIRMATION_ENDPOINT\s*=\s*"https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec"/);
assert.doesNotMatch(config, /\b(?:OWNER_EMAIL|ADMIN_SECRET)\b/);
assert.doesNotMatch(config, /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
assert.match(approvalBackend, /MailApp\.sendEmail/);
assert.match(approvalBackend, /hashToken\(token\)/);
assert.match(approvalBackend, /timingSafeEqual/);
assert.match(approvalBackend, /PAID_REPORT_SHEET_NAME = "Paid_Report"/);
assert.match(workflow, /test ! -e _site\/approval-backend\.gs/);
assert.match(workflow, /test ! -e _site\/ai-methods\/report-data\.json/);

// Secondary-page checkout routing remains direct.
assert.match(checkoutEntry, /checkout/);
assert.match(checkoutEntry, /button\.click\(\)/);
