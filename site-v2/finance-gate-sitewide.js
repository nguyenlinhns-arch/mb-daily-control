(() => {
  "use strict";

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
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: location.pathname,
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: OFFER.id,
      merchant: OFFER.merchant,
      placement: "early_finance_banner_sitewide_v3",
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
