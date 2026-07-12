(()=>{"use strict";
  const SHEET_ID="1bEs7aoDZl8kr3vJGjgSk8q1iROtS0ssVQCRCA8jfOuQ";
  const SHEET_GID="480517506";
  const previewUrl=`https://docs.google.com/spreadsheets/d/${SHEET_ID}/preview?rm=minimal&single=true&gid=${SHEET_GID}`;
  const editUrl=`https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit#gid=${SHEET_GID}`;
  const ownerMarkup=`<section class="private-finance-section"><div class="private-finance-shell"><div class="private-finance-header"><div class="private-finance-title"><span class="private-finance-icon" aria-hidden="true">🔒</span><div><span class="private-finance-kicker">SỔ RIÊNG CỦA TÔI</span><h2>Lãi/lỗ cá nhân</h2><p>Khung Google Sheets chỉ tải khi bấm mở để website vào nhanh hơn.</p></div></div><div class="private-finance-actions"><span class="private-finance-badge">OWNER VIEW</span><button class="private-finance-open" type="button" data-load-private-finance>Hiện sổ riêng</button><a class="private-finance-open" href="${editUrl}" target="_blank" rel="noopener noreferrer">Mở trong Sheets ↗</a></div></div><div class="private-finance-frame-wrap" data-private-finance-frame><div class="private-finance-foot"><span>Chưa tải khung riêng để tiết kiệm thời gian và dữ liệu.</span><span>Bấm “Hiện sổ riêng” khi cần xem.</span></div></div></div></section>`;

  const app=document.getElementById("app");
  if(!app)return;

  const replace=()=>{
    if(app.querySelector(".private-finance-section"))return;
    const target=[...app.querySelectorAll("section.section")].find(section=>/Theo dõi vốn và lợi nhuận|Lũy kế đã khóa|LÃI\/LỖ/i.test(section.textContent||""));
    if(target)target.outerHTML=ownerMarkup;
  };

  app.addEventListener("click",event=>{
    const button=event.target.closest?.("[data-load-private-finance]");
    if(!button)return;
    const wrap=app.querySelector("[data-private-finance-frame]");
    if(!wrap||wrap.querySelector("iframe"))return;
    button.disabled=true;
    button.textContent="Đang tải…";
    wrap.innerHTML=`<iframe class="private-finance-frame" title="Sổ lãi lỗ cá nhân" src="${previewUrl}" loading="lazy" referrerpolicy="no-referrer"></iframe><div class="private-finance-foot"><span>Dữ liệu do Google kiểm soát quyền truy cập.</span><span>Nếu khung không hiện, dùng nút “Mở trong Sheets”.</span></div>`;
  });

  new MutationObserver(replace).observe(app,{childList:true,subtree:true});
  replace();
})();