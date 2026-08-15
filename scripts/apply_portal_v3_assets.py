#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CSS='<link rel="stylesheet" href="/portal-v3.css?v=20260815-1">'
MOBILE_CSS_LINK='<link rel="stylesheet" href="/mobile-v1.css?v=20260815-1">'
SENSITIVE={'phuong-phap-4so/index.html','lich-su-doi-chieu/index.html','phuong-phap-cong-khai/index.html'}
SCHEMA_RE=re.compile(r'<script type="application/ld\+json">(?:(?!</script>).)*"@id":"https://lemienbac\.com/#portal-v3"(?:(?!</script>).)*</script>',re.S)

MOBILE_CSS=r'''
/* Lê Miền Bắc mobile-first layer */
html{scroll-padding-bottom:72px}body.portal-home,body.portal-subpage{overflow-x:hidden}
.lm-affiliate-section,.lm-ad-slot{width:100%;padding:8px 0}.lm-affiliate-inner,.lm-ad-inner{max-width:1180px;margin:auto;padding:0 16px}.lm-affiliate-card{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;padding:14px 15px;border:1px solid #ead9d5;border-radius:14px;background:linear-gradient(135deg,#fff8f4,#fff);text-decoration:none!important;color:#243542!important;box-shadow:0 2px 10px rgba(20,35,48,.04)}.lm-affiliate-card b{display:block;font-size:14px}.lm-affiliate-card span{display:block;margin-top:2px;color:#6c7880;font-size:11px}.lm-affiliate-cta{min-height:42px;padding:0 12px;border-radius:10px;display:flex!important;align-items:center;justify-content:center;background:#ee4d2d;color:#fff!important;font-size:12px!important;font-weight:900;white-space:nowrap}.lm-affiliate-note{margin:6px 2px 0;color:#879199;font-size:9px;line-height:1.4}.lm-ad-inner{text-align:center}.lm-ad-label{margin:0 0 6px;color:#8a969e;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}.lm-ad-box{min-height:90px;display:flex;align-items:center;justify-content:center;overflow:hidden}.lm-ad-box--300{width:300px;min-height:250px;margin:auto;max-width:100vw}.lm-ad-box iframe{max-width:100%}.lm-mobile-320-slot{display:none}
@media(max-width:700px){
  html{scroll-padding-bottom:68px}body.portal-home,body.portal-subpage{font-size:15px;line-height:1.5;padding-bottom:62px!important}
  button,a,input,select,textarea{touch-action:manipulation}input,select,textarea{font-size:16px!important}
  .portal-home .portal-header{min-height:50px;padding:6px 10px;gap:7px}.portal-home .portal-brand-mark{width:34px;height:34px}.portal-home .portal-brand span:last-child{display:none}.portal-home .portal-nav{gap:2px;-webkit-overflow-scrolling:touch;scrollbar-width:none}.portal-home .portal-nav::-webkit-scrollbar{display:none}.portal-home .portal-nav a{min-height:40px;display:inline-flex;align-items:center;padding:6px 8px!important;font-size:11px!important}
  .portal-home .portal-topline .portal-wrap{min-height:0!important;padding:6px 12px!important;display:block!important;font-size:11px!important;line-height:1.35}.portal-home .portal-topline a{display:none}
  .portal-home .portal-wrap{padding-left:12px!important;padding-right:12px!important}.portal-home .portal-hero{padding:14px 0!important}.portal-home .portal-hero-grid{gap:10px!important}.portal-home h1{font-size:30px!important;line-height:1.05!important;letter-spacing:-.025em}.portal-home .portal-lead{margin-top:8px!important;font-size:14px!important;line-height:1.5}.portal-home .portal-status{gap:5px!important;margin-top:10px!important}.portal-home .portal-status span{padding:5px 7px!important;font-size:10px!important}
  .portal-home .portal-paid-card{padding:12px!important}.portal-home .portal-paid-card h2{margin:3px 0 6px;font-size:18px;line-height:1.2}.portal-home .portal-paid-lock{gap:6px!important;margin:8px 0!important}.portal-home .portal-paid-lock div{padding:7px!important}.portal-home .portal-paid-lock b{font-size:18px!important}.portal-home .portal-paid-card button,[data-open-checkout]{min-height:46px;font-size:13px}
  .portal-home .portal-section{padding:11px 0!important}.portal-home .portal-section-title{align-items:flex-start!important;gap:8px!important;margin-bottom:8px!important}.portal-home .portal-section-title h2{font-size:19px!important;line-height:1.2}.portal-home .portal-section-title p{font-size:11.5px!important;line-height:1.4}.portal-home .portal-section-title a{font-size:11px!important;white-space:nowrap}
  .portal-home .portal-result-card{padding:10px!important}.portal-home .portal-result-head{align-items:flex-start!important;margin-bottom:8px!important}.portal-home .portal-result-head strong{font-size:15px!important}.portal-home .portal-result-head span{font-size:10px!important}.portal-home .portal-results{grid-template-columns:repeat(5,minmax(0,1fr))!important;gap:5px!important}.portal-home .portal-result{min-width:0;padding:6px 1px!important}.portal-home .portal-result small{font-size:8px!important}.portal-home .portal-result b{font-size:15px!important}.portal-home .portal-dup-note{font-size:10.5px!important;margin-top:7px!important}
  .portal-home .portal-tools{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}.portal-home .portal-tool{min-height:108px;padding:10px!important}.portal-home .portal-tool b{font-size:14px!important;line-height:1.25}.portal-home .portal-tool span{font-size:11px!important;line-height:1.35}.portal-home .portal-tool em{margin-top:6px!important;font-size:10.5px!important}
  .portal-home .portal-methods{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}.portal-home .portal-method{padding:9px!important}.portal-home .portal-method-head{align-items:flex-start!important;margin-bottom:7px!important}.portal-home .portal-method-head b{font-size:12px!important;line-height:1.25}.portal-home .portal-method-head span{font-size:9px!important}.portal-home .portal-ball{width:30px!important;height:30px!important;font-size:12px!important}
  .portal-home .portal-quick-grid{grid-template-columns:1fr!important;gap:8px!important}.portal-home .portal-table{font-size:11.5px!important}.portal-home .portal-table th,.portal-home .portal-table td{padding:7px 8px!important}.portal-home .portal-proof{gap:8px!important}.portal-home .portal-proof-rate{padding:14px!important}.portal-home .portal-proof-rate strong{font-size:36px!important}.portal-home .portal-proof-copy{padding:14px!important}.portal-home .portal-proof-copy h2{font-size:18px!important}.portal-home .portal-proof-copy p{font-size:12px!important;line-height:1.45}
  .portal-home .buy-simple-card{grid-template-columns:1fr!important;gap:14px!important;padding:16px!important}.portal-home .buy-simple-card ol{margin:0!important}.portal-home .buy-simple-card>button{width:100%;min-height:48px}.portal-home .buy-legal{padding:0 12px;font-size:10px!important}
  .portal-mobile-nav{min-height:58px}.portal-mobile-nav a{min-height:56px!important}.portal-mobile-nav a b{font-size:16px!important}.portal-mobile-nav a span{font-size:9px!important}
  .portal-subpage .portal-site-head{padding:6px 10px!important;gap:7px!important}.portal-subpage .portal-site-brand-mark{width:32px!important;height:32px!important}.portal-subpage .portal-site-nav{gap:2px;-webkit-overflow-scrolling:touch}.portal-subpage .portal-site-nav a{min-height:40px;display:inline-flex;align-items:center;padding:6px 7px!important;font-size:10.5px!important}.portal-subpage .portal-contextbar-inner{padding:5px 12px!important;font-size:10.5px!important}.portal-subpage main,.portal-subpage .main{padding-left:12px!important;padding-right:12px!important}.portal-page-intro{margin:10px 12px 0!important;padding:13px!important}.portal-page-intro h1{font-size:25px!important}.portal-page-intro>p:last-child{font-size:12px!important}.portal-v2-wrap{padding:10px 12px 24px!important}.portal-v2-card{padding:11px!important;border-radius:12px!important}.portal-v2-table{min-width:460px!important;font-size:11.5px!important}.portal-v2-table th,.portal-v2-table td{padding:8px 7px!important}.portal-method-grid-v2{gap:7px!important}.portal-method-card-v2{padding:10px!important}.portal-method-ball-v2{width:31px!important;height:31px!important}.portal-breadcrumbs{margin-top:7px!important;padding:0 12px!important;font-size:10px!important}.portal-number-compare{padding:10px!important;margin-bottom:10px!important}.portal-number-compare-grid{gap:6px!important}.portal-number-compare-card{padding:8px!important}.portal-history-controls select{min-height:42px}.portal-history-codes{gap:5px!important}
  .lm-affiliate-section,.lm-ad-slot{padding:6px 0}.lm-affiliate-inner,.lm-ad-inner{padding:0 10px}.lm-affiliate-card{grid-template-columns:1fr;padding:12px;gap:9px}.lm-affiliate-card b{font-size:13px}.lm-affiliate-card span{font-size:10.5px}.lm-affiliate-cta{width:100%;min-height:44px}.lm-ad-label{margin-bottom:4px}.lm-ad-box--300{max-width:300px}.lm-ad-box{overflow:hidden}
}
@media(max-width:390px){
  .portal-home h1{font-size:27px!important}.portal-home .portal-methods{grid-template-columns:1fr!important}.portal-home .portal-results{grid-template-columns:repeat(5,minmax(0,1fr))!important}.portal-home .portal-tool{min-height:104px}.portal-number-compare-grid{grid-template-columns:1fr 1fr!important}
}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}.portal-home .portal-tool{transition:none!important}}
'''

