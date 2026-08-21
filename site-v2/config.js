// Public endpoint only. Administrative approval secrets must never be stored here.
window.ORDER_CONFIRMATION_ENDPOINT = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec";

// The product grid remains available after useful content, but the legacy
// floating Shopee nudge is intentionally suppressed before checkout-enhance.js
// installs its timer. This keeps AI checkout as the primary mobile conversion.
try {
  sessionStorage.setItem("lm_shopee_nudge_v1", "shown");
} catch (_) {}

// Privacy-safe first-party attribution. This random browser identifier contains
// no name, phone number, email address or device fingerprint. app.js already
// persists the attribution object with each payment claim, so adding the ID
// here lets Orders distinguish repeat-browser purchases without a backend
// schema change. We also preserve first-touch and last-touch source hints so
// paid/social traffic is not incorrectly lumped into direct/unknown.
(() => {
  "use strict";
  const VISITOR_KEY = "lemienbac_visitor_v1";
  const ATTRIBUTION_KEY = "lemienbac_attribution_v1";
  const visitorPattern = /^v1_[0-9a-f]{32}$/;
  const url = new URL(window.location.href);

  function sourceHint(params) {
    const utmSource = String(params.get("utm_source") || "").trim().toLowerCase();
    if (utmSource) return utmSource.slice(0, 80);
    if (params.get("gclid") || params.get("gbraid") || params.get("wbraid")) return "google_ads";
    if (params.get("fbclid")) return "facebook";
    if (params.get("zarsrc") || params.get("gidzl")) return "zalo";
    try {
      if (document.referrer) {
        const ref = new URL(document.referrer);
        if (ref.hostname && ref.hostname !== url.hostname) return ref.hostname.slice(0, 120);
      }
    } catch (_) {}
    return "direct_or_unknown";
  }

  try {
    let visitorId = String(localStorage.getItem(VISITOR_KEY) || "");
    if (!visitorPattern.test(visitorId)) {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      visitorId = `v1_${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
      localStorage.setItem(VISITOR_KEY, visitorId);
    }

    let attribution = {};
    try {
      attribution = JSON.parse(localStorage.getItem(ATTRIBUTION_KEY) || "{}") || {};
    } catch (_) {
      attribution = {};
    }

    const now = new Date().toISOString();
    const hint = sourceHint(url.searchParams);
    attribution.visitor_id = visitorId;
    attribution.visitor_id_version = 1;
    attribution.commerce_measurement = "baseline_v1";
    if (!attribution.first_source_hint) attribution.first_source_hint = hint;
    if (!attribution.first_landing_page) attribution.first_landing_page = `${url.origin}${url.pathname}`;
    if (!attribution.first_seen_at) attribution.first_seen_at = now;
    attribution.last_source_hint = hint;
    attribution.last_landing_page = `${url.origin}${url.pathname}`;
    attribution.last_seen_at = now;

    for (const key of ["fbclid", "zarsrc", "gidzl"]) {
      const value = url.searchParams.get(key);
      if (value) attribution[key] = value.slice(0, 250);
    }
    if (document.referrer) {
      try {
        const ref = new URL(document.referrer);
        if (ref.hostname && ref.hostname !== url.hostname) attribution.referrer_host = ref.hostname.slice(0, 120);
      } catch (_) {}
    }

    localStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(attribution));
  } catch (_) {
    // Storage may be unavailable in strict privacy modes; checkout still works.
  }
})();

// MAX2 delivery compatibility layer.
// The existing Apps Script web app still returns the legacy two-pair schema.
// During the MB ALL transition the private Paid_Report writes the same MAX2
// pair into both legacy slots. After approval this observer collapses that
// duplicated compatibility payload to one two-number Production result, so the
// customer never sees a fake second pair or a mixed legacy 4SO recommendation.
(() => {
  "use strict";

  function normalizePair(card) {
    if (!card) return [];
    const values = Array.from(card.querySelectorAll("strong, .delivery-number, .number"))
      .map((node) => String(node.textContent || "").match(/\b\d{2}\b/g) || [])
      .flat();
    return values.slice(0, 2);
  }

  function collapseMax2Delivery() {
    const view = document.querySelector("#delivery-view, [data-delivery-view]");
    if (!view || view.hidden) return;
    const cards = Array.from(view.querySelectorAll(".delivery-pair, [data-delivery-pair]"));
    if (cards.length < 2) return;
    const first = normalizePair(cards[0]);
    const second = normalizePair(cards[1]);
    if (first.length !== 2 || second.length !== 2 || first.join("|") !== second.join("|")) return;

    cards[1].remove();
    const rank = cards[0].querySelector(".delivery-rank, [data-delivery-rank]");
    if (rank) rank.textContent = "SỐ CHỌN PRODUCTION";
    const title = view.querySelector("h2, h3, [data-delivery-title]");
    const reportDate = String(document.body?.dataset?.reportDate || "").trim();
    if (title) title.textContent = reportDate ? `Số MAX2 ngày ${reportDate}` : "Số MAX2 hôm nay";
    view.dataset.max2Collapsed = "true";
  }

  function relabelPublicMethods() {
    for (const node of document.querySelectorAll("h1,h2,h3,p,span")) {
      if (String(node.textContent || "").trim() === "Phương pháp công khai hôm nay") {
        node.textContent = "Phương pháp công khai theo dữ liệu T−1";
      }
    }
  }

  const start = () => {
    relabelPublicMethods();
    collapseMax2Delivery();
    const observer = new MutationObserver(() => {
      collapseMax2Delivery();
      relabelPublicMethods();
    });
    observer.observe(document.body, {subtree: true, childList: true, attributes: true, attributeFilter: ["hidden", "class"]});
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();
})();
