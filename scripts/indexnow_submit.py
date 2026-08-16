#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
BASE='https://lemienbac.com'
HOST='lemienbac.com'
KEY='1e867f1b0577cda0167ab3317c2016d332d374e9c6921e95'
ENDPOINT='https://api.indexnow.org/indexnow'
USER_AGENT='lemienbac-indexnow/1.1'


def validate_urls(urls:list[str])->list[str]:
    urls=list(dict.fromkeys(urls))
    if not urls or len(urls)>10000:raise ValueError(f'Invalid URL count: {len(urls)}')
    for url in urls:
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.netloc!=HOST:
            raise ValueError(f'Unexpected sitemap URL: {url}')
    return urls


def sitemap_urls(path:Path)->list[str]:
    return sitemap_urls_bytes(path.read_bytes())


def sitemap_urls_bytes(raw:bytes)->list[str]:
    tree=ET.parse(io.BytesIO(raw));ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
    urls=[]
    for node in tree.getroot().findall(ns+'url'):
        loc=node.find(ns+'loc');url=(loc.text or '').strip() if loc is not None else ''
        if url:urls.append(url)
    return validate_urls(urls)


def payload_for(urls:list[str])->dict[str,object]:
    return {'host':HOST,'key':KEY,'keyLocation':f'{BASE}/{KEY}.txt','urlList':validate_urls(urls)}


def prepare(root:Path)->dict[str,object]:
    # Final-release housekeeping: remove forbidden display remnants first.
    import optimize_monetization_placement as monetization
    placement=monetization.apply(root)

    # Last HTML mutation before artifact readiness. Synthetic self-test roots
    # intentionally omit the commerce block and therefore skip this stage.
    surface={'status':'SKIP','reason':'missing_real_home_commerce_surface'}
    home=root/'index.html'
    if home.is_file() and (root/'report-readiness.json').is_file():
        home_text=home.read_text(encoding='utf-8')
        if 'buy-simple portal-buy' in home_text:
            import final_revenue_surface as revenue_surface
            surface=revenue_surface.apply(root)

    urls=sitemap_urls(root/'sitemap.xml')
    key_file=root/f'{KEY}.txt';key_file.write_text(KEY,encoding='utf-8')
    payload=payload_for(urls)
    (root/'indexnow-payload.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'status':'READY','urls':len(urls),'key_file':key_file.name,'monetization_placement':placement,'final_revenue_surface':surface}


def fetch_live(url:str)->bytes:
    request=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=20) as response:
        if int(response.status)!=200:raise RuntimeError(f'GET {url}: HTTP {response.status}')
        return response.read(2_000_000)


def post_payload(payload:dict[str,object])->dict[str,object]:
    body=json.dumps(payload,separators=(',',':')).encode('utf-8')
    request=urllib.request.Request(ENDPOINT,data=body,headers={'Content-Type':'application/json; charset=utf-8','User-Agent':USER_AGENT},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            code=int(response.status);response_body=response.read(500).decode('utf-8','replace')
    except urllib.error.HTTPError as exc:
        code=int(exc.code);response_body=exc.read(500).decode('utf-8','replace')
    accepted=code in (200,202)
    deferred=code==429
    return {'http_status':code,'accepted':accepted,'deferred':deferred,'response':response_body[:200]}


def submit(root:Path)->dict[str,object]:
    ready=prepare(root)
    payload=json.loads((root/'indexnow-payload.json').read_text(encoding='utf-8'))
    result={**ready,**post_payload(payload)}
    if not result['accepted'] and not result['deferred']:
        print(json.dumps(result,ensure_ascii=False))
        raise SystemExit(1)
    return result


def submit_live()->dict[str,object]:
    sitemap_raw=fetch_live(f'{BASE}/sitemap.xml?indexnow=1')
    urls=sitemap_urls_bytes(sitemap_raw)
    key_url=f'{BASE}/{KEY}.txt?verify=1'
    key_raw=fetch_live(key_url).decode('utf-8','replace').strip()
    if key_raw!=KEY:raise RuntimeError('Live IndexNow key verification failed')
    result={'status':'LIVE_VERIFIED','urls':len(urls),'key_verified':True,**post_payload(payload_for(urls))}
    if not result['accepted'] and not result['deferred']:
        print(json.dumps(result,ensure_ascii=False))
        raise SystemExit(1)
    return result


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);root.joinpath('sitemap.xml').write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://lemienbac.com/</loc></url><url><loc>https://lemienbac.com/thong-ke-xsmb/</loc></url></urlset>',encoding='utf-8')
        result=prepare(root);payload=json.loads((root/'indexnow-payload.json').read_text())
        assert result['urls']==2 and (root/f'{KEY}.txt').read_text()==KEY
        assert payload['host']==HOST and payload['keyLocation'].endswith(f'/{KEY}.txt') and len(payload['urlList'])==2
        assert sitemap_urls_bytes((root/'sitemap.xml').read_bytes())==payload['urlList']
        assert result['monetization_placement']['status']=='SKIP'
        assert result['final_revenue_surface']['status']=='SKIP'
    print('INDEXNOW_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--prepare',action='store_true');p.add_argument('--submit',action='store_true');p.add_argument('--submit-live',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test();return
    if a.submit_live:print(json.dumps(submit_live(),ensure_ascii=False));return
    if a.submit:print(json.dumps(submit(a.output_root),ensure_ascii=False));return
    print(json.dumps(prepare(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
