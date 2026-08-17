#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINANCE_SOURCE = ROOT / "site-v2" / "finance-gate-sitewide.js"
FINANCE_TAG = '<script defer src="/finance-gate-sitewide.js?v=20260816-2"></script>'
EXCLUDED = {"404.html", "go/shopee/index.html"}

PRODUCTS = [
    {
        "id": "1",
        "name": "Tông đơ Philips MG3911/15 7in1",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mp1ohea3di4g9e",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773390&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vVCVDMyVCNG5nLSVDNCU5MSVDNiVBMS1QaGlsaXBzLU1HMzkxMS0xNS1NdWx0aWdyb29tLTMwMDAtN2luMS1jJUUxJUJBJUFGdC10JUUxJUJCJTg5YS1yJUMzJUIzYy0lQzQlOTFhLW4lQzQlODNuZy1zJUUxJUJCJUFELWQlRTElQkIlQTVuZy10JUUxJUJBJUExaS1uaCVDMyVBMC1pLjQ2MzYwMDA2MS40OTUxMTM1NzAxNw==&redirect_302=1",
    },
    {
        "id": "2",
        "name": "Sạc dự phòng Anker Zolo 20.000mAh 22.5W",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mlnj4c7kwkjp03",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773391&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vUyVFMSVCQSVBMWMtZCVFMSVCQiVCMS1waCVDMyVCMm5nLUFua2VyLVpvbG8tQTExMEQtMjAwMDBtQWgtY2h1JUUxJUJBJUE5bi0zQy1UcnVuZy1RdSVFMSVCQiU5MWMtYyVDMyVBMXAtVVNCLUMtdCVDMyVBRGNoLWglRTElQkIlQTNwLXMlRTElQkElQTFjLW5oYW5oLTIyLjVXLWkuMTIwMjg4OTY3OC40NTU1NDAxNDY3NQ==&redirect_302=1",
    },
    {
        "id": "3",
        "name": "Máy vặn vít pin Bosch GO 3",
        "image": "https://down-vn.img.susercontent.com/file/sg-11134201-8259d-mrbyk5d9m3gs2c",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773392&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktdiVFMSVCQSVCN24tdiVDMyVBRHQtcGluLUJvc2NoLUdvLTMtaS43NTgxMDI0OS4yNTUxNDU2ODgyOQ==&redirect_302=1",
    },
    {
        "id": "4",
        "name": "Máy hút bụi cầm tay Deerma DX118C 600W",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m83aax7f0sasfe",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773393&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktSCVDMyVCQXQtQiVFMSVCQiVBNWktQyVFMSVCQSVBN20tVGF5LURlZXJtYS1EWDExOEMtJTI4QiVFMSVCQSVBMk4tTSVFMSVCQiU5QUktNjAwVyUyOS1DaCVDMyVBRG5oLWglQzMlQTNuZy1EZWVybWEtaS4yODE0MzI4NC4yNzQ1Nzg2MDQwNA==&redirect_302=1",
    },
]

STYLE = '''<style id="lm-shop-grid-style-v3">
.lm-shop-grid{display:block!important;visibility:visible!important;opacity:1!important;width:100%;padding:18px 0 12px;background:#fff}.lm-shop-grid-inner{max-width:1180px;margin:auto;padding:0 16px}.lm-shop-grid-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:10px}.lm-shop-grid-head span{display:block;color:#ee4d2d;font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.lm-shop-grid-head h2{margin:2px 0 0;color:#203542;font-size:19px;line-height:1.2}.lm-shop-grid-head small{color:#84919a;font-size:10px;white-space:nowrap}.lm-shop-grid-items{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.lm-shop-item{display:block!important;visibility:visible!important;opacity:1!important;min-width:0;overflow:hidden;border:1px solid #e7ebee;border-radius:14px;background:#fff;color:#243542!important;text-decoration:none!important;box-shadow:0 2px 9px rgba(24,42,54,.05)}.lm-shop-item-media{aspect-ratio:1/1;background:linear-gradient(135deg,#f7f8fa,#edf1f4);overflow:hidden}.lm-shop-item-media img{display:block;width:100%;height:100%;object-fit:cover}.lm-shop-item-copy{padding:9px}.lm-shop-item-copy strong{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2;min-height:36px;font-size:12px;line-height:1.45;color:#263946}.lm-shop-item-copy b{display:flex;align-items:center;justify-content:center;min-height:38px;margin-top:8px;border-radius:9px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:900}.lm-shop-grid-note{margin:6px 1px 0;color:#929ca3;font-size:8.5px;line-height:1.35}
@media(max-width:700px){.lm-shop-grid{padding:14px 0 9px}.lm-shop-grid-inner{padding:0 10px}.lm-shop-grid-head h2{font-size:17px}.lm-shop-grid-head small{display:none}.lm-shop-grid-items{display:flex!important;gap:8px;overflow-x:auto;scroll-snap-type:x mandatory;padding:0 1px 4px;scrollbar-width:none}.lm-shop-grid-items::-webkit-scrollbar{display:none}.lm-shop-item{flex:0 0 min(42vw,170px);scroll-snap-align:start}.lm-shop-item-copy{padding:8px}.lm-shop-item-copy strong{font-size:11.5px;min-height:34px}.lm-shop-item-copy b{min-height:40px;font-size:10.5px}}
</style>'''

