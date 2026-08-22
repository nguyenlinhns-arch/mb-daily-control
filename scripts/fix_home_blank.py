#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dmy(value: str) -> str:
    return date.fromisoformat(value).strftime('%d/%m/%Y')


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def build_main(label: str, lock_label: str) -> str:
    return f'''<main id="main" class="mball-home-main" data-mball-home-main="v4-no-empty-gap">
<section class="mball-home-status"><div class="portal-wrap"><span><b>MB_ALL</b> · 31/31 phương pháp · Data Lock {lock_label}</span><span>Target {label} · PRE-DRAW</span></div></section>

<section class="portal-hero mball-home-hero"><div class="portal-wrap portal-hero-grid">
  <div class="mball-home-intro">
    <p class="portal-kicker">MB_ALL · 31 PHƯƠNG PHÁP</p>
    <h1>Chọn lọc động mỗi ngày<br><em>bằng dữ liệu T−1</em></h1>
    <p class="portal-lead">Mỗi ngày hệ thống chạy đủ 31 phương pháp bằng dữ liệu đến {lock_label}, đánh giá hiệu quả gần 3–5–7–10 ngày, P/L, ROI, số nháy và trạng thái HOT/COLD, rồi chấm điểm trực tiếp từng số. Không cố định phương pháp và không cố định số lượng số.</p>
    <div class="portal-status"><span>31/31 phương pháp</span><span>3–5–7–10 ngày</span><span>HOT/COLD</span><span>PRE-DRAW FROZEN</span></div>
  </div>
  <aside class="portal-paid-card" data-paid-suggestion-card="true" data-daily-offer-static="mball-home-v4">
    <small>THANH TOÁN NHẬN GỢI Ý SỐ</small>
    <h2>Gợi ý số MB_ALL - {label}</h2>
    <div class="lm-returning-note">Gợi ý ngày {label} đã sẵn sàng · 30.000đ/ngày · xác nhận thanh toán qua email.</div>
    <div class="portal-paid-lock" aria-label="TOP 1 và TOP 2 được ẩn trước khi thanh toán"><div><small>TOP 1</small><b>•• — ••</b></div><div><small>TOP 2</small><b>•• — ••</b></div></div>
    <button type="button" data-open-checkout data-cta-position="portal-hero">THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>
    <p class="portal-paid-note">Gợi ý số chỉ mở sau khi giao dịch được xác nhận. Zalo chỉ dùng để hỗ trợ.</p>
  </aside>
</div></section>

<section class="portal-section mball-tools-section"><div class="portal-wrap">
  <div class="portal-section-title"><div><h2>Công cụ thống kê XSMB</h2><p>Dữ liệu 27/27 mã đã hoàn tất đến {lock_label}.</p></div></div>
  <div class="portal-tools mball-tools-grid">
    <a class="portal-card portal-tool" href="/thong-ke-xsmb/"><b>Ma trận 00–99</b><span>Hồ sơ từng số theo nhiều cửa sổ</span><em>Mở công cụ →</em></a>
    <a class="portal-card portal-tool" href="/tan-suat-xsmb/"><b>Tần suất</b><span>Ngày có mặt và tổng số nháy</span><em>Xem bảng →</em></a>
    <a class="portal-card portal-tool" href="/lo-gan-xsmb/"><b>Lô gan</b><span>Gan hiện tại, gan max, lần gần nhất</span><em>Xem gan →</em></a>
    <a class="portal-card portal-tool" href="/cap-dao-xsmb/"><b>45 cặp đảo</b><span>Tần suất cặp và khoảng vắng</span><em>Xem cặp →</em></a>
    <a class="portal-card portal-tool" href="/thong-ke-dau-duoi-xsmb/"><b>Đầu / đuôi</b><span>Phân bố chữ số 0–9</span><em>Xem thống kê →</em></a>
    <a class="portal-card portal-tool" href="/thong-ke-tong-xsmb/"><b>Theo tổng</b><span>Phân bố tổng 0–9</span><em>Xem thống kê →</em></a>
    <a class="portal-card portal-tool" href="/thong-ke-theo-thu-xsmb/"><b>Theo thứ</b><span>So sánh theo ngày trong tuần</span><em>Xem thống kê →</em></a>
    <a class="portal-card portal-tool" href="/tra-cuu-xsmb/"><b>Tra cứu</b><span>Dò bộ số theo lịch sử</span><em>Tra cứu →</em></a>
  </div>
</div></section>

<section class="portal-section mball-method-overview" data-mball-method-overview="mball-31-live-v4"><div class="portal-wrap">
  <div class="portal-section-title"><div><p class="mball-overview-kicker">QUY TRÌNH MB_ALL</p><h2>MB_ALL chạy đủ 31 phương pháp mỗi ngày</h2><p>Không chọn trước một phương pháp. Tất cả đầu ra được tính trước, sau đó mới đánh giá trạng thái và chọn lọc.</p></div></div>
  <div class="portal-methods mball31-process" data-mball31-process="true">
    <article class="portal-method"><div class="portal-method-head"><b>1. Chạy đủ 31/31</b><span>T−1</span></div><p>Mỗi phương pháp chỉ dùng dữ liệu đã hoàn tất đến ngày liền trước.</p></article>
    <article class="portal-method"><div class="portal-method-head"><b>2. Đánh giá hiệu quả gần</b><span>3–5–7–10</span></div><p>Theo dõi W/Hòa/L, streak, P/L, ROI, số nháy và độ ổn định.</p></article>
    <article class="portal-method"><div class="portal-method-head"><b>3. Chấm HOT/COLD</b><span>NET SCORE</span></div><p>Tín hiệu tốt cộng điểm, tín hiệu xấu trừ điểm; kiểm soát phiếu trùng và đồng thuận.</p></article>
    <article class="portal-method"><div class="portal-method-head"><b>4. Chọn động và khóa</b><span>PRE-DRAW</span></div><p>Không cố định số lượng. Chỉ giữ số vượt ngưỡng và khóa trước giờ quay.</p></article>
  </div>
  <div class="mball-overview-lock"><strong>Đầu ra 31 phương pháp và số cuối được giữ kín</strong><span>Chỉ mở sau khi thanh toán được xác nhận qua email. Không dùng kết quả ngày {label} để sửa lựa chọn của chính ngày đó.</span></div>
</div></section>

<section class="mball-home-why"><div class="portal-wrap"><div class="mball-home-why-grid">
  <article><b>Dữ liệu T−1</b><span>Không look-ahead, không dùng kết quả ngày đang chọn.</span></article>
  <article><b>Chọn số động</b><span>Có thể 0, 1, 2 hoặc nhiều số nếu đủ điều kiện.</span></article>
  <article><b>Khóa trước quay</b><span>Lệnh được giữ nguyên để kiểm toán và quyết toán thực tế.</span></article>
</div></div></section>

<section class="buy-simple portal-buy" id="buy" data-paid-suggestion-section="true"><div class="wrap buy-simple-card">
  <div><p class="eyebrow">THANH TOÁN NHẬN GỢI Ý SỐ</p><h2>30.000đ/ngày</h2><p class="buy-copy">Thanh toán một lần để nhận gợi ý số MB_ALL đã khóa cho ngày {label}.</p><p class="checkout-scope" id="checkout-scope">Gợi ý ngày {label} · dữ liệu khóa đến {lock_label} · không tự gia hạn.</p></div>
  <div><strong>Xác nhận thanh toán qua email</strong><p>Sau khi chuyển khoản, bấm gửi xác nhận. Chủ dịch vụ kiểm tra giao dịch qua email và gợi ý số tự mở sau khi được phê duyệt.</p></div>
  <button class="button button-primary button-large" type="button" data-open-checkout data-cta-position="final">THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>
</div><p class="buy-legal">Thanh toán một lần · Không tự gia hạn · Zalo chỉ dùng để hỗ trợ.</p></section>
</main>'''


