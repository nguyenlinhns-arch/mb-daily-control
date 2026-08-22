// Public website runtime configuration for the MB ALL frozen output.
window.ORDER_CONFIRMATION_ENDPOINT = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec";

try {
  sessionStorage.setItem("lm_shopee_nudge_v1", "shown");
} catch (_) {}

// Privacy-safe first-party attribution retained from the production website.
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
    // Storage can be unavailable in strict privacy modes; the public page still works.
  }
})();

window.MB_ALL_PUBLIC_CURRENT = Object.freeze({
  targetDate: "22/08/2026",
  dataLock: "21/08/2026",
  frozenAt: "00:50 ngày 22/08/2026",
  status: "PRE_DRAW_FROZEN_KEP5OF5",
  finalNumbers: ["98", "89"],
  methods: [
    ["A1 Exact", "98", "ACTIVE"],
    ["X2 RBK Exact", "A0", "A0"],
    ["X3 Profit 30-34", "18, 69, 20", "ACTIVE"],
    ["X3 Growth 32-34", "18, 69, 20", "RETIRED ALIAS · NO VOTE"],
    ["D1 KNN730/10", "78, 87", "ACTIVE"],
    ["BLEND60_G025 Pair", "05, 50", "ACTIVE"],
    ["R4268", "73", "ACTIVE"],
    ["MB_2SO_V1 / P0072", "05, 50", "ACTIVE"],
    ["MB_4SO_V1", "05, 50, 06, 60", "ACTIVE"],
    ["4SO AntiStick Repeat3", "05, 50, 06, 60", "ACTIVE"],
    ["4SO AntiStick Miss3", "05, 50, 06, 60", "ACTIVE"],
    ["3SOT8_A1G2", "98, 05, 50", "ACTIVE"],
    ["Stable6 Core4+HOT60", "05, 50, 06, 60, 34, 54", "ACTIVE"],
    ["ROLL7 5/7", "98, 18, 69, 20", "RETIRED ALIAS · NO VOTE"],
    ["ROLL30 25/30", "98, 18, 69, 20", "ACTIVE"],
    ["KEP Strength", "33", "NO 5/5 CONSENSUS · NO VOTE"],
    ["KEP Grid", "11", "NO 5/5 CONSENSUS · NO VOTE"],
    ["KEP Frequency60", "33", "NO 5/5 CONSENSUS · NO VOTE"],
    ["KEP Gap", "44", "NO 5/5 CONSENSUS · NO VOTE"],
    ["KEP Momentum", "33", "NO 5/5 CONSENSUS · NO VOTE"],
    ["MAX2 V1", "73, 50", "ACTIVE"],
    ["MAX2 R2 Balanced", "73, 50", "ACTIVE"],
    ["MAX2 R2 HitMax4", "73, 50", "ACTIVE"],
    ["MAX2 R2 Monthly", "73, 50", "ACTIVE"],
    ["MAX2 R4 Vote3 Brake", "73, 50", "ACTIVE"],
    ["V10 Pair2 A1+KNN", "05, 50, 89, 98", "ACTIVE"],
    ["HITMAX K1", "50", "ACTIVE"],
    ["HITMAX K2", "89, 98", "ACTIVE"],
    ["HITMAX K3", "05, 50, 89", "ACTIVE"]
  ]
});