TRACK = '''<script id="lm-shop-grid-track-v3">(()=>{const root=document.querySelector('section[data-sitewide-products="true"]');if(!root)return;const push=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,merchant:'Shopee',affiliate_network:'ACCESSTRADE',placement:'lower_4_cards_v3',...extra})};let seen=false;const fire=()=>{if(seen)return;seen=true;push('affiliate_product_grid_view')};if('IntersectionObserver'in window){const o=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){fire();o.disconnect()}},{threshold:[.2]});o.observe(root)}else fire();root.addEventListener('click',e=>{const a=e.target.closest('[data-shop-item]');if(a)push('affiliate_product_click',{product_index:Number(a.dataset.shopItem||0),product_name:a.dataset.productName||''})})})();</script>'''


def remove_section(text: str, marker: str) -> str:
    while marker in text:
        pos = text.find(marker)
        start = text.rfind('<section', 0, pos)
        end = text.find('</section>', pos)
        if start < 0 or end < 0:
            break
        text = text[:start] + text[end + len('</section>'):]
    return text


def write_dispatcher(root: Path) -> None:
    target = root / 'go' / 'shopee' / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    mapping = {p['id']: p['url'] for p in PRODUCTS}
    payload = json.dumps(mapping, ensure_ascii=False).replace('</', '<\\/')
    target.write_text(
        '<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Đang mở sản phẩm</title></head>'
        '<body><p>Đang mở sản phẩm…</p><script>'
        f'const m={payload};const p=new URLSearchParams(location.search).get("p")||"1";location.replace(m[p]||m["1"]);'
        '</script></body></html>', encoding='utf-8')


def build_grid(home: bool) -> str:
    placement = ' data-affiliate-static-placement="after_tools"' if home else ''
    cards = []
    for index, product in enumerate(PRODUCTS, start=1):
        name = html.escape(product['name'])
        image = html.escape(product['image'], quote=True)
        cards.append(
            f'<a class="lm-shop-item" href="/go/shopee/?p={product["id"]}" target="_blank" rel="nofollow noopener" data-shop-item="{index}" data-product-name="{name}">'
            f'<div class="lm-shop-item-media"><img src="{image}" loading="lazy" decoding="async" alt="{name}"></div>'
            f'<div class="lm-shop-item-copy"><strong>{name}</strong><b>Xem trên Shopee →</b></div></a>'
        )
    return (
        f'<section class="lm-shop-grid"{placement} data-sitewide-products="true">'
        '<div class="lm-shop-grid-inner"><div class="lm-shop-grid-head"><div><span>Liên kết đối tác</span>'
        '<h2>Sản phẩm Shopee đang giới thiệu</h2></div><small>4 sản phẩm</small></div>'
        '<div class="lm-shop-grid-items">' + ''.join(cards) + '</div>'
        '<p class="lm-shop-grid-note">Website có thể nhận hoa hồng khi phát sinh giao dịch đủ điều kiện.</p></div></section>'
    )


def section_end_for_marker(text: str, marker: str) -> int | None:
    pos = text.find(marker)
    if pos < 0:
        return None
    start = text.rfind('<section', 0, pos)
    end = text.find('</section>', pos)
    if start < 0 or end < 0:
        return None
    return end + len('</section>')


def insert_grid(text: str, home: bool) -> str:
    if home:
        for marker in ('<h2>Công cụ thống kê XSMB</h2>', 'Công cụ thống kê XSMB', 'portal-tools'):
            end = section_end_for_marker(text, marker)
            if end is not None:
                return text[:end] + build_grid(True) + text[end:]
    end = text.lower().rfind('</main>')
    if end < 0:
        end = text.lower().rfind('</body>')
    if end < 0:
        raise ValueError('missing main/body end')
    return text[:end] + build_grid(home) + text[end:]


