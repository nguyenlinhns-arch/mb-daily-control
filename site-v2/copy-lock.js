(() => {
  "use strict";

  function reportDateLabel() {
    const bodyDate = String(document.body?.dataset?.reportDate || "").trim();
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(bodyDate)) return bodyDate;
    const text = document.body?.textContent || "";
    const target = text.match(/Target\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/Bản\s+phân\s+tích\s+AI\s+ngày\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/LÊ\s+MIỀN\s+BẮC\s+NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i);
    return target ? target[1] : "";
  }

  function applyCopyLock() {
    if (window.location.pathname !== "/") return;
    const date = reportDateLabel();
    if (!date) return;

    const lead = document.querySelector(".portal-hero .portal-lead");
    if (lead) {
      const desired = `Theo dõi dữ liệu kỳ gần nhất, tần suất, lô gan, cặp đảo và các phương pháp công khai. Gợi ý số cho ngày hôm nay <strong>${date}</strong> chỉ với 30.000đ.`;
      if (lead.innerHTML !== desired) lead.innerHTML = desired;
      lead.dataset.dailySalesCopy = "v1";
    }

    const heading = [...document.querySelectorAll(".portal-section-title h2")]
      .find((node) => /^(Phương pháp công khai hôm nay|Gợi ý số ngày hôm nay)/i.test((node.textContent || "").trim()));
    if (heading) {
      const desiredHeading = `Gợi ý số ngày hôm nay · ${date}`;
      if ((heading.textContent || "").trim() !== desiredHeading) heading.textContent = desiredHeading;
      heading.dataset.dailyRecommendationHeading = "v2";
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
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    window.setTimeout(applyCopyLock, 50);
    window.setTimeout(applyCopyLock, 300);
    window.setTimeout(applyCopyLock, 1000);
    window.setTimeout(() => {
      applyCopyLock();
      observer.disconnect();
    }, 2500);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
