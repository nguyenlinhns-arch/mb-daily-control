#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r'<link\b[^>]*>', re.I)
ATTR_RE = re.compile(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2', re.I | re.S)
VERSION = '20260815-4'


def attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(3) for m in ATTR_RE.finditer(tag)}


def local_css_path(root: Path, href: str) -> Path | None:
    clean = href.split('?', 1)[0].split('#', 1)[0]
    if clean.startswith('http://') or clean.startswith('https://') or clean.startswith('//') or clean.startswith('data:'):
        return None
    if not (clean.startswith('/') or clean.startswith('./') or clean.endswith('.css')):
        return None
    rel = clean.lstrip('/').removeprefix('./')
    path = root / rel
    return path if path.is_file() else None


def bundle_for(root: Path, hrefs: list[str], cache: dict[tuple[str, ...], str]) -> str:
    normalized = tuple(h.split('?', 1)[0].split('#', 1)[0] for h in hrefs)
    if normalized in cache:
        return cache[normalized]
    chunks: list[str] = []
    for href in hrefs:
        path = local_css_path(root, href)
        if path is None:
            raise ValueError(f'Missing local CSS: {href}')
        chunks.append(path.read_text(encoding='utf-8').strip())
    content = '\n'.join(chunks) + '\n'
    digest = hashlib.sha256(("\n".join(normalized) + "\n" + content).encode('utf-8')).hexdigest()[:12]
    name = f'portal-css-{digest}.css'
    (root / name).write_text(content, encoding='utf-8')
    cache[normalized] = name
    return name


def process_page(path: Path, root: Path, cache: dict[tuple[str, ...], str]) -> tuple[bool, int, int]:
    text = path.read_text(encoding='utf-8')
    matches: list[tuple[re.Match[str], str]] = []
    for match in LINK_RE.finditer(text):
        a = attrs(match.group(0))
        rel = a.get('rel', '').lower().split()
        href = a.get('href', '')
        if 'stylesheet' in rel and local_css_path(root, href) is not None:
            matches.append((match, href))
    before = len(matches)
    if before <= 1:
        return False, before, before
    name = bundle_for(root, [href for _, href in matches], cache)
    replacement = f'<link rel="stylesheet" href="/{name}?v={VERSION}">'
    parts: list[str] = []
    cursor = 0
    for idx, (match, _) in enumerate(matches):
        parts.append(text[cursor:match.start()])
        if idx == 0:
            parts.append(replacement)
        cursor = match.end()
    parts.append(text[cursor:])
    updated = ''.join(parts)
    path.write_text(updated, encoding='utf-8')
    return True, before, 1


def validate(root: Path) -> dict[str, int]:
    pages = 0
    max_local_css = 0
    for path in root.rglob('*.html'):
        pages += 1
        text = path.read_text(encoding='utf-8')
        local = 0
        for tag in LINK_RE.findall(text):
            a = attrs(tag)
            if 'stylesheet' in a.get('rel', '').lower().split() and local_css_path(root, a.get('href', '')) is not None:
                local += 1
        max_local_css = max(max_local_css, local)
        if local > 1:
            raise ValueError(f'More than one local stylesheet remains: {path.relative_to(root)} ({local})')
    return {'pages': pages, 'max_local_stylesheets': max_local_css}


def apply(root: Path) -> dict[str, Any]:
    cache: dict[tuple[str, ...], str] = {}
    pages = changed = requests_before = requests_after = 0
    for path in root.rglob('*.html'):
        pages += 1
        did, before, after = process_page(path, root, cache)
        changed += int(did)
        requests_before += before
        requests_after += after
    check = validate(root)
    return {
        'status': 'PASS',
        'pages': pages,
        'pages_bundled': changed,
        'bundles': len(cache),
        'css_requests_before': requests_before,
        'css_requests_after': requests_after,
        **check,
    }


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / 'a.css').write_text('body{color:#111}', encoding='utf-8')
        (root / 'b.css').write_text('a{color:#222}', encoding='utf-8')
        (root / 'index.html').write_text('<html><head><link rel="stylesheet" href="/a.css?v=1"><link href="/b.css" rel="stylesheet"></head><body></body></html>', encoding='utf-8')
        result = apply(root)
        text = (root / 'index.html').read_text(encoding='utf-8')
        assert result['pages_bundled'] == 1 and result['css_requests_before'] == 2 and result['css_requests_after'] == 1
        assert text.count('rel="stylesheet"') == 1 and 'portal-css-' in text
        assert len(list(root.glob('portal-css-*.css'))) == 1
    print('PORTAL_CSS_BUNDLE_SELF_TEST_OK')


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--output-root', type=Path, default=ROOT / '_site')
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        self_test()
    else:
        print(json.dumps(apply(a.output_root), ensure_ascii=False))


if __name__ == '__main__':
    main()
