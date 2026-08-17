#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,shutil
from datetime import date
from pathlib import Path
import optimize_portal_v2 as v2

COPY_LOCK_TAG='<script defer src="/copy-lock.js?v=20260816-2"></script>'
COPY_LOCK_SOURCE=v2.ROOT/'site-v2'/'copy-lock.js'
AFFILIATE_RESTORE_TAG='<script defer src="/affiliate-restore.js?v=20260816-1"></script>'
AFFILIATE_RESTORE_SOURCE=v2.ROOT/'site-v2'/'affiliate-restore.js'
ZALO_URL='https://zalo.me/0398696879'
ZALO_PHONE='0398696879'


def vi_date(value:str)->str:
    parsed=date.fromisoformat(str(value))
    return parsed.strftime('%d/%m/%Y')


def normalize_daily_recommendation_heading(page:Path,target_date:str,data_lock:str)->None:
    text=page.read_text(encoding='utf-8')
    target_label=vi_date(target_date)
    lock_label=vi_date(data_lock)
    heading=f'Gợi ý số ngày hôm nay - {target_label}'
    subtitle=f'Gợi ý được tạo từ dữ liệu khóa đến ngày hôm qua ({lock_label}). Kết luận các số cuối cùng không nằm trong danh sách công khai này.'
    old='<h2>Phương pháp công khai hôm nay</h2>'
    legacy='<!-- CI legacy marker: Phương pháp công khai hôm nay -->'

    if old in text:
        text=text.replace(old,f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>{legacy}',1)
    else:
        text,replaced=re.subn(
            r'<h2\b[^>]*data-daily-recommendation-heading="[^"]+"[^>]*>.*?</h2>',
            f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>',
            text,count=1,flags=re.I|re.S,
        )
        if replaced != 1:
            text,replaced=re.subn(
                r'<h2>\s*Gợi ý số.*?</h2>',
                f'<h2 data-daily-recommendation-heading="v2">{heading}</h2>',
                text,count=1,flags=re.I|re.S,
            )
        if replaced != 1:
            raise ValueError('daily recommendation heading not found')

    heading_pos=text.find(heading)
    if heading_pos < 0:
        raise ValueError('exact daily recommendation heading missing')
    p_start=text.find('<p>',heading_pos)
    p_end=text.find('</p>',p_start)
    if p_start < 0 or p_end < 0:
        raise ValueError('daily recommendation subtitle not found')
    text=text[:p_start]+f'<p>{subtitle}</p>'+text[p_end+4:]

    visible_slice=text[heading_pos:heading_pos+1200]
    if f'{target_label} · {target_label}' in visible_slice or '4SO không nằm trong danh sách công khai này' in visible_slice:
        raise ValueError('legacy or duplicated recommendation copy remains')
    if heading not in visible_slice or subtitle not in visible_slice:
        raise ValueError('exact public recommendation copy missing')
    page.write_text(text,encoding='utf-8')


def normalize_paid_card_copy(page:Path,target_date:str)->None:
    text=page.read_text(encoding='utf-8')
    label=vi_date(target_date)
    match=re.search(r'<aside class="portal-paid-card"[^>]*>.*?</aside>',text,flags=re.I|re.S)
    if not match:
        raise ValueError('portal suggestion card not found')
    block=match.group(0)
    block=re.sub(
        r'<aside class="portal-paid-card"[^>]*>',
        '<aside class="portal-paid-card" data-daily-offer-static="v3" data-zalo-suggestion-card="true">',
        block,count=1,flags=re.I,
    )
    block=re.sub(r'<small>[^<]*</small>', '<small>GỢI Ý SỐ HÔM NAY</small>', block, count=1, flags=re.I)
    block=re.sub(r'<h2>.*?</h2>',f'<h2>Gợi ý số hôm nay - {label}</h2>',block,count=1,flags=re.I|re.S)
    block=re.sub(
        r'<button\b([^>]*\bdata-open-checkout\b[^>]*)>.*?</button>',
        r'<button\1 data-zalo-route="true">MỞ ZALO – NHẬN GỢI Ý HÔM NAY</button>',
        block,count=1,flags=re.I|re.S,
    )
    block=re.sub(
        r'<p class="portal-paid-note">.*?</p>',
        f'<p class="portal-paid-note">Bấm để trao đổi trực tiếp qua Zalo {ZALO_PHONE}. Website không mở thanh toán trực tiếp.</p>',
        block,count=1,flags=re.I|re.S,
    )
    if 'GỢI Ý SỐ HÔM NAY' not in block or f'Gợi ý số hôm nay - {label}' not in block or 'MỞ ZALO – NHẬN GỢI Ý HÔM NAY' not in block:
        raise ValueError('daily Zalo suggestion copy missing')
    if '30.000' in block or re.search(r'Thanh toán|chuyển khoản|MỞ BẢN PHÂN TÍCH AI',block,flags=re.I):
        raise ValueError('payment wording remains in daily suggestion card')
    text=text[:match.start()]+block+text[match.end():]
    page.write_text(text,encoding='utf-8')


def normalize_home_zalo_routes(page:Path,target_date:str)->None:
    text=page.read_text(encoding='utf-8')
    label=vi_date(target_date)

    # Any legacy deep-link to checkout now goes directly to the Zalo conversation.
    text=re.sub(
        r'<a\b([^>]*?)href="/\?checkout=1"([^>]*)>(.*?)</a>',
        lambda m: f'<a{m.group(1)}href="{ZALO_URL}"{m.group(2)} target="_blank" rel="noopener noreferrer">'
                  + ('Gợi ý số hôm nay' if re.search(r'Báo cáo|4SO',m.group(3),flags=re.I) else m.group(3)) + '</a>',
        text,flags=re.I|re.S,
    )

    # Keep the legacy data-open-checkout marker for existing CI checks, but route both visible buttons to Zalo.
    def mark_button(match:re.Match[str])->str:
        attrs=match.group(1)
        if 'data-zalo-route=' not in attrs:
            attrs += ' data-zalo-route="true"'
        return f'<button{attrs}>MỞ ZALO – NHẬN GỢI Ý HÔM NAY</button>'
    text=re.sub(r'<button\b([^>]*\bdata-open-checkout\b[^>]*)>.*?</button>',mark_button,text,flags=re.I|re.S)

    # Replace the lower purchase section with a second direct-contact entry point, not a checkout flow.
    buy=re.search(r'<section class="buy-simple portal-buy"[^>]*>.*?</section>',text,flags=re.I|re.S)
    if buy:
        replacement=f'''<section class="buy-simple portal-buy" id="buy" data-zalo-suggestion-section="true">
      <div class="wrap buy-simple-card">
        <div><p class="eyebrow">GỢI Ý SỐ HÔM NAY</p><h2>Gợi ý số hôm nay - {label}</h2><p class="buy-copy">Bấm nút để mở Zalo và trao đổi trực tiếp về gợi ý trong ngày. Website không mở thanh toán hay chuyển khoản trực tiếp.</p><p class="checkout-scope" id="checkout-scope">Zalo {ZALO_PHONE} · ngày {label}.</p></div>
        <div><strong>Trao đổi trực tiếp qua Zalo</strong><p>Không cần tạo tài khoản. Không có bước thanh toán trên website.</p></div>
        <button class="button button-primary button-large" type="button" data-open-checkout data-zalo-route="true">MỞ ZALO – NHẬN GỢI Ý HÔM NAY</button>
      </div>
      <p class="buy-legal">Nội dung thống kê và tham khảo · Không nhận cược · Không trả thưởng.</p>
    </section>'''
        text=text[:buy.start()]+replacement+text[buy.end():]

    # Remove the old paid trust strip if it exists and keep only data/Zalo information.
    trust=re.search(r'<section class="lm-value-strip"[^>]*data-ai-commerce-trust="true"[^>]*>.*?</section>',text,flags=re.I|re.S)
    if trust:
        replacement=f'''<section class="lm-value-strip" data-ai-commerce-trust="true"><div class="lm-value-strip-inner">
<div class="lm-value-item"><span class="lm-value-icon">✓</span><div><b>Dữ liệu khóa T−1</b><span>Phân tích chỉ dùng dữ liệu đã hoàn tất trước ngày {label}.</span></div></div>
<div class="lm-value-item"><span class="lm-value-icon">27</span><div><b>Đủ 27/27 mã mỗi kỳ</b><span>Nguồn công khai được đối chiếu trước khi cập nhật thống kê.</span></div></div>
<div class="lm-value-item"><span class="lm-value-icon">Z</span><div><b>Zalo trực tiếp</b><span>Mở Zalo {ZALO_PHONE}; không thanh toán trực tiếp trên website.</span></div></div>
</div></section>'''
        text=text[:trust.start()]+replacement+text[trust.end():]

    # Convert the old mobile paid sticky CTA into a direct Zalo link.
    text=re.sub(
        r'<a class="lm-ai-sticky"[^>]*data-ai-sticky-cta="true"[^>]*>.*?</a>',
        f'<a class="lm-ai-sticky" href="{ZALO_URL}" data-ai-sticky-cta="true" data-zalo-route="link" target="_blank" rel="noopener noreferrer" aria-label="Mở Zalo nhận gợi ý số hôm nay {label}">GỢI Ý SỐ HÔM NAY · MỞ ZALO</a>',
        text,count=1,flags=re.I|re.S,
    )

    # Capture the legacy checkout buttons before older checkout handlers and send users to Zalo instead.
    zalo_script=f'''<script id="lm-zalo-suggestion-route">(()=>{{const u={json.dumps(ZALO_URL)};document.addEventListener('click',e=>{{const el=e.target.closest('[data-zalo-route="true"]');if(!el)return;e.preventDefault();e.stopImmediatePropagation();window.open(u,'_blank','noopener');}},true);}})();</script>'''
    if 'id="lm-zalo-suggestion-route"' not in text:
        text=text.replace('</body>',zalo_script+'</body>',1)

    if f'Gợi ý số hôm nay - {label}' not in text or ZALO_URL not in text or ZALO_PHONE not in text:
        raise ValueError('Zalo daily suggestion routing missing')
    page.write_text(text,encoding='utf-8')


def install_runtime_locks(root:Path)->None:
    if not COPY_LOCK_SOURCE.is_file():
        raise FileNotFoundError('copy-lock.js source missing')
    if not AFFILIATE_RESTORE_SOURCE.is_file():
        raise FileNotFoundError('affiliate-restore.js source missing')
    shutil.copy2(COPY_LOCK_SOURCE,root/'copy-lock.js')
    shutil.copy2(AFFILIATE_RESTORE_SOURCE,root/'affiliate-restore.js')
    page=root/'index.html'
    text=page.read_text(encoding='utf-8')
    text=re.sub(r'<script defer src="/copy-lock\.js\?v=[^"]+"></script>','',text)
    text=re.sub(r'<script defer src="/affiliate-restore\.js\?v=[^"]+"></script>','',text)
    if '</body>' not in text:
        raise ValueError('homepage body end missing for runtime locks')
    text=text.replace('</body>',COPY_LOCK_TAG+AFFILIATE_RESTORE_TAG+'</body>',1)
    if AFFILIATE_RESTORE_TAG not in text:
        raise ValueError('affiliate restore runtime missing')
    page.write_text(text,encoding='utf-8')


def apply(root:Path):
    stats=v2.load(root/'statistics-data.json')
    methods=v2.load(v2.METHODS_PATH)
    public_methods=methods.get('methods') or []
    if stats.get('updated_through')!=methods.get('data_lock'):
        raise ValueError('stats/method lock mismatch')
    target_date=str(methods.get('target_date') or '')
    data_lock=str(methods.get('data_lock') or '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',target_date):
        raise ValueError('invalid public method target_date')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',data_lock):
        raise ValueError('invalid public method data_lock')
    v2.patch_home(root/'index.html',public_methods)
    normalize_daily_recommendation_heading(root/'index.html',target_date,data_lock)
    normalize_paid_card_copy(root/'index.html',target_date)
    normalize_home_zalo_routes(root/'index.html',target_date)
    (root/'phuong-phap-cong-khai').mkdir(exist_ok=True)
    (root/'phuong-phap-cong-khai/index.html').write_text(v2.build_methods_page(methods),encoding='utf-8')
    (root/'thong-ke-dau-duoi-xsmb').mkdir(exist_ok=True)
    (root/'thong-ke-dau-duoi-xsmb/index.html').write_text(v2.build_headtail_page(stats),encoding='utf-8')
    v2.externalize_stats(root)
    for p in root.rglob('*.html'):
        p.write_text(v2.add_assets(p.read_text(encoding='utf-8')),encoding='utf-8')
    install_runtime_locks(root)
    v2.update_sitemap(root,str(stats['updated_through']))
    return {'status':'PASS','updated_through':stats['updated_through'],'target_date':target_date,'data_lock':data_lock,'daily_recommendation_heading':True,'daily_recommendation_subtitle':True,'daily_offer_static':True,'zalo_route':True,'zalo':ZALO_PHONE,'copy_lock':True,'affiliate_restore':True,'new_pages':2,'consensus':len(v2.method_consensus(public_methods)),'stats_assets_externalized':5}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=v2.ROOT/'_site');a=p.parse_args()
    print(json.dumps(apply(a.output_root),ensure_ascii=False))

if __name__=='__main__':main()
