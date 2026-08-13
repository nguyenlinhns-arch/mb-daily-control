import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd(), "site-v2");
const read = (name) => readFile(resolve(root, name), "utf8");
const [index, styles, app, legal, sample, config, workflow, completedWorkflow, completedScript, backend] = await Promise.all([
  read("index.html"),
  read("styles.css"),
  read("app.js"),
  read("legal.html"),
  read("mau-bao-cao.html"),
  read("config.js"),
  readFile(resolve(process.cwd(), ".github/workflows/pages.yml"), "utf8"),
  readFile(resolve(process.cwd(), ".github/workflows/completed-draw-daily-1900.yml"), "utf8"),
  readFile(resolve(process.cwd(), "scripts/update_completed_draw_report.py"), "utf8"),
  read("approval-backend.gs")
]);

for (const file of ["styles.css", "app.js", "config.js", "mau-bao-cao.html", "legal.html", "robots.txt", "sitemap.xml", "404.html", "favicon.svg"]) {
  assert.ok(await read(file), `${file} must not be empty`);
}
assert.ok((await stat(resolve(root, "og.png"))).size > 100_000, "og.png must be a real social preview image");

// The destination must clearly describe one available historical-data service.
assert.match(index, /DỊCH VỤ PHÂN TÍCH DỮ LIỆU LỊCH SỬ XSMB/i);
assert.match(index, /không cung cấp dự đoán, số khuyến nghị/i);
assert.match(index, /BẰNG CHỨNG CÓ THỂ KIỂM TRA/);
assert.match(index, /943[\s\S]*phiên lịch sử/);
assert.match(index, /27\/27[\s\S]*bản ghi phiên gần nhất/);
assert.match(index, /<span>[2-9]<\/span><strong>nguồn trùng khớp/);
assert.match(index, /95cc3b29870936ff/);
assert.match(index, /7 lớp kiểm định của báo cáo gần nhất/);
assert.equal((index.match(/role="row"/g) || []).length, 7);
assert.match(index, /https:\/\/lemienbac\.com\/og\.png/);
assert.match(index, /Phương pháp luận công khai/i);
assert.match(index, /Bạn nhận được gì/i);
assert.match(index, /Đơn vị và kênh hỗ trợ|Giới thiệu và độc lập/i);
assert.match(index, /30\.000đ/);
assert.match(index, /200\.000đ/);
assert.match(index, /800\.000đ/);
assert.match(index, /Thanh toán một lần, không tự gia hạn/i);
assert.match(index, /quy trình công khai/i);
assert.match(index, /Tôi đã chuyển khoản – gửi yêu cầu đối soát/);
assert.match(index, /id="delivery-view"/);
assert.match(index, /Zalo chỉ dùng khi cần/i);
assert.match(index, /COMPLETED_DRAW_REPORT:START/);
assert.ok(index.indexOf('id="evidence"') < index.indexOf('id="methodology"'));
assert.ok(index.indexOf('id="methodology"') < index.indexOf('id="pricing"'));
assert.doesNotMatch(index, /RETAIL SAMPLE|Doanh thu|Đơn hàng/);

// High-risk future-pick and unverifiable-performance copy must stay absent.
const publicCopy = `${index}\n${sample}\n${legal}`;
assert.doesNotMatch(publicCopy, /hôm nay đánh|chốt số|số đẹp|bao lô|xiên|cam kết trúng/i);
assert.doesNotMatch(publicCopy, /15\.000|24\/30|80%/i);
assert.doesNotMatch(publicCopy, /mở kết luận|kết luận 1 số|kết luận 2 số|kết luận 4 số|dàn số/i);
assert.doesNotMatch(publicCopy, /4SO|MB THANG/i);
assert.doesNotMatch(publicCopy, />[^<]*0398[^<]*</i);
assert.match(publicCopy, /Hỗ trợ ngay/);

// The public sample must show the actual structure and the limits of the paid report.
assert.match(sample, /DẤU VẾT NGUỒN/);
assert.match(sample, /7 LỚP KIỂM ĐỊNH/);
assert.match(sample, /MÃ KIỂM TRA|Mã kiểm tra/);
assert.match(sample, /không phải xác suất/i);
assert.match(sample, /NỘI DUNG BẢN ĐẶT THEO PHẠM VI/);

// Legal copy must disclose provider identity, deliverable, prices, refund and privacy.
assert.match(legal, /Đơn vị và kênh hỗ trợ/);
assert.match(legal, /30\.000đ[\s\S]*200\.000đ[\s\S]*800\.000đ/);
assert.match(legal, /không tự kích hoạt dịch vụ/i);
assert.match(legal, /Chỉ sau bước này.*đã thanh toán/is);
assert.match(legal, /Điều kiện hoàn phí/);
assert.match(legal, /Google Analytics chỉ được bật sau khi người dùng đồng ý/i);

// Checkout must record payment claims separately from confirmed purchases.
assert.match(app, /payment_submitted/);
assert.match(app, /result\.status === "approved"/);
assert.match(app, /track\("purchase"/);
assert.match(app.slice(app.indexOf("function showDelivery"), app.indexOf("function hiddenPost")), /track\("purchase"/);
assert.match(app.slice(app.indexOf("async function checkStatus"), app.indexOf("function startPolling")), /result\.status === "approved"[\s\S]*showDelivery/);
assert.doesNotMatch(app.slice(app.indexOf("async function submitPaymentClaim"), app.indexOf("function jsonp")), /track\("purchase"/);
assert.match(app, /__fourSoStatus_/);
assert.match(app, /Báo cáo 1 phiên đã công bố/);
assert.match(backend, /Báo cáo 1 phiên đã công bố/);
assert.match(backend, /Không bao gồm dự đoán, số khuyến nghị hoặc hướng dẫn đặt cược/);

assert.match(config, /ORDER_CONFIRMATION_ENDPOINT/);
assert.doesNotMatch(config, /ADMIN_SECRET|OWNER_EMAIL/);
assert.match(styles, /\.evidence-grid/);
assert.match(styles, /\.methodology-grid/);
assert.match(styles, /\.pricing-grid/);

assert.doesNotMatch(workflow, /schedule:/);
assert.match(workflow, /cp site-v2\/index\.html/);
assert.match(workflow, /cp site-v2\/og\.png/);
assert.doesNotMatch(workflow, /build_seo_pages|landing-v7|report-data/);
assert.match(completedWorkflow, /cron: "0 12 \* \* \*"/);
assert.match(completedWorkflow, /update_completed_draw_report\.py/);
assert.match(completedScript, /POST_DRAW_ONLY_NO_PREDICTIONS_NO_STAKES_NO_FINANCIAL_PNL/);
assert.match(completedScript, /7 lớp kiểm định của báo cáo gần nhất/);
assert.doesNotMatch(completedScript, /plan_next_day|actual_order|pnl_vnd/i);

console.log("Historical data service site smoke checks passed.");
