#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOPEE_SMARTLINK = "https://nguyenlinhtkv_aul4jx.accesslanding.site"
INTERNAL_SHOPEE_PATH = "/go/shopee/"
FINANCE_SOURCE = ROOT / "site-v2" / "finance-gate-sitewide.js"
FINANCE_TAG = '<script defer src="/finance-gate-sitewide.js?v=20260816-1"></script>'
STYLE_ID = "lm-sitewide-affiliate-style"
TRACK_ID = "lm-sitewide-affiliate-track"
EXCLUDED = {"404.html", "go/shopee/index.html"}

STYLE = '''<style id="lm-sitewide-affiliate-style">
.lm-sitewide-affiliate{width:100%;padding:8px 0;background:transparent}.lm-sitewide-affiliate-inner{max-width:1180px;margin:auto;padding:0 16px}.lm-sitewide-affiliate-card{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:13px 14px;border:1px solid #f0d7cc;border-radius:14px;background:linear-gradient(135deg,#fff8f4,#fff);color:#263744!important;text-decoration:none!important;box-shadow:0 3px 14px rgba(39,29,24,.05)}.lm-sitewide-affiliate-badge{display:inline-flex;margin-bottom:3px;padding:3px 6px;border-radius:999px;background:#fff0e8;color:#b84b16;font-size:8px;font-weight:1000;letter-spacing:.07em;text-transform:uppercase}.lm-sitewide-affiliate-card strong{display:block;font-size:14px;line-height:1.25}.lm-sitewide-affiliate-card small{display:block;margin-top:3px;color:#71808a;font-size:10.5px;line-height:1.4}.lm-sitewide-affiliate-cta{display:flex;align-items:center;justify-content:center;min-height:42px;padding:0 13px;border-radius:10px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:1000;white-space:nowrap}.lm-sitewide-affiliate-note{margin:5px 2px 0;color:#929ba1;font-size:8.5px;line-height:1.35}
@media(max-width:700px){.lm-sitewide-affiliate{padding:6px 0}.lm-sitewide-affiliate-inner{padding:0 10px}.lm-sitewide-affiliate-card{grid-template-columns:1fr;gap:8px;padding:11px 12px}.lm-sitewide-affiliate-card strong{font-size:13px}.lm-sitewide-affiliate-card small{font-size:10px}.lm-sitewide-affiliate-cta{width:100%;min-height:44px}}
</style>'''

TRACK = '''<script id="lm-sitewide-affiliate-track">(()=>{const strip=document.querySelector('[data-sitewide-affiliate="true"]');if(!strip)return;const push=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,affiliate_network:'ACCESSTRADE',merchant:'Shopee',placement:'sitewide_top',...extra})};let fired=false;const fire=()=>{if(fired)return;fired=true;push('affiliate_shopee_strip_view')};if('IntersectionObserver'in window){const o=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting&&e.intersectionRatio>=.35)){fire();o.disconnect()}},{threshold:[.35]});o.observe(strip)}else fire();strip.addEventListener('click',()=>{try{sessionStorage.setItem('lm_affiliate_intent_v1','1')}catch(_){}push('affiliate_shopee_strip_click')})})();</script>'''


def remove_section(text: str, marker: str) -> str:
    while marker in text:
        pos = text.find(marker)
        start = text.rfind('<section', 0, pos)
        end = text.find('</section>', pos)
        if start < 0 or end < 0:
            break
        text = text[:start] + text[end + len('</section>'):]
    return text


def strip_markup() -> str:
    return f'''<section class="lm-sitewide-affiliate" data-sitewide-affiliate="true" aria-label="Ưu đãi Shopee tài trợ ACCESSTRADE"><div class="lm-sitewide-affiliate-inner"><a class="lm-sitewide-affiliate-card" href="{INTERNAL_SHOPEE_PATH}" rel="sponsored nofollow"><div><span class="lm-sitewide-affiliate-badge">Tài trợ · ACCESSTRADE</span><strong>Shopee · xem ưu đãi mua sắm hôm nay</strong><small>Mở Shopee để xem sản phẩm và ưu đãi đang có. Giá mua không tăng vì liên kết này.</small></div><span class="lm-sitewide-affiliate-cta">XEM ƯU ĐÃI →</span></a><p class="lm-sitewide-affiliate-note">Website có thể nhận hoa hồng khi phát sinh giao dịch đủ điều kiện.</p></div></section>'''


