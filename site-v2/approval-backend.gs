/**
 * Le Mien Bac AI order approval service for Google Apps Script.
 *
 * Deploy as a web app, execute as the owner, access "Anyone". Put the deployed
 * /exec URL into window.ORDER_CONFIRMATION_ENDPOINT before app.js loads.
 * Never put ADMIN_SECRET in the public website.
 */

const SITE_URL = "https://lemienbac.com/";
const SHEET_NAME = "Orders";
const PAID_REPORT_SHEET_NAME = "Paid_Report";
const DELIVERY_SCHEMA = "fourso-top2-v1";
const VALID_PLANS = Object.freeze({ day: 30000, week: 200000, month: 800000 });
const SERVICE_NAME = "Lê Miền Bắc AI order approval";
const SERVICE_VERSION = "1.0";

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
    MailApp.sendEmail({ to: ownerEmail(), subject, htmlBody: html, name: "Lê Miền Bắc AI" });
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
  if (action === "daily005") return dailyMbWebRun_();
  return jsonOutput({ ok: true, service: SERVICE_NAME, version: SERVICE_VERSION });
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
  const report = readPaidFourSoReport();
  return {
    schema: DELIVERY_SCHEMA,
    title: `4SO ngày ${report.reportDate}`,
    pairs: [
      { rank: 1, numbers: [report.top1Left, report.top1Right] },
      { rank: 2, numbers: [report.top2Left, report.top2Right] }
    ]
  };
}

function readPaidFourSoReport() {
  const spreadsheetId = PropertiesService.getScriptProperties().getProperty("ORDER_SHEET_ID");
  if (!spreadsheetId) throw new Error("ORDER_SHEET_ID is not configured");

  const sheet = SpreadsheetApp.openById(spreadsheetId).getSheetByName(PAID_REPORT_SHEET_NAME);
  if (!sheet || sheet.getLastRow() < 2) throw new Error("Paid 4SO report is not available");

  const values = sheet.getRange(2, 1, 1, 7).getDisplayValues()[0];
  const report = {
    reportDate: clean(values[0], 10),
    lockDate: clean(values[1], 10),
    top1Left: clean(values[2], 2),
    top1Right: clean(values[3], 2),
    top2Left: clean(values[4], 2),
    top2Right: clean(values[5], 2)
  };
  const snapshot = readPublicReportSnapshot();
  const codes = [report.top1Left, report.top1Right, report.top2Left, report.top2Right];
  if (
    !/^\d{2}\/\d{2}\/\d{4}$/.test(report.reportDate)
    || !/^\d{2}\/\d{2}\/\d{4}$/.test(report.lockDate)
    || codes.some((code) => !/^\d{2}$/.test(code))
    || report.reportDate !== snapshot.reportDate
    || report.lockDate !== snapshot.lockDate
  ) {
    throw new Error("Paid 4SO report does not match the current report date");
  }
  return report;
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
  const bytes = Utilities.computeHmacSha256Signature(value, adminSecret(), Utilities.Charset.UTF_8);
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, "");
}

function ownerEmail() {
  const properties = PropertiesService.getScriptProperties();
  let value = clean(properties.getProperty("OWNER_EMAIL"), 320);
  if (!value) {
    value = clean(Session.getEffectiveUser().getEmail(), 320);
    if (!value) throw new Error("OWNER_EMAIL is not available for this deployment");
    properties.setProperty("OWNER_EMAIL", value);
  }
  return value;
}

