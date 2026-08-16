#!/usr/bin/env python3
"""Finalize the portal homepage, strengthen the daily AI funnel and sanitize public 4SO surfaces."""
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

    replacements = (
        (f'<p class="eyebrow">BÁO CÁO 4SO NGÀY {label}</p>', f'<p class="eyebrow">BẢN PHÂN TÍCH AI NGÀY {label}</p>'),
        (f'Mở đúng một báo cáo 4SO cho ngày {label} sau khi giao dịch được xác nhận.', f'Mở bản phân tích AI ngày {label} sau khi giao dịch được xác nhận.'),
        (f'01 báo cáo ngày {label}', f'Bản phân tích AI ngày {label}'),
        ('NHẬN BÁO CÁO 4SO – 30.000Đ', 'MỞ BẢN PHÂN TÍCH AI – 30.000Đ'),
        (f'NHẬN BÁO CÁO NGÀY {label}', f'BẢN PHÂN TÍCH AI NGÀY {label}'),
        (f'Nhận báo cáo AI ngày {label}', f'Mở bản phân tích AI ngày {label}'),
        ('NHẬN BÁO CÁO NGÀY HÔM NAY', f'BẢN PHÂN TÍCH AI NGÀY {label}'),
        ('Nhận báo cáo AI ngày hôm nay', f'Mở bản phân tích AI ngày {label}'),
        ('01 báo cáo ngày hôm nay', f'Bản phân tích AI ngày {label}'),
        ('Giao dịch được xác nhận, báo cáo mở trên màn hình', 'Giao dịch được xác nhận, bản phân tích mở trên màn hình'),
        ('Báo cáo sẽ tự mở trên màn hình khi giao dịch được xác nhận.', 'Bản phân tích sẽ tự mở trên màn hình khi giao dịch được xác nhận.'),
        ('TÔI ĐÃ CHUYỂN KHOẢN – YÊU CẦU NHẬN BÁO CÁO', 'TÔI ĐÃ CHUYỂN KHOẢN – MỞ BẢN PHÂN TÍCH AI'),
        ('NHẬN GỢI Ý SỐ – 30.000Đ', 'MỞ BẢN PHÂN TÍCH AI – 30.000Đ'),
    )
    for old, new in replacements:
        content = content.replace(old, new)

    buy = re.search(r'<section class="buy-simple portal-buy"[^>]*>.*?</section>', content, flags=re.I | re.S)
    if not buy:
        raise ValueError("Purchase block missing after portal build")
    block = buy.group(0)
    if f'BẢN PHÂN TÍCH AI NGÀY {label}' not in block or 'MỞ BẢN PHÂN TÍCH AI – 30.000Đ' not in block:
        raise ValueError("Explicit daily AI product copy missing from purchase block")
    if 'BÁO CÁO 4SO NGÀY' in block:
        raise ValueError("Legacy purchase wording remains in purchase block")
    return content


