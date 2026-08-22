// Public endpoint only. Administrative approval secrets must never be stored here.
window.ORDER_CONFIRMATION_ENDPOINT = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec";

// Keep the paid report as the primary mobile conversion.
try {
  sessionStorage.setItem("lm_shopee_nudge_v1", "shown");
} catch (_) {}

// Privacy-safe first-party attribution.
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
    // Checkout still works when storage is unavailable.
  }
})();

// Current homepage model: MB_ALL, 31 methods, dynamic daily selection.
(() => {
  "use strict";

  const HOME_TITLE = "MB_ALL hôm nay – 31 phương pháp chọn lọc động";
  const HOME_DESCRIPTION = "Báo cáo MB_ALL ngày hôm nay: chạy đủ 31 phương pháp bằng dữ liệu khóa đến T−1, đánh giá phong độ 3/5/7/10 ngày, P/L và trạng thái HOT/COLD để chọn số động trước giờ quay.";

  function isHomepage() {
    return document.body?.classList.contains("landing-simple")
      || document.body?.classList.contains("portal-home")
      || window.location.pathname === "/"
      || window.location.pathname === "/index.html";
  }

  function ensureStyle() {
    if (document.getElementById("mball-31-home-style")) return;
    const style = document.createElement("style");
    style.id = "mball-31-home-style";
    style.textContent = `
      .historical-proof-section,
      #statistics.historical-proof-section,
      .portal-home .portal-proof,
      .portal-home .lm-ai-history-note{display:none!important}
      .portal-home .mball31-process{grid-template-columns:repeat(4,minmax(0,1fr))!important}
      .portal-home .mball31-process .portal-method p{margin:0;color:#5f6e79;font-size:12px;line-height:1.5}
      @media(max-width:900px){.portal-home .mball31-process{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
      @media(max-width:620px){.portal-home .mball31-process{grid-template-columns:1fr!important}}
    `;
    document.head.appendChild(style);
  }

  function setText(selector, value, root = document) {
    const node = root.querySelector(selector);
    if (node && node.textContent !== value) node.textContent = value;
  }

  function setHtml(selector, value, root = document) {
    const node = root.querySelector(selector);
    if (node && node.innerHTML !== value) node.innerHTML = value;
  }

  function setMeta(selector, value) {
    const node = document.querySelector(selector);
    if (node && node.getAttribute("content") !== value) node.setAttribute("content", value);
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

  function removeLegacyProof() {
    document.querySelectorAll(".historical-proof-section").forEach((node) => node.remove());
    for (const rate of document.querySelectorAll(".portal-proof-rate,.historical-rate")) {
      const section = rate.closest(".portal-section,.historical-proof-section,section");
      if (section) section.remove();
    }
    document.querySelectorAll(".lm-ai-history-note").forEach((node) => node.remove());
  }

  function rebuildMethodSection() {
    const section = Array.from(document.querySelectorAll(".portal-section")).find((item) => {
      const title = item.querySelector(".portal-section-title h2");
      return /Phương pháp công khai hôm nay|MB_ALL chạy đủ 31 phương pháp/.test(String(title?.textContent || ""));
    });
    if (!section) return;

    setText(".portal-section-title h2", "MB_ALL chạy đủ 31 phương pháp mỗi ngày", section);
    setText(
      ".portal-section-title p",
      "Không dùng một phương pháp cố định. Toàn bộ 31 phương pháp được chạy bằng dữ liệu đến T−1, sau đó mới đánh giá trạng thái và chấm điểm từng số.",
      section
    );

    const grid = section.querySelector(".portal-methods");
    if (grid && grid.dataset.mball31Process !== "true") {
      grid.dataset.mball31Process = "true";
      grid.classList.add("mball31-process");
      grid.innerHTML = `
        <article class="portal-method"><div class="portal-method-head"><b>1. Chạy đủ 31/31</b><span>T−1</span></div><p>Mỗi phương pháp chỉ dùng dữ liệu đã hoàn tất đến ngày liền trước.</p></article>
        <article class="portal-method"><div class="portal-method-head"><b>2. Đánh giá hiệu quả gần</b><span>3–5–7–10</span></div><p>Đối chiếu chuỗi thắng/thua, P/L, số nháy, ROI và độ ổn định gần.</p></article>
        <article class="portal-method"><div class="portal-method-head"><b>3. Chấm HOT/COLD</b><span>THEO SỐ</span></div><p>Tín hiệu tốt cộng điểm, tín hiệu xấu trừ điểm; không chọn theo cảm tính.</p></article>
        <article class="portal-method"><div class="portal-method-head"><b>4. Chọn động và khóa</b><span>PRE-DRAW</span></div><p>Số lượng số thay đổi theo điểm thực tế và được khóa trước giờ quay.</p></article>
      `;
    }

    setText(
      ".portal-disclaimer",
      "Đầu ra từng phương pháp và số cuối cùng không công khai trước thanh toán. Kết quả ngày T không được dùng để sửa lựa chọn ngày T.",
      section
    );
  }

  function rewriteCommerceProof() {
    const block = document.querySelector(".lm-ai-commerce-proof");
    if (!block) return;

    setText("h3", "Báo cáo MB_ALL gồm gì?", block);
    const lead = block.querySelector(":scope > p:not(.lm-ai-history-note)");
    const leadCopy = "Một báo cáo riêng cho ngày hiện tại, được tạo sau khi khóa dữ liệu T−1 và chạy đủ 31 phương pháp.";
    if (lead && lead.textContent !== leadCopy) lead.textContent = leadCopy;

    const values = [
      ["31 phương pháp độc lập", "Không phụ thuộc vào một công thức duy nhất; toàn bộ hệ thống được chạy trước khi kết luận."],
      ["Chọn lọc động theo ngày", "Đánh giá phong độ gần, P/L và trạng thái HOT/COLD rồi chấm trực tiếp từng số."],
      ["Khóa trước giờ quay", "Kết luận chỉ mở sau xác nhận thanh toán và không sửa theo kết quả ngày hiện tại."]
    ];
    Array.from(block.querySelectorAll(".lm-ai-commerce-grid > div")).slice(0, values.length).forEach((card, index) => {
      setText("b", values[index][0], card);
      setText("span", values[index][1], card);
    });

    block.querySelectorAll(".lm-ai-history-note").forEach((node) => node.remove());
    const link = block.querySelector(".lm-ai-secondary-link");
    if (link) {
      if (link.textContent !== "Xem nguyên tắc vận hành MB_ALL →") link.textContent = "Xem nguyên tắc vận hành MB_ALL →";
      if (link.getAttribute("href") !== "/gioi-thieu/") link.setAttribute("href", "/gioi-thieu/");
    }
  }

  function rewriteCheckoutText() {
    replaceText(document.querySelector("#checkout"), [
      ["2 cặp 4SO · 4 đầu ra xếp hạng · Top 3 và hồ sơ nguồn", "Kết luận MB_ALL đã khóa · số chọn cuối cùng · dữ liệu T−1"],
      ["4 số được chia thành 2 cặp theo thứ tự xếp hạng.", "Kết luận MB_ALL chỉ mở sau khi giao dịch được xác nhận."],
      ["Đang tải kết luận 4SO", "Đang tải kết luận MB_ALL"],
      ["Kết luận 4SO", "Kết luận MB_ALL"],
      ["kết luận 4SO", "kết luận MB_ALL"],
      ["Bản phân tích AI", "Báo cáo MB_ALL"],
      ["bản phân tích AI", "báo cáo MB_ALL"],
      ["4SO ngày", "MB_ALL ngày"]
    ]);
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
      } catch (_) {}
    }
  }

  function applyHomeCopy() {
    if (!document.body || !isHomepage()) return;
    ensureStyle();
    removeLegacyProof();

    document.title = HOME_TITLE;
    setMeta('meta[name="description"]', HOME_DESCRIPTION);
    setMeta('meta[property="og:title"]', HOME_TITLE);
    setMeta('meta[property="og:description"]', HOME_DESCRIPTION);
    setMeta('meta[name="twitter:title"]', HOME_TITLE);
    setMeta('meta[name="twitter:description"]', HOME_DESCRIPTION);

    const reportDate = String(document.body.dataset.reportDate || "hôm nay");
    const lockDate = String(document.body.dataset.lockDate || "T−1");

    setText(".hero .eyebrow", `MB_ALL · 31 PHƯƠNG PHÁP · NGÀY ${reportDate}`);
    setHtml(".hero h1", "MB_ALL với 31 phương pháp<br><em>chọn lọc động mỗi ngày</em>");
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

    setText(".portal-kicker", "MB_ALL · 31 PHƯƠNG PHÁP");
    setHtml(".portal-hero h1", "MB_ALL – 31 phương pháp<br>chọn lọc động mỗi ngày");
    setText(
      ".portal-lead",
      "Mỗi ngày MB_ALL chạy đủ 31 phương pháp bằng dữ liệu đến T−1, đánh giá hiệu quả gần theo 3–5–7–10 ngày, P/L, số nháy và trạng thái HOT/COLD, rồi chấm điểm trực tiếp từng số. Không cố định phương pháp và không cố định số lượng số được chọn."
    );
    setText(".portal-paid-card small", "MB_ALL · BÁO CÁO RIÊNG");
    setText(".portal-paid-card h2", "Kết luận hôm nay đã khóa");
    setText(".portal-paid-card button", "MỞ KẾT LUẬN MB_ALL – 30.000Đ");
    setText(".portal-paid-note", "Số cuối cùng chỉ mở sau khi giao dịch được xác nhận.");

    const sampleLink = document.querySelector(".sample-link");
    if (sampleLink) {
      if (sampleLink.textContent !== "Cách MB_ALL hoạt động") sampleLink.textContent = "Cách MB_ALL hoạt động";
      if (sampleLink.getAttribute("href") !== "/gioi-thieu/") sampleLink.setAttribute("href", "/gioi-thieu/");
    }

    setText(".buy-simple .eyebrow", "MỞ KẾT LUẬN MB_ALL HÔM NAY");
    setText(
      ".buy-copy",
      "Trang công khai giới thiệu nguyên tắc vận hành. Bản trả phí mở kết luận MB_ALL đã khóa cho ngày hôm nay, được tạo sau khi chạy đủ 31 phương pháp và chọn lọc tín hiệu theo trạng thái hiệu quả gần."
    );
    setText(".site-header [data-open-checkout]", "Mở báo cáo MB_ALL");
    setText(".hero [data-open-checkout]", "Mở kết luận hôm nay");
    setText(".portal-buy [data-open-checkout]", "MỞ KẾT LUẬN MB_ALL – 30.000Đ");
    setText(".lm-ai-sticky", "MỞ BÁO CÁO MB_ALL · 30.000Đ");

    rebuildMethodSection();
    rewriteCommerceProof();
    rewriteCheckoutText();
    rewriteJsonLd();

    replaceText(document.body, [
      ["7 lớp báo cáo", "31 phương pháp MB_ALL"],
      ["7 lớp phân tích", "31 phương pháp MB_ALL"],
      ["phân tích qua 7 lớp", "chạy qua 31 phương pháp"],
      ["Xem mẫu 4SO", "Cách MB_ALL hoạt động"]
    ]);

    document.body.dataset.mballModel = "31-method-dynamic-selection";
  }

  const start = () => {
    applyHomeCopy();
    window.setTimeout(applyHomeCopy, 250);
    window.setTimeout(applyHomeCopy, 900);
    window.setTimeout(applyHomeCopy, 1800);

    document.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target?.closest("[data-open-checkout],#payment-self-confirm")) return;
      window.setTimeout(rewriteCheckoutText, 0);
      window.setTimeout(rewriteCheckoutText, 250);
      window.setTimeout(rewriteCheckoutText, 900);
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }

  window.MB_ALL_REWRITE_CHECKOUT = rewriteCheckoutText;
})();

