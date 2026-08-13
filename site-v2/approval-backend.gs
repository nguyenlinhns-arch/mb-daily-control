/**
 * 4SO AI order approval service for Google Apps Script.
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
    const subject = `[4SO AI] Khách báo đã chuyển khoản – ${code}`;
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
    MailApp.sendEmail({ to: OWNER_EMAIL, subject, htmlBody: html, name: "4SO AI Website" });
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
  // Replace this retrospective sample with the corresponding already-published
  // report artifact. Never place future lottery picks or betting advice here.
  const labels = { day: "Gói 1 ngày", week: "Gói 1 tuần", month: "Gói 1 tháng" };
  return {
    title: `Báo cáo dữ liệu AI – ${labels[plan] || "Đã xác nhận"}`,
    summary: "Báo cáo sử dụng dữ liệu đã được công bố đến ngày hôm trước và chỉ phục vụ phân tích hồi cứu.",
    metrics: [
      { label: "Trạng thái dữ liệu", value: "Đã khóa" },
      { label: "Cửa sổ phân tích", value: "7 / 30 ngày" },
      { label: "Dữ liệu tương lai", value: "Không sử dụng" }
    ],
    notes: [
      "Nguồn và ngày khóa dữ liệu được ghi rõ trong báo cáo.",
      "Có bảng đối chiếu và mô tả biến động lịch sử.",
      "Không bao gồm dự đoán, số khuyến nghị hoặc cam kết kết quả tương lai."
    ],
    url: `${SITE_URL}mau-bao-cao.html`
  };
}

function getOrderSheet() {
  const properties = PropertiesService.getScriptProperties();
  let spreadsheetId = properties.getProperty("ORDER_SHEET_ID");
  let spreadsheet;
  if (!spreadsheetId) {
    spreadsheet = SpreadsheetApp.create("4SO AI – Xác nhận thanh toán");
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

