const SOURCE_NAME = "XSMB_Source_2024_2026_MB_v1.3";
const CONFIG_ID = "MB_MAX_V03_CUM3_2SO_INT_V3";
const CUM3_ID = "MB_CUM3_V2_0_MAX";
const MB2SO_ID = "MB_2SO_V1";
const CAPITAL_RULE_ID = "MB_CAPITAL_PROTECTION_V1";
const POINT_COST = 23000;
const POINT_PAYOUT = 80000;
const DEFAULT_TARGET_DATE = "2026-07-29";
const LEDGER_STORAGE_KEY = "mb-max-v03-ledger";
const SELECTED_CODES_STORAGE_KEY = "mb-max-v03-selected-codes";
const PROJECT_URL_STORAGE_KEY = "mb-max-v03-chatgpt-project-url";
const CHATGPT_FALLBACK_URL = "https://chatgpt.com/";

const commandMeta = {
  reviewRun: "Rà soát số",
  dailyRun: "Chạy MB MAX V03",
  settle: "Cập nhật kết quả",
  capitalBrake: "Kiểm tra lệnh phanh",
  strongList: "Quét số mạnh",
  report: "Xuất báo cáo ngày",
};

const strongNumbers = [
  ["13", 94, "Core candidate", "Champion + MB16HO", "Chờ artifact"],
  ["83", 91, "Core candidate", "Champion + Coverage", "Chờ artifact"],
  ["52", 83, "Third candidate", "MB16HO + CUM3", "Cần Gate"],
  ["54", 77, "Shadow watch", "CUM3", "Dedupe"],
  ["90", 73, "Pair watch", "MB 2SO", "Tham chiếu"],
  ["91", 69, "Frequency watch", "MB16HO", "Theo dõi"],
  ["92", 66, "Frequency watch", "MB16HO", "Theo dõi"],
];

const checklist = [
  ["Data Lock t-1", "Khóa dữ liệu đến hết ngày trước phiên chạy, outcome_known_at_selection=false."],
  ["27/27 verified", "Không đủ 27/27 thì WAIT_RESULT_DATA hoặc NO_BET."],
  ["Champion hợp lệ", "Champion là nguồn chính duy nhất tạo Core."],
  ["CUM3 audit", "Vector đủ 100 mã, tổng 100, Top3 sau dedupe."],
  ["MB 2SO audit", "Đúng một cặp đảo Top1, không dùng kết quả ngày t."],
  ["Cluster/dedupe", "Mỗi cluster tối đa một phiếu effective weight."],
  ["Capital Gate", "Không manual override, không tăng điểm, không gỡ."],
  ["Hash/Readback", "Chỉ công nhận PUBLISHED+PASS+HASH_MATCH."],
];

const state = {
  activeCommand: "reviewRun",
  targetDate: DEFAULT_TARGET_DATE,
  selectedCodes: "",
  projectUrl: "",
  ledger: [],
};

const $ = (id) => document.getElementById(id);

function isIsoDate(input) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input)) return false;
  const [year, month, day] = input.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

function normalizeDate(input) {
  return isIsoDate(input) ? input : DEFAULT_TARGET_DATE;
}

function displayDate(input) {
  const [year, month, day] = normalizeDate(input).split("-");
  return `${day}/${month}/${year}`;
}

function previousDate(input) {
  const [year, month, day] = normalizeDate(input).split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() - 1);
  return date.toISOString().slice(0, 10);
}

function formatMoney(value) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

function readStorage(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Blocked browser storage should not break the dashboard.
  }
}

function parseLedger(raw) {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((row) => {
      return (
        row &&
        typeof row.id === "string" &&
        isIsoDate(row.date) &&
        ["CORE", "PROFIT", "COVERAGE", "NO_BET"].includes(row.mode) &&
        typeof row.codes === "string" &&
        Number.isFinite(row.points) &&
        Number.isFinite(row.hitPointUnits) &&
        Number.isFinite(row.net) &&
        ["WIN", "LOSS", "BREAKEVEN", "NO_BET"].includes(row.status)
      );
    });
  } catch {
    return [];
  }
}

