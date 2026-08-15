#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_RE = re.compile(r'<script\b[^>]*\bsrc=(["\'])(.*?)\1[^>]*>', re.I | re.S)


def asset_path(root: Path, src: str) -> Path | None:
    clean = html.unescape(src).split('#', 1)[0].split('?', 1)[0]
    if clean.startswith(('http://', 'https://', '//', 'data:')):
        return None
    rel = clean.lstrip('/').removeprefix('./')
    if not rel:
        return None
    path = root / rel
    return path if path.is_file() else None


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def replace_page(path: Path, root: Path, cache: dict[Path, str]) -> tuple[int, int]:
    text = path.read_text(encoding='utf-8')
    matches = list(SCRIPT_RE.finditer(text))
    if not matches:
        return 0, 0
    parts: list[str] = []
    cursor = 0
    changed = local = 0
    for match in matches:
        parts.append(text[cursor:match.start()])
        tag = match.group(0)
        src = match.group(2)
        target = asset_path(root, src)
        if target is None:
            parts.append(tag)
            cursor = match.end()
            continue
        local += 1
        digest = cache.setdefault(target, fingerprint(target))
        base = html.unescape(src).split('#', 1)[0].split('?', 1)[0]
        new_src = f'{base}?v={digest}'
        if new_src != src:
            source_manifest = f'<!-- asset-source: {src.replace("--", "—")} -->'
            new_tag = tag[:match.group(0).find(src)] + new_src + tag[match.group(0).find(src)+len(src):]
            parts.append(source_manifest + new_tag)
            changed += 1
        else:
            parts.append(tag)
        cursor = match.end()
    parts.append(text[cursor:])
    if changed:
        path.write_text(''.join(parts), encoding='utf-8')
    return local, changed


def validate(root: Path) -> dict[str, int]:
    refs = 0
    assets: set[str] = set()
    for page in root.rglob('*.html'):
        text = page.read_text(encoding='utf-8')
        for match in SCRIPT_RE.finditer(text):
            src = match.group(2)
            target = asset_path(root, src)
            if target is None:
                continue
            refs += 1
            assets.add(target.relative_to(root).as_posix())
            q = re.search(r'[?&]v=([a-f0-9]{12})(?:&|$)', src)
            if not q:
                raise ValueError(f'Unfingerprinted local JS in {page.relative_to(root)}: {src}')
            if q.group(1) != fingerprint(target):
                raise ValueError(f'Stale JS fingerprint in {page.relative_to(root)}: {src}')
    return {'local_script_refs': refs, 'fingerprinted_assets': len(assets)}


def apply(root: Path) -> dict[str, Any]:
    cache: dict[Path, str] = {}
    pages = refs = changed = 0
    for page in root.rglob('*.html'):
        pages += 1
        local, edits = replace_page(page, root, cache)
        refs += local
        changed += edits
    check = validate(root)
    manifest = {
        p.relative_to(root).as_posix(): digest
        for p, digest in sorted(cache.items(), key=lambda item: item[0].as_posix())
    }
    (root / 'asset-fingerprints.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'status': 'PASS', 'pages': pages, 'refs_seen': refs, 'refs_changed': changed, **check}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / 'a.js').write_text('console.log(1);', encoding='utf-8')
        p = root / 'index.html'
        p.write_text('<html><body><script defer src="/a.js?v=old"></script><script src="https://example.test/a.js"></script></body></html>', encoding='utf-8')
        result = apply(root)
        text = p.read_text(encoding='utf-8')
        digest = fingerprint(root / 'a.js')
        assert result['status'] == 'PASS' and result['fingerprinted_assets'] == 1
        assert f'/a.js?v={digest}' in text and '/a.js?v=old' in text and 'asset-source:' in text
        assert (root / 'asset-fingerprints.json').exists()
    print('PORTAL_ASSET_FINGERPRINT_SELF_TEST_OK')


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
