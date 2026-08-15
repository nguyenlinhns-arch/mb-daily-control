(()=>{
  'use strict';
  const path=location.pathname;
  const routes=[['/','⌂','Home'],['/thong-ke-xsmb/','▦','Thống kê'],['/lo-gan-xsmb/','↕','Lô gan'],['/tra-cuu-xsmb/','⌕','Tra cứu'],['/phuong-phap-cong-khai/','AI','Phương pháp']];
  if(!document.querySelector('.portal-mobile-nav')){
    const nav=document.createElement('nav');
    nav.className='portal-mobile-nav'; nav.setAttribute('aria-label','Điều hướng nhanh trên điện thoại');
    nav.innerHTML=routes.map(([href,icon,label])=>`<a href="${href}"${path===href?' class="is-active"':''}><b>${icon}</b><span>${label}</span></a>`).join('');
    document.body.appendChild(nav);
  }
  document.querySelectorAll('.portal-fast-links a,.portal-mobile-nav a').forEach(a=>{
    if(a.getAttribute('href')===path)a.classList.add('is-active');
  });

  const parseCodes=value=>[...new Set((String(value||'').match(/\d{1,2}/g)||[]).map(x=>String(Number(x)).padStart(2,'0')).filter(x=>+x>=0&&+x<=99))].slice(0,20);
  const fmt=s=>s?s.split('-').reverse().join('/'):'Chưa có';
  let statsPromise;
  const loadStats=()=>statsPromise||(statsPromise=fetch('/statistics-data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('statistics-data');return r.json()}));

  if(path==='/tra-cuu-xsmb/'){
    const params=new URLSearchParams(location.search); const numbers=params.get('numbers'); const days=params.get('days');
    const form=document.querySelector('#lookup');
    if(form&&numbers){
      const input=form.querySelector('[name="numbers"]'); const select=form.querySelector('[name="days"]');
      if(input)input.value=numbers; if(select&&days&&[...select.options].some(o=>o.value===days))select.value=days;
      requestAnimationFrame(()=>form.requestSubmit());
    }
    if(form){
      form.addEventListener('submit',()=>{
        setTimeout(async()=>{
          try{
            const data=await loadStats(); const f=new FormData(form); const codes=parseCodes(f.get('numbers')); const window=String(+f.get('days')||60);
            if(!codes.length)return;
            const rows=codes.map(code=>{
              const n=(data.numbers||[]).find(x=>x.code===code); if(!n)return null;
              const s=n.windows?.[window]||n.windows?.['60']; if(!s)return null;
              return {code,n,s};
            }).filter(Boolean);
            const out=document.querySelector('#lookupOut'); if(!out||!rows.length)return;
            out.querySelector('.portal-number-compare')?.remove();
            const section=document.createElement('section'); section.className='portal-number-compare';
            section.innerHTML=`<div class="portal-number-compare-head"><div><b>So sánh từng số</b><span>Cửa sổ ${window} kỳ · bấm số để mở hồ sơ chi tiết</span></div><a href="/thong-ke-xsmb/">Ma trận 00–99 →</a></div><div class="portal-number-compare-grid">${rows.map(({code,n,s})=>`<a class="portal-number-compare-card" href="/thong-ke-xsmb/?so=${code}"><strong>${code}</strong><span><b>${s.days_seen}/${s.window}</b> ngày có mặt</span><span><b>${s.hits}</b> nháy</span><span>Gan <b>${n.current_gap}</b> kỳ</span><small>Gần nhất ${fmt(n.last_seen)}</small></a>`).join('')}</div>`;
            out.prepend(section);
            const q=new URLSearchParams(); q.set('numbers',codes.join(',')); q.set('days',window); history.replaceState({},'',`${location.pathname}?${q}`);
            window.dataLayer=window.dataLayer||[]; window.dataLayer.push({event:'xsmb_lookup_compare',page_path:path,numbers:codes.join('-'),window});
          }catch{}
        },0);
      });
    }
  }

  if(path==='/thong-ke-xsmb/'){
    const params=new URLSearchParams(location.search); const code=params.get('so');
    const openCode=value=>{
      const c=parseCodes(value)[0]; if(!c)return;
      const button=document.querySelector(`[data-number="${c}"]`); if(!button)return;
      button.click();
      setTimeout(()=>document.querySelector('#profile')?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'}),30);
    };
    if(code)requestAnimationFrame(()=>openCode(code));
    document.addEventListener('click',e=>{
      const button=e.target.closest('[data-number]'); if(!button)return;
      const c=button.dataset.number; if(!/^\d{2}$/.test(c||''))return;
      const q=new URLSearchParams(location.search); q.set('so',c); history.replaceState({},'',`${location.pathname}?${q}`);
    });
  }

  document.querySelectorAll('[data-portal-track]').forEach(a=>a.addEventListener('click',()=>{
    window.dataLayer=window.dataLayer||[]; window.dataLayer.push({event:'portal_internal_click',page_path:path,target:a.getAttribute('href')||'',label:a.dataset.portalTrack||''});
  }));
})();
