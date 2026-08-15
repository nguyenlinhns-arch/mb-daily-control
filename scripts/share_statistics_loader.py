#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD="(()=>{let D;const load=()=>D?Promise.resolve(D):fetch('/statistics-data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>D=x);"
NEW="(()=>{let D=window.LM_STATS_DATA||null;const load=()=>D?Promise.resolve(D):(window.LM_STATS_PROMISE||(window.LM_STATS_PROMISE=fetch('/statistics-data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>{D=x;window.LM_STATS_DATA=x;return x})));window.LM_LOAD_STATS=load;"


def apply(root:Path)->dict[str,object]:
    path=root/'xsmb-stats.js'
    if not path.is_file():raise ValueError('Missing xsmb-stats.js')
    text=path.read_text(encoding='utf-8')
    if NEW in text:
        return {'status':'PASS','changed':False,'shared_loader':True}
    if OLD not in text:
        raise ValueError('Unexpected xsmb-stats.js loader; refusing blind patch')
    text=text.replace(OLD,NEW,1)
    path.write_text(text,encoding='utf-8')
    if "window.LM_LOAD_STATS=load" not in text or text.count("fetch('/statistics-data.json'")!=1:
        raise ValueError('Shared statistics loader validation failed')
    return {'status':'PASS','changed':True,'shared_loader':True}


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);p=root/'xsmb-stats.js';p.write_text(OLD+'console.log(1)})();',encoding='utf-8')
        result=apply(root);t=p.read_text(encoding='utf-8')
        assert result['changed'] and 'window.LM_LOAD_STATS=load' in t and t.count("fetch('/statistics-data.json'")==1
        assert apply(root)['changed'] is False
    print('SHARED_STATISTICS_LOADER_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
