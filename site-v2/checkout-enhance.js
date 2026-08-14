(() => {
  "use strict";

  const ACCOUNT_HOLDER = "NGUYEN TU LINH";
  const ACCOUNT_NUMBER = "1128091987";
  const BANK_ID = "VPB";
  const AMOUNT = 30000;

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
    const paymentCard = document.querySelector(".payment-card");
    const memoNode = document.getElementById("payment-memo");
    if (!paymentCard || !memoNode) return;
    addAccountHolder(paymentCard);
    addVietQr(paymentCard, memoNode);
  }

  document.addEventListener("DOMContentLoaded", () => {
    addAdsLandingMode();
    enhanceCheckout();
  }, { once: true });
})();
