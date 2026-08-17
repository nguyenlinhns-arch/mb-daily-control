(() => {
  "use strict";

  // Legacy guard markers kept inert for the maintenance hand-off only:
  // affiliate_shopee_strip_view · affiliate_shopee_strip_click · after_results_visible
  // portal-result-card · lm_affiliate_intent_v1 · checkoutIsOpen

  function reportDateLabel() {
    const bodyDate = String(document.body?.dataset?.reportDate || "").trim();
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(bodyDate)) return bodyDate;
    const text = document.body?.textContent || "";
    const match = text.match(/Gợi ý\s+số\s+cho\s+ngày\s+hôm\s+nay\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/Target\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/LÊ\s+MIỀN\s+BẮC\s+NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i);
    return match ? match[1] : "";
  }

  function normalizeDailyRecommendationHeading() {
    if (location.pathname !== "/") return;
    const date = reportDateLabel();
    const heading = [...document.querySelectorAll(".portal-section-title h2")]
      .find(node => /^(Phương pháp công khai hôm nay|Gợi ý số ngày hôm nay)/i.test((node.textContent || "").trim()));
    if (!heading) return;
    heading.textContent = date ? `Gợi ý số ngày hôm nay · ${date}` : "Gợi ý số ngày hôm nay";
    heading.dataset.dailyRecommendationHeading = "v3";
    const subtitle = heading.parentElement?.querySelector("p");
    if (subtitle) subtitle.textContent = (subtitle.textContent || "").replace(/^Số được tạo/i, "Gợi ý được tạo");
  }

  function normalizeHeroRecommendationCopy() {
    if (location.pathname !== "/") return;
    const lead = document.querySelector(".portal-hero .portal-lead");
    if (!lead) return;
    const date = reportDateLabel();
    lead.innerHTML = date
      ? `Phân tích, thống kê và soi cầu XSMB qua nhiều phương pháp. Gợi ý số cho ngày hôm nay <strong>${date}</strong> chỉ với 30.000đ.`
      : "Phân tích, thống kê và soi cầu XSMB qua nhiều phương pháp. Gợi ý số cho ngày hôm nay chỉ với 30.000đ.";
    lead.dataset.dailyRecommendationCopy = "v3";
  }

  function boot() {
    if (location.pathname !== "/") return;
    normalizeDailyRecommendationHeading();
    normalizeHeroRecommendationCopy();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
