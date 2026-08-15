#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEO_LINKS_MARKER = 'data-seo-discovery-links="true"'
SEO_LINKS = '''<div class="portal-fast-links" data-seo-discovery-links="true" aria-label="Dữ liệu XSMB chuyên sâu"><a href="/xsmb-30-ngay/">XSMB 30 ngày</a><a href="/nguon-du-lieu-xsmb/">Nguồn dữ liệu &amp; cách tính</a></div>'''
VPBANK_URL = 'https://go.isclix.com/deep_link/v6/6342443575996511342/6822308958202075636?sub4=oneatweb&url_enc=aHR0cHM6Ly92YXlvbmxpbmUudnBiYW5rLmNvbS52bi8%3D'
VPBANK_STYLE = '''<style id="lm-finance-top-style">.lm-finance-top{width:100%;padding:7px 0;background:#f4f7f6;border-bottom:1px solid #dfe7e3}.lm-finance-top-inner{width:min(calc(100% - 28px),1180px);margin:auto}.lm-finance-top-card{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center;padding:12px 15px;border-radius:14px;background:linear-gradient(135deg,#123f32,#0b2f28);color:#fff;text-decoration:none!important;box-shadow:0 5px 16px rgba(15,50,40,.16)}.lm-finance-top-label{display:block;margin-bottom:3px;color:#c7ded5;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}.lm-finance-top-copy strong{display:block;font-size:16px;line-height:1.25;color:#fff}.lm-finance-top-rate{display:block;margin-top:4px;color:#fff;font-size:13px;font-weight:900}.lm-finance-top-cta{min-height:42px;padding:0 14px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#fff;color:#143f32!important;font-size:12px;font-weight:900;white-space:nowrap}@media(max-width:700px){.lm-finance-top{padding:5px 0}.lm-finance-top-inner{width:calc(100% - 20px)}.lm-finance-top-card{grid-template-columns:1fr;padding:10px 11px;gap:7px}.lm-finance-top-copy strong{font-size:15px}.lm-finance-top-rate{font-size:12.5px}.lm-finance-top-cta{min-height:42px;width:100%}}</style>'''
VPBANK_HTML = f'''<section id="lm-finance-top" class="lm-finance-top" data-static-finance-banner="true" aria-label="Liên kết tài trợ vay online VPBank qua ACCESSTRADE"><div class="lm-finance-top-inner"><a class="lm-finance-top-card" href="{VPBANK_URL}" target="_blank" rel="sponsored nofollow noopener noreferrer"><div class="lm-finance-top-copy"><span class="lm-finance-top-label">Liên kết tài trợ · ACCESSTRADE</span><strong>Vay online VPBank</strong><span class="lm-finance-top-rate">Từ 1,2%/tháng · Đăng ký ban đầu chỉ cần Căn cước công dân</span></div><span class="lm-finance-top-cta">Vay tiền nhanh online →</span></a></div></section>'''
FORBIDDEN_AD_DOMAINS = ('effectivecpmnetwork.com','highperformanceformat.com')
FORBIDDEN_AD_IDS = ('lm-adsterra-native','lm-adsterra-300x250','adsterra-native-1','adsterra-banner-300x250')


def section_bounds(text: str, needle: str) -> tuple[int, int] | None:
    pos = text.find(needle)
    if pos < 0:return None
    start = pos if text.startswith('<section', pos) else text.rfind('<section', 0, pos)
    end = text.find('</section>', pos)
    if start < 0 or end < 0:return None
    return start, end + len('</section>')


def remove_section(text: str, needle: str) -> tuple[str, bool]:
    bounds = section_bounds(text, needle)
    if not bounds:return text, False
    start, end = bounds
    return text[:start] + text[end:], True


def remove_non_accesstrade_ads(text: str) -> tuple[str, bool]:
    before = text
    for marker in FORBIDDEN_AD_IDS:
        while marker in text:
            updated, removed = remove_section(text, marker)
            if not removed:break
            text = updated
    text = re.sub(r'<style\b[^>]*id="lm-final-monetization-style"[^>]*>.*?</style>','',text,flags=re.I|re.S)
    text = text.replace('<!-- LM_ADSTERRA_320X50_SLOT_PENDING -->','')
    for domain in FORBIDDEN_AD_DOMAINS:
        if domain in text:raise ValueError(f'Non-ACCESSTRADE ad loader remains: {domain}')
    return text, text != before


def ensure_static_seo_links(text: str) -> tuple[str, bool]:
    if SEO_LINKS_MARKER in text:return text, False
    marker = '<div class="portal-tools">'
    start = text.find(marker)
    if start < 0:return text, False
    end = text.find('</div>', start + len(marker))
    if end < 0:return text, False
    end += len('</div>')
    return text[:end] + SEO_LINKS + text[end:], True


