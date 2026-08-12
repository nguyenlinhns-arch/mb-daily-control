import { readFileSync } from "node:fs";
import vm from "node:vm";

const landing = readFileSync(new URL("../ai-methods/landing-v7.html", import.meta.url), "utf8");
const overrides = readFileSync(new URL("../ai-methods/v7-overrides.css", import.meta.url), "utf8");
const publicMethodsText = readFileSync(new URL("../ai-methods/public-methods.json", import.meta.url), "utf8");
const publicMethods = JSON.parse(publicMethodsText);
const yesterdayProofText = readFileSync(new URL("../ai-methods/yesterday-proof.json", import.meta.url), "utf8");
const yesterdayProof = JSON.parse(yesterdayProofText);
const workflow = readFileSync(new URL("../.github/workflows/pages.yml", import.meta.url), "utf8");

const requiredLandingTokens = [
  "KHUYẾN NGHỊ HÔM NAY",
  "ĐANG KIỂM TRA DỮ LIỆU",
  "month-winning-rows",
  "SỐ KHUYẾN NGHỊ HÔM QUA",
  "80%",
  "GIỚI THIỆU 4SO AI",
  "method-board",
  "method-rows",
  "public-methods.json",
  "yesterday-proof.json",
  "KẾT LUẬN CUỐI CÙNG",
  "paywall-lock",
  "MỞ KẾT LUẬN · 30.000đ",
  "checkout-progress",
  "seo-guide-section",
  "/cho-so-mien-bac-hom-nay/",
  "/phuong-phap-4so/",
  "/lich-su-doi-chieu/",
  "/thong-ke-lo-to-mien-bac-bang-ai/",
  "1128091987",
  "CopyPaymentDetails",
  "og-4so-ai-v2.jpg",
  "v7-overrides.css",
  "google-site-verification",
  "/gioi-thieu/",
  "setPaymentAvailability(false)",
  "G-R9TBYP97BC",
];

for (const token of requiredLandingTokens) {
  if (!landing.includes(token)) {
    throw new Error(`Missing conversion landing token: ${token}`);
  }
}

const visibleText = landing
  .replace(/<script[\s\S]*?<\/script>/gi, " ")
  .replace(/<style[\s\S]*?<\/style>/gi, " ")
  .replace(/<[^>]+>/g, " ")
  .replace(/\s+/g, " ")
  .trim();

for (const token of [
  "BẢNG PHÂN TÍCH AI 4SO",
  "Các ngày trúng trong tháng",
  "Số khuyến nghị và kết quả",
  "AI tổng hợp dữ liệu và nhiều phương pháp trước khi kết luận",
  "Số theo các phương pháp",
  "SAO CHÉP STK + SỐ TIỀN + NỘI DUNG",
  "TÔI ĐÃ CHUYỂN KHOẢN GỬI ẢNH QUA ZALO",
  "Cho số Miền Bắc hôm nay",
  "Phương pháp 4SO",
  "Lịch sử đối chiếu",
  "Thống kê Lô tô bằng AI",
]) {
  if (!visibleText.includes(token)) {
    throw new Error(`Contextual markup must preserve visible copy: ${token}`);
  }
}

if (visibleText.includes("0398696879")) {
  throw new Error("Zalo phone number must not be visible on the landing page");
}

if ((landing.match(/data-package=/g) || []).length !== 3) {
  throw new Error("Checkout must expose exactly three package choices");
}

for (const token of ["body{margin:0;min-width:320px", ".month-wins{padding:16px", ".yesterday-proof{padding:16px", ".ai-intro{padding:18px", ".method-board{background:#fff}", ".modal-plans{margin-top:15px;display:grid;grid-template-columns:1fr", ".mobile-bar button"]) {
  if (!overrides.includes(token)) {
    throw new Error(`Missing mobile readability rule: ${token}`);
  }
}

for (const token of [
  'class="context-phrase"',
  'class="keep-together"',
  'class="table-label"',
  'class="button-line"',
  'class="win-result"',
  'class="result-tokens"',
  "const renderHitTokens=",
  "const old=button.innerHTML",
  "button.innerHTML=old",
]) {
  if (!landing.includes(token)) throw new Error(`Missing contextual line-wrap structure: ${token}`);
}

