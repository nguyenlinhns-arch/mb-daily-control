(() => {
  "use strict";

  const SUPPORT_ZALO_ROUTE = "/go/zalo.htm";
  const OVERVIEW_VERSION = "mball-31-v2";

  function reportDateLabel() {
    const bodyDate = String(document.body?.dataset?.reportDate || "").trim();
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(bodyDate)) return bodyDate;
    const text = document.body?.textContent || "";
    const target = text.match(/Target\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/Gợi\s+ý\s+số[^\n]{0,100}?(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/LÊ\s+MIỀN\s+BẮC\s+NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i);
    return target ? target[1] : "";
  }

  function dataLockLabel() {
    const bodyLock = String(
      document.body?.dataset?.dataLock
      || document.body?.dataset?.lockDate
      || ""
    ).trim();
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(bodyLock)) return bodyLock;
    const text = document.body?.textContent || "";
    const match = text.match(/Data\s*lock\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/dữ\s+liệu\s+khóa\s+đến(?:\s+ngày\s+hôm\s+qua\s*\()?\s*(\d{2}\/\d{2}\/\d{4})/i);
    return match ? match[1] : "";
  }

  function setText(node, value) {
    if (node && (node.textContent || "").trim() !== value) node.textContent = value;
  }

  function normalizePaidButton(button, date) {
    if (!button) return;
    setText(button, "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ");
    button.setAttribute("aria-label", `Thanh toán nhận gợi ý số MB_ALL ngày ${date}, giá 30.000 đồng`);
    button.removeAttribute("data-zalo-route");
    button.removeAttribute("target");
    button.removeAttribute("rel");
    button.removeAttribute("disabled");
    button.removeAttribute("aria-disabled");
  }

  function normalizeSuggestionCard(card, date) {
    if (!card) return;
    setText(card.querySelector(":scope > small"), "THANH TOÁN NHẬN GỢI Ý SỐ");
    setText(card.querySelector(":scope > h2"), `Gợi ý số MB_ALL - ${date}`);

    let readyNote = card.querySelector(":scope > .lm-returning-note");
    const title = card.querySelector(":scope > h2");
    if (!readyNote && title) {
      readyNote = document.createElement("div");
      readyNote.className = "lm-returning-note";
      title.insertAdjacentElement("afterend", readyNote);
    }
    setText(readyNote, `Gợi ý ngày ${date} đã sẵn sàng · 30.000đ/ngày · xác nhận thanh toán qua email.`);

    normalizePaidButton(card.querySelector("[data-open-checkout]"), date);

    let kicker = card.querySelector(".lm-ai-runtime-kicker");
    const button = card.querySelector("[data-open-checkout]");
    if (!kicker && button) {
      kicker = document.createElement("span");
      kicker.className = "lm-ai-runtime-kicker";
      button.insertAdjacentElement("afterend", kicker);
    }
    setText(kicker, "Thanh toán một lần · Không tự gia hạn · Xác nhận qua email");

    let note = card.querySelector(".portal-paid-note");
    if (!note) {
      note = document.createElement("p");
      note.className = "portal-paid-note";
      card.appendChild(note);
    }
    setText(note, "Gợi ý số chỉ mở sau khi giao dịch được xác nhận. Zalo chỉ dùng để hỗ trợ.");

    const lock = card.querySelector(".portal-paid-lock");
    if (lock) lock.setAttribute("aria-label", "TOP 1 và TOP 2 được ẩn trước khi thanh toán");

    card.removeAttribute("data-zalo-suggestion-card");
    card.dataset.dailyOfferCopy = "paid-email-v1";
    card.dataset.paidSuggestionCard = "true";
  }

  function ensureSupportButton() {
    let support = document.getElementById("mball-zalo-support");
    if (!support) {
      support = document.createElement("a");
      support.id = "mball-zalo-support";
      support.className = "mball-zalo-support-button";
      document.body.appendChild(support);
    }
    support.href = SUPPORT_ZALO_ROUTE;
    support.target = "_blank";
    support.rel = "noopener noreferrer";
    support.setAttribute("aria-label", "Hỗ trợ qua Zalo");
    setText(support, "Hỗ trợ");
  }

  function ensureOverviewStyle() {
    if (document.getElementById("mball-method-overview-style")) return;
    const style = document.createElement("style");
    style.id = "mball-method-overview-style";
    style.textContent = `
      .portal-home .mball-method-overview{padding:20px 0!important}
      .portal-home .mball-method-overview .portal-section-title{align-items:flex-start!important;margin-bottom:12px!important}
      .portal-home .mball-overview-kicker{margin:0 0 5px!important;color:#b3161b!important;font-size:10px!important;font-weight:1000!important;letter-spacing:.08em!important;text-transform:uppercase!important}
      .portal-home .mball31-process{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:10px!important}
      .portal-home .mball31-process .portal-method{min-width:0!important;padding:14px!important;border:1px solid #dfe4e9!important;border-radius:13px!important;background:#fff!important;box-shadow:0 2px 10px rgba(16,35,50,.04)!important}
      .portal-home .mball31-process .portal-method-head{margin-bottom:7px!important;align-items:flex-start!important}
      .portal-home .mball31-process .portal-method-head b{font-size:14px!important;line-height:1.3!important}
      .portal-home .mball31-process .portal-method-head span{flex:0 0 auto!important;background:#f5e9ea!important;color:#a70e15!important;font-size:9px!important;font-weight:1000!important}
      .portal-home .mball31-process .portal-method p{margin:0!important;color:#5f6e79!important;font-size:12px!important;line-height:1.5!important}
      .portal-home .mball-overview-lock{display:flex!important;align-items:flex-start!important;justify-content:space-between!important;gap:14px!important;margin-top:11px!important;padding:13px 14px!important;border:1px solid #efc8ca!important;border-radius:13px!important;background:#fff8f8!important}
      .portal-home .mball-overview-lock strong{display:block!important;color:#a20e15!important;font-size:13px!important}
      .portal-home .mball-overview-lock span{display:block!important;max-width:760px!important;color:#6f6163!important;font-size:11px!important;line-height:1.5!important}
      @media(max-width:900px){.portal-home .mball31-process{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
      @media(max-width:620px){.portal-home .mball31-process{grid-template-columns:1fr!important}.portal-home .mball-overview-lock{display:block!important}.portal-home .mball-overview-lock span{margin-top:4px!important}}
    `;
    document.head.appendChild(style);
  }

  function findMethodSection() {
    const marked = document.querySelector('[data-mball-method-overview]');
    if (marked) return marked;
    return [...document.querySelectorAll(".portal-section")].find((section) => {
      const heading = section.querySelector(".portal-section-title h2, [data-daily-recommendation-heading]");
      const value = String(heading?.textContent || "").trim();
      return /Phương pháp công khai|Gợi ý số hôm nay|MB_ALL chạy đủ 31 phương pháp/i.test(value)
        && Boolean(section.querySelector(".portal-methods, .portal-consensus"));
    }) || null;
  }

  function normalizeMballMethodOverview(date, dataLock) {
    const section = findMethodSection();
    if (!section) return;
    ensureOverviewStyle();

    const lockLabel = dataLock || "T−1";
    const expectedKey = `${OVERVIEW_VERSION}|${date}|${lockLabel}`;
    if (section.dataset.mballOverviewKey === expectedKey
        && !section.querySelector(".portal-method-numbers,.portal-ball,.portal-consensus")) return;

    section.classList.add("mball-method-overview");
    section.dataset.mballMethodOverview = OVERVIEW_VERSION;
    section.dataset.mballOverviewKey = expectedKey;
    section.innerHTML = `
      <div class="portal-wrap">
        <div class="portal-section-title">
          <div>
            <p class="mball-overview-kicker">MB_ALL · DATA LOCK ${lockLabel}</p>
            <h2 data-daily-recommendation-heading="${OVERVIEW_VERSION}">MB_ALL chạy đủ 31 phương pháp mỗi ngày</h2>
            <p>Không chọn trước một phương pháp. Hệ thống chạy đủ 31/31 phương pháp bằng dữ liệu đến ${lockLabel}, sau đó mới đánh giá trạng thái gần và chấm điểm từng số.</p>
          </div>
        </div>
        <div class="portal-methods mball31-process" data-mball31-process="true">
          <article class="portal-method"><div class="portal-method-head"><b>1. Chạy đủ 31/31</b><span>T−1</span></div><p>Mỗi đầu ra chỉ dùng dữ liệu đã hoàn tất đến ngày liền trước; không dùng kết quả ngày đang chọn.</p></article>
          <article class="portal-method"><div class="portal-method-head"><b>2. Đánh giá hiệu quả gần</b><span>3–5–7–10</span></div><p>Đối chiếu W/Hòa/L, chuỗi thắng–thua, P/L, ROI, số nháy và độ ổn định theo các cửa sổ gần.</p></article>
          <article class="portal-method"><div class="portal-method-head"><b>3. Chấm HOT/COLD từng số</b><span>NET SCORE</span></div><p>Tín hiệu tốt cộng điểm, tín hiệu xấu trừ điểm; kiểm soát phiếu trùng và chỉ tính đồng thuận KÉP khi đủ điều kiện.</p></article>
          <article class="portal-method"><div class="portal-method-head"><b>4. Chọn động và khóa</b><span>PRE-DRAW</span></div><p>Không cố định phương pháp hoặc số lượng số. Chỉ giữ các số vượt ngưỡng rồi khóa trước giờ quay.</p></article>
        </div>
        <div class="mball-overview-lock">
          <strong>Đầu ra 31 phương pháp và số cuối được giữ kín</strong>
          <span>Chỉ mở sau khi thanh toán được xác nhận qua email. Kết quả ngày ${date} không được dùng để sửa lựa chọn của chính ngày đó.</span>
        </div>
        <p class="portal-disclaimer">MB_ALL là quy trình tổng hợp tín hiệu động, không phải một phương pháp cố định và không công khai các số thành phần trước thanh toán.</p>
      </div>`;
  }

  function applyCopyLock() {
    if (window.location.pathname !== "/") return;
    const date = reportDateLabel();
    const dataLock = dataLockLabel();
    if (!date) return;

    const lead = document.querySelector(".portal-hero .portal-lead");
    if (lead) {
      const desired = `MB_ALL chạy đủ 31 phương pháp bằng dữ liệu đến T−1, đánh giá hiệu quả gần và chấm HOT/COLD để chọn số động. Gợi ý ngày <strong>${date}</strong> chỉ mở sau khi thanh toán được xác nhận.`;
      if (lead.innerHTML !== desired) lead.innerHTML = desired;
      lead.dataset.dailySalesCopy = "mball-paid-v1";
    }

    document.querySelectorAll(".portal-paid-card").forEach((card) => normalizeSuggestionCard(card, date));

    const sticky = document.querySelector("[data-ai-sticky-cta]");
    if (sticky) {
      setText(sticky, "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ");
      sticky.setAttribute("href", "#buy");
      sticky.removeAttribute("target");
      sticky.removeAttribute("rel");
      sticky.removeAttribute("data-zalo-route");
      sticky.setAttribute("aria-label", `Thanh toán nhận gợi ý số MB_ALL ngày ${date}, giá 30.000 đồng`);
    }

    normalizeMballMethodOverview(date, dataLock);
    document.querySelectorAll('[data-zalo-route="true"]').forEach((node) => node.removeAttribute("data-zalo-route"));
    ensureSupportButton();
    document.documentElement.dataset.purchaseRoute = "paid-checkout-v1";
  }

  function boot() {
    if (window.location.pathname !== "/") return;
    applyCopyLock();
    const observer = new MutationObserver(applyCopyLock);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["hidden", "data-returning-ai-buyer"]
    });
    for (const delay of [50, 250, 750, 1500, 3000, 6000]) window.setTimeout(applyCopyLock, delay);
    window.setTimeout(() => {
      applyCopyLock();
      observer.disconnect();
    }, 10000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
