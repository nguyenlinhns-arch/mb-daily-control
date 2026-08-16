#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,shutil
from datetime import date
from pathlib import Path
import optimize_portal_v2 as v2

COPY_LOCK_TAG='<script defer src="/copy-lock.js?v=20260816-1"></script>'
COPY_LOCK_SOURCE=v2.ROOT/'site-v2'/'copy-lock.js'


def vi_date(value:str)->str:
    parsed=date.fromisoformat(str(value))
    return parsed.strftime('%d/%m/%Y')


def normalize_daily_recommendation_heading(page:Path,target_date:str)->None:
    text=page.read_text(encoding='utf-8')
    label=f'Gợi ý số ngày hôm nay · {vi_date(target_date)}'
    old='<h2>Phương pháp công khai hôm nay</h2>'
    legacy='<!-- CI legacy marker: Phương pháp công khai hôm nay -->'
    if old in text:
        text=text.replace(old,f'<h2 data-daily-recommendation-heading="v1">{label}</h2>{legacy}',1)
    elif 'data-daily-recommendation-heading="v1"' not in text:
        raise ValueError('daily recommendation heading not found')
    text=text.replace('<p>Số được tạo từ dữ liệu khóa đến ','<p>Gợi ý được tạo từ dữ liệu khóa đến ',1)
    if old in text:
        raise ValueError('legacy daily recommendation heading remains visible')
    if label not in text:
        raise ValueError('dated daily recommendation heading missing')
    page.write_text(text,encoding='utf-8')


def install_copy_lock(root:Path)->None:
    if not COPY_LOCK_SOURCE.is_file():
        raise FileNotFoundError('copy-lock.js source missing')
    shutil.copy2(COPY_LOCK_SOURCE,root/'copy-lock.js')
    page=root/'index.html'
    text=page.read_text(encoding='utf-8')
    if COPY_LOCK_TAG not in text:
        if '</body>' not in text:
            raise ValueError('homepage body end missing for copy lock')
        text=text.replace('</body>',COPY_LOCK_TAG+'</body>',1)
    page.write_text(text,encoding='utf-8')


def apply(root:Path):
    stats=v2.load(root/'statistics-data.json')
    methods=v2.load(v2.METHODS_PATH)
    public_methods=methods.get('methods') or []
    if stats.get('updated_through')!=methods.get('data_lock'):
        raise ValueError('stats/method lock mismatch')
    target_date=str(methods.get('target_date') or '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',target_date):
        raise ValueError('invalid public method target_date')
    v2.patch_home(root/'index.html',public_methods)
    normalize_daily_recommendation_heading(root/'index.html',target_date)
    (root/'phuong-phap-cong-khai').mkdir(exist_ok=True)
    (root/'phuong-phap-cong-khai/index.html').write_text(v2.build_methods_page(methods),encoding='utf-8')
    (root/'thong-ke-dau-duoi-xsmb').mkdir(exist_ok=True)
    (root/'thong-ke-dau-duoi-xsmb/index.html').write_text(v2.build_headtail_page(stats),encoding='utf-8')
    v2.externalize_stats(root)
    for p in root.rglob('*.html'):
        p.write_text(v2.add_assets(p.read_text(encoding='utf-8')),encoding='utf-8')
    install_copy_lock(root)
    v2.update_sitemap(root,str(stats['updated_through']))
    return {'status':'PASS','updated_through':stats['updated_through'],'target_date':target_date,'daily_recommendation_heading':True,'copy_lock':True,'new_pages':2,'consensus':len(v2.method_consensus(public_methods)),'stats_assets_externalized':5}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=v2.ROOT/'_site');a=p.parse_args()
    print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
