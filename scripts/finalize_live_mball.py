#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dmy(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def section_bounds(text: str, marker: str | re.Pattern[str]) -> tuple[int, int] | None:
    if isinstance(marker, str):
        pos = text.find(marker)
        if pos < 0:
            return None
    else:
        match = marker.search(text)
        if not match:
            return None
        pos = match.start()
    start = pos if text.startswith("<section", pos) else text.rfind("<section", 0, pos)
    end = text.find("</section>", pos)
    if start < 0 or end < 0:
        return None
    return start, end + len("</section>")


def remove_section(text: str, marker: str | re.Pattern[str]) -> tuple[str, bool]:
    bounds = section_bounds(text, marker)
    if not bounds:
        return text, False
    start, end = bounds
    return text[:start] + text[end:], True


def replace_section(text: str, markers: tuple[str | re.Pattern[str], ...], replacement: str) -> tuple[str, bool]:
    for marker in markers:
        bounds = section_bounds(text, marker)
        if bounds:
            start, end = bounds
            return text[:start] + replacement + text[end:], True
    return text, False


def paid_card(label: str) -> str:
    return f'''<aside class="portal-paid-card" data-daily-offer-static="mball-paid-v5" data-paid-suggestion-card="true">
  <small>THANH TOÁN NHẬN GỢI Ý SỐ</small>
  <h2>Gợi ý số MB_ALL - {label}</h2>
  <div class="lm-returning-note">Gợi ý ngày {label} đã sẵn sàng · 30.000đ/ngày · xác nhận thanh toán qua email.</div>
  <div class="portal-paid-lock" aria-label="TOP 1 và TOP 2 được ẩn trước khi thanh toán">
    <div><small>TOP 1</small><b>•• — ••</b></div>
    <div><small>TOP 2</small><b>•• — ••</b></div>
  </div>
  <button type="button" data-open-checkout data-cta-position="portal-hero" aria-label="Thanh toán nhận gợi ý số MB_ALL ngày {label}, giá 30.000 đồng">THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>
  <span class="lm-ai-runtime-kicker">Thanh toán một lần · Không tự gia hạn · Xác nhận qua email</span>
  <p class="portal-paid-note">Gợi ý số chỉ mở sau khi giao dịch được xác nhận. Zalo chỉ dùng để hỗ trợ.</p>
</aside>'''


def overview_section(label: str, lock_label: str) -> str:
    return f'''<section class="portal-section mball-method-overview" data-mball-method-overview="mball-31-live-v3">
  <div class="portal-wrap">
    <div class="portal-section-title">
      <div>
        <p class="mball-overview-kicker">MB_ALL · DATA LOCK {lock_label}</p>
        <h2>MB_ALL chạy đủ 31 phương pháp mỗi ngày</h2>
        <p>Không chọn trước một phương pháp. Hệ thống chạy đủ 31/31 phương pháp bằng dữ liệu đến {lock_label}, sau đó mới đánh giá trạng thái gần và chấm điểm từng số.</p>
      </div>
    </div>
    <div class="portal-methods mball31-process" data-mball31-process="true">
      <article class="portal-method"><div class="portal-method-head"><b>1. Chạy đủ 31/31</b><span>T−1</span></div><p>Mỗi đầu ra chỉ dùng dữ liệu đã hoàn tất đến ngày liền trước; không dùng kết quả ngày đang chọn.</p></article>
      <article class="portal-method"><div class="portal-method-head"><b>2. Đánh giá hiệu quả gần</b><span>3–5–7–10</span></div><p>Đối chiếu W/Hòa/L, chuỗi thắng–thua, P/L, ROI, số nháy và độ ổn định theo các cửa sổ gần.</p></article>
      <article class="portal-method"><div class="portal-method-head"><b>3. Chấm HOT/COLD từng số</b><span>NET SCORE</span></div><p>Tín hiệu tốt cộng điểm, tín hiệu xấu trừ điểm; kiểm soát phiếu trùng và chỉ tính đồng thuận KÉP khi đủ điều kiện.</p></article>
      <article class="portal-method"><div class="portal-method-head"><b>4. Chọn động và khóa</b><span>PRE-DRAW</span></div><p>Không cố định phương pháp hoặc số lượng số. Chỉ giữ các số vượt ngưỡng rồi khóa trước giờ quay.</p></article>
    </div>
    <div class="mball-overview-lock">
      <strong>Đầu ra 31 phương pháp và số cuối được giữ kín</strong>
      <span>Chỉ mở sau khi thanh toán được xác nhận qua email. Kết quả ngày {label} không được dùng để sửa lựa chọn của chính ngày đó.</span>
    </div>
    <p class="portal-disclaimer">MB_ALL là quy trình tổng hợp tín hiệu động, không phải một phương pháp cố định và không công khai các số thành phần trước thanh toán.</p>
  </div>
</section>'''


