(() => {
  "use strict";

  const OFFER = {
    id: "vpbank-vay-online",
    merchant: "VPBank",
    url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
  };

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

  function mount() {
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

    section.querySelector("a")?.addEventListener("click", () => emit("affiliate_finance_click"));

    const anchor = document.querySelector(".portal-topline") || document.querySelector(".portal-header") || document.querySelector("header");
    if (anchor) anchor.insertAdjacentElement("afterend", section);
    else document.body.prepend(section);

    trackView(section);
  }

  document.addEventListener("DOMContentLoaded", mount, { once: true });
})();