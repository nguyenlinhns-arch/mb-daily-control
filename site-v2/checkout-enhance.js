(() => {
  "use strict";

  const ACCOUNT_HOLDER = "NGUYEN TU LINH";
  const ACCOUNT_NUMBER = "1128091987";
  const BANK_ID = "VPB";
  const AMOUNT = 30000;
  const SHOPEE_PRODUCTS = [
    {
      name: "Tông đơ Philips MG3911/15 7in1",
      image: "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mp1ohea3di4g9e",
      url: "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773390&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vVCVDMyVCNG5nLSVDNCU5MSVDNiVBMS1QaGlsaXBzLU1HMzkxMS0xNS1NdWx0aWdyb29tLTMwMDAtN2luMS1jJUUxJUJBJUFGdC10JUUxJUJCJTg5YS1yJUMzJUEydS10JUMzJUIzYy0lQzQlOTFhLW4lQzQlODNuZy1zJUUxJUJCJUFELWQlRTElQkIlQTVuZy10JUUxJUJBJUExaS1uaCVDMyVBMC1pLjQ2MzYwMDA2MS40OTUxMTM1NzAxNw==&redirect_302=1"
    },
    {
      name: "Sạc dự phòng Anker Zolo 20.000mAh 22.5W",
      image: "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mlnj4c7kwkjp03",
      url: "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773391&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vUyVFMSVCQSVBMWMtZCVFMSVCQiVCMS1waCVDMyVCMm5nLUFua2VyLVpvbG8tQTExMEQtMjAwMDBtQWgtY2h1JUUxJUJBJUE5bi0zQy1UcnVuZy1RdSVFMSVCQiU5MWMtYyVDMyVBMXAtVVNCLUMtdCVDMyVBRGNoLWglRTElQkIlQTNwLXMlRTElQkElQTFjLW5oYW5oLTIyLjVXLWkuMTIwMjg4OTY3OC40NTU1NDAxNDY3NQ==&redirect_302=1"
    },
    {
      name: "Máy vặn vít pin Bosch GO 3",
      image: "https://down-vn.img.susercontent.com/file/sg-11134201-8259d-mrbyk5d9m3gs2c",
      url: "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773392&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktdiVFMSVCQSVCN24tdiVDMyVBRHQtcGluLUJvc2NoLUdvLTMtaS43NTgxMDI0OS4yNTUxNDU2ODgyOQ==&redirect_302=1"
    },
    {
      name: "Máy hút bụi cầm tay Deerma DX118C 600W",
      image: "https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m83aax7f0sasfe",
      url: "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773393&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktSCVDMyVCQXQtQiVFMSVCQiVBNWktQyVFMSVCQSVBN20tVGF5LURlZXJtYS1EWDExOEMtJTI4QiVFMSVCQSVBMk4tTSVFMSVCQiU5QUktNjAwVyUyOS1DaCVDMyVBRG5oLWglQzMlQTNuZy1EZWVybWEtaS4yODE0MzI4NC4yNzQ1Nzg2MDQwNA==&redirect_302=1"
    }
  ];
  let checkoutEnhanced = false;

  function isGoogleAdsVisit(url) {
    const paidMedium = /^(cpc|ppc|paid|paidsearch|paid-search)$/i.test(url.searchParams.get("utm_medium") || "");
    const googleSource = /^(google|googleads|google-ads)$/i.test(url.searchParams.get("utm_source") || "");
    return ["gclid", "gbraid", "wbraid"].some((key) => url.searchParams.has(key))
      || (googleSource && paidMedium);
  }

  function addAdsLandingMode() {
    if (isGoogleAdsVisit(new URL(window.location.href))) {
      document.body.classList.add("ads-landing");
    }
  }

  function emitAffiliateClick(product, index) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: "affiliate_product_click",
      affiliate_network: "ACCESSTRADE",
      merchant: "Shopee",
      product_index: index + 1,
      product_name: product.name
    });
  }

  function addDirectShopeeDeals() {
    document.querySelectorAll("#lm-shopee-gate").forEach((node) => node.remove());
    document.body.classList.remove("lm-shopee-gate-open");
    if (window.location.pathname !== "/" || document.querySelector(".lm-product-deals")) return;

    const style = document.createElement("style");
    style.id = "lm-product-deals-style";
    style.textContent = `
      .lm-product-deals{width:100%;padding:8px 0}.lm-product-deals-inner{max-width:1180px;margin:auto;padding:0 16px}
      .lm-product-deals-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:9px}.lm-product-deals-head div{min-width:0}.lm-product-deals-kicker{display:block;color:#ee4d2d;font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.lm-product-deals-head h2{margin:2px 0 0;color:#203542;font-size:19px;line-height:1.2}.lm-product-deals-head small{color:#84919a;font-size:10px;white-space:nowrap}
      .lm-product-deals-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.lm-product-card{min-width:0;overflow:hidden;border:1px solid #e7ebee;border-radius:14px;background:#fff;color:#243542!important;text-decoration:none!important;box-shadow:0 2px 9px rgba(24,42,54,.04)}.lm-product-image{aspect-ratio:1/1;background:#f6f7f8;overflow:hidden}.lm-product-image img{display:block;width:100%;height:100%;object-fit:cover}.lm-product-copy{padding:9px}.lm-product-copy strong{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2;min-height:36px;font-size:12px;line-height:1.45;color:#263946}.lm-product-copy span{display:flex;align-items:center;justify-content:center;min-height:38px;margin-top:8px;border-radius:9px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:900}.lm-product-disclosure{margin:6px 1px 0;color:#929ca3;font-size:8.5px;line-height:1.35}
      @media(max-width:700px){.lm-product-deals{padding:6px 0}.lm-product-deals-inner{padding:0 10px}.lm-product-deals-head{align-items:start}.lm-product-deals-head h2{font-size:17px}.lm-product-deals-head small{display:none}.lm-product-deals-grid{display:flex;gap:8px;overflow-x:auto;scroll-snap-type:x mandatory;padding:0 1px 4px;scrollbar-width:none}.lm-product-deals-grid::-webkit-scrollbar{display:none}.lm-product-card{flex:0 0 min(42vw,170px);scroll-snap-align:start}.lm-product-copy{padding:8px}.lm-product-copy strong{font-size:11.5px;min-height:34px}.lm-product-copy span{min-height:40px;font-size:10.5px}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.className = "lm-product-deals";
    section.setAttribute("aria-label", "Đồ nam và gia dụng Shopee");
    section.innerHTML = `
      <div class="lm-product-deals-inner">
        <div class="lm-product-deals-head"><div><span class="lm-product-deals-kicker">Đồ nam & gia dụng</span><h2>Dễ dùng · dễ mua · mở đúng sản phẩm</h2></div><small>Liên kết đối tác ACCESSTRADE</small></div>
        <div class="lm-product-deals-grid"></div>
        <p class="lm-product-disclosure">Liên kết đối tác · giá và ưu đãi xem trực tiếp trên Shopee.</p>
      </div>`;

    const grid = section.querySelector(".lm-product-deals-grid");
    SHOPEE_PRODUCTS.forEach((product, index) => {
      const card = document.createElement("a");
      card.className = "lm-product-card";
      card.href = product.url;
      card.target = "_blank";
      card.rel = "sponsored noopener noreferrer";
      card.innerHTML = `<div class="lm-product-image"><img src="${product.image}" loading="lazy" decoding="async" alt="${product.name.replace(/\"/g, "&quot;")}"></div><div class="lm-product-copy"><strong>${product.name}</strong><span>Xem trên Shopee →</span></div>`;
      card.addEventListener("click", () => emitAffiliateClick(product, index));
      grid.appendChild(card);
    });

    const oldAffiliate = document.querySelector(".lm-affiliate-section");
    if (oldAffiliate) {
      oldAffiliate.replaceWith(section);
      return;
    }
    const toolsSection = [...document.querySelectorAll("section")].find((node) => /Công cụ thống kê XSMB/i.test(node.textContent || ""));
    if (toolsSection) toolsSection.insertAdjacentElement("afterend", section);
  }

  function addAccountHolder(paymentCard) {
    if (paymentCard.querySelector("[data-account-holder]")) return;
    const bankRow = paymentCard.querySelector(".pay-row");
    if (!bankRow) return;

    const row = document.createElement("div");
    row.className = "pay-row pay-row-holder";
    row.dataset.accountHolder = "true";

    const label = document.createElement("span");
    label.textContent = "Chủ tài khoản";
    const value = document.createElement("strong");
    value.id = "bank-account-holder";
    value.textContent = ACCOUNT_HOLDER;

    row.append(label, value);
    bankRow.insertAdjacentElement("afterend", row);
  }

  function qrUrl(memo) {
    const params = new URLSearchParams({
      amount: String(AMOUNT),
      addInfo: memo,
      accountName: ACCOUNT_HOLDER
    });
    return `https://img.vietqr.io/image/${BANK_ID}-${ACCOUNT_NUMBER}-compact2.png?${params.toString()}`;
  }

  function addVietQr(paymentCard, memoNode) {
    if (document.querySelector(".vietqr-panel")) return;

    const figure = document.createElement("figure");
    figure.className = "vietqr-panel";
    figure.setAttribute("aria-label", "Mã VietQR chuyển khoản báo cáo hôm nay");

    const copy = document.createElement("figcaption");
    copy.innerHTML = "<strong>Quét VietQR để chuyển nhanh</strong><span>Số tiền và nội dung chuyển khoản được điền sẵn. Hãy kiểm tra đúng tên người nhận trước khi xác nhận.</span>";

    const image = document.createElement("img");
    image.className = "vietqr-image";
    image.width = 360;
    image.height = 360;
    image.loading = "lazy";
    image.decoding = "async";
    image.alt = `VietQR VPBank ${ACCOUNT_NUMBER}, người nhận ${ACCOUNT_HOLDER}`;
    image.referrerPolicy = "no-referrer";
    image.addEventListener("error", () => {
      figure.classList.add("vietqr-unavailable");
    });

    const note = document.createElement("p");
    note.className = "vietqr-recipient";
    note.innerHTML = `<span>Người nhận</span><strong>${ACCOUNT_HOLDER}</strong>`;

    const update = () => {
      const memo = String(memoNode.textContent || "").trim();
      if (!/^\d{12}$/.test(memo)) return;
      image.src = qrUrl(memo);
      figure.classList.remove("vietqr-unavailable");
    };

    figure.append(copy, image, note);
    paymentCard.insertAdjacentElement("afterend", figure);
    update();
    new MutationObserver(update).observe(memoNode, { childList: true, characterData: true, subtree: true });
  }

  function enhanceCheckout() {
    if (checkoutEnhanced) return;
    const paymentCard = document.querySelector(".payment-card");
    const memoNode = document.getElementById("payment-memo");
    if (!paymentCard || !memoNode) return;
    checkoutEnhanced = true;
    addAccountHolder(paymentCard);
    addVietQr(paymentCard, memoNode);
  }

  document.addEventListener("DOMContentLoaded", () => {
    addAdsLandingMode();
    addDirectShopeeDeals();

    document.querySelectorAll("[data-open-checkout]").forEach((button) => {
      button.addEventListener("click", enhanceCheckout, { once: true });
    });

    const checkout = document.getElementById("checkout");
    if (checkout && checkout.hidden === false) enhanceCheckout();
  }, { once: true });
})();