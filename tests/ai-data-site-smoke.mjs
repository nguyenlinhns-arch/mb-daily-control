import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd(), "site-v2");
const read = (name) => readFile(resolve(root, name), "utf8");
const [index, app, legal, sample, config, workflow, completedWorkflow, completedScript] = await Promise.all([
  read("index.html"),
  read("app.js"),
  read("legal.html"),
  read("mau-bao-cao.html"),
  read("config.js"),
  readFile(resolve(process.cwd(), ".github/workflows/pages.yml"), "utf8"),
  readFile(resolve(process.cwd(), ".github/workflows/completed-draw-daily-1900.yml"), "utf8"),
  readFile(resolve(process.cwd(), "scripts/update_completed_draw_report.py"), "utf8")
]);

for (const file of ["styles.css", "app.js", "config.js", "mau-bao-cao.html", "legal.html", "robots.txt", "sitemap.xml", "404.html", "favicon.svg"]) {
  assert.ok(await read(file), `${file} must not be empty`);
}

assert.match(index, /Tôi đã chuyển khoản – báo chủ dịch vụ/);
assert.match(index, /id="delivery-view"/);
assert.match(index, /Zalo chỉ dùng khi bạn cần hỗ trợ/);
assert.match(index, /không đưa ra số dự đoán/i);
assert.match(index, />1 số</);
assert.match(index, />2 số</);
assert.match(index, />4 số</);
assert.match(index, />Dàn số</);
assert.ok(index.indexOf('class="proof-strip"') < index.indexOf('class="method-list"'));
assert.ok(index.indexOf('class="method-list"') < index.indexOf('class="unlock-card"'));
assert.doesNotMatch(index, /RETAIL SAMPLE|Doanh thu|Đơn hàng/);

assert.match(app, /payment_submitted/);
assert.match(app, /result\.status === "approved"/);
assert.match(app, /track\("purchase"/);
assert.match(app.slice(app.indexOf("function showDelivery"), app.indexOf("function hiddenPost")), /track\("purchase"/);
assert.match(app.slice(app.indexOf("async function checkStatus"), app.indexOf("function startPolling")), /result\.status === "approved"[\s\S]*showDelivery/);
assert.doesNotMatch(app.slice(app.indexOf("async function submitPaymentClaim"), app.indexOf("function jsonp")), /track\("purchase"/);
assert.match(app, /customer_token/);
assert.match(app, /timing|pending/i);

assert.match(config, /ORDER_CONFIRMATION_ENDPOINT/);
assert.doesNotMatch(config, /ADMIN_SECRET|OWNER_EMAIL/);
assert.match(legal, /không tự kích hoạt dịch vụ/i);
assert.match(legal, /Chỉ sau bước này.*đã thanh toán/is);
assert.match(sample, /dữ liệu giả lập/i);
assert.match(sample, /không phải dự đoán/i);
assert.match(sample, /Kết luận 1 số/);
assert.match(sample, /Kết luận dàn số/);
assert.doesNotMatch(index + sample + legal, /4SO|MB THANG/i);
assert.doesNotMatch(index + sample + legal, />[^<]*0398[^<]*</i);
assert.match(index + sample + legal, /Hỗ trợ ngay/);
assert.match(index, /thống kê bằng AI qua 7 lớp phương pháp/i);
assert.match(index, /Hơn 15\.000 lượt tính toán mỗi ngày/);
assert.match(index, /đối chiếu lịch sử 30 ngày[\s\S]*80%/i);
assert.doesNotMatch(index, /class="hero-card"/);

assert.doesNotMatch(index + sample, /hôm nay đánh|chốt số|số đẹp|bao lô|xiên|cam kết trúng/i);
assert.doesNotMatch(workflow, /schedule:/);
assert.match(workflow, /cp site-v2\/index\.html/);
assert.doesNotMatch(workflow, /build_seo_pages|landing-v7|report-data/);
assert.match(index, /COMPLETED_DRAW_REPORT:START/);
assert.match(index, /Tham khảo 7 lớp báo cáo ngày \d{2}\/\d{2}\/\d{4}/);
assert.match(index, /PHIÊN ĐÃ CÔNG BỐ/);
assert.match(completedWorkflow, /cron: "0 12 \* \* \*"/);
assert.match(completedWorkflow, /update_completed_draw_report\.py/);
assert.match(completedScript, /POST_DRAW_ONLY_NO_PREDICTIONS_NO_STAKES_NO_FINANCIAL_PNL/);
assert.doesNotMatch(completedScript, /plan_next_day|actual_order|pnl_vnd/i);

console.log("AI data report site smoke checks passed.");
