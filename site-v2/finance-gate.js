(() => {
  "use strict";

  const OFFER = {
    id: "vpbank-vay-online",
    merchant: "VPBank",
    url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
  };

  const SESSION_KEY = "lm_finance_latest_results_gate_v4";
  const EARLY_DELAY_MS = 12000;
  const EARLY_SCROLL_PX = 120;
  let observer = null;
  let earlyTimer = null;
  let previousFocus = null;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      page_path: window.location.pathname,
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: OFFER.id,
      merchant: OFFER.merchant,
      placement: "after_latest_results_gate",
      ...extra
    });
  }

  function sessionGet(key) {
    try { return sessionStorage.getItem(key); } catch (_) { return null; }
  }

  function sessionSet(key, value) {
    try { sessionStorage.setItem(key, value); } catch (_) {}
  }

  function gateConsumed() { return sessionGet(SESSION_KEY) === "shown"; }

  function checkoutIsOpen() {
    const checkout = document.getElementById("checkout");
    return Boolean(checkout && checkout.hidden === false);
  }

  function stopTriggers() {
    observer?.disconnect();
    observer = null;
    if (earlyTimer) {
      window.clearTimeout(earlyTimer);
      earlyTimer = null;
    }
  }

  function findResultsAnchor() {
    const resultCard = document.querySelector(".portal-result-card");
    if (resultCard) return resultCard.closest(".portal-section") || resultCard;

    const resultSection = [...document.querySelectorAll(".portal-section, section")].find((section) => {
      const heading = section.querySelector(".portal-section-title h2, h2");
      return heading && /27\s+mã\s+kỳ\s+gần\s+nhất/i.test(heading.textContent || "");
    });
    if (resultSection) return resultSection;

    return document.querySelector(".portal-hero") || document.querySelector("main") || null;
  }

  function addStyle() {
    if (document.getElementById("lm-finance-gate-v4-style")) return;
    const style = document.createElement("style");
    style.id = "lm-finance-gate-v4-style";
    style.textContent = `
      #lm-finance-gate-sentinel{width:100%;height:1px;pointer-events:none}
      body.lm-finance-gate-open{overflow:hidden!important;overscroll-behavior:none}
      .lm-finance-gate{position:fixed;inset:0;z-index:180;display:flex;align-items:center;justify-content:center;padding:18px;background:rgba(8,18,27,.72);backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px)}
      .lm-finance-sheet{position:relative;width:min(100%,560px);max-height:calc(100vh - 36px);max-height:calc(100svh - 36px);overflow:auto;overscroll-behavior:contain;border:1px solid rgba(255,255,255,.65);border-radius:24px;background:#fff;box-shadow:0 28px 90px rgba(0,0,0,.34);animation:lmFinanceFade .22s ease-out both}
      .lm-finance-handle{display:none;width:42px;height:5px;margin:9px auto 2px;border-radius:999px;background:#d5dadd}
      .lm-finance-close-x{position:absolute;top:13px;right:13px;z-index:4;width:38px;height:38px;border:0;border-radius:999px;background:rgba(23,36,46,.08);color:#21333f;font-size:24px;line-height:1;cursor:pointer;display:grid;place-items:center}
      .lm-finance-head{padding:25px 24px 16px;background:linear-gradient(180deg,#f3fbf8 0%,#fff 100%)}
      .lm-finance-badge{display:inline-flex;align-items:center;min-height:25px;padding:5px 9px;border-radius:999px;background:#e5f7f0;color:#08745d;font-size:9px;font-weight:1000;letter-spacing:.07em;text-transform:uppercase}
      .lm-finance-head h2{max-width:440px;margin:11px 44px 0 0;color:#172c36;font-size:28px;line-height:1.08;letter-spacing:-.025em}
      .lm-finance-lead{margin:8px 0 0;color:#60727b;font-size:12px;line-height:1.45}
      .lm-finance-rate{display:flex;align-items:flex-end;gap:5px;margin-top:15px;color:#05765e}
      .lm-finance-rate small{padding-bottom:4px;color:#60736d;font-size:11px;font-weight:800}
      .lm-finance-rate strong{font-size:38px;line-height:.95;letter-spacing:-.04em}
      .lm-finance-rate span{padding-bottom:4px;font-size:12px;font-weight:900}
      .lm-finance-body{padding:0 24px 22px}
      .lm-finance-benefits{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0 0 16px;padding:0;list-style:none}
      .lm-finance-benefits li{display:flex;min-width:0;min-height:76px;flex-direction:column;align-items:center;justify-content:center;padding:10px 7px;border:1px solid #e4ece8;border-radius:14px;background:#f8fbfa;text-align:center}
      .lm-finance-benefits b{display:block;color:#08745d;font-size:18px;line-height:1}
      .lm-finance-benefits span{display:block;margin-top:5px;color:#50636c;font-size:10px;font-weight:800;line-height:1.25}
      .lm-finance-cta{display:flex;width:100%;min-height:58px;align-items:center;justify-content:center;border-radius:15px;background:linear-gradient(135deg,#f57b16,#ff9500);color:#fff!important;text-decoration:none!important;font-size:15px;font-weight:1000;letter-spacing:.015em;box-shadow:0 12px 26px rgba(245,123,22,.24);touch-action:manipulation}
      .lm-finance-cta:active{transform:translateY(1px)}
      .lm-finance-close{width:100%;min-height:49px;margin-top:9px;border:1px solid #dce5e1;border-radius:13px;background:#fff;color:#42565e;font-size:13px;font-weight:900;cursor:pointer;touch-action:manipulation}
      .lm-finance-note{display:block;margin:9px auto 0;max-width:430px;color:#8a989e;text-align:center;font-size:9px;line-height:1.4}
      @keyframes lmFinanceFade{from{opacity:0;transform:translateY(8px) scale(.99)}to{opacity:1;transform:none}}
      @keyframes lmFinanceSheetUp{from{opacity:.55;transform:translateY(28px)}to{opacity:1;transform:none}}
      @media(max-width:700px){
        .lm-finance-gate{align-items:flex-end;justify-content:center;padding:0;background:rgba(8,18,27,.66)}
        .lm-finance-sheet{width:100%;max-width:none;max-height:88vh;max-height:88svh;border:0;border-radius:24px 24px 0 0;padding-bottom:max(10px,env(safe-area-inset-bottom));animation:lmFinanceSheetUp .25s cubic-bezier(.2,.8,.2,1) both}
        .lm-finance-handle{display:block}
        .lm-finance-close-x{top:12px;right:12px;width:36px;height:36px;background:#eef2f1;font-size:22px}
        .lm-finance-head{padding:13px 16px 13px;background:#fff}
        .lm-finance-badge{min-height:23px;padding:4px 8px;font-size:8.5px}
        .lm-finance-head h2{margin:9px 42px 0 0;font-size:24px;line-height:1.08}
        .lm-finance-lead{margin-top:6px;font-size:11px}
        .lm-finance-rate{margin-top:11px;gap:4px}
        .lm-finance-rate small{font-size:10px;padding-bottom:3px}
        .lm-finance-rate strong{font-size:34px}
        .lm-finance-rate span{font-size:11px;padding-bottom:3px}
        .lm-finance-body{padding:0 16px 8px}
        .lm-finance-benefits{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-bottom:12px}
        .lm-finance-benefits li{min-height:66px;padding:8px 5px;border-radius:12px}
        .lm-finance-benefits b{font-size:16px}
        .lm-finance-benefits span{margin-top:4px;font-size:9px;line-height:1.2}
        .lm-finance-cta{min-height:56px;border-radius:14px;font-size:14px}
        .lm-finance-close{min-height:46px;margin-top:8px;border-radius:12px;font-size:12px}
        .lm-finance-note{margin-top:7px;font-size:8.5px;line-height:1.35}
      }
      @media(max-width:370px){
        .lm-finance-head h2{font-size:22px}
        .lm-finance-rate strong{font-size:31px}
        .lm-finance-benefits li{min-height:62px;padding:7px 3px}
        .lm-finance-benefits span{font-size:8.5px}
      }
      @media(prefers-reduced-motion:reduce){.lm-finance-gate{backdrop-filter:none;-webkit-backdrop-filter:none}.lm-finance-sheet{animation:none}}
    `;
    document.head.appendChild(style);
  }

  function closeGate(reason, track = true) {
    const gate = document.getElementById("lm-finance-gate");
    if (!gate) return;
    gate.remove();
    document.body.classList.remove("lm-finance-gate-open");
    document.removeEventListener("keydown", onKeydown);
    if (track) emit("affiliate_finance_gate_close", { trigger: reason });
    if (previousFocus && typeof previousFocus.focus === "function") previousFocus.focus({ preventScroll: true });
    previousFocus = null;
  }

  function onKeydown(event) {
    if (event.key === "Escape") closeGate("escape");
  }

  function showGate(trigger) {
    if (gateConsumed() || checkoutIsOpen() || document.getElementById("lm-finance-gate") || document.visibilityState !== "visible") return;

    stopTriggers();
    sessionSet(SESSION_KEY, "shown");
    addStyle();
    previousFocus = document.activeElement;

    const gate = document.createElement("div");
    gate.id = "lm-finance-gate";
    gate.className = "lm-finance-gate";
    gate.setAttribute("role", "dialog");
    gate.setAttribute("aria-modal", "true");
    gate.setAttribute("aria-labelledby", "lm-finance-title");
    gate.setAttribute("aria-describedby", "lm-finance-desc");
    gate.innerHTML = `
      <div class="lm-finance-sheet">
        <div class="lm-finance-handle" aria-hidden="true"></div>
        <button class="lm-finance-close-x" type="button" aria-label="Đóng quảng cáo">×</button>
        <div class="lm-finance-head">
          <span class="lm-finance-badge">Ưu đãi tài chính · VPBank</span>
          <h2 id="lm-finance-title">Vay tiền mặt online nhanh</h2>
          <p class="lm-finance-lead" id="lm-finance-desc">Đăng ký online, xét duyệt theo hồ sơ</p>
          <div class="lm-finance-rate"><small>Lãi suất từ</small><strong>1,2%</strong><span>/tháng</span></div>
        </div>
        <div class="lm-finance-body">
          <ul class="lm-finance-benefits" aria-label="Thông tin chính">
            <li><b>100%</b><span>Đăng ký online</span></li>
            <li><b>12–60</b><span>Tháng kỳ hạn</span></li>
            <li><b>0</b><span>Tài sản thế chấp</span></li>
          </ul>
          <a class="lm-finance-cta" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">VAY TIỀN NHANH ONLINE</a>
          <button class="lm-finance-close" type="button">Đóng để xem tiếp</button>
          <span class="lm-finance-note">Liên kết tài trợ qua ACCESSTRADE. Điều kiện vay theo VPBank.</span>
        </div>
      </div>`;

    gate.querySelector(".lm-finance-close-x")?.addEventListener("click", () => closeGate("top_close"));
    gate.querySelector(".lm-finance-close")?.addEventListener("click", () => closeGate("continue_close"));
    gate.querySelector(".lm-finance-cta")?.addEventListener("click", () => {
      emit("affiliate_finance_click", { trigger });
      window.setTimeout(() => closeGate("cta_click", false), 0);
    });

    document.body.appendChild(gate);
    document.body.classList.add("lm-finance-gate-open");
    document.addEventListener("keydown", onKeydown);
    gate.querySelector(".lm-finance-close-x")?.focus({ preventScroll: true });
    emit("affiliate_finance_gate_view", { trigger });
  }

  function installGate() {
    if (window.location.pathname !== "/" || gateConsumed()) return;
    const anchor = findResultsAnchor();
    if (!anchor) return;

    addStyle();
    const sentinel = document.createElement("div");
    sentinel.id = "lm-finance-gate-sentinel";
    sentinel.setAttribute("aria-hidden", "true");
    anchor.insertAdjacentElement("afterend", sentinel);

    earlyTimer = window.setTimeout(() => {
      if (!gateConsumed() && window.scrollY >= EARLY_SCROLL_PX && document.visibilityState === "visible") showGate("engaged_12s");
    }, EARLY_DELAY_MS);

    if (!("IntersectionObserver" in window)) {
      const fallback = () => {
        const rect = sentinel.getBoundingClientRect();
        if (rect.top <= window.innerHeight * 0.92) {
          window.removeEventListener("scroll", fallback);
          showGate("after_latest_results_scroll");
        }
      };
      window.addEventListener("scroll", fallback, { passive: true });
      fallback();
      return;
    }

    observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      showGate("after_latest_results");
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0 });
    observer.observe(sentinel);
  }

  document.addEventListener("DOMContentLoaded", installGate, { once: true });
})();
