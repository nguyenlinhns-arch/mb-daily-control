#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
METHODS_PATH=ROOT/'ai-methods'/'public-methods.json'
STATS_PAGES=('thong-ke-xsmb/index.html','tan-suat-xsmb/index.html','lo-gan-xsmb/index.html','cap-dao-xsmb/index.html','tra-cuu-xsmb/index.html')
NEW_PATHS=('/thong-ke-dau-duoi-xsmb/','/phuong-phap-cong-khai/')
VERSION='20260815-2'


def esc(x:Any)->str:return html.escape(str(x),quote=True)
def dmy(s:str)->str:return date.fromisoformat(s).strftime('%d/%m/%Y')

def load(path:Path)->dict[str,Any]:
    x=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(x,dict):raise ValueError(path)
    return x


def method_consensus(methods:list[dict[str,Any]])->list[dict[str,Any]]:
    seen:dict[str,list[str]]=defaultdict(list)
    for m in methods:
        mid=str(m.get('id') or '').upper(); name=str(m.get('name') or mid)
        if '4SO' in mid or '4SO' in name.upper():raise ValueError('4SO in public methods')
        for n in dict.fromkeys(str(v).zfill(2)[-2:] for v in (m.get('numbers') or [])):
            if not re.fullmatch(r'\d{2}',n):raise ValueError('invalid method number')
            seen[n].append(name)
    rows=[{'code':n,'count':len(names),'methods':names} for n,names in seen.items() if len(names)>=2]
    return sorted(rows,key=lambda r:(-r['count'],r['code']))


def consensus_html(methods:list[dict[str,Any]])->str:
    rows=method_consensus(methods)
    if not rows:return '<div class="portal-consensus"><div class="portal-consensus-head"><b>Đồng thuận giữa phương pháp</b><a href="/phuong-phap-cong-khai/">Xem chi tiết →</a></div><p class="portal-consensus-note">Hôm nay chưa có số nào được từ hai phương pháp công khai trở lên cùng nhắc.</p></div>'
    chips=''.join(f'<div class="portal-consensus-item" title="{esc(", ".join(r["methods"]))}"><strong>{r["code"]}</strong><span>{r["count"]} phương pháp</span></div>' for r in rows[:12])
    return f'<div class="portal-consensus"><div class="portal-consensus-head"><b>Số được nhiều phương pháp công khai cùng nhắc</b><a href="/phuong-phap-cong-khai/">Xem tổng hợp →</a></div><div class="portal-consensus-list">{chips}</div><p class="portal-consensus-note">Chỉ tính 6 phương pháp công khai; không dùng hoặc suy ngược đầu ra 4SO.</p></div>'


