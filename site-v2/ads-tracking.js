(() => {
  "use strict";

  const ADS_SESSION_KEY = "lm_google_ads_visit_v1";

  function isGoogleAdsVisit(url) {
    const paidMedium = /^(cpc|ppc|paid|paidsearch|paid-search)$/i.test(url.searchParams.get("utm_medium") || "");
    const googleSource = /^(google|googleads|google-ads)$/i.test(url.searchParams.get("utm_source") || "");
    return ["gclid", "gbraid", "wbraid"].some((key) => url.searchParams.has(key))
      || (googleSource && paidMedium);
  }

  function paidSession() {
    const direct = isGoogleAdsVisit(new URL(window.location.href));
    if (direct) {
      try { sessionStorage.setItem(ADS_SESSION_KEY, "1"); } catch (_) {}
    }
    try { return direct || sessionStorage.getItem(ADS_SESSION_KEY) === "1"; }
    catch (_) { return direct; }
  }

  function emit(name, parameters = {}) {
    if (typeof window.gtag !== "function") return;
    const reportDate = document.body?.dataset?.reportDate || "";
    window.gtag("event", name, {
      report_date: reportDate,
      traffic_type: paidSession() ? "google_ads" : "other",
      ...parameters
    });
  }

  function loadNativeAd() {
    const slot = document.getElementById("lm-adsterra-native");
    const marker = slot?.querySelector("[data-lm-native-ad-src]");
    if (!slot || !marker || slot.dataset.lmAdLoaded === "true") return;
    const src = marker.getAttribute("data-lm-native-ad-src") || "";
    if (!src.startsWith("https://")) return;
    const script = document.createElement("script");
    script.async = true;
    script.dataset.cfasync = "false";
    script.src = src;
    slot.dataset.lmAdLoaded = "true";
    marker.replaceWith(script);
    emit("ad_slot_load", { slot: "native" });
  }

  function setupNativeLazyLoad() {
    const slot = document.getElementById("lm-adsterra-native");
    if (!slot?.querySelector("[data-lm-native-ad-src]")) return;
    if (!("IntersectionObserver" in window)) {
      loadNativeAd();
      return;
    }
    const saveData = Boolean(navigator.connection?.saveData);
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      loadNativeAd();
    }, { rootMargin: saveData ? "0px" : "600px 0px" });
    observer.observe(slot);
  }

  function trackSlotViews() {
    if (!("IntersectionObserver" in window)) return;
    const seen = new WeakSet();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.5 || seen.has(entry.target)) return;
        seen.add(entry.target);
        emit("ad_slot_view", { slot: entry.target.dataset.lmAdSlot || "unknown" });
        observer.unobserve(entry.target);
      });
    }, { threshold: [0.5] });
    document.querySelectorAll("[data-lm-ad-slot]").forEach((slot) => observer.observe(slot));
  }

  document.addEventListener("DOMContentLoaded", () => {
    const directPaidVisit = isGoogleAdsVisit(new URL(window.location.href));
    paidSession();
    if (directPaidVisit) emit("google_ads_landing_view", { page_path: window.location.pathname });

    setupNativeLazyLoad();
    trackSlotViews();

    const affiliate = document.getElementById("affiliate-shopee-smartlink");
    if (affiliate) {
      affiliate.addEventListener("click", () => {
        emit("affiliate_click", { partner: "accesstrade", merchant: "shopee", placement: "after_tools" });
      });
    }

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