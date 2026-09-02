#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_LEGACY = {
    "ai-methods/yesterday-proof.json",
    "data/public-historical-proof.json",
}
FORBIDDEN_DETAIL = (
    "recommended_numbers", '"outputs"', '"observed"',
    "canonical_codes", "canonical_pairs", "final_codes", "final_pairs",
)


def load(path: Path) -> dict[str, Any]:
    doc=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(doc,dict): raise ValueError(path)
    return doc


def validate_public_methods() -> None:
    doc=load(ROOT/'ai-methods/public-methods.json')
    methods=doc.get('methods') or []
    if len(methods)!=6: raise ValueError('public methods must contain exactly 6 methods')
    target=date.fromisoformat(str(doc['target_date'])); lock=date.fromisoformat(str(doc['data_lock']))
    if lock!=target-timedelta(days=1): raise ValueError('public methods lock must be T-1')
    for method in methods:
        mid=str(method.get('id') or '').upper(); name=str(method.get('name') or '').upper()
        if '4SO' in mid or '4SO' in name: raise ValueError('4SO found in public methods')
        nums=method.get('numbers') or []
        if not nums or any(not re.fullmatch(r'\d{2}',str(n)) for n in nums):
            raise ValueError(f'invalid public method numbers: {method.get("name")}')

    mb_all=doc.get('mb_all') or {}
    if mb_all.get('public_method_outputs_hidden') is not True:
        raise ValueError('MB_ALL public method outputs must be marked hidden')
    nested=mb_all.get('methods') or []
    if int(mb_all.get('method_count_run') or 0)!=31 or len(nested)!=31:
        raise ValueError('MB_ALL public method metadata must contain exactly 31 methods')
    for method in nested:
        name=str(method.get('name') or '').upper()
        mid=str(method.get('id') or '').upper()
        nums=method.get('numbers') or []
        if ('4SO' in name or '4SO' in mid) and nums:
            raise ValueError(f'4SO paid method output leaked into public repo: {method.get("name")}')


def validate_report_templates() -> None:
    for rel in ('ai-methods/report-data.json','ai-methods/report-share-data.json'):
        doc=load(ROOT/rel)
        if doc.get('report_stage')!='TEMPLATE': raise ValueError(f'{rel} must remain TEMPLATE in public repo')
        if doc.get('final_codes') not in ([],None) or doc.get('final_pairs') not in ([],None):
            raise ValueError(f'{rel} contains final 4SO output')
        for row in doc.get('top3') or []:
            pair=str(row.get('pair') or '--')
            if pair not in ('--',''): raise ValueError(f'{rel} contains a real top3 pair')
            if row.get('score') not in (None,''): raise ValueError(f'{rel} contains a real score')


def validate_safe_public_json() -> None:
    for rel in ('data/paid-report-ready.json','data/source-access.json','data/affiliate-offers.json'):
        raw=(ROOT/rel).read_text(encoding='utf-8').lower()
        for key in ('canonical_codes','canonical_pairs','final_codes','final_pairs'):
            if key in raw: raise ValueError(f'{rel} contains {key}')


def changed_files() -> set[str]:
    try:
        out=subprocess.check_output(['git','diff','--name-only','HEAD^','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL)
        return {x.strip().replace('\\','/') for x in out.splitlines() if x.strip()}
    except Exception:
        return set()


def validate_changed_sensitive() -> dict[str,Any]:
    changed=changed_files(); inspected=[]
    ready=load(ROOT/'data/paid-report-ready.json')
    report_day=date.fromisoformat(str(ready['report_date']))
    for rel in sorted(SENSITIVE_LEGACY & changed):
        doc=load(ROOT/rel); inspected.append(rel)
        raw=(ROOT/rel).read_text(encoding='utf-8').lower()
        for key in ('canonical_codes','canonical_pairs','final_codes','final_pairs','top1','top2','slot1_r4268','slot2_selected'):
            if key in raw: raise ValueError(f'{rel} contains current paid-output field: {key}')
        if rel=='ai-methods/yesterday-proof.json':
            if doc.get('schema_version')!='MB_PUBLIC_YESTERDAY_PROOF_V3_PRODUCTION_AWARE':
                raise ValueError('yesterday proof must use Production-aware completed schema')
            proof_day=date.fromisoformat(str(doc['date']))
            if proof_day>=report_day: raise ValueError('yesterday proof must be completed before current paid report')
            picks=doc.get('recommended_numbers') or []
            if len(picks) not in (2,4) or any(not re.fullmatch(r'\d{2}',str(x)) for x in picks):
                raise ValueError('invalid completed Production output')
        elif rel=='data/public-historical-proof.json':
            if doc.get('schema_version')!='MB_PUBLIC_HISTORICAL_PROOF_V2_PRODUCTION_AWARE':
                raise ValueError('historical proof must use Production-aware schema')
            recent=doc.get('recent_period') or {}
            recent_end=date.fromisoformat(str(recent['period_end']))
            if recent_end>=report_day: raise ValueError('historical proof may contain completed days only')
            snap=doc.get('method_snapshot') or {}
            if snap.get('paid_output_hidden') is not True: raise ValueError('paid output must stay hidden')
            if str(snap.get('target_date'))!=str(ready.get('report_date')) or str(snap.get('data_lock'))!=str(ready.get('data_lock')):
                raise ValueError('method snapshot must match public readiness dates')
    return {'changed_files':len(changed),'sensitive_inspected':inspected}

def run() -> dict[str,Any]:
    validate_public_methods(); validate_report_templates(); validate_safe_public_json()
    sensitive=validate_changed_sensitive()
    return {'status':'PASS','public_methods':6,'templates_locked':2,**sensitive}


def self_test() -> None:
    assert re.fullmatch(r'\d{2}','05') and not re.fullmatch(r'\d{2}','5')
    print('PUBLIC_REPO_BOUNDARY_GUARD_SELF_TEST_OK')


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    if a.self_test:self_test()
    else: print(json.dumps(run(),ensure_ascii=False))

if __name__=='__main__':main()