def shell(title:str,desc:str,route:str,body:str)->str:
    nav=[('/','Trang chủ'),('/thong-ke-xsmb/','Thống kê'),('/tan-suat-xsmb/','Tần suất'),('/lo-gan-xsmb/','Lô gan'),('/cap-dao-xsmb/','Cặp đảo'),('/thong-ke-dau-duoi-xsmb/','Đầu/đuôi'),('/tra-cuu-xsmb/','Tra cứu'),('/phuong-phap-cong-khai/','Phương pháp')]
    links=''.join(f'<a class="{"is-active" if href==route else ""}" href="{href}">{label}</a>' for href,label in nav)
    foot=''.join(f'<a href="{href}">{label}</a>' for href,label in nav[1:])
    canonical='https://lemienbac.com'+route
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="theme-color" content="#b3161b"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{canonical}"><link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/portal-subpages.css?v=20260815-1"><link rel="stylesheet" href="/portal-v2.css?v={VERSION}"></head><body class="portal-subpage"><header class="portal-site-header" data-portal-shell="v1"><div class="portal-site-head"><a class="portal-site-brand" href="/"><span class="portal-site-brand-mark">LM</span><span><strong>LÊ MIỀN BẮC</strong><small>DỮ LIỆU · THỐNG KÊ XSMB</small></span></a><nav class="portal-site-nav" aria-label="Điều hướng chính">{links}</nav><a class="portal-site-cta" href="/?checkout=1">Báo cáo 4SO</a></div></header><div class="portal-contextbar"><div class="portal-contextbar-inner"><span>Công cụ thống kê miễn phí · dữ liệu khóa T−1</span><a href="/thong-ke-xsmb/">Mở trung tâm thống kê →</a></div></div>{body}<footer class="portal-site-footer"><div class="portal-site-footer-inner"><div><strong>LÊ MIỀN BẮC</strong><p>Cổng dữ liệu và thống kê XSMB. Thống kê mô tả dữ liệu đã công bố, không phải cam kết kết quả.</p></div><nav class="portal-site-footer-nav">{foot}<a href="/legal.html">Điều khoản & bảo mật</a></nav></div><div class="portal-site-footer-bottom">© 2026 Lê Miền Bắc · Dữ liệu công khai và thống kê mô tả.</div></footer><script defer src="/portal-v2.js?v={VERSION}"></script></body></html>'''


def build_methods_page(method_doc:dict[str,Any])->str:
    methods=method_doc.get('methods') or []
    cards=[]
    for m in methods:
        name=str(m.get('name') or m.get('id') or '')
        nums=[str(v).zfill(2)[-2:] for v in (m.get('numbers') or [])]
        cards.append(f'<article class="portal-method-card-v2"><header><b>{esc(name)}</b><span>{len(nums)} số</span></header><div class="portal-method-balls-v2">'+''.join(f'<span class="portal-method-ball-v2">{esc(n)}</span>' for n in nums)+'</div></article>')
    con=consensus_html(methods)
    target=dmy(str(method_doc['target_date'])); lock=dmy(str(method_doc['data_lock']))
    body=f'''<main><section class="portal-page-intro"><p class="eyebrow">PHƯƠNG PHÁP CÔNG KHAI</p><h1>6 phương pháp XSMB công khai ngày {target}</h1><p>Đầu ra dưới đây chỉ dùng dữ liệu khóa đến {lock}. 4SO không nằm trong danh sách công khai và không thể suy ra từ trang này.</p></section><div class="portal-v2-wrap"><section class="portal-v2-card"><h2>Đầu ra theo từng phương pháp</h2><div class="portal-method-grid-v2">{"".join(cards)}</div>{con}</section><section class="portal-v2-card"><h2>Cách sử dụng bảng này</h2><p>Mỗi phương pháp là một góc nhìn thống kê riêng. Việc nhiều phương pháp cùng nhắc một số chỉ là dữ liệu đồng thuận giữa các mô hình công khai, không phải xác suất đảm bảo.</p><div class="portal-related"><a href="/tan-suat-xsmb/">Tần suất 00–99</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/thong-ke-dau-duoi-xsmb/">Đầu/đuôi</a><a href="/tra-cuu-xsmb/">Dò bộ số</a></div></section></div></main>'''
    return shell('Phương pháp XSMB công khai hôm nay: A1, 2SO, X3, F01, F06, Kép | Lê Miền Bắc','Tổng hợp 6 phương pháp XSMB công khai, số đồng thuận giữa phương pháp và liên kết sang tần suất, lô gan, đầu đuôi. Không công khai 4SO.','/phuong-phap-cong-khai/',body)


def digit_stats(stats:dict[str,Any],window:int)->tuple[list[int],list[int]]:
    rows=(stats.get('recent_history') or [])[-window:]
    heads=[0]*10; tails=[0]*10
    for row in rows:
        for code in row[1:28]:
            s=str(code).zfill(2)[-2:]; heads[int(s[0])]+=1; tails[int(s[1])]+=1
    return heads,tails


