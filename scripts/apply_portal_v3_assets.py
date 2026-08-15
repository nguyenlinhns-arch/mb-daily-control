#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CSS='<link rel="stylesheet" href="/portal-v3.css?v=20260815-1">'
SENSITIVE={'phuong-phap-4so/index.html','lich-su-doi-chieu/index.html'}
SCHEMA_RE=re.compile(r'<script type="application/ld\+json">(?:(?!</script>).)*"@id":"https://lemienbac\.com/#portal-v3"(?:(?!</script>).)*</script>',re.S)

def apply(root:Path)->dict[str,int]:
    n=0; stripped=0
    for p in root.rglob('*.html'):
        t=p.read_text(encoding='utf-8')
        rel=p.relative_to(root).as_posix()
        if rel in SENSITIVE:
            t2,count=SCHEMA_RE.subn('',t,count=1)
            if count:
                t=t2; stripped+=1
        if 'portal-v3.css' not in t:
            t=t.replace('</head>',CSS+'</head>',1)
        p.write_text(t,encoding='utf-8')
        n+=1
    return {'pages':n,'sensitive_schema_removed':stripped}

def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/'phuong-phap-4so').mkdir();
        (r/'phuong-phap-4so/index.html').write_text('<html><head><script type="application/ld+json">{"@id":"https://lemienbac.com/#portal-v3","name":"4SO","dateModified":"2026-08-15"}</script></head><body></body></html>',encoding='utf-8')
        result=apply(r); text=(r/'phuong-phap-4so/index.html').read_text(encoding='utf-8')
        assert result['pages']==1 and result['sensitive_schema_removed']==1 and 'portal-v3.css' in text and '#portal-v3' not in text
    print('PORTAL_V3_ASSETS_SELF_TEST_OK')

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root)))
if __name__=='__main__':main()
