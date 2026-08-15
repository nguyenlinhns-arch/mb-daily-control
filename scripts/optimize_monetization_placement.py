#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BANNER_ID='lm-adsterra-300x250'
NATIVE_ID='lm-adsterra-native'
NATIVE_SRC='https://pl30863058.effectivecpmnetwork.com/e336b428517bbcb55a3e3da308cc7939/invoke.js'
BANNER_SRC='https://www.highperformanceformat.com/b3caa39744fc30610e7756cf4ccb98cd/invoke.js'
BUY_MARKER='<section class="buy-simple portal-buy"'
SEO_LINKS_MARKER='data-seo-discovery-links="true"'
SEO_LINKS='''<div class="portal-fast-links" data-seo-discovery-links="true" aria-label="Dữ liệu XSMB chuyên sâu"><a href="/xsmb-30-ngay/">XSMB 30 ngày</a><a href="/nguon-du-lieu-xsmb/">Nguồn dữ liệu &amp; cách tính</a></div>'''
AD_STYLE='''<style id="lm-final-monetization-style">.lm-ad-slot{width:100%;padding:8px 0}.lm-ad-inner{max-width:1180px;margin:auto;padding:0 16px;text-align:center}.lm-ad-label{margin:0 0 6px;color:#8a969e;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}.lm-ad-box{min-height:90px;display:flex;align-items:center;justify-content:center;overflow:hidden}.lm-ad-box--300{width:300px;min-height:250px;margin:auto;max-width:100vw}.lm-ad-box iframe{max-width:100%}@media(max-width:700px){.lm-ad-slot{padding:6px 0}.lm-ad-inner{padding:0 10px}.lm-ad-label{margin-bottom:4px}.lm-ad-box--300{max-width:300px}.lm-ad-box{overflow:hidden}}</style>'''
NATIVE_HTML=f'''<section class="lm-ad-slot" aria-label="Quảng cáo"><div class="lm-ad-inner"><p class="lm-ad-label">Quảng cáo</p><div class="lm-ad-box" id="{NATIVE_ID}" data-lm-ad-slot="native"><span data-lm-native-ad-src="{NATIVE_SRC}" hidden></span><div id="container-e336b428517bbcb55a3e3da308cc7939"></div></div></div></section>'''
BANNER_HTML=f'''<section class="lm-ad-slot" aria-label="Quảng cáo"><div class="lm-ad-inner"><p class="lm-ad-label">Quảng cáo</p><div class="lm-ad-box lm-ad-box--300" id="{BANNER_ID}" data-lm-ad-slot="banner-300"><script>atOptions={{'key':'b3caa39744fc30610e7756cf4ccb98cd','format':'iframe','height':250,'width':300,'params':{{}}}};</script><script src="{BANNER_SRC}"></script></div></div></section>'''


def section_bounds(text:str,needle:str)->tuple[int,int]|None:
    pos=text.find(needle)
    if pos<0:return None
    start=pos if text.startswith('<section',pos) else text.rfind('<section',0,pos)
    end=text.find('</section>',pos)
    if start<0 or end<0:return None
    return start,end+len('</section>')


def ensure_ad_style(text:str)->tuple[str,bool]:
    if 'id="lm-final-monetization-style"' in text:return text,False
    if '</head>' not in text:raise ValueError('Missing </head> for monetization style')
    return text.replace('</head>',AD_STYLE+'</head>',1),True


def ensure_native(text:str)->tuple[str,bool]:
    if NATIVE_ID in text:return text,False
    methods=section_bounds(text,'<h2>Phương pháp công khai')
    if not methods:methods=section_bounds(text,'portal-methods')
    if methods:
        insert=methods[1]
        return text[:insert]+'\n'+NATIVE_HTML+'\n'+text[insert:],True
    buy=section_bounds(text,BUY_MARKER)
    if buy:
        insert=buy[0]
        return text[:insert]+NATIVE_HTML+'\n'+text[insert:],True
    raise ValueError('Cannot find safe native ad placement')


def ensure_banner_after_buy(text:str)->tuple[str,bool,str]:
    buy=section_bounds(text,BUY_MARKER)
    if not buy:raise ValueError('Buy section missing')
    ad=section_bounds(text,BANNER_ID)
    if not ad:
        insert=buy[1]
        text=text[:insert]+'\n'+BANNER_HTML+'\n'+text[insert:]
        return text,True,'after_buy'
    a0,a1=ad;b0,b1=buy
    if a0>b1:return text,False,'after_buy'
    block=text[a0:a1]
    text=text[:a0]+text[a1:]
    buy=section_bounds(text,BUY_MARKER)
    if not buy:raise ValueError('Buy section disappeared after banner removal')
    insert=buy[1]
    text=text[:insert]+'\n'+block+'\n'+text[insert:]
    return text,True,'after_buy'


def ensure_static_seo_links(text:str)->tuple[str,bool]:
    if SEO_LINKS_MARKER in text:return text,False
    marker='<div class="portal-tools">'
    start=text.find(marker)
    if start<0:return text,False
    end=text.find('</div>',start+len(marker))
    if end<0:return text,False
    end+=len('</div>')
    return text[:end]+SEO_LINKS+text[end:],True


