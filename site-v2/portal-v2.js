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
  if(path==='/tra-cuu-xsmb/'){
    const params=new URLSearchParams(location.search); const numbers=params.get('numbers'); const days=params.get('days');
    const form=document.querySelector('#lookup');
    if(form&&numbers){
      const input=form.querySelector('[name="numbers"]'); const select=form.querySelector('[name="days"]');
      if(input)input.value=numbers; if(select&&days&&[...select.options].some(o=>o.value===days))select.value=days;
      requestAnimationFrame(()=>form.requestSubmit());
    }
  }
  document.querySelectorAll('[data-portal-track]').forEach(a=>a.addEventListener('click',()=>{
    window.dataLayer=window.dataLayer||[]; window.dataLayer.push({event:'portal_internal_click',page_path:path,target:a.getAttribute('href')||'',label:a.dataset.portalTrack||''});
  }));
})();
