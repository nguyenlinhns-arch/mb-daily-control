// Public endpoint only. Administrative approval secrets must never be stored here.
window.ORDER_CONFIRMATION_ENDPOINT = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec";

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
