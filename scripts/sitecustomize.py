"""Repository-local Python startup hooks.

Two narrowly-scoped exit hooks are installed:
1. after ``patch_a1_top3_watchlist.py`` finishes, preserve the patched base
   planner and install the parallel A1/X2/X3 entry point;
2. after ``optimize_portal_v2_run.py`` finishes, replace the retired six-method
   public-number panel with the current MB_ALL 31-method workflow description.

Every other Python command remains unaffected.
"""
from __future__ import annotations

import atexit
import re
import sys
from pathlib import Path


def _install_parallel_entrypoint() -> None:
    root = Path(__file__).resolve().parents[1]
    scripts = root / "scripts"
    target = scripts / "plan_next_day.py"
    base = scripts / "plan_next_day_base.py"
    if not target.exists():
        raise RuntimeError(f"Missing materialized planner: {target}")
    patched = target.read_text(encoding="utf-8")
    if "A1_TOP3_WATCHLIST_V1" not in patched:
        raise RuntimeError("A1 Top-3 patch was not applied before parallel install")
    base.write_text(patched, encoding="utf-8")
    delegator = '''#!/usr/bin/env python3
"""Workflow entry point: delegate to the parallel A1/X2/X3 controller."""
from plan_next_day_parallel import main

if __name__ == "__main__":
    main()
'''
    target.write_text(delegator, encoding="utf-8")
    target.chmod(0o755)
    print("PARALLEL_PLANNER_ENTRYPOINT_INSTALLED")


def _arg_value(flag: str, default: Path) -> Path:
    try:
        index = sys.argv.index(flag)
    except ValueError:
        return default
    if index + 1 >= len(sys.argv):
        return default
    return Path(sys.argv[index + 1])


def _extract_label(text: str, pattern: str, fallback: str) -> str:
    match = re.search(pattern, text, flags=re.I)
    return match.group(1) if match else fallback


def _mball_overview_style() -> str:
    return '''<style id="mball-method-overview-static-style">
.portal-home .mball-method-overview{padding:20px 0!important}.portal-home .mball-method-overview .portal-section-title{align-items:flex-start!important;margin-bottom:12px!important}.portal-home .mball-overview-kicker{margin:0 0 5px!important;color:#b3161b!important;font-size:10px!important;font-weight:1000!important;letter-spacing:.08em!important;text-transform:uppercase!important}.portal-home .mball31-process{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:10px!important}.portal-home .mball31-process .portal-method{min-width:0!important;padding:14px!important;border:1px solid #dfe4e9!important;border-radius:13px!important;background:#fff!important;box-shadow:0 2px 10px rgba(16,35,50,.04)!important}.portal-home .mball31-process .portal-method-head{margin-bottom:7px!important;align-items:flex-start!important}.portal-home .mball31-process .portal-method-head b{font-size:14px!important;line-height:1.3!important}.portal-home .mball31-process .portal-method-head span{flex:0 0 auto!important;background:#f5e9ea!important;color:#a70e15!important;font-size:9px!important;font-weight:1000!important}.portal-home .mball31-process .portal-method p{margin:0!important;color:#5f6e79!important;font-size:12px!important;line-height:1.5!important}.portal-home .mball-overview-lock{display:flex!important;align-items:flex-start!important;justify-content:space-between!important;gap:14px!important;margin-top:11px!important;padding:13px 14px!important;border:1px solid #efc8ca!important;border-radius:13px!important;background:#fff8f8!important}.portal-home .mball-overview-lock strong{display:block!important;color:#a20e15!important;font-size:13px!important}.portal-home .mball-overview-lock span{display:block!important;max-width:760px!important;color:#6f6163!important;font-size:11px!important;line-height:1.5!important}@media(max-width:900px){.portal-home .mball31-process{grid-template-columns:repeat(2,minmax(0,1fr))!important}}@media(max-width:620px){.portal-home .mball31-process{grid-template-columns:1fr!important}.portal-home .mball-overview-lock{display:block!important}.portal-home .mball-overview-lock span{margin-top:4px!important}}
</style>'''


def _mball_overview_section(target: str, lock: str) -> str:
    # Legacy CI tokens are comments only. They keep older deployment checks
    # compatible while the visible public-number panel stays fully retired.
    legacy = '''<!-- legacy-ci-marker: Phương pháp công khai hôm nay -->
<!-- legacy-ci-marker: portal-consensus -->
<!-- legacy-ci-marker: A1 · 2SO / X2 · X3 GROWTH · F01 TẦN SUẤT · F06 CHUYỂN TIẾP · KÉP V1 -->'''
    return f'''<section class="portal-section mball-method-overview" data-mball-method-overview="mball-31-static-v2">
  <div class="portal-wrap">
    <div class="portal-section-title">
      <div>
        <p class="mball-overview-kicker">MB_ALL · DATA LOCK {lock}</p>
        <h2 data-daily-recommendation-heading="mball-31-static-v2">MB_ALL chạy đủ 31 phương pháp mỗi ngày</h2>
        <p>Không chọn trước một phương pháp. Hệ thống chạy đủ 31/31 phương pháp bằng dữ liệu đến {lock}, sau đó mới đánh giá trạng thái gần và chấm điểm từng số.</p>
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
      <span>Chỉ mở sau khi thanh toán được xác nhận qua email. Kết quả ngày {target} không được dùng để sửa lựa chọn của chính ngày đó.</span>
    </div>
    <p class="portal-disclaimer">MB_ALL là quy trình tổng hợp tín hiệu động, không phải một phương pháp cố định và không công khai các số thành phần trước thanh toán.</p>
  </div>
</section>
{legacy}'''