AFFILIATE='''
<section class="lm-affiliate-section" aria-label="Liên kết đối tác">
  <div class="lm-affiliate-inner">
    <a class="lm-affiliate-card" id="affiliate-shopee-smartlink" href="https://nguyenlinhtkv_aul4jx.accesslanding.site" target="_blank" rel="sponsored noopener noreferrer">
      <div><b>Ưu đãi mua sắm Shopee hôm nay</b><span>Smartlink ACCESSTRADE · xem sản phẩm và ưu đãi đang được giới thiệu.</span></div>
      <span class="lm-affiliate-cta">Xem ưu đãi →</span>
    </a>
    <p class="lm-affiliate-note">Website có thể nhận hoa hồng từ giao dịch đủ điều kiện; giá mua của bạn không tăng vì liên kết này.</p>
  </div>
</section>
'''

NATIVE_AD='''
<section class="lm-ad-slot" aria-label="Quảng cáo">
  <div class="lm-ad-inner"><p class="lm-ad-label">Quảng cáo</p><div class="lm-ad-box" id="lm-adsterra-native">
    <script async="async" data-cfasync="false" src="https://pl30863058.effectivecpmnetwork.com/e336b428517bbcb55a3e3da308cc7939/invoke.js"></script>
    <div id="container-e336b428517bbcb55a3e3da308cc7939"></div>
  </div></div>
</section>
'''

