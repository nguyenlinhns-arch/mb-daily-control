import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd(), "site-v2");
const read = (name) => readFile(resolve(root, name), "utf8");
const [index, styles, app, legal, sample, workflow, completedWorkflow, completedScript] = await Promise.all([
  read("index.html"),
  read("styles.css"),
  read("app.js"),
  read("legal.html"),
  read("mau-bao-cao.html"),
  readFile(resolve(process.cwd(), ".github/workflows/pages.yml"), "utf8"),
  readFile(resolve(process.cwd(), ".github/workflows/completed-draw-daily-1900.yml"), "utf8"),
  readFile(resolve(process.cwd(), "scripts/update_completed_draw_report.py"), "utf8")
]);

for (const file of ["styles.css", "app.js", "mau-bao-cao.html", "legal.html", "robots.txt", "sitemap.xml", "404.html", "favicon.svg"]) {
  assert.ok(await read(file), `${file} must not be empty`);
}
assert.ok((await stat(resolve(root, "og.png"))).size > 100_000, "og.png must be a real social preview image");

// One clearly described daily report, one clear price, and one simple delivery flow.
assert.match(index, /BÁO CÁO DỮ LIỆU AI NGÀY/i);
assert.match(index, /Báo cáo dữ liệu AI[\s\S]*ngày hôm nay/i);
assert.match(index, /30\.000đ/);
assert.match(index, /Thanh toán một lần · Không tự gia hạn/i);
assert.match(index, /7 phương pháp hôm nay/i);
assert.match(index, /khỏi tự gom|Không cần tự gom/i);
assert.match(index, /Nhận báo cáo đầy đủ/i);
assert.match(index, /Nhắn Zalo để nhận báo cáo/i);
assert.match(index, /Hiện thông tin chuyển khoản/i);
assert.match(index, /id="bank-account">1128091987/);
assert.match(index, /data-open-checkout/);
assert.match(index, /id="copy-payment"/);
assert.match(index, /id="copy-order-code"/);
assert.match(index, /id="zalo-delivery"/);
assert.match(index, /Hỗ trợ ngay/);
assert.match(index, /https:\/\/lemienbac\.com\/og\.png/);
assert.match(index, /COMPLETED_DRAW_REPORT:START/);
assert.equal((index.match(/role="row"/g) || []).length, 7);
assert.doesNotMatch(index, /200\.000đ|800\.000đ|07 BÁO CÁO HẰNG NGÀY|30 BÁO CÁO HẰNG NGÀY/);
assert.doesNotMatch(index, /config\.js/);

// The published report date must always be one day after the locked data date.
const reportDateMatch = index.match(/data-report-date="(\d{2}\/\d{2}\/\d{4})" data-lock-date="(\d{2}\/\d{2}\/\d{4})"/);
assert.ok(reportDateMatch, "index must publish report and lock dates");
const parseViDate = (value) => {
  const [day, month, year] = value.split("/").map(Number);
  return Date.UTC(year, month - 1, day);
};
assert.equal(parseViDate(reportDateMatch[1]) - parseViDate(reportDateMatch[2]), 86400000, "report date must be T+1 from locked data");
assert.ok(index.indexOf('id="methods"') < index.indexOf('id="buy"'));
assert.doesNotMatch(index, /id="included"|id="about"|faq-section|steps-section|pricing-section/);

// Future-pick, betting and unverifiable-performance copy must stay absent.
const publicCopy = `${index}\n${sample}\n${legal}`;
assert.doesNotMatch(publicCopy, /hôm nay đánh|chốt số|số đẹp|bao lô|xiên|cam kết trúng/i);
assert.doesNotMatch(publicCopy, /15\.000|24\/30|80%/i);
assert.doesNotMatch(publicCopy, /mở kết luận|kết luận 1 số|kết luận 2 số|kết luận 4 số|dàn số/i);
assert.doesNotMatch(publicCopy, /4SO|MB THANG/i);
assert.doesNotMatch(publicCopy, />[^<]*0398[^<]*</i);
assert.match(publicCopy, /không bán số/i);

// Evidence and the public sample must remain inspectable.
assert.match(index, /943[\s\S]*phiên lịch sử/);
assert.match(index, /27\/27[\s\S]*bản ghi/);
assert.match(index, /<strong>[2-9]<\/strong> nguồn khớp/);
assert.match(index, /95cc3b29870936ff/);
assert.match(sample, /DẤU VẾT NGUỒN/);
assert.match(sample, /PHẠM VI BÁO CÁO/);
assert.ok(sample.includes(`Ngày báo cáo mẫu: ${reportDateMatch[1]}`));
assert.ok(sample.includes(`Khóa nguồn: ${reportDateMatch[2]}`));
assert.match(sample, /7 LỚP KIỂM ĐỊNH/);
assert.match(sample, /7 phiên[\s\S]*30 phiên[\s\S]*90 phiên/);
assert.match(sample, /KẾT LUẬN DỮ LIỆU MẪU/);
assert.ok(sample.includes(`Kết luận ngày ${reportDateMatch[1]}`));
assert.match(sample, /không phải xác suất/i);

// Legal copy must match the one-report, bank-transfer-to-Zalo experience.
assert.match(legal, /một loại sản phẩm[\s\S]*30\.000đ/i);
assert.match(legal, /một báo cáo/i);
assert.match(legal, /không tự gia hạn/i);
assert.match(legal, /chuyển khoản[\s\S]*nhắn qua Zalo/i);
assert.match(legal, /Đối soát thủ công/);
assert.match(legal, /Điều kiện hoàn phí/);
assert.match(legal, /Google Analytics chỉ được bật sau khi người dùng đồng ý/i);
assert.doesNotMatch(legal, /200\.000đ|800\.000đ|07 báo cáo|30 báo cáo/);

// Browser code tracks real funnel steps but never claims an unverified purchase.
assert.match(app, /begin_checkout/);
assert.match(app, /add_payment_info/);
assert.match(app, /generate_lead/);
assert.match(app, /zalo_after_bank_transfer/);
assert.match(app, /Báo cáo dữ liệu AI ngày hôm nay/);
assert.doesNotMatch(app, /BACKEND_ENDPOINT|ORDER_CONFIRMATION_ENDPOINT|payment_submitted|track\("purchase"|startPolling|checkStatus/);
assert.match(styles, /\.hero-offer/);
assert.match(styles, /\.buy-simple-card/);
assert.match(styles, /\.checkout-actions/);

// Deployment and the 19:00 completed-draw updater stay reproducible.
assert.doesNotMatch(workflow, /schedule:/);
assert.match(workflow, /cp site-v2\/index\.html/);
assert.match(workflow, /cp site-v2\/og\.png/);
assert.match(completedWorkflow, /cron: "0 12 \* \* \*"/);
assert.match(completedWorkflow, /update_completed_draw_report\.py/);
assert.match(completedScript, /POST_DRAW_ONLY_NO_PREDICTIONS_NO_STAKES_NO_FINANCIAL_PNL/);
assert.match(completedScript, /7 phương pháp hôm nay/);
assert.doesNotMatch(completedScript, /plan_next_day|actual_order|pnl_vnd/i);

console.log("Simple daily AI data report site smoke checks passed.");
