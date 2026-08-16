(() => {
  "use strict";

  function reportDateLabel() {
    const bodyDate = String(document.body?.dataset?.reportDate || "").trim();
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(bodyDate)) return bodyDate;
    const text = document.body?.textContent || "";
    const target = text.match(/Target\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/Gợi\s+ý\s+số\s+(?:cho\s+)?ngày\s+hôm\s+nay(?:\s*[·:-]?\s*)(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/Bản\s+phân\s+tích\s+AI\s+ngày\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/LÊ\s+MIỀN\s+BẮC\s+NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i);
    return target ? target[1] : "";
  }

  function setText(node, value) {
    if (node && (node.textContent || "").trim() !== value) node.textContent = value;
  }

  function applyCopyLock() {
    if (window.location.pathname !== "/") return;
    const date = reportDateLabel();
    if (!date) return;

    const lead = document.querySelector(".portal-hero .portal-lead");
    if (lead) {
      const desired = `Theo dõi dữ liệu kỳ gần nhất, tần suất, lô gan, cặp đảo và các phương pháp công khai. Gợi ý số cho ngày hôm nay <strong>${date}</strong> chỉ với 30.000đ.`;
      if (lead.innerHTML !== desired) lead.innerHTML = desired;
      lead.dataset.dailySalesCopy = "v2";
    }

    const paidCard = document.querySelector(".portal-paid-card");
    if (paidCard) {
      const eyebrow = paidCard.querySelector("small");
      setText(eyebrow, "GỢI Ý SỐ HÔM NAY");

      const title = paidCard.querySelector("h2");
      setText(title, `Gợi ý số ngày hôm nay · ${date}`);

      let readyNote = paidCard.querySelector(".lm-returning-note");
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
      paidCard.dataset.dailyOfferCopy = "v3";
    }

    const sticky = document.querySelector("[data-ai-sticky-cta]");
    if (sticky) {
      setText(sticky, "MỞ GỢI Ý SỐ HÔM NAY · 30.000Đ");
      sticky.setAttribute("aria-label", `Mở gợi ý số ngày hôm nay ${date}, giá 30.000 đồng`);
    }

    const heading = [...document.querySelectorAll(".portal-section-title h2")]
      .find((node) => /^(Phương pháp công khai hôm nay|Gợi ý số ngày hôm nay)/i.test((node.textContent || "").trim()));
    if (heading) {
      const desiredHeading = `Gợi ý số ngày hôm nay · ${date}`;
      setText(heading, desiredHeading);
      heading.dataset.dailyRecommendationHeading = "v3";
      const subtitle = heading.parentElement?.querySelector("p");
      if (subtitle && /^Số được tạo/i.test(subtitle.textContent || "")) {
        subtitle.textContent = (subtitle.textContent || "").replace(/^Số được tạo/i, "Gợi ý được tạo");
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