(() => {
  "use strict";
  const current = window.MB_ALL_PUBLIC_CURRENT;

  function addStyles() {
    if (document.getElementById("mb-all-open-style")) return;
    const style = document.createElement("style");
    style.id = "mb-all-open-style";
    style.textContent = `
      #mb-all-open-today{background:linear-gradient(135deg,#7f1d1d,#b91c1c 55%,#dc2626);color:#fff;padding:28px 0 30px;border-bottom:5px solid #fbbf24;box-shadow:0 16px 40px rgba(127,29,29,.24)}
      #mb-all-open-today .mball-wrap{width:min(1120px,calc(100% - 32px));margin:auto}
      #mb-all-open-today .mball-top{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;flex-wrap:wrap}
      #mb-all-open-today .mball-kicker{margin:0 0 8px;font-weight:900;letter-spacing:.12em;font-size:13px;color:#fde68a}
      #mb-all-open-today h1{margin:0;font-size:clamp(28px,5vw,50px);line-height:1.05;color:#fff}
      #mb-all-open-today .mball-meta{margin:10px 0 0;font-size:15px;line-height:1.6;color:#fee2e2}
      #mb-all-open-today .mball-badge{background:#fff;color:#991b1b;border:2px solid #fde68a;border-radius:999px;padding:10px 16px;font-size:13px;font-weight:900}
      #mb-all-open-today .mball-picks{display:grid;grid-template-columns:repeat(2,minmax(0,180px));gap:14px;margin:24px 0 16px}
      #mb-all-open-today .mball-pick{background:#fff;color:#991b1b;border:4px solid #fbbf24;border-radius:22px;min-height:146px;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 12px 28px rgba(0,0,0,.22)}
      #mb-all-open-today .mball-pick small{font-size:13px;font-weight:900;letter-spacing:.1em}
      #mb-all-open-today .mball-pick strong{font-size:clamp(64px,10vw,96px);line-height:.95;letter-spacing:-.06em}
      #mb-all-open-today .mball-support{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:18px}
      #mb-all-open-today .mball-support div{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.28);border-radius:14px;padding:12px 14px;line-height:1.45}
      #mb-all-open-today .mball-support strong{display:block;color:#fde68a}
      #mb-all-open-today details{background:#fff;color:#1f2937;border-radius:16px;overflow:hidden;margin-top:18px}
      #mb-all-open-today summary{cursor:pointer;padding:15px 18px;font-weight:900;color:#991b1b;background:#fff7ed}
      #mb-all-open-today .mball-methods{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border-top:1px solid #e5e7eb}
      #mb-all-open-today .mball-method{display:grid;grid-template-columns:minmax(150px,1fr) minmax(100px,.7fr);gap:10px;padding:11px 14px;border-bottom:1px solid #e5e7eb}
      #mb-all-open-today .mball-method:nth-child(odd){border-right:1px solid #e5e7eb}
      #mb-all-open-today .mball-method b{color:#111827}#mb-all-open-today .mball-method span{text-align:right;font-weight:900;color:#b91c1c}
      #mb-all-open-today .mball-method em{grid-column:1/-1;font-size:11px;font-style:normal;color:#6b7280}
      #mb-all-open-today .mball-note{margin:14px 0 0;font-size:13px;line-height:1.55;color:#fee2e2}
      .mball-public-hidden{display:none!important}
      @media(max-width:680px){#mb-all-open-today{padding:22px 0 24px}#mb-all-open-today .mball-wrap{width:calc(100% - 20px)}#mb-all-open-today .mball-picks{grid-template-columns:1fr 1fr;gap:10px}#mb-all-open-today .mball-pick{min-height:124px;border-radius:18px}#mb-all-open-today .mball-support,#mb-all-open-today .mball-methods{grid-template-columns:1fr}#mb-all-open-today .mball-method:nth-child(odd){border-right:0}}
    `;
    document.head.appendChild(style);
  }

  function methodMarkup() {
    return current.methods.map(([name, numbers, status], index) => `
      <div class="mball-method"><b>${String(index + 1).padStart(2, "0")}. ${name}</b><span>${numbers}</span>${status === "ACTIVE" ? "" : `<em>${status}</em>`}</div>`).join("");
  }

  function install() {
    const main = document.querySelector("main");
    if (!main) return;
    addStyles();
    document.body.dataset.reportDate = current.targetDate;
    document.body.dataset.lockDate = current.dataLock;

    if (!document.getElementById("mb-all-open-today")) {
      const section = document.createElement("section");
      section.id = "mb-all-open-today";
      section.setAttribute("aria-label", "Số MB ALL chốt hôm nay");
      section.innerHTML = `
        <div class="mball-wrap">
          <div class="mball-top"><div><p class="mball-kicker">MB ALL · 29/29 PHƯƠNG PHÁP · ĐÃ MỞ CÔNG KHAI</p><h1>Số chốt ngày ${current.targetDate}</h1><p class="mball-meta">Data Lock: <strong>${current.dataLock}</strong> · Freeze: <strong>${current.frozenAt}</strong><br>Hệ chốt: <strong>V5.0 HOT/COLD · KEP 5/5</strong></p></div><div class="mball-badge">${current.status}</div></div>
          <div class="mball-picks"><div class="mball-pick"><small>TOP 1</small><strong>${current.finalNumbers[0]}</strong></div><div class="mball-pick"><small>TOP 2</small><strong>${current.finalNumbers[1]}</strong></div></div>
          <div class="mball-support"><div><strong>98 · Net Score 2,0</strong>ROLL30 25/30 + V10 Pair2 A1+KNN</div><div><strong>89 · Net Score 2,0</strong>HITMAX K3 + V10 Pair2 A1+KNN</div></div>
          <details><summary>Xem đủ 29/29 đầu ra đã chạy trước khi chốt</summary><div class="mball-methods">${methodMarkup()}</div></details>
          <p class="mball-note">KEP 33/11/44 không đạt đồng thuận 5/5 nên không được tính phiếu. V5.1 shadow = A0; V3 benchmark = 18, 69, 20; V4 benchmark = 78, 87. Bộ 98–89 là output cuối đã khóa, không sửa theo kết quả ngày ${current.targetDate}.</p>
        </div>`;
      main.prepend(section);
    }

    document.querySelectorAll("[data-open-checkout],.buy-simple,.mobile-cta,#checkout").forEach((node) => node.classList.add("mball-public-hidden"));
    document.querySelectorAll(".sample-link").forEach((node) => {
      if (node.textContent !== "MB ALL 29/29") node.textContent = "MB ALL 29/29";
      if (node.getAttribute("href") !== "#mb-all-open-today") node.setAttribute("href", "#mb-all-open-today");
    });
  }

  const start = () => {
    install();
    setTimeout(install, 300);
    setTimeout(install, 1200);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();
})();
