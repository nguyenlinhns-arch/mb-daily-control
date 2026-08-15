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
      .lm-finance-return{position:fixed;inset:0;z-index:140;display:grid;place-items:center;padding:16px;background:rgba(5,20,33,.72);backdrop-filter:blur(5px)}
      .lm-finance-return-card{position:relative;width:min(100%,440px);overflow:hidden;border:1px solid rgba(255,255,255,.2);border-radius:24px;background:#fff;box-shadow:0 28px 80px rgba(0,0,0,.34)}
      .lm-finance-return-head{position:relative;padding:20px 20px 22px;background:linear-gradient(135deg,#005f4b 0%,#00886a 58%,#00a884 100%);color:#fff}
      .lm-finance-return-head:after{content:"₫";position:absolute;right:18px;bottom:-12px;width:74px;height:74px;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.12);color:rgba(255,255,255,.7);font-size:44px;font-weight:900}
      .lm-finance-return-label{display:block;padding-right:74px;color:#d8fff4;font-size:9px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}
      .lm-finance-return-title{display:block;margin-top:7px;font-size:20px;line-height:1.15;color:#fff}
      .lm-finance-return-limit{display:block;margin-top:8px;color:#fff;font-size:36px;font-weight:1000;line-height:1;letter-spacing:-.03em}.lm-finance-return-limit small{display:block;margin-bottom:4px;color:#caffef;font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}
      .lm-finance-return-body{padding:15px 18px 19px}
      .lm-finance-return-benefits{display:grid;gap:7px;margin:0 0 13px;padding:0;list-style:none}.lm-finance-return-benefits li{display:flex;align-items:center;gap:8px;min-height:34px;padding:7px 9px;border-radius:10px;background:#f4f8f6;color:#263b35;font-size:12px;font-weight:800}.lm-finance-return-benefits li:before{content:"✓";display:grid;place-items:center;flex:0 0 20px;width:20px;height:20px;border-radius:50%;background:#dff6ed;color:#00775d;font-size:12px;font-weight:1000}
      .lm-finance-return-cta{min-height:54px;display:flex;align-items:center;justify-content:center;border-radius:13px;background:linear-gradient(135deg,#ff7a00,#ff9500);color:#fff!important;text-decoration:none!important;font-size:15px;font-weight:1000;box-shadow:0 10px 22px rgba(255,122,0,.28)}
      .lm-finance-return-close{position:absolute;top:11px;right:11px;z-index:2;min-width:58px;height:34px;padding:0 10px;border:1px solid rgba(255,255,255,.4);border-radius:999px;background:rgba(0,0,0,.16);color:#fff;font-size:11px;font-weight:900;cursor:pointer}
      .lm-finance-return-sponsored{display:block;margin-top:8px;text-align:center;color:#8a9791;font-size:8px}
      @media(max-width:700px){.lm-finance-return{padding:12px}.lm-finance-return-card{border-radius:19px}.lm-finance-return-head{padding:18px 16px 20px}.lm-finance-return-title{font-size:18px}.lm-finance-return-limit{font-size:33px}.lm-finance-return-body{padding:13px 15px 16px}.lm-finance-return-benefits{gap:6px}.lm-finance-return-benefits li{font-size:11.5px}.lm-finance-return-cta{min-height:52px;font-size:14px}}
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
          <span class="lm-finance-return-label">VPBank · Vay nhanh online</span>
          <strong class="lm-finance-return-title" id="lm-finance-return-title">Cần thêm tiền cho chi tiêu?</strong>
          <span class="lm-finance-return-limit"><small>Hạn mức vay</small>ĐẾN 200 TRIỆU</span>
        </div>
        <div class="lm-finance-return-body">
          <ul class="lm-finance-return-benefits">
            <li>Không cần tài sản đảm bảo</li>
            <li>Lãi suất chỉ từ 1,2%/tháng</li>
            <li>Phê duyệt hồ sơ trong vài phút</li>
          </ul>
          <a class="lm-finance-return-cta" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">VAY TIỀN NHANH ONLINE →</a>
          <span class="lm-finance-return-sponsored">Liên kết tài trợ qua ACCESSTRADE · điều kiện thực tế theo VPBank</span>
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
      .lm-finance-top{width:100%;padding:7px 0;background:#f3f7f5;border-bottom:1px solid #dfe7e3}
      .lm-finance-top-inner{width:min(calc(100% - 28px),1180px);margin:auto}
      .lm-finance-top-card{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:13px;align-items:center;padding:11px 14px;border-radius:15px;background:linear-gradient(135deg,#00634e,#008b6b);color:#fff;text-decoration:none!important;box-shadow:0 6px 18px rgba(0,95,75,.18)}
      .lm-finance-top-money{display:grid;place-items:center;width:58px;height:58px;border-radius:14px;background:rgba(255,255,255,.13);color:#fff;font-size:12px;font-weight:900;line-height:1.05;text-align:center}.lm-finance-top-money b{display:block;font-size:18px}
      .lm-finance-top-label{display:block;margin-bottom:2px;color:#d5fff4;font-size:8.5px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.lm-finance-top-copy strong{display:block;font-size:16px;line-height:1.2;color:#fff}.lm-finance-top-rate{display:block;margin-top:4px;color:#fff;font-size:11.5px;font-weight:800}
      .lm-finance-top-cta{min-height:44px;padding:0 14px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#ff8500;color:#fff!important;font-size:12px;font-weight:1000;white-space:nowrap;box-shadow:0 7px 16px rgba(255,133,0,.26)}
      @media(max-width:700px){.lm-finance-top{padding:5px 0}.lm-finance-top-inner{width:calc(100% - 18px)}.lm-finance-top-card{grid-template-columns:50px minmax(0,1fr);padding:9px 10px;gap:9px}.lm-finance-top-money{width:50px;height:50px;border-radius:12px;font-size:10px}.lm-finance-top-money b{font-size:16px}.lm-finance-top-copy strong{font-size:14px}.lm-finance-top-rate{font-size:10.5px;line-height:1.35}.lm-finance-top-cta{grid-column:1/-1;min-height:43px;width:100%}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.id = "lm-finance-top";
    section.className = "lm-finance-top";
    section.setAttribute("aria-label", "Liên kết tài trợ vay online VPBank qua ACCESSTRADE");
    section.innerHTML = `
      <div class="lm-finance-top-inner">
        <a class="lm-finance-top-card" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">
          <span class="lm-finance-top-money">ĐẾN<b>200TR</b></span>
          <div class="lm-finance-top-copy">
            <span class="lm-finance-top-label">VPBank · Vay nhanh online</span>
            <strong>Không cần tài sản đảm bảo</strong>
            <span class="lm-finance-top-rate">Lãi từ 1,2%/tháng · Phê duyệt hồ sơ trong vài phút</span>
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