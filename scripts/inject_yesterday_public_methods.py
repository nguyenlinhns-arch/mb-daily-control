#!/usr/bin/env python3
"""Retire the yesterday-method block and keep compact revenue-retention hooks.

The homepage no longer publishes the long yesterday-method proof block. This
compatibility hook removes legacy artifacts, personalizes the AI CTA for prior
buyers on the same browser, adds a post-purchase Zalo follow-up, and reduces
mobile payment friction with copy-ready transfer fields. No account, phone,
email, prior paid output or canonical 4SO value is exposed.
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
  const ZALO_URL="https://zalo.me/0398696879";
  const BANK_ACCOUNT="1128091987";
  const emit=(event,extra={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,page_path:location.pathname,...extra})};
  const currentReportDate=()=>String(document.body?.dataset?.reportDate||"").trim();
  const currentStamp=()=>{const value=currentReportDate();const m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);return m?`${m[3].slice(-2)}${m[2]}${m[1]}`:""};
  const priorPurchases=()=>{const stamps=[];try{for(let i=0;i<localStorage.length;i+=1){const key=localStorage.key(i)||"";if(!key.startsWith(PURCHASE_PREFIX))continue;const m=/^lemienbac_purchase_AI-(\d{6})-[A-Z0-9]+$/i.exec(key);if(m)stamps.push(m[1]);}}catch(_){}return stamps};
  const addStyle=()=>{if(document.getElementById("lm-ai-retention-style"))return;const style=document.createElement("style");style.id="lm-ai-retention-style";style.textContent='body[data-returning-ai-buyer="true"] .lm-product-deals,body[data-returning-ai-buyer="true"] .lm-affiliate-section{display:none!important}.lm-returning-note{display:flex;align-items:center;gap:7px;margin:7px 0 9px;padding:8px 10px;border:1px solid #d7e8dc;border-radius:10px;background:#f3faf5;color:#355d42;font-size:10.5px;font-weight:850;line-height:1.35}.lm-returning-note:before{content:"✓";width:18px;height:18px;display:grid;place-items:center;border-radius:50%;background:#dcefe2;color:#2f6840;font-size:10px;font-weight:1000}.lm-postpurchase-zalo{margin-top:12px;padding:11px 12px;border:1px solid #cfe2f1;border-radius:12px;background:#f4faff}.lm-postpurchase-zalo b{display:block;color:#24475e;font-size:12px}.lm-postpurchase-zalo span{display:block;margin-top:3px;color:#637986;font-size:10.5px;line-height:1.4}.lm-postpurchase-zalo a{display:inline-flex;margin-top:8px;min-height:40px;align-items:center;justify-content:center;padding:0 12px;border-radius:10px;background:#0877c9;color:#fff!important;text-decoration:none!important;font-size:11px;font-weight:950}.lm-fastpay{margin-top:10px;padding:10px;border:1px solid #dce5eb;border-radius:12px;background:#f8fbfd}.lm-fastpay-title{display:block;color:#344f61;font-size:11px;font-weight:900}.lm-fastpay-note{display:block;margin-top:2px;color:#71828d;font-size:9.5px;line-height:1.35}.lm-fastpay-actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.lm-fastpay-btn{min-height:42px;border:1px solid #cbd8e1;border-radius:10px;background:#fff;color:#29475a;font:inherit;font-size:10.5px;font-weight:950;cursor:pointer}.lm-fastpay-btn.is-copied{border-color:#b9d9c1;background:#edf8f0;color:#2f6840}.lm-fastpay-status{min-height:16px;margin-top:5px;color:#567061;font-size:9px;font-weight:800}.lm-fastpay-value{font-variant-numeric:tabular-nums}@media(max-width:700px){.lm-returning-note{font-size:10px;padding:7px 9px}.lm-postpurchase-zalo{padding:10px}.lm-postpurchase-zalo a{width:100%;min-height:44px}.lm-fastpay{padding:9px}.lm-fastpay-actions{grid-template-columns:1fr}.lm-fastpay-btn{min-height:46px;font-size:11px}}';document.head.appendChild(style)};
  const copyText=async(value)=>{const text=String(value||"").trim();if(!text)return false;try{if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(text);return true;}}catch(_){}try{const area=document.createElement("textarea");area.value=text;area.setAttribute("readonly","");area.style.position="fixed";area.style.opacity="0";document.body.appendChild(area);area.select();const ok=document.execCommand("copy");area.remove();return ok;}catch(_){return false;}};
  const flashCopy=(button,status,message)=>{button.classList.add("is-copied");const original=button.textContent;button.textContent="ĐÃ SAO CHÉP ✓";status.textContent=message;window.setTimeout(()=>{button.classList.remove("is-copied");button.textContent=original;},1800)};
  const installFastPay=()=>{
    addStyle();const payment=document.querySelector(".payment-card");const memo=document.getElementById("payment-memo");if(!payment||!memo||payment.querySelector(".lm-fastpay"))return false;
    const box=document.createElement("div");box.className="lm-fastpay";box.innerHTML='<span class="lm-fastpay-title">Thanh toán trên chính điện thoại này?</span><span class="lm-fastpay-note">Sao chép nhanh rồi chuyển sang app ngân hàng. Số tiền vẫn là 30.000đ và nội dung phải giữ nguyên.</span><div class="lm-fastpay-actions"><button type="button" class="lm-fastpay-btn" data-copy-account>Sao chép STK <span class="lm-fastpay-value">'+BANK_ACCOUNT+'</span></button><button type="button" class="lm-fastpay-btn" data-copy-memo>Sao chép nội dung</button></div><div class="lm-fastpay-status" aria-live="polite"></div>';
    payment.appendChild(box);const status=box.querySelector(".lm-fastpay-status");const accountBtn=box.querySelector("[data-copy-account]");const memoBtn=box.querySelector("[data-copy-memo]");
    accountBtn?.addEventListener("click",async()=>{if(await copyText(BANK_ACCOUNT)){flashCopy(accountBtn,status,"Đã sao chép số tài khoản VPBank.");emit("ai_payment_copy_account",{report_date:currentReportDate()});}else status.textContent="Không sao chép tự động được. Hãy nhấn giữ số tài khoản để sao chép.";});
    memoBtn?.addEventListener("click",async()=>{const value=String(memo.textContent||"").trim();if(!/^\d{12}$/.test(value)){status.textContent="Nội dung chuyển khoản đang được tạo. Vui lòng thử lại sau một giây.";return;}if(await copyText(value)){flashCopy(memoBtn,status,"Đã sao chép đúng nội dung chuyển khoản.");emit("ai_payment_copy_memo",{report_date:currentReportDate()});}else status.textContent="Không sao chép tự động được. Hãy nhấn giữ nội dung để sao chép.";});
    emit("ai_fastpay_view",{report_date:currentReportDate()});return true;
  };
  const personalizeReturning=()=>{
    if(location.pathname!=="/")return;
    const current=currentStamp();const purchases=priorPurchases();const prior=purchases.filter(stamp=>stamp&&stamp!==current);if(!prior.length)return;
    const uniqueDays=new Set(prior);document.body.dataset.returningAiBuyer="true";addStyle();
    const card=document.querySelector(".portal-paid-card");if(card){const small=card.querySelector("small");if(small)small.textContent="BẠN ĐÃ TỪNG MỞ BẢN AI";const title=card.querySelector("h2");if(title&&!card.querySelector(".lm-returning-note"))title.insertAdjacentHTML("afterend",'<div class="lm-returning-note">Bản hôm nay đã sẵn sàng · thanh toán một lần · không cần tạo tài khoản.</div>');}
    const sticky=document.querySelector("[data-ai-sticky-cta]");if(sticky)sticky.textContent="MỞ LẠI BẢN AI HÔM NAY · 30.000Đ";
    emit("ai_returning_buyer_view",{prior_purchase_markers:prior.length,prior_purchase_days:uniqueDays.size});
    document.addEventListener("click",event=>{const target=event.target instanceof Element?event.target:null;if(!target)return;const cta=target.closest("[data-open-checkout],[data-ai-sticky-cta]");if(cta)emit("ai_returning_buyer_checkout",{prior_purchase_days:uniqueDays.size,placement:cta.hasAttribute("data-ai-sticky-cta")?"sticky":cta.closest(".portal-paid-card")?"hero":"purchase"});});
  };
  const installPostPurchaseZalo=()=>{
    addStyle();const delivery=document.getElementById("delivery-view");if(!delivery)return;
    const render=()=>{if(delivery.hidden!==false||delivery.dataset.rendered!=="true"||delivery.querySelector(".lm-postpurchase-zalo"))return;const box=document.createElement("div");box.className="lm-postpurchase-zalo";box.innerHTML='<b>Muốn nhận nhắc khi bản AI ngày mới sẵn sàng?</b><span>Nhắn Zalo sau khi đã xem báo cáo. Đây là tùy chọn, không ảnh hưởng quyền truy cập hiện tại.</span><a href="'+ZALO_URL+'" target="_blank" rel="noopener noreferrer" data-postpurchase-zalo="true">NHẮN ZALO ĐỂ NHẬN NHẮC →</a>';delivery.appendChild(box);emit("ai_postpurchase_zalo_view",{report_date:currentReportDate()});box.querySelector("a")?.addEventListener("click",()=>emit("ai_postpurchase_zalo_click",{report_date:currentReportDate()}));};
    render();const observer=new MutationObserver(render);observer.observe(delivery,{attributes:true,attributeFilter:["hidden","data-rendered"],childList:true,subtree:true});
  };
  const installFastPayObserver=()=>{if(installFastPay())return;const observer=new MutationObserver(()=>{if(installFastPay())observer.disconnect()});observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["hidden"]});window.setTimeout(()=>observer.disconnect(),180000)};
  const run=()=>{if(location.pathname!=="/")return;personalizeReturning();installPostPurchaseZalo();installFastPayObserver()};
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
        raise ValueError("Revenue retention hook missing")
    home.write_text(text, encoding="utf-8")

    legacy = root / "yesterday-public-methods.json"
    if legacy.exists():
        legacy.unlink()

    return {
        "status": "PASS",
        "homepage_block": False,
        "public_json": False,
        "returning_buyer_personalization": True,
        "postpurchase_zalo": True,
        "mobile_fastpay": True,
        "changed": text != before,
    }


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.joinpath("index.html").write_text(
            '<html><head><style id="lm-yesterday-public-methods-style">x</style></head>'
            '<body><main><section data-yesterday-public-methods="true">old</section>'
            '<section><h2>Công cụ thống kê XSMB</h2></section></main><div class="payment-card"><div id="payment-memo">123456789012</div></div><div id="delivery-view"></div></body></html>',
            encoding="utf-8",
        )
        root.joinpath("yesterday-public-methods.json").write_text('{}', encoding="utf-8")
        result = apply(root)
        output = root.joinpath("index.html").read_text(encoding="utf-8")
        assert result["status"] == "PASS"
        assert result["returning_buyer_personalization"] is True and result["postpurchase_zalo"] is True and result["mobile_fastpay"] is True
        assert MARKER not in output and STYLE_ID not in output
        assert f'id="{RETENTION_ID}"' in output
        for marker in ("ai_returning_buyer_view", "ai_returning_buyer_checkout", "ai_postpurchase_zalo_view", "ai_postpurchase_zalo_click", "ai_fastpay_view", "ai_payment_copy_account", "ai_payment_copy_memo"):
            assert marker in output
        assert not root.joinpath("yesterday-public-methods.json").exists()
    print("AI_REVENUE_RETENTION_SELF_TEST_OK")


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
