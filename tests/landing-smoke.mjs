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
  "BẢNG PHÂN TÍCH AI 4SO",
  "KHUYẾN NGHỊ HÔM NAY",
  "ĐANG KIỂM TRA DỮ LIỆU",
  "Các ngày trúng trong tháng",
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
  "SAO CHÉP STK + SỐ TIỀN + NỘI DUNG",
  "TÔI ĐÃ CHUYỂN KHOẢN · GỬI ẢNH QUA ZALO",
  "1128091987",
  "CopyPaymentDetails",
  "og-4so-ai-v2.jpg",
  "v7-overrides.css",
];

for (const token of requiredLandingTokens) {
  if (!landing.includes(token)) {
    throw new Error(`Missing conversion landing token: ${token}`);
  }
}

const visibleText = landing
  .replace(/<script[\s\S]*?<\/script>/gi, " ")
  .replace(/<style[\s\S]*?<\/style>/gi, " ")
  .replace(/<[^>]+>/g, " ");

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

if (yesterdayProof.date !== "2026-08-11") {
  throw new Error("Yesterday proof must be settled through 11/08/2026");
}

if (JSON.stringify(yesterdayProof.recommended_numbers) !== JSON.stringify(["05", "91", "50", "19"])) {
  throw new Error("Yesterday recommendation does not match the locked 11/08/2026 record");
}

const expectedHits = {"05": 1, "91": 2, "50": 1};
for (const hit of yesterdayProof.hits || []) {
  if (expectedHits[hit.number] !== hit.count) throw new Error(`Unexpected yesterday hit: ${hit.number}`);
  delete expectedHits[hit.number];
}
if (Object.keys(expectedHits).length || yesterdayProof.unique_hit_count !== 3 || yesterdayProof.total_occurrences !== 4) {
  throw new Error("Yesterday hit summary must be 3/4 numbers and 4 occurrences");
}

const validation = yesterdayProof.historical_validation || {};
if (validation.hit_days !== 24 || validation.total_days !== 30 || validation.rate_pct !== 80) {
  throw new Error("Historical 30-day validation must remain 24/30 = 80%");
}

const monthSummary = yesterdayProof.month_summary || {};
if (monthSummary.month !== "2026-08" || monthSummary.observed_days !== 11 || monthSummary.win_days !== 8 || monthSummary.winning_days?.length !== 8) {
  throw new Error("August winning-day summary must remain 8/11 through 11/08/2026");
}

if (/final_codes|final_pairs|canonical_codes|canonical_pairs/i.test(yesterdayProofText)) {
  throw new Error("Locked 4SO conclusion must not appear in public proof data");
}

if (!workflow.includes("Path('ai-methods/landing-v7.html').read_text")) {
  throw new Error("GitHub Pages must deploy the maintained landing-v7 source");
}

if (workflow.includes("V7_GZ_B64")) {
  throw new Error("GitHub Pages must not deploy the obsolete embedded v7 payload");
}

const scriptMatch = landing.match(/<script>([\s\S]*?)<\/script>/i);
if (!scriptMatch) {
  throw new Error("Landing page script is missing");
}
new vm.Script(scriptMatch[1], { filename: "landing-v7-inline.js" });

console.log("4SO AI conversion landing smoke test passed.");