def build_headtail_page(stats:dict[str,Any])->str:
    values={w:digit_stats(stats,w) for w in (30,60,100)}
    def table(kind:int)->str:
        name='Đầu' if kind==0 else 'Đuôi'
        rows=[]
        for d in range(10):
            v30=values[30][kind][d];v60=values[60][kind][d];v100=values[100][kind][d]
            rows.append(f'<tr><td><b>{name} {d}</b></td><td>{v30}</td><td>{v60}</td><td>{v100}</td><td>{v60/60:.2f}</td></tr>')
        return '<div class="portal-v2-scroll"><table class="portal-v2-table"><thead><tr><th>'+name+'</th><th>Nháy/30</th><th>Nháy/60</th><th>Nháy/100</th><th>TB/ngày 60</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    updated=dmy(str(stats['updated_through']))
    body=f'''<main><section class="portal-page-intro"><p class="eyebrow">THỐNG KÊ ĐẦU · ĐUÔI 0–9</p><h1>Tần suất đầu và đuôi XSMB</h1><p>Đếm chữ số hàng chục (đầu) và hàng đơn vị (đuôi) của toàn bộ 27 mã mỗi ngày. Dữ liệu cập nhật đến {updated}.</p></section><div class="portal-v2-wrap"><div class="portal-v2-grid"><section class="portal-v2-card"><h2>Thống kê đầu 0–9</h2>{table(0)}</section><section class="portal-v2-card"><h2>Thống kê đuôi 0–9</h2>{table(1)}</section></div><section class="portal-v2-card"><h2>Đọc cùng các công cụ khác</h2><p>Đầu/đuôi cho góc nhìn phân bố chữ số; tần suất 00–99 và lô gan cho góc nhìn từng mã cụ thể.</p><div class="portal-related"><a href="/tan-suat-xsmb/">Tần suất 00–99</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/cap-dao-xsmb/">45 cặp đảo</a><a href="/tra-cuu-xsmb/">Tra cứu bộ số</a></div></section></div></main>'''
    return shell('Thống kê đầu đuôi XSMB 0–9 theo 30–100 kỳ | Lê Miền Bắc','Thống kê tần suất đầu và đuôi XSMB 0–9 theo 30, 60 và 100 kỳ từ đủ 27 mã kết quả mỗi ngày.','/thong-ke-dau-duoi-xsmb/',body)


def add_assets(text:str)->str:
    if 'portal-v2.css' not in text:text=text.replace('</head>',f'<link rel="stylesheet" href="/portal-v2.css?v={VERSION}"></head>',1)
    if 'portal-v2.js' not in text:text=text.replace('</body>',f'<script defer src="/portal-v2.js?v={VERSION}"></script></body>',1)
    return text


def patch_home(path:Path,methods:dict[str,Any])->None:
    t=path.read_text(encoding='utf-8')
    title='Xổ số Miền Bắc (XSMB): thống kê 00–99, lô gan, tần suất | Lê Miền Bắc'
    desc='Cổng dữ liệu XSMB: 27 mã kỳ gần nhất, tần suất 00–99, lô gan, 45 cặp đảo, đầu đuôi, tra cứu lịch sử và các phương pháp AI công khai.'
    t=re.sub(r'<title>.*?</title>',f'<title>{title}</title>',t,count=1,flags=re.I|re.S)
    t=re.sub(r'<meta name="description" content="[^"]*">',f'<meta name="description" content="{desc}">',t,count=1,flags=re.I)
    for prop,val in [('og:title',title),('og:description',desc),('twitter:title',title),('twitter:description',desc)]:
        t=re.sub(rf'(<meta (?:property|name)="{re.escape(prop)}" content=")[^"]*(">)',rf'\1{val}\2',t,count=1,flags=re.I)
    if 'portal-quick-search' not in t:
        form='<form class="portal-quick-search" action="/tra-cuu-xsmb/" method="get"><input name="numbers" inputmode="numeric" placeholder="Tra cứu nhanh: 05, 50, 83…" aria-label="Nhập bộ số cần tra cứu"><select name="days" aria-label="Số kỳ cần dò"><option value="30">30 kỳ</option><option value="60" selected>60 kỳ</option><option value="100">100 kỳ</option><option value="365">365 kỳ</option></select><button type="submit">Tra cứu</button></form>'
        t=re.sub(r'(<div class="portal-status">.*?</div>)',r'\1'+form,t,count=1,flags=re.I|re.S)
    if 'portal-consensus' not in t:
        t=t.replace('<p class="portal-disclaimer">Các phương pháp',consensus_html(methods)+'<p class="portal-disclaimer">Các phương pháp',1)
    if '/thong-ke-dau-duoi-xsmb/' not in t:
        marker='<a class="portal-card portal-tool" href="/tra-cuu-xsmb/">'
        tool='<a class="portal-card portal-tool" href="/thong-ke-dau-duoi-xsmb/"><b>Đầu / đuôi 0–9</b><span>Phân bố chữ số theo 30–100 kỳ</span><em>Xem thống kê →</em></a>'
        t=t.replace(marker,tool+marker,1)
    if '/phuong-phap-cong-khai/' not in t:
        t=t.replace('<a href="/lich-su-doi-chieu/">Lịch sử</a>','<a href="/phuong-phap-cong-khai/">Phương pháp</a><a href="/lich-su-doi-chieu/">Lịch sử</a>',1)
    path.write_text(add_assets(t),encoding='utf-8')


