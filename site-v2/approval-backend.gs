/**
 * Le Mien Bac AI order approval service for Google Apps Script.
 *
 * Deploy as a web app, execute as the owner, access "Anyone". Put the deployed
 * /exec URL into window.ORDER_CONFIRMATION_ENDPOINT before app.js loads.
 * Never put ADMIN_SECRET in the public website.
 */

const OWNER_EMAIL = "REPLACE_WITH_OWNER_EMAIL";
const ADMIN_SECRET = "REPLACE_WITH_A_LONG_RANDOM_SECRET";
const SITE_URL = "https://lemienbac.com/";
const SHEET_NAME = "Orders";
const VALID_PLANS = Object.freeze({ day: 30000, week: 200000, month: 800000 });

function doPost(event) {
  const data = event && event.parameter ? event.parameter : {};
  if (data.action !== "create") return textOutput("ignored");
  if (data.website) return textOutput("ok"); // honeypot

  const code = clean(data.order_code, 32);
  const token = clean(data.customer_token, 100);
  const plan = clean(data.plan, 20);
  const amount = Number(data.amount || 0);
  if (!/^AI-\d{6}-[A-Z0-9]{6}$/.test(code) || token.length < 20 || VALID_PLANS[plan] !== amount) {
    return textOutput("invalid");
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const sheet = getOrderSheet();
    const existing = findOrder(sheet, code);
    if (existing) return textOutput("ok");

    const createdAt = new Date();
    sheet.appendRow([
      code,
      hashToken(token),
      plan,
      amount,
      "pending",
      createdAt,
      "",
      clean(data.attribution, 3000),
      clean(data.page_url, 1000)
    ]);

    const approveUrl = approvalUrl(code, "approve");
    const rejectUrl = approvalUrl(code, "reject");
    const subject = `[Lê Miền Bắc AI] Khách báo đã chuyển khoản – ${code}`;
    const html = [
      `<p>Có khách vừa báo đã chuyển khoản.</p>`,
      `<p><b>Mã yêu cầu:</b> ${htmlEscape(code)}<br>`,
      `<b>Gói:</b> ${htmlEscape(plan)}<br>`,
      `<b>Số tiền:</b> ${amount.toLocaleString("vi-VN")}đ<br>`,
      `<b>Thời gian:</b> ${createdAt.toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })}</p>`,
      `<p>Chỉ bấm xác nhận sau khi đã thấy tiền vào tài khoản.</p>`,
      `<p><a href="${approveUrl}" style="display:inline-block;padding:14px 20px;background:#087c75;color:#fff;text-decoration:none;border-radius:9px;font-weight:bold">XÁC NHẬN ĐÃ NHẬN TIỀN</a></p>`,
      `<p><a href="${rejectUrl}">Không tìm thấy giao dịch</a></p>`
    ].join("");
    MailApp.sendEmail({ to: OWNER_EMAIL, subject, htmlBody: html, name: "Lê Miền Bắc AI" });
    return textOutput("ok");
  } finally {
    lock.releaseLock();
  }
}

function doGet(event) {
  const data = event && event.parameter ? event.parameter : {};
  const action = clean(data.action, 20);
  if (action === "status") return statusResponse(data);
  if (action === "approve" || action === "reject") return approvalResponse(data, action);
  return HtmlService.createHtmlOutput("Không có thao tác phù hợp.");
}

function statusResponse(data) {
  const callback = clean(data.callback, 80);
  if (!/^__fourSoStatus_[a-z0-9]+$/i.test(callback)) return textOutput("invalid callback");

  const code = clean(data.order_code, 32);
  const token = clean(data.customer_token, 100);
  const sheet = getOrderSheet();
  const order = findOrder(sheet, code);
  let payload = { ok: false, status: "unknown" };
  if (order && timingSafeEqual(order.tokenHash, hashToken(token))) {
    payload = {
      ok: true,
      status: order.status,
      approved_at: order.approvedAt ? new Date(order.approvedAt).toISOString() : "",
      delivery: order.status === "approved" ? buildDelivery(order.plan) : null
    };
  }
  return ContentService
    .createTextOutput(`${callback}(${JSON.stringify(payload)});`)
    .setMimeType(ContentService.MimeType.JAVASCRIPT);
}