def enhance_commerce(content: str, ready: dict[str, object], proof: dict[str, object]) -> str:
    target = str(ready.get("report_date") or "")
    lock = str(ready.get("data_lock") or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lock):
        raise ValueError("Invalid commerce target/data lock")
    label = portal.dmy(target)
    lock_label = portal.dmy(lock)
    validation = proof.get("validation") or {}
    hit_days = int(validation.get("hit_days") or 0)
    total_days = int(validation.get("total_days") or 0)
    rate_pct = int(validation.get("rate_pct") or 0)
    if total_days <= 0 or round(hit_days * 100 / total_days) != rate_pct:
        raise ValueError("Historical validation is inconsistent")

    style = '''<style id="lm-commerce-v2-style">
.lm-value-strip{background:#fff;border-bottom:1px solid #e4e8ec}.lm-value-strip-inner{max-width:1180px;margin:auto;padding:10px 16px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.lm-value-item{display:flex;gap:9px;align-items:center;padding:10px 11px;border:1px solid #e4e8ec;border-radius:12px;background:#fafbfc}.lm-value-icon{width:32px;height:32px;flex:0 0 32px;display:grid;place-items:center;border-radius:10px;background:#f4e9e9;color:#aa1419;font-weight:1000}.lm-value-item b{display:block;color:#182735;font-size:12px}.lm-value-item span{display:block;margin-top:1px;color:#6e7c86;font-size:10px;line-height:1.35}
.lm-ai-commerce-proof{margin:14px 0 2px;padding:14px;border:1px solid #e5d4d5;border-radius:14px;background:linear-gradient(135deg,#fffafa,#fff)}.lm-ai-commerce-proof h3{margin:0 0 3px;color:#172432;font-size:16px}.lm-ai-commerce-proof>p{margin:0 0 10px;color:#66747f;font-size:11.5px}.lm-ai-commerce-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.lm-ai-commerce-grid div{padding:10px;border:1px solid #ebe4e4;border-radius:10px;background:#fff}.lm-ai-commerce-grid b{display:block;color:#a51017;font-size:13px}.lm-ai-commerce-grid span{display:block;margin-top:2px;color:#6a7781;font-size:10.5px;line-height:1.4}.lm-ai-history-note{margin:9px 0 0!important;color:#7b696a!important;font-size:9.5px!important;line-height:1.45}.lm-ai-history-note strong{color:#93434a}.lm-ai-secondary-link{display:inline-flex;margin-top:9px;color:#8e1117!important;font-size:11px;font-weight:900;text-decoration:none!important}
.lm-ai-sticky{display:none}.lm-sponsored-copy{letter-spacing:.055em;text-transform:uppercase}
@media(max-width:700px){.lm-value-strip-inner{padding:8px 10px;grid-template-columns:1fr;gap:5px}.lm-value-item{padding:8px 9px}.lm-value-icon{width:29px;height:29px;flex-basis:29px}.lm-ai-commerce-proof{padding:11px;margin-top:10px}.lm-ai-commerce-grid{grid-template-columns:1fr;gap:5px}.lm-ai-commerce-grid div{padding:8px 9px}.lm-ai-sticky{position:fixed;left:10px;right:10px;bottom:64px;z-index:75;min-height:48px;display:flex;align-items:center;justify-content:center;border:1px solid rgba(255,255,255,.55);border-radius:14px;background:linear-gradient(135deg,#991017,#bd171d);color:#fff!important;text-decoration:none!important;font-size:12px;font-weight:1000;box-shadow:0 14px 36px rgba(82,7,12,.28)}body.checkout-open .lm-ai-sticky{display:none}}
@media(prefers-reduced-motion:reduce){.lm-ai-sticky{scroll-behavior:auto}}
</style>'''
    if 'id="lm-commerce-v2-style"' not in content:
        content = content.replace('</head>', style + '</head>', 1)

    trust = f'''<section class="lm-value-strip" data-ai-commerce-trust="true"><div class="lm-value-strip-inner">
<div class="lm-value-item"><span class="lm-value-icon">✓</span><div><b>Dữ liệu khóa T−1</b><span>Đã hoàn tất đến {lock_label}; không dùng kết quả ngày {label} khi tạo bản phân tích.</span></div></div>
<div class="lm-value-item"><span class="lm-value-icon">27</span><div><b>Đủ 27/27 mã mỗi kỳ</b><span>Nguồn công khai được đối chiếu trước khi cập nhật thống kê và báo cáo.</span></div></div>
<div class="lm-value-item"><span class="lm-value-icon">₫</span><div><b>30.000đ một lần</b><span>Không tự gia hạn. Chỉ mở đúng bản phân tích của ngày {label}.</span></div></div>
</div></section>'''
    if 'data-ai-commerce-trust="true"' not in content:
        hero = re.search(r'<section\b[^>]*class="[^"]*portal-hero[^"]*"[^>]*>.*?</section>', content, flags=re.I | re.S)
        if not hero:
            raise ValueError("Portal hero missing for commerce trust strip")
        content = content[:hero.end()] + trust + content[hero.end():]

    proof_block = f'''<div class="lm-ai-commerce-proof" data-ai-product-proof="true"><h3>Bạn đang mua gì?</h3><p>Một bản phân tích dữ liệu AI riêng cho ngày {label}, được tạo sau khi khóa dữ liệu đến {lock_label}.</p><div class="lm-ai-commerce-grid"><div><b>Phân tích nhiều lớp</b><span>Tổng hợp các tín hiệu dữ liệu và phần kết luận riêng trong cùng một bản.</span></div><div><b>Mở sau xác nhận</b><span>Thanh toán một lần; bản phân tích mở ngay trên màn hình sau khi giao dịch được xác nhận.</span></div><div><b>Có hồ sơ đối chiếu</b><span>Thống kê lịch sử hiển thị cả ngày có và không có đầu ra xuất hiện.</span></div></div><p class="lm-ai-history-note"><strong>Đối chiếu lịch sử:</strong> {hit_days}/{total_days} ngày trong cửa sổ kiểm tra gần nhất có ít nhất một đầu ra đã lưu xuất hiện ({rate_pct}%). Đây là mô tả lịch sử, không phải xác suất hay cam kết cho ngày {label}.</p><a class="lm-ai-secondary-link" href="/thong-ke-xsmb/">Xem thống kê miễn phí trước khi mua →</a></div>'''
    if 'data-ai-product-proof="true"' not in content:
        buy = re.search(r'<section class="buy-simple portal-buy"[^>]*>.*?</section>', content, flags=re.I | re.S)
        if not buy:
            raise ValueError("Purchase block missing for product proof")
        block = buy.group(0)
        block = block.replace('</section>', proof_block + '</section>', 1)
        content = content[:buy.start()] + block + content[buy.end():]

    sticky = f'<a class="lm-ai-sticky" href="#buy" data-ai-sticky-cta="true" aria-label="Mở bản phân tích AI ngày {label}, giá 30.000 đồng">MỞ BẢN PHÂN TÍCH AI · 30.000Đ</a>'
    if 'data-ai-sticky-cta="true"' not in content:
        content = content.replace('</body>', sticky + '</body>', 1)

    script = '''<script id="lm-commerce-v2-track">(()=>{const push=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,...extra})};document.addEventListener('click',e=>{const checkout=e.target.closest('[data-open-checkout]');if(checkout)push('ai_checkout_intent',{placement:checkout.closest('.portal-paid-card')?'hero':'purchase'});const sticky=e.target.closest('[data-ai-sticky-cta]');if(sticky)push('ai_sticky_click',{placement:'mobile_sticky'});});})();</script>'''
    if 'id="lm-commerce-v2-track"' not in content:
        content = content.replace('</body>', script + '</body>', 1)
    return content


