(() => {
  "use strict";

  const PRICE = 30000;
  const PRICE_TEXT = "30.000đ";
  const REPORT_DATE = document.body.dataset.reportDate || "13/08/2026";
  const DATA_LOCK_DATE = document.body.dataset.lockDate || "12/08/2026";
  const ORDER_KEY = "lemienbac_simple_order_v1";
  const CONSENT_KEY = "lemienbac_measurement_consent_v1";
  const ZALO_URL = "https://zalo.me/0398696879";

  const checkout = document.getElementById("checkout");
  const checkoutClose = document.getElementById("checkout-close");
  const orderCodeNodes = [...document.querySelectorAll("#order-code, #payment-memo")];
  const consentPanel = document.getElementById("consent");

  function track(eventName, parameters = {}) {
    if (typeof window.gtag === "function") window.gtag("event", eventName, parameters);
  }

  function randomToken(byteLength = 4) {
    const bytes = new Uint8Array(byteLength);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(36).padStart(2, "0")).join("");
  }

  function dateStamp() {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "2-digit",
      month: "2-digit",
      day: "2-digit"
    }).formatToParts(new Date());
    const get = (type) => parts.find((part) => part.type === type)?.value || "00";
    return `${get("year")}${get("month")}${get("day")}`;
  }

  function loadOrderCode() {
    const saved = sessionStorage.getItem(ORDER_KEY) || "";
    if (/^AI-\d{6}-[A-Z0-9]{6}$/.test(saved)) return saved;
    const fresh = `AI-${dateStamp()}-${randomToken().slice(0, 6).toUpperCase()}`;
    sessionStorage.setItem(ORDER_KEY, fresh);
    return fresh;
  }

  const orderCode = loadOrderCode();
  orderCodeNodes.forEach((node) => { node.textContent = orderCode; });
  document.querySelectorAll(".checkout-scope").forEach((node) => {
    node.textContent = `01 báo cáo ngày ${REPORT_DATE} · dữ liệu khóa đến ${DATA_LOCK_DATE}.`;
  });

  function openCheckout() {
    checkout.hidden = false;
    document.body.classList.add("modal-open");
    checkoutClose.focus();
    track("begin_checkout", {
      currency: "VND",
      value: PRICE,
      items: [{ item_id: "daily-report", item_name: "Báo cáo dữ liệu AI ngày hôm nay", price: PRICE, quantity: 1 }]
    });
  }

  function closeCheckout() {
    checkout.hidden = true;
    document.body.classList.remove("modal-open");
  }

  async function copyText(value, button) {
    try {
      await navigator.clipboard.writeText(value);
      const previous = button.textContent;
      button.textContent = "Đã sao chép";
      window.setTimeout(() => { button.textContent = previous; }, 1500);
      track("add_payment_info", { currency: "VND", value: PRICE, payment_type: "bank_transfer" });
    } catch (_) {
      button.textContent = "Hãy sao chép thủ công";
    }
  }

  document.querySelectorAll("[data-open-checkout]").forEach((button) => {
    button.addEventListener("click", openCheckout);
  });
  checkoutClose.addEventListener("click", closeCheckout);
  checkout.addEventListener("click", (event) => { if (event.target === checkout) closeCheckout(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !checkout.hidden) closeCheckout(); });

  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const node = document.getElementById(button.dataset.copyTarget);
      let value = node?.textContent?.trim() || "";
      if (button.hasAttribute("data-copy-plain")) value = value.replace(/\D/g, "");
      copyText(value, button);
    });
  });

  document.getElementById("copy-payment").addEventListener("click", (event) => {
    copyText(`VPBank\n1128091987\nSố tiền: ${PRICE_TEXT}\nNội dung: ${orderCode}`, event.currentTarget);
  });
  document.getElementById("copy-order-code").addEventListener("click", (event) => {
    copyText(orderCode, event.currentTarget);
  });

  document.getElementById("zalo-delivery").addEventListener("click", () => {
    navigator.clipboard?.writeText(orderCode).catch(() => {});
    track("generate_lead", { method: "zalo_after_bank_transfer", order_code: orderCode, currency: "VND", value: PRICE });
  });
  document.querySelectorAll(`a[href^="${ZALO_URL}"]`).forEach((link) => {
    if (link.id === "zalo-delivery") return;
    link.addEventListener("click", () => track("generate_lead", { method: "zalo_support" }));
  });

  function updateConsent(granted) {
    const value = granted ? "granted" : "denied";
    window.gtag?.("consent", "update", {
      analytics_storage: value,
      ad_storage: value,
      ad_user_data: value,
      ad_personalization: value
    });
    localStorage.setItem(CONSENT_KEY, granted ? "granted" : "denied");
    consentPanel.hidden = true;
  }

  document.getElementById("consent-accept").addEventListener("click", () => updateConsent(true));
  document.getElementById("consent-reject").addEventListener("click", () => updateConsent(false));
  const storedConsent = localStorage.getItem(CONSENT_KEY);
  if (storedConsent === "granted") updateConsent(true);
  else if (storedConsent === "denied") updateConsent(false);
  else consentPanel.hidden = false;

  track("view_item", {
    currency: "VND",
    value: PRICE,
    items: [{ item_id: "daily-report", item_name: "Báo cáo dữ liệu AI ngày hôm nay", price: PRICE, quantity: 1 }]
  });
})();
