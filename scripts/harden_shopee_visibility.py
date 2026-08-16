#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"404.html"}
PRODUCTS = [
    {
        "slug": "1",
        "name": "Tông đơ Philips MG3911/15 7in1",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mp1ohea3di4g9e",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773390&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vVCVDMyVCNG5nLSVDNCU5MSVDNiVBMS1QaGlsaXBzLU1HMzkxMS0xNS1NdWx0aWdyb29tLTMwMDAtN2luMS1jJUUxJUJBJUFGdC10JUUxJUJCJTg5YS1yJUMzJUIzYy0lQzQlOTFhLW4lQzQlODNuZy1zJUUxJUJCJUFELWQlRTElQkIlQTVuZy10JUUxJUJBJUExaS1uaCVDMyVBMC1pLjQ2MzYwMDA2MS40OTUxMTM1NzAxNw==&redirect_302=1",
    },
    {
        "slug": "2",
        "name": "Sạc dự phòng Anker Zolo 20.000mAh 22.5W",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mlnj4c7kwkjp03",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773391&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vUyVFMSVCQSVBMWMtZCVFMSVCQiVCMS1waCVDMyVCMm5nLUFua2VyLVpvbG8tQTExMEQtMjAwMDBtQWgtY2h1JUUxJUJBJUE5bi0zQy1UcnVuZy1RdSVFMSVCQiU5MWMtYyVDMyVBMXAtVVNCLUMtdCVDMyVBRGNoLWglRTElQkIlQTNwLXMlRTElQkElQTFjLW5oYW5oLTIyLjVXLWkuMTIwMjg4OTY3OC40NTU1NDAxNDY3NQ==&redirect_302=1",
    },
    {
        "slug": "3",
        "name": "Máy vặn vít pin Bosch GO 3",
        "image": "https://down-vn.img.susercontent.com/file/sg-11134201-8259d-mrbyk5d9m3gs2c",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773392&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktdiVFMSVCQSVCN24tdiVDMyVBRHQtcGluLUJvc2NoLUdvLTMtaS43NTgxMDI0OS4yNTUxNDU2ODgyOQ==&redirect_302=1",
    },
    {
        "slug": "4",
        "name": "Máy hút bụi cầm tay Deerma DX118C 600W",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m83aax7f0sasfe",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773393&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktSCVDMyVCQXQtQiVFMSVCQiVBNWktQyVFMSVCQSVBN20tVGF5LURlZXJtYS1EWDExOEMtJTI4QiVFMSVCQSVBMk4tTSVFMSVCQiU5QUktNjAwVyUyOS1DaCVDMyVBRG5oLWglQzMlQTNuZy1EZWVybWEtaS4yODE0MzI4NC4yNzQ1Nzg2MDQwNA==&redirect_302=1",
    },
]

STYLE = '''<style id="lm-shop-cards-v2-style">
.lm-shop-cards-v2{display:block!important;visibility:visible!important;opacity:1!important;width:100%;padding:18px 0 10px}.lm-shop-cards-v2-inner{max-width:1180px;margin:auto;padding:0 16px}.lm-shop-cards-v2-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:10px}.lm-shop-cards-v2-head span{display:block;color:#ee4d2d;font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.lm-shop-cards-v2-head h2{margin:2px 0 0;color:#203542;font-size:19px;line-height:1.2}.lm-shop-cards-v2-head small{color:#84919a;font-size:10px}.lm-shop-cards-v2-grid{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.lm-shop-card-v2{display:block!important;min-width:0;overflow:hidden;border:1px solid #e7ebee;border-radius:14px;background:#fff;color:#243542!important;text-decoration:none!important;box-shadow:0 2px 9px rgba(24,42,54,.04)}.lm-shop-card-v2-media{aspect-ratio:1/1;background:linear-gradient(135deg,#f8fafc,#eef2f5);overflow:hidden}.lm-shop-card-v2-media img{display:block;width:100%;height:100%;object-fit:cover}.lm-shop-card-v2-copy{padding:9px}.lm-shop-card-v2-copy strong{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2;min-height:36px;font-size:12px;line-height:1.45;color:#263946}.lm-shop-card-v2-copy b{display:flex;align-items:center;justify-content:center;min-height:38px;margin-top:8px;border-radius:9px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:900}.lm-shop-cards-v2-note{margin:6px 1px 0;color:#929ca3;font-size:8.5px;line-height:1.35}
@media(max-width:700px){.lm-shop-cards-v2{padding:14px 0 8px}.lm-shop-cards-v2-inner{padding:0 10px}.lm-shop-cards-v2-head h2{font-size:17px}.lm-shop-cards-v2-head small{display:none}.lm-shop-cards-v2-grid{display:flex!important;gap:8px;overflow-x:auto;scroll-snap-type:x mandatory;padding:0 1px 4px;scrollbar-width:none}.lm-shop-cards-v2-grid::-webkit-scrollbar{display:none}.lm-shop-card-v2{flex:0 0 min(42vw,170px);scroll-snap-align:start}.lm-shop-card-v2-copy strong{font-size:11.5px;min-height:34px}.lm-shop-card-v2-copy b{min-height:40px;font-size:10.5px}}
</style>'''