function fallbackCopy(text) {
  const scratch = document.createElement("textarea");
  scratch.value = text;
  scratch.setAttribute("readonly", "true");
  scratch.style.position = "fixed";
  scratch.style.left = "-9999px";
  document.body.appendChild(scratch);
  scratch.select();
  try {
    return document.execCommand("copy");
  } finally {
    document.body.removeChild(scratch);
  }
}

function normalizeProjectUrl(value) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  const candidate = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;

  try {
    const url = new URL(candidate);
    const allowedHost = ["chatgpt.com", "chat.openai.com"].includes(url.hostname);
    const allowedProtocol = ["http:", "https:"].includes(url.protocol);
    if (!allowedHost || !allowedProtocol) return "";
    url.hash = "";
    url.searchParams.delete("q");
    return url.toString();
  } catch {
    return "";
  }
}

function buildChatGptCommandUrl(command) {
  const targetUrl = state.projectUrl || CHATGPT_FALLBACK_URL;
  const url = new URL(targetUrl);
  url.searchParams.set("q", command);
  return url.toString();
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to execCommand.
    }
  }
  try {
    return fallbackCopy(text);
  } catch {
    return false;
  }
}

function statusFromNet(points, net) {
  if (points <= 0) return "NO_BET";
  if (net > 0) return "WIN";
  if (net < 0) return "LOSS";
  return "BREAKEVEN";
}

function statusLabel(status) {
  if (status === "WIN") return "Thắng";
  if (status === "LOSS") return "Thua";
  if (status === "BREAKEVEN") return "Hòa";
  return "Không đánh";
}

function calculateMetrics(rows) {
  const sorted = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  let cumulative = 0;
  let peak = 0;
  let maxDrawdown = 0;

  sorted.forEach((row) => {
    cumulative += row.net;
    peak = Math.max(peak, cumulative);
    maxDrawdown = Math.max(maxDrawdown, peak - cumulative);
  });

  let liveLossStreak = 0;
  for (let index = sorted.length - 1; index >= 0; index -= 1) {
    const status = sorted[index].status;
    if (status === "NO_BET") continue;
    if (status === "LOSS") {
      liveLossStreak += 1;
      continue;
    }
    break;
  }

  let liveWinStreak = 0;
  for (let index = sorted.length - 1; index >= 0; index -= 1) {
    const status = sorted[index].status;
    if (status === "NO_BET") continue;
    if (status === "WIN") {
      liveWinStreak += 1;
      continue;
    }
    break;
  }

  const profitLock = peak >= 25000000 && peak - cumulative >= 6900000;
  let riskState = "ALLOW";
  if (profitLock) riskState = "MONTH_PROFIT_LOCK";
  else if (liveLossStreak >= 5) riskState = "HARD_PAUSE";
  else if (liveLossStreak >= 3) riskState = "PAUSE_SHADOW";
  else if (liveLossStreak >= 2) riskState = "CORE_ONLY";

  return { cumulative, peak, maxDrawdown, liveLossStreak, liveWinStreak, riskState };
}

function nextAction(riskState) {
  if (riskState === "ALLOW") return "ALLOW";
  if (riskState === "CORE_ONLY") return "CORE_ONLY";
  if (riskState === "PAUSE_SHADOW") return "Shadow";
  if (riskState === "MONTH_PROFIT_LOCK") return "Profit Lock";
  return "HARD_PAUSE";
}

function commandHeader() {
  return `Dự án MB MAX V03. Target Date: ${displayDate(state.targetDate)}. Data Lock: hết ngày ${displayDate(previousDate(state.targetDate))}. Nguồn chuẩn duy nhất: ${SOURCE_NAME}. Config ID: ${CONFIG_ID}. CUM3 ID: ${CUM3_ID}. MB 2SO ID: ${MB2SO_ID}. Capital Rule ID: ${CAPITAL_RULE_ID}.`;
}

