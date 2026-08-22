#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date
from pathlib import Path

import hide_public_phone_numbers as phone_privacy
import optimize_portal_v2 as v2

COPY_LOCK_TAG = '<script defer src="/copy-lock.js?v=20260817-2"></script>'
COPY_LOCK_SOURCE = v2.ROOT / "site-v2" / "copy-lock.js"
AFFILIATE_RESTORE_TAG = '<script defer src="/affiliate-restore.js?v=20260816-1"></script>'
AFFILIATE_RESTORE_SOURCE = v2.ROOT / "site-v2" / "affiliate-restore.js"
CHECKOUT_ROUTE = "/?checkout=1"
SUPPORT_ZALO_ROUTE = "/go/zalo.htm"
ASSET_VERSION = "20260822-4"


def vi_date(value: str) -> str:
    parsed = date.fromisoformat(str(value))
    return parsed.strftime("%d/%m/%Y")


def normalize_daily_recommendation_heading(page: Path, target_date: str, data_lock: str) -> None:
    text = page.read_text(encoding="utf-8")
    target_label = vi_date(target_date)
    lock_label = vi_date(data_lock)
    heading = f"Gợi ý số ngày hôm nay - {target_label}"
    subtitle = (
        f"Gợi ý được tạo từ dữ liệu khóa đến ngày hôm qua ({lock_label}). "
        "Kết luận các số cuối cùng không nằm trong danh sách công khai này."
    )
    old = "<h2>Phương pháp công khai hôm nay</h2>"
    legacy = "<!-- CI legacy marker: Phương pháp công khai hôm nay -->"

    if old in text:
        text = text.replace(
            old,
            f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>{legacy}',
            1,
        )
    else:
        text, replaced = re.subn(
            r'<h2\b[^>]*data-daily-recommendation-heading="[^"]+"[^>]*>.*?</h2>',
            f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>',
            text,
            count=1,
            flags=re.I | re.S,
        )
        if replaced != 1:
            text, replaced = re.subn(
                r"<h2>\s*Gợi ý số.*?</h2>",
                f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>',
                text,
                count=1,
                flags=re.I | re.S,
            )
        if replaced != 1:
            raise ValueError("daily recommendation heading not found")

    heading_pos = text.find(heading)
    if heading_pos < 0:
        raise ValueError("exact daily recommendation heading missing")
    p_start = text.find("<p>", heading_pos)
    p_end = text.find("</p>", p_start)
    if p_start < 0 or p_end < 0:
        raise ValueError("daily recommendation subtitle not found")
    text = text[:p_start] + f"<p>{subtitle}</p>" + text[p_end + 4 :]

    visible_slice = text[heading_pos : heading_pos + 1200]
    if f"{target_label} · {target_label}" in visible_slice or "4SO không nằm trong danh sách công khai này" in visible_slice:
        raise ValueError("legacy or duplicated recommendation copy remains")
    if heading not in visible_slice or subtitle not in visible_slice:
        raise ValueError("exact public recommendation copy missing")
    page.write_text(text, encoding="utf-8")


def _replace_or_insert_returning_note(block: str, label: str) -> str:
    note = (
        f'<div class="lm-returning-note">Gợi ý ngày {label} đã sẵn sàng · '
        "30.000đ/ngày · xác nhận thanh toán qua email.</div>"
    )
    if re.search(r'<div class="lm-returning-note">.*?</div>', block, flags=re.I | re.S):
        return re.sub(
            r'<div class="lm-returning-note">.*?</div>',
            note,
            block,
            count=1,
            flags=re.I | re.S,
        )
    return block.replace("</h2>", "</h2>" + note, 1)


