#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import optimize_portal_v2 as v2


def apply(root:Path):
    stats=v2.load(root/'statistics-data.json')
    methods=v2.load(v2.METHODS_PATH)
    public_methods=methods.get('methods') or []
    if stats.get('updated_through')!=methods.get('data_lock'):
        raise ValueError('stats/method lock mismatch')
    v2.patch_home(root/'index.html',public_methods)
    (root/'phuong-phap-cong-khai').mkdir(exist_ok=True)
    (root/'phuong-phap-cong-khai/index.html').write_text(v2.build_methods_page(methods),encoding='utf-8')
    (root/'thong-ke-dau-duoi-xsmb').mkdir(exist_ok=True)
    (root/'thong-ke-dau-duoi-xsmb/index.html').write_text(v2.build_headtail_page(stats),encoding='utf-8')
    v2.externalize_stats(root)
    for p in root.rglob('*.html'):
        p.write_text(v2.add_assets(p.read_text(encoding='utf-8')),encoding='utf-8')
    v2.update_sitemap(root,str(stats['updated_through']))
    return {'status':'PASS','updated_through':stats['updated_through'],'new_pages':2,'consensus':len(v2.method_consensus(public_methods)),'stats_assets_externalized':5}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=v2.ROOT/'_site');a=p.parse_args()
    print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