def write_redirect(root: Path) -> None:
    target = root / 'go' / 'shopee' / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Đang mở Shopee</title>'
        f'<meta http-equiv="refresh" content="0;url={SHOPEE_SMARTLINK}"></head><body>'
        '<p>Đang mở ưu đãi Shopee…</p>'
        f'<script>location.replace({SHOPEE_SMARTLINK!r});</script></body></html>',
        encoding='utf-8',
    )


def insert_after_opening_main(text: str, markup: str) -> str:
    match = re.search(r'<main\b[^>]*>', text, flags=re.I)
    if match:
        return text[:match.end()] + markup + text[match.end():]
    match = re.search(r'<body\b[^>]*>', text, flags=re.I)
    if match:
        return text[:match.end()] + markup + text[match.end():]
    raise ValueError('HTML missing main/body anchor')


def apply(root: Path) -> dict[str, object]:
    pages = [p for p in root.rglob('*.html') if p.relative_to(root).as_posix() not in EXCLUDED and not p.relative_to(root).as_posix().startswith('go/shopee/')]
    if not pages:
        return {'status': 'SKIP', 'reason': 'no_public_html', 'pages': 0}
    if not FINANCE_SOURCE.is_file():
        raise FileNotFoundError(FINANCE_SOURCE)

    write_redirect(root)
    shutil.copy2(FINANCE_SOURCE, root / 'finance-gate-sitewide.js')
    injected = 0
    for page in pages:
        rel = page.relative_to(root).as_posix()
        text = page.read_text(encoding='utf-8')
        text = remove_section(text, 'data-sitewide-affiliate="true"')
        # Retire the older home strip so the sitewide strip becomes the one canonical visible banner.
        if rel == 'index.html':
            text = remove_section(text, 'data-primary-affiliate-strip="static-v3"')
            text = remove_section(text, 'data-primary-affiliate-strip="v2"')
            text = remove_section(text, 'data-primary-affiliate-strip="restore-v1"')
        if f'id="{STYLE_ID}"' not in text:
            if '</head>' not in text:
                raise ValueError(f'{rel}: missing </head>')
            text = text.replace('</head>', STYLE + '</head>', 1)
        text = re.sub(r'<script\s+defer\s+src="/finance-gate-sitewide\.js\?v=[^"]+"></script>', '', text, flags=re.I)
        if '</head>' not in text:
            raise ValueError(f'{rel}: missing </head> for finance runtime')
        text = text.replace('</head>', FINANCE_TAG + '</head>', 1)
        text = re.sub(r'<script\s+id="lm-sitewide-affiliate-track">.*?</script>', '', text, flags=re.I | re.S)
        text = insert_after_opening_main(text, strip_markup())
        if '</body>' not in text:
            raise ValueError(f'{rel}: missing </body>')
        text = text.replace('</body>', TRACK + '</body>', 1)
        if 'data-sitewide-affiliate="true"' not in text or FINANCE_TAG not in text:
            raise ValueError(f'{rel}: sitewide affiliate contract missing')
        page.write_text(text, encoding='utf-8')
        injected += 1

    # Home must expose the banner in static HTML without waiting for JS.
    home = (root / 'index.html').read_text(encoding='utf-8')
    if 'data-sitewide-affiliate="true"' not in home or INTERNAL_SHOPEE_PATH not in home:
        raise ValueError('Homepage sitewide affiliate strip missing')
    return {'status': 'PASS', 'pages': injected, 'home_static': True, 'shopee_redirect': True, 'finance_sitewide': True}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.joinpath('index.html').write_text('<html><head></head><body><main><h1>Home</h1></main></body></html>', encoding='utf-8')
        root.joinpath('stats').mkdir()
        root.joinpath('stats/index.html').write_text('<html><head></head><body><main><h1>Stats</h1></main></body></html>', encoding='utf-8')
        source = root / 'fake-finance.js'
        source.write_text('x', encoding='utf-8')
        global FINANCE_SOURCE
        old = FINANCE_SOURCE
        FINANCE_SOURCE = source
        try:
            result = apply(root)
        finally:
            FINANCE_SOURCE = old
        assert result['status'] == 'PASS' and result['pages'] == 2
        assert all('data-sitewide-affiliate="true"' in p.read_text(encoding='utf-8') for p in (root/'index.html', root/'stats/index.html'))
        assert (root/'go/shopee/index.html').is_file()
    print('SITEWIDE_AFFILIATE_SELF_TEST_OK')


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