def buy_section(label: str, lock_label: str) -> str:
    return f'''<section class="buy-simple portal-buy" id="buy" data-paid-suggestion-section="true">
  <div class="wrap buy-simple-card">
    <div><p class="eyebrow">THANH TOÁN NHẬN GỢI Ý SỐ</p><h2>30.000đ/ngày</h2><p class="buy-copy">Thanh toán một lần để nhận gợi ý số MB_ALL đã khóa cho ngày {label}.</p><p class="checkout-scope" id="checkout-scope">Gợi ý ngày {label} · dữ liệu khóa đến {lock_label} · không tự gia hạn.</p></div>
    <div><strong>Xác nhận thanh toán qua email</strong><p>Sau khi chuyển khoản, bấm gửi xác nhận. Chủ dịch vụ kiểm tra giao dịch qua email và gợi ý số tự mở sau khi được phê duyệt.</p></div>
    <button class="button button-primary button-large" type="button" data-open-checkout data-cta-position="final">THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ</button>
  </div>
  <p class="buy-legal">Thanh toán một lần · Không tự gia hạn · Zalo chỉ dùng để hỗ trợ · Không nhận cược · Không trả thưởng.</p>
</section>'''


def extra_style() -> str:
    return '''<style id="mball-live-final-style">
.portal-home .portal-proof,.portal-home .historical-proof-section{display:none!important}.portal-home .mball-method-overview{padding:20px 0!important}.portal-home .mball-method-overview .portal-section-title{align-items:flex-start!important;margin-bottom:12px!important}.portal-home .mball-overview-kicker{margin:0 0 5px!important;color:#b3161b!important;font-size:10px!important;font-weight:1000!important;letter-spacing:.08em!important;text-transform:uppercase!important}.portal-home .mball31-process{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:10px!important}.portal-home .mball31-process .portal-method{min-width:0!important;padding:14px!important;border:1px solid #dfe4e9!important;border-radius:13px!important;background:#fff!important;box-shadow:0 2px 10px rgba(16,35,50,.04)!important}.portal-home .mball31-process .portal-method-head{margin-bottom:7px!important;align-items:flex-start!important}.portal-home .mball31-process .portal-method-head b{font-size:14px!important;line-height:1.3!important}.portal-home .mball31-process .portal-method-head span{flex:0 0 auto!important;background:#f5e9ea!important;color:#a70e15!important;font-size:9px!important;font-weight:1000!important}.portal-home .mball31-process .portal-method p{margin:0!important;color:#5f6e79!important;font-size:12px!important;line-height:1.5!important}.portal-home .mball-overview-lock{display:flex!important;align-items:flex-start!important;justify-content:space-between!important;gap:14px!important;margin-top:11px!important;padding:13px 14px!important;border:1px solid #efc8ca!important;border-radius:13px!important;background:#fff8f8!important}.portal-home .mball-overview-lock strong{display:block!important;color:#a20e15!important;font-size:13px!important}.portal-home .mball-overview-lock span{display:block!important;max-width:760px!important;color:#6f6163!important;font-size:11px!important;line-height:1.5!important}.portal-home .lm-ai-runtime-kicker{display:block;margin-top:8px;color:#79575a;font-size:10px;font-weight:850;line-height:1.4}#mball-zalo-support{position:fixed!important;right:18px!important;bottom:20px!important;z-index:2147483000!important;width:74px!important;height:74px!important;box-sizing:border-box!important;display:flex!important;align-items:center!important;justify-content:center!important;padding:18px 0 0!important;border:4px solid #fff!important;border-radius:50%!important;background:linear-gradient(145deg,#1780ff,#0068ff)!important;color:#fff!important;text-decoration:none!important;text-align:center!important;font-size:12px!important;font-weight:1000!important;line-height:1.05!important;box-shadow:0 12px 28px rgba(0,74,190,.32)!important}#mball-zalo-support::before{content:"Zalo";display:block;position:absolute;top:15px;font-size:12px;font-weight:1000}@media(max-width:900px){.portal-home .mball31-process{grid-template-columns:repeat(2,minmax(0,1fr))!important}}@media(max-width:700px){#mball-zalo-support{right:12px!important;bottom:72px!important;width:66px!important;height:66px!important;border-width:3px!important;font-size:10.5px!important}#mball-zalo-support::before{top:13px;font-size:11px}}@media(max-width:620px){.portal-home .mball31-process{grid-template-columns:1fr!important}.portal-home .mball-overview-lock{display:block!important}.portal-home .mball-overview-lock span{margin-top:4px!important}}
</style>'''


