(() => {
  "use strict";

  const ATTR_V1_KEY = "lemienbac_attribution_v1";
  const ATTR_V2_KEY = "lemienbac_attribution_v2";
  const VISITOR_KEY = "lemienbac_visitor_v1";
  const SESSION_KEY = "lemienbac_session_v2";
  const visitorPattern = /^v1_[0-9a-f]{32}$/;

  const readJson = (key) => {
    try { return JSON.parse(localStorage.getItem(key) || "{}") || {}; }
    catch (_) { return {}; }
  };
  const lset = (key, value) => { try { localStorage.setItem(key, value); } catch (_) {} };
  const ssget = (key) => { try { return sessionStorage.getItem(key); } catch (_) { return null; } };
  const ssset = (key, value) => { try { sessionStorage.setItem(key, value); } catch (_) {} };
  const short = (value, limit = 160) => String(value || "").trim().slice(0, limit);

  function randomHex(bytesLength = 16) {
    try {
      const bytes = new Uint8Array(bytesLength);
      crypto.getRandomValues(bytes);
      return Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
    } catch (_) {
      return `${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`.slice(0, bytesLength * 2).padEnd(bytesLength * 2, "0");
    }
  }

  function ensureVisitorId() {
    let id = "";
    try { id = String(localStorage.getItem(VISITOR_KEY) || ""); } catch (_) {}
    if (!visitorPattern.test(id)) {
      id = `v1_${randomHex(16)}`;
      lset(VISITOR_KEY, id);
    }
    return id;
  }

  function ensureSessionId() {
    let id = ssget(SESSION_KEY) || "";
    if (!/^s2_[0-9a-f]{24,40}$/.test(id)) {
      id = `s2_${randomHex(12)}`;
      ssset(SESSION_KEY, id);
    }
    return id;
  }

  function sourceGroupFromHint(hint) {
    const value = String(hint || "").toLowerCase();
    if (!value || value === "direct_or_unknown" || value === "direct") return "direct";
    if (value.includes("google_ads") || value === "googleads" || value === "google-ads") return "google_ads";
    if (value.includes("google")) return "google_organic";
    if (value.includes("facebook") || value.includes("fb") || value.includes("instagram") || value.includes("meta")) return "facebook";
    if (value.includes("zalo")) return "zalo";
    return "other";
  }

  function detectTouch() {
    const url = new URL(location.href);
    const p = url.searchParams;
    const utmSource = short(p.get("utm_source"), 80).toLowerCase();
    const utmMedium = short(p.get("utm_medium"), 80).toLowerCase();
    const utmCampaign = short(p.get("utm_campaign"), 120);
    const utmContent = short(p.get("utm_content"), 120);
    const utmTerm = short(p.get("utm_term"), 120);
    const paidMedium = /^(cpc|ppc|paid|paid_search|paid-search|paidsearch|paid_social|paid-social|paidsocial|social_paid)$/i.test(utmMedium);
    const hasGoogleClickId = ["gclid", "gbraid", "wbraid"].some(key => p.has(key));
    const hasFbclid = p.has("fbclid");
    const hasZaloId = p.has("zarsrc") || p.has("gidzl");

    const common = { utm_source: utmSource, utm_medium: utmMedium, utm_campaign: utmCampaign, utm_content: utmContent, utm_term: utmTerm };
    if (hasGoogleClickId) return { ...common, group: "google_ads", source: "google", medium: utmMedium || "cpc", evidence: "google_click_id", explicit: true };
    if (/^(google|googleads|google-ads)$/i.test(utmSource) && paidMedium) return { ...common, group: "google_ads", source: "google", medium: utmMedium || "cpc", evidence: "utm_paid", explicit: true };

    if (/^(facebook|fb|meta|instagram)$/i.test(utmSource)) {
      return { ...common, group: paidMedium ? "facebook_ads" : "facebook_social", source: utmSource === "instagram" ? "instagram" : "facebook", medium: utmMedium || (paidMedium ? "paid_social" : "social"), evidence: paidMedium ? "utm_paid" : "utm_social", explicit: true };
    }
    if (hasFbclid) return { ...common, group: "facebook_click", source: "facebook", medium: utmMedium || "referral", evidence: "fbclid", explicit: true };

    if (/^zalo$/i.test(utmSource) || hasZaloId) return { ...common, group: "zalo", source: "zalo", medium: utmMedium || "social", evidence: hasZaloId ? "zalo_click_id" : "utm", explicit: true };

    if (utmSource) return { ...common, group: "other_campaign", source: utmSource, medium: utmMedium || "campaign", evidence: "utm", explicit: true };

    try {
      if (document.referrer) {
        const ref = new URL(document.referrer);
        const host = ref.hostname.toLowerCase();
        if (host && host !== url.hostname) {
          if (/(^|\.)google\./.test(host)) return { ...common, group: "google_organic", source: "google", medium: "organic", evidence: "referrer", explicit: true };
          if (/(^|\.)(facebook\.com|fb\.com|instagram\.com)$/.test(host) || host === "l.facebook.com" || host === "lm.facebook.com") return { ...common, group: "facebook_social", source: host.includes("instagram") ? "instagram" : "facebook", medium: "social", evidence: "referrer", explicit: true };
          if (host === "zalo.me" || host.endsWith(".zalo.me")) return { ...common, group: "zalo", source: "zalo", medium: "social", evidence: "referrer", explicit: true };
          return { ...common, group: "referral", source: host, medium: "referral", evidence: "referrer", explicit: true };
        }
      }
    } catch (_) {}
    return { ...common, group: "direct", source: "direct", medium: "none", evidence: "none", explicit: false };
  }

  function copyClickIds(target, params) {
    for (const key of ["gclid", "gbraid", "wbraid", "fbclid", "zarsrc", "gidzl"]) {
      const value = params.get(key);
      if (value) target[key] = short(value, 250);
    }
  }

  function syncAttribution() {
    const url = new URL(location.href);
    const touch = detectTouch();
    const legacy = readJson(ATTR_V1_KEY);
    let attr = readJson(ATTR_V2_KEY);
    const now = new Date().toISOString();
    const visitorId = ensureVisitorId();
    const sessionId = ensureSessionId();

    if (!attr.visitor_id) attr.visitor_id = legacy.visitor_id || visitorId;
    attr.visitor_id = visitorId;
    attr.visitor_id_version = 2;
    attr.session_id = sessionId;
    attr.attribution_schema = "first_last_non_direct_v2";
    attr.commerce_measurement = "source_attribution_v2";

    if (!attr.first_seen_at) attr.first_seen_at = legacy.first_seen_at || now;
    if (!attr.first_landing_page) attr.first_landing_page = legacy.first_landing_page || legacy.landing_page || `${url.origin}${url.pathname}`;
    if (!attr.first_source_group) {
      attr.first_source_group = legacy.first_source_group || sourceGroupFromHint(legacy.first_source_hint) || touch.group;
      attr.first_source = legacy.first_source || legacy.first_source_hint || touch.source;
      attr.first_medium = legacy.first_medium || (attr.first_source_group === "direct" ? "none" : touch.medium);
    }

    if (touch.explicit || !attr.last_source_group || attr.last_source_group === "direct") {
      attr.last_source_group = touch.group;
      attr.last_source = touch.source;
      attr.last_medium = touch.medium;
      attr.last_campaign = touch.utm_campaign || attr.last_campaign || "";
      attr.last_content = touch.utm_content || attr.last_content || "";
      attr.last_term = touch.utm_term || attr.last_term || "";
      attr.last_evidence = touch.evidence;
      attr.last_touch_at = now;
    }

    attr.first_source_hint = attr.first_source_group;
    attr.last_source_hint = attr.last_source_group || "direct";
    attr.last_landing_page = `${url.origin}${url.pathname}`;
    attr.last_seen_at = now;
    attr.current_page_path = url.pathname;
    attr.current_touch_group = touch.group;
    attr.current_touch_evidence = touch.evidence;
    copyClickIds(attr, url.searchParams);

    try {
      if (document.referrer) {
        const ref = new URL(document.referrer);
        if (ref.hostname && ref.hostname !== url.hostname) attr.referrer_host = short(ref.hostname, 120);
      }
    } catch (_) {}

    const serialized = JSON.stringify(attr);
    lset(ATTR_V2_KEY, serialized);
    lset(ATTR_V1_KEY, serialized);
    return attr;
  }

  let ATTRIBUTION = syncAttribution();
  const trafficContext = () => ({
    traffic_source_group: ATTRIBUTION.last_source_group || "direct",
    traffic_source: ATTRIBUTION.last_source || "direct",
    traffic_medium: ATTRIBUTION.last_medium || "none",
    traffic_campaign: ATTRIBUTION.last_campaign || "",
    traffic_first_source_group: ATTRIBUTION.first_source_group || "direct",
    traffic_session_id: ATTRIBUTION.session_id || ""
  });

  const emitTraffic = () => {
    ATTRIBUTION = syncAttribution();
    const payload = {
      event: "traffic_source_session",
      page_path: location.pathname,
      ...trafficContext(),
      has_google_click_id: Boolean(ATTRIBUTION.gclid || ATTRIBUTION.gbraid || ATTRIBUTION.wbraid),
      has_fbclid: Boolean(ATTRIBUTION.fbclid),
      attribution_schema: "first_last_non_direct_v2"
    };
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(payload);
    if (typeof window.gtag === "function") {
      window.gtag("event", "traffic_source_session", {
        page_path: payload.page_path,
        traffic_source_group: payload.traffic_source_group,
        traffic_source: payload.traffic_source,
        traffic_medium: payload.traffic_medium,
        traffic_campaign: payload.traffic_campaign,
        traffic_first_source_group: payload.traffic_first_source_group,
        attribution_schema: payload.attribution_schema
      });
    }
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", emitTraffic, { once: true });
  else emitTraffic();
  document.addEventListener("click", event => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target?.closest("[data-open-checkout],[data-ai-sticky-cta]")) return;
    ATTRIBUTION = syncAttribution();
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: "traffic_checkout_intent", page_path: location.pathname, ...trafficContext() });
  }, true);

  const OFFER = {
    id: "vpbank-vay-online",
    merchant: "VPBank",
    url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
  };

  const CLOSED_KEY = "lm_vpbank_banner_closed_v3";
  const MIN_DELAY_MS = 3000;
  const MIN_SCROLL_RATIO = 0.08;
  let timer = 0;
  let scrollHandler = null;
  let reopenTimer = 0;

  // Retire old suppression state so users who saw the previous 24h-cooldown
  // version are immediately eligible for the new banner.
  try {
    sessionStorage.removeItem("lm_finance_sitewide_banner_v1");
    localStorage.removeItem("lm_finance_sitewide_last_shown_v1");
    sessionStorage.removeItem("lm_finance_early_banner_v1");
    localStorage.removeItem("lm_finance_last_shown_v2");
  } catch (_) {}

  const emit = (event, extra = {}) => {
    ATTRIBUTION = syncAttribution();
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: location.pathname,
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: OFFER.id,
      merchant: OFFER.merchant,
      placement: "early_finance_banner_sitewide_v3",
      ...trafficContext(),
      ...extra
    });
  };

  const sget = key => { try { return sessionStorage.getItem(key); } catch (_) { return null; } };
  const sset = (key, value) => { try { sessionStorage.setItem(key, value); } catch (_) {} };

  function pageAllowed() {
    return !/(?:^|\/)404(?:\.html)?\/?$/i.test(location.pathname)
      && !/^\/go\/shopee\/?$/i.test(location.pathname);
  }

  function checkoutIsOpen() {
    const checkout = document.getElementById("checkout");
    return Boolean(checkout && checkout.hidden === false);
  }

  function depthRatio() {
    const height = Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight || 0);
    if (!height) return 0;
    return Math.min(1, (window.scrollY + window.innerHeight) / height);
  }

  function eligible() {
    return pageAllowed()
      && document.visibilityState === "visible"
      && !checkoutIsOpen()
      && sget(CLOSED_KEY) !== "1"
      && !document.getElementById("lm-sponsor-vp");
  }

  function stopTriggers() {
    if (timer) { clearTimeout(timer); timer = 0; }
    if (scrollHandler) { removeEventListener("scroll", scrollHandler); scrollHandler = null; }
  }

  function addStyle() {
    if (document.getElementById("lm-sponsor-vp-style")) return;
    const style = document.createElement("style");
    style.id = "lm-sponsor-vp-style";
    style.textContent = `
      .lm-sponsor-float{display:block!important;visibility:visible!important;opacity:1!important;position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:2147482000;width:min(820px,calc(100vw - 28px));border:1px solid rgba(255,255,255,.30);border-radius:20px;background:linear-gradient(120deg,#2b0b63 0%,#5a167c 45%,#e76e22 100%);box-shadow:0 18px 46px rgba(28,13,55,.30);overflow:hidden;color:#fff;animation:lmSponsorIn .2s ease-out both}
      .lm-sponsor-inner{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:center;padding:16px 18px 14px}.lm-sponsor-copy{min-width:0}.lm-sponsor-badge{display:inline-flex;padding:4px 7px;border-radius:999px;background:rgba(255,255,255,.16);color:#ffe6a8;font-size:8.5px;font-weight:1000;letter-spacing:.08em;text-transform:uppercase}.lm-sponsor-float h2{margin:6px 0 0;color:#fff;font-size:24px;line-height:1.08}.lm-sponsor-float p{margin:5px 0 0;color:rgba(255,255,255,.88);font-size:11.5px;line-height:1.4}.lm-sponsor-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}.lm-sponsor-meta span{display:inline-flex;align-items:center;min-height:26px;padding:0 8px;border:1px solid rgba(255,255,255,.2);border-radius:999px;background:rgba(255,255,255,.08);color:#fff;font-size:9px;font-weight:850}.lm-sponsor-cta{appearance:none;border:0;min-width:170px;min-height:48px;display:flex;align-items:center;justify-content:center;padding:0 18px;border-radius:14px;background:linear-gradient(135deg,#ff7a22,#ffb11a);color:#fff;font-size:12px;font-weight:1000;cursor:pointer}.lm-sponsor-x{position:absolute;top:8px;right:8px;width:28px;height:28px;border:1px solid rgba(255,255,255,.25);border-radius:50%;background:rgba(255,255,255,.16);color:#fff;font-size:18px;line-height:1;cursor:pointer}.lm-sponsor-note{display:block;padding:0 18px 10px;color:rgba(255,255,255,.70);font-size:8px;line-height:1.35}
      @keyframes lmSponsorIn{from{opacity:0;transform:translate(-50%,10px)}to{opacity:1;transform:translate(-50%,0)}}
      @media(max-width:700px){.lm-sponsor-float{left:10px;right:10px;bottom:calc(66px + env(safe-area-inset-bottom,0px));width:auto;transform:none;border-radius:17px}.lm-sponsor-inner{grid-template-columns:1fr;padding:13px 13px 11px;gap:10px}.lm-sponsor-float h2{padding-right:32px;font-size:20px}.lm-sponsor-float p{font-size:10.5px}.lm-sponsor-cta{width:100%;min-width:0;min-height:46px}.lm-sponsor-x{top:7px;right:7px;width:26px;height:26px}@keyframes lmSponsorIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}}
      @media(prefers-reduced-motion:reduce){.lm-sponsor-float{animation:none}}
    `;
    document.head.appendChild(style);
  }

  function closeOffer(reason, explicit = false) {
    const node = document.getElementById("lm-sponsor-vp");
    if (node) node.remove();
    if (explicit) {
      sset(CLOSED_KEY, "1");
      emit("affiliate_finance_close", { trigger: reason });
    }
  }

  function openOffer(trigger) {
    emit("affiliate_finance_click", { trigger });
    const popup = window.open(OFFER.url, "_blank", "noopener,noreferrer");
    if (!popup) location.href = OFFER.url;
  }

  function showOffer(trigger) {
    if (!eligible()) return;
    stopTriggers();
    addStyle();

    const offer = document.createElement("aside");
    offer.id = "lm-sponsor-vp";
    offer.className = "lm-sponsor-float";
    offer.setAttribute("role", "complementary");
    offer.setAttribute("aria-label", "Ưu đãi vay tiền online tài trợ");
    offer.innerHTML = `
      <button class="lm-sponsor-x" type="button" aria-label="Đóng quảng cáo">×</button>
      <div class="lm-sponsor-inner">
        <div class="lm-sponsor-copy">
          <span class="lm-sponsor-badge">Tài trợ · ACCESSTRADE · VPBank</span>
          <h2>Vay tiền online</h2>
          <p>Xem ưu đãi, điều kiện và đăng ký online theo chính sách của VPBank.</p>
          <div class="lm-sponsor-meta"><span>Đăng ký online</span><span>Xem điều kiện</span><span>VPBank xét duyệt</span></div>
        </div>
        <button class="lm-sponsor-cta" type="button" data-go-vpbank>XEM NGAY →</button>
      </div>
      <span class="lm-sponsor-note">Liên kết tài trợ qua ACCESSTRADE. Điều kiện và quyết định thực tế do VPBank áp dụng.</span>`;

    offer.querySelector(".lm-sponsor-x")?.addEventListener("click", () => closeOffer("top_close", true));
    offer.querySelector("[data-go-vpbank]")?.addEventListener("click", () => openOffer(trigger));
    document.body.appendChild(offer);
    emit("affiliate_finance_view", { trigger, scroll_ratio: Number(depthRatio().toFixed(2)) });
  }

  function armTriggers(delay = MIN_DELAY_MS) {
    stopTriggers();
    if (!eligible()) return;
    const started = Date.now();
    timer = setTimeout(() => { if (eligible()) showOffer("early_3s"); }, delay);
    scrollHandler = () => {
      if (!eligible()) return;
      if (depthRatio() >= MIN_SCROLL_RATIO || Date.now() - started >= MIN_DELAY_MS) showOffer("early_scroll_08");
    };
    addEventListener("scroll", scrollHandler, { passive: true });
  }

  function installSuppression() {
    document.addEventListener("click", event => {
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest("[data-open-checkout],[data-ai-sticky-cta]")) closeOffer("checkout_intent", false);
    }, true);

    if (document.body && "MutationObserver" in window) {
      new MutationObserver(() => {
        if (checkoutIsOpen()) {
          closeOffer("checkout_open", false);
          return;
        }
        if (sget(CLOSED_KEY) !== "1" && !document.getElementById("lm-sponsor-vp")) {
          clearTimeout(reopenTimer);
          reopenTimer = setTimeout(() => armTriggers(1200), 250);
        }
      }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden"] });
    }
  }

  function installOffer() {
    installSuppression();
    armTriggers();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", installOffer, { once: true });
  else installOffer();
})();