function buildCommand() {
  const header = commandHeader();
  const dateLabel = displayDate(state.targetDate);
  const selectedLine = state.selectedCodes.trim()
    ? `Số đang nhập trên dashboard: ${state.selectedCodes.trim()}.`
    : "Dashboard chưa có final_codes; chỉ chốt khi artifact canonical PASS.";

  if (state.activeCommand === "reviewRun") {
    return `${header}

Hãy bấm chạy/rà soát theo đúng Project MB MAX V03 cho ngày ${dateLabel} và tạo list số trước khi quyết định xuống tiền.

Yêu cầu chạy:
1. Khóa dữ liệu đến hết t-1; xác nhận đủ 27/27; outcome_known_at_selection=false.
2. Chạy lần lượt Champion, MB16HO, CUM3 và MB 2SO; không dùng kết quả ngày t.
3. Tạo list số theo từng nguồn: Champion Top2, MB16HO Top2/Top3/Top5, CUM3 Top3, MB 2SO Top Pair.
4. Cluster/dedupe bắt buộc: mỗi cluster tối đa một phiếu effective weight; CUM3 và MB 2SO chỉ là tham chiếu sau dedupe.
5. Tính ConsensusScore, ghi nguồn hỗ trợ, cluster, effective_weight, trạng thái Core/Third/Watch/Dedupe.
6. Sau khi có list, lập phương án:
   - Phương án A: CORE_ONLY, 2 số Champion x 50 điểm.
   - Phương án B: PROFIT, 3 số x 50 điểm nếu số thứ ba đủ ít nhất hai cluster độc lập và Capital Gate cho phép.
   - Phương án C: NO_BET nếu thiếu dữ liệu, lỗi audit, capital blocked hoặc Publication Contract không đạt.
7. Chạy hai Capital Gate và kiểm tra LIVE_LOSS_STREAK, MODEL_LOSS_STREAK, SHADOW_RECOVERY, LIVE_PROBATION, P/L tháng, đỉnh tháng, drawdown.
8. Chỉ kết luận từ artifact canonical PUBLISHED+PASS+HASH_MATCH. Nếu chưa đạt, trả final_codes=[], total_points=0, total_capital=0.

Trả về đúng cấu trúc:
1. Bảng list số: số, nguồn, cluster, effective_weight, ConsensusScore, vai trò, ghi chú dedupe.
2. Bảng phương án A/B/C: số, điểm, vốn, điều kiện được phép, rủi ro.
3. Kết luận duy nhất: ALLOW, CORE_ONLY hoặc NO_BET.
4. final_codes, total_points, total_capital, Risk State, SHA-256 và lý do chốt/không chốt.`;
  }

  if (state.activeCommand === "dailyRun") {
    return `${header}

Hãy chạy đầy đủ pipeline LOCK_DATA -> LOAD_MANIFEST/REGISTRY -> RUN_CHAMPION -> RUN_MB16HO -> RUN_CUM3 -> RUN_MB_2SO -> VALIDATE -> CLUSTER/DEDUPE -> METHOD_QUALITY -> SCORE -> AUDIT/TIE_AUDIT -> SELECT_CORE -> BUILD_PROFIT_CANDIDATE -> CAPITAL_GATES -> FINALIZE -> HASH/READBACK -> PUBLISH.

Bắt buộc:
1. Khóa dữ liệu đến hết t-1, đủ 27/27, outcome_known_at_selection=false.
2. Champion là nguồn chính duy nhất tạo Core.
3. CUM3 đủ 100 mã, tổng 100, chỉ phát một phiếu Top3 sau dedupe.
4. MB 2SO xuất đúng một cặp đảo Top1, chỉ tham chiếu sau dedupe.
5. Số thứ ba chỉ vào khi có ít nhất hai cluster độc lập hỗ trợ và Capital Gate cho phép.
6. Nếu thiếu Publication Contract: publishable=false, final_codes=[], total_points=0, total_capital=0.

Trả về bảng gồm Champion Top2, MB16HO Top2/Top3/Top5, CUM3 Top3, MB 2SO Top Pair, cluster/dedupe/effective_weight, Capital Gate 1/2, Risk State, final_codes, điểm, vốn và SHA-256.`;
  }

  if (state.activeCommand === "settle") {
    return `${header}

Hãy cập nhật kết quả và lãi/lỗ cho ngày ${dateLabel}.

Bắt buộc:
1. Đọc artifact canonical PUBLISHED+PASS+HASH_MATCH của ngày ${dateLabel}; không dùng số chưa publish.
2. Đối chiếu kết quả XSMB ngày ${dateLabel}; tính nháy từng final_code.
3. Công thức vốn: 23.000đ/điểm; trả 80.000đ/điểm/nháy; tối đa 150 điểm/ngày; điểm chia hết cho 5.
4. Cập nhật ledger: ngày, final_codes, điểm từng số, tổng điểm, số nháy, lãi/lỗ, lũy kế tháng, đỉnh tháng, drawdown.
5. Cập nhật LIVE_LOSS_STREAK, MODEL_LOSS_STREAK, SHADOW_RECOVERY, LIVE_PROBATION.
6. WAIT, lỗi dữ liệu, NO_BET hoặc thiếu artifact không tăng và không xóa chuỗi.

Trả về bảng settlement và kết luận trạng thái vốn cho phiên kế tiếp. ${selectedLine}`;
  }

  if (state.activeCommand === "capitalBrake") {
    return `${header}

Hãy chỉ kiểm tra Capital Protection Gate trước khi xuống tiền cho ngày ${dateLabel}.

Áp dụng cứng:
1. Sau 1 thua: không tăng điểm, không thêm số.
2. Sau 2 thua Live: phiên kế tiếp CORE_ONLY, cấm Profit Mode và số thứ ba.
3. Sau 3 thua Live: phiên kế tiếp PAUSE_SHADOW.
4. Hai Shadow tiếp theo cùng thua: MODEL_LOSS_STREAK=5, chuyển HARD_PAUSE.
5. Profit Lock nếu P/L tháng từng đạt 25.000.000đ rồi giảm 6.900.000đ từ đỉnh.
6. CONFIG_MISMATCH, HASH_MISMATCH, MULTIPLE_FINALS, look-ahead, sai số/điểm/vốn hoặc publication fail đều CAPITAL_BLOCKED.

Trả về ALLOW, CORE_ONLY, NO_BET hoặc CAPITAL_BLOCKED; nêu rõ lý do và bộ đếm chuỗi.`;
  }

  if (state.activeCommand === "strongList") {
    return `${header}

Hãy quét danh sách số mạnh cho ngày ${dateLabel}, không giới hạn số lượng ban đầu nhưng phải phân tầng rõ:
1. Core candidates từ Champion.
2. MB16HO Top2/Top3/Top5 sau cluster/dedupe.
3. CUM3 Top3 sau kiểm tra vector 100 mã, tổng 100.
4. MB 2SO Top Pair sau audit chống look-ahead.
5. Giao thoa số có từ ít nhất hai cluster độc lập.
6. Số bị dedupe hoặc chỉ là tham chiếu phải ghi effective_weight=0.

Trả về bảng: số, nguồn hỗ trợ, cluster, effective_weight, ConsensusScore, trạng thái Core/Third/Watch/Dedupe, và ghi rõ số nào được chọn nếu Capital Gate cho phép.`;
  }

  return `${header}

Hãy xuất báo cáo ngày MB MAX V03 cho ${dateLabel}.

Báo cáo bắt buộc có Data Lock, 27/27, Snapshot/Run/Config/Capital Rule ID, SHA-256, Champion Top2, MB16HO Top2/Top3/Top5, CUM3 Top3, MB 2SO Top Pair, giao thoa/phân kỳ, cluster/dedupe/effective_weight, số thứ ba nếu có, hai Capital Gate, chuỗi thua, Risk State, Shadow Recovery, Live Probation, P/L tháng, đỉnh tháng, drawdown, Audit, Hash, Readback và một kết luận duy nhất: ALLOW, CORE_ONLY hoặc NO_BET.

Nếu thiếu bất kỳ điều kiện Publication Contract nào thì final_codes=[], total_points=0, total_capital=0.`;
}

