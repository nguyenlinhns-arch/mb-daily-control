(() => {
  "use strict";

  const OFFER = {
    id: "vpbank-vay-online",
    network: "ACCESSTRADE",
    merchant: "VPBank",
    url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
  };

  function emitClick() {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: "affiliate_finance_click",
      affiliate_network: OFFER.network,
      affiliate_offer_id: OFFER.id,
      merchant: OFFER.merchant,
      placement: "home_top"
    });
  }

  function mount() {
    if (window.location.pathname !== "/" || document.getElementById("lm-finance-top")) return;

    const style = document.createElement("style");
    style.id = "lm-finance-top-style";
    style.textContent = `
      .lm-finance-top{width:100%;padding:8px 0;background:#f4f7f6;border-bottom:1px solid #dfe7e3}
      .lm-finance-top-inner{width:min(calc(100% - 28px),1180px);margin:auto}
      .lm-finance-top-card{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center;padding:13px 15px;border-radius:14px;background:linear-gradient(135deg,#123f32,#0b2f28);color:#fff;text-decoration:none!important;box-shadow:0 5px 16px rgba(15,50,40,.16)}
      .lm-finance-top-label{display:block;margin-bottom:2px;color:#c7ded5;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
      .lm-finance-top-copy strong{display:block;font-size:15px;line-height:1.25;color:#fff}.lm-finance-top-copy span:last-child{display:block;margin-top:3px;color:#d7e7e1;font-size:11px;line-height:1.4}
      .lm-finance-top-cta{min-height:42px;padding:0 14px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#fff;color:#143f32;font-size:12px;font-weight:900;white-space:nowrap}
      .lm-finance-top-note{margin:5px 2px 0;color:#75847e;font-size:9px;line-height:1.35}
      @media(max-width:700px){.lm-finance-top{padding:6px 0}.lm-finance-top-inner{width:calc(100% - 20px)}.lm-finance-top-card{grid-template-columns:1fr;padding:11px 12px;gap:8px}.lm-finance-top-copy strong{font-size:14px}.lm-finance-top-copy span:last-child{font-size:10.5px}.lm-finance-top-cta{min-height:42px;width:100%}.lm-finance-top-note{font-size:8.5px}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.id = "lm-finance-top";
    section.className = "lm-finance-top";
    section.setAttribute("aria-label", "Quảng cáo tài chính VPBank");
    section.innerHTML = `
      <div class="lm-finance-top-inner">
        <a class="lm-finance-top-card" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">
          <div class="lm-finance-top-copy">
            <span class="lm-finance-top-label">Quảng cáo tài chính · ACCESSTRADE</span>
            <strong>Cần thêm tài chính? Xem điều kiện vay online tại VPBank</strong>
            <span>Đăng ký trực tuyến trên website VPBank. Hạn mức, lãi suất và phê duyệt phụ thuộc hồ sơ.</span>
          </div>
          <span class="lm-finance-top-cta">Xem điều kiện vay →</span>
        </a>
        <p class="lm-finance-top-note">Khoản vay có lãi/phí. Cân nhắc khả năng trả nợ trước khi đăng ký.</p>
      </div>`;

    section.querySelector("a")?.addEventListener("click", emitClick);
    const anchor = document.querySelector(".portal-topline") || document.querySelector(".portal-header") || document.querySelector("header");
    if (anchor) anchor.insertAdjacentElement("afterend", section);
    else document.body.prepend(section);
  }

  document.addEventListener("DOMContentLoaded", mount, { once: true });
})();