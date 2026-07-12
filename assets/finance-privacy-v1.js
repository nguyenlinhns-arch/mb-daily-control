(()=>{"use strict";
  const SHEET_ID="1bEs7aoDZl8kr3vJGjgSk8q1iROtS0ssVQCRCA8jfOuQ";
  const SHEET_GID="480517506";
  const previewUrl=`https://docs.google.com/spreadsheets/d/${SHEET_ID}/preview?rm=minimal&single=true&gid=${SHEET_GID}`;
  const editUrl=`https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit#gid=${SHEET_GID}`;
  const ownerMarkup=`<section class="private-finance-section"><div class="private-finance-shell"><div class="private-finance-header"><div class="private-finance-title"><span class="private-finance-icon" aria-hidden="true">🔒</span><div><span class="private-finance-kicker">SỔ RIÊNG CỦA TÔI</span><h2>Lãi/lỗ cá nhân</h2><p>Đăng nhập đúng tài khoản Google được cấp quyền để xem trực tiếp.</p></div></div><div class="private-finance-actions"><span class="private-finance-badge">OWNER VIEW</span><a class="private-finance-open" href="${editUrl}" target="_blank" rel="noopener noreferrer">Mở trong Google Sheets ↗</a></div></div><div class="private-finance-frame-wrap"><iframe class="private-finance-frame" title="Sổ lãi lỗ cá nhân" src="${previewUrl}" loading="lazy" referrerpolicy="no-referrer"></iframe></div><div class="private-finance-foot"><span>Dữ liệu được Google kiểm soát quyền truy cập; người không được cấp quyền sẽ không xem được.</span><span>Nếu khung không hiện do trình duyệt chặn cookie, dùng nút “Mở trong Google Sheets”.</span></div></div></section>`;
  const replace=()=>{
    const app=document.getElementById("app");if(!app)return;
    const existing=app.querySelector(".private-finance-section");
    if(existing)return;
    const sections=[...app.querySelectorAll("section.section")];
    const target=sections.find(section=>/Theo dõi vốn và lợi nhuận|LÃI\/LỖ/i.test(section.textContent||""));
    if(target)target.outerHTML=ownerMarkup;
  };
  const observer=new MutationObserver(replace);
  const start=()=>{const app=document.getElementById("app");if(app){observer.observe(app,{childList:true,subtree:true});replace()}};
  document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();
})();
