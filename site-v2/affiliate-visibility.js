(() => {
  "use strict";

  const SHOPEE = {
    id: "shopee-smartlink-primary",
    merchant: "Shopee",
    url: "https://nguyenlinhtkv_aul4jx.accesslanding.site"
  };
  const AI_INTENT_KEY = "lm_ai_purchase_intent_v1";
  const AFFILIATE_INTENT_KEY = "lm_affiliate_intent_v1";
  const PURCHASE_PREFIX = "lemienbac_purchase_";
  let viewed = false;
  let observer = null;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: window.location.pathname,
      affiliate_network: "ACCESSTRADE",
      merchant: SHOPEE.merchant,
      placement: "after_tools_visible",
      ...extra
    });
  }

  function sessionGet(key) {
    try { return sessionStorage.getItem(key); } catch (_) { return null; }
  }

  function sessionSet(key, value) {
    try { sessionStorage.setItem(key, value); } catch (_) {}
  }

  function hasPurchaseMarker() {
    try {
      for (let index = 0; index < localStorage.length; index += 1) {
        const key = localStorage.key(index) || "";
        if (key.startsWith(PURCHASE_PREFIX)) return true;
      }
    } catch (_) {}
    return false;
  }

  function checkoutIsOpen() {
    const checkout = document.getElementById("checkout");
    return Boolean(checkout && checkout.hidden === false);
  }

  function shouldSuppress() {
    return hasPurchaseMarker()
      || document.body?.dataset?.returningAiBuyer === "true"
      || sessionGet(AI_INTENT_KEY) === "1"
      || checkoutIsOpen();
  }

  function toolsAnchor() {
    return [...document.querySelectorAll("section")].find((section) => /Công cụ thống kê XSMB/i.test(section.textContent || ""))
      || document.querySelector(".portal-tools")?.closest("section")
      || null;
  }

  function removeStrip(reason = "suppressed") {
    const strip = document.querySelector("[data-primary-affiliate-strip]");
    if (!strip) return;
    strip.remove();
    if (observer) {
      observer.disconnect();
      observer = null;
    }
    if (viewed) emit("affiliate_shopee_strip_hide", { reason });
  }

  function installStyle() {
    if (document.getElementById("lm-primary-affiliate-style")) return;
    const style = document.createElement("style");
    style.id = "lm-primary-affiliate-style";
    style.textContent = `
      .lm-primary-affiliate-strip{width:100%;padding:8px 0}.lm-primary-affiliate-inner{max-width:1180px;margin:auto;padding:0 16px}
      .lm-primary-affiliate-card{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:13px 14px;border:1px solid #f0d7cc;border-radius:14px;background:linear-gradient(135deg,#fff8f4,#fff);color:#263744!important;text-decoration:none!important;box-shadow:0 3px 14px rgba(39,29,24,.05)}
      .lm-primary-affiliate-badge{display:inline-flex;margin-bottom:3px;padding:3px 6px;border-radius:999px;background:#fff0e8;color:#b84b16;font-size:8px;font-weight:1000;letter-spacing:.07em;text-transform:uppercase}.lm-primary-affiliate-card strong{display:block;font-size:14px;line-height:1.25}.lm-primary-affiliate-card small{display:block;margin-top:3px;color:#71808a;font-size:10.5px;line-height:1.4}.lm-primary-affiliate-cta{display:flex;align-items:center;justify-content:center;min-height:42px;padding:0 13px;border-radius:10px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:1000;white-space:nowrap}.lm-primary-affiliate-note{margin:5px 2px 0;color:#929ba1;font-size:8.5px;line-height:1.35}
      @media(max-width:700px){.lm-primary-affiliate-strip{padding:6px 0}.lm-primary-affiliate-inner{padding:0 10px}.lm-primary-affiliate-card{grid-template-columns:1fr;gap:8px;padding:11px 12px}.lm-primary-affiliate-card strong{font-size:13px}.lm-primary-affiliate-card small{font-size:10px}.lm-primary-affiliate-cta{width:100%;min-height:44px}}
    `;
    document.head.appendChild(style);
  }

  function trackView(strip) {
    const fire = () => {
      if (viewed || !strip.isConnected || shouldSuppress()) return;
      viewed = true;
      emit("affiliate_shopee_strip_view", { affiliate_offer_id: SHOPEE.id });
    };
    if (!("IntersectionObserver" in window)) {
      fire();
      return;
    }
    observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting && entry.intersectionRatio >= 0.5)) return;
      fire();
      observer?.disconnect();
      observer = null;
    }, { threshold: [0.5] });
    observer.observe(strip);
  }

  function installStrip() {
    if (window.location.pathname !== "/" || shouldSuppress() || document.querySelector("[data-primary-affiliate-strip]")) return;
    const anchor = toolsAnchor();
    if (!anchor) return;
    installStyle();

    const section = document.createElement("section");
    section.className = "lm-primary-affiliate-strip";
    section.dataset.primaryAffiliateStrip = "v1";
    section.setAttribute("aria-label", "Ưu đãi mua sắm tài trợ");
    section.innerHTML = `
      <div class="lm-primary-affiliate-inner">
        <a class="lm-primary-affiliate-card" href="${SHOPEE.url}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-primary-shopee-link>
          <div><span class="lm-primary-affiliate-badge">Tài trợ · ACCESSTRADE</span><strong>Shopee · xem ưu đãi mua sắm hôm nay</strong><small>Mở Shopee để xem sản phẩm và ưu đãi đang có. Không ảnh hưởng giá mua của bạn.</small></div>
          <span class="lm-primary-affiliate-cta">XEM ƯU ĐÃI →</span>
        </a>
        <p class="lm-primary-affiliate-note">Website có thể nhận hoa hồng khi phát sinh giao dịch đủ điều kiện.</p>
      </div>`;
    anchor.insertAdjacentElement("afterend", section);

    section.querySelector("[data-primary-shopee-link]")?.addEventListener("click", () => {
      sessionSet(AFFILIATE_INTENT_KEY, "1");
      emit("affiliate_shopee_strip_click", { affiliate_offer_id: SHOPEE.id });
    });
    trackView(section);
  }

  function installSuppressionWatch() {
    document.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target?.closest("[data-open-checkout], [data-ai-sticky-cta]")) return;
      sessionSet(AI_INTENT_KEY, "1");
      removeStrip("ai_intent");
    }, true);

    if (document.body && "MutationObserver" in window) {
      new MutationObserver(() => {
        if (shouldSuppress()) removeStrip("buyer_or_checkout");
      }).observe(document.body, { attributes: true, attributeFilter: ["data-returning-ai-buyer"], childList: true, subtree: true });
    }
  }

  function boot() {
    if (window.location.pathname !== "/") return;
    installSuppressionWatch();
    window.setTimeout(installStrip, 0);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