// Paid-delivery compatibility layer.
// Paid_Report can write the same two-number MB_ALL result into both legacy
// slots. Only after approval do we collapse that duplicate payload.
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
    if (cards.length >= 2) {
      const first = normalizePair(cards[0]);
      const second = normalizePair(cards[1]);
      if (first.length === 2 && second.length === 2 && first.join("|") === second.join("|")) {
        cards[1].remove();
        const rank = cards[0].querySelector(".delivery-pair-rank, .delivery-rank, [data-delivery-rank]");
        if (rank && rank.textContent !== "SỐ CHỌN MB ALL") rank.textContent = "SỐ CHỌN MB ALL";
        const pairWrap = view.querySelector("#delivery-pairs, [data-delivery-pairs]");
        if (pairWrap) pairWrap.setAttribute("aria-label", `Số MB ALL: ${first.join(", ")}`);
        view.dataset.mballCollapsed = "true";
      }
    }

    const reportDate = String(document.body?.dataset?.reportDate || "").trim();
    const title = view.querySelector("#delivery-title, h2, h3, [data-delivery-title]");
    const wantedTitle = reportDate ? `Số MB ALL ngày ${reportDate}` : "Số MB ALL hôm nay";
    if (title && title.textContent !== wantedTitle) title.textContent = wantedTitle;
  }

  function relabelPublicMethods() {
    for (const node of document.querySelectorAll("h1,h2,h3,p,span")) {
      if (String(node.textContent || "").trim() === "Phương pháp công khai hôm nay") {
        node.textContent = "MB_ALL chạy đủ 31 phương pháp mỗi ngày";
      }
    }
  }

  const refresh = () => {
    collapsePaidDelivery();
    relabelPublicMethods();
    if (typeof window.MB_ALL_REWRITE_CHECKOUT === "function") window.MB_ALL_REWRITE_CHECKOUT();
  };

  const start = () => {
    refresh();
    const observer = new MutationObserver(refresh);
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
