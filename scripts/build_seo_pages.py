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
import html
import json
import re
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_METHODS = ROOT / "ai-methods" / "public-methods.json"
YESTERDAY_PROOF = ROOT / "ai-methods" / "yesterday-proof.json"
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
BASE_URL = "https://lemienbac.com"
LOCKED_FIELD_PATTERN = re.compile(
    r"(?:final|canonical)[_-]?(?:codes|pairs)", re.IGNORECASE
)

NAV_LINKS = (
    ("/cho-so-mien-bac-hom-nay/", "Số hôm nay"),
    ("/phuong-phap-4so/", "Phương pháp 4SO"),
    ("/lich-su-doi-chieu/", "Lịch sử"),
    ("/thong-ke-lo-to-mien-bac-bang-ai/", "Thống kê AI"),
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
                "@type": "WebSite",
                "@id": f"{BASE_URL}/#website",
                "url": f"{BASE_URL}/",
                "name": "4SO AI",
                "description": "Phân tích dữ liệu Lô tô Miền Bắc bằng AI theo ngày.",
                "inLanguage": "vi-VN",
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
  <link rel="stylesheet" href="/ai-methods/seo.css?v=20260812" />
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
        <details><summary>Tỷ lệ 80% có phải cam kết thắng không?</summary><p>Không. 80% chỉ mô tả 24 ngày có ít nhất một số xuất hiện trong một cửa sổ 30 ngày đã kiểm định. Kết quả tương lai có thể khác.</p></details>
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


def history_page(proof: dict[str, Any]) -> tuple[str, str]:
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
    winning_days = {
        str(item.get("date")): item
        for item in month.get("winning_days") or []
        if isinstance(item, dict) and item.get("date")
    }
    rows = []
    for day_number in range(1, observed + 1):
        day_value = month_date.replace(day=day_number)
        item = winning_days.get(day_value.isoformat())
        if item:
            hits = item.get("hits") or []
            hits_html = "".join(
                f'<span>{esc(hit.get("number"))}{f" × {int(hit.get("count"))}" if int(hit.get("count") or 0) > 1 else ""}</span>'
                for hit in hits
            )
            picks = number_chips(item.get("recommended_numbers") or [], "mini-number")
            rows.append(
                f'<article class="history-row hit-row"><time datetime="{day_value.isoformat()}">{compact_day(day_value)}</time><div class="history-picks">{picks}</div><strong class="history-status hit">Trúng</strong><div class="history-hits">{hits_html}</div></article>'
            )
        else:
            rows.append(
                f'<article class="history-row miss-row"><time datetime="{day_value.isoformat()}">{compact_day(day_value)}</time><div class="history-picks muted">Đã ghi nhận trong mẫu</div><strong class="history-status miss">Chưa trúng</strong><div class="history-hits"><span>0/4 số xuất hiện</span></div></article>'
            )
    validation = proof.get("historical_validation") or {}
    rate = int(validation.get("rate_pct") or 0)
    history_total = int(validation.get("total_days") or 0)
    history_hits = int(validation.get("hit_days") or 0)
    title = f"Lịch sử đối chiếu số Miền Bắc tháng {month_label} | 4SO AI"
    description = f"Lịch sử đối chiếu 4SO AI tháng {month_label}: {wins}/{observed} ngày trúng đã quan sát; hiển thị cả ngày trúng và ngày chưa trúng, không ẩn khỏi tỷ lệ."
    breadcrumbs = [("/", "Trang chủ"), (path, "Lịch sử đối chiếu")]
    schema = web_page_schema(
        title=title,
        description=description,
        canonical_path=path,
        breadcrumbs=breadcrumbs,
    )
    body = f'''
    <section class="seo-hero compact-hero"><div class="seo-wrap reading-width">
      <p class="eyebrow">LỊCH SỬ ĐỐI CHIẾU</p>
      <h1><span class="phrase">Kết quả số</span> <span class="phrase">Miền Bắc</span> <span class="phrase">tháng {esc(month_label)}</span></h1>
      <p class="lead">Bảng này ghi đủ {observed} ngày đã quan sát trong tháng, gồm cả ngày trúng và ngày chưa trúng. Một ngày được tính là trúng khi ít nhất một trong bốn số đã khóa trước kết quả xuất hiện trong 27 mã.</p>
    </div></section>
    <section class="seo-section"><div class="seo-wrap">
      <div class="metric-grid history-metrics"><article><strong>{wins}/{observed}</strong><span>ngày trúng trong tháng</span></article><article><strong>{rate}%</strong><span>{history_hits}/{history_total} ngày ở cửa sổ kiểm định</span></article><article><strong>{observed - wins}</strong><span>ngày chưa trúng vẫn được tính</span></article></div>
      <div class="history-table" role="table" aria-label="Lịch sử đối chiếu tháng {esc(month_label)}">
        <div class="history-head" role="row"><span>Ngày</span><span>4 số đã khóa</span><span>Trạng thái</span><span>Kết quả xuất hiện</span></div>
        {''.join(rows)}
      </div>
      <p class="fine-print">Các ngày chưa trúng được giữ trong mẫu và mẫu số. Tỷ lệ lịch sử chỉ mô tả dữ liệu đã qua, không phải cam kết hoặc xác suất bảo đảm cho ngày tiếp theo.</p>
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


def sitemap_xml(today: date) -> str:
    daily = today.isoformat()
    fixed = "2026-08-12"
    rows = (
        ("/", daily, "daily", "1.0"),
        ("/cho-so-mien-bac-hom-nay/", daily, "daily", "0.9"),
        ("/phuong-phap-4so/", fixed, "monthly", "0.8"),
        ("/lich-su-doi-chieu/", daily, "daily", "0.8"),
        ("/thong-ke-lo-to-mien-bac-bang-ai/", fixed, "monthly", "0.8"),
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


def build(output_root: Path, today: date) -> list[Path]:
    public = load_json(PUBLIC_METHODS)
    proof = load_json(YESTERDAY_PROOF)
    validate_public_payload(public)
    pages = [
        today_page(public, proof, today),
        method_page(today),
        history_page(proof),
        statistics_page(today),
    ]
    written = []
    for path, content in pages:
        target = output_root / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    sitemap = output_root / "sitemap.xml"
    sitemap.write_text(sitemap_xml(today), encoding="utf-8")
    written.append(sitemap)
    return written


def validate_output(output_root: Path, today: date) -> None:
    expected = {
        "cho-so-mien-bac-hom-nay": "Cho số Miền Bắc hôm nay",
        "phuong-phap-4so": "4SO là gì?",
        "lich-su-doi-chieu": "Lịch sử đối chiếu",
        "thong-ke-lo-to-mien-bac-bang-ai": "Thống kê Lô tô Miền Bắc",
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
        print("SEO_STATIC_RENDER_SELF_TEST_OK")
        return
    paths = build(args.output_root, today)
    validate_output(args.output_root, today)
    print(json.dumps({"date": today.isoformat(), "pages": [str(path) for path in paths]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
