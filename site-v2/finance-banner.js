(() => {
  "use strict";

  const OFFERS = [
    {
      id: "vpbank-vay-online",
      merchant: "VPBank",
      label: "Vay online",
      url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
    },
    {
      id: "vpbank-credit-card-senid",
      merchant: "VPBank / SenID",
      label: "Mở thẻ tín dụng",
      url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6417244891749212821?sub4=oneatweb&url_enc=aHR0cHM6Ly9tb3RoZS5zZW5pZC52bi90cGNfYXQ%3D"
    }
  ];

  function emitClick(offer) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: "affiliate_finance_click",
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: offer.id,
      merchant: offer.merchant,
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
      .lm-finance-top-card{padding:13px 15px;border-radius:14px;background:linear-gradient(135deg,#123f32,#0b2f28);color:#fff;box-shadow:0 5px 16px rgba(15,50,40,.16)}
      .lm-finance-top-label{display:block;margin-bottom:3px;color:#c7ded5;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
      .lm-finance-top-copy strong{display:block;font-size:15px;line-height:1.25;color:#fff}.lm-finance-top-copy span:last-child{display:block;margin-top:3px;color:#d7e7e1;font-size:11px;line-height:1.4}
      .lm-finance-top-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.lm-finance-top-cta{min-height:42px;padding:0 11px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#fff;color:#143f32!important;text-decoration:none!important;font-size:12px;font-weight:900;text-align:center}.lm-finance-top-cta-secondary{background:#dcece6;color:#143f32!important}
      .lm-finance-top-note{margin:5px 2px 0;color:#75847e;font-size:9px;line-height:1.35}
      @media(max-width:700px){.lm-finance-top{padding:6px 0}.lm-finance-top-inner{width:calc(100% - 20px)}.lm-finance-top-card{padding:11px 12px}.lm-finance-top-copy strong{font-size:14px}.lm-finance-top-copy span:last-child{font-size:10.5px}.lm-finance-top-actions{grid-template-columns:1fr;gap:7px}.lm-finance-top-cta{min-height:42px;width:100%}.lm-finance-top-note{font-size:8.5px}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.id = "lm-finance-top";
    section.className = "lm-finance-top";
    section.setAttribute("aria-label", "Ưu đãi tài chính qua ACCESSTRADE");
    section.innerHTML = `
      <div class="lm-finance-top-inner">
        <div class="lm-finance-top-card">
          <div class="lm-finance-top-copy">
            <span class="lm-finance-top-label">Quảng cáo tài chính · ACCESSTRADE</span>
            <strong>Ưu đãi tài chính VPBank</strong>
            <span>Chọn nhu cầu phù hợp. Điều kiện, hạn mức, lãi suất/phí và phê duyệt phụ thuộc từng hồ sơ và sản phẩm.</span>
          </div>
          <div class="lm-finance-top-actions">
            <a class="lm-finance-top-cta" data-finance-offer="vpbank-vay-online" href="${OFFERS[0].url}" target="_blank" rel="sponsored nofollow noopener noreferrer">Vay online →</a>
            <a class="lm-finance-top-cta lm-finance-top-cta-secondary" data-finance-offer="vpbank-credit-card-senid" href="${OFFERS[1].url}" target="_blank" rel="sponsored nofollow noopener noreferrer">Mở thẻ tín dụng →</a>
          </div>
        </div>
        <p class="lm-finance-top-note">Sản phẩm tín dụng có thể phát sinh lãi/phí. Cân nhắc khả năng trả nợ và đọc điều kiện trước khi đăng ký.</p>
      </div>`;

    section.querySelectorAll("[data-finance-offer]").forEach((link) => {
      const offer = OFFERS.find((item) => item.id === link.dataset.financeOffer);
      if (offer) link.addEventListener("click", () => emitClick(offer));
    });

    const anchor = document.querySelector(".portal-topline") || document.querySelector(".portal-header") || document.querySelector("header");
    if (anchor) anchor.insertAdjacentElement("afterend", section);
    else document.body.prepend(section);
  }

  document.addEventListener("DOMContentLoaded", mount, { once: true });
})();