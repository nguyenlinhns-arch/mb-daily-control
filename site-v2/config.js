// Public endpoint only. Administrative approval secrets must never be stored here.
window.ORDER_CONFIRMATION_ENDPOINT = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec";

// Keep the paid AI report as the primary mobile conversion.
try {
  sessionStorage.setItem("lm_shopee_nudge_v1", "shown");
} catch (_) {}

// Privacy-safe first-party attribution. This random browser identifier contains
// no name, phone number, email address or device fingerprint. app.js persists
// the attribution object with each payment claim so Orders can distinguish
// repeat-browser purchases without changing the backend schema.
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

// Paid-delivery compatibility layer.
// The existing Apps Script endpoint still returns the legacy two-pair schema.
// During the MB ALL transition, Paid_Report can write the same two-number MB ALL
// result into both legacy slots. Only after the order is approved do we collapse
// that duplicate payload into one paid MB ALL result for the customer.
(() => {
  "use strict";

  function normalizePair(card) {
    if (!card) return [];
    return Array.from(card.querySelectorAll("strong, .delivery-number, .number"))
      .map((node) => String(node.textContent || "").match(/\b\d{2}\b/g) || [])
      .flat()
      .slice(0, 2);
  }

  function collapsePaidDelivery() {
    const view = document.querySelector("#delivery-view, [data-delivery-view]");
    if (!view || view.hidden) return;

    const cards = Array.from(view.querySelectorAll(".delivery-pair, [data-delivery-pair]"));
    if (cards.length < 2) return;

    const first = normalizePair(cards[0]);
    const second = normalizePair(cards[1]);
    if (first.length !== 2 || second.length !== 2 || first.join("|") !== second.join("|")) return;

    cards[1].remove();

    const rank = cards[0].querySelector(
      ".delivery-pair-rank, .delivery-rank, [data-delivery-rank]"
    );
    if (rank) rank.textContent = "SỐ CHỌN MB ALL";

    const reportDate = String(document.body?.dataset?.reportDate || "").trim();
    const title = view.querySelector("#delivery-title, h2, h3, [data-delivery-title]");
    if (title) title.textContent = reportDate ? `Số MB ALL ngày ${reportDate}` : "Số MB ALL hôm nay";

    const pairWrap = view.querySelector("#delivery-pairs, [data-delivery-pairs]");
    if (pairWrap) pairWrap.setAttribute("aria-label", `Số MB ALL: ${first.join(", ")}`);

    view.dataset.mballCollapsed = "true";
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
    collapsePaidDelivery();
    const observer = new MutationObserver(() => {
      collapsePaidDelivery();
      relabelPublicMethods();
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["hidden", "class"]
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
