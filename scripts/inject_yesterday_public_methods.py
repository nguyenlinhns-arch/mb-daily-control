#!/usr/bin/env python3
"""Retire the yesterday-method block and keep a small retention hook.

The homepage no longer publishes the long yesterday-method proof block. The
compatibility hook now only removes any legacy artifact and injects a compact,
privacy-preserving returning-buyer personalization. A buyer is recognized only
from prior local purchase markers already stored in that browser; no account,
phone number, email address or prior paid output is exposed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'data-yesterday-public-methods="true"'
STYLE_ID = "lm-yesterday-public-methods-style"
RETENTION_ID = "lm-ai-retention-v1"

RETENTION_SCRIPT = r'''<script id="lm-ai-retention-v1">(()=>{
  "use strict";
  const PURCHASE_PREFIX="lemienbac_purchase_";
  const emit=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,...extra})};
  const currentReportDate=()=>String(document.body?.dataset?.reportDate||"").trim();
  const currentStamp=()=>{const value=currentReportDate();const m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);return m?`${m[3].slice(-2)}${m[2]}${m[1]}`:""};
  const priorPurchases=()=>{const stamps=[];try{for(let i=0;i<localStorage.length;i+=1){const key=localStorage.key(i)||"";if(!key.startsWith(PURCHASE_PREFIX))continue;const m=/^lemienbac_purchase_AI-(\d{6})-[A-Z0-9]+$/i.exec(key);if(m)stamps.push(m[1]);}}catch(_){}return stamps};
  const run=()=>{
    if(location.pathname!=="/")return;
    const current=currentStamp();
    const purchases=priorPurchases();
    const prior=purchases.filter(stamp=>stamp&&stamp!==current);
    if(!prior.length)return;
    const uniqueDays=new Set(prior);
    document.body.dataset.returningAiBuyer="true";
    const style=document.createElement("style");
    style.id="lm-ai-retention-style";
    style.textContent='body[data-returning-ai-buyer="true"] .lm-product-deals,body[data-returning-ai-buyer="true"] .lm-affiliate-section{display:none!important}.lm-returning-note{display:flex;align-items:center;gap:7px;margin:7px 0 9px;padding:8px 10px;border:1px solid #d7e8dc;border-radius:10px;background:#f3faf5;color:#355d42;font-size:10.5px;font-weight:850;line-height:1.35}.lm-returning-note:before{content:"✓";width:18px;height:18px;display:grid;place-items:center;border-radius:50%;background:#dcefe2;color:#2f6840;font-size:10px;font-weight:1000}@media(max-width:700px){.lm-returning-note{font-size:10px;padding:7px 9px}}';
    document.head.appendChild(style);
    const card=document.querySelector(".portal-paid-card");
    if(card){
      const small=card.querySelector("small");
      if(small)small.textContent="BẠN ĐÃ TỪNG MỞ BẢN AI";
      const title=card.querySelector("h2");
      if(title&&!card.querySelector(".lm-returning-note"))title.insertAdjacentHTML("afterend",'<div class="lm-returning-note">Bản hôm nay đã sẵn sàng · thanh toán một lần · không cần tạo tài khoản.</div>');
    }
    const sticky=document.querySelector("[data-ai-sticky-cta]");
    if(sticky)sticky.textContent="MỞ LẠI BẢN AI HÔM NAY · 30.000Đ";
    emit("ai_returning_buyer_view",{prior_purchase_markers:prior.length,prior_purchase_days:uniqueDays.size});
    document.addEventListener("click",event=>{const target=event.target instanceof Element?event.target:null;if(!target)return;const cta=target.closest("[data-open-checkout],[data-ai-sticky-cta]");if(cta)emit("ai_returning_buyer_checkout",{prior_purchase_days:uniqueDays.size,placement:cta.hasAttribute("data-ai-sticky-cta")?"sticky":cta.closest(".portal-paid-card")?"hero":"purchase"});});
  };
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",run,{once:true});else run();
})();</script>'''


def apply(root: Path) -> dict[str, Any]:
    home = root / "index.html"
    if not home.is_file():
        raise FileNotFoundError(home)

    text = home.read_text(encoding="utf-8")
    before = text
    text = re.sub(
        r'<section\b[^>]*data-yesterday-public-methods="true"[^>]*>.*?</section>',
        '',
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'<style\b[^>]*id="lm-yesterday-public-methods-style"[^>]*>.*?</style>',
        '',
        text,
        flags=re.I | re.S,
    )
    text = re.sub(
        r'<script\b[^>]*id="lm-ai-retention-v1"[^>]*>.*?</script>',
        '',
        text,
        flags=re.I | re.S,
    )
    if MARKER in text or STYLE_ID in text:
        raise ValueError("Retired yesterday-method block still present")
    if "</body>" not in text:
        raise ValueError("Homepage missing </body>")
    text = text.replace("</body>", RETENTION_SCRIPT + "\n</body>", 1)
    if f'id="{RETENTION_ID}"' not in text:
        raise ValueError("Returning-buyer retention hook missing")
    home.write_text(text, encoding="utf-8")

    legacy = root / "yesterday-public-methods.json"
    if legacy.exists():
        legacy.unlink()

    return {
        "status": "PASS",
        "homepage_block": False,
        "public_json": False,
        "retention": True,
        "changed": text != before,
    }


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.joinpath("index.html").write_text(
            '<html><head><style id="lm-yesterday-public-methods-style">x</style></head>'
            '<body><main><section data-yesterday-public-methods="true">old</section>'
            '<section><h2>Công cụ thống kê XSMB</h2></section></main></body></html>',
            encoding="utf-8",
        )
        root.joinpath("yesterday-public-methods.json").write_text('{}', encoding="utf-8")
        result = apply(root)
        output = root.joinpath("index.html").read_text(encoding="utf-8")
        assert result["status"] == "PASS" and result["retention"] is True
        assert MARKER not in output and STYLE_ID not in output
        assert f'id="{RETENTION_ID}"' in output
        assert "ai_returning_buyer_view" in output and "ai_returning_buyer_checkout" in output
        assert not root.joinpath("yesterday-public-methods.json").exists()
    print("AI_RETENTION_HOOK_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT / "_site")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(apply(args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