function adminSecret() {
  const properties = PropertiesService.getScriptProperties();
  let value = clean(properties.getProperty("ADMIN_SECRET"), 500);
  if (!value) {
    value = `${Utilities.getUuid()}${Utilities.getUuid()}${Utilities.getUuid()}`;
    properties.setProperty("ADMIN_SECRET", value);
  }
  return value;
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

function jsonOutput(value) {
  return ContentService
    .createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

/*
 * Daily 00:05 private pipeline.
 *
 * This runs inside the owner's Apps Script account, so the paid TOP1/TOP2
 * values never pass through GitHub or the public website repository.
 */
const DAILY_MB_TZ = "Asia/Ho_Chi_Minh";
const DAILY_MB_SOURCE_SHEET_ID = "1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w";
const DAILY_MB_HISTORY_TABS = Object.freeze(["MB_History_27", "MB_History_27_IMPORT"]);
const DAILY_MB_CONFIG_TAB = "V32_Private_Config";
const DAILY_MB_PNL_TAB = "Linh";
const DAILY_MB_METHOD_ID = "MB_4SO_V1";
const DAILY_MB_CONFIG_ID = "MB_4SO_PRIMARY_V1_20260731";
const DAILY_MB_ALGORITHM_ID = "MB_4SO_TOP2_2SO_T1_V1";
const DAILY_MB_POINTS_PER_CODE = 50;
const DAILY_MB_COST_PER_POINT = 23000;
const DAILY_MB_PAYOUT_PER_HIT_POINT = 80000;
const DAILY_MB_MAX_ATTEMPTS = 6;

function dailyMbWebRun_() {
  const today = Utilities.formatDate(new Date(), DAILY_MB_TZ, "yyyy-MM-dd");
  const properties = PropertiesService.getScriptProperties();
  if (properties.getProperty("DAILY_MB_WEB_LAST_SUCCESS") === today) {
    return textOutput(`DAILY_MB_005_ALREADY_DONE target=${today}`);
  }
  const minuteOfDay = Number(Utilities.formatDate(new Date(), DAILY_MB_TZ, "H")) * 60
    + Number(Utilities.formatDate(new Date(), DAILY_MB_TZ, "m"));
  if (minuteOfDay > 60) return textOutput("DAILY_MB_005_OUTSIDE_WINDOW");
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    if (properties.getProperty("DAILY_MB_WEB_LAST_SUCCESS") === today) {
      return textOutput(`DAILY_MB_005_ALREADY_DONE target=${today}`);
    }
    const result = dailyMbPipeline_(dailyMbAddDays_(today, -1), today);
    properties.setProperty("DAILY_MB_WEB_LAST_SUCCESS", today);
    return textOutput(result);
  } catch (error) {
    const message = String(error && error.stack ? error.stack : error);
    return textOutput(`DAILY_MB_005_ERROR ${message.slice(0, 1500)}`);
  } finally {
    lock.releaseLock();
  }
}

function dailyMbPipeline_(lockIso, targetIso) {
  if (targetIso !== dailyMbAddDays_(lockIso, 1)) throw new Error("Target must be exactly T after DATA_LOCK");
  const today = Utilities.formatDate(new Date(), DAILY_MB_TZ, "yyyy-MM-dd");
  if (lockIso >= today) throw new Error("DATA_LOCK must be a completed day");

  const latest = dailyMbCrosscheck_(lockIso);
  const sourceBook = SpreadsheetApp.openById(DAILY_MB_SOURCE_SHEET_ID);
  const history = dailyMbSyncHistory_(sourceBook, lockIso, latest.codes);
  const ranked = dailyMbScorePairs_(history);
  const ids = dailyMbPrivateIds_(sourceBook);
  const pnlBook = SpreadsheetApp.openById(ids.pnlSheetId);
  const paidBook = SpreadsheetApp.openById(ids.paidReportSheetId);

  dailyMbSettlePaid_(pnlBook, paidBook, history, lockIso, targetIso);
  dailyMbRecordRun_(sourceBook, targetIso, lockIso, ranked, history);
  dailyMbUpdatePaid_(paidBook, targetIso, lockIso, ranked);
  dailyMbVerifyNoDuplicates_(pnlBook, paidBook, sourceBook, lockIso, targetIso);
  return `DAILY_MB_005_OK lock=${lockIso} target=${targetIso} sources=${latest.sources.length} pairs=45 paid_codes=PRIVATE`;
}

function dailyMbCrosscheck_(iso) {
  const dmy = dailyMbDmyDash_(iso);
  const sources = [
    ["xosodaiphat", `https://xosodaiphat.com/xsmb-${dmy}.html`],
    ["xosothienphu", `https://xosothienphu.vn/xsmb-${dmy}.html`],
    ["xoso.com.vn", `https://xoso.com.vn/xsmb-${dmy}.html`],
    ["minhngoc", `https://www.minhngoc.net.vn/ket-qua-xo-so/mien-bac/${dmy}.html`],
    ["kqxs", `https://kqxs.vn/mien-bac/xsmb-${dmy}`],
    ["ketqua", `https://ketqua.net/xo-so-truyen-thong.php?ngay=${dmy}`]
  ];
  const groups = {};
  const failures = [];
  sources.forEach(([name, url]) => {
    try {
      const response = UrlFetchApp.fetch(url, {
        muteHttpExceptions: true,
        followRedirects: true,
        headers: {
          "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
          "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7"
        }
      });
      if (response.getResponseCode() !== 200) throw new Error(`HTTP ${response.getResponseCode()}`);
      const codes = dailyMbParsePrizes_(response.getContentText());
      const key = codes.join("|");
      if (!groups[key]) groups[key] = { codes, sources: [] };
      groups[key].sources.push({ source: name, url, codes_sha256: dailyMbSha256_(key) });
    } catch (error) {
      failures.push(`${name}:${String(error).slice(0, 160)}`);
    }
  });
  const variants = Object.keys(groups).map((key) => groups[key]);
  variants.sort((a, b) => b.sources.length - a.sources.length || b.codes.join("").localeCompare(a.codes.join("")));
  if (!variants.length || variants[0].sources.length < 2) {
    throw new Error(`DAILY_MB_SOURCE_NOT_READY ${iso}; variants=${variants.map((v) => v.sources.length).join(",")}; failures=${failures.join(";")}`);
  }
  return variants[0];
}

function dailyMbParsePrizes_(html) {
  const plain = dailyMbStripHtml_(html);
  const labels = {
    DB: "(?:G\\s*\\.\\s*(?:ĐB|DB)|Giải\\s*(?:ĐB|DB|Đặc\\s*biệt)|Đặc\\s*biệt|ĐB)",
    G1: "(?:G\\s*\\.\\s*1|Giải\\s*(?:nhất|1)(?![0-9]))",
    G2: "(?:G\\s*\\.\\s*2|Giải\\s*(?:nhì|hai|2)(?![0-9]))",
    G3: "(?:G\\s*\\.\\s*3|Giải\\s*(?:ba|3)(?![0-9]))",
    G4: "(?:G\\s*\\.\\s*4|Giải\\s*(?:tư|bốn|4)(?![0-9]))",
    G5: "(?:G\\s*\\.\\s*5|Giải\\s*(?:năm|5)(?![0-9]))",
    G6: "(?:G\\s*\\.\\s*6|Giải\\s*(?:sáu|6)(?![0-9]))",
    G7: "(?:G\\s*\\.\\s*7|Giải\\s*(?:bảy|7)(?![0-9]))"
  };
  const prizes = [["DB", 5, 1], ["G1", 5, 1], ["G2", 5, 2], ["G3", 5, 6], ["G4", 4, 4], ["G5", 4, 6], ["G6", 3, 3], ["G7", 2, 4]];
  const dbMatches = dailyMbAllMatches_(plain, labels.DB, 0, plain.length);
  for (let startIndex = 0; startIndex < dbMatches.length; startIndex += 1) {
    let current = dbMatches[startIndex];
    const output = [];
    let ok = true;
    for (let index = 0; index < prizes.length; index += 1) {
      const [key, width, count] = prizes[index];
      if (index > 0) {
        current = dailyMbFirstMatch_(plain, labels[key], current.end, Math.min(plain.length, current.end + 800));
        if (!current) { ok = false; break; }
      }
      let blockEnd = Math.min(plain.length, current.end + 800);
      if (index + 1 < prizes.length) {
        const nextKey = prizes[index + 1][0];
        const next = dailyMbFirstMatch_(plain, labels[nextKey], current.end, blockEnd);
        if (!next) { ok = false; break; }
        blockEnd = next.start;
      } else {
        blockEnd = Math.min(plain.length, current.end + 160);
      }
      const block = plain.slice(current.end, blockEnd);
      const values = dailyMbNumbers_(block, width).slice(0, count);
      if (values.length !== count) { ok = false; break; }
      values.forEach((number) => output.push(number.slice(-2)));
    }
    if (ok && output.length === 27) return output;
  }
  throw new Error("Không tách được đủ 27 giải DB→G7");
}

function dailyMbStripHtml_(raw) {
  return String(raw || "")
    .replace(/<(script|style|noscript)\b[^>]*>[\s\S]*?<\/\1>/gi, " ")
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;|&#160;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, "\"")
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&#(\d+);/g, (_, value) => String.fromCharCode(Number(value)))
    .replace(/\s+/g, " ")
    .trim();
}

function dailyMbAllMatches_(text, pattern, start, end) {
  const selected = text.slice(start, end);
  const regex = new RegExp(pattern, "gi");
  const result = [];
  let match;
  while ((match = regex.exec(selected)) !== null) {
    result.push({ start: start + match.index, end: start + regex.lastIndex });
    if (match[0].length === 0) regex.lastIndex += 1;
  }
  return result;
}

function dailyMbFirstMatch_(text, pattern, start, end) {
  const values = dailyMbAllMatches_(text, pattern, start, end);
  return values.length ? values[0] : null;
}

function dailyMbNumbers_(text, width) {
  const regex = new RegExp(`(^|[^0-9])([0-9]{${width}})(?![0-9])`, "g");
  const values = [];
  let match;
  while ((match = regex.exec(text)) !== null) values.push(match[2]);
  return values;
}

function dailyMbSyncHistory_(book, lockIso, lockCodes) {
  const sheets = DAILY_MB_HISTORY_TABS.map((name) => {
    const sheet = book.getSheetByName(name);
    if (!sheet) throw new Error(`Missing canonical history tab ${name}`);
    return sheet;
  });
  let history = dailyMbReadHistory_(sheets[0]);
  let mirror = dailyMbReadHistory_(sheets[1]);
  if (JSON.stringify(history) !== JSON.stringify(mirror)) throw new Error("Canonical history tabs differ");
  if (!history.length) throw new Error("Canonical history is empty");
  let latest = history[history.length - 1][0];
  if (latest > lockIso) throw new Error(`Canonical history is ahead of DATA_LOCK: ${latest}`);
  while (latest < lockIso) {
    const next = dailyMbAddDays_(latest, 1);
    const codes = next === lockIso ? lockCodes : dailyMbCrosscheck_(next).codes;
    const row = [next].concat(codes);
    sheets.forEach((sheet) => sheet.appendRow(row));
    history.push(row);
    latest = next;
  }
  const existing = history.filter((row) => row[0] === lockIso);
  if (existing.length !== 1 || existing[0].slice(1).join("|") !== lockCodes.join("|")) {
    throw new Error("Canonical source conflicts with public cross-check");
  }
  history = dailyMbReadHistory_(sheets[0]);
  mirror = dailyMbReadHistory_(sheets[1]);
  if (JSON.stringify(history) !== JSON.stringify(mirror) || history[history.length - 1][0] !== lockIso) {
    throw new Error("Canonical history readback failed");
  }
  return history;
}

function dailyMbReadHistory_(sheet) {
  const values = sheet.getDataRange().getDisplayValues();
  const rows = [];
  values.forEach((raw, index) => {
    if (!raw[0] || index === 0 && String(raw[0]).toLowerCase() === "date") return;
    const iso = dailyMbParseDate_(raw[0]);
    const codes = raw.slice(1, 28).map((value) => String(value).trim().padStart(2, "0"));
    if (!iso || codes.length !== 27 || codes.some((code) => !/^\d{2}$/.test(code))) {
      throw new Error(`Invalid history row ${index + 1}`);
    }
    rows.push([iso].concat(codes));
  });
  rows.sort((a, b) => a[0].localeCompare(b[0]));
  for (let index = 1; index < rows.length; index += 1) {
    if (rows[index][0] <= rows[index - 1][0]) throw new Error(`Duplicate or unordered history ${rows[index][0]}`);
  }
  if (rows.length < 365) throw new Error("MB 4SO requires at least 365 locked draws");
  return rows;
}

function dailyMbPrivateIds_(sourceBook) {
  const sheet = sourceBook.getSheetByName(DAILY_MB_CONFIG_TAB);
  if (!sheet) throw new Error("Private config tab is missing");
  const values = sheet.getRange(1, 1, Math.min(20, sheet.getLastRow()), 3).getDisplayValues();
  const config = {};
  values.slice(1).forEach((row) => {
    const key = String(row[0] || "").trim();
    if (!key) return;
    if (Object.prototype.hasOwnProperty.call(config, key)) throw new Error(`Duplicate private config key ${key}`);
    config[key] = String(row[1] || "").trim();
  });
  if (config.CONFIG_VERSION !== "MB_V32_PRIVATE_CONFIG_V1") throw new Error("Private config version mismatch");
  if (!/^[A-Za-z0-9_-]{20,200}$/.test(config.PNL_SHEET_ID || "")) throw new Error("Invalid P/L sheet ID");
  if (!/^[A-Za-z0-9_-]{20,200}$/.test(config.PAID_REPORT_SHEET_ID || "")) throw new Error("Invalid paid report sheet ID");
  return { pnlSheetId: config.PNL_SHEET_ID, paidReportSheetId: config.PAID_REPORT_SHEET_ID };
}

function dailyMbRankPct_(values) {
  const total = values.length;
  return values.map((value) => {
    const lower = values.filter((item) => item < value).length;
    const equal = values.filter((item) => item === value).length;
    return (lower + (equal + 1) / 2) / total;
  });
}

function dailyMbScorePairs_(history) {
  const metrics = [];
  for (let left = 0; left < 10; left += 1) {
    for (let right = left + 1; right < 10; right += 1) {
      const a = String(left) + String(right);
      const b = String(right) + String(left);
      const flags = history.map((row) => row.slice(1).indexOf(a) >= 0 || row.slice(1).indexOf(b) >= 0 ? 1 : 0);
      const hitRate = (window) => {
        const sample = flags.slice(-window);
        return sample.reduce((sum, value) => sum + value, 0) / sample.length;
      };
      const occurrences = (window) => {
        const sample = window ? history.slice(-window) : history;
        return sample.reduce((sum, row) => sum + row.slice(1).filter((code) => code === a || code === b).length, 0);
      };
      let gap = flags.length;
      for (let offset = 0; offset < flags.length; offset += 1) {
        if (flags[flags.length - 1 - offset]) { gap = offset; break; }
      }
      metrics.push({ pair: `${a}-${b}`, left: a, right: b, hit_rate_60: hitRate(60), hit_rate_21: hitRate(21), occurrence_21: occurrences(21), occurrence_all: occurrences(0), hit_rate_365: hitRate(365), gap });
    }
  }
  const hitRanks = dailyMbRankPct_(metrics.map((item) => item.hit_rate_60));
  const gapRanks = dailyMbRankPct_(metrics.map((item) => Math.log1p(item.gap)));
  metrics.forEach((item, index) => {
    item.score = hitRanks[index] + 0.25 * gapRanks[index]
      + 1e-6 * item.hit_rate_60 + 1e-7 * item.hit_rate_21
      + 1e-8 * item.occurrence_21 + 1e-9 * item.occurrence_all
      + 1e-10 * item.hit_rate_365;
  });
  metrics.sort((a, b) => b.score - a.score);
  if (metrics.length !== 45 || new Set(metrics.map((item) => item.pair)).size !== 45) throw new Error("MB 4SO did not score 45 unique pairs");
  if (Math.abs(metrics[1].score - metrics[2].score) <= 1e-12) throw new Error("TIE_REVIEW rank 2 and 3");
  const selected = [metrics[0].left, metrics[0].right, metrics[1].left, metrics[1].right];
  if (new Set(selected).size !== 4) throw new Error("TOP1/TOP2 must contain four distinct codes");
  return metrics;
}

function dailyMbSettlePaid_(pnlBook, paidBook, history, lockIso, targetIso) {
  const pnlSheet = pnlBook.getSheetByName(DAILY_MB_PNL_TAB);
  const paidSheet = paidBook.getSheetByName(PAID_REPORT_SHEET_NAME);
  if (!pnlSheet || !paidSheet || paidSheet.getLastRow() < 2) throw new Error("P/L or Paid_Report tab is missing");
  const paid = paidSheet.getRange(2, 1, 1, 7).getDisplayValues()[0];
  const activeIso = dailyMbParseDate_(paid[0]);
  if (!activeIso || activeIso > targetIso) throw new Error(`Invalid active Paid_Report date ${paid[0]}`);

  const ledgerLast = Math.max(pnlSheet.getLastRow(), 5);
  const ledger = ledgerLast >= 6 ? pnlSheet.getRange(6, 1, ledgerLast - 5, 11).getDisplayValues() : [];
  const matches = ledger.map((row, index) => ({ row, number: index + 6 })).filter((item) => dailyMbParseDate_(item.row[0]) === activeIso && String(item.row[1]).trim().toUpperCase() === "4SO");
  if (matches.length > 1) throw new Error(`Duplicate 4SO P/L rows for ${activeIso}`);
  if (activeIso === targetIso) {
    const lockRows = ledger.filter((row) => dailyMbParseDate_(row[0]) === lockIso && String(row[1]).trim().toUpperCase() === "4SO");
    if (lockRows.length !== 1) throw new Error("Paid report advanced but T-1 P/L is not unique");
    return;
  }
  if (activeIso > lockIso) throw new Error("Paid_Report is neither settled nor current");
  if (matches.length === 1) return;

  const resultRow = history.find((row) => row[0] === activeIso);
  if (!resultRow) throw new Error(`Missing locked result for paid report ${activeIso}`);
  const codes = paid.slice(2, 6).map((value) => String(value).trim().padStart(2, "0"));
  if (codes.length !== 4 || new Set(codes).size !== 4 || codes.some((code) => !/^\d{2}$/.test(code))) throw new Error("Invalid paid codes for settlement");
  const counts = {};
  resultRow.slice(1).forEach((code) => { counts[code] = (counts[code] || 0) + 1; });
  const hitCodes = codes.filter((code) => Number(counts[code] || 0) > 0);
  const totalHits = codes.reduce((sum, code) => sum + Number(counts[code] || 0), 0);
  const points = codes.length * DAILY_MB_POINTS_PER_CODE;
  const capital = points * DAILY_MB_COST_PER_POINT;
  const payout = totalHits * DAILY_MB_POINTS_PER_CODE * DAILY_MB_PAYOUT_PER_HIT_POINT;
  const pnl = payout - capital;
  const previousCumulative = ledger.length ? dailyMbNumber_(ledger[ledger.length - 1][8]) : 0;
  const rowNumber = ledgerLast + 1;
  const detail = hitCodes.length ? hitCodes.map((code) => `${code} × ${counts[code]}`).join("; ") : "—";
  const note = `Tự động quyết toán 4SO ngày ${dailyMbViDate_(activeIso)} lúc 00:05. Báo cáo đã khóa trước kết quả gồm ${codes.join(", ")}, mỗi số ${DAILY_MB_POINTS_PER_CODE} điểm; kết quả nguồn đủ 27/27; tổng ${totalHits} nháy; vốn ${capital}đ; trả thưởng ${payout}đ; P/L ${pnl}đ. SOURCE_METHOD=4SO; AUTO_SETTLED_00_05; outcome_known_at_selection=false.`;
  pnlSheet.getRange(rowNumber, 1, 1, 11).setValues([[
    dailyMbViDate_(activeIso), "4SO", codes.join(", "), hitCodes.length ? hitCodes.join(", ") : "Không trúng", detail,
    totalHits, points, pnl, previousCumulative + pnl, pnl > 0 ? "Thắng" : pnl < 0 ? "Thua" : "Hòa", note
  ]]);
  const readback = pnlSheet.getRange(rowNumber, 1, 1, 11).getDisplayValues()[0];
  if (dailyMbParseDate_(readback[0]) !== activeIso || String(readback[1]).trim().toUpperCase() !== "4SO") throw new Error("P/L settlement readback failed");
}

function dailyMbRecordRun_(book, targetIso, lockIso, ranked, history) {
  const now = Utilities.formatDate(new Date(), DAILY_MB_TZ, "yyyy-MM-dd'T'HH:mm:ssXXX");
  const runId = `MB_4SO_AUTO_${targetIso.replace(/-/g, "")}_0005`;
  const scoreVector = `MB_4SO_TOP45_${targetIso.replace(/-/g, "")}`;
  const top = ranked.slice(0, 4);
  const artifact = dailyMbSha256_(JSON.stringify({ schema: "MB_4SO_DAILY_AUTO_V1", target: targetIso, lock: lockIso, history, top, config: DAILY_MB_CONFIG_ID, algorithm: DAILY_MB_ALGORITHM_ID }));

  dailyMbAppendIfMissing_(book, "MB_FINAL_DECISION_CURRENT", 26,
    (row) => dailyMbParseDate_(row[0]) === targetIso && String(row[5]) === DAILY_MB_ALGORITHM_ID,
    (row) => String(row[11]) === top[0].pair && String(row[14]) === top[1].pair,
    [targetIso, lockIso, now, runId, DAILY_MB_CONFIG_ID, DAILY_MB_ALGORITHM_ID, "MB_4SO_V1 > TOP2_REVERSE_PAIRS > AUTO_00_05", "LOCKED_27_27_HASH_MATCH", "PAID_REPORT_PRIVATE_FIXED50", "FALSE", "FALSE", top[0].pair, top[0].score, 100, top[1].pair, top[1].score, 100, top[2].pair, top[2].score, 0, top[3].pair, top[3].score, 0, 200, 4600000, "PAID_REPORT_READY: TOP1 + TOP2"]);

  dailyMbAppendIfMissing_(book, "MB_Method_Outputs_Current", 14,
    (row) => String(row[2]) === runId && String(row[3]) === DAILY_MB_METHOD_ID,
    (row) => String(row[5]) === `${top[0].pair}|${top[1].pair}`,
    [targetIso, lockIso, runId, DAILY_MB_METHOD_ID, "PRODUCTION_CANONICAL", `${top[0].pair}|${top[1].pair}`, scoreVector, "TOP2_REVERSE_PAIRS", "TRUE", 1, DAILY_MB_CONFIG_ID, artifact, "PUBLISHED_PASS_PRIVATE", "45/45 pairs; private paid delivery; automatic 00:05 run."]);

  const candidateSheet = book.getSheetByName("MB_Top_Candidates_Current");
  if (!candidateSheet) throw new Error("Missing MB_Top_Candidates_Current");
  const candidateValues = candidateSheet.getDataRange().getDisplayValues().slice(1).filter((row) => String(row[2]) === runId);
  if (candidateValues.length) {
    if (candidateValues.length !== 4 || candidateValues.map((row) => String(row[5])).join("|") !== top.map((item) => item.pair).join("|")) throw new Error("Candidate ranking conflict");
  } else {
    const rows = top.map((item, index) => [targetIso, lockIso, runId, scoreVector, index + 1, item.pair, item.score, "", `RANK_${index + 1}`, "FALSE", index < 2 ? 100 : 0, "FALSE", index < 2 ? "TOP2_PAIR_PRIVATE" : "AUDIT_ONLY_NO_FUND", "Canonical automatic 00:05 ranking."]);
    candidateSheet.getRange(candidateSheet.getLastRow() + 1, 1, rows.length, 14).setValues(rows);
  }

  dailyMbAppendIfMissing_(book, "MB_RUN_LOG", 22,
    (row) => String(row[3]) === runId,
    // A run can already have been recorded by the canonical Python worker. Its
    // artifact serialization is intentionally implementation-specific, so
    // idempotency is established from the shared run identity and immutable
    // method/config fields. The selected pairs are checked independently in
    // MB_FINAL_DECISION_CURRENT, MB_Method_Outputs_Current and Paid_Report.
    (row) => dailyMbParseDate_(row[1]) === targetIso
      && String(row[4]) === DAILY_MB_CONFIG_ID
      && String(row[8]) === DAILY_MB_METHOD_ID
      && Number(row[6]) === 27,
    [now, targetIso, lockIso, runId, DAILY_MB_CONFIG_ID, `AUTO MB 4SO ${dailyMbViDate_(targetIso)} AT 00:05`, 27, "FALSE", DAILY_MB_METHOD_ID, DAILY_MB_METHOD_ID, "challengers_weight_0", 45, 45, "FALSE", "PAID_REPORT_READY_FIXED50", "PRIVATE_PAID_REPORT", 200, 4600000, "AUTO_00_05_PRIVATE", "PASS_27_27_TIE_NO_LOOKAHEAD_READBACK", artifact, "Paid codes remain outside the public repository."]);
}

function dailyMbAppendIfMissing_(book, tab, width, identity, verify, row) {
  const sheet = book.getSheetByName(tab);
  if (!sheet) throw new Error(`Missing private tab ${tab}`);
  const values = sheet.getDataRange().getDisplayValues().slice(1).map((raw) => dailyMbPad_(raw, width));
  const matches = values.filter(identity);
  if (matches.length > 1) throw new Error(`${tab} duplicate automation identity`);
  if (matches.length === 1) {
    if (!verify(matches[0])) throw new Error(`${tab} conflicts with canonical output`);
    return;
  }
  sheet.getRange(sheet.getLastRow() + 1, 1, 1, width).setValues([dailyMbPad_(row, width)]);
}

function dailyMbUpdatePaid_(paidBook, targetIso, lockIso, ranked) {
  const sheet = paidBook.getSheetByName(PAID_REPORT_SHEET_NAME);
  if (!sheet) throw new Error("Paid_Report is missing");
  const top1 = ranked[0];
  const top2 = ranked[1];
  const expected = [dailyMbViDate_(targetIso), dailyMbViDate_(lockIso), top1.left, top1.right, top2.left, top2.right];
  const current = dailyMbPad_(sheet.getRange(2, 1, 1, 7).getDisplayValues()[0], 7);
  if (dailyMbParseDate_(current[0]) === targetIso) {
    if (current.slice(0, 6).map(String).join("|") !== expected.join("|")) throw new Error("Paid_Report conflicts with canonical output");
    return;
  }
  if (dailyMbParseDate_(current[0]) > targetIso) throw new Error("Paid_Report is ahead of target");
  const stamp = Utilities.formatDate(new Date(), DAILY_MB_TZ, "dd/MM/yyyy HH:mm") + " Asia/Saigon";
  sheet.getRange(2, 1, 1, 7).setNumberFormat("@").setValues([[].concat(expected, stamp)]);
  const readback = sheet.getRange(2, 1, 1, 7).getDisplayValues()[0];
  if (readback.slice(0, 6).map(String).join("|") !== expected.join("|")) throw new Error("Paid_Report readback failed");
}

function dailyMbVerifyNoDuplicates_(pnlBook, paidBook, sourceBook, lockIso, targetIso) {
  DAILY_MB_HISTORY_TABS.forEach((tab) => {
    const rows = dailyMbReadHistory_(sourceBook.getSheetByName(tab));
    if (rows.filter((row) => row[0] === lockIso).length !== 1) throw new Error(`${tab} does not contain exactly one DATA_LOCK row`);
  });
  const pnlSheet = pnlBook.getSheetByName(DAILY_MB_PNL_TAB);
  const pnlRows = pnlSheet.getLastRow() >= 6 ? pnlSheet.getRange(6, 1, pnlSheet.getLastRow() - 5, 11).getDisplayValues() : [];
  if (pnlRows.filter((row) => dailyMbParseDate_(row[0]) === lockIso && String(row[1]).trim().toUpperCase() === "4SO").length !== 1) throw new Error("T-1 P/L row is not unique");
  const paid = paidBook.getSheetByName(PAID_REPORT_SHEET_NAME).getRange(2, 1, 1, 7).getDisplayValues()[0];
  if (dailyMbParseDate_(paid[0]) !== targetIso || dailyMbParseDate_(paid[1]) !== lockIso) throw new Error("Paid_Report dates failed final verification");
  const runId = `MB_4SO_AUTO_${targetIso.replace(/-/g, "")}_0005`;
  ["MB_RUN_LOG", "MB_Method_Outputs_Current"].forEach((tab) => {
    const sheet = sourceBook.getSheetByName(tab);
    const count = sheet.getDataRange().getDisplayValues().slice(1).filter((row) => String(row[tab === "MB_RUN_LOG" ? 3 : 2]) === runId).length;
    if (count !== 1) throw new Error(`${tab} automation row is not unique`);
  });
}

function dailyMbParseDate_(value) {
  if (Object.prototype.toString.call(value) === "[object Date]" && !isNaN(value.getTime())) return Utilities.formatDate(value, DAILY_MB_TZ, "yyyy-MM-dd");
  const text = String(value == null ? "" : value).trim().slice(0, 10);
  let match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (match) return `${match[1]}-${match[2]}-${match[3]}`;
  match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text);
  if (match) return `${match[3]}-${String(match[2]).padStart(2, "0")}-${String(match[1]).padStart(2, "0")}`;
  return "";
}

function dailyMbAddDays_(iso, days) {
  const date = new Date(`${iso}T12:00:00+07:00`);
  return Utilities.formatDate(new Date(date.getTime() + Number(days) * 86400000), DAILY_MB_TZ, "yyyy-MM-dd");
}

function dailyMbViDate_(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match) throw new Error(`Invalid ISO date ${iso}`);
  return `${match[3]}/${match[2]}/${match[1]}`;
}

function dailyMbDmyDash_(iso) {
  return dailyMbViDate_(iso).replace(/\//g, "-");
}

function dailyMbPad_(row, width) {
  const result = Array.prototype.slice.call(row || [], 0, width);
  while (result.length < width) result.push("");
  return result;
}

function dailyMbNumber_(value) {
  const normalized = String(value == null ? "" : value).replace(/[^0-9-]/g, "");
  return normalized ? Number(normalized) : 0;
}

function dailyMbSha256_(value) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(value), Utilities.Charset.UTF_8)
    .map((byte) => (`0${((byte + 256) % 256).toString(16)}`).slice(-2)).join("");
}

