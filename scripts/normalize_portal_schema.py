#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
BLOCK=re.compile(r'<script type="application/ld\+json">(.*?)</script>',re.I|re.S)
V3_ID='https://lemienbac.com/#portal-v3'
BRAND='Lê Miền Bắc'
STATS={
 'thong-ke-xsmb/index.html','tan-suat-xsmb/index.html','lo-gan-xsmb/index.html',
 'cap-dao-xsmb/index.html','tra-cuu-xsmb/index.html',
}
RICH_SEO={
 'cho-so-mien-bac-hom-nay/index.html','thong-ke-lo-to-mien-bac-bang-ai/index.html','gioi-thieu/index.html',
}


def types_of(node:dict[str,Any])->set[str]:
    raw=node.get('@type')
    if isinstance(raw,str):return {raw}
    if isinstance(raw,list):return {str(x) for x in raw}
    return set()


def types_in(value:Any)->set[str]:
    out:set[str]=set()
    if isinstance(value,dict):
        out|=types_of(value)
        for v in value.values():out|=types_in(v)
    elif isinstance(value,list):
        for v in value:out|=types_in(v)
    return out


def page_meta(text:str)->tuple[str,str]:
    title_m=re.search(r'<title>(.*?)</title>',text,re.I|re.S)
    desc_m=re.search(r'<meta\s+name="description"\s+content="([^"]*)"',text,re.I)
    title=html.unescape(re.sub(r'<[^>]+>','',title_m.group(1)).strip()) if title_m else BRAND
    desc=html.unescape(desc_m.group(1)).strip() if desc_m else 'Cổng dữ liệu và thống kê XSMB.'
    return title,desc


def align_schema(value:Any,title:str,desc:str)->Any:
    if isinstance(value,list):
        return [align_schema(x,title,desc) for x in value]
    if not isinstance(value,dict):
        return value
    node={k:align_schema(v,title,desc) for k,v in value.items()}
    types=types_of(node)
    if 'Organization' in types or 'WebSite' in types:
        node['name']=BRAND
    if 'WebPage' in types:
        node['name']=title
        node['description']=desc
    return node


def render(doc:dict[str,Any])->str:
    return '<script type="application/ld+json">'+json.dumps(doc,ensure_ascii=False,separators=(',',':'))+'</script>'


def process(path:Path,root:Path)->dict[str,int]:
    rel=path.relative_to(root).as_posix(); text=path.read_text(encoding='utf-8')
    title,desc=page_meta(text)
    matches=list(BLOCK.finditer(text))
    if not matches:return {'removed':0,'updated':0}
    docs=[]
    for m in matches:
        try: docs.append(json.loads(m.group(1)))
        except Exception: docs.append(None)
    remove:set[int]=set(); replacements:dict[int,str]={}; updated=0

    # Rich legacy SEO pages already have useful Organization/WebSite/FAQ schema.
    # Keep those and remove the simpler V3 duplicate block.
    if rel in RICH_SEO:
        for i,d in enumerate(docs):
            if isinstance(d,dict) and d.get('@id')==V3_ID:remove.add(i)

    # Core statistics pages keep the V3 WebPage + Breadcrumb + Dataset block,
    # removing the older duplicate WebPage/Dataset block.
    if rel in STATS:
        v3=[i for i,d in enumerate(docs) if isinstance(d,dict) and d.get('@id')==V3_ID]
        if v3:
            keep=v3[-1]
            for i,d in enumerate(docs):
                if i==keep or not isinstance(d,dict):continue
                ts=types_in(d)
                if 'Dataset' in ts and 'WebPage' in ts:remove.add(i)

    # Homepage keeps the richer legacy WebSite/Organization block. The V3 block
    # contributes the current WebPage only, so remove its duplicate WebSite node.
    for i,d in enumerate(docs):
        if not isinstance(d,dict) or i in remove:continue
        candidate=d
        if rel=='index.html' and d.get('@id')==V3_ID:
            graph=d.get('@graph')
            if isinstance(graph,list):
                candidate=dict(d)
                candidate['@graph']=[node for node in graph if not (isinstance(node,dict) and 'WebSite' in types_of(node))]
        aligned=align_schema(candidate,title,desc)
        if aligned!=d:
            replacements[i]=render(aligned);updated+=1

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

    for path in root.rglob('*.html'):
        text=path.read_text(encoding='utf-8')
        title,_=page_meta(text)
        docs=[]
        for raw in BLOCK.findall(text):
            try:docs.append(json.loads(raw))
            except Exception:continue
        web=sum('WebPage' in types_in(d) for d in docs)
        dataset=sum('Dataset' in types_in(d) for d in docs)
        rel=path.relative_to(root).as_posix()
        if rel in STATS and (web>1 or dataset>1):raise ValueError(f'duplicate structured data: {rel}')
        for d in docs:
            def visit(v:Any)->None:
                if isinstance(v,dict):
                    ts=types_of(v)
                    if ('Organization' in ts or 'WebSite' in ts) and v.get('name')!=BRAND:
                        raise ValueError(f'legacy schema brand remains: {rel}')
                    if 'WebPage' in ts and v.get('name')!=title:
                        raise ValueError(f'WebPage schema title mismatch: {rel}')
                    for child in v.values():visit(child)
                elif isinstance(v,list):
                    for child in v:visit(child)
            visit(d)
    return {'pages':pages,'blocks_removed':removed,'blocks_updated':updated}


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r=Path(td);(r/'thong-ke-xsmb').mkdir();(r/'cho-so-mien-bac-hom-nay').mkdir()
        old={'@context':'https://schema.org','@graph':[{'@type':'WebPage','name':'Old page'},{'@type':'Dataset'}]}
        new={'@context':'https://schema.org','@id':V3_ID,'@graph':[{'@type':'WebPage','name':'Old V3'},{'@type':'BreadcrumbList'},{'@type':'Dataset'}]}
        p=r/'thong-ke-xsmb/index.html';p.write_text('<html><head><title>Thống kê XSMB</title><meta name="description" content="Mô tả thống kê">'+render(old)+render(new)+'</head></html>',encoding='utf-8')
        rich={'@context':'https://schema.org','@graph':[{'@type':'Organization','name':'4SO AI'},{'@type':'WebSite','name':'4SO AI'},{'@type':'WebPage','name':'4SO AI cũ'}]}
        q=r/'cho-so-mien-bac-hom-nay/index.html';q.write_text('<html><head><title>Phương pháp hôm nay</title><meta name="description" content="Mô tả hôm nay">'+render(rich)+render(new)+'</head></html>',encoding='utf-8')
        result=apply(r);text=p.read_text(encoding='utf-8');rich_text=q.read_text(encoding='utf-8')
        assert result['blocks_removed']==2 and text.count('application/ld+json')==1 and 'BreadcrumbList' in text
        assert '"name":"Lê Miền Bắc"' in rich_text and '"name":"Phương pháp hôm nay"' in rich_text and '4SO AI cũ' not in rich_text
    print('PORTAL_SCHEMA_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
