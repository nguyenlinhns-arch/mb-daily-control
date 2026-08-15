// Public endpoint only. Administrative approval secrets must never be stored here.
window.ORDER_CONFIRMATION_ENDPOINT = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec";

// Homepage affiliate entry gate. Shows once per browser-tab session and never auto-redirects.
(()=>{
  'use strict';
  const SMARTLINK='https://nguyenlinhtkv_aul4jx.accesslanding.site';
  const KEY='lm_shopee_gate_seen_v1';
  if(location.pathname!=='/')return;

  const alreadySeen=()=>{try{return sessionStorage.getItem(KEY)==='1'}catch{return false}};
  const markSeen=()=>{try{sessionStorage.setItem(KEY,'1')}catch{}};

  const mount=()=>{
    if(alreadySeen()||document.getElementById('lm-shopee-gate'))return;

    const style=document.createElement('style');
    style.id='lm-shopee-gate-style';
    style.textContent=`
      .lm-shopee-gate{position:fixed;inset:0;z-index:9999;display:grid;place-items:center;padding:16px;background:rgba(8,20,30,.72);backdrop-filter:blur(5px)}
      .lm-shopee-gate-card{position:relative;width:min(440px,100%);overflow:hidden;border:1px solid #f0d6cb;border-radius:22px;background:#fff;box-shadow:0 26px 80px rgba(0,0,0,.28);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1d2d38}
      .lm-shopee-gate-top{padding:25px 22px 18px;background:linear-gradient(135deg,#fff4ee,#fff)}
      .lm-shopee-gate-badge{display:inline-flex;align-items:center;gap:6px;padding:5px 8px;border-radius:999px;background:#fff0e8;color:#b73e22;font-size:10px;font-weight:900;letter-spacing:.04em;text-transform:uppercase}
      .lm-shopee-gate h2{margin:10px 0 0;font-size:26px;line-height:1.12;letter-spacing:-.025em;color:#152936}
      .lm-shopee-gate p{margin:8px 0 0;color:#62717b;font-size:13px;line-height:1.5}
      .lm-shopee-gate-actions{display:grid;gap:9px;padding:0 22px 20px}
      .lm-shopee-gate-primary,.lm-shopee-gate-secondary{min-height:50px;border-radius:12px;display:flex;align-items:center;justify-content:center;padding:0 14px;font:inherit;font-size:14px;font-weight:900;text-decoration:none;cursor:pointer}
      .lm-shopee-gate-primary{border:0;background:#ee4d2d;color:#fff!important;box-shadow:0 9px 22px rgba(238,77,45,.22)}
      .lm-shopee-gate-secondary{border:1px solid #dbe1e5;background:#fff;color:#40515d}
      .lm-shopee-gate-note{padding:12px 22px 18px;border-top:1px solid #edf0f2;color:#879199;font-size:10px;line-height:1.45}
      .lm-shopee-gate-close{position:absolute;right:10px;top:10px;width:38px;height:38px;border:1px solid #e1e5e8;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.95);color:#52626d;font:700 21px/1 system-ui;cursor:pointer}
      body.lm-shopee-gate-open{overflow:hidden}
      @media(max-width:600px){
        .lm-shopee-gate{align-items:end;padding:0;background:rgba(8,20,30,.66)}
        .lm-shopee-gate-card{width:100%;border-radius:22px 22px 0 0;border-left:0;border-right:0;border-bottom:0;padding-bottom:max(0px,env(safe-area-inset-bottom))}
        .lm-shopee-gate-top{padding:23px 18px 15px}.lm-shopee-gate h2{font-size:23px}.lm-shopee-gate p{font-size:12.5px}
        .lm-shopee-gate-actions{padding:0 18px 16px}.lm-shopee-gate-primary,.lm-shopee-gate-secondary{min-height:52px;font-size:13px}
        .lm-shopee-gate-note{padding:11px 18px 15px}.lm-shopee-gate-close{right:12px;top:11px;width:36px;height:36px}
      }
      @media(prefers-reduced-motion:reduce){.lm-shopee-gate{backdrop-filter:none}}
    `;
    document.head.appendChild(style);

    const gate=document.createElement('aside');
    gate.id='lm-shopee-gate';
    gate.className='lm-shopee-gate';
    gate.setAttribute('role','dialog');
    gate.setAttribute('aria-modal','true');
    gate.setAttribute('aria-labelledby','lm-shopee-gate-title');
    gate.innerHTML=`
      <div class="lm-shopee-gate-card">
        <button type="button" class="lm-shopee-gate-close" aria-label="Đóng và xem thống kê">×</button>
        <div class="lm-shopee-gate-top">
          <span class="lm-shopee-gate-badge">Liên kết đối tác · ACCESSTRADE</span>
          <h2 id="lm-shopee-gate-title">Shopee – Ưu đãi hôm nay</h2>
          <p>Xem deal, mã giảm giá và sản phẩm đang được giới thiệu trước khi tiếp tục xem thống kê XSMB.</p>
        </div>
        <div class="lm-shopee-gate-actions">
          <a class="lm-shopee-gate-primary" href="${SMARTLINK}" target="_blank" rel="sponsored noopener noreferrer">XEM ƯU ĐÃI SHOPEE →</a>
          <button type="button" class="lm-shopee-gate-secondary">ĐÓNG – XEM THỐNG KÊ</button>
        </div>
        <div class="lm-shopee-gate-note">Nếu bạn mua hàng đủ điều kiện sau khi bấm liên kết, website có thể nhận hoa hồng từ ACCESSTRADE; giá mua của bạn không tăng vì liên kết này.</div>
      </div>`;

    const close=()=>{
      markSeen();
      document.body.classList.remove('lm-shopee-gate-open');
      gate.remove();
    };
    gate.querySelector('.lm-shopee-gate-close').addEventListener('click',close);
    gate.querySelector('.lm-shopee-gate-secondary').addEventListener('click',close);
    gate.querySelector('.lm-shopee-gate-primary').addEventListener('click',()=>{markSeen();setTimeout(close,80)});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.getElementById('lm-shopee-gate'))close()},{once:true});
    document.body.classList.add('lm-shopee-gate-open');
    document.body.appendChild(gate);
    gate.querySelector('.lm-shopee-gate-primary').focus({preventScroll:true});
  };

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});
  else mount();
})();
