import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd(), "site-v2");
const read = (name) => readFile(resolve(root, name), "utf8");
const [
  index,
  styles,
  app,
  legal,
  sample,
  workflow,
  completedWorkflow,
  completedScript,
  sourceAccessRaw,
  midnightWorkflow,
  historicalProofRaw
] = await Promise.all([
  read("index.html"),
  read("styles.css"),
  read("app.js"),
  read("legal.html"),
  read("mau-bao-cao.html"),
  readFile(resolve(process.cwd(), ".github/workflows/pages.yml"), "utf8"),
  readFile(resolve(process.cwd(), ".github/workflows/completed-draw-daily-1900.yml"), "utf8"),
  readFile(resolve(process.cwd(), "scripts/update_completed_draw_report.py"), "utf8"),
  readFile(resolve(process.cwd(), "data/source-access.json"), "utf8"),
  readFile(resolve(process.cwd(), ".github/workflows/daily-report-midnight.yml"), "utf8"),
  readFile(resolve(process.cwd(), "data/public-historical-proof.json"), "utf8")
]);
const sourceAccess = JSON.parse(sourceAccessRaw);
const historicalProof = JSON.parse(historicalProofRaw);

for (const file of ["styles.css", "app.js", "mau-bao-cao.html", "legal.html", "robots.txt", "sitemap.xml", "404.html", "favicon.svg"]) {
  assert.ok(await read(file), `${file} must not be empty`);
}
assert.ok((await stat(resolve(root, "og.png"))).size > 100_000, "og.png must be a real social preview image");

// One clearly described daily report, one clear price, and one simple delivery flow.
assert.match(index, /BÁO CÁO DỮ LIỆU AI NGÀY/i);
assert.match(index, /Báo cáo dữ liệu AI[\s\S]*ngày hôm nay/i);
assert.match(index, /30\.000đ/);
assert.match(index, /Thanh toán một lần · Không tự gia hạn/i);
assert.match(index, /khỏi tự gom|Không cần tự gom/i);
assert.match(index, /80%/);
assert.match(index, /24\/30 ngày/);
assert.match(index, /14\/07\/2026–12\/08\/2026/);
assert.match(index, /Có cả ngày xuất hiện và không xuất hiện/i);
assert.match(index, /Số được lưu theo 7 lớp báo cáo/i);
assert.match(index, /6 phương pháp độc lập và 1 lớp tổng hợp 4SO/i);
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
assert.equal((index.match(/role="listitem"/g) || []).length, 7);
assert.doesNotMatch(index, /200\.000đ|800\.000đ|07 BÁO CÁO HẰNG NGÀY|30 BÁO CÁO HẰNG NGÀY/);
assert.doesNotMatch(index, /config\.js/);

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
assert.equal(sourceAccess.history_end, viDateToIso(reportDateMatch[2]), "public source record must match the displayed lock date");
assert.match(index, new RegExp(`Báo cáo cho ngày hôm nay \\(${reportDateMatch[1].replaceAll("/", "\\/")}\\)`, "i"));
assert.match(index, new RegExp(`Dữ liệu khóa đến hết ngày hôm qua \\(${reportDateMatch[2].replaceAll("/", "\\/")}\\)`, "i"));
assert.ok(index.indexOf('id="methods"') < index.indexOf('id="buy"'));
assert.doesNotMatch(index, /id="included"|id="about"|faq-section|steps-section|pricing-section/);

// Future-pick, betting and unverifiable-performance copy must stay absent.
const publicCopy = `${index}\n${sample}\n${legal}`;
assert.doesNotMatch(publicCopy, /hôm nay đánh|chốt số|số đẹp|bao lô|xiên|cam kết trúng/i);
assert.doesNotMatch(publicCopy, /15\.000/i);
assert.doesNotMatch(publicCopy, /mở kết luận|kết luận 1 số|kết luận 2 số|kết luận 4 số|dàn số/i);
assert.doesNotMatch(publicCopy, /MB THANG/i);
assert.doesNotMatch(publicCopy, />[^<]*0398[^<]*</i);
assert.match(publicCopy, /không bán số/i);
assert.match(publicCopy, /Tỷ lệ 80% chỉ mô tả cửa sổ lịch sử đã hoàn tất, không phải xác suất hoặc cam kết/i);

