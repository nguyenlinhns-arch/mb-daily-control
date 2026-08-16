#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINANCE_SOURCE = ROOT / "site-v2" / "finance-gate-sitewide.js"
FINANCE_TAG = '<script defer src="/finance-gate-sitewide.js?v=20260816-2"></script>'
EXCLUDED = {"404.html", "go/shopee/index.html"}

PRODUCTS = [
    {
        "name": "Tông đơ Philips MG3911/15 7in1",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mp1ohea3di4g9e",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773390&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vVCVDMyVCNG5nLSVDNCU5MSVDNiVBMS1QaGlsaXBzLU1HMzkxMS0xNS1NdWx0aWdyb29tLTMwMDAtN2luMS1jJUUxJUJBJUFGdC10JUUxJUJCJTg5YS1yJUMzJUEydS10JUMzJUIzYy0lQzQlOTFhLW4lQzQlODNuZy1zJUUxJUJCJUFELWQlRTElQkIlQTVuZy10JUUxJUJBJUExaS1uaCVDMyVBMC1pLjQ2MzYwMDA2MS40OTUxMTM1NzAxNw==&redirect_302=1",
    },
    {
        "name": "Sạc dự phòng Anker Zolo 20.000mAh 22.5W",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mlnj4c7kwkjp03",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773391&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vUyVFMSVCQSVBMWMtZCVFMSVCQiVCMS1waCVDMyVCMm5nLUFua2VyLVpvbG8tQTExMEQtMjAwMDBtQWgtY2h1JUUxJUJBJUE5bi0zQy1UcnVuZy1RdSVFMSVCQiU5MWMtYyVDMyVBMXAtVVNCLUMtdCVDMyVBRGNoLWglRTElQkIlQTNwLXMlRTElQkElQTFjLW5oYW5oLTIyLjVXLWkuMTIwMjg4OTY3OC40NTU1NDAxNDY3NQ==&redirect_302=1",
    },
    {
        "name": "Máy vặn vít pin Bosch GO 3",
        "image": "https://down-vn.img.susercontent.com/file/sg-11134201-8259d-mrbyk5d9m3gs2c",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773392&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktdiVFMSVCQSVCN24tdiVDMyVBRHQtcGluLUJvc2NoLUdvLTMtaS43NTgxMDI0OS4yNTUxNDU2ODgyOQ==&redirect_302=1",
    },
    {
        "name": "Máy hút bụi cầm tay Deerma DX118C 600W",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m83aax7f0sasfe",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773393&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktSCVDMyVCQXQtQiVFMSVCQiVBNWktQyVFMSVCQSVBN20tVGF5LURlZXJtYS1EWDExOEMtJTI4QiVFMSVCQSVBMk4tTSVFMSVCQiU5QUktNjAwVyUyOS1DaCVDMyVBRG5oLWglQzMlQTNuZy1EZWVybWEtaS4yODE0MzI4NC4yNzQ1Nzg2MDQwNA==&redirect_302=1",
    },
]

STYLE = '''<style id="lm-sitewide-products-style">
.lm-sitewide-products{width:100%;padding:18px 0 10px}.lm-sitewide-products-inner{max-width:1180px;margin:auto;padding:0 16px}.lm-sitewide-products-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:9px}.lm-sitewide-products-kicker{display:block;color:#ee4d2d;font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.lm-sitewide-products-head h2{margin:2px 0 0;color:#203542;font-size:19px;line-height:1.2}.lm-sitewide-products-head small{color:#84919a;font-size:10px;white-space:nowrap}.lm-sitewide-products-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.lm-sitewide-product-card{min-width:0;overflow:hidden;border:1px solid #e7ebee;border-radius:14px;background:#fff;color:#243542!important;text-decoration:none!important;box-shadow:0 2px 9px rgba(24,42,54,.04)}.lm-sitewide-product-image{aspect-ratio:1/1;background:#f6f7f8;overflow:hidden}.lm-sitewide-product-image img{display:block;width:100%;height:100%;object-fit:cover}.lm-sitewide-product-copy{padding:9px}.lm-sitewide-product-copy strong{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2;min-height:36px;font-size:12px;line-height:1.45;color:#263946}.lm-sitewide-product-copy span{display:flex;align-items:center;justify-content:center;min-height:38px;margin-top:8px;border-radius:9px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:900}.lm-sitewide-products-note{margin:6px 1px 0;color:#929ca3;font-size:8.5px;line-height:1.35}
@media(max-width:700px){.lm-sitewide-products{padding:14px 0 8px}.lm-sitewide-products-inner{padding:0 10px}.lm-sitewide-products-head h2{font-size:17px}.lm-sitewide-products-head small{display:none}.lm-sitewide-products-grid{display:flex;gap:8px;overflow-x:auto;scroll-snap-type:x mandatory;padding:0 1px 4px;scrollbar-width:none}.lm-sitewide-products-grid::-webkit-scrollbar{display:none}.lm-sitewide-product-card{flex:0 0 min(42vw,170px);scroll-snap-align:start}.lm-sitewide-product-copy{padding:8px}.lm-sitewide-product-copy strong{font-size:11.5px;min-height:34px}.lm-sitewide-product-copy span{min-height:40px;font-size:10.5px}}
</style>'''

