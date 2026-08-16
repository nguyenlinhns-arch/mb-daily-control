#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOPEE_SMARTLINK = "https://nguyenlinhtkv_aul4jx.accesslanding.site"
PRODUCTS = [
    {
        "name": "Tông đơ Philips MG3911/15 7in1",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mp1ohea3di4g9e",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773390&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vVCVDMyVCNG5nLSVDNCU5MSVDNiVBMS1QaGlsaXBzLU1HMzkxMS0xNS1NdWx0aWdyb29tLTMwMDAtN2luMS1jJUUxJUJBJUFGdC10JUUxJUJCJTg5YS1yJUMzJUEydS10JUMzJUIzYy0lQzQlOTFhLW4lQzQlODNuZy1zJUUxJUJCJUFELWQlRTElQkIlQTVuZy10JUUxJUJBJUExaS1uaCVDMyVBMC1pLjQ2MzYwMDA2MS40OTUxMTM1NzAxNw==&redirect_302=1",
    },
    {
        "name": "Sạc dự phòng Anker Zolo 20.000mAh 22.5W",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mlnj4c7kwkjp03",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773391&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vUyVFMSVCQSVBMWMtZCVFMSVCQiVCMS1waCVDMyVCMm5nLUFua2VyLVpvbG8tQTExMEQtMjAwMDBtQWgtY2h1JUUxJUJBJUE5bi0zQy1UcnVuZy1RdSVFMSVCQiU5MWMtYyVDMyVBMXAtVVNCLUMtdCVDMyVBRGNoLWglRTElQkIlQTNwLXMlRTElQkElQTFjLW5oYW5oLTIyLjVXLWkuMTIwMjg4OTY3OC40NTU1NDAxNDY3NQ==&redirect_302=1",
    },
    {
        "name": "Máy vặn vít pin Bosch GO 3",
        "image": "https://down-vn.img.susercontent.com/file/sg-11134201-8259d-mrbyk5d9m3gs2c",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773392&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktdiVFMSVCQSVCN24tdiVDMyVBRHQtcGluLUJvc2NoLUdvLTMtaS43NTgxMDI0OS4yNTUxNDU2ODgyOQ==&redirect_302=1",
    },
    {
        "name": "Máy hút bụi cầm tay Deerma DX118C 600W",
        "image": "https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m83aax7f0sasfe",
        "url": "https://go.isclix.com/deep_link/v5/6342443575996511342/4751584435713464237?utm_source=accesstrade&utm_content=oneat&ref=at-ldp&sub3=773393&sub4=oneatapp&sub5=landing-22508&url_enc=aHR0cHM6Ly9zaG9wZWUudm4vTSVDMyVBMXktSCVDMyVCQXQtQiVFMSVCQiVBNWktQyVFMSVCQSVBN20tVGF5LURlZXJtYS1EWDExOEMtJTI4QiVFMSVCQSVBMk4tTSVFMSVCQiU5QUktNjAwVyUyOS1DaCVDMyVBRG5oLWglQzMlQTNuZy1EZWVybWEtaS4yODE0MzI4NC4yNzQ1Nzg2MDQwNA==&redirect_302=1",
    },
]


