(() => {
  "use strict";

  const SHOPEE = {
    id: "shopee-smartlink",
    merchant: "Shopee",
    url: "https://nguyenlinhtkv_aul4jx.accesslanding.site"
  };
  const AI_INTENT_KEY = "lm_ai_purchase_intent_v1";
  let productGridViewed = false;
  let checkoutOpened = false;
  let qrViewed = false;
  let claimSubmitted = false;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: window.location.pathname,
      ...extra
    });
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
      .lm-affiliate-section{margin:14px 0!important}.lm-affiliate-card{position:relative;overflow:hidden;border-color:#e8dfd8!important;background:linear-gradient(135deg,#fffaf7,#fff)!important;box-shadow:0 4px 18px rgba(39,29,24,.05)!important}.lm-affiliate-card:before{content:"TÀI TRỢ";position:absolute;top:9px;right:10px;padding:3px 6px;border-radius:999px;background:#fff1e8;color:#b84b16;font-size:8px;font-weight:1000;letter-spacing:.08em}.lm-affiliate-card b{padding-right:56px;color:#263744!important;font-size:14px!important}.lm-affiliate-card .lm-affiliate-cta{background:#ee4d2d!important;box-shadow:none!important}.lm-affiliate-note{color:#8b9298!important}
      .lm-ai-runtime-kicker{display:block;margin-top:7px;color:#79575a;font-size:10px;font-weight:850;line-height:1.4}.lm-product-deals{margin-top:16px!important;border-top:1px solid #edf0f2;padding-top:18px!important}.lm-product-deals-head h2:after{content:" · khu tài trợ";color:#9a7770;font-size:10px;font-weight:700}.lm-shopee-nudge{display:none!important}
      @media(max-width:700px){.lm-affiliate-card:before{top:8px;right:8px}.lm-affiliate-card b{padding-right:54px}.lm-product-deals{margin-top:12px!important;padding-top:14px!important}}
    `;
    document.head.appendChild(style);
  }

  function polishHomeCopy() {
    if (window.location.pathname !== "/") return;
    const date = reportDateLabel();
    const heroTitle = document.querySelector(".portal-hero h1");
    if (heroTitle) heroTitle.textContent = "Thống kê XSMB & phân tích AI dữ liệu";

    const heroLead = document.querySelector(".portal-hero .portal-lead");
    if (heroLead) {
      heroLead.innerHTML = `Theo dõi dữ liệu kỳ gần nhất, tần suất, lô gan, cặp đảo và các phương pháp công khai. Khi cần phần kết luận riêng cho ngày <strong>${date}</strong>, mở bản phân tích AI một lần 30.000đ.`;
    }

    const paidCard = document.querySelector(".portal-paid-card");
    if (paidCard) {
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
        kicker.textContent = "Thanh toán một lần · Không tự gia hạn · Dữ liệu lịch sử không phải cam kết kết quả";
        button?.insertAdjacentElement("afterend", kicker);
      }
    }
  }

  function affiliateMarkup() {
    return `
      <section class="lm-affiliate-section" aria-label="Liên kết tài trợ" data-affiliate-commerce="true">
        <div class="lm-affiliate-inner">
          <a class="lm-affiliate-card" id="affiliate-shopee-smartlink" href="${SHOPEE.url}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate="${SHOPEE.id}">
            <div><b>Shopee · xem sản phẩm và ưu đãi đang có</b><span>Khu vực tài trợ qua ACCESSTRADE. Mở Shopee để tham khảo sản phẩm phù hợp.</span></div>
            <span class="lm-affiliate-cta">Xem trên Shopee →</span>
          </a>
          <p class="lm-affiliate-note">Website có thể nhận hoa hồng từ giao dịch đủ điều kiện; giá mua không tăng vì liên kết này.</p>
        </div>
      </section>`;
  }

  function proofAnchor() {
    const proof = document.querySelector(".portal-proof");
    if (proof) return proof.closest(".portal-section") || proof;
    const history = [...document.querySelectorAll("section")].find(section => /Lịch sử đối chiếu|hiệu quả lịch sử|đối chiếu lịch sử/i.test(section.textContent || ""));
    if (history) return history;
    const methods = [...document.querySelectorAll("section")].find(section => /Phương pháp công khai/i.test(section.textContent || ""));
    if (methods) return methods;
    return document.querySelector(".portal-tools")?.closest(".portal-section") || null;
  }

  function moveAffiliateAfterProof() {
    if (window.location.pathname !== "/") return;
    const anchor = proofAnchor();
    if (!anchor) return;
    const products = document.querySelector(".lm-product-deals");
    const generic = document.querySelector(".lm-affiliate-section");
    if (products) {
      if (generic) generic.remove();
      if (anchor.nextElementSibling !== products) anchor.insertAdjacentElement("afterend", products);
      return;
    }
    if (generic && anchor.nextElementSibling !== generic) anchor.insertAdjacentElement("afterend", generic);
  }

  function installAffiliateFallback() {
    if (window.location.pathname !== "/" || document.querySelector(".lm-product-deals")) return;
    let card = document.getElementById("affiliate-shopee-smartlink");
    if (!card) {
      const anchor = proofAnchor();
      if (anchor) {
        anchor.insertAdjacentHTML("afterend", affiliateMarkup());
        card = document.getElementById("affiliate-shopee-smartlink");
      }
    }
    if (!card) return;
    card.href = SHOPEE.url;
    card.setAttribute("rel", "sponsored nofollow noopener noreferrer");
    card.addEventListener("click", () => emit("affiliate_shopee_click", {
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: SHOPEE.id,
      merchant: SHOPEE.merchant,
      placement: "after_proof"
    }));
  }

  function trackProductGridView() {
    const grid = document.querySelector(".lm-product-deals");
    if (!grid || productGridViewed) return;
    const fire = () => {
      if (productGridViewed) return;
      productGridViewed = true;
      emit("affiliate_product_grid_view", {
        affiliate_network: "ACCESSTRADE",
        merchant: "Shopee",
        placement: "after_proof"
      });
    };
    if (!("IntersectionObserver" in window)) return fire();
    const observer = new IntersectionObserver(entries => {
      if (!entries.some(entry => entry.isIntersecting && entry.intersectionRatio >= 0.4)) return;
      fire();
      observer.disconnect();
    }, { threshold: [0.4] });
    observer.observe(grid);
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

    const observer = new MutationObserver(() => {
      if (!checkoutOpened && checkoutVisible()) {
        checkoutOpened = true;
        emit("ai_checkout_open", { product: "daily_ai_analysis", price_vnd: 30000, source: "mutation" });
      }
      markQrView();
      moveAffiliateAfterProof();
      trackProductGridView();
      document.querySelectorAll("#lm-shopee-nudge, #lm-shopee-gate").forEach(node => node.remove());
      document.body.classList.remove("lm-shopee-gate-open");
    });
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden"] });
  }

  document.addEventListener("DOMContentLoaded", () => {
    addRuntimeStyle();
    polishHomeCopy();
    moveAffiliateAfterProof();
    installAffiliateFallback();
    trackProductGridView();
    installAiFunnelTracking();
  }, { once: true });
})();
