(() => {
  "use strict";

  const PLANS = Object.freeze({
    day: { label: "Gói 1 ngày", price: 30000, priceText: "30.000đ" },
    week: { label: "Gói 1 tuần", price: 200000, priceText: "200.000đ" },
    month: { label: "Gói 1 tháng", price: 800000, priceText: "800.000đ" }
  });

  // Filled after the Google Apps Script approval service is deployed.
  const BACKEND_ENDPOINT = String(window.ORDER_CONFIRMATION_ENDPOINT || "").trim();
  const ORDER_KEY = "lemienbac_order_v3";
  const ATTRIBUTION_KEY = "lemienbac_attribution_v3";
  const CONSENT_KEY = "lemienbac_measurement_consent_v1";
  const ZALO_URL = "https://zalo.me/0398696879";
  const POLL_INTERVAL_MS = 5000;

  const checkout = document.getElementById("checkout");
  const checkoutClose = document.getElementById("checkout-close");
  const orderCodeNode = document.getElementById("order-code");
  const amountNode = document.getElementById("payment-amount");
  const memoNode = document.getElementById("payment-memo");
  const selfConfirmButton = document.getElementById("payment-self-confirm");
  const pendingPanel = document.getElementById("payment-pending");
  const pendingTitle = document.getElementById("pending-title");
  const pendingCopy = document.getElementById("pending-copy");
  const deliveryView = document.getElementById("delivery-view");
  const deliveryTitle = document.getElementById("delivery-title");
  const deliverySummary = document.getElementById("delivery-summary");
  const deliveryMetrics = document.getElementById("delivery-metrics");
  const deliveryNotes = document.getElementById("delivery-notes");
  const deliveryLink = document.getElementById("delivery-link");
  const modalPlanButtons = [...document.querySelectorAll("[data-modal-plan]")];
  const consentPanel = document.getElementById("consent");

  let pollTimer = 0;
  let submitting = false;
  let activePlan = "day";
  let order = loadOrder();

  function track(eventName, parameters = {}) {
    if (typeof window.gtag === "function") {
      window.gtag("event", eventName, parameters);
    }
  }

  function randomToken(byteLength = 18) {
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

  function newOrder() {
    return {
      code: `AI-${dateStamp()}-${randomToken(4).slice(0, 6).toUpperCase()}`,
      customerToken: randomToken(20),
      plan: "day",
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
      if (parsed && /^AI-\d{6}-[A-Z0-9]{6}$/.test(parsed.code) && parsed.customerToken) {
        return { ...newOrder(), ...parsed };
      }
    } catch (_) {
      // A fresh, anonymous order is safer than trusting malformed session data.
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
      // Attribution is optional; the order flow must still work without storage.
    }
    return saved;
  }

  const attribution = collectAttribution();

  function setPlan(planKey, { trackSelection = false } = {}) {
    if (!PLANS[planKey] || ["pending", "approved", "rejected"].includes(order.status)) return;
    activePlan = planKey;
    order.plan = planKey;
    saveOrder();
    modalPlanButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.modalPlan === planKey);
      button.setAttribute("aria-pressed", String(button.dataset.modalPlan === planKey));
    });
    amountNode.textContent = PLANS[planKey].priceText;
    memoNode.textContent = order.code;
    if (trackSelection) {
      track("select_item", {
        item_list_name: "Gói báo cáo AI",
        items: [{ item_id: planKey, item_name: PLANS[planKey].label, price: PLANS[planKey].price, quantity: 1 }]
      });
    }
  }

  function updateCheckoutState() {
    activePlan = PLANS[order.plan] ? order.plan : "day";
    orderCodeNode.textContent = order.code;
    amountNode.textContent = PLANS[activePlan].priceText;
    memoNode.textContent = order.code;

    const locked = ["pending", "approved", "rejected"].includes(order.status);
    modalPlanButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.modalPlan === activePlan);
      button.disabled = locked;
      button.setAttribute("aria-pressed", String(button.dataset.modalPlan === activePlan));
    });
    selfConfirmButton.disabled = locked || submitting;
    selfConfirmButton.hidden = order.status === "approved";

    if (order.status === "pending") {
      showPending("Đã gửi email báo chủ dịch vụ", "Vui lòng giữ màn hình này. Hệ thống đang chờ chủ dịch vụ đối soát và xác nhận giao dịch.");
      startPolling();
    } else if (order.status === "approved") {
      showDelivery(order.delivery || {});
    } else if (order.status === "rejected") {
      showPending("Giao dịch chưa được xác nhận", "Chủ dịch vụ chưa tìm thấy giao dịch. Vui lòng kiểm tra mã chuyển khoản hoặc dùng Zalo để được hỗ trợ.", true);
    } else {
      pendingPanel.hidden = true;
      deliveryView.hidden = true;
    }
  }

  function openCheckout(planKey = "day") {
    if (order.status === "draft" && PLANS[planKey]) setPlan(planKey);
    updateCheckoutState();
    checkout.hidden = false;
    document.body.classList.add("modal-open");
    checkoutClose.focus();
    track("begin_checkout", {
      currency: "VND",
      value: PLANS[activePlan].price,
      items: [{ item_id: activePlan, item_name: PLANS[activePlan].label, price: PLANS[activePlan].price, quantity: 1 }]
    });
  }

  function closeCheckout() {
    checkout.hidden = true;
    document.body.classList.remove("modal-open");
  }

  function showPending(title, copy, error = false) {
    pendingPanel.hidden = false;
    pendingPanel.classList.toggle("is-error", error);
    pendingPanel.querySelector(".pending-icon").textContent = error ? "!" : "…";
    pendingTitle.textContent = title;
    pendingCopy.textContent = copy;
    deliveryView.hidden = true;
  }

  function escapeText(value) {
    return String(value ?? "");
  }

  function showDelivery(delivery) {
    stopPolling();
    order.status = "approved";
    order.approvedAt = order.approvedAt || new Date().toISOString();
    order.delivery = delivery;
    saveOrder();

    pendingPanel.hidden = true;
    deliveryView.hidden = false;
    selfConfirmButton.hidden = true;
    modalPlanButtons.forEach((button) => { button.disabled = true; });
    deliveryTitle.textContent = escapeText(delivery.title || "Báo cáo dữ liệu AI đã được mở");
    deliverySummary.textContent = escapeText(delivery.summary || "Giao dịch đã được chủ dịch vụ xác nhận.");

    deliveryMetrics.replaceChildren();
    const metrics = Array.isArray(delivery.metrics) ? delivery.metrics.slice(0, 6) : [];
    for (const metric of metrics) {
      const card = document.createElement("article");
      const label = document.createElement("small");
      const value = document.createElement("strong");
      label.textContent = escapeText(metric.label);
      value.textContent = escapeText(metric.value);
      card.append(label, value);
      deliveryMetrics.append(card);
    }

    deliveryNotes.replaceChildren();
    const notes = Array.isArray(delivery.notes) ? delivery.notes.slice(0, 8) : [];
    if (notes.length) {
      const list = document.createElement("ul");
      for (const note of notes) {
        const item = document.createElement("li");
        item.textContent = escapeText(note);
        list.append(item);
      }
      deliveryNotes.append(list);
    }

    const safeUrl = /^https:\/\//i.test(delivery.url || "") ? delivery.url : "";
    deliveryLink.hidden = !safeUrl;
    if (safeUrl) deliveryLink.href = safeUrl;

    const purchaseKey = `lemienbac_purchase_${order.code}`;
    if (!localStorage.getItem(purchaseKey)) {
      track("purchase", {
        transaction_id: order.code,
        currency: "VND",
        value: PLANS[order.plan].price,
        items: [{ item_id: order.plan, item_name: PLANS[order.plan].label, price: PLANS[order.plan].price, quantity: 1 }]
      });
      localStorage.setItem(purchaseKey, "1");
    }
  }

  function hiddenPost(endpoint, fields) {
    const frameName = `order-frame-${randomToken(5)}`;
    const iframe = document.createElement("iframe");
    iframe.name = frameName;
    iframe.title = "Gửi xác nhận thanh toán";
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

  async function submitPaymentClaim() {
    if (submitting || order.status !== "draft") return;
    if (!BACKEND_ENDPOINT) {
      showPending("Chưa kết nối được kênh xác nhận", "Vui lòng dùng nút Zalo hỗ trợ. Hệ thống chưa gửi email và chưa ghi nhận thanh toán.", true);
      return;
    }

    submitting = true;
    selfConfirmButton.disabled = true;
    selfConfirmButton.textContent = "Đang gửi thông báo…";
    const plan = PLANS[order.plan];

    hiddenPost(BACKEND_ENDPOINT, {
      action: "create",
      order_code: order.code,
      customer_token: order.customerToken,
      plan: order.plan,
      amount: plan.price,
      submitted_at: new Date().toISOString(),
      page_url: window.location.href.slice(0, 1000),
      attribution: JSON.stringify(attribution).slice(0, 3000),
      contact: "",
      website: ""
    });

    order.status = "pending";
    order.submittedAt = new Date().toISOString();
    saveOrder();
    track("payment_submitted", {
      currency: "VND",
      value: plan.price,
      transaction_id: order.code,
      plan: order.plan
    });
    showPending("Đã gửi email báo chủ dịch vụ", "Vui lòng giữ màn hình này. Khi chủ dịch vụ bấm xác nhận, báo cáo sẽ tự mở tại đây.");
    selfConfirmButton.textContent = "Đã báo chuyển khoản";
    startPolling();
    submitting = false;
  }

  function jsonp(params) {
    return new Promise((resolve, reject) => {
      const callbackName = `__leMienBacStatus_${randomToken(6)}`;
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
      // A transient polling failure is retried. It does not change payment state.
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

  async function copyText(text, button) {
    try {
      await navigator.clipboard.writeText(text);
      const previous = button.textContent;
      button.textContent = "Đã sao chép";
      window.setTimeout(() => { button.textContent = previous; }, 1500);
      track("add_payment_info", { currency: "VND", value: PLANS[order.plan].price, payment_type: "bank_transfer" });
    } catch (_) {
      button.textContent = "Không sao chép được";
    }
  }

  document.querySelectorAll("[data-open-checkout]").forEach((button) => {
    button.addEventListener("click", () => openCheckout(button.dataset.plan || "day"));
  });
  modalPlanButtons.forEach((button) => {
    button.addEventListener("click", () => setPlan(button.dataset.modalPlan, { trackSelection: true }));
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
    const plan = PLANS[order.plan];
    copyText(`VPBank\n1128091987\nSố tiền: ${plan.priceText}\nNội dung: ${order.code}`, event.currentTarget);
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

  updateCheckoutState();
  track("view_item", {
    currency: "VND",
    value: PLANS.day.price,
    items: [{ item_id: "day", item_name: PLANS.day.label, price: PLANS.day.price, quantity: 1 }]
  });
})();