def apply(output_root: Path) -> dict[str, object]:
    page = output_root / "index.html"
    stats_path = output_root / "statistics-data.json"
    if not page.exists() or not stats_path.exists():
        raise FileNotFoundError("Homepage or statistics-data.json missing")

    ready = portal.load_json(portal.PAID_READY)
    proof = portal.load_json(portal.PUBLIC_PROOF)
    result = portal.build_home(
        page.read_text(encoding="utf-8"),
        portal.load_json(stats_path),
        portal.load_json(portal.PUBLIC_METHODS),
        proof,
        ready,
    )
    result = rewrite_purchase_copy(result, ready)
    result = enhance_commerce(result, ready, proof)

    buttons = re.findall(r'<button\b[^>]*\bdata-open-checkout\b[^>]*>', result, flags=re.I)
    if len(buttons) != 2:
        raise ValueError(f"Homepage must contain exactly two checkout buttons, found {len(buttons)}")
    if 'data-home-portal="v1"' not in result or 'Phương pháp công khai hôm nay' not in result:
        raise ValueError("Portal homepage markers missing")
    if 'data-ai-commerce-trust="true"' not in result or 'data-ai-product-proof="true"' not in result:
        raise ValueError("Commerce trust/product proof layer missing")
    if re.search(r'4SO[^<]{0,180}\b\d{2}\b\s*[-–—]\s*\b\d{2}\b', result, flags=re.I):
        raise ValueError("Potential current 4SO pair leaked in homepage")

    page.write_text(result, encoding="utf-8")
    privacy = fourso_privacy.sanitize(output_root)

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
        "homepage": "portal-v1-commerce-v2",
        "checkout_buttons": 2,
        "purchase_copy": f"Bản phân tích AI ngày {portal.dmy(str(ready['report_date']))}",
        "commerce_trust": True,
        "mobile_sticky": True,
        "fourso_public_mode": privacy["mode"],
    }


def self_test() -> None:
    ready = {"report_date": "2026-08-16", "data_lock": "2026-08-15"}
    sample = ('<html><head></head><body><section class="portal-hero"><h1>X</h1></section>'
              '<section class="buy-simple portal-buy" id="buy"><p class="eyebrow">BÁO CÁO 4SO NGÀY 16/08/2026</p>'
              '<p>Mở đúng một báo cáo 4SO cho ngày 16/08/2026 sau khi giao dịch được xác nhận.</p><p>01 báo cáo ngày 16/08/2026</p>'
              '<button>NHẬN BÁO CÁO 4SO – 30.000Đ</button></section></body></html>')
    proof = {"validation": {"hit_days": 21, "total_days": 30, "rate_pct": 70}}
    out = rewrite_purchase_copy(sample, ready)
    out = enhance_commerce(out, ready, proof)
    assert 'BẢN PHÂN TÍCH AI NGÀY 16/08/2026' in out
    assert 'MỞ BẢN PHÂN TÍCH AI – 30.000Đ' in out
    assert 'data-ai-commerce-trust="true"' in out
    assert 'data-ai-product-proof="true"' in out
    assert 'data-ai-sticky-cta="true"' in out
    assert '21/30 ngày' in out
    assert 'BÁO CÁO 4SO NGÀY 16/08/2026' not in out
    print('HOME_PORTAL_SAFE_COMMERCE_V2_SELF_TEST_OK')


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