def dmy(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def remove_section_by_marker(text: str, marker: str) -> str:
    pos = text.find(marker)
    if pos < 0:
        return text
    start = text.rfind("<section", 0, pos)
    end = text.find("</section>", pos)
    if start < 0 or end < 0:
        return text
    return text[:start] + text[end + len("</section>"):]


def section_bounds(text: str, marker: str) -> tuple[int, int] | None:
    pos = text.find(marker)
    if pos < 0:
        return None
    start = text.rfind("<section", 0, pos)
    end = text.find("</section>", pos)
    if start < 0 or end < 0:
        return None
    return start, end + len("</section>")


def first_section_bounds(text: str, markers: tuple[str, ...]) -> tuple[int, int] | None:
    for marker in markers:
        bounds = section_bounds(text, marker)
        if bounds:
            return bounds
    return None


def build_purchase(label: str) -> str:
    return f'''<section id="buy" class="buy-simple portal-buy lm-synced-purchase" data-final-purchase-surface="v1">
  <div class="portal-wrap lm-synced-purchase-wrap">
    <div class="portal-paid-card lm-synced-paid-card">
      <small>GỢI Ý SỐ HÔM NAY</small>
      <h2>Gợi ý số ngày hôm nay - {label}</h2>
      <div class="lm-returning-note">Gợi ý ngày {label} đã sẵn sàng · mở một lần · không cần tạo tài khoản.</div>
      <div class="portal-paid-lock" aria-label="Kết luận được khóa trước thanh toán">
        <div><span>TOP 1</span><b>•• — ••</b></div>
        <div><span>TOP 2</span><b>•• — ••</b></div>
      </div>
      <button class="button button-primary button-large" type="button" data-open-checkout aria-label="Mở gợi ý số ngày hôm nay {label}, giá 30.000 đồng">MỞ GỢI Ý SỐ HÔM NAY · 30.000Đ</button>
      <span class="lm-ai-runtime-kicker">Thanh toán một lần · Không tự gia hạn · Dữ liệu lịch sử không phải cam kết kết quả</span>
      <p class="portal-paid-note">Kết luận các số cuối cùng chỉ mở sau khi giao dịch được xác nhận.</p>
    </div>
  </div>
</section>'''


def build_strip() -> str:
    return f'''<section class="lm-primary-affiliate-strip lm-static-affiliate" data-primary-affiliate-strip="static-v3" aria-label="Ưu đãi mua sắm tài trợ ACCESSTRADE">
  <div class="lm-primary-affiliate-inner">
    <a class="lm-primary-affiliate-card" href="{SHOPEE_SMARTLINK}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-static-shopee-strip>
      <div><span class="lm-primary-affiliate-badge">Tài trợ · ACCESSTRADE</span><strong>Shopee · xem ưu đãi mua sắm hôm nay</strong><small>Mở Shopee để xem sản phẩm và ưu đãi đang có. Giá mua không tăng vì liên kết này.</small></div>
      <span class="lm-primary-affiliate-cta">XEM ƯU ĐÃI →</span>
    </a>
    <p class="lm-primary-affiliate-note">Website có thể nhận hoa hồng khi phát sinh giao dịch đủ điều kiện.</p>
  </div>
</section>'''


def build_products() -> str:
    cards = []
    for index, product in enumerate(PRODUCTS, start=1):
        cards.append(f'''<a class="lm-product-card" href="{product['url']}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-static-affiliate-product="{index}" data-product-name="{product['name']}"><div class="lm-product-image"><img src="{product['image']}" loading="lazy" decoding="async" alt="{product['name']}"></div><div class="lm-product-copy"><strong>{product['name']}</strong><span>Xem trên Shopee →</span></div></a>''')
    return '''<section class="lm-product-deals lm-static-product-grid" data-affiliate-static-placement="after_tools" aria-label="Sản phẩm Shopee qua ACCESSTRADE"><div class="lm-product-deals-inner"><div class="lm-product-deals-head"><div><span class="lm-product-deals-kicker">Tài trợ · ACCESSTRADE</span><h2>Sản phẩm Shopee đang giới thiệu</h2></div><small>4 sản phẩm · mở trực tiếp trên Shopee</small></div><div class="lm-product-deals-grid">''' + "".join(cards) + '''</div><p class="lm-product-disclosure">Liên kết đối tác · giá và ưu đãi xem trực tiếp trên Shopee.</p></div></section>'''


STYLE = '''<style id="lm-final-revenue-surface-style">
.lm-synced-purchase{padding:24px 0!important;background:#fff}.lm-synced-purchase-wrap{display:flex!important;justify-content:center!important}.lm-synced-paid-card{width:min(100%,520px)!important;box-sizing:border-box!important}.lm-synced-paid-card .lm-returning-note{margin:8px 0 10px!important}.lm-synced-paid-card .portal-paid-lock{margin:10px 0!important}.lm-synced-paid-card .lm-ai-runtime-kicker{display:block;margin-top:8px;color:#79575a;font-size:10px;font-weight:850;line-height:1.4}.lm-synced-paid-card .portal-paid-note{margin-top:8px!important}
.lm-primary-affiliate-strip{width:100%;padding:8px 0}.lm-primary-affiliate-inner{max-width:1180px;margin:auto;padding:0 16px}.lm-primary-affiliate-card{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:13px 14px;border:1px solid #f0d7cc;border-radius:14px;background:linear-gradient(135deg,#fff8f4,#fff);color:#263744!important;text-decoration:none!important;box-shadow:0 3px 14px rgba(39,29,24,.05)}.lm-primary-affiliate-badge{display:inline-flex;margin-bottom:3px;padding:3px 6px;border-radius:999px;background:#fff0e8;color:#b84b16;font-size:8px;font-weight:1000;letter-spacing:.07em;text-transform:uppercase}.lm-primary-affiliate-card strong{display:block;font-size:14px;line-height:1.25}.lm-primary-affiliate-card small{display:block;margin-top:3px;color:#71808a;font-size:10.5px;line-height:1.4}.lm-primary-affiliate-cta{display:flex;align-items:center;justify-content:center;min-height:42px;padding:0 13px;border-radius:10px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:1000;white-space:nowrap}.lm-primary-affiliate-note{margin:5px 2px 0;color:#929ba1;font-size:8.5px;line-height:1.35}
.lm-product-deals{width:100%;padding:8px 0}.lm-product-deals-inner{max-width:1180px;margin:auto;padding:0 16px}.lm-product-deals-head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:9px}.lm-product-deals-kicker{display:block;color:#ee4d2d;font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.lm-product-deals-head h2{margin:2px 0 0;color:#203542;font-size:19px;line-height:1.2}.lm-product-deals-head small{color:#84919a;font-size:10px;white-space:nowrap}.lm-product-deals-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.lm-product-card{min-width:0;overflow:hidden;border:1px solid #e7ebee;border-radius:14px;background:#fff;color:#243542!important;text-decoration:none!important;box-shadow:0 2px 9px rgba(24,42,54,.04)}.lm-product-image{aspect-ratio:1/1;background:#f6f7f8;overflow:hidden}.lm-product-image img{display:block;width:100%;height:100%;object-fit:cover}.lm-product-copy{padding:9px}.lm-product-copy strong{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2;min-height:36px;font-size:12px;line-height:1.45;color:#263946}.lm-product-copy span{display:flex;align-items:center;justify-content:center;min-height:38px;margin-top:8px;border-radius:9px;background:#ee4d2d;color:#fff;font-size:11px;font-weight:900}.lm-product-disclosure{margin:6px 1px 0;color:#929ca3;font-size:8.5px;line-height:1.35}
body:not([data-affiliate-checkout-open="true"]) .lm-static-affiliate,body:not([data-affiliate-checkout-open="true"]) .lm-static-product-grid{display:block!important;visibility:visible!important;opacity:1!important}body[data-affiliate-checkout-open="true"] .lm-static-affiliate,body[data-affiliate-checkout-open="true"] .lm-static-product-grid{display:none!important}
@media(max-width:700px){.lm-synced-purchase{padding:16px 0!important}.lm-synced-purchase-wrap{padding-left:10px!important;padding-right:10px!important}.lm-synced-paid-card{width:100%!important}.lm-primary-affiliate-strip{padding:6px 0}.lm-primary-affiliate-inner,.lm-product-deals-inner{padding:0 10px}.lm-primary-affiliate-card{grid-template-columns:1fr;gap:8px;padding:11px 12px}.lm-primary-affiliate-card strong{font-size:13px}.lm-primary-affiliate-card small{font-size:10px}.lm-primary-affiliate-cta{width:100%;min-height:44px}.lm-product-deals-grid{display:flex;gap:8px;overflow-x:auto;scroll-snap-type:x mandatory;padding:0 1px 4px;scrollbar-width:none}.lm-product-deals-grid::-webkit-scrollbar{display:none}.lm-product-card{flex:0 0 min(42vw,170px);scroll-snap-align:start}.lm-product-deals-head h2{font-size:17px}.lm-product-deals-head small{display:none}}
</style>'''

TRACK = '''<script id="lm-static-affiliate-track">(()=>{if(location.pathname!=="/")return;const push=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,affiliate_network:"ACCESSTRADE",...extra})};let stripViewed=false,gridViewed=false;const strip=document.querySelector("[data-static-shopee-strip]");const grid=document.querySelector(".lm-static-product-grid");const view=(node,event,extra)=>{if(!node)return;if(!("IntersectionObserver"in window)){push(event,extra);return;}const o=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting&&e.intersectionRatio>=.35)){push(event,extra);o.disconnect()}},{threshold:[.35]});o.observe(node)};if(strip&&!stripViewed){stripViewed=true;view(strip,"affiliate_shopee_strip_view",{merchant:"Shopee",placement:"after_results_static"})}if(grid&&!gridViewed){gridViewed=true;view(grid,"affiliate_product_grid_view",{merchant:"Shopee",placement:"after_tools_static"})}document.addEventListener("click",e=>{const t=e.target instanceof Element?e.target:null;if(!t)return;const s=t.closest("[data-static-shopee-strip]");if(s)push("affiliate_shopee_strip_click",{merchant:"Shopee",placement:"after_results_static"});const p=t.closest("[data-static-affiliate-product]");if(p)push("affiliate_product_click",{merchant:"Shopee",placement:"after_tools_static",product_index:Number(p.dataset.staticAffiliateProduct||0),product_name:p.dataset.productName||""})},true)})();</script>'''


def apply(root: Path) -> dict:
    page = root / "index.html"
    ready = load(root / "report-readiness.json")
    target = str(ready.get("report_date") or "")
    lock = str(ready.get("data_lock") or "")
    label = dmy(target)
    lock_label = dmy(lock)
    text = page.read_text(encoding="utf-8")

    # Replace the wide legacy purchase block with the same visual grammar as the hero offer card.
    buy = re.search(r'<section\b[^>]*class="[^"]*buy-simple\s+portal-buy[^"]*"[^>]*>.*?</section>', text, flags=re.I | re.S)
    if not buy:
        raise ValueError("legacy purchase block not found")
    text = text[:buy.start()] + build_purchase(label) + text[buy.end():]

    # Remove old static smartlink placements; runtime duplicates are prevented by the static markers below.
    text = remove_section_by_marker(text, 'id="affiliate-shopee-smartlink"')
    text = remove_section_by_marker(text, 'data-primary-affiliate-strip=')
    text = remove_section_by_marker(text, 'class="lm-product-deals')

    # Static Shopee strip immediately after the most stable result anchor available in the final artifact.
    results = first_section_bounds(text, (
        '27 mã kỳ gần nhất',
        'Kết quả XSMB',
        'portal-results',
        'portal-result-card',
    ))
    if not results:
        raise ValueError("results section not found for affiliate strip")
    _, result_end = results
    text = text[:result_end] + build_strip() + text[result_end:]

    # Static four-product grid immediately after the tools section.
    tools = first_section_bounds(text, ('<h2>Công cụ thống kê XSMB</h2>', 'Công cụ thống kê XSMB', 'portal-tools'))
    if not tools:
        raise ValueError("tools section not found for affiliate product grid")
    _, tools_end = tools
    text = text[:tools_end] + build_products() + text[tools_end:]

    if 'id="lm-final-revenue-surface-style"' not in text:
        text = text.replace('</head>', STYLE + '</head>', 1)
    text = re.sub(r'<script id="lm-static-affiliate-track">.*?</script>', '', text, flags=re.I | re.S)
    text = text.replace('</body>', TRACK + '</body>', 1)

    # Explicit contracts: synced paid card and ACCESSTRADE surfaces must be present.
    required = (
        f'Gợi ý số ngày hôm nay - {label}',
        'MỞ GỢI Ý SỐ HÔM NAY · 30.000Đ',
        'data-primary-affiliate-strip="static-v3"',
        'data-affiliate-static-placement="after_tools"',
        'Tông đơ Philips MG3911/15 7in1',
        'Sạc dự phòng Anker Zolo 20.000mAh 22.5W',
        'Máy vặn vít pin Bosch GO 3',
        'Máy hút bụi cầm tay Deerma DX118C 600W',
        'affiliate_shopee_strip_view',
        'affiliate_product_click',
    )
    for token in required:
        if token not in text:
            raise ValueError(f"final revenue surface missing: {token}")
    lower = text[text.find('data-final-purchase-surface="v1"'):text.find('data-final-purchase-surface="v1"') + 2600]
    for legacy in ('BẢN PHÂN TÍCH AI NGÀY', 'MỞ BẢN PHÂN TÍCH AI', 'Top 1–Top 2 được khóa'):
        if legacy in lower:
            raise ValueError(f"legacy lower purchase copy remains: {legacy}")

    page.write_text(text, encoding="utf-8")
    return {
        "status": "PASS",
        "report_date": target,
        "data_lock": lock,
        "display_date": label,
        "display_lock": lock_label,
        "purchase_synced": True,
        "shopee_strip_static": True,
        "shopee_product_grid_static": True,
        "product_count": 4,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    print(json.dumps(apply(args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
