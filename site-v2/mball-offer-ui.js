(() => {
  "use strict";

  const ZALO_URL = "https://zalo.me/0398696879";
  const STYLE_ID = "mball-paid-offer-style-v1";
  const SUPPORT_ID = "mball-zalo-support";

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      [data-mball-payment-card="true"]{
        position:relative;
        overflow:hidden;
        border-color:#f0b7ba!important;
        background:linear-gradient(145deg,#fff 0%,#fff7f7 100%)!important;
      }
      [data-mball-payment-card="true"]::before{
        content:"";
        position:absolute;
        inset:0 0 auto 0;
        height:4px;
        background:linear-gradient(90deg,#a30f16,#d71920);
      }
      .mball-offer-kicker{
        display:inline-flex;
        align-items:center;
        min-height:26px;
        padding:0 9px;
        border-radius:999px;
        background:#fce8e9;
        color:#a30f16;
        font-size:10px;
        font-weight:1000;
        letter-spacing:.07em;
      }
      .mball-offer-title{
        margin:11px 0 7px!important;
        color:#172432!important;
        font-size:24px!important;
        line-height:1.15!important;
      }
      .mball-offer-price{
        display:flex;
        align-items:baseline;
        gap:4px;
        margin:4px 0 9px;
        color:#b11118;
      }
      .mball-offer-price strong{
        font-size:32px;
        line-height:1;
        letter-spacing:-.03em;
      }
      .mball-offer-price span{
        font-size:14px;
        font-weight:900;
      }
      .mball-offer-copy,
      .mball-offer-email{
        margin:0 0 9px!important;
        color:#596875!important;
        font-size:12px!important;
        line-height:1.5!important;
      }
      .mball-offer-email{
        display:flex;
        gap:7px;
        align-items:flex-start;
        padding:9px 10px;
        border:1px solid #ead8d9;
        border-radius:10px;
        background:#fff;
        color:#5e4b4d!important;
      }
      .mball-offer-email b{
        flex:0 0 auto;
        color:#a30f16;
      }
      .mball-footer-pay-button{
        width:100%;
        min-height:48px;
        margin-top:3px;
        padding:11px 14px;
        border:0;
        border-radius:12px;
        background:linear-gradient(135deg,#971018,#c71921);
        color:#fff;
        font:inherit;
        font-size:12px;
        font-weight:1000;
        letter-spacing:.03em;
        cursor:pointer;
        box-shadow:0 8px 20px rgba(151,16,24,.2);
      }
      .mball-footer-pay-button:hover{filter:brightness(1.05)}
      .mball-footer-pay-button:focus-visible{
        outline:3px solid rgba(196,25,33,.26);
        outline-offset:3px;
      }
      #${SUPPORT_ID}{
        position:fixed;
        right:20px;
        bottom:22px;
        z-index:2147483000;
        width:76px;
        height:76px;
        box-sizing:border-box;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        gap:1px;
        border:4px solid #fff;
        border-radius:50%;
        background:linear-gradient(145deg,#1677ff,#0068ff);
        color:#fff!important;
        text-decoration:none!important;
        text-align:center;
        font-size:12px;
        font-weight:1000;
        line-height:1.05;
        box-shadow:0 12px 28px rgba(0,74,190,.32);
        transition:transform .16s ease,box-shadow .16s ease;
      }
      #${SUPPORT_ID}::before{
        content:"Zalo";
        display:block;
        font-size:13px;
        font-weight:1000;
      }
      #${SUPPORT_ID}:hover{
        transform:translateY(-2px);
        box-shadow:0 15px 34px rgba(0,74,190,.4);
      }
      #${SUPPORT_ID}:focus-visible{
        outline:4px solid rgba(0,104,255,.25);
        outline-offset:3px;
      }
      @media(max-width:700px){
        #${SUPPORT_ID}{
          right:12px;
          bottom:72px;
          width:66px;
          height:66px;
          border-width:3px;
          font-size:10.5px;
        }
        #${SUPPORT_ID}::before{font-size:12px}
        .mball-offer-title{font-size:21px!important}
        .mball-offer-price strong{font-size:29px}
      }
      @media(prefers-reduced-motion:reduce){
        #${SUPPORT_ID}{transition:none}
      }
    `;
    document.head.appendChild(style);
  }

  function normalizeText(value) {
    return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
  }

  function findBannerCard() {
    const candidates = Array.from(document.querySelectorAll("h2,h3,h4,strong,b,p,span"));
    const heading = candidates.find((node) => normalizeText(node.textContent).includes("đặt banner quảng cáo"));
    if (!heading) return null;

    return heading.closest(
      "article,.portal-card,.portal-v3-card,.portal-footer-card,.portal-support-card,.footer-card,.info-card,section"
    ) || heading.parentElement;
  }

  function openCheckoutFromNewButton(button) {
    const proxy = Array.from(document.querySelectorAll("[data-open-checkout]"))
      .find((node) => node !== button && !node.disabled);
    if (proxy) {
      proxy.click();
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

  function rewriteBannerCard() {
    const card = findBannerCard();
    if (!card || card.dataset.mballPaymentCard === "true") return;

    card.dataset.mballPaymentCard = "true";
    card.innerHTML = `
      <span class="mball-offer-kicker">GỢI Ý SỐ MB_ALL</span>
      <h3 class="mball-offer-title">Thanh toán nhận gợi ý số</h3>
      <div class="mball-offer-price"><strong>30.000đ</strong><span>/ ngày</span></div>
      <p class="mball-offer-copy">Thanh toán một lần để nhận gợi ý số đã khóa cho đúng ngày hiện tại.</p>
      <p class="mball-offer-email"><b>✉</b><span>Sau khi chuyển khoản, bấm gửi xác nhận. Hệ thống gửi email để chủ dịch vụ kiểm tra và mở gợi ý số.</span></p>
      <button class="mball-footer-pay-button" type="button" data-mball-footer-checkout>THANH TOÁN NHẬN GỢI Ý SỐ</button>
    `;

    const button = card.querySelector("[data-mball-footer-checkout]");
    button?.addEventListener("click", () => {
      try {
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({ event: "mball_footer_checkout_click", value: 30000, currency: "VND" });
      } catch (_) {}
      openCheckoutFromNewButton(button);
    });
  }

  function ensureZaloSupport() {
    let support = document.getElementById(SUPPORT_ID);
    const legacy = document.querySelector("#floating-zalo,.floating-zalo");

    if (!support && legacy) {
      support = legacy;
      support.id = SUPPORT_ID;
      support.classList.remove("floating-zalo");
    }

    if (!support) {
      support = document.createElement("a");
      support.id = SUPPORT_ID;
      document.body.appendChild(support);
    }

    support.href = ZALO_URL;
    support.target = "_blank";
    support.rel = "noopener noreferrer";
    support.setAttribute("aria-label", "Hỗ trợ qua Zalo 0398696879");
    support.textContent = "Hỗ trợ";

    if (support.dataset.mballZaloBound !== "true") {
      support.dataset.mballZaloBound = "true";
      support.addEventListener("click", () => {
        try {
          window.dataLayer = window.dataLayer || [];
          window.dataLayer.push({ event: "generate_lead", method: "zalo_support", phone: "0398696879" });
        } catch (_) {}
      });
    }
  }

  function rewriteEmailConfirmationCopy() {
    const instruction = document.querySelector(".zalo-instruction");
    if (instruction) {
      instruction.textContent = "Sau khi chuyển khoản, bấm nút dưới đây. Hệ thống gửi email xác nhận để chủ dịch vụ kiểm tra giao dịch và mở gợi ý số.";
    }

    const confirm = document.getElementById("payment-self-confirm");
    if (confirm && !confirm.disabled) {
      confirm.textContent = "TÔI ĐÃ CHUYỂN KHOẢN – GỬI EMAIL XÁC NHẬN";
    }

    const pendingTitle = document.getElementById("pending-title");
    const pendingCopy = document.getElementById("pending-copy");
    if (pendingTitle && /đã gửi|đối soát/i.test(pendingTitle.textContent || "")) {
      pendingTitle.textContent = "Đã gửi email xác nhận thanh toán";
    }
    if (pendingCopy && /chờ|quay lại|tải lại/i.test(pendingCopy.textContent || "")) {
      pendingCopy.textContent = "Chủ dịch vụ sẽ kiểm tra giao dịch qua email; gợi ý số tự mở sau khi được xác nhận.";
    }

    const legal = document.querySelector(".checkout-legal");
    if (legal && !normalizeText(legal.textContent).includes("email xác nhận")) {
      legal.insertAdjacentText(
        "afterbegin",
        "Yêu cầu thanh toán được gửi qua email để chủ dịch vụ xác nhận; nút bấm không tự xác nhận tiền đã vào tài khoản. "
      );
    }
  }

  function refresh() {
    ensureStyles();
    rewriteBannerCard();
    ensureZaloSupport();
    rewriteEmailConfirmationCopy();
  }

  const start = () => {
    refresh();
    window.setTimeout(refresh, 300);
    window.setTimeout(refresh, 1000);
    window.setTimeout(refresh, 2200);

    document.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest("[data-open-checkout],#payment-self-confirm")) {
        window.setTimeout(rewriteEmailConfirmationCopy, 0);
        window.setTimeout(rewriteEmailConfirmationCopy, 250);
        window.setTimeout(rewriteEmailConfirmationCopy, 900);
      }
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
