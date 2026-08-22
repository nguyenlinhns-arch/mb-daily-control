#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import finalize_mball_website as base


def replace_method_section(text: str, target: str, lock: str) -> str:
    """Replace only the section that actually contains the public method grid.

    The homepage also has a paid-card H2 beginning with "Gợi ý số". Selecting
    by heading alone can therefore replace the hero instead of the retired
    public-number panel. This selector requires the method/consensus structure.
    """
    sections = list(re.finditer(r'<section\b[^>]*class="[^"]*portal-section[^"]*"[^>]*>.*?</section>', text, flags=re.I | re.S))
    for match in sections:
        block = match.group(0)
        if not re.search(r'class="[^"]*portal-methods|class="[^"]*portal-consensus|data-mball-method-overview', block, flags=re.I):
            continue
        if not re.search(r'Phương pháp công khai|Gợi ý số|MB_ALL chạy đủ 31 phương pháp', block, flags=re.I):
            continue
        return text[: match.start()] + base.method_overview(target, lock) + text[match.end() :]
    raise RuntimeError("Unable to find the public method-output section")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("_site"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    base.replace_method_section = replace_method_section
    if args.self_test:
        base.main = lambda: None
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "phuong-phap-cong-khai").mkdir()
            (root / "phuong-phap-cong-khai" / "index.html").write_text("<html><body><main>old</main></body></html>", encoding="utf-8")
            (root / "index.html").write_text('''<html><head><script src="config.js?v=old"></script></head><body class="portal-home" data-report-date="22/08/2026" data-lock-date="21/08/2026"><main><section class="portal-hero"><div><p class="portal-kicker">old</p><h1>old</h1><p class="portal-lead">old</p></div><aside class="portal-paid-card"><small>old</small><h2>Gợi ý số hôm nay - 22/08/2026</h2><div class="portal-paid-lock"><div>TOP 1</div><div>TOP 2</div></div><button data-open-checkout>MỞ ZALO – NHẬN GỢI Ý HÔM NAY</button></aside></section><section class="portal-section"><div class="portal-section-title"><h2>Gợi ý số hôm nay - 22/08/2026</h2></div><div class="portal-methods"><span class="portal-ball">98</span></div><div class="portal-consensus">old</div></section><section class="portal-section"><div class="portal-proof"><div>KIỂM ĐỊNH LỊCH SỬ 4SO 70%</div></div></section><section class="buy-simple portal-buy"><button data-open-checkout>MỞ ZALO – NHẬN GỢI Ý HÔM NAY</button></section></main><div id="checkout"><p class="zalo-instruction">old</p><button class="payment-confirm" id="payment-self-confirm">old</button></div></body></html>''', encoding="utf-8")
            base.finalize(root)
            output = (root / "index.html").read_text(encoding="utf-8")
            assert "portal-hero" in output
            assert "MB_ALL chạy đủ 31 phương pháp mỗi ngày" in output
            assert "KIỂM ĐỊNH LỊCH SỬ 4SO" not in base.visible_text(output)
            assert "MỞ ZALO – NHẬN GỢI Ý HÔM NAY" not in base.visible_text(output)
        print("RUN_FINAL_MBALL_DEPLOY_SELF_TEST_OK")
        return

    base.finalize(args.output_root)
    print("RUN_FINAL_MBALL_DEPLOY_OK")


if __name__ == "__main__":
    main()
