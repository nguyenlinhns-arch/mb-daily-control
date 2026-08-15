#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def remove_section_containing(text: str, marker: str) -> tuple[str, bool]:
    pos = text.find(marker)
    if pos < 0:
        return text, False
    start = text.rfind('<section', 0, pos)
    end = text.find('</section>', pos)
    if start < 0 or end < 0:
        raise RuntimeError(f'Cannot isolate section containing {marker}')
    return text[:start] + text[end + len('</section>'):], True


def clean_portal_builder() -> bool:
    path = ROOT / 'scripts' / 'apply_portal_v3_assets.py'
    text = path.read_text(encoding='utf-8')
    before = text

    text, count = re.subn(
        r"\nNATIVE_AD='''.*?'''\n\nBANNER_300='''.*?'''\nMOBILE_320_MARKER='[^']*'\n",
        "\n# Monetization policy: ACCESSTRADE only.\n",
        text,
        count=1,
        flags=re.S,
    )
    if count not in (0, 1):
        raise RuntimeError(f'Unexpected Adsterra constant matches: {count}')

    text = re.sub(
        r"\n    methods=section_around\(text,'<h2>Phương pháp công khai hôm nay</h2>'\).*?changed=True\n"
        r"    buy=text\.find\('<section class=\"buy-simple portal-buy\"'\).*?changed=True\n",
        "\n",
        text,
        count=1,
        flags=re.S,
    )

    text = text.replace(
        "    return {'status':'PASS','changed':changed,'affiliate':'affiliate-shopee-smartlink' in text,'native':'lm-adsterra-native' in text,'banner_300':'lm-adsterra-300x250' in text,'mobile_320_slot':MOBILE_320_MARKER in text}",
        "    return {'status':'PASS','changed':changed,'affiliate':'affiliate-shopee-smartlink' in text,'native':False,'banner_300':False,'mobile_320_slot':False}",
    )
    text = text.replace(
        "        assert m['affiliate'] and m['native'] and m['banner_300'] and MOBILE_320_MARKER in t",
        "        assert m['affiliate'] and not m['native'] and not m['banner_300'] and 'lm-adsterra' not in t",
    )

    # Dead Adsterra-only CSS is removed too; affiliate styling remains.
    text = text.replace('.lm-affiliate-section,.lm-ad-slot{width:100%;padding:8px 0}', '.lm-affiliate-section{width:100%;padding:8px 0}')
    text = text.replace('.lm-affiliate-inner,.lm-ad-inner{max-width:1180px;margin:auto;padding:0 16px}', '.lm-affiliate-inner{max-width:1180px;margin:auto;padding:0 16px}')
    text = re.sub(r'\.lm-ad-inner\{text-align:center\}.*?\.lm-mobile-320-slot\{display:none\}', '', text, count=1)
    text = text.replace('.lm-affiliate-section,.lm-ad-slot{padding:6px 0}', '.lm-affiliate-section{padding:6px 0}')
    text = text.replace('.lm-affiliate-inner,.lm-ad-inner{padding:0 10px}', '.lm-affiliate-inner{padding:0 10px}')
    text = re.sub(r'\.lm-ad-label\{margin-bottom:4px\}\.lm-ad-box--300\{max-width:300px\}\.lm-ad-box\{overflow:hidden\}', '', text, count=1)

    if text != before:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def clean_legacy_ai_page() -> bool:
    path = ROOT / 'ai-methods' / 'index.html'
    text = path.read_text(encoding='utf-8')
    before = text

    text = re.sub(
        r'\n\s*/\* Adsterra display monetization v1 \*/.*?(?=\n\s*</style>)',
        '',
        text,
        count=1,
        flags=re.S,
    )
    for marker in ('id="adsterra-native-1"', 'id="adsterra-banner-300x250"'):
        text, _ = remove_section_containing(text, marker)

    if text != before:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def clean_legacy_workflow() -> bool:
    path = ROOT / '.github' / 'workflows' / 'clarify-xsmb-statistics.yml'
    text = path.read_text(encoding='utf-8')
    before = text

    text = re.sub(
        r'\n      - name: Deploy Adsterra units\n.*?(?=\n      - name: Commit\n)',
        '',
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace(
        "if git diff --quiet -- ai-methods/landing-v3.html ai-methods/index.html; then exit 0; fi",
        "if git diff --quiet -- ai-methods/landing-v3.html; then exit 0; fi",
    )
    text = text.replace(
        'git add ai-methods/landing-v3.html ai-methods/index.html',
        'git add ai-methods/landing-v3.html',
    )
    text = text.replace(
        "git commit -m 'Add Adsterra native and display ads'",
        "git commit -m 'Clarify XSMB statistics wording'",
    )

    if text != before:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def verify() -> None:
    active = [
        ROOT / 'scripts' / 'apply_portal_v3_assets.py',
        ROOT / 'ai-methods' / 'index.html',
        ROOT / '.github' / 'workflows' / 'clarify-xsmb-statistics.yml',
    ]
    forbidden = re.compile(r'effectivecpmnetwork\.com|highperformanceformat\.com|id="lm-adsterra|id="adsterra-', re.I)
    found = [str(p.relative_to(ROOT)) for p in active if forbidden.search(p.read_text(encoding='utf-8'))]
    if found:
        raise RuntimeError(f'Non-ACCESSTRADE ad code remains in active sources: {found}')

    checkout = (ROOT / 'site-v2' / 'checkout-enhance.js').read_text(encoding='utf-8')
    finance = (ROOT / 'site-v2' / 'finance-banner.js').read_text(encoding='utf-8')
    if 'go.isclix.com/deep_link' not in checkout or 'go.isclix.com/deep_link' not in finance:
        raise RuntimeError('Expected ACCESSTRADE deep links are missing')


def main() -> None:
    changed = []
    if clean_portal_builder(): changed.append('scripts/apply_portal_v3_assets.py')
    if clean_legacy_ai_page(): changed.append('ai-methods/index.html')
    if clean_legacy_workflow(): changed.append('.github/workflows/clarify-xsmb-statistics.yml')
    verify()
    print('ACCESSTRADE_ONLY_OK')
    for item in changed:
        print(item)


if __name__ == '__main__':
    main()