if ((landing.match(/class="context-phrase"/g) || []).length < 12) {
  throw new Error("Long headings must be split into enough semantic phrases");
}

for (const token of [
  ".context-phrase{display:inline-block;max-width:100%;white-space:nowrap}",
  ".keep-together{white-space:nowrap}",
  ".table-label>span{display:block;white-space:nowrap}",
  ".method-label strong{max-width:100%;",
  "overflow-wrap:normal;word-break:normal;hyphens:none",
  ".board-heading,.method-row{grid-template-columns:86px minmax(0,1fr)}",
  ".report-titlebar h1 .context-phrase{display:block}",
]) {
  if (!overrides.includes(token)) throw new Error(`Missing contextual line-wrap CSS: ${token}`);
}

if (/\.method-label strong\{[^}]*overflow-wrap:anywhere/.test(overrides) || /word-break:\s*break-all/.test(overrides)) {
  throw new Error("Method names must never break in the middle of a word");
}

if (landing.includes("final_codes") || landing.includes("final_pairs")) {
  throw new Error("Current paid conclusion must not be embedded in public landing source");
}

if (!/^\d{4}-\d{2}-\d{2}$/.test(publicMethods.target_date) || !/^\d{4}-\d{2}-\d{2}$/.test(publicMethods.data_lock)) {
  throw new Error("Public method output dates are invalid");
}

for (const token of [
  "timeZone:'Asia/Ho_Chi_Minh'",
  "const initialTarget=reportDay()",
  "return `${value.year}-${value.month}-${value.day}`",
  "const previousISO=",
  "const initialLock=previousISO(initialTarget)",
  "lockDisplay=display(data.data_lock)",
  "data.target_date!==initialTarget",
  "data.data_lock!==previousISO(initialTarget)",
  "data.recommendation_scope!=='TODAY_ONLY'",
  "Không hiển thị lại số của ngày cũ.",
  "ĐANG CẬP NHẬT DỮ LIỆU HÔM NAY",
]) {
  if (!landing.includes(token)) throw new Error(`Landing must use today's Vietnam date: ${token}`);
}

if (landing.includes("target=data.target_date") || landing.includes("afterDailyUpdate")) {
  throw new Error("Public method data or the 19:15 rollover must not replace today's report date");
}

if (publicMethods.source_status !== "LOCKED_27_OF_27" || publicMethods.outcome_known_at_selection !== false) {
  throw new Error("Public method data must come from a locked 27/27 no-look-ahead snapshot");
}

if (publicMethods.schema_version !== "MB_PUBLIC_METHOD_OUTPUTS_V2_TODAY_ONLY" || publicMethods.recommendation_scope !== "TODAY_ONLY") {
  throw new Error("Public method output must be explicitly scoped to today's recommendation block");
}

const targetMs = Date.parse(`${publicMethods.target_date}T00:00:00Z`);
const lockMs = Date.parse(`${publicMethods.data_lock}T00:00:00Z`);
if (!Number.isFinite(targetMs) || targetMs - lockMs !== 86_400_000) {
  throw new Error("Public method data lock must be exactly target date minus one day");
}

if (!Array.isArray(publicMethods.methods) || publicMethods.methods.length < 4) {
  throw new Error("Public method output must list multiple methods");
}

for (const method of publicMethods.methods) {
  if (!method.name || !Array.isArray(method.numbers) || !method.numbers.length) {
    throw new Error("Every public method row must include a name and at least one number");
  }
  if (method.numbers.some((value) => !/^\d{2}$/.test(String(value)))) {
    throw new Error(`Invalid public number in ${method.name}`);
  }
}

if (/final_codes|final_pairs|canonical_codes|canonical_pairs/i.test(publicMethodsText)) {
  throw new Error("Locked 4SO conclusion fields must not appear in public method data");
}

if (landing.includes("method.status") || landing.includes("method.note") || landing.includes("method-footnote")) {
  throw new Error("Public method rows must show only method names and numbers");
}

if (yesterdayProof.date !== "2026-08-12") {
  throw new Error("Yesterday proof must be settled through 12/08/2026");
}