def externalize_stats(root:Path)->None:
    sample=(root/STATS_PAGES[0]).read_text(encoding='utf-8')
    styles=re.findall(r'<style>(.*?)</style>',sample,flags=re.S)
    css=next((s for s in styles if '.top{' in s and '.grid{' in s),None)
    scripts=re.findall(r'<script>(.*?)</script>',sample,flags=re.S)
    js=next((s for s in scripts if 'xsmb_number_open' in s and 'xsmb_lookup' in s),None)
    if not css or not js:raise ValueError('stats inline assets not found')
    (root/'xsmb-stats.css').write_text(css.strip()+'\n',encoding='utf-8')
    (root/'xsmb-stats.js').write_text(js.strip()+'\n',encoding='utf-8')
    for rel in STATS_PAGES:
        p=root/rel;t=p.read_text(encoding='utf-8')
        t=t.replace(f'<style>{css}</style>',f'<link rel="stylesheet" href="/xsmb-stats.css?v={VERSION}">',1)
        t=t.replace(f'<script>{js}</script>',f'<script defer src="/xsmb-stats.js?v={VERSION}"></script>',1)
        p.write_text(t,encoding='utf-8')


def update_sitemap(root:Path,updated:str)->None:
    p=root/'sitemap.xml';t=p.read_text(encoding='utf-8')
    add=''.join(f'  <url><loc>https://lemienbac.com{x}</loc><lastmod>{updated}</lastmod></url>\n' for x in NEW_PATHS if 'https://lemienbac.com'+x not in t)
    if add:t=t.replace('</urlset>',add+'</urlset>')
    p.write_text(t,encoding='utf-8')


def apply(root:Path)->dict[str,Any]:
    stats=load(root/'statistics-data.json');methods=load(METHODS_PATH)
    if stats.get('updated_through')!=methods.get('data_lock'):raise ValueError('stats/method lock mismatch')
    patch_home(root/'index.html',methods)
    (root/'phuong-phap-cong-khai').mkdir(exist_ok=True);(root/'phuong-phap-cong-khai/index.html').write_text(build_methods_page(methods),encoding='utf-8')
    (root/'thong-ke-dau-duoi-xsmb').mkdir(exist_ok=True);(root/'thong-ke-dau-duoi-xsmb/index.html').write_text(build_headtail_page(stats),encoding='utf-8')
    externalize_stats(root)
    for p in root.rglob('*.html'):
        p.write_text(add_assets(p.read_text(encoding='utf-8')),encoding='utf-8')
    update_sitemap(root,str(stats['updated_through']))
    return {'status':'PASS','updated_through':stats['updated_through'],'new_pages':2,'consensus':len(method_consensus(methods.get('methods') or [])),'stats_assets_externalized':5}


def self_test()->None:
    methods=[{'id':'A1','name':'A1','numbers':['05','60']},{'id':'X2','name':'2SO','numbers':['60','06']},{'id':'F01','name':'F01','numbers':['05','83']}]
    rows=method_consensus(methods);assert [r['code'] for r in rows]==['05','60']
    stats={'recent_history':[['2026-01-01',*['05']*27]],'updated_through':'2026-01-01'}
    h,t=digit_stats(stats,30);assert h[0]==27 and t[5]==27
    assert 'Không công khai 4SO' in build_methods_page({'target_date':'2026-01-02','data_lock':'2026-01-01','methods':methods})
    print('PORTAL_V2_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
