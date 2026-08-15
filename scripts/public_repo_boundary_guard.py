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
    for rel in sorted(SENSITIVE_LEGACY & changed):
        raw=(ROOT/rel).read_text(encoding='utf-8').lower(); inspected.append(rel)
        if 'aggregate' not in raw:
            raise ValueError(f'{rel} changed but is not aggregate-only')
        for token in FORBIDDEN_DETAIL:
            if token.lower() in raw:
                raise ValueError(f'{rel} changed with detailed 4SO token: {token}')
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
