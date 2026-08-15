#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='https://lemienbac.com'
GA4='G-R9TBYP97BC'
TITLE_OVERRIDES={
    '/phuong-phap-cong-khai/':'6 phương pháp XSMB công khai hôm nay | Lê Miền Bắc',
}


def route_for(path:Path,root:Path)->str:
    rel=path.relative_to(root).as_posix()
    if rel=='index.html':return '/'
    if rel.endswith('/index.html'):return '/'+rel[:-10]
    return '/'+rel


def get_title(text:str)->str:
    m=re.search(r'<title>(.*?)</title>',text,re.I|re.S)
    return html.unescape(re.sub(r'<[^>]+>','',m.group(1)).strip()) if m else 'Lê Miền Bắc'


def get_desc(text:str)->str:
    m=re.search(r'<meta\s+name="description"\s+content="([^"]*)"',text,re.I)
    return html.unescape(m.group(1)).strip() if m else 'Cổng dữ liệu và thống kê XSMB.'


def upsert_meta(text:str,attr:str,key:str,value:str)->str:
    value=html.escape(value,quote=True)
    pattern=re.compile(rf'<meta\s+{attr}="{re.escape(key)}"\s+content="[^"]*"\s*/?>',re.I)
    tag=f'<meta {attr}="{key}" content="{value}">'
    if pattern.search(text):return pattern.sub(tag,text,count=1)
    return text.replace('</head>',tag+'</head>',1)


def enrich(path:Path,root:Path)->bool:
    text=path.read_text(encoding='utf-8'); before=text
    route=route_for(path,root)
    if route in TITLE_OVERRIDES:
        title_tag='<title>'+html.escape(TITLE_OVERRIDES[route])+'</title>'
        if re.search(r'<title>.*?</title>',text,re.I|re.S):text=re.sub(r'<title>.*?</title>',title_tag,text,count=1,flags=re.I|re.S)
        else:text=text.replace('</head>',title_tag+'</head>',1)
    title=get_title(text); desc=get_desc(text); url=BASE+route
    robots=re.search(r'<meta\s+name="robots"\s+content="([^"]+)"',text,re.I)
    noindex=bool(robots and 'noindex' in robots.group(1).lower())
    if not noindex:
        has_og_image=bool(re.search(r'<meta\s+property="og:image"\s+content="[^"]+"',text,re.I))
        twitter_card='summary_large_image' if has_og_image else 'summary'
        for attr,key,value in (
            ('property','og:locale','vi_VN'),('property','og:type','website'),('property','og:url',url),
            ('property','og:title',title),('property','og:description',desc),
            ('name','twitter:card',twitter_card),('name','twitter:title',title),('name','twitter:description',desc),
        ):
            text=upsert_meta(text,attr,key,value)
    if GA4 not in text and not noindex:
        block=f'''<link rel="preconnect" href="https://www.googletagmanager.com" crossorigin><script async src="https://www.googletagmanager.com/gtag/js?id={GA4}"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{GA4}',{{allow_google_signals:false,allow_ad_personalization_signals:false}});</script>'''
        text=text.replace('</head>',block+'</head>',1)
    if text!=before:path.write_text(text,encoding='utf-8')
    return text!=before


def apply(root:Path)->dict[str,int]:
    pages=changed=ga4=0
    for path in root.rglob('*.html'):
        pages+=1; changed+=int(enrich(path,root))
        if GA4 in path.read_text(encoding='utf-8'):ga4+=1
    return {'pages':pages,'changed':changed,'ga4_pages':ga4}


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root/'phuong-phap-cong-khai').mkdir()
        p=root/'phuong-phap-cong-khai/index.html';p.write_text('<html><head><title>Tiêu đề cũ rất dài</title><meta name="description" content="Mô tả thử đủ dài để kiểm tra metadata"><meta name="robots" content="index,follow"><meta property="og:image" content="https://example.test/a.png"></head><body></body></html>',encoding='utf-8')
        result=apply(root);t=p.read_text(encoding='utf-8')
        assert result['pages']==1 and GA4 in t and 'og:title' in t and 'og:url' in t and 'twitter:description' in t
        assert 'twitter:card" content="summary_large_image' in t and '6 phương pháp XSMB công khai hôm nay' in t
    print('PORTAL_METADATA_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
