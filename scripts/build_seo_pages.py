#!/usr/bin/env python3
"""Build static, indexable SEO pages for the public 4SO AI website.

The current-day page is rendered from ``public-methods.json`` so crawlers can
read the same public recommendations that visitors see without executing
JavaScript.  The paid 4SO conclusion is intentionally absent from every input
and output.  If the public payload is not scoped to the current Vietnam date
with a T-1 data lock, the page fails closed and publishes no method numbers.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_METHODS = ROOT / "ai-methods" / "public-methods.json"
YESTERDAY_PROOF = ROOT / "ai-methods" / "yesterday-proof.json"
LANDING_TEMPLATE = ROOT / "ai-methods" / "landing-v7.html"
SITE_V2_TEMPLATE = ROOT / "site-v2" / "index.html"
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
BASE_URL = "https://lemienbac.com"
SEARCH_CONSOLE_TOKEN = "YsFOP33bdoRwdFS2sVoqfnzoxmniLWHrJzxpSx2uDsA"
GA4_MEASUREMENT_ID = "G-R9TBYP97BC"
LOCKED_FIELD_PATTERN = re.compile(
    r"(?:final|canonical)[_-]?(?:codes|pairs)", re.IGNORECASE
)

NAV_LINKS = (
    ("/cho-so-mien-bac-hom-nay/", "Số hôm nay"),
    ("/phuong-phap-4so/", "Phương pháp 4SO"),
    ("/lich-su-doi-chieu/", "Lịch sử"),
    ("/thong-ke-lo-to-mien-bac-bang-ai/", "Thống kê AI"),
    ("/gioi-thieu/", "Giới thiệu"),
)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def display_day(value: str | date) -> str:
    parsed = date.fromisoformat(value) if isinstance(value, str) else value
    return parsed.strftime("%d/%m/%Y")


def compact_day(value: str | date) -> str:
    parsed = date.fromisoformat(value) if isinstance(value, str) else value
    return parsed.strftime("%d/%m")


def load_json(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if LOCKED_FIELD_PATTERN.search(raw):
        raise ValueError(f"LOCKED_4SO_FIELD_FOUND: {path}")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def validate_public_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != "MB_PUBLIC_METHOD_OUTPUTS_V2_TODAY_ONLY":
        raise ValueError("Invalid public method schema")
    if payload.get("recommendation_scope") != "TODAY_ONLY":
        raise ValueError("Public methods must be TODAY_ONLY")
    if payload.get("source_status") != "LOCKED_27_OF_27":
        raise ValueError("Public source is not locked 27/27")
    if payload.get("outcome_known_at_selection") is not False:
        raise ValueError("Public payload violates no-look-ahead")
    target = date.fromisoformat(str(payload.get("target_date")))
    lock = date.fromisoformat(str(payload.get("data_lock")))
    if target - lock != timedelta(days=1):
        raise ValueError("Public data lock must be exactly T-1")
    methods = payload.get("methods")
    if not isinstance(methods, list) or len(methods) < 4:
        raise ValueError("Public method list is incomplete")
    for method in methods:
        numbers = method.get("numbers") if isinstance(method, dict) else None
        if not method.get("name") or not isinstance(numbers, list) or not numbers:
            raise ValueError("Invalid public method row")
        if any(not re.fullmatch(r"\d{2}", str(number)) for number in numbers):
            raise ValueError(f"Invalid public number in {method.get('name')}")


def validate_proof_payload(proof: dict[str, Any]) -> None:
    if proof.get("schema_version") != "MB_PUBLIC_YESTERDAY_PROOF_V3_PRODUCTION_AWARE":
        raise ValueError("Invalid public proof schema")
    proof_day = date.fromisoformat(str(proof.get("date")))
    recommended = proof.get("recommended_numbers")
    if not isinstance(recommended, list) or len(recommended) not in (2, 4) or len(set(recommended)) != len(recommended):
        raise ValueError("Yesterday proof must contain the official Production output count")
    if any(not re.fullmatch(r"\d{2}", str(number)) for number in recommended):
        raise ValueError("Yesterday proof contains an invalid number")

    validation = proof.get("historical_validation") or {}
    window_start = date.fromisoformat(str(validation.get("window_start")))
    window_end = date.fromisoformat(str(validation.get("window_end")))
    total_days = int(validation.get("total_days") or 0)
    hit_days = int(validation.get("hit_days") or 0)
    if (window_end - window_start).days + 1 != total_days or window_end > proof_day:
        raise ValueError("Historical validation window is incomplete")
    if int(validation.get("rate_pct") or -1) != round(hit_days * 100 / total_days):
        raise ValueError("Historical validation rate is inconsistent")

    month = proof.get("month_summary") or {}
    records = month.get("daily_records")
    observed = int(month.get("observed_days") or 0)
    if not isinstance(records, list) or len(records) != observed:
        raise ValueError("Month history must contain one record per observed day")
    expected_start = date.fromisoformat(str(month.get("period_start")))
    expected_end = date.fromisoformat(str(month.get("period_end")))
    if expected_end != proof_day or (expected_end - expected_start).days + 1 != observed:
        raise ValueError("Month history dates are not continuous")
    transition = proof.get("production_transition") or {}
    max2_live_from = date.fromisoformat(str(transition.get("max2_live_from") or "9999-12-31"))
    wins = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("Invalid month history record")
        record_day = date.fromisoformat(str(record.get("date")))
        if record_day != expected_start + timedelta(days=index):
            raise ValueError("Month history is not ordered or continuous")
        picks = record.get("recommended_numbers")
        hits = record.get("hits")
        expected_count = 2 if record_day >= max2_live_from else 4
        if not isinstance(picks, list) or len(picks) != expected_count or len(set(picks)) != expected_count:
            raise ValueError(f"Invalid Production record for {record_day}")
        if any(not re.fullmatch(r"\d{2}", str(number)) for number in picks):
            raise ValueError(f"Invalid number in history for {record_day}")
        if not isinstance(hits, list):
            raise ValueError(f"Invalid hits for {record_day}")
        status = "hit" if hits else "miss"
        if record.get("status") != status:
            raise ValueError(f"History status mismatch for {record_day}")
        record_hash = str(record.get("record_hash") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", record_hash):
            raise ValueError(f"Missing record hash for {record_day}")
        canonical_record = {key: value for key, value in record.items() if key != "record_hash"}
        expected_hash = hashlib.sha256(json.dumps(canonical_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if record_hash != expected_hash:
            raise ValueError(f"Record hash mismatch for {record_day}")
        wins += bool(hits)
    if wins != int(month.get("win_days") or -1):
        raise ValueError("Month win count is inconsistent")
    if observed - wins != int(month.get("miss_days") or -1):
        raise ValueError("Month miss count is inconsistent")

def breadcrumb_schema(items: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": label,
                "item": f"{BASE_URL}{path}",
            }
            for index, (path, label) in enumerate(items, start=1)
        ],
    }


def web_page_schema(
    *,
    title: str,
    description: str,
    canonical_path: str,
    breadcrumbs: list[tuple[str, str]],
    modified: str | None = None,
    paywalled: bool = False,
) -> dict[str, Any]:
    canonical = f"{BASE_URL}{canonical_path}"
    page: dict[str, Any] = {
        "@type": "WebPage",
        "@id": f"{canonical}#webpage",
        "url": canonical,
        "name": title,
        "description": description,
        "inLanguage": "vi-VN",
        "isPartOf": {"@id": f"{BASE_URL}/#website"},
        "breadcrumb": {"@id": f"{canonical}#breadcrumb"},
        "primaryImageOfPage": {"@id": f"{BASE_URL}/ai-methods/og-4so-ai-v2.jpg"},
    }
    if modified:
        page["dateModified"] = modified
    if paywalled:
        page.update(
            {
                "isAccessibleForFree": False,
                "hasPart": {
                    "@type": "WebPageElement",
                    "isAccessibleForFree": False,
                    "cssSelector": ".paywall",
                },
            }
        )
    breadcrumb = breadcrumb_schema(breadcrumbs)
    breadcrumb["@id"] = f"{canonical}#breadcrumb"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{BASE_URL}/#organization",
                "name": "4SO AI",
                "url": f"{BASE_URL}/",
                "logo": f"{BASE_URL}/favicon.svg",
                "contactPoint": {
                    "@type": "ContactPoint",
                    "contactType": "customer support",
                    "url": "https://zalo.me/0398696879",
                    "availableLanguage": "Vietnamese",
                },
            },
            {
                "@type": "WebSite",
                "@id": f"{BASE_URL}/#website",
                "url": f"{BASE_URL}/",
                "name": "4SO AI",
                "description": "Phân tích dữ liệu Lô tô Miền Bắc bằng AI theo ngày.",
                "inLanguage": "vi-VN",
                "publisher": {"@id": f"{BASE_URL}/#organization"},
            },
            page,
            breadcrumb,
        ],
    }


def breadcrumb_html(items: list[tuple[str, str]]) -> str:
    links = []
    for index, (path, label) in enumerate(items):
        if index == len(items) - 1:
            links.append(f'<span aria-current="page">{esc(label)}</span>')
        else:
            links.append(f'<a href="{esc(path)}">{esc(label)}</a>')
    return '<span aria-hidden="true">›</span>'.join(links)


def nav_html() -> str:
    return "".join(
        f'<a href="{esc(path)}">{esc(label)}</a>' for path, label in NAV_LINKS
    )


def shell(
    *,
    title: str,
    description: str,
    canonical_path: str,
    breadcrumbs: list[tuple[str, str]],
    body: str,
    schema: dict[str, Any],
    target_date: str = "",
) -> str:
    canonical = f"{BASE_URL}{canonical_path}"
    target_attribute = f' data-target-date="{esc(target_date)}"' if target_date else ""
    structured = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html>
<html lang="vi"{target_attribute}>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1" />
  <meta name="google-site-verification" content="{SEARCH_CONSOLE_TOKEN}" />
  <meta name="theme-color" content="#071f33" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}" />
  <link rel="canonical" href="{esc(canonical)}" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <meta property="og:locale" content="vi_VN" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{esc(canonical)}" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(description)}" />
  <meta property="og:image" content="{BASE_URL}/ai-methods/og-4so-ai-v2.jpg" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="4SO AI phân tích dữ liệu Lô tô Miền Bắc" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="stylesheet" href="/ai-methods/seo.css?v=20260812-final" />
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{GA4_MEASUREMENT_ID}',{{allow_google_signals:false,allow_ad_personalization_signals:false}});</script>
  <script type="application/ld+json">{structured}</script>
</head>
<body>
  <a class="skip-link" href="#noi-dung">Đi đến nội dung chính</a>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="seo-brand" href="/" aria-label="4SO AI - Trang chủ"><b>4SO</b><span><strong>4SO AI</strong><small>Thống kê Lô tô Miền Bắc</small></span></a>
      <a class="top-cta" href="/#pricing"><span>Xem gói</span><span>mở kết luận</span></a>
    </div>
    <nav class="seo-nav" aria-label="Điều hướng nội dung">{nav_html()}</nav>
  </header>
  <main id="noi-dung">
    <div class="seo-wrap breadcrumbs" aria-label="Đường dẫn">{breadcrumb_html(breadcrumbs)}</div>
    {body}
  </main>
  <footer class="seo-footer">
    <div class="seo-wrap footer-grid">
      <div><strong>4SO AI</strong><p>Dịch vụ phân tích dữ liệu dành cho người đủ 18 tuổi. Không nhận cược, giữ tiền cược hoặc trả thưởng.</p></div>
      <nav aria-label="Liên kết cuối trang">{nav_html()}<a href="/legal.html">Điều khoản &amp; bảo mật</a></nav>
    </div>
  </footer>
  <script>
  (()=>{{
    const emit=(name,params={{}})=>{{try{{window.dataLayer=window.dataLayer||[];window.dataLayer.push({{event:name,page_path:location.pathname,...params}})}}catch{{}}}};
    document.querySelectorAll('.top-cta,.primary-cta').forEach(link=>link.addEventListener('click',()=>emit('seo_cta_click',{{destination:link.getAttribute('href')||''}})));
    document.querySelectorAll('details').forEach(item=>item.addEventListener('toggle',()=>{{if(item.open)emit('seo_faq_open',{{question:item.querySelector('summary')?.textContent||''}})}}));
    const target=document.documentElement.dataset.targetDate;
    if(!target)return;
    const parts=new Intl.DateTimeFormat('en-CA',{{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit'}}).formatToParts(new Date());
    const values=Object.fromEntries(parts.map(part=>[part.type,part.value]));
    const today=`${{values.year}}-${{values.month}}-${{values.day}}`;
    if(today!==target){{
      document.documentElement.classList.add('stale-day');
      const warning=document.querySelector('#stale-warning');
      if(warning)warning.hidden=false;
    }}
  }})();
  </script>
</body>
</html>
'''


def number_chips(numbers: list[Any], css_class: str = "number-chip") -> str:
    return "".join(
        f'<span class="{esc(css_class)}">{esc(number)}</span>' for number in numbers
    )


def method_rows(payload: dict[str, Any]) -> str:
    rows = []
    for method in payload.get("methods", []):
        rows.append(
            '<article class="method-item">'
            f'<h3>{esc(method["name"])}</h3>'
            f'<div class="method-numbers" aria-label="Số của {esc(method["name"])}">'
            f'{number_chips(method["numbers"])}</div></article>'
        )
    return "".join(rows)


def replace_marker_block(source: str, marker: str, replacement: str) -> str:
    pattern = re.compile(
        rf"(?P<start><!-- {re.escape(marker)}_START -->).*?(?P<end><!-- {re.escape(marker)}_END -->)",
        re.DOTALL,
    )
    updated, count = pattern.subn(
        lambda match: f'{match.group("start")}\n{replacement}\n{match.group("end")}',
        source,
    )
    if count != 1:
        raise ValueError(f"Landing marker {marker} must occur exactly once")
    return updated


def replace_element_text(source: str, element_id: str, value: str) -> str:
    pattern = re.compile(
        rf'(?P<open><(?P<tag>[a-z0-9]+)[^>]*\bid="{re.escape(element_id)}"[^>]*>).*?(?P<close></(?P=tag)>)',
        re.IGNORECASE | re.DOTALL,
    )
    updated, count = pattern.subn(
        lambda match: f'{match.group("open")}{esc(value)}{match.group("close")}',
        source,
    )
    if count != 1:
        raise ValueError(f"Landing element #{element_id} must occur exactly once")
    return updated


def replace_data_text(source: str, attribute: str, value: str) -> str:
    pattern = re.compile(
        rf'(?P<open><(?P<tag>strong|b)[^>]*\b{re.escape(attribute)}\b[^>]*>).*?(?P<close></(?P=tag)>)',
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub(
        lambda match: f'{match.group("open")}{esc(value)}{match.group("close")}',
        source,
    )


def landing_method_rows(payload: dict[str, Any]) -> str:
    rows = []
    for method in payload.get("methods", []):
        rows.append(
            '<div class="method-row">'
            f'<div class="method-label"><strong>{esc(method["name"])}</strong></div>'
            '<div class="method-result"><div class="number-list">'
            f'{number_chips(method["numbers"])}'
            '</div></div></div>'
        )
    return "\n".join(rows)


def landing_month_rows(proof: dict[str, Any]) -> str:
    rows = []
    for item in (proof.get("month_summary") or {}).get("winning_days") or []:
        hits = item.get("hits") or []
        hit_set = {str(hit.get("number")) for hit in hits}
        picks = "".join(
            f'<b class="{"is-hit" if str(number) in hit_set else ""}">{esc(number)}</b>'
            for number in item.get("recommended_numbers") or []
        )
        results = "".join(
            f'<span>{esc(hit.get("number"))}{f" × {int(hit.get("count"))}" if int(hit.get("count") or 0) > 1 else ""}</span>'
            for hit in hits
        )
        rows.append(
            f'<div class="win-row" role="row"><time datetime="{esc(item.get("date"))}">{compact_day(str(item.get("date")))}</time>'
            f'<div class="win-picks">{picks}</div><strong class="win-result">{results}</strong></div>'
        )
    return "\n".join(rows)


def site_v2_history_block(proof: dict[str, Any], expected_lock: date) -> str:
    if proof.get("date") != expected_lock.isoformat():
        return f'''<section class="historical-proof-section" id="statistics">
      <div class="wrap historical-proof-shell"><div class="historical-proof-copy">
        <p class="eyebrow">THỐNG KÊ THEO NGÀY</p><h2>Đang cập nhật đối chiếu {display_day(expected_lock)}</h2>
        <p>Không dùng lại dữ liệu đối chiếu của ngày cũ dưới nhãn ngày mới.</p>
      </div></div>
    </section>'''
    validation = proof.get("historical_validation") or {}
    month = proof.get("month_summary") or {}
    rows = []
    for item in month.get("daily_records") or []:
        hit_map = {
            str(hit.get("number")): int(hit.get("count") or 0)
            for hit in item.get("hits") or []
        }
        picks = "".join(
            f'<b class="{"is-observed" if hit_map.get(str(number)) else ""}">{esc(number)}</b>'
            for number in item.get("recommended_numbers") or []
        )
        observed = "".join(
            f'<span>{esc(number)}{f" × {count}" if count > 1 else ""}</span>'
            for number, count in hit_map.items()
        ) or '<span class="history-miss">Không xuất hiện</span>'
        rows.append(
            f'<div class="history-day-row" role="row"><time datetime="{esc(item.get("date"))}">'
            f'{display_day(str(item.get("date")))}</time><div class="history-outputs">{picks}</div>'
            f'<strong class="history-observed {"has-observed" if hit_map else ""}">{observed}</strong></div>'
        )
    return f'''<section class="historical-proof-section" id="statistics">
      <div class="wrap historical-proof-shell">
        <div class="historical-proof-summary">
          <div class="historical-rate"><p>CỬA SỔ KIỂM ĐỊNH 30 NGÀY</p><strong>{int(validation.get("rate_pct") or 0)}%</strong><span>{int(validation.get("hit_days") or 0)}/{int(validation.get("total_days") or 0)} ngày có ít nhất một đầu ra xuất hiện</span></div>
          <div class="historical-proof-copy"><p class="eyebrow">THỐNG KÊ THEO NGÀY</p><h2>Có cả ngày xuất hiện và không xuất hiện</h2><p>Bảng dưới hiển thị đủ {int(month.get("observed_days") or 0)} ngày đã hoàn tất từ {display_day(str(month.get("period_start")))}–{display_day(str(month.get("period_end")))}; không chỉ chọn các ngày thuận lợi.</p><div><strong>{int(month.get("win_days") or 0)}/{int(month.get("observed_days") or 0)} ngày</strong><span>trong giai đoạn gần nhất có đầu ra xuất hiện</span></div></div>
        </div>
        <div class="history-days" role="table" aria-label="Đối chiếu đầu ra theo từng ngày đã hoàn tất">
          <div class="history-day-head" role="row"><span>Ngày</span><span>4 đầu ra đã lưu</span><span>Đối chiếu thực tế</span></div>
          {"".join(rows)}
        </div>
        <p class="historical-disclaimer"><strong>Cách tính:</strong> Một ngày được ghi nhận khi có ít nhất một trong bốn đầu ra đã lưu xuất hiện trong 27 mã kết quả đã công bố. Tỷ lệ lịch sử không phải xác suất hoặc cam kết cho ngày tiếp theo. <a href="/ai-methods/yesterday-proof.json" target="_blank" rel="noopener">Hồ sơ thống kê</a>.</p>
      </div>
    </section>'''


def render_site_v2_landing(public: dict[str, Any], proof: dict[str, Any], today: date) -> str:
    source = SITE_V2_TEMPLATE.read_text(encoding="utf-8")
    expected_lock = today - timedelta(days=1)
    fresh = (
        public.get("target_date") == today.isoformat()
        and public.get("data_lock") == expected_lock.isoformat()
        and public.get("source_status") == "LOCKED_27_OF_27"
        and public.get("outcome_known_at_selection") is False
        and len(public.get("methods") or []) == 6
    )
    report_match = re.search(r'data-report-date="([^"]+)"', source)
    lock_match = re.search(r'data-lock-date="([^"]+)"', source)
    if not report_match or not lock_match:
        raise ValueError("site-v2 template is missing report date attributes")
    old_report, old_lock = report_match.group(1), lock_match.group(1)
    report_display, lock_display = display_day(today), display_day(expected_lock)
    source = source.replace(old_report, report_display).replace(old_lock, lock_display)
    source = re.sub(
        r'<body class="landing-simple" data-report-date="[^"]+" data-lock-date="[^"]+"(?: data-public-ready="[^"]+")?>',
        f'<body class="landing-simple" data-report-date="{report_display}" data-lock-date="{lock_display}" data-public-ready="{str(fresh).lower()}">',
        source,
        count=1,
    )
    source = re.sub(r"BÁO CÁO NGÀY \d{2}/\d{2}/\d{4}", f"BÁO CÁO NGÀY {report_display}", source)
    history = site_v2_history_block(proof, expected_lock)
    source = re.sub(
        r'<!-- COMPLETED_DRAW_REPORT:START -->.*?<!-- COMPLETED_DRAW_REPORT:END -->',
        f'<!-- COMPLETED_DRAW_REPORT:START -->\n{history}\n    <!-- COMPLETED_DRAW_REPORT:END -->',
        source,
        count=1,
        flags=re.DOTALL,
    )
    if fresh:
        methods = f'''<section class="public-methods-v2" data-current-methods>
      <div class="wrap"><div class="section-copy"><p class="eyebrow">SỐ CÔNG KHAI HÔM NAY</p><h2>Số theo từng phương pháp AI</h2><p>Mỗi hàng chỉ hiển thị tên phương pháp và số. Đây là đầu ra riêng lẻ, chưa phải kết luận 4SO trả phí.</p></div>
      <div class="public-method-grid">{method_rows(public)}</div></div>
    </section>'''
    else:
        methods = '''<section class="public-methods-v2"><div class="wrap"><div class="section-copy"><p class="eyebrow">SỐ CÔNG KHAI HÔM NAY</p><h2>Đang cập nhật dữ liệu hôm nay</h2></div><div class="public-method-pending">Không hiển thị lại dãy của ngày cũ và chưa mở thanh toán.</div></div></section>'''
        source = re.sub(r'(<button\b[^>]*\bdata-open-checkout\b)(?![^>]*\bdisabled\b)', r'\1 disabled', source)
    source = source.replace(
        '    <section class="buy-simple" id="buy">',
        f'    {methods}\n\n    <section class="buy-simple" id="buy">',
        1,
    )
    source = source.replace(
        '<nav><a href="/mau-bao-cao.html">Báo cáo mẫu</a><a href="/legal.html">Điều khoản</a></nav>',
        '<nav><a href="/cho-so-mien-bac-hom-nay/">Số hôm nay</a><a href="/phuong-phap-4so/">Phương pháp</a><a href="/lich-su-doi-chieu/">Lịch sử</a><a href="/thong-ke-lo-to-mien-bac-bang-ai/">Thống kê AI</a><a href="/gioi-thieu/">Giới thiệu</a><a href="/mau-bao-cao.html">Báo cáo mẫu</a><a href="/legal.html">Điều khoản</a></nav>',
        1,
    )
    if LOCKED_FIELD_PATTERN.search(source):
        raise ValueError("Paid 4SO field leaked into site-v2 landing")
    return source


def render_landing(public: dict[str, Any], proof: dict[str, Any], today: date) -> str:
    source = LANDING_TEMPLATE.read_text(encoding="utf-8")
    if LOCKED_FIELD_PATTERN.search(source):
        raise ValueError("Paid 4SO field leaked into landing template")
    expected_lock = today - timedelta(days=1)
    fresh = (
        public.get("target_date") == today.isoformat()
        and public.get("data_lock") == expected_lock.isoformat()
        and public.get("source_status") == "LOCKED_27_OF_27"
        and public.get("outcome_known_at_selection") is False
    )
    source = source.replace(
        '<html lang="vi">',
        f'<html lang="vi" data-static-date="{today.isoformat()}" data-static-fresh="{str(fresh).lower()}">',
    )
    source = replace_data_text(source, "data-date", display_day(today))
    source = replace_data_text(source, "data-lock", display_day(expected_lock))
    source = replace_element_text(
        source,
        "report-status",
        "ĐÃ HOÀN TẤT PHÂN TÍCH" if fresh else "ĐANG CẬP NHẬT DỮ LIỆU HÔM NAY",
    )
    methods = (
        landing_method_rows(public)
        if fresh
        else '<div class="method-loading method-loading-error">Số khuyến nghị hôm nay đang được cập nhật. Không hiển thị lại số của ngày cũ.</div>'
    )
    source = replace_marker_block(source, "METHOD_ROWS", methods)

    proof_fresh = proof.get("date") == expected_lock.isoformat()
    if proof_fresh:
        month = proof.get("month_summary") or {}
        validation = proof.get("historical_validation") or {}
        recommended = proof.get("recommended_numbers") or []
        hits = proof.get("hits") or []
        hit_map = {str(hit.get("number")): int(hit.get("count") or 0) for hit in hits}
        yesterday_numbers = "".join(
            f'<b class="{"hit" if hit_map.get(str(number)) else ""}{" multi-hit" if hit_map.get(str(number), 0) > 1 else ""}">{esc(number)}'
            f'{f"<small>×{hit_map[str(number)]}</small>" if hit_map.get(str(number), 0) > 1 else ""}</b>'
            for number in recommended
        )
        yesterday_results = "".join(
            f'<span>{esc(hit.get("number"))}{f" × {int(hit.get("count"))}" if int(hit.get("count") or 0) > 1 else ""}</span>'
            for hit in hits
        ) or "<span>0/4 số xuất hiện</span>"
        source = replace_marker_block(source, "MONTH_ROWS", landing_month_rows(proof))
        source = replace_marker_block(source, "YESTERDAY_NUMBERS", yesterday_numbers)
        source = replace_marker_block(source, "YESTERDAY_RESULTS", yesterday_results)
        source = replace_element_text(source, "month-label", f'ĐỐI CHIẾU THÁNG {str(month.get("month"))[5:7]}/{str(month.get("month"))[:4]}')
        source = replace_element_text(source, "month-win-score", f'{month.get("win_days")}/{month.get("observed_days")} ngày trúng')
        source = replace_element_text(source, "yesterday-date", display_day(str(proof.get("date"))))
        source = replace_element_text(source, "hit-summary", f'{proof.get("unique_hit_count")}/{proof.get("recommended_count")} số trúng · {proof.get("total_occurrences")} nháy')
        source = replace_element_text(source, "yesterday-result-summary", f'{proof.get("unique_hit_count")} trong {proof.get("recommended_count")} số khuyến nghị đã xuất hiện')
        source = replace_element_text(source, "validation-rate", f'{validation.get("rate_pct")}%')
        source = replace_element_text(source, "validation-window", f'{validation.get("hit_days")}/{validation.get("total_days")} ngày')
    else:
        source = replace_marker_block(
            source,
            "YESTERDAY_NUMBERS",
            '<span class="proof-pending">Đang cập nhật đối chiếu ngày mới</span>',
        )
        source = replace_marker_block(
            source,
            "YESTERDAY_RESULTS",
            "<span>Đang cập nhật</span>",
        )
        source = replace_element_text(source, "yesterday-date", display_day(expected_lock))
        source = replace_element_text(source, "hit-summary", "Đang cập nhật")
        source = replace_element_text(
            source,
            "yesterday-result-summary",
            "Chưa dùng lại kết quả đối chiếu của ngày cũ",
        )
    if LOCKED_FIELD_PATTERN.search(source):
        raise ValueError("Paid 4SO field leaked into rendered landing")
    return source


def today_page(
    public: dict[str, Any], proof: dict[str, Any], today: date
) -> tuple[str, str]:
    expected_lock = today - timedelta(days=1)
    fresh = (
        public.get("target_date") == today.isoformat()
        and public.get("data_lock") == expected_lock.isoformat()
        and public.get("source_status") == "LOCKED_27_OF_27"
        and public.get("outcome_known_at_selection") is False
    )
    shown_date = display_day(today)
    title = f"Cho số Miền Bắc hôm nay {shown_date} bằng AI | 4SO"
    description = (
        f"Cho số Miền Bắc hôm nay {shown_date} bằng AI từ dữ liệu khóa đến "
        f"{display_day(expected_lock)}: công khai số theo 6 phương pháp, khóa riêng kết luận 4SO."
        if fresh
        else f"Trang cho số Miền Bắc hôm nay {shown_date} đang kiểm tra dữ liệu T−1; số của ngày cũ không được hiển thị lại dưới ngày mới."
    )
    canonical_path = "/cho-so-mien-bac-hom-nay/"
    breadcrumbs = [("/", "Trang chủ"), (canonical_path, "Số Miền Bắc hôm nay")]
    generated = str(public.get("generated_at") or datetime.now(VN_TZ).isoformat()) if fresh else datetime.now(VN_TZ).isoformat(timespec="seconds")
    schema = web_page_schema(
        title=title,
        description=description,
        canonical_path=canonical_path,
        breadcrumbs=breadcrumbs,
        modified=generated,
        paywalled=fresh,
    )
    schema["@graph"].append(
        {
            "@type": "FAQPage",
            "@id": f"{BASE_URL}{canonical_path}#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": "Các số trên trang có phải kết luận 4SO không?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Không. Đây là đầu ra của từng phương pháp; kết luận 4SO là bước tổng hợp riêng gồm hai cặp đảo và bốn số.",
                    },
                },
                {
                    "@type": "Question",
                    "name": "Số hôm nay được tính từ dữ liệu nào?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Chỉ dùng kết quả đã công bố đến hết ngày hôm qua và phải đủ 27 trên 27 mã.",
                    },
                },
                {
                    "@type": "Question",
                    "name": "Tỷ lệ lịch sử có phải cam kết thắng không?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Không. Tỷ lệ lịch sử chỉ mô tả một cửa sổ dữ liệu đã kiểm định và không bảo đảm kết quả tương lai.",
                    },
                },
            ],
        }
    )
    method_content = (
        f'<div class="method-list" data-current-methods>{method_rows(public)}</div>'
        if fresh
        else '<div class="notice warning">Dữ liệu ngày mới đang được kiểm tra. Số của ngày cũ không được hiển thị lại.</div>'
    )
    historical = proof.get("historical_validation") or {}
    month = proof.get("month_summary") or {}
    rate = int(historical.get("rate_pct") or 0)
    hit_days = int(historical.get("hit_days") or 0)
    total_days = int(historical.get("total_days") or 0)
    month_hits = int(month.get("win_days") or 0)
    month_days = int(month.get("observed_days") or 0)
    status_label = "Đã cập nhật" if fresh else "Đang cập nhật"
    conclusion_card = (
        f'''<div class="paywall locked-card" data-nosnippet>
          <span class="lock-badge">ĐANG KHÓA</span>
          <div class="masked-pairs" aria-label="Hai cặp 4SO đang khóa"><b>•• — ••</b><b>•• — ••</b></div>
          <p>Thanh toán phí báo cáo để nhận đúng kết luận đã khóa của ngày {shown_date}.</p>
          <a class="primary-cta" href="/#pricing"><span>MỞ KẾT LUẬN</span><span>TỪ 30.000đ</span></a>
        </div>'''
        if fresh
        else '''<div class="locked-card unavailable-card">
          <span class="lock-badge">ĐANG CẬP NHẬT</span>
          <div class="masked-pairs" aria-label="Kết luận chưa sẵn sàng"><b>•• — ••</b><b>•• — ••</b></div>
          <p>Chưa mở thanh toán cho ngày mới cho đến khi dữ liệu T−1 đủ 27/27 và quá trình kiểm tra hoàn tất.</p>
          <span class="disabled-cta">CHƯA NHẬN THANH TOÁN</span>
        </div>'''
    )
    body = f'''
    <section class="seo-hero">
      <div class="seo-wrap hero-grid">
        <div>
          <p class="eyebrow">KHUYẾN NGHỊ THEO NGÀY · {esc(status_label)}</p>
          <h1><span class="phrase">Cho số Miền Bắc</span> <span class="phrase">hôm nay bằng AI</span></h1>
          <p class="hero-date">Ngày <time datetime="{today.isoformat()}">{shown_date}</time></p>
          <p class="lead">Dưới đây là các dãy số công khai do 6 phương pháp thống kê tạo ra từ dữ liệu XSMB đã công bố đến hết ngày hôm qua. Kết luận 4SO cuối cùng gồm đúng 2 cặp đảo và 4 số được tách riêng.</p>
        </div>
        <aside class="data-card" aria-label="Trạng thái dữ liệu">
          <span>Ngày phân tích</span><strong>{shown_date}</strong>
          <span>Khóa dữ liệu</span><strong>{display_day(expected_lock)}</strong>
          <span>Kiểm tra nguồn</span><strong>{'Đủ 27/27 mã' if fresh else 'Đang kiểm tra'}</strong>
        </aside>
      </div>
    </section>
    <section class="seo-section public-methods" aria-labelledby="public-methods-title">
      <div class="seo-wrap">
        <div class="section-heading"><p class="eyebrow">SỐ CÔNG KHAI HÔM NAY</p><h2 id="public-methods-title"><span class="phrase">Số theo từng</span> <span class="phrase">phương pháp AI</span></h2><p>Mỗi hàng chỉ hiển thị tên phương pháp và số. Đây là đầu ra riêng lẻ, chưa phải kết luận 4SO cuối cùng.</p></div>
        <div id="stale-warning" class="notice warning" hidden>Dữ liệu trên trang đã sang ngày mới. Hệ thống đang cập nhật và không tiếp tục dùng dãy của ngày trước.</div>
        {method_content}
      </div>
    </section>
    <section class="seo-section soft" aria-labelledby="locked-title">
      <div class="seo-wrap two-column">
        <div>
          <p class="eyebrow">BƯỚC TỔNG HỢP CUỐI</p>
          <h2 id="locked-title"><span class="phrase">Kết luận 4SO:</span> <span class="phrase">2 cặp đảo · 4 số</span></h2>
          <p>4SO chấm toàn bộ 45 cặp đảo hợp lệ, xếp hạng theo dữ liệu đến T−1 rồi khóa đúng hai cặp đứng đầu trước giờ có kết quả. Phần này không được đặt trong HTML hoặc JSON công khai.</p>
          <a class="text-link" href="/phuong-phap-4so/">Xem cách phương pháp 4SO hoạt động →</a>
        </div>
        {conclusion_card}
      </div>
    </section>
    <section class="seo-section" aria-labelledby="history-summary-title">
      <div class="seo-wrap">
        <div class="section-heading"><p class="eyebrow">ĐỐI CHIẾU CÔNG KHAI</p><h2 id="history-summary-title"><span class="phrase">Kết quả lịch sử</span> <span class="phrase">ghi cả ngày trúng</span> <span class="phrase">và chưa trúng</span></h2></div>
        <div class="metric-grid">
          <article><strong>{rate}%</strong><span>{hit_days}/{total_days} ngày trong cửa sổ kiểm định</span></article>
          <article><strong>{month_hits}/{month_days}</strong><span>ngày trúng trong tháng đang theo dõi</span></article>
          <article><strong>27/27</strong><span>mã kết quả được kiểm tra mỗi ngày</span></article>
        </div>
        <p class="fine-print">Tỷ lệ {rate}% là kết quả của một cửa sổ lịch sử {total_days} ngày đã đối chiếu, không phải xác suất bảo đảm và không cam kết kỳ tiếp theo.</p>
        <a class="text-link" href="/lich-su-doi-chieu/">Xem lịch sử đối chiếu theo ngày →</a>
      </div>
    </section>
    <section class="seo-section soft" aria-labelledby="faq-title">
      <div class="seo-wrap reading-width">
        <div class="section-heading"><p class="eyebrow">CÂU HỎI THƯỜNG GẶP</p><h2 id="faq-title"><span class="phrase">Hiểu đúng về</span> <span class="phrase">“cho số Miền Bắc</span> <span class="phrase">hôm nay”</span></h2></div>
        <details><summary>Các số trên trang có phải kết luận 4SO không?</summary><p>Không. Các dãy đang công khai là đầu ra của từng phương pháp. Kết luận 4SO là bước tổng hợp riêng, chỉ gồm 2 cặp đảo và 4 số.</p></details>
        <details><summary>Số hôm nay được tính từ dữ liệu nào?</summary><p>Chỉ dùng kết quả đã công bố đến hết ngày hôm qua. Nếu nguồn chưa đủ 27/27 mã hoặc ngày khóa không đúng T−1, website không công khai lại số cũ.</p></details>
        <details><summary>Tỷ lệ {rate}% có phải cam kết thắng không?</summary><p>Không. {rate}% chỉ mô tả {hit_days} ngày có ít nhất một số xuất hiện trong một cửa sổ {total_days} ngày đã kiểm định. Kết quả tương lai có thể khác.</p></details>
        <details><summary>Website có nhận cược hoặc trả thưởng không?</summary><p>Không. Đây là dịch vụ dữ liệu và báo cáo thống kê dành cho người đủ 18 tuổi; website không nhận cược, giữ tiền cược hoặc trả thưởng.</p></details>
      </div>
    </section>
    '''
    page = shell(
        title=title,
        description=description,
        canonical_path=canonical_path,
        breadcrumbs=breadcrumbs,
        body=body,
        schema=schema,
        target_date=public.get("target_date", "") if fresh else today.isoformat(),
    )
    return canonical_path, page


def method_page(today: date) -> tuple[str, str]:
    path = "/phuong-phap-4so/"
    title = "Phương pháp 4SO là gì? Cách chọn 2 cặp đảo | 4SO AI"
    description = "Giải thích phương pháp 4SO: khóa dữ liệu T−1, chấm 45 cặp đảo, chọn đúng 2 cặp và kiểm tra chống look-ahead trước khi công bố."
    breadcrumbs = [("/", "Trang chủ"), (path, "Phương pháp 4SO")]
    schema = web_page_schema(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
    )
    body = f'''
    <section class="seo-hero compact-hero"><div class="seo-wrap reading-width">
      <p class="eyebrow">PHƯƠNG PHÁP MB 4SO</p>
      <h1><span class="phrase">4SO là gì?</span> <span class="phrase">Cách chọn</span> <span class="phrase">2 cặp đảo</span></h1>
      <p class="lead">4SO là quy trình phân tích Lô tô Miền Bắc theo ngày: dùng toàn bộ dữ liệu đã công bố đến T−1, chấm đủ 45 cặp đảo không kép và chọn đúng hai cặp đứng đầu, tương ứng bốn số khác nhau.</p>
    </div></section>
    <section class="seo-section"><div class="seo-wrap reading-width">
      <div class="section-heading"><p class="eyebrow">QUY TRÌNH KHÓA TRƯỚC KẾT QUẢ</p><h2><span class="phrase">Bốn bước tạo</span> <span class="phrase">một kết luận 4SO</span></h2></div>
      <ol class="step-list">
        <li><b>1</b><div><strong>Khóa dữ liệu T−1</strong><p>Nguồn phải kết thúc đúng ngày hôm qua, mỗi ngày đủ 27 mã từ 00 đến 99, không trùng ngày và không có ô lỗi.</p></div></li>
        <li><b>2</b><div><strong>Chấm đủ 45 cặp đảo</strong><p>Loại các số kép và chỉ giữ một đại diện cho mỗi cặp đảo. Không thêm cặp theo cảm tính sau khi đã nhìn thấy kết quả.</p></div></li>
        <li><b>3</b><div><strong>Xếp hạng và lấy Top 2</strong><p>Mỗi cặp được đánh giá từ tỷ lệ xuất hiện gần đây và khoảng cách hiện tại. Tie-break được khóa trước; trường hợp hòa chưa giải quyết phải dừng để rà soát.</p></div></li>
        <li><b>4</b><div><strong>Audit rồi mới xuất bản</strong><p>Kiểm tra hash nguồn, cấu hình, executor, no-look-ahead, tính duy nhất và đọc lại. Chỉ khi toàn bộ PASS mới có một kết luận cho ngày T.</p></div></li>
      </ol>
    </div></section>
    <section class="seo-section soft"><div class="seo-wrap two-column">
      <div><p class="eyebrow">ĐẦU VÀO CÔNG KHAI</p><h2><span class="phrase">Sáu phương pháp</span> <span class="phrase">và một lớp kết luận</span></h2><p>A1, 2SO/X2, X3 Growth, F01 Tần suất, F06 Chuyển tiếp và Kép V1 tạo ra các dãy công khai. 4SO là lớp thứ bảy dùng để xếp hạng cặp và tạo kết luận cuối cùng.</p></div>
      <div class="plain-card"><ul class="check-list"><li>Không dùng kết quả ngày T</li><li>Không sửa công thức sau khi biết kết quả</li><li>Không thêm số ngoài hai cặp canonical</li><li>Không coi backtest là bảo đảm thắng</li></ul></div>
    </div></section>
    <section class="seo-section"><div class="seo-wrap reading-width">
      <div class="section-heading"><p class="eyebrow">CÁCH ĐỌC BÁO CÁO</p><h2><span class="phrase">Số phương pháp</span> <span class="phrase">khác với</span> <span class="phrase">kết luận cuối</span></h2></div>
      <p>Các số ở bảng công khai cho biết từng mô hình đang ưu tiên điều gì. Chúng có thể trùng nhau hoặc khác nhau. Người đọc không nên tự cộng toàn bộ dãy thành một giỏ mới, vì kết luận 4SO chỉ lấy đúng hai cặp sau bước chấm và audit riêng.</p>
      <p>Ngày báo cáo và ngày khóa dữ liệu luôn tách biệt: báo cáo ngày T phải dùng dữ liệu đến T−1. Nếu hai mốc không khớp, website chuyển sang trạng thái đang cập nhật và không dùng lại số của ngày trước.</p>
      <div class="cta-panel"><div><strong>Xem số công khai ngày {display_day(today)}</strong><span>HTML được dựng sẵn từ dữ liệu đã khóa đến hôm qua.</span></div><a class="primary-cta" href="/cho-so-mien-bac-hom-nay/"><span>XEM SỐ</span><span>HÔM NAY →</span></a></div>
    </div></section>
    '''
    return path, shell(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
        body=body,
        schema=schema,
    )


def history_page(proof: dict[str, Any], today: date) -> tuple[str, str]:
    path = "/lich-su-doi-chieu/"
    month = proof.get("month_summary") or {}
    month_iso = str(month.get("month") or proof.get("date", "")[:7])
    try:
        month_date = date.fromisoformat(f"{month_iso}-01")
    except ValueError:
        month_date = date.today().replace(day=1)
    month_label = month_date.strftime("%m/%Y")
    observed = int(month.get("observed_days") or 0)
    wins = int(month.get("win_days") or 0)
    records = month.get("daily_records") or []
    rows = []
    for item in records:
        day_value = date.fromisoformat(str(item.get("date")))
        hits = item.get("hits") or []
        status = "hit" if hits else "miss"
        hits_html = (
            "".join(
                f'<span>{esc(hit.get("number"))}{f" × {int(hit.get("count"))}" if int(hit.get("count") or 0) > 1 else ""}</span>'
                for hit in hits
            )
            if hits
            else "<span>0/4 số xuất hiện</span>"
        )
        evidence_parts = [f'Bản ghi #{esc(str(item.get("record_hash"))[:12])}']
        if item.get("published_at"):
            published = datetime.fromisoformat(str(item["published_at"]))
            evidence_parts.append(f'khóa {published.strftime("%d/%m %H:%M")} ICT')
        evidence = " · ".join(evidence_parts)
        rows.append(
            f'<article class="history-row {status}-row" role="row">'
            f'<time datetime="{day_value.isoformat()}">{compact_day(day_value)}</time>'
            f'<div class="history-picks">{number_chips(item.get("recommended_numbers") or [], "mini-number")}</div>'
            f'<strong class="history-status {status}">{"Trúng" if hits else "Chưa trúng"}</strong>'
            f'<div class="history-hits">{hits_html}<small class="record-evidence">{evidence}</small></div>'
            "</article>"
        )
    validation = proof.get("historical_validation") or {}
    rate = int(validation.get("rate_pct") or 0)
    history_total = int(validation.get("total_days") or 0)
    history_hits = int(validation.get("hit_days") or 0)
    window_start = display_day(str(validation.get("window_start")))
    window_end = display_day(str(validation.get("window_end")))
    title = f"Lịch sử đối chiếu số Miền Bắc tháng {month_label} | 4SO AI"
    description = f"Lịch sử đối chiếu 4SO AI tháng {month_label}: {wins}/{observed} ngày trúng đã quan sát; hiển thị cả ngày trúng và ngày chưa trúng, không ẩn khỏi tỷ lệ."
    breadcrumbs = [("/", "Trang chủ"), (path, "Lịch sử đối chiếu")]
    schema = web_page_schema(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
        modified=today.isoformat(),
    )
    schema["@graph"].append(
        {
            "@type": "Dataset",
            "@id": f"{BASE_URL}{path}#dataset",
            "name": f"Lịch sử đối chiếu 4SO AI tháng {month_label}",
            "description": description,
            "url": f"{BASE_URL}{path}",
            "inLanguage": "vi-VN",
            "temporalCoverage": f'{month.get("period_start")}/{month.get("period_end")}',
            "creator": {"@id": f"{BASE_URL}/#organization"},
            "license": f"{BASE_URL}/legal.html#terms",
            "isAccessibleForFree": True,
        }
    )
    body = f'''
    <section class="seo-hero compact-hero"><div class="seo-wrap reading-width">
      <p class="eyebrow">LỊCH SỬ ĐỐI CHIẾU</p>
      <h1><span class="phrase">Kết quả số</span> <span class="phrase">Miền Bắc</span> <span class="phrase">tháng {esc(month_label)}</span></h1>
      <p class="hero-date">Trang cập nhật ngày <time datetime="{today.isoformat()}">{display_day(today)}</time></p>
      <p class="lead">Bảng này ghi đủ {observed} ngày đã quan sát trong tháng, gồm cả ngày trúng và ngày chưa trúng. Một ngày được tính là trúng khi ít nhất một trong bốn số đã khóa trước kết quả xuất hiện trong 27 mã.</p>
    </div></section>
    <section class="seo-section"><div class="seo-wrap">
      <div class="metric-grid history-metrics"><article><strong>{wins}/{observed}</strong><span>ngày trúng trong tháng</span></article><article><strong>{rate}%</strong><span>{history_hits}/{history_total} ngày ở cửa sổ kiểm định</span></article><article><strong>{observed - wins}</strong><span>ngày chưa trúng vẫn được tính</span></article></div>
      <div class="history-table" role="table" aria-label="Lịch sử đối chiếu tháng {esc(month_label)}">
        <div class="history-head" role="row"><span>Ngày</span><span>4 số đã khóa</span><span>Trạng thái</span><span>Kết quả xuất hiện</span></div>
        {''.join(rows)}
      </div>
      <p class="fine-print">Cửa sổ kiểm định 30 ngày: {window_start}–{window_end}. Các ngày chưa trúng được giữ nguyên bốn số đã khóa, trạng thái và hash bản ghi; không bị loại khỏi mẫu số. Tỷ lệ lịch sử chỉ mô tả dữ liệu đã qua, không phải cam kết hoặc xác suất bảo đảm cho ngày tiếp theo.</p>
    </div></section>
    <section class="seo-section soft"><div class="seo-wrap two-column"><div><p class="eyebrow">NGUYÊN TẮC ĐỐI CHIẾU</p><h2><span class="phrase">Khóa trước,</span> <span class="phrase">settlement sau</span></h2><p>Số của ngày T phải được khóa khi kết quả T chưa biết. Sau khi có đủ 27 mã, hệ thống đếm số lần xuất hiện của từng số, xác định ngày trúng hoặc chưa trúng rồi mới cập nhật lịch sử.</p></div><div class="plain-card"><ul class="check-list"><li>Không sửa ngược dãy đã công bố</li><li>Không bỏ ngày chưa trúng khỏi mẫu</li><li>Nháy được đếm từ đủ 27 mã</li><li>Không suy diễn khi nguồn còn thiếu</li></ul></div></div></section>
    '''
    return path, shell(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
        body=body,
        schema=schema,
    )


def statistics_page(today: date) -> tuple[str, str]:
    path = "/thong-ke-lo-to-mien-bac-bang-ai/"
    title = "Thống kê Lô tô Miền Bắc bằng AI hoạt động thế nào? | 4SO"
    description = "Cách 4SO AI chuẩn hóa 27 mã XSMB, tính tần suất, chuyển tiếp, gan và cặp đảo từ dữ liệu T−1 để tạo báo cáo theo ngày."
    breadcrumbs = [("/", "Trang chủ"), (path, "Thống kê bằng AI")]
    schema = web_page_schema(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
    )
    body = f'''
    <section class="seo-hero compact-hero"><div class="seo-wrap reading-width">
      <p class="eyebrow">THỐNG KÊ XSMB BẰNG AI</p>
      <h1><span class="phrase">Thống kê Lô tô</span> <span class="phrase">Miền Bắc bằng AI</span> <span class="phrase">hoạt động thế nào?</span></h1>
      <p class="lead">AI trong 4SO không “biết trước” kết quả. Hệ thống tự động chuẩn hóa lịch sử, tính các đặc trưng thống kê theo cùng một công thức và kiểm tra dữ liệu trước khi xuất bản báo cáo ngày mới.</p>
    </div></section>
    <section class="seo-section"><div class="seo-wrap">
      <div class="section-heading"><p class="eyebrow">SÁU GÓC NHÌN CÔNG KHAI</p><h2><span class="phrase">Mỗi phương pháp</span> <span class="phrase">đo một tín hiệu</span> <span class="phrase">khác nhau</span></h2></div>
      <div class="explain-grid">
        <article><b>A1</b><h3>Gan và gan tối đa</h3><p>Theo dõi khoảng cách từ lần xuất hiện gần nhất và vị trí của số trong vùng điều kiện đã định trước.</p></article>
        <article><b>2SO / X2</b><h3>Cân bằng cặp đảo</h3><p>So sánh hai chiều của một cặp đảo trên nhiều cửa sổ để tránh chỉ nhìn một số đơn lẻ.</p></article>
        <article><b>X3 GROWTH</b><h3>Tăng trưởng gần</h3><p>Kết hợp mức xuất hiện trong 21 ngày và khoảng cách hiện tại để xếp ba số nổi bật.</p></article>
        <article><b>F01</b><h3>Tần suất 60 ngày</h3><p>Xếp các số theo số ngày có xuất hiện trong cửa sổ 60 ngày gần nhất.</p></article>
        <article><b>F06</b><h3>Chuyển tiếp 180 ngày</h3><p>Đo những số thường xuất hiện ở kỳ tiếp theo sau các số có mặt trong kỳ khóa gần nhất.</p></article>
        <article><b>KÉP V1</b><h3>Nhóm số kép</h3><p>So sánh các số 00, 11 đến 99 bằng khoảng cách và tần suất để chọn nhóm theo dõi.</p></article>
      </div>
    </div></section>
    <section class="seo-section soft"><div class="seo-wrap reading-width">
      <div class="section-heading"><p class="eyebrow">KIỂM SOÁT DỮ LIỆU</p><h2><span class="phrase">Vì sao phải đủ</span> <span class="phrase">27/27 mã?</span></h2></div>
      <p>Một bảng XSMB đầy đủ được chuyển thành 27 mã hai chữ số theo thứ tự giải. Thiếu một mã có thể làm sai tần suất, nháy, chuyển tiếp và cả thứ hạng. Vì vậy báo cáo ngày T chỉ được tạo khi dòng T−1 có đủ 27 mã hợp lệ, ngày nguồn không trùng và snapshot có thể kiểm tra lại bằng hash.</p>
      <div class="data-flow"><div><b>1</b><span>Kết quả đã công bố</span></div><div><b>2</b><span>Chuẩn hóa 27 mã</span></div><div><b>3</b><span>Tính 6 phương pháp</span></div><div><b>4</b><span>Audit 4SO</span></div></div>
    </div></section>
    <section class="seo-section"><div class="seo-wrap reading-width">
      <div class="section-heading"><p class="eyebrow">GIỚI HẠN CẦN BIẾT</p><h2><span class="phrase">Thống kê hỗ trợ</span> <span class="phrase">quyết định,</span> <span class="phrase">không tạo sự</span> <span class="phrase">chắc chắn</span></h2></div>
      <p>Tần suất cao, gan dài hoặc một chuyển tiếp mạnh chỉ là mô tả lịch sử. Những tín hiệu đó không làm kết quả ngẫu nhiên trong tương lai trở thành chắc chắn. Vì thế website công bố nguồn, ngày khóa, lịch sử có cả ngày chưa trúng và cảnh báo rõ rằng backtest không phải bảo đảm.</p>
      <div class="cta-panel"><div><strong>Xem báo cáo ngày {display_day(today)}</strong><span>Các số công khai được dựng trực tiếp trong HTML.</span></div><a class="primary-cta" href="/cho-so-mien-bac-hom-nay/"><span>XEM PHÂN TÍCH</span><span>HÔM NAY →</span></a></div>
    </div></section>
    '''
    return path, shell(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
        body=body,
        schema=schema,
    )


def about_page(today: date) -> tuple[str, str]:
    path = "/gioi-thieu/"
    title = "Giới thiệu 4SO AI và nguyên tắc biên tập dữ liệu"
    description = "Thông tin về 4SO AI, người phụ trách nội dung, nguồn dữ liệu, quy trình kiểm tra, giới hạn của AI và cách yêu cầu sửa sai."
    breadcrumbs = [("/", "Trang chủ"), (path, "Giới thiệu")]
    schema = web_page_schema(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
        modified=today.isoformat(),
    )
    page_node = next(
        node for node in schema["@graph"] if node.get("@id") == f"{BASE_URL}{path}#webpage"
    )
    page_node["@type"] = "AboutPage"
    page_node["about"] = {"@id": f"{BASE_URL}/#organization"}
    body = f'''
    <section class="seo-hero compact-hero"><div class="seo-wrap reading-width">
      <p class="eyebrow">GIỚI THIỆU &amp; TRÁCH NHIỆM NỘI DUNG</p>
      <h1><span class="phrase">4SO AI là</span> <span class="phrase">dịch vụ phân tích</span> <span class="phrase">dữ liệu theo ngày</span></h1>
      <p class="hero-date">Trang cập nhật ngày <time datetime="{today.isoformat()}">{display_day(today)}</time></p>
      <p class="lead">Website công khai đầu ra của sáu phương pháp thống kê và lịch sử đối chiếu; chỉ khóa phần kết luận 4SO cuối cùng. Nội dung nhằm giúp người đọc kiểm tra quy trình và giới hạn của dữ liệu trước khi sử dụng.</p>
    </div></section>
    <section class="seo-section"><div class="seo-wrap reading-width">
      <div class="section-heading"><p class="eyebrow">ĐƠN VỊ VẬN HÀNH</p><h2><span class="phrase">Ai chịu trách nhiệm</span> <span class="phrase">cho nội dung?</span></h2></div>
      <div class="plain-card"><p><strong>Tên dịch vụ:</strong> 4SO AI.</p><p><strong>Người phụ trách nội dung:</strong> Thầy Linh, đại diện nhóm vận hành 4SO AI.</p><p><strong>Kênh hỗ trợ công khai:</strong> <a class="text-link" href="https://zalo.me/0398696879" target="_blank" rel="noopener noreferrer">Zalo hỗ trợ 4SO AI →</a></p><p><strong>Cập nhật tài liệu:</strong> {display_day(today)}.</p></div>
    </div></section>
    <section class="seo-section soft"><div class="seo-wrap two-column">
      <div><p class="eyebrow">NGUYÊN TẮC BIÊN TẬP</p><h2><span class="phrase">Khóa dữ liệu trước,</span> <span class="phrase">đối chiếu sau</span></h2><p>Báo cáo ngày T chỉ dùng dữ liệu đã công bố đến T−1. Nguồn phải đủ 27/27 mã, ngày không trùng, đầu ra không biết trước kết quả và các kiểm tra audit phải hoàn tất trước khi hiển thị số ngày mới.</p></div>
      <div class="plain-card"><ul class="check-list"><li>Không gắn số ngày cũ cho ngày mới</li><li>Không sửa ngược lịch sử sau kết quả</li><li>Giữ cả ngày trúng và ngày chưa trúng</li><li>Không đưa kết luận trả phí vào HTML/JSON công khai</li></ul></div>
    </div></section>
    <section class="seo-section"><div class="seo-wrap reading-width">
      <div class="section-heading"><p class="eyebrow">NGUỒN &amp; GIỚI HẠN</p><h2><span class="phrase">AI tính toán,</span> <span class="phrase">không biết trước</span> <span class="phrase">kết quả</span></h2></div>
      <p>Hệ thống chuẩn hóa kết quả Xổ số Miền Bắc đã công bố thành 27 mã hai chữ số, sau đó áp dụng cùng các công thức tần suất, chuyển tiếp, gan, tăng trưởng và cặp đảo. Hash nguồn và hash bản ghi được dùng để hỗ trợ kiểm tra tính nhất quán.</p>
      <p>Tần suất, backtest và tỷ lệ lịch sử chỉ mô tả dữ liệu đã qua. Chúng không biến một kết quả tương lai thành chắc chắn, không phải tư vấn tài chính và không phải cam kết lợi nhuận.</p>
    </div></section>
    <section class="seo-section soft"><div class="seo-wrap reading-width">
      <div class="section-heading"><p class="eyebrow">SỬA SAI &amp; KHIẾU NẠI</p><h2><span class="phrase">Cách yêu cầu</span> <span class="phrase">kiểm tra lại</span></h2></div>
      <p>Nếu phát hiện sai ngày, thiếu số, sai kết quả đối chiếu hoặc lỗi thanh toán, hãy gửi URL, ảnh chụp và thời điểm quan sát qua Zalo. Nhóm vận hành sẽ kiểm tra bản ghi nguồn, công bố phần sửa trên trang liên quan và không xóa ngày chưa trúng để làm đẹp tỷ lệ.</p>
      <div class="cta-panel"><div><strong>Xem điều khoản và chính sách dữ liệu</strong><span>Phạm vi dịch vụ, hoàn phí, bảo mật và quyền của người dùng.</span></div><a class="primary-cta" href="/legal.html"><span>ĐỌC ĐIỀU KHOẢN</span><span>&amp; BẢO MẬT →</span></a></div>
    </div></section>
    '''
    return path, shell(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
        body=body,
        schema=schema,
    )


def sitemap_xml(today: date) -> str:
    daily = today.isoformat()
    fixed = "2026-08-12"
    rows = (
        ("/", daily, "daily", "1.0"),
        ("/cho-so-mien-bac-hom-nay/", daily, "daily", "0.9"),
        ("/phuong-phap-4so/", daily, "monthly", "0.8"),
        ("/lich-su-doi-chieu/", daily, "daily", "0.8"),
        ("/thong-ke-lo-to-mien-bac-bang-ai/", daily, "monthly", "0.8"),
        ("/gioi-thieu/", daily, "yearly", "0.6"),
        ("/legal.html", fixed, "yearly", "0.3"),
    )
    urls = "\n".join(
        "  <url>\n"
        f"    <loc>{BASE_URL}{path}</loc>\n"
        f"    <lastmod>{modified}</lastmod>\n"
        f"    <changefreq>{frequency}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
        for path, modified, frequency, priority in rows
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )


def llms_text(today: date) -> str:
    return f'''# 4SO AI

> Website phân tích dữ liệu Lô tô Miền Bắc theo ngày, công khai đầu ra của sáu phương pháp và lịch sử đối chiếu. Kết luận 4SO trả phí không nằm trong HTML hoặc JSON công khai.

## Trang chính

- [Báo cáo công khai hôm nay]({BASE_URL}/cho-so-mien-bac-hom-nay/): dữ liệu ngày {display_day(today)}, khóa T−1 và số theo từng phương pháp.
- [Phương pháp 4SO]({BASE_URL}/phuong-phap-4so/): quy trình khóa dữ liệu, chấm 45 cặp đảo và audit chống look-ahead.
- [Lịch sử đối chiếu]({BASE_URL}/lich-su-doi-chieu/): đủ ngày trúng và chưa trúng, bốn số đã khóa và hash bản ghi.
- [Thống kê bằng AI]({BASE_URL}/thong-ke-lo-to-mien-bac-bang-ai/): vai trò của sáu phương pháp công khai.
- [Giới thiệu và trách nhiệm nội dung]({BASE_URL}/gioi-thieu/): người phụ trách, nguồn, giới hạn và quy trình sửa sai.
- [Điều khoản và bảo mật]({BASE_URL}/legal.html): phạm vi dịch vụ, thanh toán, hoàn phí và dữ liệu cá nhân.

## Nguyên tắc sử dụng

- Báo cáo ngày T chỉ dùng dữ liệu đã công bố đến T−1 và phải đủ 27/27 mã.
- Tỷ lệ lịch sử và backtest không phải cam kết hoặc xác suất bảo đảm cho tương lai.
- Dịch vụ chỉ dành cho người đủ 18 tuổi; không nhận cược, giữ tiền cược hay trả thưởng.
'''


def build(output_root: Path, today: date) -> list[Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    public = load_json(PUBLIC_METHODS)
    proof = load_json(YESTERDAY_PROOF)
    validate_public_payload(public)
    validate_proof_payload(proof)
    pages = [
        today_page(public, proof, today),
        method_page(today),
        history_page(proof, today),
        statistics_page(today),
        about_page(today),
    ]
    written = []
    for path, content in pages:
        target = output_root / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    landing = render_site_v2_landing(public, proof, today)
    for target in (
        output_root / "index.html",
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(landing, encoding="utf-8")
        written.append(target)
    public_dir = output_root / "ai-methods"
    public_dir.mkdir(parents=True, exist_ok=True)
    for source in (PUBLIC_METHODS, YESTERDAY_PROOF):
        target = public_dir / source.name
        shutil.copyfile(source, target)
        written.append(target)
    sitemap = output_root / "sitemap.xml"
    sitemap.write_text(sitemap_xml(today), encoding="utf-8")
    written.append(sitemap)
    llms = output_root / "llms.txt"
    llms.write_text(llms_text(today), encoding="utf-8")
    written.append(llms)
    return written


def validate_output(output_root: Path, today: date) -> None:
    expected = {
        "cho-so-mien-bac-hom-nay": "Cho số Miền Bắc hôm nay",
        "phuong-phap-4so": "4SO là gì?",
        "lich-su-doi-chieu": "Lịch sử đối chiếu",
        "thong-ke-lo-to-mien-bac-bang-ai": "Thống kê Lô tô Miền Bắc",
        "gioi-thieu": "Người phụ trách nội dung",
    }
    for slug, token in expected.items():
        page = output_root / slug / "index.html"
        text = page.read_text(encoding="utf-8")
        if token not in text:
            raise AssertionError(f"Missing SEO token {token!r} in {page}")
        if f'<link rel="canonical" href="{BASE_URL}/{slug}/"' not in text:
            raise AssertionError(f"Invalid canonical in {page}")
        if LOCKED_FIELD_PATTERN.search(text):
            raise AssertionError(f"Paid 4SO field leaked into {page}")
        if "application/ld+json" not in text or "BreadcrumbList" not in text:
            raise AssertionError(f"Structured data missing in {page}")
    today_text = (output_root / "cho-so-mien-bac-hom-nay" / "index.html").read_text(
        encoding="utf-8"
    )
    if display_day(today) not in today_text:
        raise AssertionError("Today's Vietnam date is not statically rendered")
    is_fresh = "data-current-methods" in today_text
    if is_fresh and ("cssSelector\":\".paywall" not in today_text or 'class="paywall locked-card"' not in today_text):
        raise AssertionError("Fresh-day paywall markup is incomplete")
    if not is_fresh and ('class="paywall locked-card"' in today_text or "CHƯA NHẬN THANH TOÁN" not in today_text):
        raise AssertionError("Stale-day page must disable the paywall")
    if is_fresh:
        for token in ("A1", "2SO / X2", "F01 TẦN SUẤT", "F06 CHUYỂN TIẾP"):
            if token not in today_text:
                raise AssertionError(f"Static current method missing: {token}")
    landing = (output_root / "index.html").read_text(encoding="utf-8")
    if SEARCH_CONSOLE_TOKEN not in landing:
        raise AssertionError("Search Console verification tag missing from homepage")
    if "fonts.googleapis.com" in landing or "fonts.gstatic.com" in landing:
        raise AssertionError("Homepage must not block rendering on external fonts")
    if is_fresh and landing.count('class="method-item"') != 6:
        raise AssertionError("Homepage must statically render exactly six public methods")
    if not is_fresh and 'class="method-item"' in landing:
        raise AssertionError("Stale homepage must remove old public methods")
    if f'data-public-ready="{str(is_fresh).lower()}"' not in landing:
        raise AssertionError("Homepage must publish an explicit daily readiness state")
    app_text = (ROOT / "site-v2" / "app.js").read_text(encoding="utf-8")
    if not all(token in app_text for token in ("setPaymentAvailability(", "STATIC_PUBLIC_READY", "dataReady")):
        raise AssertionError("Homepage payment must fail closed until daily data validates")
    history = (output_root / "lich-su-doi-chieu" / "index.html").read_text(encoding="utf-8")
    expected_history_rows = int((load_json(YESTERDAY_PROOF).get("month_summary") or {}).get("observed_days") or 0)
    if history.count('class="history-row ') != expected_history_rows or "Đã ghi nhận trong mẫu" in history:
        raise AssertionError("History page must show all four picks for every observed day")
    if "Dataset" not in history or "Bản ghi #" not in history:
        raise AssertionError("History dataset provenance is incomplete")
    if not (output_root / "llms.txt").read_text(encoding="utf-8").startswith("# 4SO AI"):
        raise AssertionError("llms.txt was not generated")
    sitemap = (output_root / "sitemap.xml").read_text(encoding="utf-8")
    for slug in expected:
        if f"{BASE_URL}/{slug}/" not in sitemap:
            raise AssertionError(f"Sitemap missing {slug}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("_site"))
    parser.add_argument("--today", help="Override Vietnam date (YYYY-MM-DD) for deterministic tests")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else datetime.now(VN_TZ).date()
    if args.self_test:
        with tempfile.TemporaryDirectory(prefix="mb-seo-") as temporary:
            output = Path(temporary)
            build(output, today)
            validate_output(output, today)
            stale = today + timedelta(days=1)
            build(output, stale)
            stale_text = (output / "cho-so-mien-bac-hom-nay" / "index.html").read_text(encoding="utf-8")
            if "data-current-methods" in stale_text or 'class="paywall locked-card"' in stale_text:
                raise AssertionError("Stale SEO page must hide old method numbers and disable the paywall")
            if "CHƯA NHẬN THANH TOÁN" not in stale_text:
                raise AssertionError("Stale SEO page must fail closed before payment")
            stale_landing = (output / "index.html").read_text(encoding="utf-8")
            if "Không dùng lại dữ liệu đối chiếu của ngày cũ" not in stale_landing:
                raise AssertionError("Stale homepage must not present an older proof as yesterday")
        print("SEO_STATIC_RENDER_SELF_TEST_OK")
        return
    paths = build(args.output_root, today)
    validate_output(args.output_root, today)
    print(json.dumps({"date": today.isoformat(), "pages": [str(path) for path in paths]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
