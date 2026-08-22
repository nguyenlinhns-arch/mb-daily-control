// Public endpoint only. Administrative approval secrets must never be stored here.
window.ORDER_CONFIRMATION_ENDPOINT = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec";

// Keep the paid MB_ALL report as the primary mobile conversion.
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

// Current website model: MB_ALL, 31 methods, dynamic daily selection.
(() => {
  "use strict";

  const HOME_TITLE = "MB_ALL hôm nay – 31 phương pháp chọn lọc động";
  const HOME_DESCRIPTION = "Gợi ý số MB_ALL ngày hôm nay: chạy đủ 31 phương pháp bằng dữ liệu khóa đến T−1, đánh giá phong độ 3/5/7/10 ngày, P/L và trạng thái HOT/COLD để chọn số động trước giờ quay.";
  const ZALO_URL = "https://zalo.me/0398696879";
  const SUPPORT_ID = "mball-zalo-support";

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

      [data-mball-payment-card="true"]{
        position:relative!important;
        overflow:hidden!important;
        box-sizing:border-box!important;
        border-color:#edc5c7!important;
        background:linear-gradient(145deg,#fff 0%,#fff7f7 100%)!important;
        box-shadow:0 4px 16px rgba(130,20,27,.06)!important;
      }
      [data-mball-payment-card="true"]::before{
        content:"";
        position:absolute;
        inset:0 0 auto 0;
        height:4px;
        background:linear-gradient(90deg,#a20e15,#d31b22);
      }
      .mball-offer-kicker{
        display:inline-flex;
        align-items:center;
        min-height:25px;
        padding:0 9px;
        border-radius:999px;
        background:#fae8e9;
        color:#a20e15;
        font-size:9.5px;
        font-weight:1000;
        letter-spacing:.07em;
      }
      .mball-offer-title{
        margin:10px 0 6px!important;
        color:#172432!important;
        font-size:22px!important;
        line-height:1.18!important;
      }
      .mball-offer-price{
        display:flex;
        align-items:baseline;
        gap:4px;
        margin:5px 0 10px;
        color:#b11118;
      }
      .mball-offer-price strong{
        font-size:31px;
        line-height:1;
        letter-spacing:-.035em;
      }
      .mball-offer-price span{
        font-size:13px;
        font-weight:900;
      }
      .mball-offer-copy,
      .mball-offer-email{
        margin:0 0 9px!important;
        color:#596875!important;
        font-size:12px!important;
        line-height:1.48!important;
      }
      .mball-offer-email{
        display:flex;
        gap:7px;
        align-items:flex-start;
        padding:9px 10px;
        border:1px solid #ead9da;
        border-radius:10px;
        background:#fff;
        color:#5e4b4d!important;
      }
      .mball-offer-email b{flex:0 0 auto;color:#a20e15}
      .mball-footer-pay-button{
        width:100%;
        min-height:47px;
        margin-top:2px;
        padding:11px 13px;
        border:0;
        border-radius:11px;
        background:linear-gradient(135deg,#981018,#c71921);
        color:#fff;
        font:inherit;
        font-size:11.5px;
        font-weight:1000;
        letter-spacing:.025em;
        cursor:pointer;
        box-shadow:0 8px 20px rgba(151,16,24,.19);
      }
      .mball-footer-pay-button:hover{filter:brightness(1.05)}
      .mball-footer-pay-button:focus-visible{outline:3px solid rgba(196,25,33,.25);outline-offset:3px}

      #${SUPPORT_ID}{
        position:fixed!important;
        right:20px!important;
        bottom:22px!important;
        z-index:2147483000!important;
        width:76px!important;
        height:76px!important;
        box-sizing:border-box!important;
        display:flex!important;
        flex-direction:column!important;
        align-items:center!important;
        justify-content:center!important;
        gap:1px!important;
        padding:0!important;
        border:4px solid #fff!important;
        border-radius:50%!important;
        background:linear-gradient(145deg,#1780ff,#0068ff)!important;
        color:#fff!important;
        text-decoration:none!important;
        text-align:center!important;
        font-size:12px!important;
        font-weight:1000!important;
        line-height:1.05!important;
        box-shadow:0 12px 28px rgba(0,74,190,.32)!important;
        visibility:visible!important;
        opacity:1!important;
        transform:none;
        transition:transform .16s ease,box-shadow .16s ease!important;
      }
      #${SUPPORT_ID}::before{
        content:"Zalo";
        display:block;
        font-size:13px;
        font-weight:1000;
      }
      #${SUPPORT_ID}:hover{
        transform:translateY(-2px)!important;
        box-shadow:0 15px 34px rgba(0,74,190,.4)!important;
      }
      #${SUPPORT_ID}:focus-visible{outline:4px solid rgba(0,104,255,.25);outline-offset:3px}

      @media(max-width:900px){
        .portal-home .mball31-process{grid-template-columns:repeat(2,minmax(0,1fr))!important}
      }
      @media(max-width:700px){
        #${SUPPORT_ID}{
          right:12px!important;
          bottom:72px!important;
          width:66px!important;
          height:66px!important;
          border-width:3px!important;
          font-size:10.5px!important;
        }
        #${SUPPORT_ID}::before{font-size:12px}
        .mball-offer-title{font-size:20px!important}
        .mball-offer-price strong{font-size:28px}
      }
      @media(max-width:620px){
        .portal-home .mball31-process{grid-template-columns:1fr!important}
      }
      @media(prefers-reduced-motion:reduce){
        #${SUPPORT_ID}{transition:none!important}
      }
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

  function normalized(value) {
    return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
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

    setText("h3", "Gợi ý số MB_ALL gồm gì?", block);
    const lead = block.querySelector(":scope > p:not(.lm-ai-history-note)");
    const leadCopy = "Một gợi ý số riêng cho ngày hiện tại, được tạo sau khi khóa dữ liệu T−1 và chạy đủ 31 phương pháp.";
    if (lead && lead.textContent !== leadCopy) lead.textContent = leadCopy;

    const values = [
      ["31 phương pháp độc lập", "Không phụ thuộc vào một công thức duy nhất; toàn bộ hệ thống được chạy trước khi kết luận."],
      ["Chọn lọc động theo ngày", "Đánh giá phong độ gần, P/L và trạng thái HOT/COLD rồi chấm trực tiếp từng số."],
      ["Khóa trước giờ quay", "Gợi ý số chỉ mở sau xác nhận thanh toán và không sửa theo kết quả ngày hiện tại."]
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

  function findAdvertisingCard() {
    const heading = Array.from(document.querySelectorAll("h2,h3,h4,strong,b,p,span"))
      .find((node) => normalized(node.textContent).includes("đặt banner quảng cáo"));
    if (!heading) return null;

    let current = heading.parentElement;
    for (let depth = 0; current && depth < 7; depth += 1, current = current.parentElement) {
      const classes = String(current.className || "");
      if (/(^|\s|[-_])(card|box|support|advert|contact)(\s|[-_]|$)/i.test(classes)) return current;
    }
    return heading.closest("article") || heading.parentElement;
  }

  function openCheckoutFromNewButton(button) {
    const existing = Array.from(document.querySelectorAll("[data-open-checkout]"))
      .find((node) => node !== button && !node.disabled);
    if (existing) {
      existing.click();
      return;
    }

    const checkout = document.getElementById("checkout");
    if (checkout) {
      checkout.hidden = false;
      document.body.classList.add("modal-open", "checkout-open");
      document.getElementById("checkout-close")?.focus();
      return;
    }
    window.location.assign("/?checkout=1");
  }

  function rewriteAdvertisingCard() {
    const card = findAdvertisingCard();
    if (!card || card.dataset.mballPaymentCard === "true") return;

    card.dataset.mballPaymentCard = "true";
    card.innerHTML = `
      <span class="mball-offer-kicker">GỢI Ý SỐ MB_ALL</span>
      <h3 class="mball-offer-title">Thanh toán nhận gợi ý số</h3>
      <div class="mball-offer-price"><strong>30.000đ</strong><span>/ ngày</span></div>
      <p class="mball-offer-copy">Thanh toán một lần để nhận gợi ý số đã khóa cho đúng ngày hiện tại.</p>
      <p class="mball-offer-email"><b>✉</b><span>Sau khi chuyển khoản, bấm gửi xác nhận. Hệ thống gửi email để chủ dịch vụ kiểm tra giao dịch và mở gợi ý số.</span></p>
      <button class="mball-footer-pay-button" type="button" data-mball-footer-checkout>THANH TOÁN NHẬN GỢI Ý SỐ</button>
    `;

    const button = card.querySelector("[data-mball-footer-checkout]");
    button?.addEventListener("click", () => {
      try {
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({
          event: "mball_footer_checkout_click",
          value: 30000,
          currency: "VND",
          product: "daily_number_suggestion"
        });
      } catch (_) {}
      openCheckoutFromNewButton(button);
    });
  }

  function ensureZaloSupport() {
    let support = document.getElementById(SUPPORT_ID);
    const legacy = document.querySelector("#floating-zalo,.floating-zalo");

    if (!support && legacy) support = legacy;
    if (!support) {
      support = document.createElement("a");
      document.body.appendChild(support);
    }

    support.id = SUPPORT_ID;
    support.className = "mball-zalo-support-button";
    support.href = ZALO_URL;
    support.target = "_blank";
    support.rel = "noopener noreferrer";
    support.setAttribute("aria-label", "Hỗ trợ qua Zalo 0398696879");
    if (support.textContent !== "Hỗ trợ") support.textContent = "Hỗ trợ";

    if (support.dataset.mballZaloBound !== "true") {
      support.dataset.mballZaloBound = "true";
      support.addEventListener("click", () => {
        try {
          window.dataLayer = window.dataLayer || [];
          window.dataLayer.push({
            event: "generate_lead",
            method: "zalo_support",
            phone: "0398696879"
          });
        } catch (_) {}
      });
    }
  }

  function rewriteCheckoutText() {
    replaceText(document.querySelector("#checkout"), [
      ["2 cặp 4SO · 4 đầu ra xếp hạng · Top 3 và hồ sơ nguồn", "Gợi ý số MB_ALL đã khóa · dữ liệu T−1"],
      ["4 số được chia thành 2 cặp theo thứ tự xếp hạng.", "Gợi ý số MB_ALL chỉ mở sau khi giao dịch được xác nhận."],
      ["Đang tải kết luận 4SO", "Đang tải gợi ý số MB_ALL"],
      ["Kết luận 4SO", "Gợi ý số MB_ALL"],
      ["kết luận 4SO", "gợi ý số MB_ALL"],
      ["Bản phân tích AI", "Gợi ý số MB_ALL"],
      ["bản phân tích AI", "gợi ý số MB_ALL"],
      ["Báo cáo dữ liệu AI", "Gợi ý số MB_ALL"],
      ["4SO ngày", "MB_ALL ngày"]
    ]);

    const instruction = document.querySelector(".zalo-instruction");
    const instructionCopy = "Sau khi chuyển khoản, bấm nút dưới đây. Hệ thống gửi email xác nhận để chủ dịch vụ kiểm tra giao dịch và mở gợi ý số.";
    if (instruction && instruction.textContent !== instructionCopy) instruction.textContent = instructionCopy;

    const confirm = document.getElementById("payment-self-confirm");
    if (confirm && !confirm.disabled && confirm.textContent !== "TÔI ĐÃ CHUYỂN KHOẢN – GỬI EMAIL XÁC NHẬN") {
      confirm.textContent = "TÔI ĐÃ CHUYỂN KHOẢN – GỬI EMAIL XÁC NHẬN";
    }

    const pendingTitle = document.getElementById("pending-title");
    const pendingCopy = document.getElementById("pending-copy");
    if (pendingTitle && /đã gửi|đối soát/i.test(pendingTitle.textContent || "")) {
      pendingTitle.textContent = "Đã gửi email xác nhận thanh toán";
    }
    if (pendingCopy && /chờ|quay lại|tải lại|xác nhận/i.test(pendingCopy.textContent || "")) {
      pendingCopy.textContent = "Chủ dịch vụ sẽ kiểm tra giao dịch qua email; gợi ý số tự mở sau khi được xác nhận.";
    }
  }

  function rewriteJsonLd() {
    const replacements = [
      ["Báo cáo dữ liệu AI ngày hôm nay", "Gợi ý số MB_ALL ngày hôm nay"],
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

  function applyHomepageCopy() {
    if (!isHomepage()) return;
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
      `Gợi ý cho ngày ${reportDate}. Dữ liệu khóa đến ${lockDate}; số được khóa trước giờ quay và không sửa theo kết quả ngày hiện tại.`
    );
    setText(".simple-hero-offer small", "GỢI Ý SỐ MB_ALL HÔM NAY");
    setText(".simple-hero-offer span", "31 phương pháp · Chấm HOT/COLD · Chọn số động theo ngày");

    setText(".portal-kicker", "MB_ALL · 31 PHƯƠNG PHÁP");
    setHtml(".portal-hero h1", "MB_ALL – 31 phương pháp<br>chọn lọc động mỗi ngày");
    setText(
      ".portal-lead",
      "Mỗi ngày MB_ALL chạy đủ 31 phương pháp bằng dữ liệu đến T−1, đánh giá hiệu quả gần theo 3–5–7–10 ngày, P/L, số nháy và trạng thái HOT/COLD, rồi chấm điểm trực tiếp từng số. Không cố định phương pháp và không cố định số lượng số được chọn."
    );
    setText(".portal-paid-card small", "GỢI Ý SỐ MB_ALL");
    setText(".portal-paid-card h2", "Gợi ý hôm nay đã khóa");
    setText(".portal-paid-card button", "MỞ GỢI Ý SỐ · 30.000Đ");
    setText(".portal-paid-note", "Gợi ý số cuối cùng chỉ mở sau khi giao dịch được xác nhận qua email.");

    const sampleLink = document.querySelector(".sample-link");
    if (sampleLink) {
      if (sampleLink.textContent !== "Cách MB_ALL hoạt động") sampleLink.textContent = "Cách MB_ALL hoạt động";
      if (sampleLink.getAttribute("href") !== "/gioi-thieu/") sampleLink.setAttribute("href", "/gioi-thieu/");
    }

    setText(".buy-simple .eyebrow", "THANH TOÁN NHẬN GỢI Ý SỐ");
    setText(
      ".buy-copy",
      "Thanh toán 30.000đ cho một ngày để mở gợi ý số MB_ALL đã khóa. Sau khi chuyển khoản, hệ thống gửi email để chủ dịch vụ kiểm tra và xác nhận giao dịch."
    );
    setText(".site-header [data-open-checkout]", "Nhận gợi ý số");
    setText(".hero [data-open-checkout]", "Nhận gợi ý số hôm nay");
    setText(".portal-buy [data-open-checkout]", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ");
    setText(".lm-ai-sticky", "NHẬN GỢI Ý SỐ · 30.000Đ");

    rebuildMethodSection();
    rewriteCommerceProof();
    rewriteAdvertisingCard();
    rewriteJsonLd();

    replaceText(document.body, [
      ["7 lớp báo cáo", "31 phương pháp MB_ALL"],
      ["7 lớp phân tích", "31 phương pháp MB_ALL"],
      ["phân tích qua 7 lớp", "chạy qua 31 phương pháp"],
      ["Xem mẫu 4SO", "Cách MB_ALL hoạt động"]
    ]);

    document.body.dataset.mballModel = "31-method-dynamic-selection";
  }

  function refresh() {
    ensureStyle();
    ensureZaloSupport();
    rewriteCheckoutText();
    applyHomepageCopy();
  }

  const start = () => {
    refresh();
    window.setTimeout(refresh, 250);
    window.setTimeout(refresh, 900);
    window.setTimeout(refresh, 1800);
    window.setTimeout(refresh, 3200);

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
// slots. Only after owner approval do we collapse that duplicate payload.
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
        if (rank && rank.textContent !== "GỢI Ý SỐ MB ALL") rank.textContent = "GỢI Ý SỐ MB ALL";
        const pairWrap = view.querySelector("#delivery-pairs, [data-delivery-pairs]");
        if (pairWrap) pairWrap.setAttribute("aria-label", `Gợi ý số MB ALL: ${first.join(", ")}`);
        view.dataset.mballCollapsed = "true";
      }
    }

    const reportDate = String(document.body?.dataset?.reportDate || "").trim();
    const title = view.querySelector("#delivery-title, h2, h3, [data-delivery-title]");
    const wantedTitle = reportDate ? `Gợi ý số MB ALL ngày ${reportDate}` : "Gợi ý số MB ALL hôm nay";
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
