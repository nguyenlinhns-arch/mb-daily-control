#!/usr/bin/env python3
from pathlib import Path

p = Path('site-v2/checkout-enhance.js')
t = p.read_text(encoding='utf-8')

old = '''.lm-shopee-nudge-card{display:grid;grid-template-columns:minmax(0,1fr) auto 32px;gap:8px;align-items:center;padding:9px 9px 9px 12px;border:1px solid #f2c8bb;border-radius:14px;background:#fff;box-shadow:0 10px 30px rgba(30,38,44,.2)}
        .lm-shopee-nudge-copy{min-width:0}.lm-shopee-nudge-kicker{display:block;color:#ee4d2d;font-size:9px;font-weight:900;letter-spacing:.04em;text-transform:uppercase}.lm-shopee-nudge-copy strong{display:block;overflow:hidden;margin-top:1px;color:#263946;font-size:12px;line-height:1.25;text-overflow:ellipsis;white-space:nowrap}
        .lm-shopee-nudge-cta{min-height:40px;padding:0 11px;border-radius:9px;display:flex;align-items:center;justify-content:center;background:#ee4d2d;color:#fff!important;text-decoration:none!important;font-size:11px;font-weight:900;white-space:nowrap}
        .lm-shopee-nudge-close{width:32px;height:32px;border:0;border-radius:50%;background:#f1f3f5;color:#5b6870;font-size:19px;line-height:1;cursor:pointer}
        @media(max-width:700px){.lm-shopee-nudge{left:8px;right:8px;bottom:calc(66px + env(safe-area-inset-bottom,0px));width:auto;transform:translateY(18px)}.lm-shopee-nudge.is-visible{transform:translateY(0)}.lm-shopee-nudge-card{grid-template-columns:minmax(0,1fr) auto 30px;gap:6px;padding:8px 7px 8px 10px;border-radius:12px}.lm-shopee-nudge-kicker{font-size:8.5px}.lm-shopee-nudge-copy strong{font-size:11px}.lm-shopee-nudge-cta{min-height:38px;padding:0 9px;font-size:10.5px}.lm-shopee-nudge-close{width:30px;height:30px}}'''

new = '''.lm-shopee-nudge-card{display:grid;grid-template-columns:66px minmax(0,1fr) 32px;gap:9px;align-items:center;padding:8px;border:1px solid #f2c8bb;border-radius:15px;background:#fff;box-shadow:0 12px 34px rgba(30,38,44,.22)}
        .lm-shopee-nudge-image{width:66px;height:66px;overflow:hidden;border-radius:11px;background:#f6f7f8}.lm-shopee-nudge-image img{display:block;width:100%;height:100%;object-fit:cover}
        .lm-shopee-nudge-copy{min-width:0}.lm-shopee-nudge-kicker{display:block;color:#ee4d2d;font-size:9px;font-weight:1000;letter-spacing:.04em;text-transform:uppercase}.lm-shopee-nudge-copy strong{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2;margin-top:2px;color:#263946;font-size:12px;line-height:1.25}.lm-shopee-nudge-cta{min-height:36px;margin-top:6px;padding:0 10px;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;background:#ee4d2d;color:#fff!important;text-decoration:none!important;font-size:10.5px;font-weight:1000;white-space:nowrap}
        .lm-shopee-nudge-close{width:32px;height:32px;border:0;border-radius:50%;background:#f1f3f5;color:#5b6870;font-size:19px;line-height:1;cursor:pointer}
        @media(max-width:700px){.lm-shopee-nudge{left:8px;right:8px;bottom:calc(66px + env(safe-area-inset-bottom,0px));width:auto;transform:translateY(18px)}.lm-shopee-nudge.is-visible{transform:translateY(0)}.lm-shopee-nudge-card{grid-template-columns:58px minmax(0,1fr) 30px;gap:7px;padding:7px;border-radius:13px}.lm-shopee-nudge-image{width:58px;height:58px;border-radius:10px}.lm-shopee-nudge-kicker{font-size:8px}.lm-shopee-nudge-copy strong{font-size:10.8px}.lm-shopee-nudge-cta{min-height:34px;margin-top:5px;padding:0 8px;font-size:10px}.lm-shopee-nudge-close{width:30px;height:30px}}'''

if old not in t:
    raise SystemExit('old Shopee nudge CSS not found')
t = t.replace(old, new, 1)

old_html = '''      <div class="lm-shopee-nudge-card">
        <div class="lm-shopee-nudge-copy"><span class="lm-shopee-nudge-kicker">🔥 Deal Shopee hôm nay</span><strong>${product.name}</strong></div>
        <a class="lm-shopee-nudge-cta" href="${product.url}" target="_blank" rel="sponsored noopener noreferrer">Xem deal →</a>
        <button class="lm-shopee-nudge-close" type="button" aria-label="Đóng deal Shopee">×</button>
      </div>'''

new_html = '''      <div class="lm-shopee-nudge-card">
        <div class="lm-shopee-nudge-image"><img src="${product.image}" alt="" loading="lazy" decoding="async"></div>
        <div class="lm-shopee-nudge-copy"><span class="lm-shopee-nudge-kicker">🔥 Deal cho nam hôm nay</span><strong>${product.name}</strong><a class="lm-shopee-nudge-cta" href="${product.url}" target="_blank" rel="sponsored noopener noreferrer">Xem giá trên Shopee →</a></div>
        <button class="lm-shopee-nudge-close" type="button" aria-label="Đóng deal Shopee">×</button>
      </div>'''

if old_html not in t:
    raise SystemExit('old Shopee nudge HTML not found')
t = t.replace(old_html, new_html, 1)
p.write_text(t, encoding='utf-8')
print('SHOPEE_NUDGE_CREATIVE_PATCHED')
