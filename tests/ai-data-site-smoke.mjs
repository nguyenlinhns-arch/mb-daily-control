import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd(), "site-v2");
const read = (name) => readFile(resolve(root, name), "utf8");
const [
  index,
  styles,
  app,
  config,
  approvalBackend,
  legal,
  sample,
  workflow,
  completedWorkflow,
  completedScript,
  sourceAccessRaw,
  midnightWorkflow,
  historicalProofRaw,
  catchupScript
] = await Promise.all([
  read("index.html"),
  read("styles.css"),
  read("app.js"),
  read("config.js"),
  read("approval-backend.gs"),
  read("legal.html"),
  read("mau-bao-cao.html"),
  readFile(resolve(process.cwd(), ".github/workflows/pages.yml"), "utf8"),
  readFile(resolve(process.cwd(), ".github/workflows/completed-draw-daily-1900.yml"), "utf8"),
  readFile(resolve(process.cwd(), "scripts/update_completed_draw_report.py"), "utf8"),
  readFile(resolve(process.cwd(), "data/source-access.json"), "utf8"),
  readFile(resolve(process.cwd(), ".github/workflows/daily-report-midnight.yml"), "utf8"),
  readFile(resolve(process.cwd(), "data/public-historical-proof.json"), "utf8"),
  readFile(resolve(process.cwd(), "scripts/run_mb4so_005.ps1"), "utf8")
]);
const sourceAccess = JSON.parse(sourceAccessRaw);
const historicalProof = JSON.parse(historicalProofRaw);

for (const file of ["styles.css", "app.js", "mau-bao-cao.html", "legal.html", "robots.txt", "sitemap.xml", "404.html", "favicon.svg"]) {
  assert.ok(await read(file), `${file} must not be empty`);
}
assert.ok((await stat(resolve(root, "og.png"))).size > 100_000, "og.png must be a real social preview image");

// One clearly described daily report, one clear price, and one email-approved delivery flow.
assert.match(index, /BÁO CÁO DỮ LIỆU AI NGÀY/i);
assert.match(index, /Báo cáo dữ liệu AI[\s\S]*ngày hôm nay/i);
assert.match(index, /30\.000đ/);
assert.match(index, /Thanh toán một lần · Không tự gia hạn/i);
assert.match(index, /khỏi tự gom|Không cần tự gom/i);
assert.match(index, new RegExp(`${historicalProof.validation.rate_pct}%`));
assert.match(index, new RegExp(`${historicalProof.validation.hit_days}\\/${historicalProof.validation.total_days} ngày`));
assert.match(index, /DỮ LIỆU TỪ 2024 ĐẾN NGÀY HÔM NAY/);
assert.doesNotMatch(index, /ĐỐI CHIẾU LỊCH SỬ · 14\/07\/2026–12\/08\/2026/);
assert.match(index, /Có cả ngày xuất hiện và không xuất hiện/i);
assert.doesNotMatch(index, /Dịch vụ phân tích dữ liệu; không bán số, không nhận cược và không bảo đảm kết quả tương lai/i);
assert.doesNotMatch(index, /Số được lưu theo 7 lớp báo cáo/i);
assert.doesNotMatch(index, /6 phương pháp độc lập và 1 lớp tổng hợp 4SO/i);
assert.match(index, /Nhận báo cáo đầy đủ/i);
assert.match(index, /Bấm báo đã chuyển khoản/i);
assert.match(index, /Chủ dịch vụ xác nhận, báo cáo mở trên màn hình/i);
assert.match(index, /Hiện thông tin chuyển khoản/i);
assert.match(index, /id="bank-account">1128091987/);
assert.match(index, /data-open-checkout/);
assert.match(index, /id="copy-payment"/);
assert.match(index, /id="payment-self-confirm"/);
assert.match(index, /Mã riêng 12 chữ số: 6 số đầu là ngày YYMMDD, 6 số sau được tạo ngẫu nhiên/i);
assert.match(index, /app\.js\?v=20260813-13/);
assert.match(index, /id="payment-pending"/);
assert.match(index, /id="delivery-view"/);
assert.match(index, /id="delivery-pairs"/);
assert.match(index, /4 số được chia thành 2 cặp theo thứ tự xếp hạng/i);
assert.doesNotMatch(index, /delivery-summary|delivery-metrics|delivery-notes/);
assert.match(index, /id="zalo-order"/);
assert.match(index, /chỉ gửi yêu cầu đối soát, chưa tự xác nhận tiền đã vào tài khoản/i);
assert.match(index, /Hỗ trợ ngay/);
assert.match(index, /https:\/\/lemienbac\.com\/og\.png/);
assert.match(index, /COMPLETED_DRAW_REPORT:START/);
assert.doesNotMatch(index, /id="methods"|historical-method-row|historical-method-list/);
assert.doesNotMatch(index, /200\.000đ|800\.000đ|07 BÁO CÁO HẰNG NGÀY|30 BÁO CÁO HẰNG NGÀY/);
assert.ok(index.indexOf('src="./config.js') < index.indexOf('src="./app.js'), "public endpoint config must load before app.js");
assert.doesNotMatch(index, /type="email"|name="email"|type="tel"|name="phone"/i);