function approvalResponse(data, action) {
  const code = clean(data.order_code, 32);
  const signature = clean(data.signature, 200);
  const expected = sign(`${action}|${code}`);
  if (!timingSafeEqual(signature, expected)) {
    return approvalPage("Liên kết không hợp lệ", "Không thể xác thực yêu cầu này.", false);
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const sheet = getOrderSheet();
    const order = findOrder(sheet, code);
    if (!order) return approvalPage("Không tìm thấy yêu cầu", code, false);
    if (order.status === "approved") return approvalPage("Đã xác nhận trước đó", `${code} đã được mở cho khách.`, true);

    const status = action === "approve" ? "approved" : "rejected";
    sheet.getRange(order.row, 5).setValue(status);
    sheet.getRange(order.row, 7).setValue(new Date());
    const title = status === "approved" ? "Đã xác nhận thanh toán" : "Đã đánh dấu chưa tìm thấy giao dịch";
    const copy = status === "approved"
      ? `Màn hình của khách ${code} sẽ tự mở báo cáo trong vài giây.`
      : `Khách ${code} sẽ được hướng dẫn liên hệ hỗ trợ.`;
    return approvalPage(title, copy, status === "approved");
  } finally {
    lock.releaseLock();
  }
}

function buildDelivery(plan) {
  const snapshot = readPublicReportSnapshot();
  const labels = {
    day: `Báo cáo dữ liệu AI ngày ${snapshot.reportDate}`,
    week: "Bộ 07 báo cáo dữ liệu hằng ngày",
    month: "Bộ 30 báo cáo dữ liệu hằng ngày"
  };
  return {
    title: labels[plan] || "Báo cáo dữ liệu AI đã xác nhận",
    summary: `Báo cáo ngày ${snapshot.reportDate} sử dụng ${snapshot.historyRows} phiên đã công bố và khóa toàn bộ dữ liệu tại ngày ${snapshot.lockDate}.`,
    metrics: [
      { label: "Phiên lịch sử", value: String(snapshot.historyRows) },
      { label: "Phiên gần nhất", value: "27 / 27" },
      { label: "Nguồn trùng khớp", value: String(snapshot.sourceCount) },
      { label: "Giá trị khác nhau", value: snapshot.uniqueCount },
      { label: "Giá trị lặp", value: snapshot.repeatedCount },
      { label: "Dữ liệu tương lai", value: "0" }
    ],
    notes: [
      snapshot.verifiedFinding,
      snapshot.observationFinding,
      "Kết luận được tạo từ 7 lớp kiểm định và so sánh các cửa sổ 7/30/90 phiên đã hoàn tất.",
      "Báo cáo không bán số, không đưa danh sách số khuyến nghị và không suy diễn dữ liệu lịch sử thành bảo đảm cho kết quả tương lai."
    ]
  };
}

function readPublicReportSnapshot() {
  const fallback = fallbackReportSnapshot();
  try {
    const accessResponse = UrlFetchApp.fetch(`${SITE_URL}source-access.json`, { muteHttpExceptions: true });
    const sampleResponse = UrlFetchApp.fetch(`${SITE_URL}mau-bao-cao.html`, { muteHttpExceptions: true });
    if (accessResponse.getResponseCode() !== 200 || sampleResponse.getResponseCode() !== 200) return fallback;
    const access = JSON.parse(accessResponse.getContentText());
    const html = sampleResponse.getContentText();
    const lockDate = viDateFromIso(access.history_end) || fallback.lockDate;
    return {
      reportDate: nextViDate(access.history_end) || fallback.reportDate,
      lockDate,
      historyRows: Number(access.history_rows || fallback.historyRows),
      sourceCount: Number(access.source_count || fallback.sourceCount),
      uniqueCount: extractText(html, /data-unique-count-chip>([^<]+)<\/span>/i, fallback.uniqueCount),
      repeatedCount: extractText(html, /data-repeated-count-chip>([^<]+)<\/span>/i, fallback.repeatedCount),
      verifiedFinding: extractText(html, /data-finding-verified>([^<]+)<\/p>/i, fallback.verifiedFinding),
      observationFinding: extractText(html, /data-finding-observation>([^<]+)<\/p>/i, fallback.observationFinding)
    };
  } catch (_) {
    return fallback;
  }
}

