(() => {
  "use strict";

  // Legacy guard markers kept inert for the maintenance hand-off only:
  // affiliate_product_grid_view · after_proof

  const AI_INTENT_KEY = "lm_ai_purchase_intent_v1";
  let checkoutOpened = false;
  let qrViewed = false;
  let claimSubmitted = false;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event, page_path: window.location.pathname, ...extra });
  }

  function sessionSet(key, value) {
    try { sessionStorage.setItem(key, value); } catch (_) {}
  }

  function reportDateLabel() {
    const bodyDate = String(document.body?.dataset?.reportDate || "").trim();
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(bodyDate)) return bodyDate;
    const text = document.body?.textContent || "";
    const target = text.match(/BẢN\s+PHÂN\s+TÍCH\s+AI\s+NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i);
    if (target) return target[1];
    return new Intl.DateTimeFormat("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
      day: "2-digit",
      month: "2-digit",
      year: "numeric"
    }).format(new Date());
  }

  function addRuntimeStyle() {
    if (document.getElementById("lm-commerce-runtime-style")) return;
    const style = document.createElement("style");
    style.id = "lm-commerce-runtime-style";
    style.textContent = `
      .lm-ai-runtime-kicker{display:block;margin-top:7px;color:#79575a;font-size:10px;font-weight:850;line-height:1.4}
      .lm-shopee-nudge{display:none!important}
      .conversion-benefits li{display:flex!important;align-items:flex-start!important;gap:8px!important;text-align:left!important}
      .conversion-benefits li::before{content:"✓"!important;display:grid!important;place-items:center!important;flex:0 0 18px!important;width:18px!important;height:18px!important;margin:1px 0 0!important;border:1px solid #e9c5c9!important;border-radius:999px!important;background:#fff1f2!important;color:#b4232f!important;font-size:11px!important;font-weight:1000!important;line-height:1!important}
      .buy-value-list strong{position:relative;padding-left:24px!important}
      @media(max-width:700px){
        .conversion-benefits{grid-template-columns:1fr!important;gap:7px!important}.conversion-benefits li{min-height:0!important;padding:10px 12px!important;border:1px solid #ece5e5!important;border-radius:11px!important;background:#faf8f7!important;font-size:12px!important;line-height:1.35!important}
        .portal-home .portal-hero{padding:20px 0!important}.portal-home .portal-hero-grid{gap:14px!important}.portal-home h1{font-size:32px!important;line-height:1.08!important}.portal-home .portal-lead{margin-top:10px!important;font-size:14px!important;line-height:1.55!important}
        .portal-home .portal-paid-card{padding:14px!important;border-radius:16px!important}.portal-home .portal-paid-card h2{margin-bottom:10px!important;font-size:19px!important;line-height:1.2!important}.portal-home .portal-paid-card button{min-height:48px!important;font-size:12px!important}.portal-home .portal-paid-note{margin-top:8px!important;font-size:10px!important}
        .portal-home .portal-section{padding:16px 0!important}.portal-home .portal-section-title{margin-bottom:10px!important}.portal-home .portal-section-title h2{font-size:20px!important}.portal-home .portal-section-title p{font-size:11.5px!important}
      }
      @media(max-width:390px){.portal-home h1{font-size:29px!important}.portal-home .portal-wrap{padding-left:10px!important;padding-right:10px!important}}
    `;
    document.head.appendChild(style);
  }

  function polishHomeCopy() {
    if (window.location.pathname !== "/") return;
    const date = reportDateLabel();
    const heroTitle = document.querySelector(".portal-hero h1");
    if (heroTitle) heroTitle.textContent = "Thống kê XSMB & phân tích AI";

    const heroLead = document.querySelector(".portal-hero .portal-lead");
    if (heroLead) {
      heroLead.innerHTML = `Phân tích, thống kê và soi cầu XSMB qua nhiều phương pháp. Gợi ý số cho ngày hôm nay <strong>${date}</strong> chỉ với 30.000đ.`;
    }

    const paidCard = document.querySelector(".portal-paid-card");
    if (!paidCard) return;
    const title = paidCard.querySelector("h2");
    if (title) title.textContent = `Bản phân tích AI ngày ${date}`;
    const button = paidCard.querySelector("[data-open-checkout]");
    if (button) {
      button.textContent = "MỞ BẢN PHÂN TÍCH AI · 30.000Đ";
      button.setAttribute("aria-label", `Mở bản phân tích AI ngày ${date}, giá 30.000 đồng`);
    }
    if (!paidCard.querySelector(".lm-ai-runtime-kicker")) {
      const kicker = document.createElement("span");
      kicker.className = "lm-ai-runtime-kicker";
      kicker.textContent = "Thanh toán một lần · Không tự gia hạn · Phân tích thống kê không cam kết kết quả";
      button?.insertAdjacentElement("afterend", kicker);
    }
  }

  function paymentQrVisible() {
    return Boolean(document.querySelector(".vietqr-panel img, .vietqr-panel, img[src*='vietqr.io']"));
  }

  function checkoutVisible() {
    const checkout = document.getElementById("checkout");
    return Boolean(checkout && checkout.hidden === false);
  }

  function markQrView() {
    if (qrViewed || !checkoutVisible() || !paymentQrVisible()) return;
    qrViewed = true;
    emit("ai_payment_qr_view", { product: "daily_ai_analysis", price_vnd: 30000 });
  }

  function installAiFunnelTracking() {
    document.addEventListener("click", event => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;
      const checkoutButton = target.closest("[data-open-checkout], [data-ai-sticky-cta]");
      if (checkoutButton) {
        sessionSet(AI_INTENT_KEY, "1");
        emit("ai_checkout_intent", {
          product: "daily_ai_analysis",
          price_vnd: 30000,
          placement: checkoutButton.closest(".portal-paid-card") ? "hero" : checkoutButton.hasAttribute("data-ai-sticky-cta") ? "sticky" : "purchase"
        });
        window.setTimeout(() => {
          if (!checkoutOpened && checkoutVisible()) {
            checkoutOpened = true;
            emit("ai_checkout_open", { product: "daily_ai_analysis", price_vnd: 30000 });
          }
          markQrView();
        }, 0);
      }

      const claim = target.closest("button, a");
      if (claim && !claimSubmitted && /đã\s+chuyển\s+khoản|xác\s+nhận\s+thanh\s+toán|yêu\s+cầu\s+nhận/i.test(claim.textContent || "")) {
        claimSubmitted = true;
        sessionSet(AI_INTENT_KEY, "1");
        emit("ai_payment_claim_submit", { product: "daily_ai_analysis", price_vnd: 30000 });
      }
    }, true);

    if (document.body && "MutationObserver" in window) {
      new MutationObserver(() => {
        if (!checkoutOpened && checkoutVisible()) {
          checkoutOpened = true;
          emit("ai_checkout_open", { product: "daily_ai_analysis", price_vnd: 30000, source: "mutation" });
        }
        markQrView();
      }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden"] });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    addRuntimeStyle();
    polishHomeCopy();
    installAiFunnelTracking();
  }, { once: true });
})();