def normalize_paid_card_copy(page: Path, target_date: str) -> None:
    text = page.read_text(encoding="utf-8")
    label = vi_date(target_date)
    match = re.search(r'<aside class="portal-paid-card"[^>]*>.*?</aside>', text, flags=re.I | re.S)
    if not match:
        raise ValueError("portal suggestion card not found")

    block = match.group(0)
    block = re.sub(
        r'<aside class="portal-paid-card"[^>]*>',
        '<aside class="portal-paid-card" data-daily-offer-static="v4" data-paid-suggestion-card="true">',
        block,
        count=1,
        flags=re.I,
    )
    block = re.sub(r'\sdata-zalo-route="[^"]*"', "", block, flags=re.I)
    block = re.sub(r'\sdata-zalo-suggestion-card="[^"]*"', "", block, flags=re.I)
    block = re.sub(
        r"<small>[^<]*</small>",
        "<small>THANH TOÁN NHẬN GỢI Ý SỐ</small>",
        block,
        count=1,
        flags=re.I,
    )
    block = re.sub(
        r"<h2>.*?</h2>",
        f"<h2>Gợi ý số MB_ALL - {label}</h2>",
        block,
        count=1,
        flags=re.I | re.S,
    )
    block = _replace_or_insert_returning_note(block, label)
    block = re.sub(
        r'<button\b([^>]*\bdata-open-checkout\b[^>]*)>.*?</button>',
        r'<button\1>THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>',
        block,
        count=1,
        flags=re.I | re.S,
    )

    runtime_note = (
        '<span class="lm-ai-runtime-kicker">30.000đ/ngày · Không tự gia hạn · '
        "Sau khi chuyển khoản, hệ thống gửi email để chủ dịch vụ xác nhận.</span>"
    )
    if re.search(r'<span class="lm-ai-runtime-kicker">.*?</span>', block, flags=re.I | re.S):
        block = re.sub(
            r'<span class="lm-ai-runtime-kicker">.*?</span>',
            runtime_note,
            block,
            count=1,
            flags=re.I | re.S,
        )
    else:
        block = re.sub(
            r"(</button>)",
            r"\1" + runtime_note,
            block,
            count=1,
            flags=re.I,
        )

    paid_note = (
        '<p class="portal-paid-note">Gợi ý số chỉ mở sau khi giao dịch được xác nhận qua email. '
        "Zalo chỉ dùng để hỗ trợ.</p>"
    )
    if re.search(r'<p class="portal-paid-note">.*?</p>', block, flags=re.I | re.S):
        block = re.sub(
            r'<p class="portal-paid-note">.*?</p>',
            paid_note,
            block,
            count=1,
            flags=re.I | re.S,
        )
    else:
        block = block.replace("</aside>", paid_note + "</aside>", 1)

    if (
        "THANH TOÁN NHẬN GỢI Ý SỐ" not in block
        or "30.000đ/ngày" not in block
        or "email" not in block.lower()
        or "MỞ ZALO" in block.upper()
    ):
        raise ValueError("paid daily suggestion card copy is incomplete")

    text = text[: match.start()] + block + text[match.end() :]
    page.write_text(text, encoding="utf-8")


def _rewrite_purchase_links(text: str) -> str:
    def replace_link(match: re.Match[str]) -> str:
        attrs_before = match.group(1)
        href = match.group(2)
        attrs_after = match.group(3)
        body = match.group(4)
        visible = re.sub(r"<[^>]+>", " ", body)
        if not re.search(r"gợi ý|báo cáo|4so|thanh toán|zalo", visible, flags=re.I):
            return match.group(0)
        attrs = (attrs_before + attrs_after)
        attrs = re.sub(r'\sdata-zalo-route="[^"]*"', "", attrs, flags=re.I)
        attrs = re.sub(r'\starget="_blank"', "", attrs, flags=re.I)
        attrs = re.sub(r'\srel="[^"]*"', "", attrs, flags=re.I)
        return f'<a{attrs} href="{CHECKOUT_ROUTE}">Thanh toán nhận gợi ý số</a>'

    return re.sub(
        r'<a\b([^>]*?)href="([^"]*(?:go/zalo|checkout=1)[^"]*)"([^>]*)>(.*?)</a>',
        replace_link,
        text,
        flags=re.I | re.S,
    )


