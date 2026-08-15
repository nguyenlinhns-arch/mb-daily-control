#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NAV = [
    ('/', 'Trang chủ'),
    ('/cho-so-mien-bac-hom-nay/', 'Hôm nay'),
    ('/thong-ke-xsmb/', 'Thống kê'),
    ('/tan-suat-xsmb/', 'Tần suất'),
    ('/lo-gan-xsmb/', 'Lô gan'),
    ('/cap-dao-xsmb/', 'Cặp đảo'),
    ('/thong-ke-dau-duoi-xsmb/', 'Đầu/đuôi'),
    ('/tra-cuu-xsmb/', 'Tra cứu'),
    ('/phuong-phap-cong-khai/', 'Phương pháp'),
    ('/thong-ke-lo-to-mien-bac-bang-ai/', 'AI'),
]

FOOT = [
    ('/thong-ke-xsmb/', 'Trung tâm thống kê'),
    ('/tan-suat-xsmb/', 'Tần suất 00–99'),
    ('/lo-gan-xsmb/', 'Lô gan XSMB'),
    ('/cap-dao-xsmb/', '45 cặp đảo'),
    ('/thong-ke-dau-duoi-xsmb/', 'Đầu/đuôi 0–9'),
    ('/tra-cuu-xsmb/', 'Tra cứu bộ số'),
    ('/phuong-phap-cong-khai/', 'Phương pháp công khai'),
    ('/cho-so-mien-bac-hom-nay/', 'Phương pháp hôm nay'),
    ('/phuong-phap-4so/', 'Giới thiệu 4SO'),
    ('/lich-su-doi-chieu/', 'Lịch sử đối chiếu'),
    ('/mau-bao-cao.html', 'Báo cáo mẫu'),
    ('/gioi-thieu/', 'Giới thiệu'),
    ('/legal.html', 'Điều khoản & bảo mật'),
]

TARGETS = {
    'cho-so-mien-bac-hom-nay/index.html',
    'phuong-phap-4so/index.html',
    'lich-su-doi-chieu/index.html',
    'thong-ke-lo-to-mien-bac-bang-ai/index.html',
    'gioi-thieu/index.html',
    'thong-ke-xsmb/index.html',
    'tan-suat-xsmb/index.html',
    'lo-gan-xsmb/index.html',
    'cap-dao-xsmb/index.html',
    'tra-cuu-xsmb/index.html',
    'mau-bao-cao.html',
    'legal.html',
    '404.html',
}


def route_for(rel: str) -> str:
    if rel.endswith('/index.html'):
        return '/' + rel[:-10]
    if rel == '404.html':
        return '/404.html'
    return '/' + rel


def nav_html(route: str) -> str:
    out = []
    for href, label in NAV:
        active = ' is-active' if route == href else ''
        out.append(f'<a class="{active.strip()}" href="{href}">{label}</a>')
    return ''.join(out)


def header(route: str) -> str:
    return f'''<header class="portal-site-header" data-portal-shell="v1">
  <div class="portal-site-head">
    <a class="portal-site-brand" href="/" aria-label="Lê Miền Bắc - Trang chủ"><span class="portal-site-brand-mark">LM</span><span><strong>LÊ MIỀN BẮC</strong><small>DỮ LIỆU · THỐNG KÊ XSMB</small></span></a>
    <nav class="portal-site-nav" aria-label="Điều hướng chính">{nav_html(route)}</nav>
    <a class="portal-site-cta" href="/?checkout=1">Báo cáo 4SO</a>
  </div>
</header>
<div class="portal-contextbar"><div class="portal-contextbar-inner"><span>Công cụ thống kê miễn phí · dữ liệu khóa T−1</span><a href="/thong-ke-xsmb/">Mở trung tâm thống kê →</a></div></div>'''


def footer() -> str:
    links = ''.join(f'<a href="{href}">{label}</a>' for href, label in FOOT)
    return f'''<footer class="portal-site-footer" data-portal-shell-footer="v1">
  <div class="portal-site-footer-inner">
    <div><strong>LÊ MIỀN BẮC</strong><p>Cổng dữ liệu và thống kê XSMB. Các bảng công khai mô tả dữ liệu đã công bố; không phải cam kết kết quả. Đầu ra 4SO hiện tại không được công khai trên các trang thống kê.</p></div>
    <nav class="portal-site-footer-nav" aria-label="Liên kết cuối trang">{links}</nav>
  </div>
  <div class="portal-site-footer-bottom">© 2026 Lê Miền Bắc · Dữ liệu công khai, thống kê mô tả và báo cáo AI.</div>
</footer>'''


def add_body_class(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        attrs = m.group(1) or ''
        cm = re.search(r'\bclass="([^"]*)"', attrs, re.I)
        if cm:
            classes = cm.group(1).split()
            if 'portal-subpage' not in classes:
                classes.append('portal-subpage')
            attrs = attrs[:cm.start(1)] + ' '.join(classes) + attrs[cm.end(1):]
        else:
            attrs += ' class="portal-subpage"'
        return '<body' + attrs + '>'
    return re.sub(r'<body([^>]*)>', repl, text, count=1, flags=re.I)


def replace_first_tag(text: str, tag: str, replacement: str) -> str:
    pattern = re.compile(rf'<{tag}\b[^>]*>.*?</{tag}>', re.I | re.S)
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    if tag == 'header':
        return text.replace('<body', '<body', 1).replace('>', '>' + replacement, 1)
    return text.replace('</body>', replacement + '</body>', 1)


def apply_page(path: Path, root: Path) -> None:
    rel = path.relative_to(root).as_posix()
    route = route_for(rel)
    text = path.read_text(encoding='utf-8')
    if 'portal-subpages.css' not in text:
        text = text.replace('</head>', '<link rel="stylesheet" href="/portal-subpages.css?v=20260815-1"></head>', 1)
    text = re.sub(r'<meta name="theme-color" content="[^"]*"\s*/?>', '<meta name="theme-color" content="#b3161b">', text, count=1, flags=re.I)
    text = add_body_class(text)
    text = replace_first_tag(text, 'header', header(route))
    text = replace_first_tag(text, 'footer', footer())
    if 'data-portal-shell="v1"' not in text or 'portal-site-footer' not in text:
        raise ValueError(f'Portal shell missing: {rel}')
    path.write_text(text, encoding='utf-8')


def apply(root: Path) -> dict[str, int]:
    changed = 0
    for rel in sorted(TARGETS):
        path = root / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        apply_page(path, root)
        changed += 1
    return {'pages': changed}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for rel in TARGETS:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('<!doctype html><html><head><meta name="theme-color" content="#000"></head><body class="x"><header class="old">old</header><main><h1>Test</h1></main><footer>old</footer></body></html>', encoding='utf-8')
        result = apply(root)
        assert result['pages'] == len(TARGETS)
        sample = (root / 'thong-ke-xsmb/index.html').read_text(encoding='utf-8')
        assert 'portal-subpage' in sample and 'portal-subpages.css' in sample
        assert 'portal-site-header' in sample and 'portal-site-footer' in sample
        assert '/thong-ke-dau-duoi-xsmb/' in sample and '/phuong-phap-cong-khai/' in sample
        assert 'is-active' in sample
    print('PORTAL_SUBPAGES_SELF_TEST_OK')


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--output-root', type=Path, default=ROOT / '_site')
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        self_test()
    else:
        print(apply(a.output_root))


if __name__ == '__main__':
    main()
