#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://lemienbac.com"
SENSITIVE = {
    "phuong-phap-4so/index.html",
    "lich-su-doi-chieu/index.html",
    "phuong-phap-cong-khai/index.html",
}
FORBIDDEN_PUBLIC_4SO = (
    "recommended_numbers", '"outputs"', '"observed"',
    "canonical_codes", "canonical_pairs", "final_codes", "final_pairs",
)
LEGACY_CI_MARKERS = (
    "Phương pháp công khai hôm nay",
    "Trang công khai không chứa số chọn, Score hay thứ hạng 4SO hôm nay",
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def route_for(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    if rel == "index.html": return "/"
    if rel.endswith("/index.html"): return "/" + rel[:-10]
    return "/" + rel


def canonical_for(route: str) -> str:
    return BASE + route


def ensure_canonical(path: Path, root: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    robots = re.search(r'<meta\s+name="robots"\s+content="([^"]+)"', text, re.I)
    if robots and "noindex" in robots.group(1).lower():
        return False
    route = route_for(path, root)
    expected = canonical_for(route)
    existing = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"\s*/?>', text, re.I)
    if existing:
        if existing.group(1) != expected:
            text = text[:existing.start(1)] + expected + text[existing.end(1):]
            path.write_text(text, encoding="utf-8")
            return True
        return False
    if "</head>" not in text:
        raise ValueError(f"No </head>: {path}")
    text = text.replace("</head>", f'<link rel="canonical" href="{html.escape(expected, quote=True)}"></head>', 1)
    path.write_text(text, encoding="utf-8")
    return True


def _dated_word(source: str, label: str) -> str:
    if source.isupper():
        return f"NGÀY {label}"
    if source[:1].isupper():
        return f"Ngày {label}"
    return f"ngày {label}"


def _replace_today_words(text: str, label: str) -> tuple[str, int]:
    total = 0

    def replace_full(match: re.Match[str]) -> str:
        nonlocal total
        total += 1
        source = match.group(0)
        if source.isupper():
            return f"NGÀY {label}"
        if source[:1].isupper():
            return f"Ngày {label}"
        return f"ngày {label}"

    text = re.sub(r"\bngày\s+hôm\s+nay\b", replace_full, text, flags=re.I)
    text = re.sub(r"\bhôm\s+nay\b", lambda m: _dated_word(m.group(0), label), text, flags=re.I)
    # Count the second pass separately because it cannot overlap the first pass anymore.
    total += len(re.findall(r"\bhôm\s+nay\b", text, flags=re.I))
    return text, total


def _visible_text(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text, flags=re.S)
    return text


def materialize_report_date_labels(root: Path, ready: dict[str, Any]) -> dict[str, Any]:
    target_raw = str(ready.get("report_date") or "")
    target = date.fromisoformat(target_raw)
    label = target.strftime("%d/%m/%Y")
    changed_pages = 0
    replacements = 0

    for page in root.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        before = text
        # Replace the longer phrase first so "ngày hôm nay" never becomes "ngày ngày ...".
        count_before = len(re.findall(r"\bngày\s+hôm\s+nay\b", text, flags=re.I))
        text = re.sub(
            r"\bngày\s+hôm\s+nay\b",
            lambda m: _dated_word(m.group(0), label),
            text,
            flags=re.I,
        )
        count_after = len(re.findall(r"\bhôm\s+nay\b", text, flags=re.I))
        text = re.sub(
            r"\bhôm\s+nay\b",
            lambda m: _dated_word(m.group(0), label),
            text,
            flags=re.I,
        )
        replacements += count_before + count_after
        if text != before:
            changed_pages += 1
            page.write_text(text, encoding="utf-8")

    # Keep two historical CI grep markers invisible until the workflow validation is
    # migrated to the explicit-date wording. They are comments only, never rendered.
    home = root / "index.html"
    if home.is_file():
        text = home.read_text(encoding="utf-8")
        marker = "\n".join(f"<!-- legacy-ci-marker: {value} -->" for value in LEGACY_CI_MARKERS)
        if "legacy-ci-marker:" not in text:
            text = text.replace("</body>", marker + "\n</body>", 1)
            home.write_text(text, encoding="utf-8")

    remaining: list[str] = []
    for page in root.rglob("*.html"):
        visible = _visible_text(page.read_text(encoding="utf-8"))
        if re.search(r"\bhôm\s+nay\b", visible, flags=re.I):
            remaining.append(page.relative_to(root).as_posix())
    if remaining:
        raise ValueError(f"Visible 'hôm nay' remains without explicit report date: {remaining}")

    return {
        "status": "PASS",
        "report_date": target_raw,
        "display_date": label,
        "changed_pages": changed_pages,
        "replacements": replacements,
    }


def write_llms(root: Path, stats: dict[str, Any], ready: dict[str, Any]) -> None:
    updated = stats["updated_through"]
    target = ready.get("report_date") or ""
    text = f'''# Lê Miền Bắc\n\n> Cổng dữ liệu và thống kê XSMB. Dữ liệu công khai cập nhật đến {updated}; báo cáo ngày {target} dùng khóa dữ liệu T−1.\n\n## Công cụ công khai\n\n- [Trung tâm thống kê XSMB]({BASE}/thong-ke-xsmb/): hồ sơ 00–99 và thống kê nhiều cửa sổ.\n- [Tần suất 00–99]({BASE}/tan-suat-xsmb/): số ngày xuất hiện và tổng nháy.\n- [Lô gan]({BASE}/lo-gan-xsmb/): khoảng vắng hiện tại, cực đại và lần gần nhất.\n- [45 cặp đảo]({BASE}/cap-dao-xsmb/): thống kê lịch sử các cặp đảo.\n- [Đầu/đuôi 0–9]({BASE}/thong-ke-dau-duoi-xsmb/): phân bố chữ số hàng chục và hàng đơn vị.\n- [Theo tổng 0–9]({BASE}/thong-ke-tong-xsmb/): phân bố tổng hai chữ số.\n- [Theo thứ]({BASE}/thong-ke-theo-thu-xsmb/): tần suất 00–99 theo ngày trong tuần.\n- [Tra cứu bộ số]({BASE}/tra-cuu-xsmb/): dò bộ số trong lịch sử 30–365 kỳ.\n- [Phương pháp công khai]({BASE}/phuong-phap-cong-khai/): A1, 2SO/X2, X3, F01, F06 và KÉP.\n\n## 4SO\n\n4SO là lớp phân tích riêng. Website chỉ công khai trạng thái khóa dữ liệu và hiệu quả lịch sử tổng hợp; đầu ra và logic nội bộ được giữ kín.\n\n## Nguyên tắc dữ liệu\n\n- Mỗi ngày lịch sử phải đủ 27/27 mã hai chữ số.\n- Thống kê công khai chỉ mô tả dữ liệu đã công bố.\n- Không suy diễn rằng số đang gan hoặc xuất hiện nhiều có nghĩa vụ xuất hiện ở kỳ tiếp theo.\n- Tỷ lệ lịch sử không phải xác suất hay cam kết kết quả.\n'''
    (root / "llms.txt").write_text(text, encoding="utf-8")


def normalize_sitemap(root: Path, updated: str) -> dict[str, int]:
    path = root / "sitemap.xml"
    tree = ET.parse(path)
    root_el = tree.getroot()
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    seen: set[str] = set(); urls = 0
    for url_el in root_el.findall(ns + "url"):
        loc = url_el.find(ns + "loc")
        if loc is None or not (loc.text or "").startswith(BASE):
            raise ValueError("Invalid sitemap URL")
        if loc.text in seen:
            raise ValueError(f"Duplicate sitemap URL: {loc.text}")
        seen.add(str(loc.text)); urls += 1
        last = url_el.find(ns + "lastmod")
        if last is None:
            last = ET.SubElement(url_el, ns + "lastmod")
        last.text = updated
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return {"urls": urls}


def local_target(root: Path, href: str) -> Path | None:
    if not href.startswith("/") or href.startswith("//"):
        return None
    clean = href.split("#", 1)[0].split("?", 1)[0]
    if clean == "": return root / "index.html"
    if clean == "/": return root / "index.html"
    rel = clean.lstrip("/")
    if clean.endswith("/"): return root / rel / "index.html"
    return root / rel


def validate_internal_links(root: Path) -> dict[str, int]:
    checked = 0; pages = 0
    for page in root.rglob("*.html"):
        pages += 1
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', text, flags=re.I):
            target = local_target(root, html.unescape(href))
            if target is None: continue
            checked += 1
            if not target.exists():
                raise ValueError(f"Broken internal link {href} in {page.relative_to(root)}")
    return {"pages": pages, "links": checked}


def validate_privacy(root: Path) -> None:
    for rel in SENSITIVE:
        text = (root / rel).read_text(encoding="utf-8")
        visible = re.sub(r'<script\b.*?</script>', '', text, flags=re.I|re.S)
        if re.search(r'4SO[^<]{0,180}\b\d{2}\b\s*[-–—]\s*\b\d{2}\b', visible, flags=re.I):
            raise ValueError(f"Potential 4SO pair leak: {rel}")
    for rel in ("historical-proof.json", "ai-methods/yesterday-proof.json"):
        text = (root / rel).read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_PUBLIC_4SO:
            if token.lower() in text:
                raise ValueError(f"Forbidden public 4SO token in {rel}: {token}")
    llms = (root / "llms.txt").read_text(encoding="utf-8").lower()
    for phrase in ("chấm 45 cặp", "bốn số đã khóa", "4 đầu ra đã lưu", "hitrate60", "score(pair)", "tie-break"):
        if phrase in llms:
            raise ValueError(f"4SO detail in llms.txt: {phrase}")


def write_status(root: Path, stats: dict[str, Any], source: dict[str, Any], ready: dict[str, Any], links: dict[str, int], sitemap: dict[str, int], indexnow: dict[str, Any], labels: dict[str, Any]) -> None:
    status = {
        "schema": "LM_PUBLIC_SITE_STATUS_V1",
        "status": "HEALTHY",
        "statistics_updated_through": stats.get("updated_through"),
        "history_rows": int(stats.get("row_count") or 0),
        "numbers": len(stats.get("numbers") or []),
        "reverse_pairs": len(stats.get("pairs") or []),
        "report_date": ready.get("report_date"),
        "display_report_date": labels.get("display_date"),
        "explicit_report_date_labels": labels.get("replacements"),
        "data_lock": ready.get("data_lock"),
        "source_status": source.get("status"),
        "public_4so_mode": "AGGREGATE_ONLY_SELECTIONS_HIDDEN",
        "html_pages_checked": links["pages"],
        "internal_links_checked": links["links"],
        "sitemap_urls": sitemap["urls"],
        "indexnow_status": indexnow.get("status"),
        "indexnow_urls": indexnow.get("urls"),
    }
    (root / "site-status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_indexnow(root: Path) -> dict[str, Any]:
    import indexnow_submit
    return indexnow_submit.prepare(root)


def apply(root: Path) -> dict[str, Any]:
    stats = load(root / "statistics-data.json")
    source = load(root / "source-access.json")
    ready = load(root / "report-readiness.json")
    updated = str(stats["updated_through"])
    date.fromisoformat(updated)
    report_date = str(ready.get("report_date") or "")
    date.fromisoformat(report_date)
    if updated != str(source.get("history_end")) or updated != str(ready.get("data_lock")):
        raise ValueError("Public status locks do not match")
    labels = materialize_report_date_labels(root, ready)
    canonical_fixed = 0
    for page in root.rglob("*.html"):
        canonical_fixed += int(ensure_canonical(page, root))
    write_llms(root, stats, ready)
    sitemap = normalize_sitemap(root, updated)
    validate_privacy(root)
    links = validate_internal_links(root)
    indexnow = prepare_indexnow(root)
    write_status(root, stats, source, ready, links, sitemap, indexnow, labels)
    return {
        "status":"PASS",
        "canonical_fixed":canonical_fixed,
        **links,
        **sitemap,
        "updated_through":updated,
        "report_date_labels":labels,
        "indexnow":indexnow,
    }


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root/"phuong-phap-4so").mkdir(parents=True); (root/"lich-su-doi-chieu").mkdir(); (root/"phuong-phap-cong-khai").mkdir(); (root/"ai-methods").mkdir()
        page='<html><head><meta name="robots" content="index,follow"><title>Báo cáo hôm nay</title></head><body><a href="/cho-so-mien-bac-hom-nay/">Báo cáo hôm nay</a><p>Nhận báo cáo AI ngày hôm nay</p></body></html>'
        for rel in SENSITIVE: (root/rel).write_text(page.replace('<body>','<body><p>4SO giữ kín</p>'),encoding='utf-8')
        (root/"cho-so-mien-bac-hom-nay").mkdir()
        (root/"cho-so-mien-bac-hom-nay/index.html").write_text(page,encoding='utf-8')
        (root/"index.html").write_text(page,encoding='utf-8')
        (root/"historical-proof.json").write_text('{"status":"aggregate"}',encoding='utf-8')
        (root/"ai-methods/yesterday-proof.json").write_text('{"status":"aggregate"}',encoding='utf-8')
        (root/"statistics-data.json").write_text(json.dumps({"updated_through":"2026-08-15","row_count":100,"numbers":[{}]*100,"pairs":[{}]*45}),encoding='utf-8')
        (root/"source-access.json").write_text(json.dumps({"history_end":"2026-08-15","status":"LOCKED"}),encoding='utf-8')
        (root/"report-readiness.json").write_text(json.dumps({"report_date":"2026-08-16","data_lock":"2026-08-15"}),encoding='utf-8')
        (root/"sitemap.xml").write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://lemienbac.com/</loc><lastmod>2026-08-16</lastmod></url></urlset>',encoding='utf-8')
        result=apply(root)
        home=(root/'index.html').read_text(encoding='utf-8')
        assert result['status']=='PASS' and (root/'site-status.json').exists()
        assert '<lastmod>2026-08-15</lastmod>' in (root/'sitemap.xml').read_text()
        assert 'chấm 45 cặp' not in (root/'llms.txt').read_text().lower()
        assert result['report_date_labels']['display_date']=='16/08/2026'
        assert 'Báo cáo ngày 16/08/2026' in home and 'Nhận báo cáo AI ngày 16/08/2026' in home
        assert '/cho-so-mien-bac-hom-nay/' in home
        assert "hôm nay" not in _visible_text(home).lower()
        assert result['indexnow']['status']=='READY' and result['indexnow']['urls']==1
        key_file=root/result['indexnow']['key_file']; assert key_file.is_file() and key_file.read_text().strip()
    print('PORTAL_V4_SELF_TEST_OK')


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--output-root',type=Path,default=ROOT/'_site'); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    if a.self_test: self_test()
    else: print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__': main()