def _round_support_markup() -> str:
    return (
        '<a id="mball-zalo-support" class="mball-zalo-support-button" '
        f'href="{SUPPORT_ZALO_ROUTE}" target="_blank" rel="noopener noreferrer" '
        'aria-label="Hỗ trợ qua Zalo">Hỗ trợ</a>'
    )


def _round_support_style() -> str:
    return """<style id="mball-round-support-style">
#mball-zalo-support{position:fixed!important;right:18px!important;bottom:20px!important;z-index:2147483000!important;width:74px!important;height:74px!important;box-sizing:border-box!important;display:flex!important;align-items:center!important;justify-content:center!important;padding:0!important;border:4px solid #fff!important;border-radius:50%!important;background:linear-gradient(145deg,#1780ff,#0068ff)!important;color:#fff!important;text-decoration:none!important;text-align:center!important;font-size:12px!important;font-weight:1000!important;line-height:1.05!important;box-shadow:0 12px 28px rgba(0,74,190,.32)!important}
#mball-zalo-support::before{content:"Zalo";display:block;position:absolute;top:15px;font-size:12px;font-weight:1000}
#mball-zalo-support{padding-top:18px!important}
@media(max-width:700px){#mball-zalo-support{right:12px!important;bottom:72px!important;width:66px!important;height:66px!important;border-width:3px!important;font-size:10.5px!important}#mball-zalo-support::before{top:13px;font-size:11px}}
</style>"""


