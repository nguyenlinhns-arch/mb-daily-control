(() => {
  "use strict";

  const OFFER = {
    id: "vpbank-vay-online",
    merchant: "VPBank",
    url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
  };
  const RETURN_INTERSTITIAL_KEY = "lm_finance_return_interstitial_v1";
  const SHOPEE_NUDGE_SESSION_KEY = "lm_shopee_nudge_v1";
  const MIN_ENGAGED_MS = 15000;
  const MIN_SCROLL_RATIO = 0.25;
  const MIN_HIDDEN_MS = 2000;

  let engaged = false;
  let visibleAccumulatedMs = 0;
  let visibleSince = document.visibilityState === "visible" ? Date.now() : 0;
  let engagementTimer = 0;
  let hiddenAt = 0;
  let returnTimer = 0;
  let previousFocus = null;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: OFFER.id,
      merchant: OFFER.merchant,
      placement: "home_upper_after_header",
      ...extra
    });
  }

  function sessionGet(key) {
    try {
      return sessionStorage.getItem(key);
    } catch (_) {
      return null;
    }
  }

  function sessionSet(key, value) {
    try {
      sessionStorage.setItem(key, value);
    } catch (_) {
      // Session storage can be unavailable in strict privacy modes.
    }
  }

  function returnInterstitialConsumed() {
    return sessionGet(RETURN_INTERSTITIAL_KEY) === "shown";
  }

  function shopeePromptConsumed() {
    return sessionGet(SHOPEE_NUDGE_SESSION_KEY) === "shown";
  }

  function markReturnInterstitialConsumed() {
    sessionSet(RETURN_INTERSTITIAL_KEY, "shown");
  }

  function suppressShopeePrompt() {
    sessionSet(SHOPEE_NUDGE_SESSION_KEY, "shown");
    const nudge = document.getElementById("lm-shopee-nudge");
    if (nudge) nudge.remove();
  }

  function checkoutIsOpen() {
    const checkout = document.getElementById("checkout");
    return Boolean(checkout && checkout.hidden === false);
  }

  function trackView(section) {
    if (!("IntersectionObserver" in window)) return;
    let sent = false;
    const observer = new IntersectionObserver((entries) => {
      if (sent || !entries.some((entry) => entry.isIntersecting && entry.intersectionRatio >= 0.5)) return;
      sent = true;
      emit("affiliate_finance_view");
      observer.disconnect();
    }, { threshold: [0.5] });
    observer.observe(section);
  }

  function markEngaged(reason) {
    if (engaged) return;
    engaged = true;
    if (engagementTimer) {
      window.clearTimeout(engagementTimer);
      engagementTimer = 0;
    }
    emit("affiliate_return_interstitial_eligible", { placement: "return_interstitial", trigger: reason });
  }

  function scheduleEngagementTimer() {
    if (engaged || document.visibilityState !== "visible") return;
    if (engagementTimer) window.clearTimeout(engagementTimer);
    const remaining = Math.max(0, MIN_ENGAGED_MS - visibleAccumulatedMs);
    if (remaining === 0) {
      markEngaged("visible_15s");
      return;
    }
    visibleSince = Date.now();
    engagementTimer = window.setTimeout(() => {
      visibleAccumulatedMs += Math.max(0, Date.now() - visibleSince);
      visibleSince = Date.now();
      markEngaged("visible_15s");
    }, remaining);
  }

  function updateEngagementByScroll() {
    if (engaged) return;
    const height = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
    const depth = height > 0 ? (window.scrollY + window.innerHeight) / height : 0;
    if (depth >= MIN_SCROLL_RATIO) markEngaged("scroll_25");
  }

  function addInterstitialStyle() {
    if (document.getElementById("lm-finance-return-style")) return;
    const style = document.createElement("style");
    style.id = "lm-finance-return-style";
    style.textContent = `
      body.lm-finance-return-open{overflow:hidden}
      .lm-finance-return{position:fixed;inset:0;z-index:140;display:grid;place-items:center;padding:18px;background:rgba(7,27,43,.66);backdrop-filter:blur(4px)}
      .lm-finance-return-card{position:relative;width:min(100%,430px);overflow:hidden;border:1px solid rgba(255,255,255,.22);border-radius:22px;background:#fff;box-shadow:0 24px 70px rgba(0,0,0,.28)}
      .lm-finance-return-head{padding:22px 20px 18px;background:linear-gradient(135deg,#123f32,#0b2f28);color:#fff}
      .lm-finance-return-label{display:block;padding-right:74px;color:#c7ded5;font-size:9px;font-weight:900;letter-spacing:.07em;text-transform:uppercase}
      .lm-finance-return-head strong{display:block;margin-top:6px;font-size:24px;line-height:1.18;color:#fff}.lm-finance-return-rate{display:block;margin-top:8px;color:#fff;font-size:14px;font-weight:900;line-height:1.45}
      .lm-finance-return-body{padding:16px 20px 20px}.lm-finance-return-body p{margin:0 0 12px;color:#61727b;font-size:11px;line-height:1.55}
      .lm-finance-return-cta{min-height:52px;display:flex;align-items:center;justify-content:center;border-radius:13px;background:#123f32;color:#fff!important;text-decoration:none!important;font-size:14px;font-weight:900}
      .lm-finance-return-close{position:absolute;top:12px;right:12px;z-index:2;min-width:58px;height:34px;padding:0 10px;border:1px solid rgba(255,255,255,.35);border-radius:999px;background:rgba(255,255,255,.14);color:#fff;font-size:11px;font-weight:800;cursor:pointer}
      @media(max-width:700px){.lm-finance-return{padding:14px}.lm-finance-return-card{border-radius:18px}.lm-finance-return-head{padding:20px 17px 16px}.lm-finance-return-head strong{font-size:21px}.lm-finance-return-rate{font-size:13px}.lm-finance-return-body{padding:14px 17px 17px}.lm-finance-return-cta{min-height:50px;font-size:13px}}
      @media(prefers-reduced-motion:reduce){.lm-finance-return{backdrop-filter:none}}
    `;
    document.head.appendChild(style);
  }

  function closeReturnInterstitial(reason, trackClose = true) {
    const overlay = document.getElementById("lm-finance-return");
    if (!overlay) return;
    overlay.remove();
    document.body.classList.remove("lm-finance-return-open");
    document.removeEventListener("keydown", onInterstitialKeydown);
    if (trackClose) emit("affiliate_finance_interstitial_close", { placement: "return_interstitial", trigger: reason });
    if (previousFocus && typeof previousFocus.focus === "function") previousFocus.focus({ preventScroll: true });
    previousFocus = null;
  }

  function onInterstitialKeydown(event) {
    if (event.key === "Escape") closeReturnInterstitial("escape");
  }

  function showReturnInterstitial(trigger) {
    if (
      window.location.pathname !== "/" ||
      document.visibilityState !== "visible" ||
      !engaged ||
      returnInterstitialConsumed() ||
      shopeePromptConsumed() ||
      checkoutIsOpen() ||
      document.getElementById("lm-finance-return")
    ) return;

    markReturnInterstitialConsumed();
    suppressShopeePrompt();
    addInterstitialStyle();
    previousFocus = document.activeElement;

    const overlay = document.createElement("div");
    overlay.id = "lm-finance-return";
    overlay.className = "lm-finance-return";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "lm-finance-return-title");
    overlay.innerHTML = `
      <div class="lm-finance-return-card">
        <button class="lm-finance-return-close" type="button" aria-label="Đóng quảng cáo">Đóng</button>
        <div class="lm-finance-return-head">
          <span class="lm-finance-return-label">Liên kết tài trợ · ACCESSTRADE</span>
          <strong id="lm-finance-return-title">Vay online VPBank</strong>
          <span class="lm-finance-return-rate">Từ 1,2%/tháng · Đăng ký ban đầu chỉ cần Căn cước công dân</span>
        </div>
        <div class="lm-finance-return-body">
          <p>Thông tin chi tiết và điều kiện được hiển thị trên trang đăng ký của VPBank.</p>
          <a class="lm-finance-return-cta" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">Vay tiền nhanh online →</a>
        </div>
      </div>`;

    overlay.querySelector(".lm-finance-return-close")?.addEventListener("click", () => closeReturnInterstitial("close_button"));
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) closeReturnInterstitial("backdrop");
    });
    overlay.querySelector(".lm-finance-return-cta")?.addEventListener("click", () => {
      emit("affiliate_finance_click", { placement: "return_interstitial", trigger });
      window.setTimeout(() => closeReturnInterstitial("cta_click", false), 0);
    });

    document.body.appendChild(overlay);
    document.body.classList.add("lm-finance-return-open");
    document.addEventListener("keydown", onInterstitialKeydown);
    overlay.querySelector(".lm-finance-return-close")?.focus({ preventScroll: true });
    emit("affiliate_finance_interstitial_view", { placement: "return_interstitial", trigger });
  }

  function setupReturnInterstitial() {
    if (window.location.pathname !== "/" || returnInterstitialConsumed() || shopeePromptConsumed()) return;

    scheduleEngagementTimer();
    window.addEventListener("scroll", updateEngagementByScroll, { passive: true });
    updateEngagementByScroll();

    document.addEventListener("visibilitychange", () => {
      const now = Date.now();
      if (document.visibilityState === "hidden") {
        if (visibleSince) visibleAccumulatedMs += Math.max(0, now - visibleSince);
        visibleSince = 0;
        if (engagementTimer) {
          window.clearTimeout(engagementTimer);
          engagementTimer = 0;
        }
        hiddenAt = now;
        return;
      }

      visibleSince = now;
      scheduleEngagementTimer();
      const awayMs = hiddenAt ? now - hiddenAt : 0;
      hiddenAt = 0;
      if (awayMs < MIN_HIDDEN_MS || !engaged) return;
      if (returnTimer) window.clearTimeout(returnTimer);
      returnTimer = window.setTimeout(() => showReturnInterstitial("tab_return"), 450);
    });
  }

  function mountTopBanner() {
    if (window.location.pathname !== "/" || document.getElementById("lm-finance-top")) return;

    const style = document.createElement("style");
    style.id = "lm-finance-top-style";
    style.textContent = `
      .lm-finance-top{width:100%;padding:7px 0;background:#f4f7f6;border-bottom:1px solid #dfe7e3}
      .lm-finance-top-inner{width:min(calc(100% - 28px),1180px);margin:auto}
      .lm-finance-top-card{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center;padding:12px 15px;border-radius:14px;background:linear-gradient(135deg,#123f32,#0b2f28);color:#fff;text-decoration:none!important;box-shadow:0 5px 16px rgba(15,50,40,.16)}
      .lm-finance-top-label{display:block;margin-bottom:3px;color:#c7ded5;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
      .lm-finance-top-copy strong{display:block;font-size:16px;line-height:1.25;color:#fff}.lm-finance-top-rate{display:block;margin-top:4px;color:#fff;font-size:13px;font-weight:900}
      .lm-finance-top-cta{min-height:42px;padding:0 14px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#fff;color:#143f32!important;font-size:12px;font-weight:900;white-space:nowrap}
      @media(max-width:700px){.lm-finance-top{padding:5px 0}.lm-finance-top-inner{width:calc(100% - 20px)}.lm-finance-top-card{grid-template-columns:1fr;padding:10px 11px;gap:7px}.lm-finance-top-copy strong{font-size:15px}.lm-finance-top-rate{font-size:12.5px}.lm-finance-top-cta{min-height:42px;width:100%}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.id = "lm-finance-top";
    section.className = "lm-finance-top";
    section.setAttribute("aria-label", "Liên kết tài trợ vay online VPBank qua ACCESSTRADE");
    section.innerHTML = `
      <div class="lm-finance-top-inner">
        <a class="lm-finance-top-card" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">
          <div class="lm-finance-top-copy">
            <span class="lm-finance-top-label">Liên kết tài trợ · ACCESSTRADE</span>
            <strong>Vay online VPBank</strong>
            <span class="lm-finance-top-rate">Từ 1,2%/tháng · Đăng ký ban đầu chỉ cần Căn cước công dân</span>
          </div>
          <span class="lm-finance-top-cta">Vay tiền nhanh online →</span>
        </a>
      </div>`;

    section.querySelector("a")?.addEventListener("click", () => {
      markReturnInterstitialConsumed();
      emit("affiliate_finance_click");
    });

    const anchor = document.querySelector(".portal-topline") || document.querySelector(".portal-header") || document.querySelector("header");
    if (anchor) anchor.insertAdjacentElement("afterend", section);
    else document.body.prepend(section);

    trackView(section);
  }

  document.addEventListener("DOMContentLoaded", () => {
    mountTopBanner();
    setupReturnInterstitial();
  }, { once: true });
})();