function renderMetrics() {
  const metrics = calculateMetrics(state.ledger);
  $("displayTargetDate").textContent = displayDate(state.targetDate);
  $("displayDataLock").textContent = displayDate(previousDate(state.targetDate));
  $("displayRiskState").textContent = metrics.riskState;
  $("riskBadge").textContent = metrics.riskState;
  $("riskBadge").className = `risk-badge ${metrics.riskState.toLowerCase()}`;
  $("liveLossStreak").textContent = String(metrics.liveLossStreak);
  $("liveWinStreak").textContent = String(metrics.liveWinStreak);
  $("nextAction").textContent = nextAction(metrics.riskState);
  $("cumulativeNet").textContent = formatMoney(metrics.cumulative);
  $("monthlyPeak").textContent = formatMoney(metrics.peak);
  $("maxDrawdown").textContent = formatMoney(metrics.maxDrawdown);
}

function renderCommand() {
  $("commandText").value = buildCommand();
  document.querySelectorAll("[data-command]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.command === state.activeCommand);
    button.setAttribute(
      "aria-pressed",
      button.dataset.command === state.activeCommand ? "true" : "false",
    );
  });
}

function markReviewSent() {
  const timestamp = new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date());
  $("reviewState").textContent = "Đã gửi lệnh";
  $("reviewTitle").textContent = `Đã mở phiên rà soát cho ngày ${displayDate(state.targetDate)}.`;
  $("reviewMessage").textContent =
    `Lúc ${timestamp}. Dashboard đã mở ChatGPT và sao chép lệnh rà soát. Hãy lấy bảng list số và kết luận ALLOW/CORE_ONLY/NO_BET; chỉ nhập vào “Số chốt” khi artifact PASS và Capital Gate cho phép.`;
  document.querySelectorAll(".review-step").forEach((step) => {
    step.classList.add("is-ready");
  });
}

