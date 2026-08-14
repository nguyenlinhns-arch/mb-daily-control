#!/usr/bin/env python3
"""Apply conversion rendering and route every purchase CTA to the live checkout.

Public statistical content may lag while the private paid report is already
published. A public-safe readiness manifest (dates and status only, never paid
codes) is therefore the authoritative payment gate. All secondary-page CTAs
land on the home page and open the checkout immediately instead of scrolling to
an intermediate section.
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
HOTFIX_HREF = "/checkout-hotfix.css?v=20260815-1"

DIRECT_CHECKOUT_SCRIPT = '''
  <script id="direct-checkout-script">
  (()=>{
    const params=new URLSearchParams(location.search);
    if(params.get('buy')!=='1')return;
    window.addEventListener('load',()=>{
      const button=[...document.querySelectorAll('[data-open-checkout]')]
        .find(item=>!item.disabled&&item.getAttribute('aria-disabled')!=='true');
      if(!button)return;
      const clean=new URL(location.href);clean.searchParams.delete('buy');
      history.replaceState({},'',clean.pathname+clean.search+clean.hash);
      window.setTimeout(()=>button.click(),80);
    },{once:true});
  })();
  </script>
'''

FLOATING_CTA = '''
  <a class="seo-purchase-float" href="/?buy=1" aria-label="Mở kết luận AI hôm nay, giá 30.000 đồng">
    <span>MỞ KẾT LUẬN AI HÔM NAY</span><b>30.000đ</b>
  </a>
'''


def paid_report_is_ready() -> bool:
    try:
        payload = json.loads(READY_MANIFEST.read_text(encoding="utf-8"))
        today = datetime.now(VN).date()
        return (
            payload.get("schema_version") == "MB_PAID_REPORT_READINESS_V1"
            and payload.get("status") == "PUBLISHED_PASS_PRIVATE"
            and payload.get("outcome_known_at_selection") is False
            and payload.get("report_date") == today.isoformat()
            and payload.get("data_lock") == (today - timedelta(days=1)).isoformat()
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


def route_purchase_links(content: str) -> str:
    content = content.replace('href="/#buy"', 'href="/?buy=1"')
    content = content.replace('href="/#pricing"', 'href="/?buy=1"')
    content = content.replace('NHẬN BÁO CÁO HÔM NAY', 'MỞ KẾT LUẬN AI HÔM NAY')
    content = content.replace('Nhận báo cáo hôm nay · 30.000đ', 'Mở kết luận AI hôm nay · 30.000đ')
    content = content.replace('<span>Xem báo cáo</span><span>hôm nay</span>', '<span>Mở kết luận AI</span><span>30.000đ</span>')
    return content


def mark_paid_ready(content: str) -> str:
    if not paid_report_is_ready():
        return content
    content = re.sub(
        r'data-public-ready="(?:true|false)"',
        'data-public-ready="true" data-paid-report-ready="true"',
        content,
        count=1,
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
            if 'id="direct-checkout-script"' not in content:
                content = content.replace("</body>", f"{DIRECT_CHECKOUT_SCRIPT}</body>", 1)
        elif 'class="seo-purchase-float"' not in content and "</body>" in content:
            content = content.replace("</body>", f"{FLOATING_CTA}</body>", 1)
            content = content.replace("<body", '<body class="has-seo-purchase-float"', 1) if '<body>' in content else content
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

    ready = 'data-public-ready="true"' in home
    history_available = 'class="historical-disclaimer"' in home
    if ready:
        for marker in (
            'class="conversion-preview"',
            "MỞ KẾT LUẬN AI HÔM NAY – 30.000Đ",
        ):
            if marker not in home:
                raise AssertionError(f"Ready page missing marker: {marker}")
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

    for page in html_files:
        if page == home_path:
            continue
        text = page.read_text(encoding="utf-8")
        if 'href="/#buy"' in text or 'href="/#pricing"' in text:
            raise AssertionError(f"Intermediate purchase route remains in {page}")
        if 'class="seo-purchase-float"' not in text:
            raise AssertionError(f"Secondary page lacks direct purchase CTA: {page}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    apply_site(args.output_root.resolve())


if __name__ == "__main__":
    main()
