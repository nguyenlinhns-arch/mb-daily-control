(() => {
  "use strict";

  function reportDateLabel() {
    const bodyDate = String(document.body?.dataset?.reportDate || "").trim();
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(bodyDate)) return bodyDate;
    const text = document.body?.textContent || "";
    const target = text.match(/Target\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/Gợi\s+ý\s+số[^\n]{0,80}?(\d{2}\/\d{2}\/\d{4})/i)
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

  function applyCopyLock() {
    if (window.location.pathname !== "/") return;
    const date = reportDateLabel();
    const dataLock = dataLockLabel();
    if (!date) return;

    const lead = document.querySelector(".portal-hero .portal-lead");
    if (lead) {
      const desired = `Theo dõi dữ liệu kỳ gần nhất, tần suất, lô gan, cặp đảo và các phương pháp công khai. Gợi ý số cho ngày hôm nay <strong>${date}</strong> chỉ với 30.000đ.`;
      if (lead.innerHTML !== desired) lead.innerHTML = desired;
      lead.dataset.dailySalesCopy = "v3";
    }

    const paidCard = document.querySelector(".portal-paid-card");
    if (paidCard) {
      setText(paidCard.querySelector("small"), "GỢI Ý SỐ HÔM NAY");
      setText(paidCard.querySelector("h2"), `Gợi ý số ngày hôm nay - ${date}`);

      let readyNote = paidCard.querySelector(".lm-returning-note");
      const title = paidCard.querySelector("h2");
      if (!readyNote && title) {
        readyNote = document.createElement("div");
        readyNote.className = "lm-returning-note";
        title.insertAdjacentElement("afterend", readyNote);
      }
      setText(readyNote, `Gợi ý ngày ${date} đã sẵn sàng · mở một lần · không cần tạo tài khoản.`);

      const button = paidCard.querySelector("[data-open-checkout]");
      if (button) {
        setText(button, "MỞ GỢI Ý SỐ HÔM NAY · 30.000Đ");
        button.setAttribute("aria-label", `Mở gợi ý số ngày hôm nay ${date}, giá 30.000 đồng`);
      }
      paidCard.dataset.dailyOfferCopy = "v4";
    }

    const sticky = document.querySelector("[data-ai-sticky-cta]");
    if (sticky) {
      setText(sticky, "MỞ GỢI Ý SỐ HÔM NAY · 30.000Đ");
      sticky.setAttribute("aria-label", `Mở gợi ý số ngày hôm nay ${date}, giá 30.000 đồng`);
    }

    const heading = document.querySelector('[data-daily-recommendation-heading]')
      || [...document.querySelectorAll(".portal-section-title h2")]
        .find((node) => /^(Phương pháp công khai|Gợi ý số)/i.test((node.textContent || "").trim()));
    if (heading) {
      setText(heading, `Gợi ý số ngày hôm nay - ${date}`);
      heading.dataset.dailyRecommendationHeading = "v4";
      const subtitle = heading.parentElement?.querySelector("p");
      if (subtitle) {
        const lockText = dataLock ? `ngày hôm qua (${dataLock})` : "ngày hôm qua";
        setText(subtitle, `Gợi ý được tạo từ dữ liệu khóa đến ${lockText}. Kết luận các số cuối cùng không nằm trong danh sách công khai này.`);
      }
    }
  }

  function boot() {
    if (window.location.pathname !== "/") return;
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