function runReviewCommand() {
  state.activeCommand = "reviewRun";
  renderCommand();
  const command = buildCommand();
  void copyText(command);
  window.open(buildChatGptCommandUrl(command), "_blank", "noopener,noreferrer");
  markReviewSent();
}

function renderSettlementPreview() {
  const points = Number($("settlementPoints").value) || 0;
  const hits = Number($("settlementHits").value) || 0;
  const net = hits * POINT_PAYOUT - points * POINT_COST;
  const status = statusFromNet(points, net);
  $("settlementPreview").textContent = formatMoney(net);
  $("settlementStatus").textContent = statusLabel(status);
}

function renderLedger() {
  const body = $("ledgerBody");
  body.innerHTML = "";

  if (state.ledger.length === 0) {
    body.innerHTML = `<tr class="empty-row"><td colspan="7">Chưa có dòng ledger nào. Hãy ghi kết quả sau khi có artifact PASS.</td></tr>`;
    return;
  }

  [...state.ledger]
    .sort((a, b) => b.date.localeCompare(a.date))
    .forEach((row) => {
      const tr = document.createElement("tr");
      const netClass = row.net >= 0 ? "positive" : "negative";
      tr.innerHTML = `
        <td>${displayDate(row.date)}</td>
        <td>${row.mode}</td>
        <td>${escapeHtml(row.codes)}</td>
        <td>${row.points}</td>
        <td>${row.hitPointUnits}</td>
        <td><strong class="${netClass}">${formatMoney(row.net)}</strong></td>
        <td>${statusLabel(row.status)}</td>
      `;
      body.appendChild(tr);
    });
}