BANNER_300='''
<section class="lm-ad-slot" aria-label="Quảng cáo">
  <div class="lm-ad-inner"><p class="lm-ad-label">Quảng cáo</p><div class="lm-ad-box lm-ad-box--300" id="lm-adsterra-300x250">
    <script>atOptions={'key':'b3caa39744fc30610e7756cf4ccb98cd','format':'iframe','height':250,'width':300,'params':{}};</script>
    <script src="https://www.highperformanceformat.com/b3caa39744fc30610e7756cf4ccb98cd/invoke.js"></script>
  </div></div>
</section>
'''
MOBILE_320_MARKER='<!-- LM_ADSTERRA_320X50_SLOT_PENDING -->'


def section_around(text:str,needle:str)->tuple[int,int]|None:
    pos=text.find(needle)
    if pos<0:return None
    start=text.rfind('<section',0,pos)
    end=text.find('</section>',pos)
    if start<0 or end<0:return None
    return start,end+len('</section>')


def inject_home_monetization(root:Path)->dict[str,object]:
    home=root/'index.html'
    if not home.is_file():return {'status':'SKIP','reason':'missing_home'}
    text=home.read_text(encoding='utf-8'); changed=False
    tools=section_around(text,'<h2>Công cụ thống kê XSMB</h2>')
    if tools and 'affiliate-shopee-smartlink' not in text:
        _,end=tools; text=text[:end]+AFFILIATE+text[end:]; changed=True
    methods=section_around(text,'<h2>Phương pháp công khai hôm nay</h2>')
    if methods and 'id="lm-adsterra-native"' not in text:
        _,end=methods; text=text[:end]+NATIVE_AD+text[end:]; changed=True
    buy=text.find('<section class="buy-simple portal-buy"')
    if buy>=0 and 'id="lm-adsterra-300x250"' not in text:
        text=text[:buy]+BANNER_300+MOBILE_320_MARKER+'\n'+text[buy:]; changed=True
    home.write_text(text,encoding='utf-8')
    return {'status':'PASS','changed':changed,'affiliate':'affiliate-shopee-smartlink' in text,'native':'lm-adsterra-native' in text,'banner_300':'lm-adsterra-300x250' in text,'mobile_320_slot':MOBILE_320_MARKER in text}