TRACK = '''<script id="lm-sitewide-products-track">(()=>{const grid=document.querySelector('[data-sitewide-products="true"]');if(!grid)return;const push=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,affiliate_network:'ACCESSTRADE',merchant:'Shopee',placement:'sitewide_lower_products',...extra})};let fired=false;const fire=()=>{if(fired)return;fired=true;push('affiliate_product_grid_view')};if('IntersectionObserver'in window){const o=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting&&e.intersectionRatio>=.35)){fire();o.disconnect()}},{threshold:[.35]});o.observe(grid)}else fire();document.addEventListener('click',e=>{const t=e.target instanceof Element?e.target:null;if(!t)return;const card=t.closest('[data-sitewide-product]');if(card)push('affiliate_product_click',{product_index:Number(card.dataset.sitewideProduct||0),product_name:card.dataset.productName||''})},true)})();</script>'''


def remove_section(text: str, marker: str) -> str:
    while marker in text:
        pos = text.find(marker)
        start = text.rfind('<section', 0, pos)
        end = text.find('</section>', pos)
        if start < 0 or end < 0:
            break
        text = text[:start] + text[end + len('</section>'):]
    return text


def build_products() -> str:
    cards = []
    for index, product in enumerate(PRODUCTS, start=1):
        cards.append(
            f'<a class="lm-sitewide-product-card" href="{product["url"]}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-sitewide-product="{index}" data-product-name="{product["name"]}">'
            f'<div class="lm-sitewide-product-image"><img src="{product["image"]}" loading="lazy" decoding="async" alt="{product["name"]}"></div>'
            f'<div class="lm-sitewide-product-copy"><strong>{product["name"]}</strong><span>Xem trên Shopee →</span></div></a>'
        )
    return '<section class="lm-sitewide-products" data-sitewide-products="true" aria-label="4 sản phẩm Shopee qua ACCESSTRADE"><div class="lm-sitewide-products-inner"><div class="lm-sitewide-products-head"><div><span class="lm-sitewide-products-kicker">Tài trợ · ACCESSTRADE</span><h2>Sản phẩm Shopee đang giới thiệu</h2></div><small>4 sản phẩm · mở trực tiếp trên Shopee</small></div><div class="lm-sitewide-products-grid">' + ''.join(cards) + '</div><p class="lm-sitewide-products-note">Liên kết đối tác · giá và ưu đãi xem trực tiếp trên Shopee.</p></div></section>'


def insert_before_main_end(text: str, markup: str) -> str:
    end = text.lower().rfind('</main>')
    if end >= 0:
        return text[:end] + markup + text[end:]
    end = text.lower().rfind('</body>')
    if end >= 0:
        return text[:end] + markup + text[end:]
    raise ValueError('HTML missing main/body end')


