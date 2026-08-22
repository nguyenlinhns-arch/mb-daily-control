// Public endpoint only. Administrative approval secrets must never be stored here.
window.ORDER_CONFIRMATION_ENDPOINT = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec";

// Keep the paid AI report as the primary mobile conversion.
try {
  sessionStorage.setItem("lm_shopee_nudge_v1", "shown");
} catch (_) {}

// Privacy-safe first-party attribution. This random browser identifier contains
// no name, phone number, email address or device fingerprint. app.js persists
// the attribution object with each payment claim so Orders can distinguish
// repeat-browser purchases without changing the backend schema.
(() => {
  "use strict";
  const VISITOR_KEY = "lemienbac_visitor_v1";
  const ATTRIBUTION_KEY = "lemienbac_attribution_v1";
  const visitorPattern = /^v1_[0-9a-f]{32}$/;
  const url = new URL(window.location.href);

  function sourceHint(params) {
    const utmSource = String(params.get("utm_source") || "").trim().toLowerCase();
    if (utmSource) return utmSource.slice(0, 80);
    if (params.get("gclid") || params.get("gbraid") || params.get("wbraid")) return "google_ads";
    if (params.get("fbclid")) return "facebook";
    if (params.get("zarsrc") || params.get("gidzl")) return "zalo";
    try {
      if (document.referrer) {
        const ref = new URL(document.referrer);
        if (ref.hostname && ref.hostname !== url.hostname) return ref.hostname.slice(0, 120);
      }
    } catch (_) {}
    return "direct_or_unknown";
  }

  try {
    let visitorId = String(localStorage.getItem(VISITOR_KEY) || "");
    if (!visitorPattern.test(visitorId)) {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      visitorId = `v1_${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
      localStorage.setItem(VISITOR_KEY, visitorId);
    }

    let attribution = {};
    try {
      attribution = JSON.parse(localStorage.getItem(ATTRIBUTION_KEY) || "{}") || {};
    } catch (_) {
      attribution = {};
    }

    const now = new Date().toISOString();
    const hint = sourceHint(url.searchParams);
    attribution.visitor_id = visitorId;
    attribution.visitor_id_version = 1;
    attribution.commerce_measurement = "baseline_v1";
    if (!attribution.first_source_hint) attribution.first_source_hint = hint;
    if (!attribution.first_landing_page) attribution.first_landing_page = `${url.origin}${url.pathname}`;
    if (!attribution.first_seen_at) attribution.first_seen_at = now;
    attribution.last_source_hint = hint;
    attribution.last_landing_page = `${url.origin}${url.pathname}`;
    attribution.last_seen_at = now;

    for (const key of ["fbclid", "zarsrc", "gidzl"]) {
      const value = url.searchParams.get(key);
      if (value) attribution[key] = value.slice(0, 250);
    }
    if (document.referrer) {
      try {
        const ref = new URL(document.referrer);
        if (ref.hostname && ref.hostname !== url.hostname) attribution.referrer_host = ref.hostname.slice(0, 120);
      } catch (_) {}
    }

    localStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(attribution));
  } catch (_) {
    // Storage may be unavailable in strict privacy modes; checkout still works.
  }
})();

// Homepage copy for the current MB_ALL operating model.
// The historical 70% block belongs to the retired 4SO presentation and is
// removed from the public homepage. The paid result remains gated by approval.
(() => {
  "use strict";

  const STYLE_ID = "mball-31-home-style";
  const HOME_TITLE = "MB_ALL hôm nay – 31 phương pháp chọn lọc động";
  const HOME_DESCRIPTION = "Báo cáo MB_ALL ngày hôm nay: chạy đủ 31 phương pháp bằng dữ liệu khóa đến T−1, đánh giá phong độ 3/5/7/10 ngày, P/L và trạng thái HOT/COLD để chọn số động trước giờ quay.";

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = ".historical-proof-section,#statistics.historical-proof-section{display:none!important}";
    document.head.appendChild(style);
  }

  function isHomepage() {
    return document.body?.classList.contains("landing-simple")
      || window.location.pathname === "/"
      || window.location.pathname === "/index.html";
  }

  function setMeta(selector, value) {
    const node = document.querySelector(selector);
    if (node) node.setAttribute("content", value);
  }

  function setText(selector, value) {
    const node = document.querySelector(selector);
    if (node && node.textContent !== value) node.textContent = value;
  }

  function replaceText(root, replacements) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      const parent = node.parentElement;
      if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/.test(parent.tagName)) continue;
      let value = node.nodeValue || "";
      for (const [from, to] of replacements) value = value.split(from).join(to);
      if (value !== node.nodeValue) node.nodeValue = value;
    }
  }

  function rewriteJsonLd() {
    const replacements = [
      ["Báo cáo dữ liệu AI ngày hôm nay", "Báo cáo MB_ALL ngày hôm nay"],
      ["bảy phương pháp phân tích", "31 phương pháp độc lập"],
      ["7 lớp báo cáo", "31 phương pháp MB_ALL"],
      ["7 lớp phân tích", "31 phương pháp MB_ALL"],
      ["4SO AI", "MB_ALL"]
    ];
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        let raw = script.textContent || "";
        for (const [from, to] of replacements) raw = raw.split(from).join(to);
        JSON.parse(raw);
        if (raw !== script.textContent) script.textContent = raw;
      } catch (_) {
        // Keep the original structured data if it cannot be parsed safely.
      }
    }
  }

  function applyHomeCopy() {
    if (!document.body || !isHomepage()) return;

    document.querySelectorAll(".historical-proof-section").forEach((node) => node.remove());
    const statistics = document.getElementById("statistics");
    if (statistics?.querySelector(".historical-rate")) statistics.remove();

    document.title = HOME_TITLE;
    setMeta('meta[name="description"]', HOME_DESCRIPTION);
    setMeta('meta[property="og:title"]', HOME_TITLE);
    setMeta('meta[property="og:description"]', HOME_DESCRIPTION);
    setMeta('meta[name="twitter:title"]', HOME_TITLE);
    setMeta('meta[name="twitter:description"]', HOME_DESCRIPTION);

    const reportDate = String(document.body.dataset.reportDate || "hôm nay");
    const lockDate = String(document.body.dataset.lockDate || "T−1");

    setText(".hero .eyebrow", `MB_ALL · 31 PHƯƠNG PHÁP · NGÀY ${reportDate}`);
    const heading = document.querySelector(".hero h1");
    if (heading) heading.innerHTML = "MB_ALL với 31 phương pháp<br><em>chọn lọc động mỗi ngày</em>";
    setText(
      ".hero-lead",
      "MB_ALL không dùng một công thức cố định. Mỗi ngày hệ thống chạy đủ 31 phương pháp bằng dữ liệu đến hết ngày T−1, đánh giá hiệu quả gần theo 3–5–7–10 ngày cùng P/L, số nháy và trạng thái HOT/COLD, rồi chấm điểm từng số để tạo lựa chọn động."
    );
    setText(
      ".hero-proof-text",
      `Báo cáo cho ngày ${reportDate}. Dữ liệu khóa đến ${lockDate}; kết luận được khóa trước giờ quay và không sửa theo kết quả ngày hiện tại.`
    );
    setText(".simple-hero-offer small", "BÁO CÁO MB_ALL HÔM NAY");
    setText(".simple-hero-offer span", "31 phương pháp · Chấm HOT/COLD · Chọn số động theo ngày");

    const sampleLink = document.querySelector(".sample-link");
    if (sampleLink) {
      sampleLink.textContent = "Cách MB_ALL hoạt động";
      sampleLink.setAttribute("href", "/gioi-thieu/");
    }

    setText(".buy-simple .eyebrow", "MỞ KẾT LUẬN MB_ALL HÔM NAY");
    setText(
      ".buy-copy",
      "Trang công khai giới thiệu nguyên tắc vận hành. Bản trả phí mở kết luận MB_ALL đã khóa cho ngày hôm nay, được tạo sau khi chạy đủ 31 phương pháp và chọn lọc tín hiệu theo trạng thái hiệu quả gần."
    );

    const headerButton = document.querySelector(".site-header [data-open-checkout]");
    if (headerButton) headerButton.textContent = "Mở báo cáo MB_ALL";
    const heroButton = document.querySelector(".hero [data-open-checkout]");
    if (heroButton) heroButton.textContent = "Mở kết luận hôm nay";

    replaceText(document.querySelector("#checkout"), [
      ["Đang tải kết luận 4SO", "Đang tải kết luận MB_ALL"],
      ["kết luận 4SO", "kết luận MB_ALL"],
      ["Kết luận 4SO", "Kết luận MB_ALL"],
      ["4SO ngày", "MB_ALL ngày"]
    ]);
    replaceText(document.body, [
      ["7 lớp báo cáo", "31 phương pháp MB_ALL"],
      ["7 lớp phân tích", "31 phương pháp MB_ALL"],
      ["phân tích qua 7 lớp", "chạy qua 31 phương pháp"],
      ["Xem mẫu 4SO", "Cách MB_ALL hoạt động"]
    ]);

    rewriteJsonLd();
    document.body.dataset.mballModel = "31-method-dynamic-selection";
  }

  ensureStyle();

  const start = () => {
    applyHomeCopy();
    window.setTimeout(applyHomeCopy, 250);
    window.setTimeout(applyHomeCopy, 900);
    window.setTimeout(applyHomeCopy, 1800);

    let queued = false;
    const observer = new MutationObserver(() => {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(() => {
        queued = false;
        applyHomeCopy();
      });
    });
    observer.observe(document.body, { subtree: true, childList: true });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();

// Paid-delivery compatibility layer.
// The existing Apps Script endpoint still returns the legacy two-pair schema.
// During the MB ALL transition, Paid_Report can write the same two-number MB ALL
// result into both legacy slots. Only after the order is approved do we collapse
// that duplicate payload into one paid MB ALL result for the customer.
(() => {
  "use strict";

  function normalizePair(card) {
    if (!card) return [];
    return Array.from(card.querySelectorAll("strong, .delivery-number, .number"))
      .map((node) => String(node.textContent || "").match(/\b\d{2}\b/g) || [])
      .flat()
      .slice(0, 2);
  }

  function collapsePaidDelivery() {
    const view = document.querySelector("#delivery-view, [data-delivery-view]");
    if (!view || view.hidden) return;

    const cards = Array.from(view.querySelectorAll(".delivery-pair, [data-delivery-pair]"));
    if (cards.length < 2) return;

    const first = normalizePair(cards[0]);
    const second = normalizePair(cards[1]);
    if (first.length !== 2 || second.length !== 2 || first.join("|") !== second.join("|")) return;

    cards[1].remove();

    const rank = cards[0].querySelector(
      ".delivery-pair-rank, .delivery-rank, [data-delivery-rank]"
    );
    if (rank) rank.textContent = "SỐ CHỌN MB ALL";

    const reportDate = String(document.body?.dataset?.reportDate || "").trim();
    const title = view.querySelector("#delivery-title, h2, h3, [data-delivery-title]");
    if (title) title.textContent = reportDate ? `Số MB ALL ngày ${reportDate}` : "Số MB ALL hôm nay";

    const pairWrap = view.querySelector("#delivery-pairs, [data-delivery-pairs]");
    if (pairWrap) pairWrap.setAttribute("aria-label", `Số MB ALL: ${first.join(", ")}`);

    view.dataset.mballCollapsed = "true";
  }

  function relabelPublicMethods() {
    for (const node of document.querySelectorAll("h1,h2,h3,p,span")) {
      if (String(node.textContent || "").trim() === "Phương pháp công khai hôm nay") {
        node.textContent = "Phương pháp công khai theo dữ liệu T−1";
      }
    }
  }

  const start = () => {
    relabelPublicMethods();
    collapsePaidDelivery();
    const observer = new MutationObserver(() => {
      collapsePaidDelivery();
      relabelPublicMethods();
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["hidden", "class"]
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
