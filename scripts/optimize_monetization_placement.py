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
BUY_MARKER='<section class="buy-simple portal-buy"'
MOBILE_MARKER='<!-- LM_ADSTERRA_320X50_SLOT_PENDING -->'
SEO_LINKS_MARKER='data-seo-discovery-links="true"'
SEO_LINKS='''<div class="portal-fast-links" data-seo-discovery-links="true" aria-label="Dữ liệu XSMB chuyên sâu"><a href="/xsmb-30-ngay/">XSMB 30 ngày</a><a href="/nguon-du-lieu-xsmb/">Nguồn dữ liệu &amp; cách tính</a></div>'''


def section_bounds(text:str,needle:str)->tuple[int,int]|None:
    pos=text.find(needle)
    if pos<0:return None
    start=pos if text.startswith('<section',pos) else text.rfind('<section',0,pos)
    end=text.find('</section>',pos)
    if start<0 or end<0:return None
    return start,end+len('</section>')


def ensure_banner_after_buy(text:str)->tuple[str,bool,str]:
    ad=section_bounds(text,BANNER_ID);buy=section_bounds(text,BUY_MARKER)
    if not ad or not buy:return text,False,'missing'
    a0,a1=ad;b0,b1=buy
    if a0>b1:return text,False,'after_buy'
    block=text[a0:a1]
    before=text[max(0,a0-len(MOBILE_MARKER)-2):a0]
    marker=MOBILE_MARKER if MOBILE_MARKER in before else ''
    remove0=a0
    if marker:
        marker_pos=text.rfind(MOBILE_MARKER,0,a0)
        if marker_pos>=0 and text[marker_pos+len(MOBILE_MARKER):a0].strip()=='':remove0=marker_pos
    text=text[:remove0]+text[a1:]
    buy=section_bounds(text,BUY_MARKER)
    if not buy:raise ValueError('Buy section disappeared after ad removal')
    insert=buy[1]
    payload='\n'+block+(marker and '\n'+marker or '')+'\n'
    text=text[:insert]+payload+text[insert:]
    if text.find(BANNER_ID)<text.find(BUY_MARKER):raise ValueError('Banner still before buy section')
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


def lazy_native_ad(text:str)->tuple[str,bool]:
    if 'data-lm-native-ad-src=' in text:return text,False
    pattern=re.compile(r'<script\s+async="async"\s+data-cfasync="false"\s+src="'+re.escape(NATIVE_SRC)+r'"></script>',re.I)
    if not pattern.search(text):return text,False
    replacement=f'<span data-lm-native-ad-src="{NATIVE_SRC}" hidden></span>'
    text=pattern.sub(replacement,text,count=1)
    text=text.replace(f'id="{NATIVE_ID}"',f'id="{NATIVE_ID}" data-lm-ad-slot="native"',1)
    text=text.replace(f'id="{BANNER_ID}"',f'id="{BANNER_ID}" data-lm-ad-slot="banner-300"',1)
    return text,True


def apply(root:Path)->dict[str,object]:
    path=root/'index.html'
    if not path.is_file():return {'status':'SKIP','reason':'missing_home'}
    text=path.read_text(encoding='utf-8')
    if not section_bounds(text,BANNER_ID) or not section_bounds(text,BUY_MARKER):
        return {'status':'SKIP','reason':'ad_or_buy_missing'}

    text,banner_changed,placement=ensure_banner_after_buy(text)
    text,seo_changed=ensure_static_seo_links(text)
    text,affiliate_changed=normalize_affiliate_copy(text)
    text,native_changed=lazy_native_ad(text)
    path.write_text(text,encoding='utf-8')

    if text.find(BANNER_ID)<text.find(BUY_MARKER):raise ValueError('Banner placement invariant failed')
    if SEO_LINKS_MARKER not in text or '/xsmb-30-ngay/' not in text or '/nguon-du-lieu-xsmb/' not in text:
        raise ValueError('Static SEO discovery links missing')
    if NATIVE_SRC in text and 'data-lm-native-ad-src=' not in text:
        raise ValueError('Native ad remains eager')
    if re.search(r'Ưu đãi mua sắm Shopee\s+ngày\s+\d{2}/\d{2}/\d{4}',text):
        raise ValueError('Affiliate copy is incorrectly tied to report date')

    return {
        'status':'PASS',
        'changed':banner_changed or seo_changed or affiliate_changed or native_changed,
        'placement':placement,
        'static_seo_links':SEO_LINKS_MARKER in text,
        'affiliate_evergreen':True,
        'native_lazy':'data-lm-native-ad-src=' in text,
    }


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);p=root/'index.html'
        p.write_text(
            '<html><body><section><div id="lm-adsterra-300x250"></div></section>'+MOBILE_MARKER+'\n'
            '<section><div class="portal-tools"><a href="/a/">A</a></div></section>'
            '<section aria-label="Liên kết đối tác"><a id="affiliate-shopee-smartlink"><b>Ưu đãi mua sắm Shopee ngày 16/08/2026</b><span>Smartlink ACCESSTRADE · xem sản phẩm và ưu đãi đang được giới thiệu.</span></a></section>'
            '<section><div id="lm-adsterra-native"><script async="async" data-cfasync="false" src="'+NATIVE_SRC+'"></script><div id="container-native"></div></div></section>'
            '<section class="buy-simple portal-buy"><b>Mua</b></section><footer></footer></body></html>',
            encoding='utf-8'
        )
        result=apply(root);t=p.read_text(encoding='utf-8')
        assert result['changed'] and t.find(BUY_MARKER)<t.find(BANNER_ID) and t.count(BANNER_ID)==1
        assert result['static_seo_links'] and result['native_lazy'] and result['affiliate_evergreen']
        assert 'data-lm-native-ad-src=' in t and '<script async="async" data-cfasync="false" src="'+NATIVE_SRC not in t
        assert 'Ưu đãi mua sắm Shopee ngày' not in t and 'Liên kết tài trợ ACCESSTRADE' in t
        assert apply(root)['changed'] is False
        other=Path(td)/'missing';other.mkdir();assert apply(other)['status']=='SKIP'
    print('MONETIZATION_PLACEMENT_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