TRACK = '''<script id="lm-shop-cards-v2-track">(()=>{const root=document.querySelector('[data-shop-cards-v2="1"]');if(!root)return;const push=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,merchant:'Shopee',network:'ACCESSTRADE',placement:'lower_4_cards_v2',...extra})};let seen=false;const view=()=>{if(seen)return;seen=true;push('affiliate_product_grid_view')};if('IntersectionObserver'in window){const o=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){view();o.disconnect()}},{threshold:[.2]});o.observe(root)}else view();root.addEventListener('click',e=>{const a=e.target.closest('[data-shop-card-v2]');if(a)push('affiliate_product_click',{product_index:Number(a.dataset.shopCardV2||0),product_name:a.dataset.productName||''})})})();</script>'''


def remove_section(text: str, marker: str) -> str:
    while marker in text:
        pos = text.find(marker)
        start = text.rfind('<section', 0, pos)
        end = text.find('</section>', pos)
        if start < 0 or end < 0:
            break
        text = text[:start] + text[end + len('</section>'):]
    return text


def build_cards() -> str:
    cards=[]
    for idx,p in enumerate(PRODUCTS,1):
        cards.append(
            f'<a class="lm-shop-card-v2" href="/go/sp/{p["slug"]}/" target="_blank" rel="nofollow noopener" data-shop-card-v2="{idx}" data-product-name="{html.escape(p["name"])}">'
            f'<div class="lm-shop-card-v2-media"><img src="{html.escape(p["image"])}" loading="lazy" decoding="async" alt="{html.escape(p["name"])}"></div>'
            f'<div class="lm-shop-card-v2-copy"><strong>{html.escape(p["name"])}</strong><b>Xem trên Shopee →</b></div></a>'
        )
    return '<section class="lm-shop-cards-v2" data-shop-cards-v2="1"><div class="lm-shop-cards-v2-inner"><div class="lm-shop-cards-v2-head"><div><span>Liên kết đối tác</span><h2>Sản phẩm Shopee đang giới thiệu</h2></div><small>4 sản phẩm</small></div><div class="lm-shop-cards-v2-grid">'+''.join(cards)+'</div><p class="lm-shop-cards-v2-note">Website có thể nhận hoa hồng khi phát sinh giao dịch đủ điều kiện.</p></div></section>'


def write_redirects(root: Path) -> None:
    for p in PRODUCTS:
        target=root/'go'/'sp'/p['slug']/'index.html'
        target.parent.mkdir(parents=True,exist_ok=True)
        url=html.escape(p['url'],quote=True)
        target.write_text(
            '<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Đang mở Shopee</title>'
            f'<meta http-equiv="refresh" content="0;url={url}"></head><body><p>Đang mở sản phẩm…</p>'
            f'<script>location.replace({p["url"]!r});</script></body></html>',encoding='utf-8')


def insert_after_tools_or_low(text: str, markup: str, home: bool) -> str:
    if home:
        for marker in ('Công cụ thống kê XSMB','portal-tools'):
            pos=text.find(marker)
            if pos>=0:
                start=text.rfind('<section',0,pos)
                end=text.find('</section>',pos)
                if start>=0 and end>=0:
                    return text[:end+10]+markup+text[end+10:]
    end=text.lower().rfind('</main>')
    if end<0:end=text.lower().rfind('</body>')
    if end<0:raise ValueError('missing main/body end')
    return text[:end]+markup+text[end:]


def apply(root: Path) -> dict[str,object]:
    write_redirects(root)
    pages=[]
    for page in root.rglob('*.html'):
        rel=page.relative_to(root).as_posix()
        if rel in EXCLUDED or rel.startswith('go/'):
            continue
        pages.append(page)
    for page in pages:
        rel=page.relative_to(root).as_posix()
        text=page.read_text(encoding='utf-8')
        for marker in ('data-shop-cards-v2="1"','data-sitewide-products="true"','data-affiliate-static-placement="after_tools"'):
            text=remove_section(text,marker)
        text=re.sub(r'<style\s+id="lm-shop-cards-v2-style">.*?</style>','',text,flags=re.I|re.S)
        text=re.sub(r'<script\s+id="lm-shop-cards-v2-track">.*?</script>','',text,flags=re.I|re.S)
        if '</head>' not in text or '</body>' not in text: raise ValueError(rel)
        text=text.replace('</head>',STYLE+'</head>',1)
        text=insert_after_tools_or_low(text,build_cards(),rel=='index.html')
        text=text.replace('</body>',TRACK+'</body>',1)
        page.write_text(text,encoding='utf-8')
    home=(root/'index.html').read_text(encoding='utf-8')
    if home.count('data-shop-cards-v2="1"') < 1: raise ValueError('home cards missing')
    if 'go.isclix.com' in re.search(r'<section class="lm-shop-cards-v2".*?</section>',home,re.S).group(0): raise ValueError('external affiliate URL leaked into visible cards')
    return {'status':'PASS','pages':len(pages),'home_cards':4,'internal_product_links':True}


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');a=p.parse_args();print(apply(a.output_root))

if __name__=='__main__':main()
