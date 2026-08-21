#!/usr/bin/env python3
"""Apply conversion rendering and route every purchase CTA to the live checkout.

The paid report and the optional public-method feed have separate readiness
states. A public-safe paid-report manifest (dates and status only, never paid
codes) is the authoritative payment gate. Every purchase CTA uses one simple
label and opens the checkout immediately.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from optimize_conversion_site import inject_stylesheet, optimize_home, write_if_changed


ROOT = Path(__file__).resolve().parents[1]
READY_MANIFEST = ROOT / "data" / "paid-report-ready.json"
VN = ZoneInfo("Asia/Ho_Chi_Minh")
HOTFIX_HREF = "/checkout-hotfix.css?v=20260815-2"

DIRECT_CHECKOUT_SCRIPT = '''
  <script id="direct-checkout-script">
  (()=>{
    const params=new URLSearchParams(location.search);
    const requested=params.get('checkout')==='1'||params.get('buy')==='1'||location.hash==='#thanh-toan';
    if(!requested)return;
    let attempts=0;
    const open=()=>{
      attempts+=1;
      const button=[...document.querySelectorAll('[data-open-checkout]')]
        .find(item=>!item.disabled&&item.getAttribute('aria-disabled')!=='true');
      if(button){
        const clean=new URL(location.href);
        clean.searchParams.delete('checkout');clean.searchParams.delete('buy');clean.hash='';
        history.replaceState({},'',clean.pathname+clean.search);
        button.click();
        return;
      }
      if(attempts<30)setTimeout(open,100);
    };
    window.addEventListener('load',()=>setTimeout(open,60),{once:true});
  })();
  </script>
'''

FLOATING_CTA = '''
  <a class="seo-purchase-float" href="/?checkout=1" aria-label="Nhận báo cáo AI hôm nay, giá 30.000 đồng">
    <span>NHẬN BÁO CÁO HÔM NAY</span><b>30.000đ</b>
  </a>
'''


def paid_report_is_ready() -> bool:
    try:
        payload = json.loads(READY_MANIFEST.read_text(encoding="utf-8"))
        now = datetime.now(VN)
        today = now.date()
        report_date = payload.get("report_date")
        data_lock = payload.get("data_lock")
        same_day = (
            report_date == today.isoformat()
            and data_lock == (today - timedelta(days=1)).isoformat()
        )
        post_draw_next_day = (
            now.hour >= 19
            and report_date == (today + timedelta(days=1)).isoformat()
            and data_lock == today.isoformat()
        )
        return (
            payload.get("schema_version") in {"MB_PAID_REPORT_READINESS_V1", "MB_PAID_REPORT_READINESS_V2_MAX2"}
            and payload.get("status") == "PUBLISHED_PASS_PRIVATE"
            and payload.get("outcome_known_at_selection") is False
            and (same_day or post_draw_next_day)
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def inject_hotfix(content: str) -> str:
    content = re.sub(
        r'<link rel="stylesheet" href="/checkout-hotfix\.css\?v=[^"]+">',
        f'<link rel="stylesheet" href="{HOTFIX_HREF}">',
        content,
        count=1,
    )
    if HOTFIX_HREF in content:
        return content
    if "</head>" not in content:
        raise ValueError("HTML page is missing </head>")
    return content.replace(
        "</head>", f'  <link rel="stylesheet" href="{HOTFIX_HREF}">\n</head>', 1
    )


def simplify_purchase_copy(content: str) -> str:
    replacements = (
        ("MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ", "NHẬN BÁO CÁO HÔM NAY – 30.000Đ"),
        ("MỞ KẾT LUẬN AI · 30K", "NHẬN BÁO CÁO · 30K"),
        ("MỞ KẾT LUẬN AI HÔM NAY", "NHẬN BÁO CÁO HÔM NAY"),
        ("Mở kết luận AI hôm nay", "Nhận báo cáo hôm nay"),
        ("Mở kết luận AI ngày hôm nay", "Nhận báo cáo AI ngày hôm nay"),
        ("mở kết luận AI ngày hôm nay", "nhận báo cáo AI ngày hôm nay"),
        ("MỞ KẾT LUẬN", "NHẬN BÁO CÁO"),
        ("YÊU CẦU MỞ KẾT LUẬN", "YÊU CẦU MỞ BÁO CÁO"),
        ("Kết luận AI sẽ tự mở", "Báo cáo sẽ tự mở"),
        ("kết luận AI sẽ tự mở", "báo cáo sẽ tự mở"),
    )
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def route_purchase_links(content: str) -> str:
    content = content.replace('href="/#buy"', 'href="/?checkout=1"')
    content = content.replace('href="/#pricing"', 'href="/?checkout=1"')
    content = content.replace('href="/?buy=1"', 'href="/?checkout=1"')
    content = content.replace(
        '<span>Xem báo cáo</span><span>hôm nay</span>',
        '<span>Nhận báo cáo</span><span>30.000đ</span>',
    )
    return simplify_purchase_copy(content)


def mark_paid_ready(content: str) -> str:
    if not paid_report_is_ready():
        return content
    content = re.sub(
        r'data-public-ready="(?:true|false)"(?:\s+data-paid-report-ready="(?:true|false)")?',
        'data-public-ready="true" data-paid-report-ready="true"',
        content,
        count=1,
    )
    content = re.sub(
        r'(<(?:button|a)\b[^>]*\bdata-open-checkout\b[^>]*)\sdisabled(?:="disabled")?',
        r'\1',
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(
        r'(<(?:button|a)\b[^>]*\bdata-open-checkout\b[^>]*)\saria-disabled="true"',
        r'\1',
        content,
        flags=re.IGNORECASE,
    )
    return content


def apply_site(output_root: Path) -> None:
    html_files = list(output_root.rglob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files found under {output_root}")

    home_path = output_root / "index.html"
    if not home_path.exists():
        raise FileNotFoundError(f"Missing home page: {home_path}")

    for page in html_files:
        content = page.read_text(encoding="utf-8")
        content = inject_hotfix(inject_stylesheet(content))
        content = route_purchase_links(content)
        if page == home_path:
            content = mark_paid_ready(content)
            content = optimize_home(content)
            content = simplify_purchase_copy(content)
            content = mark_paid_ready(content)
            if 'id="direct-checkout-script"' not in content:
                content = content.replace("</body>", f"{DIRECT_CHECKOUT_SCRIPT}</body>", 1)
        elif 'class="seo-purchase-float"' not in content and "</body>" in content:
            content = content.replace("</body>", f"{FLOATING_CTA}</body>", 1)
            if '<body>' in content:
                content = content.replace("<body>", '<body class="has-seo-purchase-float">', 1)
        write_if_changed(page, content)

    home = home_path.read_text(encoding="utf-8")
    required = (
        HOTFIX_HREF,
        'id="direct-checkout-script"',
        'class="conversion-trust"',
        'class="buy-value-list"',
        'class="buy-guarantees"',
        'class="checkout-value"',
        'class="checkout-trust"',
    )
    for marker in required:
        if marker not in home:
            raise AssertionError(f"Missing conversion marker: {marker}")

    ready = 'data-paid-report-ready="true"' in home
    history_available = 'class="historical-disclaimer"' in home
    if ready:
        for marker in (
            'data-public-ready="true"',
            'class="conversion-preview"',
            "NHẬN BÁO CÁO HÔM NAY – 30.000Đ",
        ):
            if marker not in home:
                raise AssertionError(f"Ready page missing marker: {marker}")
        purchase_buttons = re.findall(
            r'<button\b[^>]*\bdata-open-checkout\b[^>]*>', home, flags=re.IGNORECASE
        )
        if not purchase_buttons or all(" disabled" in button.lower() for button in purchase_buttons):
            raise AssertionError("Ready page has no enabled checkout button")
        if history_available and 'class="history-cta"' not in home:
            raise AssertionError("Ready page with history must contain a history CTA")
    else:
        if 'class="history-cta"' in home:
            raise AssertionError("Updating page must not expose a history purchase CTA")
        if "CHƯA NHẬN THANH TOÁN" not in home:
            raise AssertionError("Updating page must stay fail-closed")

    if history_available and 'class="history-disclosure"' not in home:
        raise AssertionError("Historical detail must be collapsed when available")
    if not history_available and 'class="history-disclosure"' in home:
        raise AssertionError("Updating page must not contain stale historical detail")
    if "MỞ KẾT LUẬN" in home:
        raise AssertionError("Old complex purchase wording remains on home page")

    for page in html_files:
        if page == home_path:
            continue
        text = page.read_text(encoding="utf-8")
        if 'href="/#buy"' in text or 'href="/#pricing"' in text or 'href="/?buy=1"' in text:
            raise AssertionError(f"Intermediate purchase route remains in {page}")
        if 'class="seo-purchase-float"' not in text:
            raise AssertionError(f"Secondary page lacks direct purchase CTA: {page}")
        if 'href="/?checkout=1"' not in text:
            raise AssertionError(f"Secondary page does not open checkout directly: {page}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    apply_site(args.output_root.resolve())


if __name__ == "__main__":
    main()
