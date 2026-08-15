#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEO_LINKS_MARKER = 'data-seo-discovery-links="true"'
SEO_LINKS = '''<div class="portal-fast-links" data-seo-discovery-links="true" aria-label="Dữ liệu XSMB chuyên sâu"><a href="/xsmb-30-ngay/">XSMB 30 ngày</a><a href="/nguon-du-lieu-xsmb/">Nguồn dữ liệu &amp; cách tính</a></div>'''
FORBIDDEN_AD_DOMAINS = (
    'effectivecpmnetwork.com',
    'highperformanceformat.com',
)
FORBIDDEN_AD_IDS = (
    'lm-adsterra-native',
    'lm-adsterra-300x250',
    'adsterra-native-1',
    'adsterra-banner-300x250',
)


def section_bounds(text: str, needle: str) -> tuple[int, int] | None:
    pos = text.find(needle)
    if pos < 0:
        return None
    start = pos if text.startswith('<section', pos) else text.rfind('<section', 0, pos)
    end = text.find('</section>', pos)
    if start < 0 or end < 0:
        return None
    return start, end + len('</section>')


def remove_section(text: str, needle: str) -> tuple[str, bool]:
    bounds = section_bounds(text, needle)
    if not bounds:
        return text, False
    start, end = bounds
    return text[:start] + text[end:], True


def remove_non_accesstrade_ads(text: str) -> tuple[str, bool]:
    before = text
    for marker in FORBIDDEN_AD_IDS:
        while marker in text:
            updated, removed = remove_section(text, marker)
            if not removed:
                break
            text = updated

    text = re.sub(
        r'<style\b[^>]*id="lm-final-monetization-style"[^>]*>.*?</style>',
        '',
        text,
        flags=re.I | re.S,
    )
    text = text.replace('<!-- LM_ADSTERRA_320X50_SLOT_PENDING -->', '')

    for domain in FORBIDDEN_AD_DOMAINS:
        if domain in text:
            raise ValueError(f'Non-ACCESSTRADE ad loader remains: {domain}')
    return text, text != before


def ensure_static_seo_links(text: str) -> tuple[str, bool]:
    if SEO_LINKS_MARKER in text:
        return text, False
    marker = '<div class="portal-tools">'
    start = text.find(marker)
    if start < 0:
        return text, False
    end = text.find('</div>', start + len(marker))
    if end < 0:
        return text, False
    end += len('</div>')
    return text[:end] + SEO_LINKS + text[end:], True


def normalize_affiliate_copy(text: str) -> tuple[str, bool]:
    before = text
    text = re.sub(
        r'Ưu đãi mua sắm Shopee(?:\s+ngày\s+\d{2}/\d{2}/\d{4})?',
        'Ưu đãi mua sắm Shopee',
        text,
    )
    text = text.replace(
        'Smartlink ACCESSTRADE · xem sản phẩm và ưu đãi đang được giới thiệu.',
        'Liên kết tài trợ ACCESSTRADE · mở Shopee để xem sản phẩm và ưu đãi hiện có.',
    )
    text = text.replace('aria-label="Liên kết đối tác"', 'aria-label="Liên kết tài trợ"')
    return text, text != before


def apply(root: Path) -> dict[str, object]:
    path = root / 'index.html'
    if not path.is_file():
        return {'status': 'SKIP', 'reason': 'missing_home'}

    text = path.read_text(encoding='utf-8')
    text, ads_removed = remove_non_accesstrade_ads(text)
    text, seo_changed = ensure_static_seo_links(text)
    text, affiliate_changed = normalize_affiliate_copy(text)
    path.write_text(text, encoding='utf-8')

    lowered = text.lower()
    for domain in FORBIDDEN_AD_DOMAINS:
        if domain in lowered:
            raise ValueError(f'Forbidden ad domain remains: {domain}')
    for marker in FORBIDDEN_AD_IDS:
        if marker in text:
            raise ValueError(f'Forbidden ad slot remains: {marker}')
    if re.search(r'Ưu đãi mua sắm Shopee\s+ngày\s+\d{2}/\d{2}/\d{4}', text):
        raise ValueError('Affiliate copy is incorrectly tied to report date')

    return {
        'status': 'PASS',
        'changed': any((ads_removed, seo_changed, affiliate_changed)),
        'placement': 'accesstrade_only',
        'static_seo_links': SEO_LINKS_MARKER in text,
        'affiliate_evergreen': True,
        'native_lazy': False,
        'adsterra_native': False,
        'adsterra_banner_300': False,
    }


def self_test() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        page = root / 'index.html'
        page.write_text(
            '<html><head><style id="lm-final-monetization-style">x</style></head><body>'
            '<section><div class="portal-tools"><a href="/a/">A</a></div></section>'
            '<section><div id="lm-adsterra-native"><script src="https://pl.example.effectivecpmnetwork.com/x"></script></div></section>'
            '<section aria-label="Liên kết đối tác"><a id="affiliate-shopee-smartlink"><b>Ưu đãi mua sắm Shopee ngày 16/08/2026</b><span>Smartlink ACCESSTRADE · xem sản phẩm và ưu đãi đang được giới thiệu.</span></a></section>'
            '<section><div id="lm-adsterra-300x250"><script src="https://www.highperformanceformat.com/x"></script></div></section>'
            '<section class="buy-simple portal-buy"><b>Mua</b></section>'
            '</body></html>',
            encoding='utf-8',
        )
        result = apply(root)
        text = page.read_text(encoding='utf-8')
        assert result['status'] == 'PASS' and result['changed']
        assert result['adsterra_native'] is False and result['adsterra_banner_300'] is False
        assert 'effectivecpmnetwork.com' not in text and 'highperformanceformat.com' not in text
        assert 'lm-adsterra' not in text and 'lm-final-monetization-style' not in text
        assert result['static_seo_links'] and 'Liên kết tài trợ ACCESSTRADE' in text
        assert 'Ưu đãi mua sắm Shopee ngày' not in text
        assert apply(root)['changed'] is False

        missing = Path(td) / 'missing'
        missing.mkdir()
        assert apply(missing)['status'] == 'SKIP'

    print('MONETIZATION_PLACEMENT_SELF_TEST_OK')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', type=Path, default=ROOT / '_site')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(apply(args.output_root), ensure_ascii=False))


if __name__ == '__main__':
    main()
