#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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


def sitemap_urls(path:Path)->list[str]:
    tree=ET.parse(path);ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
    urls=[]
    for node in tree.getroot().findall(ns+'url'):
        loc=node.find(ns+'loc');url=(loc.text or '').strip() if loc is not None else ''
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.netloc!=HOST:
            raise ValueError(f'Unexpected sitemap URL: {url}')
        urls.append(url)
    urls=list(dict.fromkeys(urls))
    if not urls or len(urls)>10000:raise ValueError(f'Invalid URL count: {len(urls)}')
    return urls


def prepare(root:Path)->dict[str,object]:
    urls=sitemap_urls(root/'sitemap.xml')
    key_file=root/f'{KEY}.txt';key_file.write_text(KEY,encoding='utf-8')
    payload={'host':HOST,'key':KEY,'keyLocation':f'{BASE}/{KEY}.txt','urlList':urls}
    (root/'indexnow-payload.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'status':'READY','urls':len(urls),'key_file':key_file.name}


def submit(root:Path)->dict[str,object]:
    ready=prepare(root)
    payload=json.loads((root/'indexnow-payload.json').read_text(encoding='utf-8'))
    body=json.dumps(payload,separators=(',',':')).encode('utf-8')
    request=urllib.request.Request(ENDPOINT,data=body,headers={'Content-Type':'application/json; charset=utf-8','User-Agent':'lemienbac-indexnow/1.0'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            code=int(response.status);response_body=response.read(500).decode('utf-8','replace')
    except urllib.error.HTTPError as exc:
        code=int(exc.code);response_body=exc.read(500).decode('utf-8','replace')
    result={**ready,'http_status':code,'accepted':code in (200,202),'response':response_body[:200]}
    if not result['accepted']:
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
    print('INDEXNOW_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--prepare',action='store_true');p.add_argument('--submit',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test();return
    if a.submit:print(json.dumps(submit(a.output_root),ensure_ascii=False));return
    print(json.dumps(prepare(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
