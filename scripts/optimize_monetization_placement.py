#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BANNER_ID='lm-adsterra-300x250'
BUY_MARKER='<section class="buy-simple portal-buy"'
MOBILE_MARKER='<!-- LM_ADSTERRA_320X50_SLOT_PENDING -->'


def section_bounds(text:str,needle:str)->tuple[int,int]|None:
    pos=text.find(needle)
    if pos<0:return None
    start=text.rfind('<section',0,pos)
    end=text.find('</section>',pos)
    if start<0 or end<0:return None
    return start,end+len('</section>')


def apply(root:Path)->dict[str,object]:
    path=root/'index.html'
    if not path.is_file():return {'status':'SKIP','reason':'missing_home'}
    text=path.read_text(encoding='utf-8')
    ad=section_bounds(text,BANNER_ID);buy=section_bounds(text,BUY_MARKER)
    if not ad or not buy:
        return {'status':'SKIP','reason':'ad_or_buy_missing'}
    a0,a1=ad;b0,b1=buy
    if a0>b1:
        return {'status':'PASS','changed':False,'placement':'after_buy'}
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
    path.write_text(text,encoding='utf-8')
    if text.find(BANNER_ID)<text.find(BUY_MARKER):raise ValueError('Banner still before buy section')
    return {'status':'PASS','changed':True,'placement':'after_buy'}


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);p=root/'index.html'
        p.write_text('<html><body><section><div id="lm-adsterra-300x250"></div></section>'+MOBILE_MARKER+'\n<section class="buy-simple portal-buy"><b>Mua</b></section><footer></footer></body></html>',encoding='utf-8')
        result=apply(root);t=p.read_text(encoding='utf-8')
        assert result['changed'] and t.find(BUY_MARKER)<t.find(BANNER_ID) and t.count(BANNER_ID)==1
        assert apply(root)['changed'] is False
        other=Path(td)/'missing';other.mkdir();assert apply(other)['status']=='SKIP'
    print('MONETIZATION_PLACEMENT_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