// The published report date must always be one day after the locked data date.
const reportDateMatch = index.match(/data-report-date="(\d{2}\/\d{2}\/\d{4})" data-lock-date="(\d{2}\/\d{2}\/\d{4})"/);
assert.ok(reportDateMatch, "index must publish report and lock dates");
const parseViDate = (value) => {
  const [day, month, year] = value.split("/").map(Number);
  return Date.UTC(year, month - 1, day);
};
const viDateToIso = (value) => {
  const [day, month, year] = value.split("/");
  return `${year}-${month}-${day}`;
};
assert.equal(parseViDate(reportDateMatch[1]) - parseViDate(reportDateMatch[2]), 86400000, "report date must be T+1 from locked data");
assert.equal(sourceAccess.history_end, historicalProof.recent_period.period_end, "public source record must match the latest audited proof date");
assert.match(index, new RegExp(`Báo cáo cho ngày hôm nay \\(${reportDateMatch[1].replaceAll("/", "\\/")}\\)`, "i"));
assert.match(index, new RegExp(`Dữ liệu khóa đến hết ngày hôm qua \\(${reportDateMatch[2].replaceAll("/", "\\/")}\\)`, "i"));
assert.ok(index.indexOf('id="statistics"') < index.indexOf('id="buy"'));
assert.doesNotMatch(index, /id="included"|id="about"|faq-section|steps-section|pricing-section/);

// Future-pick, betting and unverifiable-performance copy must stay absent.
const publicCopy = `${index}\n${sample}\n${legal}`;
assert.doesNotMatch(publicCopy, /hôm nay đánh|chốt số|số đẹp|bao lô|xiên|cam kết trúng/i);
assert.doesNotMatch(publicCopy, /15\.000/i);
assert.doesNotMatch(publicCopy, /mở kết luận|kết luận 1 số|kết luận 2 số|kết luận 4 số|dàn số/i);
assert.doesNotMatch(publicCopy, /MB THANG/i);
assert.doesNotMatch(publicCopy, />[^<]*0398[^<]*</i);
assert.match(publicCopy, /không bán số/i);
assert.match(publicCopy, /Tỷ lệ \d+% chỉ mô tả cửa sổ lịch sử đã hoàn tất, không phải xác suất hoặc cam kết/i);

// Evidence and the public sample must remain inspectable.
assert.equal(historicalProof.schema_version, "MB_PUBLIC_HISTORICAL_PROOF_V1_COMPLETED_ONLY");
assert.equal(Math.round(historicalProof.validation.hit_days * 100 / historicalProof.validation.total_days), historicalProof.validation.rate_pct);
assert.equal(historicalProof.recent_period.days.length, historicalProof.recent_period.total_days);
assert.equal(historicalProof.recent_period.days.filter((day) => day.observed.length > 0).length, historicalProof.recent_period.hit_days);
assert.equal(historicalProof.method_snapshot.layers.length, 7);
assert.equal(historicalProof.method_snapshot.target_date, "2026-08-13");
assert.equal(historicalProof.method_snapshot.data_lock, "2026-08-12");
const templateHistoryRows = (index.match(/class="history-day-row"/g) || []).length;
assert.ok(templateHistoryRows > 0 && templateHistoryRows <= historicalProof.recent_period.total_days);
for (const day of historicalProof.recent_period.days.slice(0, templateHistoryRows)) {
  assert.match(index, new RegExp(day.date.split("-").reverse().join("\\/")));
}
assert.match(index, /href="\/historical-proof\.json"/);
assert.match(index, /href="\/source-access\.json"/);
assert.ok(sample.includes(`Báo cáo cho ngày hôm nay: ${reportDateMatch[1]}`));
assert.ok(sample.includes(`Dữ liệu khóa đến hết ngày hôm qua: ${reportDateMatch[2]}`));
const observedOccurrences = (values) => values.reduce((total, value) => {
  const match = String(value).match(/×\s*(\d+)\s*$/);
  return total + (match ? Number(match[1]) : 1);
}, 0);
const featuredSample = historicalProof.recent_period.days
  .filter((day) => day.observed.length)
  .sort((left, right) => (
    observedOccurrences(right.observed) - observedOccurrences(left.observed)
    || right.observed.length - left.observed.length
    || right.date.localeCompare(left.date)
  ))[0];
