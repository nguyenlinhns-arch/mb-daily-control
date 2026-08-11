import { readFileSync } from "node:fs";
import vm from "node:vm";

const landing = readFileSync(new URL("../ai-methods/landing-v7.html", import.meta.url), "utf8");
const overrides = readFileSync(new URL("../ai-methods/v7-overrides.css", import.meta.url), "utf8");
const workflow = readFileSync(new URL("../.github/workflows/pages.yml", import.meta.url), "utf8");

const requiredLandingTokens = [
  "Chuyển khoản &amp; nhận báo cáo · 30.000đ",
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

for (const token of ["body{background:var(--cream);font-size:18px", ".modal-plans{grid-template-columns:1fr}", ".mobile-bar button"]) {
  if (!overrides.includes(token)) {
    throw new Error(`Missing mobile readability rule: ${token}`);
  }
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
