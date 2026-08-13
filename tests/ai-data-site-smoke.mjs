import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd(), "site-v2");
const read = (name) => readFile(resolve(root, name), "utf8");
const [index, app, legal, sample, config, workflow] = await Promise.all([
  read("index.html"),
  read("app.js"),
  read("legal.html"),
  read("mau-bao-cao.html"),
  read("config.js"),
  readFile(resolve(process.cwd(), ".github/workflows/pages.yml"), "utf8")
]);

for (const file of ["styles.css", "app.js", "config.js", "mau-bao-cao.html", "legal.html", "robots.txt", "sitemap.xml", "404.html", "favicon.svg"]) {
  assert.ok(await read(file), `${file} must not be empty`);
}

assert.match(index, /Tôi đã chuyển khoản – báo chủ dịch vụ/);
assert.match(index, /id="delivery-view"/);
assert.match(index, /Zalo chỉ dùng khi bạn cần hỗ trợ/);
assert.match(index, /không đưa ra số dự đoán/i);
assert.match(index, /1 số[\s\S]*MB 4SO/);
assert.match(index, /2 số[\s\S]*MB 4SO/);
assert.match(index, /4 số[\s\S]*Đủ 2 cặp[\s\S]*MB 4SO/);
assert.match(index, /Dàn[\s\S]*MB THANG/);
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
assert.match(sample, /Kết luận 1 số · MB 4SO/);
assert.match(sample, /Kết luận dàn · MB THANG/);

assert.doesNotMatch(index + sample, /hôm nay đánh|chốt số|số đẹp|bao lô|xiên|cam kết trúng/i);
assert.doesNotMatch(workflow, /schedule:/);
assert.match(workflow, /cp site-v2\/index\.html/);
assert.doesNotMatch(workflow, /build_seo_pages|landing-v7|report-data/);

console.log("AI data report site smoke checks passed.");
