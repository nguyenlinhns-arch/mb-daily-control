(() => {
  "use strict";

  const SUPPORT_ZALO_ROUTE = "/go/zalo.htm";

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
    const bodyLock = String(document.body?.dataset?.dataLock || "").trim();
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

    const heading = document.querySelector("[data-daily-recommendation-heading]")
      || [...document.querySelectorAll(".portal-section-title h2")]
        .find((node) => /^(Phương pháp công khai|Gợi ý số)/i.test((node.textContent || "").trim()));
    if (heading) {
      setText(heading, `Gợi ý số hôm nay - ${date}`);
      heading.dataset.dailyRecommendationHeading = "mball-paid-v1";
      const subtitle = heading.parentElement?.querySelector("p");
      if (subtitle) {
        const lockText = dataLock ? `ngày hôm qua (${dataLock})` : "ngày hôm qua";
        setText(subtitle, `Gợi ý được tạo từ dữ liệu khóa đến ${lockText}. Các số cuối cùng không hiển thị công khai trước thanh toán.`);
      }
    }

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
