#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEGACY_OLD="(()=>{let D;const load=()=>D?Promise.resolve(D):fetch('/statistics-data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>D=x);"
LEGACY_NEW="(()=>{let D=window.LM_STATS_DATA||null;const load=()=>D?Promise.resolve(D):(window.LM_STATS_PROMISE||(window.LM_STATS_PROMISE=fetch('/statistics-data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>{D=x;window.LM_STATS_DATA=x;return x})));window.LM_LOAD_STATS=load;"
DYNAMIC_OLD="(()=>{let D,selectedNumber='';const version=document.documentElement.dataset.statsVersion||'';const statsUrl='/statistics-data.json'+(version?'?v='+encodeURIComponent(version):'');const load=()=>D?Promise.resolve(D):fetch(statsUrl,{cache:'default'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>D=x);"
DYNAMIC_NEW="(()=>{let D=window.LM_STATS_DATA||null,selectedNumber='';const version=document.documentElement.dataset.statsVersion||'';const statsUrl='/statistics-data.json'+(version?'?v='+encodeURIComponent(version):'');const load=()=>D?Promise.resolve(D):(window.LM_STATS_PROMISE||(window.LM_STATS_PROMISE=fetch(statsUrl,{cache:'default'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>{D=x;window.LM_STATS_DATA=x;return x})));window.LM_LOAD_STATS=load;"
SHARE_MARKER='LM_STATS_SHARE_STATE_V1'
SHARE_JS=r'''
;(()=>{
  "use strict";
  const MARKER="LM_STATS_SHARE_STATE_V1";
  const RECENT_KEY="lm_stats_recent_v1";
  const WINDOWS=new Set(["7","14","30","60","90","100","365"]);
  const emit=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,...extra})};
  const currentWindow=()=>document.querySelector('.tabs button.active')?.dataset.w||"60";
  const currentNumber=()=>new URL(location.href).searchParams.get("so")||"";
  const validNumber=value=>/^\d{2}$/.test(String(value||""))&&Number(value)<=99;
  const readRecent=()=>{try{const value=JSON.parse(localStorage.getItem(RECENT_KEY)||"[]");return Array.isArray(value)?value.filter(item=>item&&validNumber(item.number)&&WINDOWS.has(String(item.window))).slice(0,5):[]}catch(_){return[]}};
  const remember=(number,windowValue)=>{if(!validNumber(number)||!WINDOWS.has(String(windowValue)))return;try{const now=Date.now();const next=[{number:String(number),window:String(windowValue),ts:now},...readRecent().filter(item=>item.number!==String(number))].slice(0,5);localStorage.setItem(RECENT_KEY,JSON.stringify(next))}catch(_){}};
  const updateUrl=(number,windowValue)=>{
    if(location.pathname!=="/thong-ke-xsmb/")return;
    const url=new URL(location.href);
    if(validNumber(number))url.searchParams.set("so",number);else url.searchParams.delete("so");
    if(WINDOWS.has(String(windowValue||"")))url.searchParams.set("w",String(windowValue));else url.searchParams.delete("w");
    history.replaceState(null,"",url.pathname+(url.search?url.search:"")+url.hash);
  };
  const addShareButton=()=>{
    if(location.pathname!=="/thong-ke-xsmb/")return;
    const profile=document.getElementById("profile");
    const number=currentNumber();
    if(!profile||!validNumber(number)||profile.querySelector("[data-stats-share]"))return;
    const actions=document.createElement("div");
    actions.className="lm-stats-profile-actions";
    actions.innerHTML='<button type="button" class="lm-stats-share" data-stats-share>Chia sẻ hồ sơ số '+number+'</button><span class="lm-stats-share-status" aria-live="polite"></span>';
    profile.appendChild(actions);
    const button=actions.querySelector("[data-stats-share]");
    const status=actions.querySelector(".lm-stats-share-status");
    button?.addEventListener("click",async()=>{
      const w=currentWindow();
      updateUrl(number,w);remember(number,w);
      const url=location.href;
      const title=`Thống kê XSMB số ${number} · ${w} kỳ`;
      let method="copy";
      try{
        if(navigator.share){await navigator.share({title,text:`Hồ sơ thống kê số ${number} trong ${w} kỳ.`,url});method="native";status.textContent="Đã mở bảng chia sẻ.";}
        else if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(url);status.textContent="Đã sao chép liên kết.";}
        else{const input=document.createElement("textarea");input.value=url;input.style.position="fixed";input.style.opacity="0";document.body.appendChild(input);input.select();document.execCommand("copy");input.remove();status.textContent="Đã sao chép liên kết.";}
        emit("xsmb_profile_share",{number,window:w,method});
      }catch(error){if(error?.name!=="AbortError")status.textContent="Không thể chia sẻ tự động trên trình duyệt này.";}
    });
  };
  const addResume=()=>{
    if(location.pathname!=="/thong-ke-xsmb/"||validNumber(currentNumber()))return;
    const profile=document.getElementById("profile");if(!profile||profile.querySelector("[data-stats-resume]"))return;
    const last=readRecent()[0];if(!last)return;
    const wrap=document.createElement("div");wrap.className="lm-stats-resume";
    wrap.innerHTML='<span>Phiên xem gần nhất</span><button type="button" data-stats-resume>Tiếp tục số '+last.number+' · '+last.window+' kỳ</button>';
    profile.appendChild(wrap);
    wrap.querySelector("[data-stats-resume]")?.addEventListener("click",()=>{
      const tab=document.querySelector(`.tabs button[data-w="${last.window}"]`);if(tab&&!tab.classList.contains("active"))tab.click();
      const button=document.querySelector(`.num[data-number="${last.number}"]`);if(button){button.click();button.scrollIntoView({block:"center",behavior:"smooth"});emit("xsmb_stats_resume",{number:last.number,window:last.window});}
    });
    emit("xsmb_stats_resume_view",{number:last.number,window:last.window});
  };
  const boot=()=>{
    if(location.pathname!=="/thong-ke-xsmb/")return;
    document.documentElement.dataset.statsShare=MARKER;
    document.addEventListener("click",event=>{
      const target=event.target instanceof Element?event.target:null;if(!target)return;
      const tab=target.closest(".tabs button[data-w]");
      if(tab&&WINDOWS.has(String(tab.dataset.w||""))){const number=currentNumber();updateUrl(number,tab.dataset.w);if(validNumber(number))remember(number,tab.dataset.w);window.setTimeout(addShareButton,0);return;}
      const numberButton=target.closest(".num[data-number]");
      if(numberButton&&validNumber(numberButton.dataset.number)){const w=currentWindow();updateUrl(numberButton.dataset.number,w);remember(numberButton.dataset.number,w);window.setTimeout(addShareButton,0);}
    });
    const profile=document.getElementById("profile");
    if(profile)new MutationObserver(addShareButton).observe(profile,{childList:true});
    const url=new URL(location.href);const number=url.searchParams.get("so")||"";const w=url.searchParams.get("w")||"";
    const hasNumber=validNumber(number);const validWindow=WINDOWS.has(w);
    if(validWindow){const tab=document.querySelector(`.tabs button[data-w="${w}"]`);if(tab&&!tab.classList.contains("active"))tab.click();}
    if(hasNumber){const button=document.querySelector(`.num[data-number="${number}"]`);if(button){window.setTimeout(()=>{button.click();button.scrollIntoView({block:"center",behavior:"smooth"});remember(number,validWindow?w:currentWindow());emit("xsmb_deep_link_open",{number,window:validWindow?w:currentWindow()});},0);}}
    else addResume();
  };
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})();
'''
SHARE_CSS=r'''
.lm-stats-profile-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:12px}.lm-stats-share{min-height:40px;padding:0 12px;border:1px solid #46647a;border-radius:9px;background:#fff;color:#15364d;font:inherit;font-size:11px;font-weight:900;cursor:pointer}.lm-stats-share-status{color:#bed0df;font-size:10px;font-weight:700}.lm-stats-resume{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px;padding:10px;border:1px solid #31546c;border-radius:10px;background:#0d2a40}.lm-stats-resume span{color:#bed0df;font-size:10px;font-weight:700}.lm-stats-resume button{min-height:40px;padding:0 12px;border:1px solid #607f94;border-radius:9px;background:#fff;color:#15364d;font:inherit;font-size:11px;font-weight:900;cursor:pointer}.num{min-width:0}.num small{overflow-wrap:anywhere}
@media(max-width:760px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:6px}.num{min-height:72px;padding:8px 3px!important}.num b{font-size:16px}.num small{font-size:9px!important;line-height:1.25}.tabs{width:100%;gap:4px}.tabs button{flex:1 1 58px;min-height:38px;padding:5px 6px!important;font-size:10.5px}.lm-stats-profile-actions{display:grid;grid-template-columns:1fr;gap:5px}.lm-stats-share{width:100%;min-height:44px}.lm-stats-resume{display:grid;grid-template-columns:1fr;gap:6px}.lm-stats-resume button{width:100%;min-height:44px}}
@media(max-width:390px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:5px}.num{min-height:68px}.num small{font-size:8.5px!important}}
'''


