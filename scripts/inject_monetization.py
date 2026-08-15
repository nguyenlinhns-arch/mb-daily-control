#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

SMARTLINK = "https://nguyenlinhtkv_aul4jx.accesslanding.site"

STYLE = r'''<style id="lm-monetization-v1">
.lm-monetization{padding:10px 0 18px}.lm-monetization .portal-wrap{max-width:1180px;margin:auto;padding-left:16px;padding-right:16px}.lm-affiliate-card{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center;padding:16px;border:1px solid #f0d1c7;border-radius:14px;background:linear-gradient(135deg,#fff7f3,#fff);text-decoration:none!important;color:#17202a!important;box-shadow:0 3px 14px rgba(18,34,48,.05)}.lm-affiliate-card small{display:block;color:#aa472f;font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.lm-affiliate-card strong{display:block;margin-top:4px;font-size:18px}.lm-affiliate-card span{display:block;margin-top:4px;color:#667480;font-size:12px}.lm-affiliate-cta{min-height:44px;padding:0 14px;border-radius:10px;display:flex!important;align-items:center;justify-content:center;background:#ee4d2d!important;color:#fff!important;font-weight:900!important;white-space:nowrap}.lm-affiliate-disclosure{margin:7px 2px 0;color:#7a8791;font-size:10px;line-height:1.45}.lm-ad-slot{padding:16px 0;text-align:center;overflow:hidden}.lm-ad-label{margin:0 0 7px;color:#89949e;font-size:10px;font-weight:800;letter-spacing:.05em;text-transform:uppercase}.lm-ad-frame{min-height:90px;display:flex;align-items:center;justify-content:center;overflow:hidden}.lm-ad-frame--300{min-height:250px}.lm-ad-frame iframe{max-width:100%!important}@media(max-width:620px){.lm-monetization{padding:8px 0 14px}.lm-monetization .portal-wrap{padding-left:12px;padding-right:12px}.lm-affiliate-card{grid-template-columns:1fr;padding:13px}.lm-affiliate-card strong{font-size:16px}.lm-affiliate-cta{width:100%;min-height:46px}.lm-ad-slot{padding:12px 0}.lm-ad-frame{max-width:100%}}
</style>'''

AFFILIATE = f'''<section class="lm-monetization" aria-label="Ưu đãi đối tác">
  <div class="portal-wrap">
    <a class="lm-affiliate-card" href="{SMARTLINK}" target="_blank" rel="sponsored noopener noreferrer" data-portal-track="affiliate_shopee_smartlink">
      <div><small>Liên kết đối tác · ACCESSTRADE</small><strong>Ưu đãi mua sắm Shopee hôm nay</strong><span>Bấm để mở Smartlink Shopee. Nếu phát sinh đơn đủ điều kiện, website có thể nhận hoa hồng mà không làm tăng giá mua.</span></div>
      <b class="lm-affiliate-cta">Xem ưu đãi →</b>
    </a>
    <p class="lm-affiliate-disclosure">Tiếp thị liên kết qua ACCESSTRADE. Hoa hồng chỉ có thể được ghi nhận sau khi người dùng bấm liên kết và phát sinh chuyển đổi đủ điều kiện.</p>
  </div>
</section>'''

NATIVE = '''<section class="lm-ad-slot" aria-label="Quảng cáo">
  <div class="portal-wrap"><p class="lm-ad-label">Quảng cáo</p><div class="lm-ad-frame" id="adsterra-native-1">
    <script async="async" data-cfasync="false" src="https://pl30863058.effectivecpmnetwork.com/e336b428517bbcb55a3e3da308cc7939/invoke.js"></script>
    <div id="container-e336b428517bbcb55a3e3da308cc7939"></div>
  </div></div>
</section>'''

BANNER = '''<section class="lm-ad-slot" aria-label="Quảng cáo">
  <div class="portal-wrap"><p class="lm-ad-label">Quảng cáo</p><div class="lm-ad-frame lm-ad-frame--300" id="adsterra-banner-300x250">
    <script>atOptions={'key':'b3caa39744fc30610e7756cf4ccb98cd','format':'iframe','height':250,'width':300,'params':{}};</script>
    <script src="https://www.highperformanceformat.com/b3caa39744fc30610e7756cf4ccb98cd/invoke.js"></script>
  </div></div>
</section>'''

METHOD_MARKER = '<section class="portal-section"><div class="portal-wrap"><div class="portal-section-title"><div><h2>Phương pháp công khai hôm nay'
BUY_MARKER = '<section class="buy-simple portal-buy" id="buy">'


def apply(root: Path) -> dict[str, object]:
    page = root / "index.html"
    if not page.is_file():
        raise ValueError("Missing homepage")
    text = page.read_text(encoding="utf-8")
    changed = False
    if 'id="lm-monetization-v1"' not in text:
        if "</head>" not in text:
            raise ValueError("Homepage has no </head>")
        text = text.replace("</head>", STYLE + "</head>", 1)
        changed = True
    if SMARTLINK not in text:
        if METHOD_MARKER not in text:
            raise ValueError("Monetization placement marker not found")
        text = text.replace(METHOD_MARKER, AFFILIATE + "\n" + NATIVE + "\n" + METHOD_MARKER, 1)
        changed = True
    if 'id="adsterra-banner-300x250"' not in text:
        if BUY_MARKER not in text:
            raise ValueError("Buy placement marker not found")
        text = text.replace(BUY_MARKER, BANNER + "\n" + BUY_MARKER, 1)
        changed = True
    page.write_text(text, encoding="utf-8")
    verify = page.read_text(encoding="utf-8")
    required = (SMARTLINK, 'id="adsterra-native-1"', 'container-e336b428517bbcb55a3e3da308cc7939', 'id="adsterra-banner-300x250"', 'b3caa39744fc30610e7756cf4ccb98cd')
    if not all(token in verify for token in required):
        raise ValueError("Monetization verification failed")
    return {"status":"PASS","changed":changed,"affiliate":True,"native":True,"banner_300x250":True}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "index.html").write_text('<html><head></head><body>'+METHOD_MARKER+BUY_MARKER+'</body></html>', encoding='utf-8')
        result = apply(root)
        text = (root / "index.html").read_text(encoding='utf-8')
        assert result['status']=='PASS' and SMARTLINK in text and text.count(SMARTLINK)==1
        assert apply(root)['changed'] is False
    print('MONETIZATION_SELF_TEST_OK')


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--output-root',type=Path,default=Path('_site')); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    if a.self_test: self_test()
    else: print(apply(a.output_root))

if __name__=='__main__': main()