def apply(root: Path) -> dict[str, object]:
    write_dispatcher(root)
    if not FINANCE_SOURCE.is_file():
        raise FileNotFoundError(FINANCE_SOURCE)
    shutil.copy2(FINANCE_SOURCE, root / 'finance-gate-sitewide.js')

    pages = []
    for page in root.rglob('*.html'):
        rel = page.relative_to(root).as_posix()
        if rel in EXCLUDED or rel.startswith('go/'):
            continue
        pages.append(page)

    for page in pages:
        rel = page.relative_to(root).as_posix()
        text = page.read_text(encoding='utf-8')
        for marker in (
            'data-sitewide-affiliate="true"', 'data-primary-affiliate-strip="sitewide-v4"',
            'data-sitewide-products="true"', 'data-affiliate-static-placement="after_tools"',
            'class="lm-product-deals', 'data-primary-affiliate-strip="static-v3"',
            'data-primary-affiliate-strip="v2"', 'data-primary-affiliate-strip="restore-v1"',
        ):
            text = remove_section(text, marker)
        for style_id in ('lm-sitewide-affiliate-style', 'lm-sitewide-products-style', 'lm-shop-grid-style-v3'):
            text = re.sub(rf'<style\s+id="{style_id}">.*?</style>', '', text, flags=re.I | re.S)
        for script_id in ('lm-sitewide-affiliate-track', 'lm-sitewide-products-track', 'lm-shop-grid-track-v3'):
            text = re.sub(rf'<script\s+id="{script_id}">.*?</script>', '', text, flags=re.I | re.S)

        text = insert_grid(text, rel == 'index.html')
        if '</head>' not in text or '</body>' not in text:
            raise ValueError(rel)
        text = text.replace('</head>', STYLE + '</head>', 1)
        text = re.sub(r'<script\s+defer\s+src="/finance-gate\.js\?v=[^"]+"></script>', '', text, flags=re.I)
        text = re.sub(r'<script\s+defer\s+src="/finance-gate-sitewide\.js\?v=[^"]+"></script>', '', text, flags=re.I)
        text = text.replace('</head>', FINANCE_TAG + '</head>', 1)
        text = text.replace('</body>', TRACK + '</body>', 1)

        section = re.search(r'<section\b[^>]*\bdata-sitewide-products="true".*?</section>', text, flags=re.I | re.S)
        if not section or section.group(0).count('data-shop-item=') != 4:
            raise ValueError(f'{rel}: expected one four-card block')
        if 'go.isclix.com' in section.group(0):
            raise ValueError(f'{rel}: direct affiliate URL leaked into visible cards')
        if FINANCE_TAG not in text:
            raise ValueError(f'{rel}: finance runtime missing')
        page.write_text(text, encoding='utf-8')

    home = (root / 'index.html').read_text(encoding='utf-8')
    if home.count('data-affiliate-static-placement="after_tools" data-sitewide-products="true"') != 1:
        raise ValueError('home lower placement missing')

    # This is the final Python builder in the Pages pipeline. Re-run the phone
    # privacy gate here so no later portal/affiliate pass can re-introduce a
    # visible phone number or direct phone-based Zalo URL.
    import hide_public_phone_numbers as phone_privacy
    privacy = phone_privacy.sanitize(root)

    return {'status':'PASS','pages':len(pages),'top_banner_removed':True,'product_grid_lower':True,'product_count':4,'internal_product_links':True,'finance_sitewide':True,'phone_privacy':privacy['status']}


def self_test() -> None:
    import tempfile
    global FINANCE_SOURCE
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.joinpath('index.html').write_text('<html><head></head><body><main><section><h2>Công cụ thống kê XSMB</h2></section></main></body></html>', encoding='utf-8')
        root.joinpath('stats').mkdir(); root.joinpath('stats/index.html').write_text('<html><head></head><body><main><h1>Stats</h1></main></body></html>', encoding='utf-8')
        fake=root/'finance.js'; fake.write_text('x',encoding='utf-8'); old=FINANCE_SOURCE; FINANCE_SOURCE=fake
        try: result=apply(root)
        finally: FINANCE_SOURCE=old
        home=(root/'index.html').read_text(encoding='utf-8')
        assert result['status']=='PASS' and result['phone_privacy']=='PASS' and home.count('data-shop-item=')==4 and '/go/shopee/?p=1' in home
        assert 'go.isclix.com' not in re.search(r'<section class="lm-shop-grid".*?</section>',home,re.S).group(0)
        assert (root/'go'/'shopee'/'index.html').is_file()
        assert (root/'go'/'zalo'/'index.html').is_file()
    print('SITEWIDE_PRODUCT_SURFACE_SELF_TEST_OK')


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument('--output-root',type=Path,default=ROOT/'_site'); parser.add_argument('--self-test',action='store_true'); args=parser.parse_args()
    if args.self_test: self_test()
    else: print(apply(args.output_root))

if __name__=='__main__': main()
