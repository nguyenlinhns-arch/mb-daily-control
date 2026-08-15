(() => {
  "use strict";

  function isGoogleAdsVisit(url) {
    const paidMedium = /^(cpc|ppc|paid|paidsearch|paid-search)$/i.test(url.searchParams.get("utm_medium") || "");
    const googleSource = /^(google|googleads|google-ads)$/i.test(url.searchParams.get("utm_source") || "");
    return ["gclid", "gbraid", "wbraid"].some((key) => url.searchParams.has(key))
      || (googleSource && paidMedium);
  }

  function emit(name, parameters = {}) {
    if (typeof window.gtag !== "function") return;
    const reportDate = document.body?.dataset?.reportDate || "";
    window.gtag("event", name, {
      report_date: reportDate,
      traffic_type: isGoogleAdsVisit(new URL(window.location.href)) ? "google_ads" : "other",
      ...parameters
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const paidVisit = isGoogleAdsVisit(new URL(window.location.href));
    if (paidVisit) emit("google_ads_landing_view", { page_path: window.location.pathname });

    document.querySelectorAll("[data-open-checkout]").forEach((button) => {
      button.addEventListener("click", () => {
        emit("purchase_cta_click", {
          cta_position: button.dataset.ctaPosition || "unknown",
          currency: "VND",
          value: 30000
        });
      });
    });

    const history = document.querySelector(".history-disclosure");
    if (history) {
      history.addEventListener("toggle", () => {
        emit("history_toggle", { state: history.open ? "open" : "closed" });
      });
    }

    const close = document.getElementById("checkout-close");
    if (close) close.addEventListener("click", () => emit("checkout_close"));
  }, { once: true });
})();