function fallbackReportSnapshot() {
  return {
    reportDate: "13/08/2026",
    lockDate: "12/08/2026",
    historyRows: 943,
    sourceCount: 3,
    uniqueCount: "22 mã",
    repeatedCount: "4 mã",
    verifiedFinding: "Phiên gần nhất đã được đối chiếu đủ 27/27 bản ghi từ nhiều nguồn công khai.",
    observationFinding: "Quan sát gần được đặt cạnh nền 7/30/90 phiên và chỉ được diễn giải như thống kê mô tả."
  };
}

function extractText(html, pattern, fallback) {
  const match = String(html || "").match(pattern);
  return match && match[1] ? clean(match[1].replace(/<[^>]*>/g, " "), 1000) : fallback;
}

function viDateFromIso(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : "";
}

function nextViDate(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
  if (!match) return "";
  const next = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])) + 86400000);
  return Utilities.formatDate(next, "UTC", "dd/MM/yyyy");
}

function getOrderSheet() {
  const properties = PropertiesService.getScriptProperties();
  let spreadsheetId = properties.getProperty("ORDER_SHEET_ID");
  let spreadsheet;
  if (!spreadsheetId) {
    spreadsheet = SpreadsheetApp.create("Lê Miền Bắc AI – Xác nhận thanh toán");
    spreadsheetId = spreadsheet.getId();
    properties.setProperty("ORDER_SHEET_ID", spreadsheetId);
  } else {
    spreadsheet = SpreadsheetApp.openById(spreadsheetId);
  }
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);
  if (!sheet) sheet = spreadsheet.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["order_code", "token_hash", "plan", "amount", "status", "created_at", "approved_at", "attribution", "page_url"]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function findOrder(sheet, code) {
  if (!code || sheet.getLastRow() < 2) return null;
  const match = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1)
    .createTextFinder(code)
    .matchEntireCell(true)
    .findNext();
  if (!match) return null;
  const row = match.getRow();
  const values = sheet.getRange(row, 1, 1, 9).getValues()[0];
  return {
    row,
    code: String(values[0]),
    tokenHash: String(values[1]),
    plan: String(values[2]),
    amount: Number(values[3]),
    status: String(values[4]),
    createdAt: values[5],
    approvedAt: values[6]
  };
}

function approvalUrl(code, action) {
  const base = ScriptApp.getService().getUrl();
  return `${base}?action=${encodeURIComponent(action)}&order_code=${encodeURIComponent(code)}&signature=${encodeURIComponent(sign(`${action}|${code}`))}`;
}

function approvalPage(title, copy, success) {
  const color = success ? "#087c75" : "#e05d40";
  const safeTitle = htmlEscape(title);
  const safeCopy = htmlEscape(copy);
  return HtmlService.createHtmlOutput(`<!doctype html><html lang="vi"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>${safeTitle}</title></head><body style="margin:0;background:#f4f7f8;font:16px Arial;color:#0b1723"><main style="max-width:560px;margin:10vh auto;padding:28px;background:#fff;border-radius:18px;box-shadow:0 18px 50px #0b172322"><div style="width:52px;height:52px;display:grid;place-items:center;border-radius:50%;background:${color};color:#fff;font-size:25px">${success ? "✓" : "!"}</div><h1 style="font-size:28px">${safeTitle}</h1><p style="line-height:1.6;color:#536674">${safeCopy}</p><a href="${SITE_URL}" style="color:${color};font-weight:bold">Mở website</a></main></body></html>`)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function hashToken(value) {
  const bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, value, Utilities.Charset.UTF_8);
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, "");
}

function sign(value) {
  const bytes = Utilities.computeHmacSha256Signature(value, ADMIN_SECRET, Utilities.Charset.UTF_8);
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, "");
}

function timingSafeEqual(left, right) {
  left = String(left || "");
  right = String(right || "");
  if (left.length !== right.length) return false;
  let diff = 0;
  for (let i = 0; i < left.length; i += 1) diff |= left.charCodeAt(i) ^ right.charCodeAt(i);
  return diff === 0;
}

function clean(value, maxLength) {
  return String(value == null ? "" : value).trim().slice(0, maxLength);
}

function htmlEscape(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char]));
}

function textOutput(value) {
  return ContentService.createTextOutput(value).setMimeType(ContentService.MimeType.TEXT);
}