def apply(root: Path) -> dict[str, object]:
    pages = [p for p in root.rglob('*.html') if p.relative_to(root).as_posix() not in EXCLUDED and not p.relative_to(root).as_posix().startswith('go/shopee/')]
    if not pages:
        return {'status': 'SKIP', 'reason': 'no_public_html', 'pages': 0}
    if not FINANCE_SOURCE.is_file():
        raise FileNotFoundError(FINANCE_SOURCE)

    shutil.copy2(FINANCE_SOURCE, root / 'finance-gate-sitewide.js')
    injected = 0
    for page in pages:
        rel = page.relative_to(root).as_posix()
        text = page.read_text(encoding='utf-8')

        # Remove the top sitewide banner introduced by the previous iteration.
        text = remove_section(text, 'data-sitewide-affiliate="true"')
        text = remove_section(text, 'data-primary-affiliate-strip="sitewide-v4"')
        text = re.sub(r'<style\s+id="lm-sitewide-affiliate-style">.*?</style>', '', text, flags=re.I | re.S)
        text = re.sub(r'<script\s+id="lm-sitewide-affiliate-track">.*?</script>', '', text, flags=re.I | re.S)

        # Keep the existing four-card grid on home; inject the same lower placement on subpages.
        if rel == 'index.html' and ('data-affiliate-static-placement="after_tools"' in text or 'lm-static-product-grid' in text):
            text = text.replace('data-affiliate-static-placement="after_tools"', 'data-affiliate-static-placement="after_tools" data-sitewide-products="true"', 1)
        else:
            text = remove_section(text, 'data-sitewide-products="true"')
            text = insert_before_main_end(text, build_products())

        if 'id="lm-sitewide-products-style"' not in text:
            if '</head>' not in text:
                raise ValueError(f'{rel}: missing </head>')
            text = text.replace('</head>', STYLE + '</head>', 1)

        # Keep exactly one VPBank sitewide runtime everywhere.
        text = re.sub(r'<script\s+defer\s+src="/finance-gate\.js\?v=[^"]+"></script>', '', text, flags=re.I)
        text = re.sub(r'<script\s+defer\s+src="/finance-gate-sitewide\.js\?v=[^"]+"></script>', '', text, flags=re.I)
        text = text.replace('</head>', FINANCE_TAG + '</head>', 1)

        text = re.sub(r'<script\s+id="lm-sitewide-products-track">.*?</script>', '', text, flags=re.I | re.S)
        if '</body>' not in text:
            raise ValueError(f'{rel}: missing </body>')
        text = text.replace('</body>', TRACK + '</body>', 1)

        if 'data-sitewide-products="true"' not in text or FINANCE_TAG not in text:
            raise ValueError(f'{rel}: lower product/finance contract missing')
        if 'data-sitewide-affiliate="true"' in text or 'sitewide-v4' in text:
            raise ValueError(f'{rel}: top Shopee banner still present')
        page.write_text(text, encoding='utf-8')
        injected += 1

    home = (root / 'index.html').read_text(encoding='utf-8')
    if home.find('data-sitewide-products="true"') < home.find('<main'):
        raise ValueError('Homepage product grid is unexpectedly above main content')
    return {'status': 'PASS', 'pages': injected, 'top_banner_removed': True, 'product_grid_lower': True, 'finance_sitewide': True, 'product_count': 4}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.joinpath('index.html').write_text('<html><head></head><body><main><h1>Home</h1><section data-affiliate-static-placement="after_tools" class="lm-static-product-grid">products</section></main></body></html>', encoding='utf-8')
        root.joinpath('stats').mkdir()
        root.joinpath('stats/index.html').write_text('<html><head></head><body><main><h1>Stats</h1></main></body></html>', encoding='utf-8')
        source = root / 'fake-finance.js'; source.write_text('x', encoding='utf-8')
        global FINANCE_SOURCE
        old = FINANCE_SOURCE; FINANCE_SOURCE = source
        try:
            result = apply(root)
        finally:
            FINANCE_SOURCE = old
        assert result['status'] == 'PASS' and result['pages'] == 2
        for p in (root/'index.html', root/'stats/index.html'):
            text = p.read_text(encoding='utf-8')
            assert 'data-sitewide-products="true"' in text
            assert 'data-sitewide-affiliate="true"' not in text
            assert '/finance-gate-sitewide.js?v=20260816-2' in text
    print('SITEWIDE_PRODUCT_SURFACE_SELF_TEST_OK')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', type=Path, default=ROOT / '_site')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(apply(args.output_root))

if __name__ == '__main__':
    main()
