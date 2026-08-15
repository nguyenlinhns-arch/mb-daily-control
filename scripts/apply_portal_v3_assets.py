#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CSS='<link rel="stylesheet" href="/portal-v3.css?v=20260815-1">'

def apply(root:Path)->dict[str,int]:
    n=0
    for p in root.rglob('*.html'):
        t=p.read_text(encoding='utf-8')
        if 'portal-v3.css' not in t:
            t=t.replace('</head>',CSS+'</head>',1)
            p.write_text(t,encoding='utf-8')
        n+=1
    return {'pages':n}

def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/'index.html').write_text('<html><head></head><body></body></html>',encoding='utf-8')
        assert apply(r)['pages']==1 and 'portal-v3.css' in (r/'index.html').read_text(encoding='utf-8')
    print('PORTAL_V3_ASSETS_SELF_TEST_OK')

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root)))
if __name__=='__main__':main()
