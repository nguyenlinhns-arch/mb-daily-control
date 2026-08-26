(() => {
  "use strict";

  // Legacy guard markers kept inert for the maintenance hand-off only:
  // affiliate_product_grid_view · after_proof

  const AI_INTENT_KEY = "lm_ai_purchase_intent_v1";
  const ORDER_KEY = "lemienbac_email_order_v1";
  const SALE_CUTOFF_MINUTES = 18 * 60;
  let checkoutOpened = false;
  let qrViewed = false;
  let claimSubmitted = false;
  let blockedTracked = "";

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
      || text.match(/Gợi ý\s+số\s+MB_ALL\s+-\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i);
    return target ? target[1] : "";
  }

  function vietnamNow() {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23"
    }).formatToParts(new Date());
    const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return {
      date: `${values.day}/${values.month}/${values.year}`,
      minutes: Number(values.hour || 0) * 60 + Number(values.minute || 0)
    };
  }

  function readExistingOrder() {
    let raw = "";
    try { raw = localStorage.getItem(ORDER_KEY) || ""; } catch (_) {}
    if (!raw) {
      try { raw = sessionStorage.getItem(ORDER_KEY) || ""; } catch (_) {}
    }
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (_) { return null; }
  }

  function existingBuyerMayReopen() {
    const order = readExistingOrder();
    if (!order || order.reportDate !== reportDateLabel()) return false;
    return order.status === "pending" || order.status === "approved";
  }

  function purchaseGateReason() {
    const now = vietnamNow();
    const reportDate = reportDateLabel();
    if (!reportDate || reportDate !== now.date) return "stale_report";
    if (now.minutes >= SALE_CUTOFF_MINUTES && !existingBuyerMayReopen()) return "cutoff";
    return "";
  }

  function newPurchaseWindowClosed() {
    return Boolean(purchaseGateReason());
  }

  function closeCheckoutForGate() {
    const checkout = document.getElementById("checkout");
    if (checkout && checkout.hidden === false) checkout.hidden = true;
    document.body?.classList.remove("modal-open", "checkout-open");
  }

  function applyPurchaseWindowGate() {
    const reason = purchaseGateReason();
    const closed = Boolean(reason);
    document.body?.classList.toggle("lm-ai-sale-closed", closed);
    if (!closed) return;

    closeCheckoutForGate();
    const stale = reason === "stale_report";
    document.querySelectorAll("[data-open-checkout], [data-ai-sticky-cta]").forEach(button => {
      if (!(button instanceof HTMLButtonElement)) return;
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
      button.setAttribute("title", stale ? "Báo cáo hiện tại chưa được cập nhật cho hôm nay" : "Báo cáo hôm nay đã khóa trước giờ quay");
      if (button.closest(".portal-paid-card")) {
        button.textContent = stale ? "BÁO CÁO HÔM NAY CHƯA SẴN SÀNG" : "BÁO CÁO HÔM NAY ĐÃ KHÓA";
      }
    });

    const paidCard = document.querySelector(".portal-paid-card");
    if (paidCard && !paidCard.querySelector(".lm-postdraw-lock-note")) {
      const note = document.createElement("p");
      note.className = "lm-postdraw-lock-note";
      note.textContent = stale
        ? "Báo cáo hiện tại chưa đúng ngày hôm nay nên thanh toán đã được khóa. Hệ thống chỉ mở lại khi dữ liệu T−1 và báo cáo ngày mới đồng bộ hợp lệ."
        : "Báo cáo hôm nay đã khóa trước giờ quay. Báo cáo ngày mới chỉ mở khi dữ liệu T−1 được khóa hợp lệ.";
      paidCard.append(note);
    }

    if (blockedTracked !== reason) {
      blockedTracked = reason;
      emit("ai_purchase_window_closed", {
        cutoff: "18:00",
        reason,
        report_date: reportDateLabel(),
        product: "daily_ai_analysis"
      });
    }
  }

  function installPurchaseWindowGate() {
    document.addEventListener("click", event => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target?.closest("[data-open-checkout], [data-ai-sticky-cta]")) return;
      if (!newPurchaseWindowClosed()) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      applyPurchaseWindowGate();
    }, true);
    applyPurchaseWindowGate();
    window.setTimeout(applyPurchaseWindowGate, 0);
    window.setTimeout(applyPurchaseWindowGate, 500);
    window.setInterval(applyPurchaseWindowGate, 30000);
  }

  function addRuntimeStyle() {
    if (document.getElementById("lm-commerce-runtime-style")) return;
    const style = document.createElement("style");
    style.id = "lm-commerce-runtime-style";
    style.textContent = `
      .lm-ai-runtime-kicker{display:block;margin-top:7px;color:#79575a;font-size:10px;font-weight:850;line-height:1.4}
      .lm-postdraw-lock-note{margin:9px 0 0;padding:9px 10px;border:1px solid #ead9db;border-radius:10px;background:#fff7f7;color:#74565a;font-size:10px;font-weight:800;line-height:1.45}
      .lm-ai-sale-closed [data-open-checkout]:disabled,.lm-ai-sale-closed [data-ai-sticky-cta]:disabled{cursor:not-allowed!important;opacity:.62!important;filter:saturate(.6)!important}
      .lm-shopee-nudge{display:none!important}
      .conversion-benefits li{display:flex!important;align-items:flex-start!important;gap:8px!important;text-align:left!important}
      .conversion-benefits li::before{content:"✓"!important;display:grid!important;place-items:center!important;flex:0 0 18px!important;width:18px!important;height:18px!important;margin:1px 0 0!important;border:1px solid #e9c5c9!important;border-radius:999px!important;background:#fff1f2!important;color:#b4232f!important;font-size:11px!important;font-weight:1000!important;line-height:1!important}
      @media(max-width:700px){.conversion-benefits{grid-template-columns:1fr!important;gap:7px!important}.portal-home .portal-hero{padding:20px 0!important}.portal-home h1{font-size:32px!important;line-height:1.08!important}.portal-home .portal-paid-card{padding:14px!important;border-radius:16px!important}.portal-home .portal-paid-card button{min-height:48px!important;font-size:12px!important}}
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
    if (heroLead && date) {
      heroLead.innerHTML = `Chỉ <strong>30.000đ</strong>, nhận gợi ý XSMB hôm nay <strong>${date}</strong> từ hơn <strong>15.000 lượt tính toán AI</strong>, kết hợp phân tích, thống kê và soi cầu qua nhiều phương pháp.`;
    }
    const paidCard = document.querySelector(".portal-paid-card");
    if (!paidCard) return;
    const title = paidCard.querySelector("h2");
    if (title && date) title.textContent = `Bản phân tích AI ngày ${date}`;
    const button = paidCard.querySelector("[data-open-checkout]");
    if (button) {
      button.textContent = "MỞ BẢN PHÂN TÍCH AI · 30.000Đ";
      button.setAttribute("aria-label", `Mở bản phân tích AI ngày ${date || "hôm nay"}, giá 30.000 đồng`);
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
          product: "daily_ai_analysis", price_vnd: 30000,
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
        applyPurchaseWindowGate();
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
    installPurchaseWindowGate();
    installAiFunnelTracking();
  }, { once: true });
})();
