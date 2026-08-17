(() => {
  "use strict";

  const ZALO_URL = "/go/zalo/";

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

  function routeButtonToZalo(button, date) {
    if (!button) return;
    setText(button, "MỞ ZALO – NHẬN GỢI Ý HÔM NAY");
    button.setAttribute("aria-label", `Mở Zalo nhận gợi ý số hôm nay ${date}`);
    button.setAttribute("data-zalo-route", "true");
    button.removeAttribute("disabled");
    button.removeAttribute("aria-disabled");
  }

  function normalizeSuggestionCard(card, date) {
    if (!card) return;
    setText(card.querySelector(":scope > small"), "GỢI Ý SỐ HÔM NAY");
    setText(card.querySelector(":scope > h2"), `Gợi ý số hôm nay - ${date}`);

    let readyNote = card.querySelector(":scope > .lm-returning-note");
    const title = card.querySelector(":scope > h2");
    if (!readyNote && title) {
      readyNote = document.createElement("div");
      readyNote.className = "lm-returning-note";
      title.insertAdjacentElement("afterend", readyNote);
    }
    setText(readyNote, `Gợi ý ngày ${date} đã sẵn sàng · mở Zalo để trao đổi.`);

    routeButtonToZalo(card.querySelector("[data-open-checkout]"), date);

    const kicker = card.querySelector(".lm-ai-runtime-kicker");
    if (kicker) kicker.remove();

    const note = card.querySelector(".portal-paid-note");
    if (note) note.remove();

    const lock = card.querySelector(".portal-paid-lock");
    if (lock) lock.setAttribute("aria-label", "TOP 1 và TOP 2 được ẩn trên trang công khai");

    card.dataset.dailyOfferCopy = "zalo-only-v3";
  }

  function applyCopyLock() {
    if (window.location.pathname !== "/") return;
    const date = reportDateLabel();
    const dataLock = dataLockLabel();
    if (!date) return;

    const lead = document.querySelector(".portal-hero .portal-lead");
    if (lead) {
      const desired = `Theo dõi dữ liệu kỳ gần nhất, tần suất, lô gan, cặp đảo và các phương pháp công khai. Gợi ý số hôm nay <strong>${date}</strong> được trao đổi trực tiếp qua Zalo.`;
      if (lead.innerHTML !== desired) lead.innerHTML = desired;
      lead.dataset.dailySalesCopy = "zalo-only-v2";
    }

    document.querySelectorAll(".portal-paid-card").forEach((card) => normalizeSuggestionCard(card, date));

    const sticky = document.querySelector("[data-ai-sticky-cta]");
    if (sticky) {
      setText(sticky, "GỢI Ý SỐ HÔM NAY · MỞ ZALO");
      sticky.setAttribute("href", ZALO_URL);
      sticky.setAttribute("target", "_blank");
      sticky.setAttribute("rel", "noopener noreferrer");
      sticky.setAttribute("data-zalo-route", "link");
      sticky.setAttribute("aria-label", `Mở Zalo nhận gợi ý số hôm nay ${date}`);
    }

    const heading = document.querySelector('[data-daily-recommendation-heading]')
      || [...document.querySelectorAll(".portal-section-title h2")]
        .find((node) => /^(Phương pháp công khai|Gợi ý số)/i.test((node.textContent || "").trim()));
    if (heading) {
      setText(heading, `Gợi ý số hôm nay - ${date}`);
      heading.dataset.dailyRecommendationHeading = "zalo-only-v2";
      const subtitle = heading.parentElement?.querySelector("p");
      if (subtitle) {
        const lockText = dataLock ? `ngày hôm qua (${dataLock})` : "ngày hôm qua";
        setText(subtitle, `Gợi ý được tạo từ dữ liệu khóa đến ${lockText}. Các số cuối cùng không hiển thị công khai trên trang.`);
      }
    }
  }

  function installZaloRouting() {
    if (document.documentElement.dataset.zaloOnlyRouting === "true") return;
    document.documentElement.dataset.zaloOnlyRouting = "true";
    document.addEventListener("click", (event) => {
      const target = event.target.closest('.portal-paid-card [data-open-checkout], [data-zalo-route="true"]');
      if (!target) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      window.open(ZALO_URL, "_blank", "noopener");
    }, true);
  }

  function boot() {
    if (window.location.pathname !== "/") return;
    installZaloRouting();
    applyCopyLock();
    const observer = new MutationObserver(applyCopyLock);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["hidden", "data-returning-ai-buyer"] });
    for (const delay of [50, 250, 750, 1500, 3000, 6000]) window.setTimeout(applyCopyLock, delay);
    window.setTimeout(() => {
      applyCopyLock();
      observer.disconnect();
    }, 10000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