def normalize_home_paid_checkout(page: Path, target_date: str) -> None:
    text = page.read_text(encoding="utf-8")
    label = vi_date(target_date)

    text = re.sub(
        r'<script\s+id="lm-zalo-suggestion-route">.*?</script>',
        "",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r'\sdata-zalo-route="[^"]*"', "", text, flags=re.I)
    text = re.sub(r'\sdata-zalo-suggestion-card="[^"]*"', "", text, flags=re.I)
    text = _rewrite_purchase_links(text)

    replacements = (
        ("MỞ ZALO – NHẬN GỢI Ý HÔM NAY", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ"),
        ("MỞ ZALO - NHẬN GỢI Ý HÔM NAY", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ"),
        ("GỢI Ý SỐ HÔM NAY · MỞ ZALO", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ"),
        ("mở Zalo để trao đổi", "thanh toán 30.000đ để mở"),
        ("Mở Zalo để trao đổi", "Thanh toán 30.000đ để mở"),
        ("Bấm nút để mở Zalo và trao đổi trực tiếp về gợi ý trong ngày.", "Thanh toán 30.000đ để nhận gợi ý số đã khóa cho đúng ngày hiện tại."),
        ("Trao đổi trực tiếp qua Zalo", "Xác nhận thanh toán qua email"),
        ("Bấm nút bên dưới để mở Zalo.", "Sau khi chuyển khoản, bấm gửi xác nhận để hệ thống báo qua email."),
    )
    for old, new in replacements:
        text = text.replace(old, new)

    def normalize_button(match: re.Match[str]) -> str:
        attrs = re.sub(r'\sdata-zalo-route="[^"]*"', "", match.group(1), flags=re.I)
        return f'<button{attrs}>THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>'

    text = re.sub(
        r'<button\b([^>]*\bdata-open-checkout\b[^>]*)>.*?</button>',
        normalize_button,
        text,
        flags=re.I | re.S,
    )

    buy = re.search(r'<section class="buy-simple portal-buy"[^>]*>.*?</section>', text, flags=re.I | re.S)
    if buy:
        replacement = f'''<section class="buy-simple portal-buy" id="buy" data-paid-suggestion-section="true">
      <div class="wrap buy-simple-card">
        <div><p class="eyebrow">THANH TOÁN NHẬN GỢI Ý SỐ</p><h2>30.000đ/ngày</h2><p class="buy-copy">Thanh toán một lần để nhận gợi ý số MB_ALL đã khóa cho ngày {label}.</p><p class="checkout-scope" id="checkout-scope">Gợi ý ngày {label} · dữ liệu khóa T−1 · không tự gia hạn.</p></div>
        <div><strong>Xác nhận thanh toán qua email</strong><p>Sau khi chuyển khoản, bấm gửi xác nhận. Chủ dịch vụ kiểm tra giao dịch qua email và gợi ý số tự mở sau khi được phê duyệt.</p></div>
        <button class="button button-primary button-large" type="button" data-open-checkout>THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>
      </div>
      <p class="buy-legal">Thanh toán một lần · Không tự gia hạn · Zalo chỉ dùng để hỗ trợ · Không nhận cược · Không trả thưởng.</p>
    </section>'''
        text = text[: buy.start()] + replacement + text[buy.end() :]

    trust = re.search(
        r'<section class="lm-value-strip"[^>]*data-ai-commerce-trust="true"[^>]*>.*?</section>',
        text,
        flags=re.I | re.S,
    )
    if trust:
        replacement = f'''<section class="lm-value-strip" data-ai-commerce-trust="true"><div class="lm-value-strip-inner">
<div class="lm-value-item"><span class="lm-value-icon">✓</span><div><b>Dữ liệu khóa T−1</b><span>Phân tích chỉ dùng dữ liệu đã hoàn tất trước ngày {label}.</span></div></div>
<div class="lm-value-item"><span class="lm-value-icon">31</span><div><b>Chạy đủ 31 phương pháp</b><span>Đánh giá hiệu quả gần và chọn số động trước giờ quay.</span></div></div>
<div class="lm-value-item"><span class="lm-value-icon">₫</span><div><b>30.000đ/ngày</b><span>Xác nhận thanh toán qua email; không tự gia hạn.</span></div></div>
</div></section>'''
        text = text[: trust.start()] + replacement + text[trust.end() :]

    text = re.sub(
        r'<a class="lm-ai-sticky"[^>]*data-ai-sticky-cta="true"[^>]*>.*?</a>',
        '<a class="lm-ai-sticky" href="#buy" data-ai-sticky-cta="true" aria-label="Thanh toán nhận gợi ý số, giá 30.000 đồng">THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</a>',
        text,
        count=1,
        flags=re.I | re.S,
    )

    text = re.sub(
        r'<a\b[^>]*(?:id="mball-zalo-support"|class="[^"]*floating-zalo[^"]*")[^>]*>.*?</a>',
        "",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r'<style\s+id="mball-round-support-style">.*?</style>', "", text, flags=re.I | re.S)
    if "</head>" not in text or "</body>" not in text:
        raise ValueError("homepage head/body end missing")
    text = text.replace("</head>", _round_support_style() + "</head>", 1)
    text = text.replace("</body>", _round_support_markup() + "</body>", 1)

    text = re.sub(r'config\.js\?v=[^"\']+', f"config.js?v={ASSET_VERSION}", text, flags=re.I)
    text = re.sub(r'checkout-entry\.js\?v=[^"\']+', f"checkout-entry.js?v={ASSET_VERSION}", text, flags=re.I)
    text = re.sub(r'checkout-enhance\.js\?v=[^"\']+', f"checkout-enhance.js?v={ASSET_VERSION}", text, flags=re.I)

    purchase_slice = text[text.find('data-paid-suggestion-card="true"') : text.find('data-paid-suggestion-card="true"') + 2400]
    lower_slice = text[text.find('data-paid-suggestion-section="true"') : text.find('data-paid-suggestion-section="true"') + 2600]
    if not purchase_slice or "THANH TOÁN NHẬN GỢI Ý SỐ" not in purchase_slice:
        raise ValueError("top paid suggestion card is missing")
    if not lower_slice or "Xác nhận thanh toán qua email" not in lower_slice:
        raise ValueError("lower paid suggestion section is missing")
    if "MỞ ZALO" in purchase_slice.upper() or "MỞ ZALO" in lower_slice.upper():
        raise ValueError("purchase CTA still routes to Zalo")
    if "data-open-checkout" not in purchase_slice or "data-open-checkout" not in lower_slice:
        raise ValueError("paid checkout button marker is missing")
    if SUPPORT_ZALO_ROUTE not in text or 'id="mball-zalo-support"' not in text:
        raise ValueError("separate Zalo support button is missing")

    page.write_text(text, encoding="utf-8")


# Backward-compatible function name retained for callers outside this script.
def normalize_home_zalo_routes(page: Path, target_date: str) -> None:
    normalize_home_paid_checkout(page, target_date)


def install_runtime_locks(root: Path) -> None:
    if not COPY_LOCK_SOURCE.is_file():
        raise FileNotFoundError("copy-lock.js source missing")
    if not AFFILIATE_RESTORE_SOURCE.is_file():
        raise FileNotFoundError("affiliate-restore.js source missing")
    shutil.copy2(COPY_LOCK_SOURCE, root / "copy-lock.js")
    shutil.copy2(AFFILIATE_RESTORE_SOURCE, root / "affiliate-restore.js")
    page = root / "index.html"
    text = page.read_text(encoding="utf-8")
    text = re.sub(r'<script defer src="/copy-lock\.js\?v=[^"]+"></script>', "", text)
    text = re.sub(r'<script defer src="/affiliate-restore\.js\?v=[^"]+"></script>', "", text)
    if "</body>" not in text:
        raise ValueError("homepage body end missing for runtime locks")
    text = text.replace("</body>", COPY_LOCK_TAG + AFFILIATE_RESTORE_TAG + "</body>", 1)
    if AFFILIATE_RESTORE_TAG not in text:
        raise ValueError("affiliate restore runtime missing")
    page.write_text(text, encoding="utf-8")


def apply(root: Path):
    stats = v2.load(root / "statistics-data.json")
    methods = v2.load(v2.METHODS_PATH)
    public_methods = methods.get("methods") or []
    if stats.get("updated_through") != methods.get("data_lock"):
        raise ValueError("stats/method lock mismatch")
    target_date = str(methods.get("target_date") or "")
    data_lock = str(methods.get("data_lock") or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_date):
        raise ValueError("invalid public method target_date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data_lock):
        raise ValueError("invalid public method data_lock")

    v2.patch_home(root / "index.html", public_methods)
    normalize_daily_recommendation_heading(root / "index.html", target_date, data_lock)
    normalize_paid_card_copy(root / "index.html", target_date)
    normalize_home_paid_checkout(root / "index.html", target_date)

    (root / "phuong-phap-cong-khai").mkdir(exist_ok=True)
    (root / "phuong-phap-cong-khai/index.html").write_text(
        v2.build_methods_page(methods), encoding="utf-8"
    )
    (root / "thong-ke-dau-duoi-xsmb").mkdir(exist_ok=True)
    (root / "thong-ke-dau-duoi-xsmb/index.html").write_text(
        v2.build_headtail_page(stats), encoding="utf-8"
    )
    v2.externalize_stats(root)
    for path in root.rglob("*.html"):
        path.write_text(v2.add_assets(path.read_text(encoding="utf-8")), encoding="utf-8")

    install_runtime_locks(root)
    privacy = phone_privacy.sanitize(root)
    v2.update_sitemap(root, str(stats["updated_through"]))
    return {
        "status": "PASS",
        "updated_through": stats["updated_through"],
        "target_date": target_date,
        "data_lock": data_lock,
        "daily_recommendation_heading": True,
        "daily_recommendation_subtitle": True,
        "daily_offer_static": True,
        "paid_checkout": True,
        "email_confirmation": True,
        "price": 30000,
        "zalo_route": SUPPORT_ZALO_ROUTE,
        "zalo_support_only": True,
        "phone_privacy": privacy["status"],
        "copy_lock": True,
        "affiliate_restore": True,
        "new_pages": 2,
        "consensus": len(v2.method_consensus(public_methods)),
        "stats_assets_externalized": 5,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=v2.ROOT / "_site")
    args = parser.parse_args()
    print(json.dumps(apply(args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
