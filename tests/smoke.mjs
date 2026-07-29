import { readFileSync } from "node:fs";

const files = ["index.html", "styles.css", "app.js", ".github/workflows/pages.yml"];
const content = Object.fromEntries(
  files.map((file) => [file, readFileSync(new URL(`../${file}`, import.meta.url), "utf8")]),
);

const requiredHtml = [
  "Control Center",
  "Rà soát số",
  "Project ChatGPT MB MAX V03",
  "saveProjectUrl",
  "projectStatus",
  "Lệnh gửi Project",
  "Quyết định vốn",
  "Ghi kết quả",
  "Số mạnh đang theo dõi",
  "Checklist xuống tiền",
  "app.js",
];

const requiredJs = [
  "MB_MAX_V03_CUM3_2SO_INT_V3",
  "MB_CAPITAL_PROTECTION_V1",
  "buildCommand",
  "PROJECT_URL_STORAGE_KEY",
  "buildChatGptCommandUrl",
  "requireProjectUrl",
  "runReviewCommand",
  "calculateMetrics",
  "localStorage",
  "chatgpt.com",
];

for (const token of requiredHtml) {
  if (!content["index.html"].includes(token)) {
    throw new Error(`Missing HTML token: ${token}`);
  }
}

for (const token of requiredJs) {
  if (!content["app.js"].includes(token)) {
    throw new Error(`Missing JS token: ${token}`);
  }
}

if (!content[".github/workflows/pages.yml"].includes("actions/deploy-pages@v4")) {
  throw new Error("Missing GitHub Pages deploy action");
}

console.log("Static dashboard smoke test passed.");
