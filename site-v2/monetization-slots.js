(() => {
  "use strict";

  const SHOPEE = {
    url: "https://nguyenlinhtkv_aul4jx.accesslanding.site",
    network: "ACCESSTRADE"
  };
  const ADSTERRA_NATIVE_SRC = "https://pl30863058.effectivecpmnetwork.com/e336b428517bbcb55a3e3da308cc7939/invoke.js";
  const ADSTERRA_NATIVE_CONTAINER = "container-e336b428517bbcb55a3e3da308cc7939";
  const ADSTERRA_300_KEY = "b3caa39744fc30610e7756cf4ccb98cd";
  const ADSTERRA_300_SRC = "https://www.highperformanceformat.com/b3caa39744fc30610e7756cf4ccb98cd/invoke.js";
  let displayLoaded = false;

  function emit(event, extra = {}) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event, page_path: window.location.pathname, ...extra });
  }

  function isPaidAcquisitionVisit() {
    const url = new URL(window.location.href);
    if (["gclid", "gbraid", "wbraid", "fbclid", "ttclid"].some((key) => url.searchParams.has(key))) return true;
    const source = (url.searchParams.get("utm_source") || "").toLowerCase();
    const medium = (url.searchParams.get("utm_medium") || "").toLowerCase();
    return /^(google|googleads|google-ads|facebook|fb|meta|instagram|tiktok)$/.test(source)
      && /^(cpc|ppc|paid|paidsearch|paid-search|paid_social|paidsocial|paid-social)$/.test(medium);
  }

  function sectionByText(pattern) {
    return [...document.querySelectorAll("section")].find((node) => pattern.test(node.textContent || "")) || null;
  }

  function toolsAnchor() {
    return sectionByText(/Công cụ thống kê XSMB/i)
      || document.querySelector(".portal-tools")?.closest("section")
      || null;
  }

  function purchaseAnchor() {
    return document.querySelector(".buy-simple")?.closest("section")
      || document.querySelector("[data-ai-product-proof]")?.closest("section")
      || sectionByText(/MỞ BẢN PHÂN TÍCH AI|30\.000/i)
      || sectionByText(/Lịch sử đối chiếu|hiệu quả lịch sử/i)
      || null;
  }

  function installStyle() {
    if (document.getElementById("lm-visible-monetization-style")) return;
    const style = document.createElement("style");
    style.id = "lm-visible-monetization-style";
    style.textContent = `
      .lm-sponsor-strip,.lm-display-ads{width:100%;padding:10px 0}.lm-sponsor-inner,.lm-display-ads-inner{max-width:1180px;margin:auto;padding:0 16px}
      .lm-sponsor-card{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:12px;padding:14px 15px;border:1px solid #f0d9d0;border-radius:15px;background:linear-gradient(135deg,#fff8f4,#fff);color:#243542!important;text-decoration:none!important;box-shadow:0 3px 14px rgba(35,40,45,.05)}
      .lm-sponsor-card:before{content:"TÀI TRỢ";position:absolute;top:8px;right:10px;padding:3px 6px;border-radius:999px;background:#fff0e8;color:#b64a18;font-size:8px;font-weight:1000;letter-spacing:.07em}.lm-sponsor-card strong{display:block;padding-right:58px;font-size:14px}.lm-sponsor-card small{display:block;margin-top:3px;color:#71808a;font-size:10.5px}.lm-sponsor-cta{display:flex;align-items:center;justify-content:center;min-height:42px;padding:0 13px;border-radius:10px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:1000;white-space:nowrap}.lm-sponsor-note{margin:6px 2px 0;color:#91999e;font-size:8.5px;line-height:1.35}
      .lm-display-ads-inner{border-top:1px solid #edf0f2;padding-top:16px}.lm-display-ads-head{display:flex;align-items:end;justify-content:space-between;gap:10px;margin-bottom:10px}.lm-display-ads-head span{color:#a0522d;font-size:9px;font-weight:1000;letter-spacing:.08em;text-transform:uppercase}.lm-display-ads-head h2{margin:2px 0 0;color:#263946;font-size:18px;line-height:1.2}.lm-display-ads-head small{color:#89959d;font-size:9px}.lm-display-ads-grid{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:12px;align-items:start}.lm-ad-frame{width:100%;border:0;border-radius:12px;background:#f7f8f9;overflow:hidden}.lm-ad-native{min-height:250px}.lm-ad-300{width:320px;height:270px;justify-self:end}.lm-display-ads-note{margin:7px 1px 0;color:#929ba1;font-size:8.5px;line-height:1.35}
      @media(max-width:700px){.lm-sponsor-strip,.lm-display-ads{padding:7px 0}.lm-sponsor-inner,.lm-display-ads-inner{padding:0 10px}.lm-sponsor-card{grid-template-columns:1fr;padding:12px;gap:9px}.lm-sponsor-card strong{padding-right:54px;font-size:13px}.lm-sponsor-card small{font-size:10px}.lm-sponsor-cta{width:100%;min-height:44px}.lm-display-ads-inner{padding-top:13px}.lm-display-ads-head{align-items:start}.lm-display-ads-head h2{font-size:16px}.lm-display-ads-head small{display:none}.lm-display-ads-grid{grid-template-columns:1fr;gap:9px}.lm-ad-native{min-height:220px}.lm-ad-300{width:min(320px,100%);height:270px;justify-self:center}}
    `;
    document.head.appendChild(style);
  }

  function addShopeeSponsor() {
    if (document.querySelector(".lm-sponsor-strip")) return;
    const anchor = toolsAnchor();
    if (!anchor) return;
    const section = document.createElement("section");
    section.className = "lm-sponsor-strip";
    section.setAttribute("aria-label", "Ưu đãi tài trợ Shopee");
    section.innerHTML = `
      <div class="lm-sponsor-inner">
        <a class="lm-sponsor-card" href="${SHOPEE.url}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-visible-shopee-ad>
          <div><strong>Shopee · ưu đãi mua sắm hôm nay</strong><small>Mở Shopee để xem sản phẩm và ưu đãi đang có qua ACCESSTRADE.</small></div>
          <span class="lm-sponsor-cta">XEM ƯU ĐÃI →</span>
        </a>
        <p class="lm-sponsor-note">Liên kết tài trợ · website có thể nhận hoa hồng từ giao dịch đủ điều kiện; giá mua không tăng vì liên kết này.</p>
      </div>`;
    anchor.insertAdjacentElement("afterend", section);
    section.querySelector("[data-visible-shopee-ad]")?.addEventListener("click", () => emit("affiliate_shopee_click", {
      affiliate_network: SHOPEE.network,
      merchant: "Shopee",
      placement: "after_tools_visible"
    }));
    emit("affiliate_shopee_view", { affiliate_network: SHOPEE.network, merchant: "Shopee", placement: "after_tools_visible" });
  }

  function adSrcdocNative() {
    return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>html,body{margin:0;padding:0;background:#f7f8f9;overflow:hidden}#${ADSTERRA_NATIVE_CONTAINER}{min-height:220px}</style></head><body><script async data-cfasync="false" src="${ADSTERRA_NATIVE_SRC}"><\/script><div id="${ADSTERRA_NATIVE_CONTAINER}"></div></body></html>`;
  }

  function adSrcdoc300() {
    return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>html,body{margin:0;padding:0;width:100%;height:100%;display:grid;place-items:center;background:#f7f8f9;overflow:hidden}</style></head><body><script>window.atOptions={key:'${ADSTERRA_300_KEY}',format:'iframe',height:250,width:300,params:{}};<\/script><script src="${ADSTERRA_300_SRC}"><\/script></body></html>`;
  }

  function loadDisplayAds(section) {
    if (displayLoaded) return;
    displayLoaded = true;
    const nativeFrame = section.querySelector("[data-adsterra-native]");
    const boxFrame = section.querySelector("[data-adsterra-300]");
    if (nativeFrame) nativeFrame.srcdoc = adSrcdocNative();
    if (boxFrame) boxFrame.srcdoc = adSrcdoc300();
    emit("display_ads_view", { network: "Adsterra", placement: "post_purchase_area", units: 2 });
  }

  function addDisplayAds() {
    if (isPaidAcquisitionVisit() || document.querySelector(".lm-display-ads")) return;
    const anchor = purchaseAnchor();
    if (!anchor) return;
    const section = document.createElement("section");
    section.className = "lm-display-ads";
    section.setAttribute("aria-label", "Quảng cáo tài trợ");
    section.innerHTML = `
      <div class="lm-display-ads-inner">
        <div class="lm-display-ads-head"><div><span>QUẢNG CÁO</span><h2>Khu vực tài trợ</h2></div><small>Display ads · chỉ tải khi cuộn tới khu vực này</small></div>
        <div class="lm-display-ads-grid">
          <iframe class="lm-ad-frame lm-ad-native" data-adsterra-native title="Quảng cáo tài trợ" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
          <iframe class="lm-ad-frame lm-ad-300" data-adsterra-300 title="Quảng cáo 300 x 250" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
        </div>
        <p class="lm-display-ads-note">Nội dung quảng cáo do đối tác quảng cáo phân phối. Đây là khu tài trợ và tách biệt với bản phân tích AI.</p>
      </div>`;
    anchor.insertAdjacentElement("afterend", section);

    if (!("IntersectionObserver" in window)) {
      window.setTimeout(() => loadDisplayAds(section), 1200);
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting || entry.boundingClientRect.top < window.innerHeight + 700)) return;
      loadDisplayAds(section);
      observer.disconnect();
    }, { rootMargin: "700px 0px" });
    observer.observe(section);
  }

  function boot() {
    if (window.location.pathname !== "/") return;
    installStyle();
    addShopeeSponsor();
    addDisplayAds();
    document.documentElement.dataset.visibleMonetization = "v1";
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
