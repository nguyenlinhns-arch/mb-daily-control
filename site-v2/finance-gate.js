(() => {
  "use strict";

  const OFFER = {
    id: "vpbank-vay-online",
    merchant: "VPBank",
    url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
  };

  const SESSION_KEY = "lm_finance_early_banner_v1";
  const AI_INTENT_KEY = "lm_ai_purchase_intent_v1";
  const AFFILIATE_INTENT_KEY = "lm_affiliate_intent_v1";
  const LAST_SHOWN_KEY = "lm_finance_last_shown_v2";
  const MIN_DELAY_MS = 8000;
  const MIN_SCROLL_RATIO = 0.18;
  const COOLDOWN_MS = 24 * 60 * 60 * 1000;
  let timer = 0;
  let scrollHandler = null;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: window.location.pathname,
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: OFFER.id,
      merchant: OFFER.merchant,
      placement: "early_finance_banner",
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
      clearTimeout(timer);
      timer = 0;
    }
    if (scrollHandler) {
      removeEventListener("scroll", scrollHandler);
      scrollHandler = null;
    }
  }

  function eligible() {
    return location.pathname === "/"
      && document.visibilityState === "visible"
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
      .lm-finance-secondary{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:76;width:min(820px,calc(100vw - 28px));border:1px solid rgba(255,255,255,.28);border-radius:20px;background:linear-gradient(120deg,#2b0b63 0%,#5a167c 45%,#e76e22 100%);box-shadow:0 18px 46px rgba(28,13,55,.28);overflow:hidden;color:#fff;animation:lmFinanceIn .2s ease-out both}
      .lm-finance-secondary-inner{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:center;padding:16px 18px 14px}.lm-finance-secondary-copy{min-width:0}.lm-finance-secondary-badge{display:inline-flex;padding:4px 7px;border-radius:999px;background:rgba(255,255,255,.16);color:#ffe6a8;font-size:8.5px;font-weight:1000;letter-spacing:.08em;text-transform:uppercase}.lm-finance-secondary h2{margin:6px 0 0;color:#fff;font-size:24px;line-height:1.08}.lm-finance-secondary p{margin:5px 0 0;color:rgba(255,255,255,.86);font-size:11.5px;line-height:1.4}.lm-finance-secondary-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}.lm-finance-secondary-meta span{display:inline-flex;align-items:center;min-height:26px;padding:0 8px;border:1px solid rgba(255,255,255,.2);border-radius:999px;background:rgba(255,255,255,.08);color:#fff;font-size:9px;font-weight:850}.lm-finance-secondary-cta{min-width:170px;min-height:48px;display:flex;align-items:center;justify-content:center;padding:0 18px;border-radius:14px;background:linear-gradient(135deg,#ff7a22,#ffb11a);color:#fff!important;text-decoration:none!important;font-size:12px;font-weight:1000;box-shadow:0 9px 24px rgba(96,31,0,.22)}.lm-finance-secondary-x{position:absolute;top:8px;right:8px;width:28px;height:28px;border:1px solid rgba(255,255,255,.25);border-radius:50%;background:rgba(255,255,255,.16);color:#fff;font-size:18px;line-height:1;cursor:pointer}.lm-finance-secondary-note{display:block;padding:0 18px 10px;color:rgba(255,255,255,.66);font-size:8px;line-height:1.35}
      @keyframes lmFinanceIn{from{opacity:0;transform:translate(-50%,10px)}to{opacity:1;transform:translate(-50%,0)}}
      @media(max-width:700px){.lm-finance-secondary{left:10px;right:10px;bottom:calc(66px + env(safe-area-inset-bottom,0px));width:auto;transform:none;border-radius:17px}.lm-finance-secondary-inner{grid-template-columns:1fr;padding:13px 13px 11px;gap:10px}.lm-finance-secondary h2{padding-right:32px;font-size:20px}.lm-finance-secondary p{font-size:10.5px}.lm-finance-secondary-meta{gap:5px;margin-top:7px}.lm-finance-secondary-meta span{font-size:8.5px;min-height:24px}.lm-finance-secondary-cta{width:100%;min-width:0;min-height:46px}.lm-finance-secondary-note{padding:0 13px 9px}.lm-finance-secondary-x{top:7px;right:7px;width:26px;height:26px}@keyframes lmFinanceIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}}
      @media(prefers-reduced-motion:reduce){.lm-finance-secondary{animation:none}}
    `;
    document.head.appendChild(style);
  }

  function closeOffer(reason, track = true) {
    const offer = document.getElementById("lm-finance-secondary");
    if (!offer) return;
    offer.remove();
    if (track) emit("affiliate_finance_close", { trigger: reason });
  }

  function showOffer(trigger) {
    if (!eligible()) return;
    stopTriggers();
    sessionSet(SESSION_KEY, "shown");
    localSet(LAST_SHOWN_KEY, String(Date.now()));
    addStyle();

    const offer = document.createElement("aside");
    offer.id = "lm-finance-secondary";
    offer.className = "lm-finance-secondary";
    offer.setAttribute("role", "complementary");
    offer.setAttribute("aria-label", "Ưu đãi vay tiền online tài trợ");
    offer.innerHTML = `
      <button class="lm-finance-secondary-x" type="button" aria-label="Đóng quảng cáo">×</button>
      <div class="lm-finance-secondary-inner">
        <div class="lm-finance-secondary-copy">
          <span class="lm-finance-secondary-badge">Tài trợ · ACCESSTRADE · VPBank</span>
          <h2>Vay tiền online</h2>
          <p>Xem ưu đãi, điều kiện và đăng ký online theo chính sách của VPBank.</p>
          <div class="lm-finance-secondary-meta"><span>Đăng ký online</span><span>Xem điều kiện</span><span>VPBank xét duyệt</span></div>
        </div>
        <a class="lm-finance-secondary-cta" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">XEM NGAY →</a>
      </div>
      <span class="lm-finance-secondary-note">Liên kết tài trợ qua ACCESSTRADE. Điều kiện và quyết định thực tế do VPBank áp dụng.</span>`;

    offer.querySelector(".lm-finance-secondary-x")?.addEventListener("click", () => closeOffer("top_close"));
    offer.querySelector(".lm-finance-secondary-cta")?.addEventListener("click", () => {
      emit("affiliate_finance_click", { trigger });
      sessionSet(AFFILIATE_INTENT_KEY, "1");
    });
    document.body.appendChild(offer);
    emit("affiliate_finance_view", { trigger, scroll_ratio: Number(depthRatio().toFixed(2)) });
  }

  function installSuppression() {
    document.addEventListener("click", event => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;
      if (target.closest("[data-open-checkout], [data-ai-sticky-cta]")) {
        sessionSet(AI_INTENT_KEY, "1");
        closeOffer("ai_intent", false);
      }
    }, true);
    if (document.body && "MutationObserver" in window) {
      new MutationObserver(() => {
        if (checkoutIsOpen()) closeOffer("checkout_open", false);
      }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden"] });
    }
  }

  function installOffer() {
    installSuppression();
    if (!eligible()) return;
    const started = Date.now();

    timer = setTimeout(() => {
      if (eligible()) showOffer("early_8s");
    }, MIN_DELAY_MS);

    scrollHandler = () => {
      if (!eligible()) return;
      if (depthRatio() >= MIN_SCROLL_RATIO || Date.now() - started >= MIN_DELAY_MS) showOffer("early_scroll_18");
    };
    addEventListener("scroll", scrollHandler, { passive: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", installOffer, { once: true });
  else installOffer();
})();