// Evidence and the public sample must remain inspectable.
assert.equal(historicalProof.schema_version, "MB_PUBLIC_HISTORICAL_PROOF_V1_COMPLETED_ONLY");
assert.equal(historicalProof.validation.hit_days * 100, historicalProof.validation.rate_pct * historicalProof.validation.total_days);
assert.equal(historicalProof.recent_period.days.length, historicalProof.recent_period.total_days);
assert.equal(historicalProof.recent_period.days.filter((day) => day.observed.length > 0).length, historicalProof.recent_period.hit_days);
assert.equal(historicalProof.method_snapshot.layers.length, 7);
assert.equal(historicalProof.method_snapshot.target_date, "2026-08-12");
assert.equal(historicalProof.method_snapshot.data_lock, "2026-08-11");
assert.equal((index.match(/class="history-day-row"/g) || []).length, historicalProof.recent_period.total_days);
assert.equal((index.match(/class="historical-method-row/g) || []).length, historicalProof.method_snapshot.layers.length);
for (const day of historicalProof.recent_period.days) assert.match(index, new RegExp(day.date.split("-").reverse().join("\\/")));
assert.match(index, /href="\/historical-proof\.json"/);
assert.match(index, new RegExp(`${sourceAccess.history_rows}[\\s\\S]*phiên lịch sử`));
assert.match(index, /27\/27[\s\S]*bản ghi/);
assert.match(index, new RegExp(`<strong>${sourceAccess.source_count}<\\/strong> nguồn khớp`));
assert.match(index, new RegExp(sourceAccess.latest_codes_sha256.slice(0, 16)));
assert.ok(sample.includes(`Báo cáo cho ngày hôm nay: ${reportDateMatch[1]}`));
assert.ok(sample.includes(`Dữ liệu khóa đến hết ngày hôm qua: ${reportDateMatch[2]}`));
assert.match(sample, /4SO ngày 25\/07\/2026/);
assert.match(sample, /<strong>52<\/strong>[\s\S]*<strong>83<\/strong>[\s\S]*<strong>54<\/strong>[\s\S]*<strong>90<\/strong>/);
assert.match(sample, /mẫu lịch sử đã hoàn tất/i);
assert.match(sample, /không phải 4SO của ngày hôm nay/i);
assert.match(sample, /7 phương pháp/i);
assert.match(sample, /Mọi thứ gọn trong một màn hình/i);

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
assert.match(workflow, /cp data\/public-historical-proof\.json _site\/historical-proof\.json/);
assert.match(completedWorkflow, /cron: "0 12 \* \* \*"/);
assert.match(completedWorkflow, /for attempt in \{1\.\.6\}/);
assert.match(completedWorkflow, /sleep 300/);
assert.match(completedWorkflow, /update_completed_draw_report\.py[\s\S]*--stage-only/);
assert.match(midnightWorkflow, /cron: "0 17 \* \* \*"/);
assert.match(midnightWorkflow, /date -d 'yesterday'/);
assert.match(midnightWorkflow, /update_completed_draw_report\.py --draw-date "\$LOCK_DATE"/);
assert.match(completedScript, /POST_DRAW_ONLY_NO_PREDICTIONS_NO_STAKES_NO_FINANCIAL_PNL/);
assert.match(completedScript, /Số được lưu theo 7 lớp báo cáo/);
assert.match(completedScript, /public-historical-proof\.json/);
assert.match(completedScript, /stage_only/);
assert.doesNotMatch(completedScript, /plan_next_day|actual_order|pnl_vnd/i);

console.log("Simple daily AI data report site smoke checks passed.");
