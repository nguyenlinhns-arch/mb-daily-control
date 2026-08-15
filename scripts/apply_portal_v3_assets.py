#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CSS='<link rel="stylesheet" href="/portal-v3.css?v=20260815-1">'
SENSITIVE={'phuong-phap-4so/index.html','lich-su-doi-chieu/index.html','phuong-phap-cong-khai/index.html'}
SCHEMA_RE=re.compile(r'<script type="application/ld\+json">(?:(?!</script>).)*"@id":"https://lemienbac\.com/#portal-v3"(?:(?!</script>).)*</script>',re.S)

def safe_llms(root:Path,stats:dict,ready:dict)->None:
    updated=stats.get('updated_through',''); target=ready.get('report_date','')
    text=f'''# Lê Miền Bắc\n\n> Cổng dữ liệu và thống kê XSMB. Dữ liệu công khai cập nhật đến {updated}; báo cáo ngày {target} dùng khóa dữ liệu T−1.\n\n## Công cụ công khai\n\n- [Trung tâm thống kê XSMB](https://lemienbac.com/thong-ke-xsmb/): hồ sơ 00–99 và thống kê nhiều cửa sổ.\n- [Tần suất 00–99](https://lemienbac.com/tan-suat-xsmb/): số ngày xuất hiện và tổng nháy.\n- [Lô gan](https://lemienbac.com/lo-gan-xsmb/): khoảng vắng hiện tại, cực đại và lần gần nhất.\n- [45 cặp đảo](https://lemienbac.com/cap-dao-xsmb/): thống kê lịch sử các cặp đảo.\n- [Đầu/đuôi 0–9](https://lemienbac.com/thong-ke-dau-duoi-xsmb/): phân bố chữ số hàng chục và hàng đơn vị.\n- [Theo tổng 0–9](https://lemienbac.com/thong-ke-tong-xsmb/): phân bố tổng hai chữ số.\n- [Theo thứ](https://lemienbac.com/thong-ke-theo-thu-xsmb/): tần suất 00–99 theo ngày trong tuần.\n- [Tra cứu bộ số](https://lemienbac.com/tra-cuu-xsmb/): dò bộ số trong lịch sử 30–365 kỳ.\n- [Phương pháp công khai](https://lemienbac.com/phuong-phap-cong-khai/): A1, 2SO/X2, X3, F01, F06 và KÉP.\n\n## 4SO\n\n4SO là lớp phân tích riêng. Website chỉ công khai trạng thái khóa dữ liệu và hiệu quả lịch sử tổng hợp; đầu ra và logic nội bộ được giữ kín.\n\n## Nguyên tắc dữ liệu\n\n- Mỗi ngày lịch sử phải đủ 27/27 mã hai chữ số.\n- Thống kê công khai chỉ mô tả dữ liệu đã công bố.\n- Không suy diễn rằng số đang gan hoặc xuất hiện nhiều có nghĩa vụ xuất hiện ở kỳ tiếp theo.\n- Tỷ lệ lịch sử không phải xác suất hay cam kết kết quả.\n'''
    (root/'llms.txt').write_text(text,encoding='utf-8')

def apply(root:Path)->dict[str,object]:
    n=0; stripped=0
    for p in root.rglob('*.html'):
        t=p.read_text(encoding='utf-8')
        rel=p.relative_to(root).as_posix()
        if rel in SENSITIVE:
            t2,count=SCHEMA_RE.subn('',t,count=1)
            if count:
                t=t2; stripped+=1
        if 'portal-v3.css' not in t:
            t=t.replace('</head>',CSS+'</head>',1)
        p.write_text(t,encoding='utf-8')
        n+=1
    import enrich_portal_metadata as metadata
    import normalize_portal_schema as schema
    import bundle_portal_css as bundle
    import fingerprint_portal_assets as fingerprint
    metadata_result=metadata.apply(root)
    schema_result=schema.apply(root)
    bundle_result=bundle.apply(root)
    fingerprint_result=fingerprint.apply(root)
    result:dict[str,object]={
        'pages':n,
        'sensitive_schema_removed':stripped,
        'metadata':metadata_result,
        'schema':schema_result,
        'css_bundle':bundle_result,
        'asset_fingerprint':fingerprint_result,
    }
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
        (r/'phuong-phap-cong-khai/index.html').write_text('<html><head><title>Phương pháp công khai</title><meta name="description" content="Mô tả"><meta name="robots" content="index,follow"><script type="application/ld+json">{"@id":"https://lemienbac.com/#portal-v3","name":"Không công khai 4SO","dateModified":"2026-08-15"}</script></head><body></body></html>',encoding='utf-8')
        result=apply(r); text=(r/'phuong-phap-cong-khai/index.html').read_text(encoding='utf-8')
        assert result['pages']==1 and result['sensitive_schema_removed']==1 and 'portal-v3.css' in text and '#portal-v3' not in text
        assert 'quality_gate' not in result and 'G-R9TBYP97BC' in text and 'og:title' in text
        assert '6 phương pháp XSMB công khai hôm nay' in text and result['css_bundle']['status']=='PASS'
        assert result['asset_fingerprint']['status']=='PASS'
    print('PORTAL_V3_ASSETS_SELF_TEST_OK')

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'_site');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:self_test()
    else:print(json.dumps(apply(a.output_root),ensure_ascii=False))
if __name__=='__main__':main()
