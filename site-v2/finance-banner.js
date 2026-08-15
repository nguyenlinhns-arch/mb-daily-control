(() => {
  "use strict";

  const OFFER = {
    id: "vpbank-vay-online",
    merchant: "VPBank",
    url: "https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D"
  };

  const GATE_SESSION_KEY = "lm_finance_stats_gate_v2";
  const STATS_HEADING = "Thống kê XSMB lô tô và phân tích bằng hệ thống AI";
  let previousFocus = null;
  let observer = null;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event,
      affiliate_network: "ACCESSTRADE",
      affiliate_offer_id: OFFER.id,
      merchant: OFFER.merchant,
      placement: "after_statistics_gate",
      ...extra
    });
  }

  function sessionGet(key) {
    try {
      return sessionStorage.getItem(key);
    } catch (_) {
      return null;
    }
  }

  function sessionSet(key, value) {
    try {
      sessionStorage.setItem(key, value);
    } catch (_) {
      // Session storage may be blocked in strict privacy modes.
    }
  }

  function gateConsumed() {
    return sessionGet(GATE_SESSION_KEY) === "shown";
  }

  function checkoutIsOpen() {
    const checkout = document.getElementById("checkout");
    return Boolean(checkout && checkout.hidden === false);
  }

  function reportDateLabel() {
    const bodyDate = String(document.body?.dataset?.reportDate || "").trim();
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(bodyDate)) return bodyDate;

    const text = document.body?.textContent || "";
    const target = text.match(/\bTarget\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/BÁO CÁO\s+4SO\s+NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i)
      || text.match(/BÁO CÁO\s+NGÀY\s+(\d{2}\/\d{2}\/\d{4})/i);
    if (target) return target[1];

    return new Intl.DateTimeFormat("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
      day: "2-digit",
      month: "2-digit",
      year: "numeric"
    }).format(new Date());
  }

  function applyHomeCopy() {
    if (window.location.pathname !== "/") return;

    const heroTitle = document.querySelector(".portal-hero h1");
    if (heroTitle) heroTitle.textContent = STATS_HEADING;

    const heroLead = document.querySelector(".portal-hero .portal-lead");
    if (heroLead) {
      heroLead.innerHTML = 'Phân tích dữ liệu kỳ gần nhất, tần suất, lô gan, 45 cặp đảo, tra cứu lịch sử và các phương pháp chọn số bằng hệ thống AI với hơn 15 nghìn lượt tính toán mỗi ngày và <strong>nhận gợi ý số ngày hôm nay</strong>';
    }

    const datedTitle = `Nhận gợi ý số ngày hôm nay (${reportDateLabel()})`;
    const paidCard = document.querySelector(".portal-paid-card");
    if (paidCard) {
      const kicker = paidCard.querySelector(":scope > small");
      if (kicker) kicker.remove();
      const title = paidCard.querySelector("h2");
      if (title) title.textContent = datedTitle;
      const button = paidCard.querySelector("[data-open-checkout]");
      if (button) {
        button.textContent = "NHẬN GỢI Ý SỐ";
        button.setAttribute("aria-label", datedTitle);
      }
    }
  }

  function findStatisticsAnchor() {
    const statsSection = [...document.querySelectorAll(".portal-section")].find((section) => {
      const heading = section.querySelector(".portal-section-title h2, h2");
      return heading && /(?:Thống kê XSMB lô tô và phân tích bằng hệ thống AI|Công cụ thống kê XSMB|Trung tâm thống kê XSMB)/i.test(heading.textContent || "");
    });
    if (statsSection) return statsSection;

    const selectors = [
      "details.history-disclosure",
      ".history-disclosure",
      ".portal-quick-grid",
      ".portal-proof",
      ".portal-result-card"
    ];
    for (const selector of selectors) {
      const node = document.querySelector(selector);
      if (node) return node.closest(".portal-section") || node;
    }

    const candidates = [...document.querySelectorAll("section,details")];
    return candidates.find((node) => /Lịch sử đối chiếu trong tháng này/i.test(node.textContent || ""))
      || candidates.find((node) => /Kết quả thực tế/i.test(node.textContent || ""))
      || null;
  }

  function addGateStyle() {
    if (document.getElementById("lm-finance-gate-style")) return;
    const style = document.createElement("style");
    style.id = "lm-finance-gate-style";
    style.textContent = `
      #lm-finance-gate-sentinel{width:100%;height:1px;pointer-events:none}
      body.lm-finance-gate-open{overflow:hidden!important}
      .lm-finance-gate{position:fixed;inset:0;z-index:160;display:grid;place-items:center;padding:18px;background:rgba(4,18,30,.76);backdrop-filter:blur(6px)}
      .lm-finance-gate-card{position:relative;width:min(100%,620px);max-height:calc(100vh - 36px);overflow:auto;border-radius:25px;background:#fff;box-shadow:0 28px 90px rgba(0,0,0,.36)}
      .lm-finance-gate-hero{position:relative;overflow:hidden;padding:29px 25px 26px;background:linear-gradient(135deg,#00634e 0%,#008e6d 62%,#00aa83 100%);color:#fff}
      .lm-finance-gate-hero:after{content:"₫";position:absolute;right:-8px;bottom:-42px;width:155px;height:155px;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.10);color:rgba(255,255,255,.72);font-size:82px;font-weight:900}
      .lm-finance-gate-kicker{display:block;padding-right:100px;color:#d6fff4;font-size:10px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}
      .lm-finance-gate-hero h2{max-width:430px;margin:8px 0 0;color:#fff;font-size:31px;line-height:1.08;letter-spacing:-.025em}
      .lm-finance-gate-rate{display:block;margin-top:13px;color:#fff;font-size:21px;font-weight:1000;line-height:1.2}
      .lm-finance-gate-body{padding:20px 24px 23px}
      .lm-finance-gate-benefits{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:0 0 17px;padding:0;list-style:none}
      .lm-finance-gate-benefits li{min-height:82px;padding:12px 10px;border-radius:13px;background:#f2f8f5;color:#244039;font-size:12px;font-weight:850;line-height:1.4}
      .lm-finance-gate-benefits b{display:block;margin-bottom:5px;color:#00775d;font-size:18px}
      .lm-finance-gate-cta{min-height:58px;display:flex;align-items:center;justify-content:center;border-radius:14px;background:linear-gradient(135deg,#ff7900,#ff9800);color:#fff!important;text-decoration:none!important;font-size:16px;font-weight:1000;box-shadow:0 12px 24px rgba(255,126,0,.28)}
      .lm-finance-gate-close{width:100%;min-height:48px;margin-top:11px;border:1px solid #dbe5e1;border-radius:12px;background:#fff;color:#42544e;font-size:13px;font-weight:900;cursor:pointer}
      .lm-finance-gate-note{display:block;margin-top:9px;text-align:center;color:#8b9893;font-size:9px;line-height:1.4}
      .lm-finance-gate-x{position:absolute;top:13px;right:13px;z-index:3;min-width:64px;height:36px;padding:0 11px;border:1px solid rgba(255,255,255,.48);border-radius:999px;background:rgba(0,0,0,.18);color:#fff;font-size:11px;font-weight:900;cursor:pointer}
      @media(max-width:700px){
        .lm-finance-gate{padding:10px}.lm-finance-gate-card{max-height:calc(100vh - 20px);border-radius:20px}.lm-finance-gate-hero{padding:23px 17px 21px}.lm-finance-gate-kicker{font-size:9px}.lm-finance-gate-hero h2{font-size:25px}.lm-finance-gate-rate{font-size:18px}.lm-finance-gate-body{padding:15px 15px 17px}.lm-finance-gate-benefits{grid-template-columns:1fr;gap:7px}.lm-finance-gate-benefits li{min-height:0;padding:9px 11px;display:flex;align-items:center;gap:8px}.lm-finance-gate-benefits b{display:inline;margin:0;font-size:15px}.lm-finance-gate-cta{min-height:54px;font-size:14px}.lm-finance-gate-close{min-height:46px}
      }
      @media(prefers-reduced-motion:reduce){.lm-finance-gate{backdrop-filter:none}}
    `;
    document.head.appendChild(style);
  }

  function closeGate(reason, track = true) {
    const gate = document.getElementById("lm-finance-gate");
    if (!gate) return;
    gate.remove();
    document.body.classList.remove("lm-finance-gate-open");
    document.removeEventListener("keydown", onGateKeydown);
    if (track) emit("affiliate_finance_gate_close", { trigger: reason });
    if (previousFocus && typeof previousFocus.focus === "function") {
      previousFocus.focus({ preventScroll: true });
    }
    previousFocus = null;
  }

  function onGateKeydown(event) {
    if (event.key === "Escape") closeGate("escape");
  }

  function showGate(trigger) {
    if (
      gateConsumed()
      || checkoutIsOpen()
      || document.getElementById("lm-finance-gate")
      || document.visibilityState !== "visible"
    ) return;

    sessionSet(GATE_SESSION_KEY, "shown");
    addGateStyle();
    previousFocus = document.activeElement;

    const gate = document.createElement("div");
    gate.id = "lm-finance-gate";
    gate.className = "lm-finance-gate";
    gate.setAttribute("role", "dialog");
    gate.setAttribute("aria-modal", "true");
    gate.setAttribute("aria-labelledby", "lm-finance-gate-title");
    gate.innerHTML = `
      <div class="lm-finance-gate-card">
        <button class="lm-finance-gate-x" type="button" aria-label="Đóng quảng cáo">Đóng ×</button>
        <div class="lm-finance-gate-hero">
          <span class="lm-finance-gate-kicker">Ưu đãi tài chính · VPBank</span>
          <h2 id="lm-finance-gate-title">Vay online 100% không cần tài sản thế chấp</h2>
          <span class="lm-finance-gate-rate">Lãi suất từ 1,2%/tháng</span>
        </div>
        <div class="lm-finance-gate-body">
          <ul class="lm-finance-gate-benefits">
            <li><b>100%</b> Đăng ký online</li>
            <li><b>12–60</b> tháng kỳ hạn</li>
            <li><b>0</b> tài sản thế chấp</li>
          </ul>
          <a class="lm-finance-gate-cta" href="${OFFER.url}" target="_blank" rel="sponsored nofollow noopener noreferrer">VAY TIỀN NHANH ONLINE →</a>
          <button class="lm-finance-gate-close" type="button">Đóng quảng cáo để xem tiếp</button>
          <span class="lm-finance-gate-note">Liên kết tài trợ qua ACCESSTRADE · lãi suất và điều kiện thực tế theo hồ sơ/gói vay VPBank.</span>
        </div>
      </div>`;

    gate.querySelector(".lm-finance-gate-x")?.addEventListener("click", () => closeGate("top_close"));
    gate.querySelector(".lm-finance-gate-close")?.addEventListener("click", () => closeGate("continue_close"));
    gate.querySelector(".lm-finance-gate-cta")?.addEventListener("click", () => {
      emit("affiliate_finance_click", { trigger });
      window.setTimeout(() => closeGate("cta_click", false), 0);
    });

    document.body.appendChild(gate);
    document.body.classList.add("lm-finance-gate-open");
    document.addEventListener("keydown", onGateKeydown);
    gate.querySelector(".lm-finance-gate-x")?.focus({ preventScroll: true });
    emit("affiliate_finance_gate_view", { trigger });
  }

  function installGateAfterStatistics() {
    if (window.location.pathname !== "/" || gateConsumed()) return;
    const anchor = findStatisticsAnchor();
    if (!anchor) return;

    addGateStyle();
    const sentinel = document.createElement("div");
    sentinel.id = "lm-finance-gate-sentinel";
    sentinel.setAttribute("aria-hidden", "true");
    anchor.insertAdjacentElement("afterend", sentinel);

    if (!("IntersectionObserver" in window)) {
      const fallback = () => {
        const rect = sentinel.getBoundingClientRect();
        if (rect.top <= window.innerHeight * 0.78) {
          window.removeEventListener("scroll", fallback);
          showGate("after_statistics_scroll");
        }
      };
      window.addEventListener("scroll", fallback, { passive: true });
      fallback();
      return;
    }

    observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer?.disconnect();
      observer = null;
      window.setTimeout(() => showGate("after_statistics"), 180);
    }, { rootMargin: "0px 0px -18% 0px", threshold: 0 });
    observer.observe(sentinel);
  }

  document.addEventListener("DOMContentLoaded", () => {
    applyHomeCopy();
    installGateAfterStatistics();
  }, { once: true });
})();
