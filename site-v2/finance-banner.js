(() => {
  "use strict";

  const SHOPEE = {
    id: "shopee-smartlink",
    merchant: "Shopee",
    url: "https://nguyenlinhtkv_aul4jx.accesslanding.site"
  };

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: window.location.pathname,
      affiliate_network: "ACCESSTRADE",
      ...extra
    });
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
      .lm-affiliate-section{margin:4px 0 14px!important}
      .lm-affiliate-card{position:relative;overflow:hidden;border-color:#e8dfd8!important;background:linear-gradient(135deg,#fffaf7,#fff)!important;box-shadow:0 4px 18px rgba(39,29,24,.05)!important}
      .lm-affiliate-card:before{content:"TÀI TRỢ";position:absolute;top:9px;right:10px;padding:3px 6px;border-radius:999px;background:#fff1e8;color:#b84b16;font-size:8px;font-weight:1000;letter-spacing:.08em}
      .lm-affiliate-card b{padding-right:56px;color:#263744!important;font-size:14px!important}
      .lm-affiliate-card .lm-affiliate-cta{background:#ee4d2d!important;box-shadow:none!important}
      .lm-affiliate-note{color:#8b9298!important}
      .lm-ai-runtime-kicker{display:block;margin-top:6px;color:#8a4d51;font-size:10px;font-weight:900;letter-spacing:.05em}
      @media(max-width:700px){.lm-affiliate-card:before{top:8px;right:8px}.lm-affiliate-card b{padding-right:54px}}
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
      heroLead.innerHTML = `Theo dõi 27 mã kỳ gần nhất, tần suất, lô gan, 45 cặp đảo và các phương pháp công khai. Khi cần phần kết luận riêng cho ngày <strong>${date}</strong>, bạn có thể mở bản phân tích AI một lần 30.000đ.`;
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
        kicker.textContent = "Thanh toán một lần · Không tự gia hạn · Không cam kết kết quả";
        button?.insertAdjacentElement("afterend", kicker);
      }
    }
  }

  function affiliateMarkup() {
    return `
      <section class="lm-affiliate-section" aria-label="Liên kết tài trợ" data-affiliate-commerce="true">
        <div class="lm-affiliate-inner">
          <a class="lm-affiliate-card" id="affiliate-shopee-smartlink" href="${SHOPEE.url}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate="${SHOPEE.id}">
            <div><b>Shopee · xem sản phẩm và ưu đãi đang có</b><span>Khu vực tài trợ qua ACCESSTRADE. Mở Shopee để tham khảo sản phẩm phù hợp với nhu cầu của bạn.</span></div>
            <span class="lm-affiliate-cta">Xem trên Shopee →</span>
          </a>
          <p class="lm-affiliate-note">Website có thể nhận hoa hồng từ giao dịch đủ điều kiện; giá mua của bạn không tăng vì liên kết này.</p>
        </div>
      </section>`;
  }

  function installAffiliate() {
    if (window.location.pathname !== "/") return;
    let card = document.getElementById("affiliate-shopee-smartlink");
    if (!card) {
      const tools = document.querySelector(".portal-tools")?.closest(".portal-section") || document.querySelector(".portal-tools");
      if (tools) {
        tools.insertAdjacentHTML("afterend", affiliateMarkup());
        card = document.getElementById("affiliate-shopee-smartlink");
      }
    }
    if (!card) return;

    card.href = SHOPEE.url;
    card.setAttribute("rel", "sponsored nofollow noopener noreferrer");
    card.dataset.affiliate = SHOPEE.id;
    const title = card.querySelector("b");
    const desc = card.querySelector("span:not(.lm-affiliate-cta)");
    const cta = card.querySelector(".lm-affiliate-cta");
    if (title) title.textContent = "Shopee · xem sản phẩm và ưu đãi đang có";
    if (desc) desc.textContent = "Khu vực tài trợ qua ACCESSTRADE. Mở Shopee để tham khảo sản phẩm phù hợp với nhu cầu của bạn.";
    if (cta) cta.textContent = "Xem trên Shopee →";

    let viewed = false;
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(entries => {
        if (viewed || !entries.some(entry => entry.isIntersecting && entry.intersectionRatio >= 0.45)) return;
        viewed = true;
        emit("affiliate_shopee_view", { affiliate_offer_id: SHOPEE.id, merchant: SHOPEE.merchant, placement: "after_free_tools" });
        observer.disconnect();
      }, { threshold: [0.45] });
      observer.observe(card);
    }
    card.addEventListener("click", () => emit("affiliate_shopee_click", {
      affiliate_offer_id: SHOPEE.id,
      merchant: SHOPEE.merchant,
      placement: "after_free_tools"
    }));
  }

  function installAiTracking() {
    document.addEventListener("click", event => {
      const checkout = event.target.closest("[data-open-checkout]");
      if (checkout) {
        emit("ai_checkout_intent", {
          product: "daily_ai_analysis",
          price_vnd: 30000,
          placement: checkout.closest(".portal-paid-card") ? "hero" : "purchase"
        });
      }
      const sticky = event.target.closest("[data-ai-sticky-cta]");
      if (sticky) emit("ai_sticky_click", { product: "daily_ai_analysis", price_vnd: 30000 });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    addRuntimeStyle();
    polishHomeCopy();
    installAffiliate();
    installAiTracking();
  }, { once: true });
})();