def visible_text(text: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def body_tag(tag: str, label: str, lock_label: str) -> str:
    tag = re.sub(r'\sdata-report-date="[^"]*"', "", tag, flags=re.I)
    tag = re.sub(r'\sdata-(?:lock-date|data-lock)="[^"]*"', "", tag, flags=re.I)
    if "portal-home" not in tag:
        class_match = re.search(r'class="([^"]*)"', tag, flags=re.I)
        if class_match:
            current = class_match.group(1)
            tag = tag[:class_match.start(1)] + "portal-home " + current + tag[class_match.end(1):]
        else:
            tag = tag[:-1] + ' class="portal-home">'
    return tag[:-1] + f' data-report-date="{label}" data-lock-date="{lock_label}">'


def patch_home(path: Path, label: str, lock_label: str, copy_lock_digest: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<title>.*?</title>", "<title>MB_ALL hôm nay – 31 phương pháp chọn lọc động</title>", text, count=1, flags=re.I | re.S)
    description = "MB_ALL chạy đủ 31 phương pháp bằng dữ liệu khóa T−1, đánh giá 3/5/7/10 ngày, P/L, ROI, số nháy và trạng thái HOT/COLD để chọn số động trước giờ quay."
    text = re.sub(r'<meta\s+name="description"\s+content="[^"]*">', f'<meta name="description" content="{description}">', text, count=1, flags=re.I)
    text = re.sub(r"<body\b([^>]*)>", lambda m: body_tag(m.group(0), label, lock_label), text, count=1, flags=re.I)
    text = re.sub(r'(<p class="portal-kicker">).*?(</p>)', r'\1MB_ALL · 31 PHƯƠNG PHÁP\2', text, count=1, flags=re.I | re.S)

    hero = re.search(r'<section\b[^>]*class="[^"]*portal-hero[^"]*"[^>]*>.*?</section>', text, flags=re.I | re.S)
    if hero:
        block = hero.group(0)
        block = re.sub(r"<h1>.*?</h1>", "<h1>MB_ALL – 31 phương pháp<br>chọn lọc động mỗi ngày</h1>", block, count=1, flags=re.I | re.S)
        block = re.sub(r'<p class="portal-lead">.*?</p>', f'<p class="portal-lead">MB_ALL chạy đủ 31 phương pháp bằng dữ liệu đến {lock_label}, đánh giá hiệu quả gần theo 3–5–7–10 ngày, P/L, ROI, số nháy và trạng thái HOT/COLD, rồi chấm điểm trực tiếp từng số. Gợi ý ngày {label} chỉ mở sau khi thanh toán được xác nhận.</p>', block, count=1, flags=re.I | re.S)
        block = re.sub(r'<(?P<tag>aside|div)\b[^>]*class="[^"]*portal-paid-card[^"]*"[^>]*>.*?</(?P=tag)>', paid_card(label), block, count=1, flags=re.I | re.S)
        text = text[:hero.start()] + block + text[hero.end():]

    for marker in (re.compile(r"portal-proof-rate", re.I), re.compile(r"KIỂM ĐỊNH LỊCH SỬ 4SO", re.I), re.compile(r"4SO chỉ công khai hiệu quả tổng hợp", re.I)):
        while True:
            text, changed = remove_section(text, marker)
            if not changed:
                break

    text, changed = replace_section(text, (
        re.compile(r'<h2\b[^>]*>\s*Phương pháp công khai hôm nay\s*</h2>', re.I),
        re.compile(r'<h2\b[^>]*>\s*Gợi ý số(?: ngày)? hôm nay[^<]*</h2>', re.I),
        re.compile(r'<h2\b[^>]*>\s*MB_ALL chạy đủ 31 phương pháp mỗi ngày\s*</h2>', re.I),
    ), overview_section(label, lock_label))
    if not changed:
        anchor = text.find('<section class="buy-simple portal-buy"')
        if anchor < 0:
            anchor = text.lower().find("</main>")
        if anchor < 0:
            raise ValueError("Unable to place MB_ALL method overview")
        text = text[:anchor] + overview_section(label, lock_label) + text[anchor:]

    text, changed = replace_section(text, (
        re.compile(r'<section\b[^>]*class="[^"]*buy-simple[^"]*portal-buy[^"]*"', re.I),
        re.compile(r'<section\b[^>]*class="[^"]*portal-buy[^"]*buy-simple[^"]*"', re.I),
    ), buy_section(label, lock_label))
    if not changed:
        anchor = text.lower().find("</main>")
        if anchor < 0:
            raise ValueError("Unable to place final purchase section")
        text = text[:anchor] + buy_section(label, lock_label) + text[anchor:]

    for old, new in (
        ("MỞ ZALO – NHẬN GỢI Ý HÔM NAY", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ"),
        ("MỞ ZALO - NHẬN GỢI Ý HÔM NAY", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ"),
        ("GỢI Ý SỐ HÔM NAY · MỞ ZALO", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ"),
        ("mở Zalo để trao đổi", "thanh toán 30.000đ để mở"),
        ("Mở Zalo để trao đổi", "Thanh toán 30.000đ để mở"),
    ):
        text = text.replace(old, new)

    text = re.sub(r'<script\s+id="lm-zalo-suggestion-route">.*?</script>', "", text, flags=re.I | re.S)
    text = re.sub(r'\sdata-zalo-route="[^"]*"', "", text, flags=re.I)
    text = re.sub(r'<a\b[^>]*(?:id="mball-zalo-support"|class="[^"]*floating-zalo[^"]*")[^>]*>.*?</a>', "", text, flags=re.I | re.S)
    text = re.sub(r'<style\s+id="(?:mball-live-final-style|mball-round-support-style|mball-method-overview-static-style)">.*?</style>', "", text, flags=re.I | re.S)
    text = re.sub(r'<script\b[^>]*src="[^"]*copy-lock\.js[^\"]*"[^>]*></script>', "", text, flags=re.I)
    if "</head>" not in text or "</body>" not in text:
        raise ValueError("Homepage head/body end missing")
    text = text.replace("</head>", extra_style() + "</head>", 1)
    support = '<a id="mball-zalo-support" class="mball-zalo-support-button" href="/go/zalo.htm" target="_blank" rel="noopener noreferrer" aria-label="Hỗ trợ qua Zalo">Hỗ trợ</a>'
    runtime = f'<script defer src="/copy-lock.js?v={copy_lock_digest}"></script>'
    text = text.replace("</body>", support + runtime + "<!-- MBALL_LIVE_FINAL_V3 --></body>", 1)

    rendered = visible_text(text)
    for forbidden in ("KIỂM ĐỊNH LỊCH SỬ 4SO", "4SO chỉ công khai hiệu quả tổng hợp", "MỞ ZALO – NHẬN GỢI Ý HÔM NAY"):
        if forbidden.lower() in rendered.lower():
            raise ValueError(f"Legacy visible block remains: {forbidden}")
    for required in ("MB_ALL chạy đủ 31 phương pháp mỗi ngày", "3–5–7–10", "HOT/COLD", "PRE-DRAW", "THANH TOÁN NHẬN GỢI Ý SỐ · 30.000Đ", "Xác nhận thanh toán qua email"):
        if required.lower() not in rendered.lower():
            raise ValueError(f"Missing live copy: {required}")
    overview = text.split('data-mball-method-overview="mball-31-live-v3"', 1)[1].split("</section>", 1)[0]
    for forbidden in ("portal-method-numbers", "portal-ball", "portal-consensus"):
        if forbidden in overview:
            raise ValueError(f"Public output remains in MB_ALL overview: {forbidden}")
    if text.count("data-open-checkout") < 2:
        raise ValueError("Paid checkout must have at least two entry points")
    path.write_text(text, encoding="utf-8")


def patch_methods_page(path: Path, label: str, lock_label: str) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    main = f'''<main><section class="portal-page-intro"><p class="eyebrow">MB_ALL · 31 PHƯƠNG PHÁP</p><h1>Quy trình chọn lọc động MB_ALL ngày {label}</h1><p>MB_ALL chạy đủ 31 phương pháp bằng dữ liệu khóa đến {lock_label}. Website không công khai đầu ra từng phương pháp hoặc số cuối trước thanh toán.</p></section><div class="portal-v2-wrap"><section class="portal-v2-card"><h2>Quy trình vận hành hàng ngày</h2><div class="portal-method-grid-v2"><article class="portal-method-card-v2"><header><b>Chạy đủ 31/31</b><span>T−1</span></header><p>Không chọn trước phương pháp; mọi đầu ra đều được tính bằng dữ liệu đã hoàn tất.</p></article><article class="portal-method-card-v2"><header><b>Đánh giá hiệu quả gần</b><span>3–5–7–10</span></header><p>Theo dõi W/Hòa/L, P/L, ROI, số nháy, streak và độ ổn định.</p></article><article class="portal-method-card-v2"><header><b>HOT/COLD theo số</b><span>NET SCORE</span></header><p>Cộng điểm tín hiệu tốt, trừ điểm tín hiệu xấu và kiểm soát phiếu trùng.</p></article><article class="portal-method-card-v2"><header><b>Chọn động và khóa</b><span>PRE-DRAW</span></header><p>Không cố định số lượng; chỉ giữ số vượt ngưỡng rồi khóa trước giờ quay.</p></article></div></section><section class="portal-v2-card"><h2>Phần nào được công khai?</h2><p>Công khai nguyên tắc dữ liệu T−1, cách đánh giá và điều kiện khóa. Đầu ra 31 phương pháp, Net Score từng số và lựa chọn cuối chỉ mở sau khi thanh toán được xác nhận qua email.</p><div class="portal-related"><a href="/thong-ke-xsmb/">Thống kê 00–99</a><a href="/tan-suat-xsmb/">Tần suất</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/?checkout=1">Thanh toán nhận gợi ý số</a></div></section></div></main>'''
    text, count = re.subn(r"<main\b[^>]*>.*?</main>", main, text, count=1, flags=re.I | re.S)
    if count != 1:
        raise ValueError("Unable to rewrite public methods page")
    path.write_text(text, encoding="utf-8")


def write_zalo_redirect(output: Path) -> None:
    target = output / "go" / "zalo.htm"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Đang mở Zalo</title></head><body><p>Đang mở Zalo…</p><script>(()=>{const p=["039","869","6879"].join("");location.replace("https://zalo.me/"+p)})();</script></body></html>', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    output = args.output_root
    methods = load_json(ROOT / "ai-methods" / "public-methods.json")
    label = dmy(str(methods["target_date"]))
    lock_label = dmy(str(methods["data_lock"]))
    copy_source = ROOT / "site-v2" / "copy-lock.js"
    if not copy_source.is_file():
        raise FileNotFoundError(copy_source)
    shutil.copy2(copy_source, output / "copy-lock.js")
    digest = hashlib.sha256(copy_source.read_bytes()).hexdigest()[:12]
    patch_home(output / "index.html", label, lock_label, digest)
    patch_methods_page(output / "phuong-phap-cong-khai" / "index.html", label, lock_label)
    write_zalo_redirect(output)
    status = {"status": "PASS", "home": "MBALL_31_LIVE_V3", "report_date": label, "data_lock": lock_label, "paid_checkout": True, "zalo_support_only": True, "legacy_70_removed": True, "public_six_method_outputs_removed": True, "copy_lock_sha": digest}
    (output / "mball-live-status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()
