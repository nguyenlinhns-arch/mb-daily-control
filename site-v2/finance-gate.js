(() => {
  "use strict";

  const OFFER = {
    id: "vpbank-vay-online",
    merchant: "VPBank",
    url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
  };

  const SESSION_KEY = "lm_finance_secondary_offer_v5";
  const AI_INTENT_KEY = "lm_ai_purchase_intent_v1";
  const AFFILIATE_INTENT_KEY = "lm_affiliate_intent_v1";
  const LAST_SHOWN_KEY = "lm_finance_last_shown_v1";
  const MIN_DELAY_MS = 60000;
  const MIN_SCROLL_RATIO = 0.72;
  const COOLDOWN_MS = 7 * 24 * 60 * 60 * 1000;
  let timer = 0;
  let scrollHandler = null;
  let previousFocus = null;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: window.location.pathname,
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: OFFER.id,
      merchant: OFFER.merchant,
      placement: "deep_engagement_secondary_offer",
      ...extra
    });
  }

  function sessionGet(key) {
    try { return sessionStorage.getItem(key); } catch (_) { return null; }
  }

  function sessionSet(key, value) {
    try { sessionStorage.setItem(key, value); } catch (_) {}
  }

  function localGet(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }

  function localSet(key, value) {
    try { localStorage.setItem(key, value); } catch (_) {}
  }

  function isPaidAcquisitionVisit() {
    const url = new URL(window.location.href);
    if (["gclid", "gbraid", "wbraid"].some(key => url.searchParams.has(key))) return true;
    const source = (url.searchParams.get("utm_source") || "").toLowerCase();
    const medium = (url.searchParams.get("utm_medium") || "").toLowerCase();
    return /^(google|googleads|google-ads|facebook|fb|meta)$/.test(source)
      && /^(cpc|ppc|paid|paidsearch|paid-search|paid_social|paidsocial)$/.test(medium);
  }

  function checkoutIsOpen() {
    const checkout = document.getElementById("checkout");
    return Boolean(checkout && checkout.hidden === false);
  }

  function hasAiIntent() {
    return sessionGet(AI_INTENT_KEY) === "1" || checkoutIsOpen();
  }

  function hasOtherAffiliateIntent() {
    return sessionGet(AFFILIATE_INTENT_KEY) === "1";
  }

  function recentlyShown() {
    const raw = Number(localGet(LAST_SHOWN_KEY) || 0);
    return Number.isFinite(raw) && raw > 0 && Date.now() - raw < COOLDOWN_MS;
  }

  function depthRatio() {
    const doc = document.documentElement;
    const body = document.body;
    const height = Math.max(doc.scrollHeight, body?.scrollHeight || 0);
    if (!height) return 0;
    return Math.min(1, (window.scrollY + window.innerHeight) / height);
  }

  function stopTriggers() {
    if (timer) {
      window.clearTimeout(timer);
      timer = 0;
    }
    if (scrollHandler) {
      window.removeEventListener("scroll", scrollHandler);
      scrollHandler = null;
    }
  }

  function markPrimaryIntent(event) {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    if (target.closest("[data-open-checkout], [data-ai-sticky-cta]")) {
      sessionSet(AI_INTENT_KEY, "1");
      stopTriggers();
      closeOffer("ai_intent", false);
      return;
    }
    if (target.closest(".lm-product-card, #affiliate-shopee-smartlink")) {
      sessionSet(AFFILIATE_INTENT_KEY, "1");
      stopTriggers();
      closeOffer("other_affiliate_intent", false);
    }
  }

  function eligible() {
    return window.location.pathname === "/"
      && document.visibilityState === "visible"
      && !isPaidAcquisitionVisit()
      && !hasAiIntent()
      && !hasOtherAffiliateIntent()
      && sessionGet(SESSION_KEY) !== "shown"
      && !recentlyShown()
      && !document.getElementById("lm-finance-secondary");
  }

  function addStyle() {
    if (document.getElementById("lm-finance-secondary-style")) return;
    const style = document.createElement("style");
    style.id = "lm-finance-secondary-style";
    style.textContent = `
      .lm-finance-secondary{position:fixed;right:18px;bottom:18px;z-index:72;width:min(390px,calc(100vw - 36px));border:1px solid #dfe8e4;border-radius:18px;background:#fff;box-shadow:0 16px 44px rgba(18,38,47,.20);overflow:hidden;animation:lmFinanceIn .2s ease-out both}
      .lm-finance-secondary-head{padding:15px 48px 10px 16px;background:linear-gradient(135deg,#f0faf7,#fff)}
      .lm-finance-secondary-badge{display:inline-flex;padding:4px 7px;border-radius:999px;background:#e4f6ef;color:#08745d;font-size:8.5px;font-weight:1000;letter-spacing:.07em;text-transform:uppercase}
      .lm-finance-secondary h2{margin:7px 0 0;color:#19313a;font-size:18px;line-height:1.18}.lm-finance-secondary p{margin:5px 0 0;color:#64777f;font-size:11px;line-height:1.4}
      .lm-finance-secondary-body{padding:0 16px 14px}.lm-finance-secondary-rate{display:flex;align-items:baseline;gap:5px;margin:1px 0 10px;color:#08745d}.lm-finance-secondary-rate strong{font-size:24px}.lm-finance-secondary-rate span{font-size:10px;font-weight:900}
      .lm-finance-secondary-actions{display:grid;grid-template-columns:1fr auto;gap:8px}.lm-finance-secondary-cta{min-height:44px;display:flex;align-items:center;justify-content:center;padding:0 12px;border-radius:11px;background:#f58220;color:#fff!important;text-decoration:none!important;font-size:11px;font-weight:1000}.lm-finance-secondary-close{min-height:44px;padding:0 12px;border:1px solid #dfe6e3;border-radius:11px;background:#fff;color:#58696f;font-size:11px;font-weight:900;cursor:pointer}.lm-finance-secondary-x{position:absolute;top:10px;right:10px;width:32px;height:32px;border:0;border-radius:50%;background:#eef3f1;color:#53646a;font-size:18px;cursor:pointer}.lm-finance-secondary-note{display:block;margin-top:7px;color:#929b9f;font-size:8px;line-height:1.35}
      @keyframes lmFinanceIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
      @media(max-width:700px){.lm-finance-secondary{left:10px;right:10px;bottom:calc(66px + env(safe-area-inset-bottom,0px));width:auto;border-radius:16px}.lm-finance-secondary-head{padding:12px 44px 8px 13px}.lm-finance-secondary h2{font-size:16px}.lm-finance-secondary-body{padding:0 13px 12px}.lm-finance-secondary-rate strong{font-size:21px}.lm-finance-secondary-actions{grid-template-columns:1fr auto}.lm-finance-secondary-cta,.lm-finance-secondary-close{min-height:42px;font-size:10.5px}}
      @media(prefers-reduced-motion:reduce){.lm-finance-secondary{animation:none}}
    `;
    document.head.appendChild(style);
  }

  function closeOffer(reason, track = true) {
    const offer = document.getElementById("lm-finance-secondary");
    if (!offer) return;
    offer.remove();
    if (track) emit("affiliate_finance_close", { trigger: reason });
    if (previousFocus && typeof previousFocus.focus === "function") {
      previousFocus.focus({ preventScroll: true });
    }
    previousFocus = null;
  }

  function showOffer(trigger) {
    if (!eligible() || depthRatio() < MIN_SCROLL_RATIO) return;
    stopTriggers();
    sessionSet(SESSION_KEY, "shown");
    localSet(LAST_SHOWN_KEY, String(Date.now()));
    addStyle();
    previousFocus = document.activeElement;

    const offer = document.createElement("aside");
    offer.id = "lm-finance-secondary";
    offer.className = "lm-finance-secondary";
    offer.setAttribute("role", "complementary");
    offer.setAttribute("aria-label", "Ưu đãi tài chính tài trợ");
    offer.innerHTML = `
      <button class="lm-finance-secondary-x" type="button" aria-label="Đóng">×</button>
      <div class="lm-finance-secondary-head">
        <span class="lm-finance-secondary-badge">Tài trợ · VPBank</span>
        <h2>Vay tiền mặt online</h2>
        <p>Đăng ký online, xét duyệt theo hồ sơ.</p>
      </div>
      <div class="lm-finance-secondary-body">
        <div class="lm-finance-secondary-rate"><strong>1,2%</strong><span>lãi suất từ / tháng</span></div>
        <div class="lm-finance-secondary-actions">
          <a class="lm-finance-secondary-cta" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">XEM ĐIỀU KIỆN VPBANK →</a>
          <button class="lm-finance-secondary-close" type="button">Đóng</button>
        </div>
        <span class="lm-finance-secondary-note">Liên kết tài trợ qua ACCESSTRADE. Điều kiện thực tế theo VPBank.</span>
      </div>`;

    offer.querySelector(".lm-finance-secondary-x")?.addEventListener("click", () => closeOffer("top_close"));
    offer.querySelector(".lm-finance-secondary-close")?.addEventListener("click", () => closeOffer("close"));
    offer.querySelector(".lm-finance-secondary-cta")?.addEventListener("click", () => {
      emit("affiliate_finance_click", { trigger });
      sessionSet(AFFILIATE_INTENT_KEY, "1");
    });
    document.body.appendChild(offer);
    emit("affiliate_finance_view", { trigger, scroll_ratio: Number(depthRatio().toFixed(2)) });
  }

  function installOffer() {
    document.addEventListener("click", markPrimaryIntent, true);
    if (!eligible()) return;
    const started = Date.now();
    let delayPassed = false;

    const maybeShow = trigger => {
      if (!delayPassed || !eligible() || depthRatio() < MIN_SCROLL_RATIO) return;
      showOffer(trigger);
    };

    timer = window.setTimeout(() => {
      delayPassed = true;
      maybeShow("deep_engagement_60s");
    }, MIN_DELAY_MS);

    scrollHandler = () => {
      if (Date.now() - started < MIN_DELAY_MS) return;
      delayPassed = true;
      maybeShow("deep_scroll_72");
    };
    window.addEventListener("scroll", scrollHandler, { passive: true });
  }

  document.addEventListener("DOMContentLoaded", installOffer, { once: true });
})();
