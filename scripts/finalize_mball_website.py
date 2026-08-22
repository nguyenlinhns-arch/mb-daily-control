#!/usr/bin/env python3
"""Apply the final, user-visible MB_ALL homepage state after every other builder.

This script deliberately runs last in the Pages workflow. It removes the
retired 4SO/70-percent proof block and the public six-method number panel,
then renders the current MB_ALL 31-method workflow and the paid 30,000 VND
email-confirmed delivery card. Zalo remains a separate support action only.
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

SUPPORT_ROUTE = "/go/zalo.htm"
FINAL_VERSION = "20260822-mball-final-v3"


def visible_text(value: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.S)
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def extract_label(text: str, patterns: tuple[str, ...], fallback: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return match.group(1)
    return fallback


def section_bounds(text: str, marker_pos: int) -> tuple[int, int] | None:
    start = text.rfind("<section", 0, marker_pos)
    end = text.find("</section>", marker_pos)
    if start < 0 or end < 0:
        return None
    return start, end + len("</section>")


def remove_sections_containing(text: str, markers: tuple[str, ...]) -> str:
    while True:
        positions = [(text.find(marker), marker) for marker in markers if marker in text]
        positions = [(pos, marker) for pos, marker in positions if pos >= 0]
        if not positions:
            return text
        pos, _ = min(positions)
        bounds = section_bounds(text, pos)
        if not bounds:
            return text
        start, end = bounds
        text = text[:start] + text[end:]


def overview_style() -> str:
    return '''<style id="mball-final-home-style">
.portal-home .portal-proof,.portal-home .historical-proof-section{display:none!important}
.portal-home .mball-method-overview{padding:20px 0!important}.portal-home .mball-method-overview .portal-section-title{align-items:flex-start!important;margin-bottom:12px!important}.portal-home .mball-overview-kicker{margin:0 0 5px!important;color:#b3161b!important;font-size:10px!important;font-weight:1000!important;letter-spacing:.08em!important;text-transform:uppercase!important}.portal-home .mball31-process{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:10px!important}.portal-home .mball31-process .portal-method{min-width:0!important;padding:14px!important;border:1px solid #dfe4e9!important;border-radius:13px!important;background:#fff!important;box-shadow:0 2px 10px rgba(16,35,50,.04)!important}.portal-home .mball31-process .portal-method-head{margin-bottom:7px!important;align-items:flex-start!important}.portal-home .mball31-process .portal-method-head b{font-size:14px!important;line-height:1.3!important}.portal-home .mball31-process .portal-method-head span{flex:0 0 auto!important;background:#f5e9ea!important;color:#a70e15!important;font-size:9px!important;font-weight:1000!important}.portal-home .mball31-process .portal-method p{margin:0!important;color:#5f6e79!important;font-size:12px!important;line-height:1.5!important}.portal-home .mball-overview-lock{display:flex!important;align-items:flex-start!important;justify-content:space-between!important;gap:14px!important;margin-top:11px!important;padding:13px 14px!important;border:1px solid #efc8ca!important;border-radius:13px!important;background:#fff8f8!important}.portal-home .mball-overview-lock strong{display:block!important;color:#a20e15!important;font-size:13px!important}.portal-home .mball-overview-lock span{display:block!important;max-width:760px!important;color:#6f6163!important;font-size:11px!important;line-height:1.5!important}.portal-home .portal-paid-card[data-paid-suggestion-card="true"]{border-color:#e9c3c6!important;background:linear-gradient(145deg,#fff,#fff7f7)!important}.portal-home .portal-paid-card[data-paid-suggestion-card="true"] .lm-returning-note{margin:8px 0 10px!important}.portal-home .portal-paid-card[data-paid-suggestion-card="true"] .lm-ai-runtime-kicker{display:block;margin-top:8px;color:#79575a;font-size:10px;font-weight:850;line-height:1.4}.portal-home .portal-paid-card[data-paid-suggestion-card="true"] .portal-paid-note{margin-top:7px!important}.portal-home .buy-simple[data-paid-suggestion-section="true"] .buy-simple-card{grid-template-columns:1.15fr .9fr auto!important}.portal-home .buy-simple[data-paid-suggestion-section="true"] .buy-simple-card>button{align-self:center!important}.portal-home .buy-simple[data-paid-suggestion-section="true"] h2{color:#b3161b!important}.portal-home #mball-zalo-support{position:fixed!important;right:18px!important;bottom:20px!important;z-index:2147483000!important;width:74px!important;height:74px!important;box-sizing:border-box!important;display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;padding:13px 0 0!important;border:4px solid #fff!important;border-radius:50%!important;background:linear-gradient(145deg,#1780ff,#0068ff)!important;color:#fff!important;text-decoration:none!important;text-align:center!important;font-size:11px!important;font-weight:1000!important;line-height:1.05!important;box-shadow:0 12px 28px rgba(0,74,190,.32)!important}.portal-home #mball-zalo-support::before{content:"Zalo";display:block;font-size:12px;font-weight:1000}
@media(max-width:900px){.portal-home .mball31-process{grid-template-columns:repeat(2,minmax(0,1fr))!important}.portal-home .buy-simple[data-paid-suggestion-section="true"] .buy-simple-card{grid-template-columns:1fr!important}}
@media(max-width:620px){.portal-home .mball31-process{grid-template-columns:1fr!important}.portal-home .mball-overview-lock{display:block!important}.portal-home .mball-overview-lock span{margin-top:4px!important}.portal-home #mball-zalo-support{right:12px!important;bottom:72px!important;width:66px!important;height:66px!important;border-width:3px!important;font-size:10px!important}}
</style>'''


def method_overview(target: str, lock: str) -> str:
    return f'''<section class="portal-section mball-method-overview" data-mball-method-overview="mball-31-final-v3">
  <div class="portal-wrap">
    <div class="portal-section-title"><div>
      <p class="mball-overview-kicker">MB_ALL · DATA LOCK {lock}</p>
      <h2 data-daily-recommendation-heading="mball-31-final-v3">MB_ALL chạy đủ 31 phương pháp mỗi ngày</h2>
      <p>Không chọn trước một phương pháp. Hệ thống chạy đủ 31/31 phương pháp bằng dữ liệu đến {lock}, sau đó mới đánh giá trạng thái gần và chấm điểm từng số.</p>
    </div></div>
    <div class="portal-methods mball31-process" data-mball31-process="true">
      <article class="portal-method"><div class="portal-method-head"><b>1. Chạy đủ 31/31</b><span>T−1</span></div><p>Mỗi đầu ra chỉ dùng dữ liệu đã hoàn tất đến ngày liền trước; không dùng kết quả ngày đang chọn.</p></article>
      <article class="portal-method"><div class="portal-method-head"><b>2. Đánh giá hiệu quả gần</b><span>3–5–7–10</span></div><p>Đối chiếu W/Hòa/L, chuỗi thắng–thua, P/L, ROI, số nháy và độ ổn định theo các cửa sổ gần.</p></article>
      <article class="portal-method"><div class="portal-method-head"><b>3. Chấm HOT/COLD từng số</b><span>NET SCORE</span></div><p>Tín hiệu tốt cộng điểm, tín hiệu xấu trừ điểm; kiểm soát phiếu trùng và chỉ tính đồng thuận KÉP khi đủ điều kiện.</p></article>
      <article class="portal-method"><div class="portal-method-head"><b>4. Chọn động và khóa</b><span>PRE-DRAW</span></div><p>Không cố định phương pháp hoặc số lượng số. Chỉ giữ các số vượt ngưỡng rồi khóa trước giờ quay.</p></article>
    </div>
    <div class="mball-overview-lock"><strong>Đầu ra 31 phương pháp và số cuối được giữ kín</strong><span>Chỉ mở sau khi thanh toán được xác nhận qua email. Kết quả ngày {target} không được dùng để sửa lựa chọn của chính ngày đó.</span></div>
    <p class="portal-disclaimer">MB_ALL là quy trình tổng hợp tín hiệu động, không phải một phương pháp cố định và không công khai các số thành phần trước thanh toán.</p>
  </div>
</section>'''


def paid_card(target: str) -> str:
    return f'''<aside class="portal-paid-card" data-paid-suggestion-card="true" data-daily-offer-static="mball-final-v3">
  <small>THANH TOÁN NHẬN GỢI Ý SỐ</small>
  <h2>Gợi ý số MB_ALL - {target}</h2>
  <div class="lm-returning-note">Gợi ý ngày {target} đã sẵn sàng · 30.000đ/ngày · xác nhận thanh toán qua email.</div>
  <div class="portal-paid-lock" aria-label="TOP 1 và TOP 2 được ẩn trước khi thanh toán"><div><small>TOP 1</small><b>•• — ••</b></div><div><small>TOP 2</small><b>•• — ••</b></div></div>
  <button type="button" data-open-checkout data-cta-position="portal-hero" aria-label="Thanh toán nhận gợi ý số MB_ALL ngày {target}, giá 30.000 đồng">THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>
  <span class="lm-ai-runtime-kicker">Thanh toán một lần · Không tự gia hạn · Xác nhận qua email</span>
  <p class="portal-paid-note">Gợi ý số chỉ mở sau khi giao dịch được xác nhận. Zalo chỉ dùng để hỗ trợ.</p>
</aside>'''


def paid_section(target: str, lock: str) -> str:
    return f'''<section class="buy-simple portal-buy" id="buy" data-paid-suggestion-section="true">
  <div class="wrap buy-simple-card">
    <div><p class="eyebrow">THANH TOÁN NHẬN GỢI Ý SỐ</p><h2>30.000đ/ngày</h2><p class="buy-copy">Thanh toán một lần để nhận gợi ý số MB_ALL đã khóa cho ngày {target}.</p><p class="checkout-scope" id="checkout-scope">Gợi ý ngày {target} · dữ liệu khóa đến {lock} · không tự gia hạn.</p></div>
    <div><strong>Xác nhận thanh toán qua email</strong><p>Sau khi chuyển khoản, bấm gửi xác nhận. Chủ dịch vụ kiểm tra giao dịch qua email và gợi ý số tự mở sau khi được phê duyệt.</p></div>
    <button class="button button-primary button-large" type="button" data-open-checkout data-cta-position="final">THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>
  </div>
  <p class="buy-legal">Thanh toán một lần · Không tự gia hạn · Zalo chỉ dùng để hỗ trợ · Không nhận cược · Không trả thưởng.</p>
</section>'''


def rewrite_checkout_copy(text: str, target: str, lock: str) -> str:
    replacements = (
        ("NHẬN BÁO CÁO HÔM NAY", "THANH TOÁN NHẬN GỢI Ý SỐ"),
        ("NHẬN BÁO CÁO NGÀY", "THANH TOÁN NHẬN GỢI Ý SỐ NGÀY"),
        ("Mở bản phân tích AI", "Thanh toán nhận gợi ý số MB_ALL"),
        ("Bản phân tích AI", "Gợi ý số MB_ALL"),
        ("bản phân tích AI", "gợi ý số MB_ALL"),
        ("2 cặp 4SO · 4 đầu ra xếp hạng · Top 3 và hồ sơ nguồn", "Gợi ý số MB_ALL đã khóa · dữ liệu T−1"),
        ("4 số được chia thành 2 cặp theo thứ tự xếp hạng.", "Gợi ý số MB_ALL chỉ mở sau khi giao dịch được xác nhận."),
        ("TÔI ĐÃ CHUYỂN KHOẢN – MỞ BẢN PHÂN TÍCH AI", "TÔI ĐÃ CHUYỂN KHOẢN – GỬI EMAIL XÁC NHẬN"),
        ("Tôi đã chuyển khoản – mở bản phân tích AI", "Tôi đã chuyển khoản – gửi email xác nhận"),
        ("MỞ ZALO – NHẬN GỢI Ý HÔM NAY", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ"),
        ("MỞ ZALO - NHẬN GỢI Ý HÔM NAY", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ"),
        ("Gợi ý ngày {target} đã sẵn sàng · mở Zalo để trao đổi.", f"Gợi ý ngày {target} đã sẵn sàng · 30.000đ/ngày · xác nhận thanh toán qua email."),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(
        r'<p class="zalo-instruction">.*?</p>',
        '<p class="zalo-instruction">Sau khi chuyển khoản, bấm nút dưới đây. Hệ thống gửi email xác nhận để chủ dịch vụ kiểm tra giao dịch và mở gợi ý số.</p>',
        text,
        count=1,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'(<button class="payment-confirm" id="payment-self-confirm"[^>]*>).*?(</button>)',
        r'\1TÔI ĐÃ CHUYỂN KHOẢN – GỬI EMAIL XÁC NHẬN\2',
        text,
        count=1,
        flags=re.I | re.S,
    )
    text = text.replace(f"01 báo cáo ngày {target} · dữ liệu khóa đến {lock}.", f"Gợi ý số MB_ALL ngày {target} · dữ liệu khóa đến {lock}.")
    return text


def replace_method_section(text: str, target: str, lock: str) -> str:
    heading = re.search(
        r"<h2\b[^>]*>(?:Phương pháp công khai hôm nay|Gợi ý số[^<]*|MB_ALL chạy đủ 31 phương pháp mỗi ngày)</h2>",
        text,
        flags=re.I,
    )
    if not heading:
        raise RuntimeError("Unable to find the homepage method panel")
    bounds = section_bounds(text, heading.start())
    if not bounds:
        raise RuntimeError("Unable to find method panel bounds")
    start, end = bounds
    return text[:start] + method_overview(target, lock) + text[end:]


def rewrite_public_methods_page(path: Path, target: str, lock: str) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    main = f'''<main><section class="portal-page-intro"><p class="eyebrow">MB_ALL · 31 PHƯƠNG PHÁP</p><h1>Quy trình chọn lọc động MB_ALL ngày {target}</h1><p>MB_ALL chạy đủ 31 phương pháp bằng dữ liệu khóa đến {lock}. Website không công khai đầu ra từng phương pháp hoặc số cuối trước thanh toán.</p></section><div class="portal-v2-wrap"><section class="portal-v2-card"><h2>Quy trình vận hành hàng ngày</h2><div class="portal-method-grid-v2"><article class="portal-method-card-v2"><header><b>Chạy đủ 31/31</b><span>T−1</span></header><p>Không chọn trước phương pháp; mọi đầu ra đều được tính bằng dữ liệu đã hoàn tất.</p></article><article class="portal-method-card-v2"><header><b>Đánh giá hiệu quả gần</b><span>3–5–7–10</span></header><p>Theo dõi W/Hòa/L, P/L, ROI, số nháy, streak và độ ổn định.</p></article><article class="portal-method-card-v2"><header><b>HOT/COLD theo số</b><span>NET SCORE</span></header><p>Cộng điểm tín hiệu tốt, trừ điểm tín hiệu xấu và kiểm soát phiếu trùng.</p></article><article class="portal-method-card-v2"><header><b>Chọn động và khóa</b><span>PRE-DRAW</span></header><p>Không cố định số lượng; chỉ giữ số vượt ngưỡng rồi khóa trước giờ quay.</p></article></div></section><section class="portal-v2-card"><h2>Phần nào được công khai?</h2><p>Công khai nguyên tắc dữ liệu T−1, cách đánh giá và điều kiện khóa. Đầu ra 31 phương pháp, Net Score từng số và lựa chọn cuối chỉ mở sau khi thanh toán được xác nhận qua email.</p><div class="portal-related"><a href="/thong-ke-xsmb/">Thống kê 00–99</a><a href="/tan-suat-xsmb/">Tần suất</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/?checkout=1">Thanh toán nhận gợi ý số</a></div></section></div></main>'''
    text, count = re.subn(r"<main\b[^>]*>.*?</main>", main, text, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Unable to replace the public methods page")
    path.write_text(text, encoding="utf-8")


def finalize(root: Path) -> None:
    page = root / "index.html"
    if not page.is_file():
        raise FileNotFoundError(page)
    text = page.read_text(encoding="utf-8")
    target = extract_label(text, (r'data-report-date="(\d{2}/\d{2}/\d{4})"', r"Target\s+(\d{2}/\d{2}/\d{4})"), "ngày hiện tại")
    lock = extract_label(text, (r'data-lock-date="(\d{2}/\d{2}/\d{4})"', r"Data\s*lock\s+(\d{2}/\d{2}/\d{4})"), "T−1")

    text = remove_sections_containing(text, ("KIỂM ĐỊNH LỊCH SỬ 4SO", "4SO chỉ công khai hiệu quả tổng hợp", 'class="portal-proof"'))
    text = replace_method_section(text, target, lock)

    text, count = re.subn(r'<aside class="portal-paid-card"[^>]*>.*?</aside>', paid_card(target), text, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Unable to replace the top paid card")
    text, count = re.subn(r'<section class="buy-simple portal-buy"[^>]*>.*?</section>', paid_section(target, lock), text, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Unable to replace the lower paid section")

    text = rewrite_checkout_copy(text, target, lock)
    text = re.sub(r'<script\s+id="lm-zalo-suggestion-route">.*?</script>', "", text, flags=re.I | re.S)
    text = re.sub(r'\sdata-zalo-route="[^"]*"', "", text, flags=re.I)
    text = re.sub(r'<a\b[^>]*(?:id="mball-zalo-support"|class="[^"]*floating-zalo[^"]*")[^>]*>.*?</a>', "", text, flags=re.I | re.S)
    text = re.sub(r'<style\s+id="(?:mball-final-home-style|mball-round-support-style|mball-method-overview-static-style)">.*?</style>', "", text, flags=re.I | re.S)

    # Refresh the main MB_ALL identity without altering the surrounding portal.
    text = re.sub(r'<p class="portal-kicker">.*?</p>', '<p class="portal-kicker">MB_ALL · 31 PHƯƠNG PHÁP</p>', text, count=1, flags=re.I | re.S)
    text = re.sub(r'<h1>.*?</h1>', '<h1>MB_ALL – 31 phương pháp<br>chọn lọc động mỗi ngày</h1>', text, count=1, flags=re.I | re.S)
    text = re.sub(r'<p class="portal-lead"[^>]*>.*?</p>', '<p class="portal-lead">Mỗi ngày MB_ALL chạy đủ 31 phương pháp bằng dữ liệu đến T−1, đánh giá hiệu quả gần theo 3–5–7–10 ngày, P/L, số nháy và trạng thái HOT/COLD, rồi chấm điểm trực tiếp từng số. Không cố định phương pháp và không cố định số lượng số được chọn.</p>', text, count=1, flags=re.I | re.S)

    support = f'<a id="mball-zalo-support" class="mball-zalo-support-button" href="{SUPPORT_ROUTE}" target="_blank" rel="noopener noreferrer" aria-label="Hỗ trợ qua Zalo">Hỗ trợ</a>'
    if "</head>" not in text or "</body>" not in text:
        raise RuntimeError("Homepage head/body end missing")
    text = text.replace("</head>", overview_style() + "</head>", 1)
    text = text.replace("</body>", support + "</body>", 1)

    # Cache-bust the runtimes that previously rewrote the paid card to Zalo.
    for asset in ("config.js", "copy-lock.js", "checkout-entry.js", "checkout-enhance.js"):
        text = re.sub(rf'{re.escape(asset)}\?v=[^"\']+', f"{asset}?v={FINAL_VERSION}", text, flags=re.I)

    rendered = visible_text(text).upper()
    for forbidden in (
        "MỞ ZALO – NHẬN GỢI Ý HÔM NAY",
        "MỞ ZALO - NHẬN GỢI Ý HÔM NAY",
        "KIỂM ĐỊNH LỊCH SỬ 4SO",
        "4SO CHỈ CÔNG KHAI HIỆU QUẢ TỔNG HỢP",
    ):
        if forbidden in rendered:
            raise RuntimeError(f"Retired visible copy remains: {forbidden}")
    for required in (
        "MB_ALL CHẠY ĐỦ 31 PHƯƠNG PHÁP MỖI NGÀY",
        "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ",
        "XÁC NHẬN THANH TOÁN QUA EMAIL",
        "ĐẦU RA 31 PHƯƠNG PHÁP VÀ SỐ CUỐI ĐƯỢC GIỮ KÍN",
    ):
        if required not in rendered:
            raise RuntimeError(f"Required visible copy missing: {required}")
    if text.count("data-open-checkout") != 2:
        raise RuntimeError(f"Expected exactly two checkout buttons, found {text.count('data-open-checkout')}")
    method_slice = text.split('data-mball-method-overview="mball-31-final-v3"', 1)[1].split("</section>", 1)[0]
    for forbidden in ("portal-method-numbers", "portal-ball", "portal-consensus"):
        if forbidden in method_slice:
            raise RuntimeError(f"Public method output remains in MB_ALL panel: {forbidden}")

    page.write_text(text, encoding="utf-8")
    rewrite_public_methods_page(root / "phuong-phap-cong-khai" / "index.html", target, lock)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("_site"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "phuong-phap-cong-khai").mkdir()
            (root / "phuong-phap-cong-khai" / "index.html").write_text("<html><body><main>old</main></body></html>", encoding="utf-8")
            (root / "index.html").write_text('''<html><head><script src="config.js?v=old"></script></head><body class="portal-home" data-report-date="22/08/2026" data-lock-date="21/08/2026"><main><section class="portal-hero"><div><p class="portal-kicker">old</p><h1>old</h1><p class="portal-lead">old</p></div><aside class="portal-paid-card"><small>old</small><h2>old</h2><div class="portal-paid-lock"><div>TOP 1</div><div>TOP 2</div></div><button data-open-checkout>MỞ ZALO – NHẬN GỢI Ý HÔM NAY</button></aside></section><section class="portal-section"><h2>Gợi ý số hôm nay - 22/08/2026</h2><div class="portal-methods"><span class="portal-ball">98</span></div><div class="portal-consensus">old</div></section><section class="portal-section"><div class="portal-proof"><div>KIỂM ĐỊNH LỊCH SỬ 4SO 70%</div></div></section><section class="buy-simple portal-buy"><button data-open-checkout>MỞ ZALO – NHẬN GỢI Ý HÔM NAY</button></section></main><div id="checkout"><p class="zalo-instruction">old</p><button class="payment-confirm" id="payment-self-confirm">old</button></div></body></html>''', encoding="utf-8")
            finalize(root)
            output = (root / "index.html").read_text(encoding="utf-8")
            assert "MB_ALL chạy đủ 31 phương pháp mỗi ngày" in output
            assert "KIỂM ĐỊNH LỊCH SỬ 4SO" not in visible_text(output)
            assert "MỞ ZALO – NHẬN GỢI Ý HÔM NAY" not in visible_text(output)
        print("FINALIZE_MBALL_WEBSITE_SELF_TEST_OK")
        return
    finalize(args.output_root)
    print("FINALIZE_MBALL_WEBSITE_OK")


if __name__ == "__main__":
    main()
