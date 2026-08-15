#!/usr/bin/env python3
"""Finalize the portal homepage and sanitize all public 4SO surfaces."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import apply_home_portal as portal
import sanitize_public_4so as fourso_privacy


def rewrite_purchase_copy(content: str, ready: dict[str, object]) -> str:
    target = str(ready.get("report_date") or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target):
        raise ValueError("Paid report date is missing or invalid")
    label = portal.dmy(target)

    # The public purchase flow should describe the thing the visitor wants,
    # while the technical 4SO/report terminology remains internal/audit-facing.
    content = content.replace(
        f'<p class="eyebrow">BÁO CÁO 4SO NGÀY {label}</p>',
        f'<p class="eyebrow">GỢI Ý SỐ NGÀY {label}</p>',
    )
    content = content.replace(
        f'Mở đúng một báo cáo 4SO cho ngày {label} sau khi giao dịch được xác nhận.',
        f'Mở gợi ý số ngày {label} sau khi giao dịch được xác nhận.',
    )
    content = content.replace(
        f'01 báo cáo ngày {label}',
        f'Gợi ý số ngày {label}',
    )
    content = content.replace(
        'NHẬN BÁO CÁO 4SO – 30.000Đ',
        'NHẬN GỢI Ý SỐ – 30.000Đ',
    )
    content = content.replace(
        f'NHẬN BÁO CÁO NGÀY {label}',
        f'GỢI Ý SỐ NGÀY {label}',
    )
    content = content.replace(
        f'Nhận báo cáo AI ngày {label}',
        f'Nhận gợi ý số ngày {label}',
    )

    # Fail closed: the main purchase card must carry the explicit target date.
    buy = re.search(
        r'<section class="buy-simple portal-buy"[^>]*>.*?</section>',
        content,
        flags=re.I | re.S,
    )
    if not buy:
        raise ValueError("Purchase block missing after portal build")
    block = buy.group(0)
    if f'GỢI Ý SỐ NGÀY {label}' not in block or 'NHẬN GỢI Ý SỐ – 30.000Đ' not in block:
        raise ValueError("Explicit daily suggestion copy missing from purchase block")
    if 'BÁO CÁO 4SO NGÀY' in block:
        raise ValueError("Legacy purchase wording remains in purchase block")
    return content


def apply(output_root: Path) -> dict[str, object]:
    page = output_root / "index.html"
    stats_path = output_root / "statistics-data.json"
    if not page.exists() or not stats_path.exists():
        raise FileNotFoundError("Homepage or statistics-data.json missing")

    ready = portal.load_json(portal.PAID_READY)
    result = portal.build_home(
        page.read_text(encoding="utf-8"),
        portal.load_json(stats_path),
        portal.load_json(portal.PUBLIC_METHODS),
        portal.load_json(portal.PUBLIC_PROOF),
        ready,
    )
    result = rewrite_purchase_copy(result, ready)

    buttons = re.findall(r'<button\b[^>]*\bdata-open-checkout\b[^>]*>', result, flags=re.I)
    if len(buttons) != 2:
        raise ValueError(f"Homepage must contain exactly two checkout buttons, found {len(buttons)}")
    if 'data-home-portal="v1"' not in result or 'Phương pháp công khai hôm nay' not in result:
        raise ValueError("Portal homepage markers missing")
    if re.search(r'4SO[^<]{0,180}\b\d{2}\b\s*[-–—]\s*\b\d{2}\b', result, flags=re.I):
        raise ValueError("Potential current 4SO pair leaked in homepage")

    page.write_text(result, encoding="utf-8")
    privacy = fourso_privacy.sanitize(output_root)

    # Final fail-closed scan of the public proof surfaces.
    for rel in ("historical-proof.json", "ai-methods/yesterday-proof.json"):
        text = (output_root / rel).read_text(encoding="utf-8").lower()
        for token in ("recommended_numbers", '"outputs"', '"observed"', "canonical_codes", "canonical_pairs", "final_codes", "final_pairs"):
            if token.lower() in text:
                raise ValueError(f"4SO public proof leak after sanitization: {rel} / {token}")
    history = (output_root / "lich-su-doi-chieu" / "index.html").read_text(encoding="utf-8")
    method = (output_root / "phuong-phap-4so" / "index.html").read_text(encoding="utf-8")
    if 'data-4so-sanitized="true"' not in history or 'data-4so-sanitized="true"' not in method:
        raise ValueError("4SO sanitized page marker missing")

    return {
        "status": "PASS",
        "homepage": "portal-v1",
        "checkout_buttons": 2,
        "purchase_copy": f"Gợi ý số ngày {portal.dmy(str(ready['report_date']))}",
        "fourso_public_mode": privacy["mode"],
    }


def self_test() -> None:
    ready = {"report_date": "2026-08-16"}
    sample = (
        '<html><body><section class="buy-simple portal-buy" id="buy">'
        '<p class="eyebrow">BÁO CÁO 4SO NGÀY 16/08/2026</p>'
        '<p>Mở đúng một báo cáo 4SO cho ngày 16/08/2026 sau khi giao dịch được xác nhận.</p>'
        '<p>01 báo cáo ngày 16/08/2026</p>'
        '<button>NHẬN BÁO CÁO 4SO – 30.000Đ</button></section>'
        '<div><p>NHẬN BÁO CÁO NGÀY 16/08/2026</p>'
        '<h2>Nhận báo cáo AI ngày 16/08/2026</h2></div></body></html>'
    )
    out = rewrite_purchase_copy(sample, ready)
    assert 'GỢI Ý SỐ NGÀY 16/08/2026' in out
    assert 'NHẬN GỢI Ý SỐ – 30.000Đ' in out
    assert 'Nhận gợi ý số ngày 16/08/2026' in out
    assert 'BÁO CÁO 4SO NGÀY 16/08/2026' not in out
    print('HOME_PORTAL_SAFE_SELF_TEST_OK')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', type=Path, default=portal.ROOT / '_site')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(apply(args.output_root), ensure_ascii=False))


if __name__ == '__main__':
    main()