def style_block() -> str:
    return '''<style id="mball-no-empty-gap-v4">
html,body{min-height:100%}.portal-home .mball-home-main{display:block!important;min-height:0!important;height:auto!important;padding:0!important;margin:0!important}.portal-home .mball-home-status{background:#eef1f4;border-bottom:1px solid #dfe4e8}.portal-home .mball-home-status .portal-wrap{min-height:38px;display:flex;align-items:center;justify-content:space-between;gap:12px;color:#536270;font-size:12px}.portal-home .mball-home-status b{color:#a81218}.portal-home .mball-home-hero{display:block!important;min-height:0!important;height:auto!important;padding:28px 0!important;background:#fff!important}.portal-home .mball-home-hero .portal-hero-grid{display:grid!important;grid-template-columns:minmax(0,1.45fr) minmax(320px,.65fr)!important;gap:22px!important;align-items:start!important}.portal-home .mball-home-intro em{font-style:normal;color:#b3161b}.portal-home .mball-tools-section{display:block!important;min-height:0!important;height:auto!important;padding:24px 0!important;background:#f5f6f8!important}.portal-home .mball-tools-grid{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:10px!important}.portal-home .mball-tools-grid .portal-tool{display:block!important;min-height:118px!important}.portal-home .mball-method-overview{display:block!important;min-height:0!important;height:auto!important;padding:26px 0!important;background:#fff!important}.portal-home .mball31-process{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:10px!important}.portal-home .mball31-process .portal-method{display:block!important;min-height:150px!important}.portal-home .mball-home-why{display:block!important;min-height:0!important;height:auto!important;padding:0 0 24px!important;background:#fff!important}.portal-home .mball-home-why-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.portal-home .mball-home-why-grid article{padding:16px;border:1px solid #dfe4e9;border-radius:14px;background:#f9fafb}.portal-home .mball-home-why-grid b{display:block;color:#192b3a;font-size:14px}.portal-home .mball-home-why-grid span{display:block;margin-top:4px;color:#667581;font-size:12px;line-height:1.45}.portal-home .portal-buy{display:block!important;min-height:0!important;height:auto!important;margin:0!important;padding:24px 0 34px!important}.portal-home .buy-simple-card{min-height:0!important;height:auto!important}.portal-home section:empty,.portal-home div:empty[data-sitewide-products="true"],.portal-home .portal-proof:empty{display:none!important;min-height:0!important;height:0!important;margin:0!important;padding:0!important}.portal-home footer{margin-top:0!important}
@media(max-width:900px){.portal-home .mball-home-hero .portal-hero-grid{grid-template-columns:1fr!important}.portal-home .mball-tools-grid,.portal-home .mball31-process{grid-template-columns:repeat(2,minmax(0,1fr))!important}.portal-home .mball-home-why-grid{grid-template-columns:1fr!important}}
@media(max-width:620px){.portal-home .mball-home-status .portal-wrap{padding-top:7px;padding-bottom:7px;align-items:flex-start;flex-direction:column;gap:2px}.portal-home .mball-tools-grid,.portal-home .mball31-process{grid-template-columns:1fr!important}.portal-home .mball-home-hero{padding:18px 0!important}.portal-home .mball-tools-section,.portal-home .mball-method-overview{padding:18px 0!important}}
</style>'''


