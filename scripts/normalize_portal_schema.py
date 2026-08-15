#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
BLOCK=re.compile(r'<script type="application/ld\+json">(.*?)</script>',re.I|re.S)
V3_ID='https://lemienbac.com/#portal-v3'
STATS={
 'thong-ke-xsmb/index.html','tan-suat-xsmb/index.html','lo-gan-xsmb/index.html',
 'cap-dao-xsmb/index.html','tra-cuu-xsmb/index.html',
}
RICH_SEO={
 'cho-so-mien-bac-hom-nay/index.html','thong-ke-lo-to-mien-bac-bang-ai/index.html','gioi-thieu/index.html',
}


def replace_brand(value:Any)->Any:
    if isinstance(value,str): return value.replace('Lê Miền Bắc AI','Lê Miền Bắc')
    if isinstance(value,list): return [replace_brand(x) for x in value]
    if isinstance(value,dict): return {k:replace_brand(v) for k,v in value.items()}
    return value


def types_in(value:Any)->set[str]:
    out:set[str]=set()
    if isinstance(value,dict):
        t=value.get('@type')
        if isinstance(t,str):out.add(t)
        elif isinstance(t,list):out.update(str(x) for x in t)
        for v in value.values():out|=types_in(v)
    elif isinstance(value,list):
        for v in value:out|=types_in(v)
    return out


def render(doc:dict[str,Any])->str:
    return '<script type="application/ld+json">'+json.dumps(doc,ensure_ascii=False,separators=(',',':'))+'</script>'


def process(path:Path,root:Path)->dict[str,int]:
    rel=path.relative_to(root).as_posix(); text=path.read_text(encoding='utf-8')
    matches=list(BLOCK.finditer(text))
    if not matches:return {'removed':0,'updated':0}
    docs=[]
    for m in matches:
        try: docs.append(json.loads(m.group(1)))
        except Exception: docs.append(None)
    remove:set[int]=set(); replacements:dict[int,str]={}; updated=0
    if rel in RICH_SEO:
        for i,d in enumerate(docs):
            if isinstance(d,dict) and d.get('@id')==V3_ID:remove.add(i)
    if rel in STATS:
        v3=[i for i,d in enumerate(docs) if isinstance(d,dict) and d.get('@id')==V3_ID]
        if v3:
            keep=v3[-1]
            for i,d in enumerate(docs):
                if i==keep or not isinstance(d,dict):continue
                ts=types_in(d)
                if 'Dataset' in ts and 'WebPage' in ts:remove.add(i)
    if rel=='index.html':
        for i,d in enumerate(docs):
            if not isinstance(d,dict):continue
            if d.get('@id')==V3_ID:
                graph=d.get('@graph')
                if isinstance(graph,list):
                    d['@graph']=[node for node in graph if not (isinstance(node,dict) and node.get('@type')=='WebSite')]
                    replacements[i]=render(d);updated+=1
            else:
                d2=replace_brand(d)
                if d2!=d:replacements[i]=render(d2);updated+=1
    if not remove and not replacements:return {'removed':0,'updated':0}
    parts=[];last=0
    for i,m in enumerate(matches):
        parts.append(text[last:m.start()])
        if i not in remove:
            parts.append(replacements.get(i,m.group(0)))
        last=m.end()
    parts.append(text[last:])
    path.write_text(''.join(parts),encoding='utf-8')
    return {'removed':len(remove),'updated':updated}


def apply(root:Path)->dict[str,int]:
    pages=removed=updated=0
    for path in root.rglob('*.html'):
        pages+=1;r=process(path,root);removed+=r['removed'];updated+=r['updated']
    # Verify pages with v3 schema have no duplicated WebPage or Dataset blocks.
    for path in root.rglob('*.html'):
        docs=[]
        for raw in BLOCK.findall(path.read_text(encoding='utf-8')):
            try:docs.append(json.loads(raw))
            except Exception:continue
        web=sum('WebPage' in types_in(d) for d in docs)
        dataset=sum('Dataset' in types_in(d) for d in docs)
        rel=path.relative_to(root).as_posix()
        if rel in STATS and (web>1 or dataset>1):raise ValueError(f'duplicate structured data: {rel}')
    return {'pages':pages,'blocks_removed':removed,'blocks_updated':updated}


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r=Path(td);(r/'thong-ke-xsmb').mkdir()
        old={'@context':'https://schema.org','@graph':[{'@type':'WebPage'},{'@type':'Dataset'}]}
        new={'@context':'https://schema.org','@id':V3_ID,'@graph':[{'@type':'WebPage'},{'@type':'BreadcrumbList'},{'@type':'Dataset'}]}
        p=r/'thong-ke-xsmb/index.html';p.write_text('<html><head>'+render(old)+render(new)+'</head></html>',encoding='utf-8')
        result=apply(r);text=p.read_text(encoding='utf-8')
        assert result['blocks_removed']==1 and text.count('application/ld+json')==1 and 'BreadcrumbList' in text
    print('PORTAL_SCHEMA_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