def normalize_affiliate_copy(text:str)->tuple[str,bool]:
    before=text
    text=re.sub(r'Ưu đãi mua sắm Shopee(?:\s+ngày\s+\d{2}/\d{2}/\d{4})?', 'Ưu đãi mua sắm Shopee', text)
    text=text.replace('Smartlink ACCESSTRADE · xem sản phẩm và ưu đãi đang được giới thiệu.','Liên kết tài trợ ACCESSTRADE · mở Shopee để xem sản phẩm và ưu đãi hiện có.')
    text=text.replace('aria-label="Liên kết đối tác"','aria-label="Liên kết tài trợ"')
    return text,text!=before


def convert_existing_native_to_lazy(text:str)->tuple[str,bool]:
    if NATIVE_ID not in text:return text,False
    changed=False
    if 'data-lm-native-ad-src=' not in text:
        pattern=re.compile(r'<script\s+async="async"\s+data-cfasync="false"\s+src="'+re.escape(NATIVE_SRC)+r'"></script>',re.I)
        replacement=f'<span data-lm-native-ad-src="{NATIVE_SRC}" hidden></span>'
        text,count=pattern.subn(replacement,text,count=1)
        changed=bool(count)
    if f'id="{NATIVE_ID}" data-lm-ad-slot=' not in text:
        text=text.replace(f'id="{NATIVE_ID}"',f'id="{NATIVE_ID}" data-lm-ad-slot="native"',1);changed=True
    if f'id="{BANNER_ID}" data-lm-ad-slot=' not in text:
        text=text.replace(f'id="{BANNER_ID}"',f'id="{BANNER_ID}" data-lm-ad-slot="banner-300"',1);changed=True
    return text,changed


def apply(root:Path)->dict[str,object]:
    path=root/'index.html'
    if not path.is_file():return {'status':'SKIP','reason':'missing_home'}
    text=path.read_text(encoding='utf-8')
    text,style_changed=ensure_ad_style(text)
    text,native_injected=ensure_native(text)
    text,native_converted=convert_existing_native_to_lazy(text)
    text,banner_changed,placement=ensure_banner_after_buy(text)
    text,seo_changed=ensure_static_seo_links(text)
    text,affiliate_changed=normalize_affiliate_copy(text)
    path.write_text(text,encoding='utf-8')
    if text.find(BANNER_ID)<text.find(BUY_MARKER):raise ValueError('Banner placement invariant failed')
    if text.count(NATIVE_ID)!=1 or text.count(BANNER_ID)!=1:raise ValueError('Ad slot uniqueness failed')
    if 'data-lm-native-ad-src=' not in text or NATIVE_SRC not in text:raise ValueError('Native lazy-load marker missing')
    if f'<script async="async" data-cfasync="false" src="{NATIVE_SRC}"></script>' in text:raise ValueError('Native ad remains eager')
    if BANNER_SRC not in text:raise ValueError('300x250 banner source missing')
    if SEO_LINKS_MARKER not in text or '/xsmb-30-ngay/' not in text or '/nguon-du-lieu-xsmb/' not in text:raise ValueError('Static SEO discovery links missing')
    if re.search(r'Ưu đãi mua sắm Shopee\s+ngày\s+\d{2}/\d{2}/\d{4}',text):raise ValueError('Affiliate copy is incorrectly tied to report date')
    return {'status':'PASS','changed':any((style_changed,native_injected,native_converted,banner_changed,seo_changed,affiliate_changed)),'placement':placement,'static_seo_links':True,'affiliate_evergreen':True,'native_lazy':True,'adsterra_native':True,'adsterra_banner_300':True}


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);p=root/'index.html'
        p.write_text('<html><head></head><body><section><div class="portal-tools"><a href="/a/">A</a></div></section><section><h2>Phương pháp công khai ngày 16/08/2026</h2></section><section aria-label="Liên kết đối tác"><a id="affiliate-shopee-smartlink"><b>Ưu đãi mua sắm Shopee ngày 16/08/2026</b><span>Smartlink ACCESSTRADE · xem sản phẩm và ưu đãi đang được giới thiệu.</span></a></section><section class="buy-simple portal-buy"><b>Mua</b></section><footer></footer></body></html>',encoding='utf-8')
        result=apply(root);t=p.read_text(encoding='utf-8')
        assert result['changed'] and result['adsterra_native'] and result['adsterra_banner_300']
        assert t.find(BUY_MARKER)<t.find(BANNER_ID) and t.count(BANNER_ID)==1 and t.count(NATIVE_ID)==1
        assert result['static_seo_links'] and result['native_lazy'] and result['affiliate_evergreen']
        assert 'data-lm-native-ad-src=' in t and NATIVE_SRC in t and BANNER_SRC in t
        assert 'Ưu đãi mua sắm Shopee ngày' not in t and 'Liên kết tài trợ ACCESSTRADE' in t
        assert apply(root)['changed'] is False
        other=Path(td)/'missing';other.mkdir();assert apply(other)['status']=='SKIP'
    print('MONETIZATION_PLACEMENT_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
