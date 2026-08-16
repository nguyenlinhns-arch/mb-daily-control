#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEGACY_OLD="(()=>{let D;const load=()=>D?Promise.resolve(D):fetch('/statistics-data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>D=x);"
LEGACY_NEW="(()=>{let D=window.LM_STATS_DATA||null;const load=()=>D?Promise.resolve(D):(window.LM_STATS_PROMISE||(window.LM_STATS_PROMISE=fetch('/statistics-data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>{D=x;window.LM_STATS_DATA=x;return x})));window.LM_LOAD_STATS=load;"
DYNAMIC_OLD="(()=>{let D,selectedNumber='';const version=document.documentElement.dataset.statsVersion||'';const statsUrl='/statistics-data.json'+(version?'?v='+encodeURIComponent(version):'');const load=()=>D?Promise.resolve(D):fetch(statsUrl,{cache:'default'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>D=x);"
DYNAMIC_NEW="(()=>{let D=window.LM_STATS_DATA||null,selectedNumber='';const version=document.documentElement.dataset.statsVersion||'';const statsUrl='/statistics-data.json'+(version?'?v='+encodeURIComponent(version):'');const load=()=>D?Promise.resolve(D):(window.LM_STATS_PROMISE||(window.LM_STATS_PROMISE=fetch(statsUrl,{cache:'default'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>{D=x;window.LM_STATS_DATA=x;return x})));window.LM_LOAD_STATS=load;"


def apply(root:Path)->dict[str,object]:
    path=root/'xsmb-stats.js'
    if not path.is_file():raise ValueError('Missing xsmb-stats.js')
    text=path.read_text(encoding='utf-8')
    if DYNAMIC_NEW in text or LEGACY_NEW in text:
        return {'status':'PASS','changed':False,'shared_loader':True,'mode':'dynamic' if DYNAMIC_NEW in text else 'legacy'}
    if DYNAMIC_OLD in text:
        text=text.replace(DYNAMIC_OLD,DYNAMIC_NEW,1);mode='dynamic'
    elif LEGACY_OLD in text:
        text=text.replace(LEGACY_OLD,LEGACY_NEW,1);mode='legacy'
    else:
        raise ValueError('Unexpected xsmb-stats.js loader; refusing blind patch')
    path.write_text(text,encoding='utf-8')
    if "window.LM_LOAD_STATS=load" not in text or text.count('fetch(')!=1:
        raise ValueError('Shared statistics loader validation failed')
    if mode=='dynamic' and ("dataStatsVersion" in text or "cache:'default'" not in text or "statsUrl" not in text):
        raise ValueError('Versioned statistics loader contract failed')
    return {'status':'PASS','changed':True,'shared_loader':True,'mode':mode}


def self_test()->None:
    import tempfile
    for mode,old,expected in [('legacy',LEGACY_OLD,LEGACY_NEW),('dynamic',DYNAMIC_OLD,DYNAMIC_NEW)]:
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'xsmb-stats.js';p.write_text(old+'console.log(1)})();',encoding='utf-8')
            result=apply(root);t=p.read_text(encoding='utf-8')
            assert result['changed'] and result['mode']==mode and expected in t
            assert 'window.LM_LOAD_STATS=load' in t and t.count('fetch(')==1
            assert apply(root)['changed'] is False
    print('SHARED_STATISTICS_LOADER_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
