(()=>{"use strict";
  const lockMarkup=`<section class="private-finance-section"><div class="section-head"><div><span class="tag">SỔ RIÊNG</span><h2>Lãi/lỗ cá nhân</h2></div><p>Không xuất bản trên website công khai.</p></div><div class="private-finance-card"><div class="private-finance-icon" aria-hidden="true">🔒</div><div class="private-finance-copy"><b>Thông tin tài chính đã được chuyển sang chế độ riêng tư</b><span>Chỉ chủ sở hữu xem trong sổ Google Drive cá nhân. Website không tải hoặc hiển thị tổng lãi/lỗ.</span><span class="private-finance-badge">OWNER ONLY</span></div></div></section>`;
  const replace=()=>{
    const app=document.getElementById("app");if(!app)return;
    const sections=[...app.querySelectorAll("section.section")];
    const target=sections.find(section=>/Theo dõi vốn và lợi nhuận|LÃI\/LỖ/i.test(section.textContent||""));
    if(target&&!target.classList.contains("private-finance-section"))target.outerHTML=lockMarkup;
  };
  const observer=new MutationObserver(replace);
  const start=()=>{const app=document.getElementById("app");if(app){observer.observe(app,{childList:true,subtree:true});replace()}};
  document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();
})();