def patch(path: Path, label: str, lock_label: str) -> None:
    text = path.read_text(encoding='utf-8')
    main = build_main(label, lock_label)
    text, count = re.subn(r'<main\b[^>]*>.*?</main>', main, text, count=1, flags=re.I | re.S)
    if count != 1:
        raise ValueError('Homepage main block missing')

    text = re.sub(r'<style\s+id="mball-no-empty-gap-v4">.*?</style>', '', text, flags=re.I | re.S)
    if '</head>' not in text:
        raise ValueError('Homepage head missing')
    text = text.replace('</head>', style_block() + '</head>', 1)

    visible = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<(?:script|style)\b.*?</(?:script|style)>', ' ', text, flags=re.I | re.S)))
    visible = re.sub(r'\s+', ' ', visible)
    for required in (
        'MB_ALL chạy đủ 31 phương pháp mỗi ngày',
        'Công cụ thống kê XSMB',
        'THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ',
        'Xác nhận thanh toán qua email',
    ):
        if required.lower() not in visible.lower():
            raise ValueError(f'Missing homepage content: {required}')
    for forbidden in ('KIỂM ĐỊNH LỊCH SỬ 4SO', 'MỞ ZALO – NHẬN GỢI Ý HÔM NAY'):
        if forbidden.lower() in visible.lower():
            raise ValueError(f'Legacy block remains: {forbidden}')
    if 'data-mball-home-main="v4-no-empty-gap"' not in text:
        raise ValueError('No-gap main marker missing')
    path.write_text(text, encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', type=Path, default=ROOT / '_site')
    args = parser.parse_args()
    public = load_json(ROOT / 'ai-methods' / 'public-methods.json')
    label = dmy(str(public['target_date']))
    lock_label = dmy(str(public['data_lock']))
    patch(args.output_root / 'index.html', label, lock_label)
    print(json.dumps({'status':'PASS','homepage':'MBALL_HOME_V4_NO_EMPTY_GAP','report_date':label,'data_lock':lock_label}, ensure_ascii=False))


if __name__ == '__main__':
    main()