if (JSON.stringify(yesterdayProof.recommended_numbers) !== JSON.stringify(["61", "18", "81", "16"])) {
  throw new Error("Yesterday recommendation does not match the locked 12/08/2026 record");
}

const expectedHits = {"81": 1};
for (const hit of yesterdayProof.hits || []) {
  if (expectedHits[hit.number] !== hit.count) throw new Error(`Unexpected yesterday hit: ${hit.number}`);
  delete expectedHits[hit.number];
}
if (Object.keys(expectedHits).length || yesterdayProof.unique_hit_count !== 1 || yesterdayProof.total_occurrences !== 1) {
  throw new Error("Yesterday hit summary must be 1/4 numbers and 1 occurrence");
}

const validation = yesterdayProof.historical_validation || {};
if (validation.hit_days !== 24 || validation.total_days !== 30 || validation.rate_pct !== 80) {
  throw new Error("Historical 30-day validation must remain 24/30 = 80%");
}

const monthSummary = yesterdayProof.month_summary || {};
if (monthSummary.month !== "2026-08" || monthSummary.observed_days !== 12 || monthSummary.win_days !== 9 || monthSummary.winning_days?.length !== 9) {
  throw new Error("August winning-day summary must remain 9/12 through 12/08/2026");
}

if (yesterdayProof.schema_version !== "MB_PUBLIC_YESTERDAY_PROOF_V2") {
  throw new Error("Yesterday proof must use the complete V2 public audit schema");
}

if (validation.window_start !== "2026-07-14" || validation.window_end !== "2026-08-12") {
  throw new Error("Historical validation must disclose its exact 30-day window");
}

if (!Array.isArray(monthSummary.daily_records) || monthSummary.daily_records.length !== 12 || monthSummary.miss_days !== 3) {
  throw new Error("August history must include all twelve daily records and three misses");
}

for (const [index, record] of monthSummary.daily_records.entries()) {
  const expectedDate = `2026-08-${String(index + 1).padStart(2, "0")}`;
  if (record.date !== expectedDate || record.recommended_numbers?.length !== 4 || !/^[0-9a-f]{64}$/.test(record.record_hash || "")) {
    throw new Error(`Incomplete auditable history record: ${expectedDate}`);
  }
  if ((record.hits?.length ? "hit" : "miss") !== record.status) {
    throw new Error(`History status does not match hits: ${expectedDate}`);
  }
}

if (/final_codes|final_pairs|canonical_codes|canonical_pairs/i.test(yesterdayProofText)) {
  throw new Error("Locked 4SO conclusion must not appear in public proof data");
}

if (!workflow.includes("python scripts/build_seo_pages.py --output-root _site")) {
  throw new Error("GitHub Pages must statically render the maintained landing-v7 source");
}

if (workflow.includes("V7_GZ_B64")) {
  throw new Error("GitHub Pages must not deploy the obsolete embedded v7 payload");
}

if (workflow.includes("cp -R ai-methods") || !workflow.includes("test ! -e _site/ai-methods/report-data.json")) {
  throw new Error("GitHub Pages artifact must exclude obsolete reports and landing versions");
}

if (!workflow.includes('cron: "1 17 * * *"') || !workflow.includes('cron: "15 18 * * *"')) {
  throw new Error("GitHub Pages must fail closed at midnight and retry after the daily operation");
}

if (landing.includes("fonts.googleapis.com") || landing.includes("fonts.gstatic.com")) {
  throw new Error("Landing page must not block rendering on external font requests");
}

if ((landing.match(/data-(?:plan-)?open[^>]*disabled/g) || []).length < 6 || !landing.includes("let dataReady=false")) {
  throw new Error("Payment controls must start disabled until today's payload validates");
}

const inlineScripts = [...landing.matchAll(/<script>([\s\S]*?)<\/script>/gi)].map((match) => match[1]);
if (!inlineScripts.length || !inlineScripts.some((script) => script.includes("const initialTarget=reportDay()"))) {
  throw new Error("Landing page script is missing");
}
for (const [index, script] of inlineScripts.entries()) {
  new vm.Script(script, { filename: `landing-v7-inline-${index}.js` });
}

console.log("4SO AI conversion landing smoke test passed.");
