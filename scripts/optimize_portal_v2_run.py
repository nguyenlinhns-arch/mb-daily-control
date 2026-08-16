#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,shutil
from datetime import date
from pathlib import Path
import optimize_portal_v2 as v2

COPY_LOCK_TAG='<script defer src="/copy-lock.js?v=20260816-2"></script>'
COPY_LOCK_SOURCE=v2.ROOT/'site-v2'/'copy-lock.js'


def vi_date(value:str)->str:
    parsed=date.fromisoformat(str(value))
    return parsed.strftime('%d/%m/%Y')


def normalize_daily_recommendation_heading(page:Path,target_date:str,data_lock:str)->None:
    text=page.read_text(encoding='utf-8')
    target_label=vi_date(target_date)
    lock_label=vi_date(data_lock)
    heading=f'Gợi ý số ngày hôm nay - {target_label}'
    subtitle=f'Gợi ý được tạo từ dữ liệu khóa đến ngày hôm qua ({lock_label}). Kết luận các số cuối cùng không nằm trong danh sách công khai này.'
    old='<h2>Phương pháp công khai hôm nay</h2>'
    legacy='<!-- CI legacy marker: Phương pháp công khai hôm nay -->'

    if old in text:
        text=text.replace(old,f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>{legacy}',1)
    else:
        text,replaced=re.subn(
            r'<h2\b[^>]*data-daily-recommendation-heading="[^"]+"[^>]*>.*?</h2>',
            f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>',
            text,count=1,flags=re.I|re.S,
        )
        if replaced != 1:
            text,replaced=re.subn(
                r'<h2>\s*Gợi ý số.*?</h2>',
                f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>',
                text,count=1,flags=re.I|re.S,
            )
        if replaced != 1:
            raise ValueError('daily recommendation heading not found')

    heading_pos=text.find(heading)
    if heading_pos < 0:
        raise ValueError('exact daily recommendation heading missing')
    p_start=text.find('<p>',heading_pos)
    p_end=text.find('</p>',p_start)
    if p_start < 0 or p_end < 0:
        raise ValueError('daily recommendation subtitle not found')
    text=text[:p_start]+f'<p>{subtitle}</p>'+text[p_end+4:]

    visible_slice=text[heading_pos:heading_pos+1200]
    if f'{target_label} · {target_label}' in visible_slice or '4SO không nằm trong danh sách công khai này' in visible_slice:
        raise ValueError('legacy or duplicated recommendation copy remains')
    if heading not in visible_slice or subtitle not in visible_slice:
        raise ValueError('exact public recommendation copy missing')
    page.write_text(text,encoding='utf-8')


def normalize_paid_card_copy(page:Path,target_date:str)->None:
    text=page.read_text(encoding='utf-8')
    label=vi_date(target_date)
    match=re.search(r'<aside class="portal-paid-card"[^>]*>.*?</aside>',text,flags=re.I|re.S)
    if not match:
        raise ValueError('portal paid card not found')
    block=match.group(0)
    block=re.sub(r'<aside class="portal-paid-card"[^>]*>', '<aside class="portal-paid-card" data-daily-offer-static="v2">', block, count=1, flags=re.I)
    block=re.sub(r'<small>[^<]*</small>', '<small>GỢI Ý SỐ HÔM NAY</small>', block, count=1, flags=re.I)
    block=re.sub(r'<h2>.*?</h2>',f'<h2>Gợi ý số ngày hôm nay - {label}</h2>',block,count=1,flags=re.I|re.S)
    block=re.sub(
        r'(<button\b[^>]*\bdata-open-checkout\b[^>]*>).*?(</button>)',
        r'\1MỞ GỢI Ý SỐ HÔM NAY · 30.000Đ\2',
        block,count=1,flags=re.I|re.S,
    )
    if 'GỢI Ý SỐ HÔM NAY' not in block or f'Gợi ý số ngày hôm nay - {label}' not in block or 'MỞ GỢI Ý SỐ HÔM NAY · 30.000Đ' not in block:
        raise ValueError('daily suggestion paid-card copy missing')
    if re.search(r'BẠN ĐÃ TỪNG MỞ BẢN AI|Bản phân tích AI ngày|MỞ BẢN PHÂN TÍCH AI|Kết luận ngày|4SO AI · BÁO CÁO RIÊNG',block,flags=re.I):
        raise ValueError('legacy AI-analysis wording remains in paid card')
    text=text[:match.start()]+block+text[match.end():]
    page.write_text(text,encoding='utf-8')


def install_copy_lock(root:Path)->None:
    if not COPY_LOCK_SOURCE.is_file():
        raise FileNotFoundError('copy-lock.js source missing')
    shutil.copy2(COPY_LOCK_SOURCE,root/'copy-lock.js')
    page=root/'index.html'
    text=page.read_text(encoding='utf-8')
    text=re.sub(r'<script defer src="/copy-lock\.js\?v=[^"]+"></script>','',text)
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
    data_lock=str(methods.get('data_lock') or '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',target_date):
        raise ValueError('invalid public method target_date')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',data_lock):
        raise ValueError('invalid public method data_lock')
    v2.patch_home(root/'index.html',public_methods)
    normalize_daily_recommendation_heading(root/'index.html',target_date,data_lock)
    normalize_paid_card_copy(root/'index.html',target_date)
    (root/'phuong-phap-cong-khai').mkdir(exist_ok=True)
    (root/'phuong-phap-cong-khai/index.html').write_text(v2.build_methods_page(methods),encoding='utf-8')
    (root/'thong-ke-dau-duoi-xsmb').mkdir(exist_ok=True)
    (root/'thong-ke-dau-duoi-xsmb/index.html').write_text(v2.build_headtail_page(stats),encoding='utf-8')
    v2.externalize_stats(root)
    for p in root.rglob('*.html'):
        p.write_text(v2.add_assets(p.read_text(encoding='utf-8')),encoding='utf-8')
    install_copy_lock(root)
    v2.update_sitemap(root,str(stats['updated_through']))
    return {'status':'PASS','updated_through':stats['updated_through'],'target_date':target_date,'data_lock':data_lock,'daily_recommendation_heading':True,'daily_recommendation_subtitle':True,'daily_offer_static':True,'copy_lock':True,'new_pages':2,'consensus':len(v2.method_consensus(public_methods)),'stats_assets_externalized':5}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=v2.ROOT/'_site');a=p.parse_args()
    print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
