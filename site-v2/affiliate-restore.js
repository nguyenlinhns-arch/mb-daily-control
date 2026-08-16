(() => {
  "use strict";

  const SHOPEE_URL = "https://nguyenlinhtkv_aul4jx.accesslanding.site";
  const RESTORE_STYLE_ID = "lm-affiliate-restore-style";

  function checkoutIsOpen() {
    const checkout = document.getElementById("checkout");
    return Boolean(checkout && checkout.hidden === false);
  }

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: window.location.pathname,
      affiliate_network: "ACCESSTRADE",
      ...extra
    });
  }

  function addRestoreStyle() {
    if (document.getElementById(RESTORE_STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = RESTORE_STYLE_ID;
    style.textContent = `
      body:not([data-affiliate-checkout-open="true"]) .lm-affiliate-section,
      body:not([data-affiliate-checkout-open="true"]) .lm-product-deals,
      body:not([data-affiliate-checkout-open="true"]) [data-primary-affiliate-strip]{display:block!important;visibility:visible!important;opacity:1!important}
      body[data-affiliate-checkout-open="true"] .lm-affiliate-section,
      body[data-affiliate-checkout-open="true"] .lm-product-deals,
      body[data-affiliate-checkout-open="true"] [data-primary-affiliate-strip]{display:none!important}
      .lm-affiliate-section,.lm-product-deals,[data-primary-affiliate-strip]{content-visibility:auto}
    `;
    document.head.appendChild(style);
  }

  function resultsAnchor() {
    const card = document.querySelector(".portal-result-card");
    if (card) return card.closest("section") || card;
    return [...document.querySelectorAll("section")].find(section => /27 mã kỳ gần nhất|kết quả xsmb/i.test(section.textContent || "")) || null;
  }

  function ensureEarlyStrip() {
    if (location.pathname !== "/" || checkoutIsOpen()) return;
    if (document.querySelector("[data-primary-affiliate-strip]")) return;
    const anchor = resultsAnchor();
    if (!anchor) return;

    const section = document.createElement("section");
    section.className = "lm-primary-affiliate-strip";
    section.dataset.primaryAffiliateStrip = "restore-v1";
    section.setAttribute("aria-label", "Ưu đãi mua sắm tài trợ ACCESSTRADE");
    section.innerHTML = `
      <div class="lm-primary-affiliate-inner">
        <a class="lm-primary-affiliate-card" href="${SHOPEE_URL}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-primary-shopee-link data-affiliate-restore-link>
          <div><span class="lm-primary-affiliate-badge">Tài trợ · ACCESSTRADE</span><strong>Shopee · xem ưu đãi mua sắm hôm nay</strong><small>Mở Shopee để xem sản phẩm và ưu đãi đang có. Giá mua không tăng vì liên kết này.</small></div>
          <span class="lm-primary-affiliate-cta">XEM ƯU ĐÃI →</span>
        </a>
        <p class="lm-primary-affiliate-note">Website có thể nhận hoa hồng khi phát sinh giao dịch đủ điều kiện.</p>
      </div>`;
    anchor.insertAdjacentElement("afterend", section);
    section.querySelector("[data-affiliate-restore-link]")?.addEventListener("click", () => {
      try { sessionStorage.setItem("lm_affiliate_intent_v1", "1"); } catch (_) {}
      emit("affiliate_shopee_strip_click", { merchant: "Shopee", placement: "after_results_restore" });
    });
    emit("affiliate_shopee_strip_view", { merchant: "Shopee", placement: "after_results_restore" });
  }

  function syncVisibility() {
    if (!document.body) return;
    const open = checkoutIsOpen();
    if (open) document.body.dataset.affiliateCheckoutOpen = "true";
    else delete document.body.dataset.affiliateCheckoutOpen;

    if (!open) {
      for (const node of document.querySelectorAll(".lm-affiliate-section,.lm-product-deals,[data-primary-affiliate-strip]")) {
        node.removeAttribute("hidden");
        if (node instanceof HTMLElement) {
          node.style.removeProperty("display");
          node.style.removeProperty("visibility");
          node.style.removeProperty("opacity");
        }
      }
      ensureEarlyStrip();
    }
  }

  function boot() {
    if (location.pathname !== "/") return;
    addRestoreStyle();
    syncVisibility();
    const observer = new MutationObserver(syncVisibility);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "data-returning-ai-buyer"] });
    for (const delay of [100, 500, 1500, 4000, 9000]) window.setTimeout(syncVisibility, delay);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
