(() => {
  "use strict";

  const url = new URL(window.location.href);
  const shouldOpen = url.searchParams.get("checkout") === "1" || window.location.hash === "#thanh-toan";

  const injectStatisticsEntry = () => {
    if (window.location.pathname !== "/" || document.querySelector("[data-public-stats-entry]")) return;

    const anchor = document.querySelector(".conversion-trust") || document.querySelector("#statistics");
    if (!anchor) return;

    const style = document.createElement("style");
    style.textContent = `
      .public-stats-entry{padding:18px 0 6px;background:#f6f8fb}
      .public-stats-entry .public-stats-card{max-width:1180px;margin:0 auto;padding:18px;border:1px solid #d8e0e8;border-radius:18px;background:#fff;box-shadow:0 4px 18px rgba(14,31,48,.06)}
      .public-stats-entry .public-stats-head{display:flex;gap:18px;align-items:end;justify-content:space-between;flex-wrap:wrap;margin-bottom:14px}
      .public-stats-entry .public-stats-head p{margin:0 0 4px;font-size:12px;font-weight:900;letter-spacing:.08em;color:#c62828}
      .public-stats-entry h2{margin:0;font-size:clamp(22px,3vw,30px);color:#102234}
      .public-stats-entry .public-stats-status{font-size:13px;color:#5a6c7a}
      .public-stats-entry .public-stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
      .public-stats-entry .public-stats-link{display:block;padding:15px;border:1px solid #dfe6ed;border-radius:14px;text-decoration:none;background:#f9fbfd;color:#102234;transition:.15s ease}
      .public-stats-entry .public-stats-link:hover{transform:translateY(-1px);border-color:#b8c7d5;box-shadow:0 4px 12px rgba(14,31,48,.08)}
      .public-stats-entry .public-stats-link b{display:block;font-size:17px;margin-bottom:4px}
      .public-stats-entry .public-stats-link span{display:block;font-size:13px;color:#60717f}
      .public-stats-entry .public-stats-all{display:inline-block;margin-top:12px;font-weight:800;color:#b71c1c;text-decoration:none}
      @media(max-width:760px){.public-stats-entry{padding:12px 0 4px}.public-stats-entry .public-stats-card{margin:0 12px;padding:14px}.public-stats-entry .public-stats-grid{grid-template-columns:repeat(2,1fr)}.public-stats-entry .public-stats-link{padding:12px}.public-stats-entry .public-stats-link b{font-size:15px}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.className = "public-stats-entry";
    section.setAttribute("data-public-stats-entry", "true");
    section.innerHTML = `
      <div class="public-stats-card">
        <div class="public-stats-head">
          <div><p>CÔNG CỤ THỐNG KÊ XSMB</p><h2>Tra cứu dữ liệu 00–99 miễn phí</h2></div>
          <div class="public-stats-status" id="public-stats-status">Đang đọc dữ liệu mới nhất…</div>
        </div>
        <div class="public-stats-grid">
          <a class="public-stats-link" href="/tan-suat-xsmb/"><b>Tần suất 00–99</b><span>7 · 14 · 30 · 60 · 100 · 365 kỳ</span></a>
          <a class="public-stats-link" href="/lo-gan-xsmb/"><b>Lô gan XSMB</b><span>Gan hiện tại, gan max, lần gần nhất</span></a>
          <a class="public-stats-link" href="/cap-dao-xsmb/"><b>45 cặp đảo</b><span>Đủ toàn bộ cặp đảo, không trùng cặp</span></a>
          <a class="public-stats-link" href="/tra-cuu-xsmb/"><b>Tra cứu bộ số</b><span>Dò lịch sử 30–365 kỳ theo bộ tự nhập</span></a>
        </div>
        <a class="public-stats-all" href="/thong-ke-xsmb/">Mở Trung tâm Thống kê XSMB →</a>
      </div>`;

    anchor.insertAdjacentElement("afterend", section);

    fetch("/statistics-data.json", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("stats")))
      .then((data) => {
        const status = document.getElementById("public-stats-status");
        if (!status) return;
        const day = String(data.updated_through || "").split("-").reverse().join("/");
        status.textContent = `${Number(data.row_count || 0).toLocaleString("vi-VN")} kỳ · dữ liệu đến ${day}`;
      })
      .catch(() => {
        const status = document.getElementById("public-stats-status");
        if (status) status.textContent = "Dữ liệu lịch sử 27 mã/ngày";
      });
  };

  let attempts = 0;
  const openCheckout = () => {
    if (!shouldOpen) return;
    attempts += 1;
    const button = [...document.querySelectorAll("[data-open-checkout]")]
      .find((node) => !node.disabled && node.getAttribute("aria-disabled") !== "true");
    if (button) {
      button.click();
      url.searchParams.delete("checkout");
      url.hash = "";
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
      return;
    }
    if (attempts < 20) window.setTimeout(openCheckout, 100);
  };

  window.addEventListener("DOMContentLoaded", () => {
    injectStatisticsEntry();
    openCheckout();
  }, { once: true });
})();