def safe_llms(root:Path,stats:dict,ready:dict)->None:
    updated=stats.get('updated_through',''); target=ready.get('report_date','')
    text=f'''# Lê Miền Bắc\n\n> Cổng dữ liệu và thống kê XSMB. Dữ liệu công khai cập nhật đến {updated}; báo cáo ngày {target} dùng khóa dữ liệu T−1.\n\n## Công cụ công khai\n\n- [Trung tâm thống kê XSMB](https://lemienbac.com/thong-ke-xsmb/): hồ sơ 00–99 và thống kê nhiều cửa sổ.\n- [Tần suất 00–99](https://lemienbac.com/tan-suat-xsmb/): số ngày xuất hiện và tổng nháy.\n- [Lô gan](https://lemienbac.com/lo-gan-xsmb/): khoảng vắng hiện tại, cực đại và lần gần nhất.\n- [45 cặp đảo](https://lemienbac.com/cap-dao-xsmb/): thống kê lịch sử các cặp đảo.\n- [Đầu/đuôi 0–9](https://lemienbac.com/thong-ke-dau-duoi-xsmb/): phân bố chữ số hàng chục và hàng đơn vị.\n- [Theo tổng 0–9](https://lemienbac.com/thong-ke-tong-xsmb/): phân bố tổng hai chữ số.\n- [Theo thứ](https://lemienbac.com/thong-ke-theo-thu-xsmb/): tần suất 00–99 theo ngày trong tuần.\n- [Tra cứu bộ số](https://lemienbac.com/tra-cuu-xsmb/): dò bộ số trong lịch sử 30–365 kỳ.\n- [Phương pháp công khai](https://lemienbac.com/phuong-phap-cong-khai/): A1, 2SO/X2, X3, F01, F06 và KÉP.\n\n## 4SO\n\n4SO là lớp phân tích riêng. Website chỉ công khai trạng thái khóa dữ liệu và hiệu quả lịch sử tổng hợp; đầu ra và logic nội bộ được giữ kín.\n\n## Nguyên tắc dữ liệu\n\n- Mỗi ngày lịch sử phải đủ 27/27 mã hai chữ số.\n- Thống kê công khai chỉ mô tả dữ liệu đã công bố.\n- Không suy diễn rằng số đang gan hoặc xuất hiện nhiều có nghĩa vụ xuất hiện ở kỳ tiếp theo.\n- Tỷ lệ lịch sử không phải xác suất hay cam kết kết quả.\n'''
    (root/'llms.txt').write_text(text,encoding='utf-8')


def apply(root:Path)->dict[str,object]:
    (root/'mobile-v1.css').write_text(MOBILE_CSS.strip()+'\n',encoding='utf-8')
    n=0; stripped=0
    for p in root.rglob('*.html'):
        t=p.read_text(encoding='utf-8'); rel=p.relative_to(root).as_posix()
        if rel in SENSITIVE:
            t2,count=SCHEMA_RE.subn('',t,count=1)
            if count:t=t2; stripped+=1
        if 'portal-v3.css' not in t:t=t.replace('</head>',CSS+'</head>',1)
        if 'mobile-v1.css' not in t:t=t.replace('</head>',MOBILE_CSS_LINK+'</head>',1)
        p.write_text(t,encoding='utf-8'); n+=1
    monetization_result=inject_home_monetization(root)
    import enrich_portal_metadata as metadata
    import normalize_portal_schema as schema
    import bundle_portal_css as bundle
    import share_statistics_loader as shared_stats
    import fingerprint_portal_assets as fingerprint
    metadata_result=metadata.apply(root); schema_result=schema.apply(root); bundle_result=bundle.apply(root); shared_stats_result=shared_stats.apply(root); fingerprint_result=fingerprint.apply(root)
    result:dict[str,object]={'pages':n,'sensitive_schema_removed':stripped,'mobile_css':{'status':'PASS','bytes':(root/'mobile-v1.css').stat().st_size},'monetization':monetization_result,'metadata':metadata_result,'schema':schema_result,'css_bundle':bundle_result,'shared_statistics_loader':shared_stats_result,'asset_fingerprint':fingerprint_result}
    required=('statistics-data.json','source-access.json','report-readiness.json','sitemap.xml','llms.txt')
    if all((root/name).exists() for name in required):
        import finalize_portal_v4 as v4
        v4.write_llms=safe_llms
        result['quality_gate']=v4.apply(root)
    return result


def self_test()->None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/'phuong-phap-cong-khai').mkdir();
        (r/'phuong-phap-cong-khai/index.html').write_text('<html><head></head><body></body></html>',encoding='utf-8')
        (r/'index.html').write_text('<html><head></head><body><section class="portal-section"><h2>Công cụ thống kê XSMB</h2></section><section class="portal-section"><h2>Phương pháp công khai hôm nay</h2></section><section class="buy-simple portal-buy"></section></body></html>',encoding='utf-8')
        (r/'mobile-v1.css').write_text(MOBILE_CSS,encoding='utf-8')
        m=inject_home_monetization(r); t=(r/'index.html').read_text(encoding='utf-8')
        assert m['affiliate'] and m['native'] and m['banner_300'] and MOBILE_320_MARKER in t
        assert '@media(max-width:700px)' in MOBILE_CSS and 'portal-results' in MOBILE_CSS
    print('PORTAL_V3_ASSETS_SELF_TEST_OK')


def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))
if __name__=='__main__':main()
