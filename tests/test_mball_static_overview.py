from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sitecustomize as hooks  # noqa: E402


with tempfile.TemporaryDirectory() as tmp:
    output = Path(tmp)
    home = output / "index.html"
    methods = output / "phuong-phap-cong-khai" / "index.html"
    methods.parent.mkdir(parents=True)

    home.write_text(
        '''<!doctype html><html><head></head><body class="portal-home" data-report-date="22/08/2026">
<main><p>Data lock 21/08/2026</p>
<section class="portal-section"><div class="portal-wrap"><div class="portal-section-title"><div>
<h2 data-daily-recommendation-heading="v2">Gợi ý số ngày hôm nay - 22/08/2026</h2><p>old</p>
</div></div><div class="portal-methods"><article class="portal-method"><div class="portal-method-numbers"><span class="portal-ball">98</span></div></article></div><div class="portal-consensus">old</div><p class="portal-disclaimer">old</p></div></section>
</main></body></html>''',
        encoding="utf-8",
    )
    methods.write_text(
        '<!doctype html><html><head></head><body><main><h1>6 phương pháp</h1><div>98</div></main></body></html>',
        encoding="utf-8",
    )

    previous = sys.argv[:]
    try:
        sys.argv = ["optimize_portal_v2_run.py", "--output-root", str(output)]
        hooks._finalize_mball_home_overview()
    finally:
        sys.argv = previous

    rendered = home.read_text(encoding="utf-8")
    public_page = methods.read_text(encoding="utf-8")

    assert "MB_ALL chạy đủ 31 phương pháp mỗi ngày" in rendered
    assert "3–5–7–10" in rendered
    assert "HOT/COLD" in rendered
    assert "PRE-DRAW" in rendered
    assert "Đầu ra 31 phương pháp và số cuối được giữ kín" in rendered
    visible = rendered.split('data-mball-method-overview="mball-31-static-v2"', 1)[1].split("</section>", 1)[0]
    assert "portal-method-numbers" not in visible
    assert "portal-ball" not in visible
    assert "portal-consensus" not in visible

    assert "Quy trình chọn lọc động MB_ALL ngày 22/08/2026" in public_page
    assert "Website không công khai đầu ra từng phương pháp" in public_page
    assert "98" not in public_page

print("MBALL_31_METHOD_OVERVIEW_STATIC_TEST_OK")