def normalize_affiliate_copy(text: str) -> tuple[str, bool]:
    before = text
    text = re.sub(r'Ưu đãi mua sắm Shopee(?:\s+ngày\s+\d{2}/\d{2}/\d{4})?','Ưu đãi mua sắm Shopee',text)
    text = text.replace('Smartlink ACCESSTRADE · xem sản phẩm và ưu đãi đang được giới thiệu.','Liên kết tài trợ ACCESSTRADE · mở Shopee để xem sản phẩm và ưu đãi hiện có.')
    text = text.replace('aria-label="Liên kết đối tác"','aria-label="Liên kết tài trợ"')
    return text, text != before


def ensure_static_vpbank(text: str) -> tuple[str, bool]:
    if 'id="lm-finance-top"' in text:
        changed = False
        if 'data-static-finance-banner="true"' not in text:
            text = text.replace('id="lm-finance-top"','id="lm-finance-top" data-static-finance-banner="true"',1)
            changed = True
        if 'id="lm-finance-top-style"' not in text:
            if '</head>' not in text:raise ValueError('Missing head for finance style')
            text = text.replace('</head>',VPBANK_STYLE+'</head>',1)
            changed = True
        return text, changed
    if '</head>' not in text:raise ValueError('Missing head for finance style')
    text = text.replace('</head>',VPBANK_STYLE+'</head>',1)
    insert = text.find('<section class="portal-hero"')
    if insert < 0:insert = text.find('<main')
    if insert < 0:
        body = re.search(r'<body\b[^>]*>', text, flags=re.I)
        if not body:raise ValueError('Missing body for finance banner')
        insert = body.end()
    text = text[:insert] + VPBANK_HTML + '\n' + text[insert:]
    return text, True


def apply(root: Path) -> dict[str, object]:
    path = root / 'index.html'
    if not path.is_file():return {'status':'SKIP','reason':'missing_home'}
    text = path.read_text(encoding='utf-8')
    text, ads_removed = remove_non_accesstrade_ads(text)
    text, seo_changed = ensure_static_seo_links(text)
    text, affiliate_changed = normalize_affiliate_copy(text)
    text, finance_changed = ensure_static_vpbank(text)
    path.write_text(text, encoding='utf-8')
    lowered = text.lower()
    for domain in FORBIDDEN_AD_DOMAINS:
        if domain in lowered:raise ValueError(f'Forbidden ad domain remains: {domain}')
    for marker in FORBIDDEN_AD_IDS:
        if marker in text:raise ValueError(f'Forbidden ad slot remains: {marker}')
    if re.search(r'Ưu đãi mua sắm Shopee\s+ngày\s+\d{2}/\d{2}/\d{4}',text):raise ValueError('Affiliate copy is incorrectly tied to report date')
    if 'data-static-finance-banner="true"' not in text or 'Từ 1,2%/tháng · Đăng ký ban đầu chỉ cần Căn cước công dân' not in text:raise ValueError('Static VPBank banner missing')
    return {'status':'PASS','changed':any((ads_removed,seo_changed,affiliate_changed,finance_changed)),'placement':'accesstrade_only','static_seo_links':SEO_LINKS_MARKER in text,'affiliate_evergreen':True,'vpbank_static_top':True,'adsterra_native':False,'adsterra_banner_300':False}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); page = root/'index.html'
        page.write_text('<html><head><style id="lm-final-monetization-style">x</style></head><body><header></header><section class="portal-hero"><h1>Hero</h1></section><section><div class="portal-tools"><a href="/a/">A</a></div></section><section aria-label="Liên kết đối tác"><a id="affiliate-shopee-smartlink"><b>Ưu đãi mua sắm Shopee ngày 16/08/2026</b><span>Smartlink ACCESSTRADE · xem sản phẩm và ưu đãi đang được giới thiệu.</span></a></section><section><div id="lm-adsterra-native"><script src="https://pl.example.effectivecpmnetwork.com/x"></script></div></section><section><div id="lm-adsterra-300x250"><script src="https://www.highperformanceformat.com/x"></script></div></section></body></html>',encoding='utf-8')
        result = apply(root); text = page.read_text(encoding='utf-8')
        assert result['status']=='PASS' and result['changed'] and result['vpbank_static_top']
        assert 'effectivecpmnetwork.com' not in text and 'highperformanceformat.com' not in text and 'lm-adsterra' not in text
        assert result['static_seo_links'] and 'Liên kết tài trợ ACCESSTRADE' in text
        assert text.find('id="lm-finance-top"') < text.find('<section class="portal-hero"')
        assert 'Từ 1,2%/tháng · Đăng ký ban đầu chỉ cần Căn cước công dân' in text
        assert 'Ưu đãi mua sắm Shopee ngày' not in text
        missing = Path(td)/'missing'; missing.mkdir(); assert apply(missing)['status']=='SKIP'
    print('MONETIZATION_PLACEMENT_SELF_TEST_OK')


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument('--output-root',type=Path,default=ROOT/'_site'); parser.add_argument('--self-test',action='store_true'); args=parser.parse_args()
    if args.self_test:self_test()
    else:print(json.dumps(apply(args.output_root),ensure_ascii=False))

if __name__=='__main__':main()