assert.equal(featuredSample.date, "2026-08-11");
assert.match(sample, /4SO ngày 11\/08\/2026/);
assert.match(sample, /KHÓA 10\/08\/2026/);
for (const output of featuredSample.outputs) assert.match(sample, new RegExp(`<strong>${output}<\\/strong>`));
assert.match(sample, /3\/4 đầu ra xuất hiện, tổng 4 lượt/);
assert.match(sample, /Mẫu sẽ tự cập nhật khi có ngày lịch sử nổi bật hơn/);
assert.match(sample, /hồ sơ lịch sử đã hoàn tất/i);
assert.match(sample, /không phải 4SO của ngày hôm nay/i);
assert.match(sample, /7 phương pháp/i);
assert.match(sample, /Mọi thứ gọn trong một màn hình/i);

// Legal copy must match the one-report, email-approved, on-screen delivery experience.
assert.match(legal, /một loại sản phẩm[\s\S]*30\.000đ/i);
assert.match(legal, /một báo cáo/i);
assert.match(legal, /không tự gia hạn/i);
assert.match(legal, /chuyển khoản[\s\S]*gửi email cho chủ dịch vụ[\s\S]*tự mở trên chính màn hình/i);
assert.match(legal, /Đối soát thủ công qua email/);
assert.match(legal, /không phải bằng chứng tiền đã vào tài khoản/i);
assert.match(legal, /Zalo chỉ là kênh hỗ trợ tự nguyện/i);
assert.match(legal, /Google Apps Script, Google Sheets và email/i);
assert.match(legal, /Điều kiện hoàn phí/);
assert.match(legal, /Google Analytics chỉ được bật sau khi người dùng đồng ý/i);
assert.match(legal, /Sự kiện mua chỉ được ghi nhận sau khi hệ thống nhận trạng thái đã xác nhận/i);
assert.doesNotMatch(legal, /200\.000đ|800\.000đ|07 báo cáo|30 báo cáo/);
assert.match(sample, /chủ dịch vụ xác nhận qua email và báo cáo tự mở trên màn hình/i);