def apply(root:Path)->dict[str,object]:
    path=root/'xsmb-stats.js'
    if not path.is_file():raise ValueError('Missing xsmb-stats.js')
    text=path.read_text(encoding='utf-8')
    changed=False
    if DYNAMIC_NEW in text:
        mode='dynamic'
    elif LEGACY_NEW in text:
        mode='legacy'
    elif DYNAMIC_OLD in text:
        text=text.replace(DYNAMIC_OLD,DYNAMIC_NEW,1);mode='dynamic';changed=True
    elif LEGACY_OLD in text:
        text=text.replace(LEGACY_OLD,LEGACY_NEW,1);mode='legacy';changed=True
    else:
        raise ValueError('Unexpected xsmb-stats.js loader; refusing blind patch')
    if SHARE_MARKER not in text:
        text=text.rstrip()+SHARE_JS+'\n';changed=True
    path.write_text(text,encoding='utf-8')
    if "window.LM_LOAD_STATS=load" not in text or text.count('fetch(')!=1:
        raise ValueError('Shared statistics loader validation failed')
    if mode=='dynamic' and ("dataStatsVersion" in text or "cache:'default'" not in text or "statsUrl" not in text):
        raise ValueError('Versioned statistics loader contract failed')
    for marker in (SHARE_MARKER,'xsmb_profile_share','xsmb_deep_link_open','lm_stats_recent_v1','xsmb_stats_resume'):
        if marker not in text: raise ValueError(f'Statistics retention contract failed: {marker}')
    css_path=root/'xsmb-stats.css'
    css_changed=False
    if css_path.is_file():
        css=css_path.read_text(encoding='utf-8')
        if '.lm-stats-profile-actions' not in css:
            css=css.rstrip()+'\n'+SHARE_CSS.strip()+'\n';css_path.write_text(css,encoding='utf-8');css_changed=True
    return {'status':'PASS','changed':changed or css_changed,'shared_loader':True,'mode':mode,'share_state':True,'resume_state':True,'mobile_grid':True}


def self_test()->None:
    import tempfile
    for mode,old,expected in [('legacy',LEGACY_OLD,LEGACY_NEW),('dynamic',DYNAMIC_OLD,DYNAMIC_NEW)]:
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'xsmb-stats.js';p.write_text(old+'console.log(1)})();',encoding='utf-8');css=root/'xsmb-stats.css';css.write_text('.grid{}',encoding='utf-8')
            result=apply(root);t=p.read_text(encoding='utf-8');c=css.read_text(encoding='utf-8')
            assert result['changed'] and result['mode']==mode and expected in t
            assert 'window.LM_LOAD_STATS=load' in t and t.count('fetch(')==1
            for marker in (SHARE_MARKER,'xsmb_profile_share','xsmb_deep_link_open','lm_stats_recent_v1','xsmb_stats_resume'):
                assert marker in t
            assert '.lm-stats-profile-actions' in c and '.lm-stats-resume' in c and 'repeat(4,minmax(0,1fr))' in c
            assert apply(root)['changed'] is False
    print('SHARED_STATISTICS_LOADER_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
