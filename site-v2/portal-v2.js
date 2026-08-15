(()=>{
  'use strict';
  const path=location.pathname;
  const CONSENT_KEY='lm_analytics_consent_v1';
  const routes=[['/','⌂','Home'],['/thong-ke-xsmb/','▦','Thống kê'],['/lo-gan-xsmb/','↕','Lô gan'],['/tra-cuu-xsmb/','⌕','Tra cứu'],['/phuong-phap-cong-khai/','AI','Phương pháp']];

  const gtag=(...args)=>{
    window.dataLayer=window.dataLayer||[];
    if(typeof window.gtag==='function')window.gtag(...args);
    else window.dataLayer.push(args);
  };
  const emit=(name,params={})=>gtag('event',name,{page_path:path,...params});

  const storedConsent=()=>{
    try{return localStorage.getItem(CONSENT_KEY)||''}catch{return ''}
  };
  const setConsent=state=>{
    const analytics=state==='granted'?'granted':'denied';
    gtag('consent','update',{
      analytics_storage:analytics,
      ad_storage:'denied',
      ad_user_data:'denied',
      ad_personalization:'denied'
    });
  };
  // No visible consent banner. New visitors stay privacy-safe with analytics denied.
  // Existing visitors who explicitly granted analytics in the past keep that choice.
  setConsent(storedConsent()==='granted'?'granted':'denied');

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
        const codes=parseCodes(new FormData(form).get('numbers'));
        const window=String(+new FormData(form).get('days')||60);
        emit('xsmb_lookup_submit',{number_count:codes.length,window});
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
            emit('xsmb_lookup_compare',{number_count:codes.length,window});
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
      emit('xsmb_profile_open',{code:c,source:'deep_link'});
      setTimeout(()=>document.querySelector('#profile')?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'}),30);
    };
    if(code)requestAnimationFrame(()=>openCode(code));
    document.addEventListener('click',e=>{
      const button=e.target.closest('[data-number]'); if(!button)return;
      const c=button.dataset.number; if(!/^\d{2}$/.test(c||''))return;
      const q=new URLSearchParams(location.search); q.set('so',c); history.replaceState({},'',`${location.pathname}?${q}`);
      emit('xsmb_profile_open',{code:c,source:'matrix'});
    });
  }

  document.querySelector('.portal-quick-search')?.addEventListener('submit',e=>{
    const f=new FormData(e.currentTarget); emit('portal_quick_search',{number_count:parseCodes(f.get('numbers')).length,window:String(f.get('days')||60)});
  });

  document.addEventListener('click',e=>{
    const a=e.target.closest('a'); if(!a)return;
    if(a.matches('.portal-tool,.portal-related a,.portal-mobile-nav a,.portal-fast-links a,[data-portal-track],.portal-number-compare-card')){
      emit('portal_internal_click',{target:a.getAttribute('href')||'',label:a.dataset.portalTrack||a.textContent.trim().slice(0,60)});
    }
  });

  const vitals={cls:0,lcp:0,inp:0};
  let vitalSent=false;
  const supported=window.PerformanceObserver?.supportedEntryTypes||[];
  const observe=(type,callback,options={})=>{
    if(!supported.includes(type))return;
    try{const po=new PerformanceObserver(list=>callback(list.getEntries()));po.observe({type,buffered:true,...options})}catch{}
  };
  observe('layout-shift',entries=>entries.forEach(x=>{if(!x.hadRecentInput)vitals.cls+=x.value}));
  observe('largest-contentful-paint',entries=>{const x=entries.at(-1);if(x)vitals.lcp=x.startTime});
  observe('event',entries=>entries.forEach(x=>{if(x.interactionId&&x.duration>vitals.inp)vitals.inp=x.duration}),{durationThreshold:40});
  const sendVitals=()=>{
    if(vitalSent)return; vitalSent=true;
    const nav=performance.getEntriesByType('navigation')[0];
    emit('web_vitals_summary',{
      lcp_ms:Math.round(vitals.lcp||0),
      cls_milli:Math.round((vitals.cls||0)*1000),
      inp_ms:Math.round(vitals.inp||0),
      load_ms:Math.round(nav?.loadEventEnd||0),
      navigation_type:nav?.type||'unknown'
    });
  };
  addEventListener('pagehide',sendVitals,{once:true});
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')sendVitals()},{once:true});
})();