// Browser code submits an anonymous claim, polls a protected status, and tracks purchase only after approval.
assert.match(app, /begin_checkout/);
assert.match(app, /add_payment_info/);
assert.match(app, /generate_lead/);
assert.match(app, /Báo cáo dữ liệu AI ngày hôm nay/);
assert.match(app, /ORDER_CONFIRMATION_ENDPOINT/);
assert.match(app, /BACKEND_ENDPOINT/);
assert.match(app, /hiddenPost/);
assert.match(app, /customer_token/);
assert.match(app, /payment_submitted/);
assert.match(app, /startPolling/);
assert.match(app, /checkStatus/);
assert.match(app, /result\.status === "approved"/);
assert.match(app, /showDelivery/);
assert.match(app, /const DELIVERY_SCHEMA = "fourso-top2-v1"/);
assert.match(app, /function randomDigits\(length = 6\)/);
assert.match(app, /code: `AI-\$\{day\}-\$\{suffix\}`/);
assert.match(app, /paymentMemo: `\$\{day\}\$\{suffix\}`/);
assert.match(app, /Nội dung: \$\{order\.paymentMemo\}/);
assert.doesNotMatch(app, /Nội dung: \$\{order\.code\}/);
assert.match(app, /delivery\.pairs\.length === 2/);
assert.match(app, /Number\(pair\.rank\) === index \+ 1/);
assert.match(app, /pair\.numbers\.length === 2/);
assert.match(app, /document\.createDocumentFragment\(\)/);
assert.match(app, /deliveryView\.dataset\.rendered = "true"/);
assert.match(app, /TOP 1:[\s\S]*TOP 2:/);
assert.match(app, /plan: "day"/);
assert.match(app, /const PRICE = 30000/);
assert.doesNotMatch(app, /zalo_after_bank_transfer/);
const submitPaymentClaim = app.slice(app.indexOf("function submitPaymentClaim"), app.indexOf("function jsonp"));
const showDelivery = app.slice(app.indexOf("function showDelivery"), app.indexOf("function updateCheckoutState"));
assert.match(submitPaymentClaim, /track\("payment_submitted"/);
assert.doesNotMatch(submitPaymentClaim, /track\("purchase"/);
assert.match(showDelivery, /track\("purchase"/);

// Only the public endpoint is shipped. Approval credentials stay server-side.
assert.match(config, /window\.ORDER_CONFIRMATION_ENDPOINT\s*=\s*"https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec"/);
assert.doesNotMatch(config, /OWNER_EMAIL|ADMIN_SECRET|@/);
assert.match(approvalBackend, /MailApp\.sendEmail/);
assert.match(approvalBackend, /approvalUrl\(code, "approve"\)/);
assert.match(approvalBackend, /hashToken\(token\)/);
assert.match(approvalBackend, /timingSafeEqual/);
assert.match(approvalBackend, /Session\.getEffectiveUser\(\)\.getEmail\(\)/);
assert.match(approvalBackend, /properties\.getProperty\("OWNER_EMAIL"\)/);
assert.match(approvalBackend, /properties\.getProperty\("ADMIN_SECRET"\)/);
assert.match(approvalBackend, /Utilities\.getUuid\(\)/);
assert.match(approvalBackend, /const PAID_REPORT_SHEET_NAME = "Paid_Report"/);
assert.match(approvalBackend, /action === "daily005"/);
assert.match(approvalBackend, /function dailyMbWebRun_\(\)/);
assert.match(approvalBackend, /MB_4SO_TOP2_2SO_T1_V1/);
assert.match(approvalBackend, /DAILY_MB_MAX_ATTEMPTS = 6/);
assert.doesNotMatch(approvalBackend, /DAILY_MB_005_OUTSIDE_WINDOW/);
assert.match(catchupScript, /while \(\$true\)/);
assert.match(catchupScript, /\$retrySeconds = 60/);
assert.match(catchupScript, /function Test-LiveWebsite/);
assert.match(catchupScript, /Live website verified for REPORT_DATE=/);
assert.match(approvalBackend, /getSheetByName\(PAID_REPORT_SHEET_NAME\)/);
assert.match(approvalBackend, /getDisplayValues\(\)/);
assert.match(approvalBackend, /schema: DELIVERY_SCHEMA/);
assert.match(approvalBackend, /pairs: \[/);
const buildDelivery = approvalBackend.slice(approvalBackend.indexOf("function buildDelivery"), approvalBackend.indexOf("function readPublicReportSnapshot"));
assert.doesNotMatch(buildDelivery, /metrics:|notes:|summary:/);
assert.doesNotMatch(approvalBackend, /REPLACE_WITH_OWNER_EMAIL|REPLACE_WITH_A_LONG_RANDOM_SECRET/);
assert.match(styles, /\.hero-offer/);
assert.match(styles, /\.buy-simple-card/);
assert.match(styles, /\.payment-confirm/);
assert.match(styles, /\.payment-pending/);
assert.match(styles, /\.delivery-view/);
assert.match(styles, /\.delivery-pairs/);
assert.match(styles, /\.delivery-pair-numbers/);

// Deployment and the 19:00 completed-draw updater stay reproducible.
assert.match(workflow, /schedule:/);
assert.match(workflow, /cron: "1 17 \* \* \*"/);
assert.match(workflow, /cron: "15 18 \* \* \*"/);
assert.match(workflow, /python scripts\/build_seo_pages\.py --output-root _site/);
assert.doesNotMatch(workflow, /cp site-v2\/index\.html/);
assert.match(workflow, /cp site-v2\/og\.png/);
assert.match(workflow, /cp site-v2\/config\.js/);
assert.match(workflow, /test ! -e _site\/approval-backend\.gs/);
assert.match(workflow, /cp data\/public-historical-proof\.json _site\/historical-proof\.json/);
assert.match(completedWorkflow, /cron: "0 12 \* \* \*"/);
assert.match(completedWorkflow, /for attempt in \{1\.\.6\}/);
assert.match(completedWorkflow, /sleep 300/);
assert.match(completedWorkflow, /update_completed_draw_report\.py[\s\S]*--stage-only/);
assert.doesNotMatch(midnightWorkflow, /schedule:/);
assert.match(midnightWorkflow, /date -d 'yesterday'/);
assert.match(midnightWorkflow, /update_completed_draw_report\.py --draw-date "\$LOCK_DATE"/);
assert.doesNotMatch(midnightWorkflow, /GOOGLE_SERVICE_ACCOUNT_JSON/);
assert.match(completedScript, /POST_DRAW_ONLY_NO_PREDICTIONS_NO_STAKES_NO_FINANCIAL_PNL/);
assert.match(completedScript, /Số được lưu theo 7 lớp báo cáo" not in block/);
assert.match(completedScript, /public-historical-proof\.json/);
assert.match(completedScript, /stage_only/);
assert.doesNotMatch(completedScript, /plan_next_day|actual_order|pnl_vnd/i);

console.log("Simple daily AI data report site smoke checks passed.");