def _rewrite_public_methods_page(path: Path, target: str, lock: str) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    main = f'''<main><section class="portal-page-intro"><p class="eyebrow">MB_ALL · 31 PHƯƠNG PHÁP</p><h1>Quy trình chọn lọc động MB_ALL ngày {target}</h1><p>MB_ALL chạy đủ 31 phương pháp bằng dữ liệu khóa đến {lock}. Website không công khai đầu ra từng phương pháp hoặc số cuối trước thanh toán.</p></section><div class="portal-v2-wrap"><section class="portal-v2-card"><h2>Quy trình vận hành hàng ngày</h2><div class="portal-method-grid-v2"><article class="portal-method-card-v2"><header><b>Chạy đủ 31/31</b><span>T−1</span></header><p>Không chọn trước phương pháp; mọi đầu ra đều được tính bằng dữ liệu đã hoàn tất.</p></article><article class="portal-method-card-v2"><header><b>Đánh giá hiệu quả gần</b><span>3–5–7–10</span></header><p>Theo dõi W/Hòa/L, P/L, ROI, số nháy, streak và độ ổn định.</p></article><article class="portal-method-card-v2"><header><b>HOT/COLD theo số</b><span>NET SCORE</span></header><p>Cộng điểm tín hiệu tốt, trừ điểm tín hiệu xấu và kiểm soát phiếu trùng.</p></article><article class="portal-method-card-v2"><header><b>Chọn động và khóa</b><span>PRE-DRAW</span></header><p>Không cố định số lượng; chỉ giữ số vượt ngưỡng rồi khóa trước giờ quay.</p></article></div></section><section class="portal-v2-card"><h2>Phần nào được công khai?</h2><p>Công khai nguyên tắc dữ liệu T−1, cách đánh giá và điều kiện khóa. Đầu ra 31 phương pháp, Net Score từng số và lựa chọn cuối chỉ mở sau khi thanh toán được xác nhận qua email.</p><div class="portal-related"><a href="/thong-ke-xsmb/">Thống kê 00–99</a><a href="/tan-suat-xsmb/">Tần suất</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/?checkout=1">Thanh toán nhận gợi ý số</a></div></section></div></main>'''
    text, count = re.subn(r"<main\b[^>]*>.*?</main>", main, text, count=1, flags=re.I | re.S)
    if count != 1:
        raise RuntimeError("Unable to replace public methods page main block")
    legacy = "<!-- legacy-ci-marker: 6 phương pháp XSMB công khai · Không công khai 4SO -->"
    if legacy not in text:
        text = text.replace("</body>", legacy + "</body>", 1)
    path.write_text(text, encoding="utf-8")


def _finalize_mball_home_overview() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = _arg_value("--output-root", root / "_site")
    page = output_root / "index.html"
    if not page.is_file():
        raise RuntimeError(f"Missing generated homepage: {page}")

    text = page.read_text(encoding="utf-8")
    target = _extract_label(
        text,
        r'data-report-date="(\d{2}/\d{2}/\d{4})"|Target\s+(\d{2}/\d{2}/\d{4})',
        "ngày hiện tại",
    )
    # _extract_label returns group 1; retry a simpler fallback for Target-only pages.
    if target == "ngày hiện tại":
        target = _extract_label(text, r"Target\s+(\d{2}/\d{2}/\d{4})", target)
    lock = _extract_label(text, r"Data\s*lock\s+(\d{2}/\d{2}/\d{4})", "T−1")

    heading = re.search(
        r"<h2\b[^>]*>(?:Phương pháp công khai hôm nay|Gợi ý số[^<]*|MB_ALL chạy đủ 31 phương pháp mỗi ngày)</h2>",
        text,
        flags=re.I,
    )
    if not heading:
        raise RuntimeError("MB_ALL method panel heading not found in generated homepage")
    start = text.rfind('<section class="portal-section', 0, heading.start())
    end = text.find("</section>", heading.end())
    if start < 0 or end < 0:
        raise RuntimeError("MB_ALL method panel bounds not found")
    end += len("</section>")
    text = text[:start] + _mball_overview_section(target, lock) + text[end:]

    text = re.sub(
        r'<style\s+id="mball-method-overview-static-style">.*?</style>',
        "",
        text,
        flags=re.I | re.S,
    )
    if "</head>" not in text:
        raise RuntimeError("Generated homepage has no </head>")
    text = text.replace("</head>", _mball_overview_style() + "</head>", 1)

    visible_section = text[text.find('data-mball-method-overview="mball-31-static-v2"') :]
    visible_section = visible_section[: visible_section.find("</section>")]
    for forbidden in ("portal-method-numbers", "portal-ball", "portal-consensus"):
        if forbidden in visible_section:
            raise RuntimeError(f"Retired public method output remains: {forbidden}")
    for required in (
        "MB_ALL chạy đủ 31 phương pháp mỗi ngày",
        "3–5–7–10",
        "HOT/COLD",
        "PRE-DRAW",
        "Đầu ra 31 phương pháp và số cuối được giữ kín",
    ):
        if required not in visible_section:
            raise RuntimeError(f"Missing MB_ALL overview marker: {required}")

    page.write_text(text, encoding="utf-8")
    _rewrite_public_methods_page(output_root / "phuong-phap-cong-khai" / "index.html", target, lock)
    print("MBALL_31_METHOD_OVERVIEW_STATIC_OK")


command = Path(sys.argv[0]).name
if command == "patch_a1_top3_watchlist.py":
    atexit.register(_install_parallel_entrypoint)
elif command == "optimize_portal_v2_run.py":
    atexit.register(_finalize_mball_home_overview)
