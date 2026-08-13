(() => {
  "use strict";

  const PRICE = 30000;
  const PRICE_TEXT = "30.000đ";
  const ITEM_NAME = "Báo cáo dữ liệu AI ngày hôm nay";
  const REPORT_DATE = document.body.dataset.reportDate || "13/08/2026";
  const DATA_LOCK_DATE = document.body.dataset.lockDate || "12/08/2026";
  const STATIC_PUBLIC_READY = document.body.dataset.publicReady === "true";
  const rawEndpoint = String(window.ORDER_CONFIRMATION_ENDPOINT || "").trim();
  const BACKEND_ENDPOINT = /^https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec$/.test(rawEndpoint)
    ? rawEndpoint
    : "";
  const ORDER_KEY = "lemienbac_email_order_v1";
  const ATTRIBUTION_KEY = "lemienbac_attribution_v1";
  const CONSENT_KEY = "lemienbac_measurement_consent_v1";
  const ZALO_URL = "https://zalo.me/0398696879";
  const POLL_INTERVAL_MS = 5000;
  const DELIVERY_SCHEMA = "fourso-top2-v1";

  const checkout = document.getElementById("checkout");
  const checkoutClose = document.getElementById("checkout-close");
  const orderCodeNode = document.getElementById("order-code");
  const paymentMemoNode = document.getElementById("payment-memo");
  const selfConfirmButton = document.getElementById("payment-self-confirm");
  const pendingPanel = document.getElementById("payment-pending");
  const pendingTitle = document.getElementById("pending-title");
  const pendingCopy = document.getElementById("pending-copy");
  const deliveryView = document.getElementById("delivery-view");
  const deliveryTitle = document.getElementById("delivery-title");
  const deliveryPairs = document.getElementById("delivery-pairs");
  const consentPanel = document.getElementById("consent");

  let pollTimer = 0;
  let submitting = false;
  let order = loadOrder();
  let dataReady = false;

  function vietnamReportDate() {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    }).formatToParts(new Date());
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return `${values.day}/${values.month}/${values.year}`;
  }

  function setPaymentAvailability(ready) {
    dataReady = Boolean(ready);
    document.querySelectorAll("[data-open-checkout]").forEach((button) => {
      button.disabled = !dataReady;
      button.setAttribute("aria-disabled", String(!dataReady));
    });
    document.body.classList.toggle("data-stale", !dataReady);
  }

  function track(eventName, parameters = {}) {
    if (typeof window.gtag === "function") window.gtag("event", eventName, parameters);
  }

  function randomToken(byteLength = 4) {
    const bytes = new Uint8Array(byteLength);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(36).padStart(2, "0")).join("");
  }

  function randomDigits(length = 6) {
    let value = "";
    while (value.length < length) {
      const bytes = new Uint8Array(length);
      crypto.getRandomValues(bytes);
      for (const byte of bytes) {
        // Discard the final six byte values to keep every decimal digit equally likely.
        if (byte < 250) value += String(byte % 10);
        if (value.length === length) break;
      }
    }
    return value;
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

  function newOrder() {
    const day = dateStamp();
    const suffix = randomDigits(6);
    return {
      // The backend keeps its legacy identifier while the bank memo is numeric-only.
      // Both contain the same YYMMDD date and six-digit random suffix for reconciliation.
      code: `AI-${day}-${suffix}`,
      paymentMemo: `${day}${suffix}`,
      customerToken: randomToken(20),
      reportDate: REPORT_DATE,
      status: "draft",
      createdAt: new Date().toISOString(),
      submittedAt: "",
      approvedAt: "",
      delivery: null
    };
  }

  function loadOrder() {
    try {
      const parsed = JSON.parse(sessionStorage.getItem(ORDER_KEY) || "null");
      if (
        parsed
        && /^AI-\d{6}-[A-Z0-9]{6}$/.test(parsed.code)
        && typeof parsed.customerToken === "string"
        && parsed.customerToken.length >= 20
        && parsed.reportDate === REPORT_DATE
      ) {
        if (parsed.status === "draft" && !/^\d{12}$/.test(String(parsed.paymentMemo || ""))) {
          const refreshed = newOrder();
          sessionStorage.setItem(ORDER_KEY, JSON.stringify(refreshed));
          return refreshed;
        }
        return {
          ...parsed,
          paymentMemo: /^\d{12}$/.test(String(parsed.paymentMemo || "")) ? parsed.paymentMemo : parsed.code
        };
      }
    } catch (_) {
      // Dữ liệu phiên lỗi sẽ được thay bằng một yêu cầu mới.
    }
    const fresh = newOrder();
    sessionStorage.setItem(ORDER_KEY, JSON.stringify(fresh));
    return fresh;
  }

  function saveOrder() {
    sessionStorage.setItem(ORDER_KEY, JSON.stringify(order));
  }

  function collectAttribution() {
    const allowed = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "gbraid", "wbraid"];
    const url = new URL(window.location.href);
    let saved = {};
    try {
      saved = JSON.parse(localStorage.getItem(ATTRIBUTION_KEY) || "{}") || {};
    } catch (_) {
      saved = {};
    }
    for (const key of allowed) {
      const value = url.searchParams.get(key);
      if (value) saved[key] = value.slice(0, 250);
    }
    if (!saved.landing_page) saved.landing_page = `${url.origin}${url.pathname}`;
    if (!saved.first_seen_at) saved.first_seen_at = new Date().toISOString();
    try {
      localStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(saved));
    } catch (_) {
      // Thông tin nguồn truy cập là tùy chọn.
    }
    return saved;
  }

  const attribution = collectAttribution();

  function showPending(title, copy, error = false) {
    pendingPanel.hidden = false;
    pendingPanel.classList.toggle("is-error", error);
    pendingPanel.querySelector(".pending-icon").textContent = error ? "!" : "…";
    pendingTitle.textContent = title;
    pendingCopy.textContent = copy;
    deliveryView.hidden = true;
  }

  function validDelivery(delivery) {
    return delivery?.schema === DELIVERY_SCHEMA
      && Array.isArray(delivery.pairs)
      && delivery.pairs.length === 2
      && delivery.pairs.every((pair, index) => (
        Number(pair.rank) === index + 1
        && Array.isArray(pair.numbers)
        && pair.numbers.length === 2
        && pair.numbers.every((code) => /^\d{2}$/.test(String(code)))
      ));
  }

  function showDelivery(delivery) {
    if (!validDelivery(delivery)) {
      order.status = "pending";
      order.delivery = null;
      saveOrder();
      showPending(
        "Đang tải kết quả 4SO",
        "Hệ thống đang cập nhật hai cặp theo thứ tự xếp hạng."
      );
      startPolling();
      return;
    }

    stopPolling();
    order.status = "approved";
    order.approvedAt = order.approvedAt || new Date().toISOString();
    order.delivery = delivery;
    saveOrder();

    // Build the complete four-number result before showing the approved panel.
    // This prevents a partially rendered state where customers only see the
    // payment confirmation heading without the two ranked pairs.
    deliveryView.hidden = true;
    deliveryView.dataset.rendered = "false";
    const pairFragment = document.createDocumentFragment();
    for (const pair of delivery.pairs) {
      const card = document.createElement("article");
      card.className = "delivery-pair";

      const rank = document.createElement("span");
      rank.className = "delivery-pair-rank";
      rank.textContent = `TOP ${pair.rank}`;

      const numbers = document.createElement("div");
      numbers.className = "delivery-pair-numbers";
      for (const code of pair.numbers) {
        const value = document.createElement("strong");
        value.textContent = String(code);
        numbers.append(value);
      }

      card.append(rank, numbers);
      pairFragment.append(card);
    }

    deliveryPairs.replaceChildren(pairFragment);
    deliveryTitle.textContent = String(delivery.title || `4SO ngày ${REPORT_DATE}`);
    deliveryPairs.setAttribute(
      "aria-label",
      `4SO gồm TOP 1: ${delivery.pairs[0].numbers.join(", ")} và TOP 2: ${delivery.pairs[1].numbers.join(", ")}`
    );
    pendingPanel.hidden = true;
    selfConfirmButton.hidden = true;
    deliveryView.dataset.rendered = "true";
    deliveryView.hidden = false;

    const purchaseKey = `lemienbac_purchase_${order.code}`;
    if (!localStorage.getItem(purchaseKey)) {
      const purchasePayload = {
        transaction_id: order.code,
        currency: "VND",
        value: PRICE,
        items: [{ item_id: "daily-report", item_name: ITEM_NAME, price: PRICE, quantity: 1 }]
      };
      track("purchase", purchasePayload);
      // Google Ads currently imports this GA4 key event as its primary purchase conversion.
      track("manual_event_PURCHASE", purchasePayload);
      localStorage.setItem(purchaseKey, "1");
    }
  }

  function updateCheckoutState() {
    orderCodeNode.textContent = order.paymentMemo;
    paymentMemoNode.textContent = order.paymentMemo;
    document.querySelectorAll(".checkout-scope").forEach((node) => {
      node.textContent = `01 báo cáo ngày ${REPORT_DATE} · dữ liệu khóa đến ${DATA_LOCK_DATE}.`;
    });

    selfConfirmButton.disabled = order.status !== "draft" || submitting;
    selfConfirmButton.hidden = order.status === "approved";
    if (order.status === "pending") {
      showPending(
        "Đã gửi email báo chủ dịch vụ",
        "Hệ thống đang chờ đối soát. Khi chủ dịch vụ bấm xác nhận trong email, báo cáo sẽ tự mở tại đây."
      );
      startPolling();
    } else if (order.status === "approved") {
      showDelivery(order.delivery || {});
    } else if (order.status === "rejected") {
      showPending(
        "Chưa tìm thấy giao dịch",
        "Vui lòng kiểm tra lại mã chuyển khoản hoặc dùng nút Hỗ trợ ngay để được đối soát.",
        true
      );
    } else {
      pendingPanel.hidden = true;
      deliveryView.hidden = true;
    }
  }

  function openCheckout() {
    if (!dataReady) return;
    updateCheckoutState();
    checkout.hidden = false;
    document.body.classList.add("modal-open");
    checkoutClose.focus();
    track("begin_checkout", {
      currency: "VND",
      value: PRICE,
      items: [{ item_id: "daily-report", item_name: ITEM_NAME, price: PRICE, quantity: 1 }]
    });
  }

  function closeCheckout() {
    checkout.hidden = true;
    document.body.classList.remove("modal-open");
  }

  function hiddenPost(endpoint, fields) {
    const frameName = `order-frame-${randomToken(5)}`;
    const iframe = document.createElement("iframe");
    iframe.name = frameName;
    iframe.title = "Gửi yêu cầu xác nhận thanh toán";
    iframe.hidden = true;

    const form = document.createElement("form");
    form.method = "POST";
    form.action = endpoint;
    form.target = frameName;
    form.hidden = true;
    form.referrerPolicy = "no-referrer";
    for (const [name, value] of Object.entries(fields)) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = String(value ?? "");
      form.append(input);
    }
    document.body.append(iframe, form);
    form.submit();
    window.setTimeout(() => { form.remove(); iframe.remove(); }, 60000);
  }

  function submitPaymentClaim() {
    if (submitting || order.status !== "draft") return;
    if (!BACKEND_ENDPOINT) {
      showPending(
        "Kênh email xác nhận chưa sẵn sàng",
        "Chưa gửi yêu cầu. Vui lòng dùng nút Hỗ trợ ngay để được kiểm tra.",
        true
      );
      return;
    }

    submitting = true;
    selfConfirmButton.disabled = true;
    selfConfirmButton.textContent = "Đang gửi email thông báo…";
    hiddenPost(BACKEND_ENDPOINT, {
      action: "create",
      order_code: order.code,
      customer_token: order.customerToken,
      plan: "day",
      amount: PRICE,
      submitted_at: new Date().toISOString(),
      page_url: window.location.href.slice(0, 1000),
      attribution: JSON.stringify({ ...attribution, report_date: REPORT_DATE }).slice(0, 3000),
      contact: "",
      website: ""
    });

    order.status = "pending";
    order.submittedAt = new Date().toISOString();
    saveOrder();
    track("payment_submitted", {
      currency: "VND",
      value: PRICE,
      transaction_id: order.code,
      report_date: REPORT_DATE
    });
    showPending(
      "Đã gửi email báo chủ dịch vụ",
      "Giữ màn hình này. Khi giao dịch được xác nhận từ email, báo cáo sẽ tự mở tại đây."
    );
    selfConfirmButton.textContent = "Đã gửi yêu cầu xác nhận";
    submitting = false;
    startPolling();
  }

  function jsonp(params) {
    return new Promise((resolve, reject) => {
      const callbackName = `__fourSoStatus_${randomToken(6)}`;
      const script = document.createElement("script");
      const timeout = window.setTimeout(() => finish(new Error("timeout")), 12000);
      const finish = (error, data) => {
        window.clearTimeout(timeout);
        delete window[callbackName];
        script.remove();
        error ? reject(error) : resolve(data);
      };
      window[callbackName] = (data) => finish(null, data);
      script.onerror = () => finish(new Error("network"));
      const url = new URL(BACKEND_ENDPOINT);
      for (const [key, value] of Object.entries({ ...params, callback: callbackName, _: Date.now() })) {
        url.searchParams.set(key, String(value));
      }
      script.referrerPolicy = "no-referrer";
      script.src = url.toString();
      document.head.append(script);
    });
  }

  async function checkStatus() {
    if (!BACKEND_ENDPOINT || order.status !== "pending") return;
    try {
      const result = await jsonp({
        action: "status",
        order_code: order.code,
        customer_token: order.customerToken
      });
      if (!result || result.ok !== true) return;
      if (result.status === "approved") {
        order.approvedAt = result.approved_at || new Date().toISOString();
        showDelivery(result.delivery || {});
      } else if (result.status === "rejected") {
        order.status = "rejected";
        saveOrder();
        stopPolling();
        updateCheckoutState();
      }
    } catch (_) {
      // Lỗi mạng tạm thời sẽ được thử lại ở lượt tiếp theo.
    }
  }

  function startPolling() {
    if (!BACKEND_ENDPOINT || pollTimer || order.status !== "pending") return;
    checkStatus();
    pollTimer = window.setInterval(checkStatus, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollTimer) window.clearInterval(pollTimer);
    pollTimer = 0;
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
  selfConfirmButton.addEventListener("click", submitPaymentClaim);

  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const node = document.getElementById(button.dataset.copyTarget);
      let value = node?.textContent?.trim() || "";
      if (button.hasAttribute("data-copy-plain")) value = value.replace(/\D/g, "");
      copyText(value, button);
    });
  });
  document.getElementById("copy-payment").addEventListener("click", (event) => {
    copyText(`VPBank\n1128091987\nSố tiền: ${PRICE_TEXT}\nNội dung: ${order.paymentMemo}`, event.currentTarget);
  });

  document.querySelectorAll(`a[href^="${ZALO_URL}"]`).forEach((link) => {
    link.addEventListener("click", () => track("generate_lead", { method: "zalo_support", order_code: order.code }));
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

  setPaymentAvailability(STATIC_PUBLIC_READY && REPORT_DATE === vietnamReportDate());
  if (dataReady) {
    updateCheckoutState();
    track("view_item", {
      currency: "VND",
      value: PRICE,
      items: [{ item_id: "daily-report", item_name: ITEM_NAME, price: PRICE, quantity: 1 }]
    });
  }
})();
