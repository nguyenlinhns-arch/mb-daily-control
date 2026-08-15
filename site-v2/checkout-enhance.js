(() => {
  "use strict";

  const ACCOUNT_HOLDER = "NGUYEN TU LINH";
  const ACCOUNT_NUMBER = "1128091987";
  const BANK_ID = "VPB";
  const AMOUNT = 30000;
  const SHOPEE_SMARTLINK = "https://nguyenlinhtkv_aul4jx.accesslanding.site";
  const SHOPEE_GATE_KEY = "lm_shopee_gate_seen_v2";
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

  function affiliateGateSeen() {
    try { return sessionStorage.getItem(SHOPEE_GATE_KEY) === "1"; }
    catch { return false; }
  }

  function markAffiliateGateSeen() {
    try { sessionStorage.setItem(SHOPEE_GATE_KEY, "1"); }
    catch {}
  }

  function addAffiliateEntryGate() {
    document.querySelectorAll(".lm-affiliate-note").forEach((node) => node.remove());
    if (window.location.pathname !== "/" || affiliateGateSeen() || document.getElementById("lm-shopee-gate")) return;

    const style = document.createElement("style");
    style.id = "lm-shopee-gate-style";
    style.textContent = `
      .lm-shopee-gate{position:fixed;inset:0;z-index:9999;display:grid;place-items:center;padding:12px;background:rgba(8,20,30,.70);backdrop-filter:blur(5px)}
      .lm-shopee-gate-card{position:relative;width:min(440px,calc(100% - 4px));max-height:calc(100vh - 24px);overflow:auto;border:1px solid #f0d6cb;border-radius:22px;background:#fff;box-shadow:0 26px 80px rgba(0,0,0,.28);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1d2d38}
      .lm-shopee-gate-top{padding:23px 20px 16px;background:linear-gradient(135deg,#fff4ee,#fff)}
      .lm-shopee-gate-badge{display:inline-flex;align-items:center;padding:5px 8px;border-radius:999px;background:#fff0e8;color:#b73e22;font-size:10px;font-weight:900;letter-spacing:.04em;text-transform:uppercase}
      .lm-shopee-gate h2{margin:10px 0 0;padding-right:32px;font-size:clamp(22px,6vw,26px);line-height:1.12;letter-spacing:-.025em;color:#152936}
      .lm-shopee-gate p{margin:8px 0 0;color:#62717b;font-size:13px;line-height:1.5}
      .lm-shopee-gate-actions{display:grid;gap:9px;padding:0 20px 20px}
      .lm-shopee-gate-primary,.lm-shopee-gate-secondary{min-height:50px;border-radius:12px;display:flex;align-items:center;justify-content:center;padding:0 14px;font:inherit;font-size:13px;font-weight:900;text-decoration:none;cursor:pointer}
      .lm-shopee-gate-primary{border:0;background:#ee4d2d;color:#fff!important;box-shadow:0 9px 22px rgba(238,77,45,.22)}
      .lm-shopee-gate-secondary{border:1px solid #dbe1e5;background:#fff;color:#40515d}
      .lm-shopee-gate-close{position:absolute;right:10px;top:10px;width:38px;height:38px;border:1px solid #e1e5e8;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.96);color:#52626d;font:700 21px/1 system-ui;cursor:pointer}
      body.lm-shopee-gate-open{overflow:hidden}
    `;
    document.head.appendChild(style);

    const gate = document.createElement("aside");
    gate.id = "lm-shopee-gate";
    gate.className = "lm-shopee-gate";
    gate.setAttribute("role", "dialog");
    gate.setAttribute("aria-modal", "true");
    gate.setAttribute("aria-labelledby", "lm-shopee-gate-title");
    gate.innerHTML = `
      <div class="lm-shopee-gate-card">
        <button type="button" class="lm-shopee-gate-close" aria-label="Đóng và xem thống kê">×</button>
        <div class="lm-shopee-gate-top">
          <span class="lm-shopee-gate-badge">Liên kết đối tác · ACCESSTRADE</span>
          <h2 id="lm-shopee-gate-title">Shopee – Ưu đãi hôm nay</h2>
          <p>Xem deal, mã giảm giá và sản phẩm đang được giới thiệu trước khi tiếp tục xem thống kê XSMB.</p>
        </div>
        <div class="lm-shopee-gate-actions">
          <a class="lm-shopee-gate-primary" href="${SHOPEE_SMARTLINK}" target="_blank" rel="sponsored noopener noreferrer">XEM ƯU ĐÃI SHOPEE →</a>
          <button type="button" class="lm-shopee-gate-secondary">ĐÓNG – XEM THỐNG KÊ</button>
        </div>
      </div>`;

    const close = () => {
      markAffiliateGateSeen();
      document.body.classList.remove("lm-shopee-gate-open");
      gate.remove();
    };

    gate.querySelector(".lm-shopee-gate-close").addEventListener("click", close);
    gate.querySelector(".lm-shopee-gate-secondary").addEventListener("click", close);
    gate.querySelector(".lm-shopee-gate-primary").addEventListener("click", () => {
      markAffiliateGateSeen();
      window.setTimeout(close, 80);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && document.getElementById("lm-shopee-gate")) close();
    }, { once: true });

    document.body.classList.add("lm-shopee-gate-open");
    document.body.appendChild(gate);
    gate.querySelector(".lm-shopee-gate-primary").focus({ preventScroll: true });
  }

  document.addEventListener("DOMContentLoaded", () => {
    addAdsLandingMode();
    addAffiliateEntryGate();

    // VietQR is created only when the user opens checkout. This avoids an
    // unnecessary third-party image request on the Google Ads landing view.
    document.querySelectorAll("[data-open-checkout]").forEach((button) => {
      button.addEventListener("click", enhanceCheckout, { once: true });
    });

    // checkout-entry.js may have opened the modal earlier in the same
    // DOMContentLoaded cycle for a /?checkout=1 route.
    const checkout = document.getElementById("checkout");
    if (checkout && checkout.hidden === false) enhanceCheckout();
  }, { once: true });
})();