function renderStrongNumbers() {
  $("strongNumberList").innerHTML = strongNumbers
    .map(
      ([code, score, role, support, status]) => `
        <article class="number-card">
          <div class="number-code">${code}</div>
          <div>
            <h3>${role}</h3>
            <p>${support} - ${status}</p>
          </div>
          <div class="score">${score}</div>
        </article>
      `,
    )
    .join("");
}

function renderChecklist() {
  $("publicationChecklist").innerHTML = checklist
    .map(
      ([title, detail]) => `
        <article class="check-item">
          <div class="check-mark">OK</div>
          <div>
            <h3>${title}</h3>
            <p>${detail}</p>
          </div>
        </article>
      `,
    )
    .join("");
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => {
    return {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[char];
  });
}

function saveState() {
  writeStorage(LEDGER_STORAGE_KEY, JSON.stringify(state.ledger));
  writeStorage(SELECTED_CODES_STORAGE_KEY, state.selectedCodes);
}

function renderAll() {
  renderMetrics();
  renderCommand();
  renderSettlementPreview();
  renderLedger();
}

function bindEvents() {
  $("targetDate").addEventListener("change", (event) => {
    state.targetDate = normalizeDate(event.target.value);
    event.target.value = state.targetDate;
    renderAll();
  });

  $("selectedCodes").addEventListener("input", (event) => {
    state.selectedCodes = event.target.value;
    saveState();
    renderCommand();
  });

  $("commandGrid").addEventListener("click", (event) => {
    const button = event.target.closest("[data-command]");
    if (!button) return;
    state.activeCommand = button.dataset.command;
    renderCommand();
  });

  $("copyCommand").addEventListener("click", async () => {
    const button = $("copyCommand");
    const ok = await copyText(buildCommand());
    button.textContent = ok ? "Đã sao chép" : "Không sao chép được";
    window.setTimeout(() => {
      button.textContent = "Sao chép lệnh";
    }, 1800);
  });

  $("openChatGPT").addEventListener("click", async () => {
    const command = buildCommand();
    await copyText(command);
    window.open(buildChatGptCommandUrl(command), "_blank", "noopener,noreferrer");
  });

  $("runReview").addEventListener("click", runReviewCommand);
  $("runReviewHeader").addEventListener("click", runReviewCommand);

  ["settlementPoints", "settlementHits"].forEach((id) => {
    $(id).addEventListener("input", renderSettlementPreview);
  });

  $("settlementMode").addEventListener("change", (event) => {
    if (event.target.value === "NO_BET") {
      $("settlementPoints").value = "0";
      $("settlementHits").value = "0";
    }
    renderSettlementPreview();
  });

  $("settlementForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const points = Number($("settlementPoints").value) || 0;
    const hits = Number($("settlementHits").value) || 0;
    const net = hits * POINT_PAYOUT - points * POINT_COST;
    const row = {
      id: `${state.targetDate}-${Date.now()}`,
      date: state.targetDate,
      mode: $("settlementMode").value,
      codes: $("settlementCodes").value.trim() || state.selectedCodes.trim() || "Chưa nhập",
      points,
      hitPointUnits: hits,
      net,
      status: statusFromNet(points, net),
      note: $("settlementNote").value.trim(),
    };
    state.ledger = [row, ...state.ledger.filter((item) => item.date !== row.date)];
    saveState();
    renderAll();
  });

  $("clearLedger").addEventListener("click", () => {
    state.ledger = [];
    saveState();
    renderAll();
  });
}

function boot() {
  state.ledger = parseLedger(readStorage(LEDGER_STORAGE_KEY));
  state.selectedCodes = readStorage(SELECTED_CODES_STORAGE_KEY) || "";
  state.projectUrl = normalizeProjectUrl(readStorage(PROJECT_URL_STORAGE_KEY) || "");
  $("targetDate").value = state.targetDate;
  $("selectedCodes").value = state.selectedCodes;
  renderStrongNumbers();
  renderChecklist();
  bindEvents();
  renderAll();
}

window.addEventListener("DOMContentLoaded", boot);
