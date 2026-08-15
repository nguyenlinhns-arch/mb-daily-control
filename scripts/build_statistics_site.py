#!/usr/bin/env python3
"""Build descriptive XSMB statistics pages from the canonical 27-code history.

The output is public historical analysis only. It never reads or publishes
canonical/final 4SO pairs, scores, rankings or paid conclusions. Shopee
placements are fail-closed until real Affiliate Custom Links are configured.
"""
from __future__ import annotations

import argparse, base64, bz2, csv, hashlib, html, io, json, re, tempfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history-27.bz2.b64"
AFFILIATE = ROOT / "data" / "affiliate-offers.json"
BASE = "https://lemienbac.com"
VN = timezone(timedelta(hours=7))
WINDOWS = (7, 14, 30, 60, 100, 365)
FORBIDDEN = re.compile(r"(?:final|canonical)[_-]?(?:codes|pairs)", re.I)


def esc(x: Any) -> str:
    return html.escape(str(x), quote=True)


def code2(x: Any) -> str:
    s = "".join(c for c in str(x or "") if c.isdigit())
    if not s:
        raise ValueError(f"Mã không hợp lệ: {x!r}")
    return s[-2:].zfill(2)


def parse_day(x: Any) -> date | None:
    s = str(x or "").strip()
    for value in (s[:10], s):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
        for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
    return None


def row_container(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("values", "rows", "history", "data", "records"):
            if isinstance(payload.get(key), list):
                return payload[key]
        mapped = [[k, *v] for k, v in payload.items() if parse_day(k) and isinstance(v, list) and len(v) == 27]
        if mapped:
            return mapped
    raise ValueError("Không tìm thấy mảng lịch sử")


def parse_rows(rows: list[Any]) -> list[tuple[date, list[str]]]:
    out: dict[date, list[str]] = {}
    for raw in rows:
        day, codes = None, None
        if isinstance(raw, dict):
            day = parse_day(raw.get("date") or raw.get("draw_date") or raw.get("ngay"))
            codes = raw.get("codes") or raw.get("values") or raw.get("lottery_codes")
            if codes is None:
                keys = [f"L{i:02d}" for i in range(1, 28)]
                if all(k in raw for k in keys):
                    codes = [raw[k] for k in keys]
        elif isinstance(raw, (list, tuple)) and len(raw) >= 28:
            day, codes = parse_day(raw[0]), raw[1:28]
        if day is None:
            continue
        if not isinstance(codes, (list, tuple)) or len(codes) != 27:
            raise ValueError(f"{day}: cần đúng 27 mã")
        values = [code2(x) for x in codes]
        if day in out and out[day] != values:
            raise ValueError(f"{day}: trùng ngày nhưng khác dữ liệu")
        out[day] = values
    history = sorted(out.items())
    if len(history) < 60:
        raise ValueError(f"Lịch sử quá ngắn: {len(history)}")
    return history


def load_history(path: Path = HISTORY) -> list[tuple[date, list[str]]]:
    packed = "".join(path.read_text(encoding="utf-8").split())
    text = bz2.decompress(base64.b64decode(packed)).decode("utf-8-sig")
    if FORBIDDEN.search(text):
        raise ValueError("Nguồn public chứa trường canonical/final")
    try:
        return parse_rows(row_container(json.loads(text)))
    except json.JSONDecodeError:
        for sep in (",", "\t", ";", "|"):
            rows = [r for r in csv.reader(io.StringIO(text), delimiter=sep) if len(r) >= 28]
            if rows:
                return parse_rows(rows)
    raise ValueError("Không đọc được history-27.bz2.b64")


def gap(flags: list[bool]) -> tuple[int, int]:
    cur = 0
    for x in reversed(flags):
        if x: break
        cur += 1
    best = run = 0
    for x in flags:
        run = 0 if x else run + 1
        best = max(best, run)
    return cur, best


def stats(history: list[tuple[date, list[str]]]) -> dict[str, Any]:
    counters = [Counter(codes) for _, codes in history]
    numbers = []
    for n in range(100):
        c = f"{n:02d}"
        flags = [x.get(c, 0) > 0 for x in counters]
        cur, mx = gap(flags)
        idx = next((i for i in range(len(flags)-1, -1, -1) if flags[i]), None)
        windows = {}
        for w in WINDOWS:
            part = counters[-min(w, len(counters)):]
            seen = sum(x.get(c, 0) > 0 for x in part)
            hits = sum(x.get(c, 0) for x in part)
            windows[str(w)] = {"window": len(part), "days_seen": int(seen), "hits": int(hits), "rate": round(seen*100/len(part),1)}
        numbers.append({"code": c, "current_gap": cur, "max_gap": mx, "last_seen": history[idx][0].isoformat() if idx is not None else None, "windows": windows})
    pairs = []
    for a in range(10):
        for b in range(a+1, 10):
            left, right = f"{a}{b}", f"{b}{a}"
            flags = [(x.get(left,0)+x.get(right,0)) > 0 for x in counters]
            cur, mx = gap(flags)
            idx = next((i for i in range(len(flags)-1, -1, -1) if flags[i]), None)
            windows = {}
            for w in WINDOWS:
                part = counters[-min(w, len(counters)):]
                seen = sum((x.get(left,0)+x.get(right,0)) > 0 for x in part)
                hits = sum(x.get(left,0)+x.get(right,0) for x in part)
                both = sum(x.get(left,0)>0 and x.get(right,0)>0 for x in part)
                windows[str(w)] = {"window":len(part),"days_seen":int(seen),"hits":int(hits),"both":int(both),"rate":round(seen*100/len(part),1)}
            pairs.append({"pair":f"{left}-{right}","left":left,"right":right,"current_gap":cur,"max_gap":mx,"last_seen":history[idx][0].isoformat() if idx is not None else None,"windows":windows})
    normalized = json.dumps([[d.isoformat(), *codes] for d,codes in history], ensure_ascii=False, separators=(",",":"))
    return {"schema":"MB_PUBLIC_XSMB_STATS_V1","generated_at":datetime.now(VN).isoformat(timespec="seconds"),"first_date":history[0][0].isoformat(),"updated_through":history[-1][0].isoformat(),"row_count":len(history),"source_sha256":hashlib.sha256(normalized.encode()).hexdigest(),"windows":list(WINDOWS),"numbers":numbers,"pairs":pairs,"recent_history":[[d.isoformat(),*codes] for d,codes in history[-365:]]}


def affiliate_config(path: Path = AFFILIATE) -> dict[str, Any]:
    if not path.exists(): return {"enabled":False,"offers":[]}
    p = json.loads(path.read_text(encoding="utf-8"))
    for o in p.get("offers") or []:
        url = str(o.get("url") or "")
        if url and not url.startswith("https://"):
            raise ValueError("Affiliate URL phải là https")
    return p


def affiliate_box(cfg: dict[str, Any], zone: str) -> str:
    if not cfg.get("enabled"): return ""
    cards = []
    for o in cfg.get("offers") or []:
        url, zones = str(o.get("url") or ""), o.get("zones") or []
        if o.get("enabled") and url.startswith("https://") and (not zones or zone in zones):
            cards.append(f'<a class="ad" href="{esc(url)}" target="_blank" rel="sponsored nofollow noopener noreferrer" data-affiliate="{esc(o.get("id","shopee"))}"><b>Shopee · {esc(o.get("title","Ưu đãi"))}</b><span>{esc(o.get("description","Xem ưu đãi trên Shopee"))}</span><strong>{esc(o.get("cta","Xem ngay"))} →</strong></a>')
    if not cards: return ""
    disclosure = esc(cfg.get("disclosure") or "Liên kết tiếp thị: website có thể nhận hoa hồng; giá mua không tăng vì việc đó.")
    return f'<aside class="ads"><small>{disclosure}</small><div>{"".join(cards[:3])}</div></aside>'


def dmy(s: str | None) -> str:
    return date.fromisoformat(s).strftime("%d/%m/%Y") if s else "Chưa có"


CSS = r'''*{box-sizing:border-box}body{margin:0;background:#f5f7fa;color:#102234;font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit}.top{position:sticky;top:0;z-index:5;background:#071f33;color:#fff;border-bottom:3px solid #e53838}.topin{max-width:1180px;margin:auto;padding:10px 16px;display:flex;gap:18px;align-items:center;justify-content:space-between}.brand{text-decoration:none;font-weight:900}.brand small{display:block;font-weight:500;color:#cbd5e1}.buy{background:#e53838;color:#fff;text-decoration:none;padding:9px 13px;border-radius:10px;font-weight:800}.nav{display:flex;gap:7px;overflow:auto;max-width:1180px;margin:auto;padding:0 16px 8px}.nav a{white-space:nowrap;text-decoration:none;padding:5px 8px;border-radius:8px;background:#12324a}.main{max-width:1180px;margin:auto;padding:16px}.source{background:#e9f3fb;border:1px solid #c8ddea;padding:10px 12px;border-radius:12px;margin-bottom:14px}.source span{display:block;color:#536779;font-size:13px}.hero,.panel,.note{background:#fff;border:1px solid #d9e0e7;border-radius:16px;padding:18px;margin:0 0 14px;box-shadow:0 2px 8px #00000008}.hero h1{font-size:clamp(24px,4vw,38px);line-height:1.15;margin:4px 0 10px}.eyebrow{font-size:12px;letter-spacing:.08em;font-weight:900;color:#c62828}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.actions a,.tabs button{border:1px solid #d2dae2;background:#fff;border-radius:9px;padding:8px 10px;text-decoration:none;font-weight:700}.actions a:hover,.tabs button.active{background:#071f33;color:#fff}.grid{display:grid;grid-template-columns:repeat(10,1fr);gap:6px}.num{border:1px solid #dce3ea;background:#fff;border-radius:9px;padding:9px 3px;cursor:pointer}.num b{display:block;font-size:17px}.num small{display:block;color:#6b7c8a;font-size:10px}.head{display:flex;gap:12px;align-items:end;justify-content:space-between;flex-wrap:wrap}.tabs{display:flex;gap:5px;flex-wrap:wrap}.tabs button{cursor:pointer;padding:6px 8px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;min-width:620px}th,td{padding:9px 8px;border-bottom:1px solid #e5eaf0;text-align:right}th:first-child,td:first-child{text-align:left}th{font-size:12px;color:#516575;background:#f7f9fb;position:sticky;top:0}.pill{display:inline-block;padding:4px 7px;border-radius:999px;background:#eef3f7;font-weight:800}.profile{background:#071f33;color:#fff;border-radius:14px;padding:16px;margin-top:12px}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.kpi{background:#12324a;padding:10px;border-radius:10px}.kpi small,.profile small{color:#bed0df;display:block}.kpi b{font-size:21px}.lookup{display:flex;gap:8px;flex-wrap:wrap}.lookup input,.lookup select{padding:10px;border:1px solid #cdd7e0;border-radius:9px;font:inherit}.lookup input{flex:1;min-width:220px}.lookup button{background:#e53838;border:0;color:#fff;border-radius:9px;padding:10px 14px;font-weight:800}.ads{background:#fff7e7;border:1px solid #ffd99a;border-radius:14px;padding:12px;margin:0 0 14px}.ads>div{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px}.ad{background:#fff;border:1px solid #ffd5a0;border-radius:10px;padding:10px;text-decoration:none}.ad span{display:block;color:#6f604b;margin:5px 0}.note{font-size:14px;color:#526575}.footer{background:#071f33;color:#dbe5ec;padding:24px 16px;text-align:center;margin-top:20px}@media(max-width:760px){.grid{grid-template-columns:repeat(5,1fr)}.kpis{grid-template-columns:repeat(2,1fr)}.ads>div{grid-template-columns:1fr}.main{padding:12px}.hero,.panel,.note{padding:14px}.topin{padding:8px 12px}}'''

JS = r'''(()=>{let D;const load=()=>D?Promise.resolve(D):fetch('/statistics-data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}).then(x=>D=x);const emit=(e,p={})=>{window.dataLayer=window.dataLayer||[];window.dataLayer.push({event:e,page_path:location.pathname,...p})};const fmt=s=>s?s.split('-').reverse().join('/'):'Chưa có';const active=()=>document.querySelector('.tabs button.active')?.dataset.w||'60';function profile(code){const r=D.numbers.find(x=>x.code===code),w=active(),s=r.windows[w],box=document.querySelector('#profile');if(!box)return;box.innerHTML=`<h3>Hồ sơ số ${code}</h3><div class="kpis"><div class="kpi"><small>Ngày có mặt /${w}</small><b>${s.days_seen}</b></div><div class="kpi"><small>Tổng nháy /${w}</small><b>${s.hits}</b></div><div class="kpi"><small>Gan hiện tại</small><b>${r.current_gap} kỳ</b></div><div class="kpi"><small>Lần gần nhất</small><b>${fmt(r.last_seen)}</b></div></div>`;emit('xsmb_number_open',{number:code,window:w})}document.addEventListener('click',async e=>{const t=e.target.closest('.tabs button');if(t){document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('active',x===t));emit('xsmb_stats_window',{window:t.dataset.w});return}const n=e.target.closest('[data-number]');if(n){await load();profile(n.dataset.number)}const a=e.target.closest('[data-affiliate]');if(a)emit('affiliate_click',{affiliate_offer_id:a.dataset.affiliate})});document.addEventListener('submit',async e=>{if(!e.target.matches('#lookup'))return;e.preventDefault();await load();const f=new FormData(e.target),codes=[...new Set((String(f.get('numbers')||'').match(/\d{1,2}/g)||[]).map(x=>String(Number(x)).padStart(2,'0')).filter(x=>+x>=0&&+x<=99))].slice(0,20),days=+f.get('days'),rows=D.recent_history.slice(-days).reverse().map(r=>{const [d,...v]=r,c=new Map();v.forEach(x=>c.set(x,(c.get(x)||0)+1));const h=codes.filter(x=>c.has(x));return h.length?[d,h.map(x=>x+(c.get(x)>1?' ×'+c.get(x):''))]:null}).filter(Boolean),out=document.querySelector('#lookupOut');out.innerHTML=codes.length?`<p>Bộ <b>${codes.join(', ')}</b> xuất hiện ít nhất một số trong <b>${rows.length}/${Math.min(days,D.recent_history.length)}</b> kỳ đã dò.</p>${rows.length?`<div class="scroll"><table><thead><tr><th>Ngày</th><th>Số xuất hiện</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${fmt(r[0])}</td><td>${r[1].join(' · ')}</td></tr>`).join('')}</tbody></table></div>`:''}`:'<p>Hãy nhập ít nhất một số 00–99.</p>';emit('xsmb_lookup',{numbers:codes.join('-'),days,matched_days:rows.length})});})();'''


def tabs(default=60) -> str:
    return '<div class="tabs">'+''.join(f'<button type="button" data-w="{w}" class="{"active" if w==default else ""}">{w} kỳ</button>' for w in WINDOWS)+'</div>'


def shell(title: str, desc: str, path: str, data: dict[str, Any], body: str, cfg: dict[str, Any], zone: str) -> str:
    url=BASE+path
    schema=json.dumps({"@context":"https://schema.org","@graph":[{"@type":"WebPage","url":url,"name":title,"description":desc,"inLanguage":"vi-VN"},{"@type":"Dataset","name":"Lịch sử 27 mã XSMB dùng cho thống kê công khai","temporalCoverage":f"{data['first_date']}/{data['updated_through']}","dateModified":data['updated_through']}]},ensure_ascii=False,separators=(",",":"))
    return f'''<!doctype html><html lang="vi" data-xsmb-stats="v1"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{esc(url)}"><link rel="icon" href="/favicon.svg"><style>{CSS}</style><script async src="https://www.googletagmanager.com/gtag/js?id=G-R9TBYP97BC"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-R9TBYP97BC',{{allow_google_signals:false,allow_ad_personalization_signals:false}});</script><script type="application/ld+json">{schema}</script></head><body><header class="top"><div class="topin"><a class="brand" href="/">LÊ MIỀN BẮC<small>Thống kê dữ liệu XSMB</small></a><a class="buy" href="/?checkout=1">Báo cáo 4SO hôm nay</a></div><nav class="nav"><a href="/">Trang chủ</a><a href="/cho-so-mien-bac-hom-nay/">Số hôm nay</a><a href="/thong-ke-xsmb/">Thống kê XSMB</a><a href="/tan-suat-xsmb/">Tần suất</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/cap-dao-xsmb/">Cặp đảo</a><a href="/tra-cuu-xsmb/">Tra cứu</a></nav></header><main class="main"><div class="source"><b>Dữ liệu đến {dmy(data['updated_through'])}</b><span>27/27 mã mỗi ngày · {data['row_count']} kỳ · SHA-256 {data['source_sha256'][:12]}…</span></div>{body}{affiliate_box(cfg,zone)}<section class="note"><b>Cách đọc:</b> đây là thống kê mô tả dữ liệu đã công bố. Khoảng vắng không có nghĩa một số “đến hạn” phải xuất hiện. Các trang này không công bố Top 2 canonical, Score hay thứ hạng 4SO.</section></main><footer class="footer">Lê Miền Bắc · Thống kê dữ liệu XSMB · <a href="/legal.html">Điều khoản &amp; bảo mật</a></footer><script>{JS}</script></body></html>'''


def hub(data: dict[str, Any]) -> str:
    grid=''.join(f'<button class="num" data-number="{r["code"]}"><b>{r["code"]}</b><small>{r["windows"]["60"]["days_seen"]}/60 · gan {r["current_gap"]}</small></button>' for r in data['numbers'])
    hot=sorted(data['numbers'],key=lambda r:(-r['windows']['60']['days_seen'],-r['windows']['60']['hits'],r['code']))[:10]
    cold=sorted(data['numbers'],key=lambda r:(-r['current_gap'],-r['max_gap'],r['code']))[:10]
    tr1=''.join(f'<tr><td><b>{r["code"]}</b></td><td>{r["windows"]["60"]["days_seen"]}/60</td><td>{r["windows"]["60"]["hits"]}</td><td>{r["current_gap"]}</td></tr>' for r in hot)
    tr2=''.join(f'<tr><td><b>{r["code"]}</b></td><td>{r["current_gap"]}</td><td>{dmy(r["last_seen"])}</td><td>{r["max_gap"]}</td></tr>' for r in cold)
    return f'''<section class="hero"><p class="eyebrow">TRUNG TÂM THỐNG KÊ XSMB</p><h1>Tra cứu tần suất, lô gan và cặp đảo 00–99</h1><p>Toàn bộ bảng tính trực tiếp từ cùng nguồn lịch sử 27 mã/ngày. Chọn số để mở hồ sơ thống kê.</p><div class="actions"><a href="/tan-suat-xsmb/">Tần suất 00–99</a><a href="/lo-gan-xsmb/">Lô gan</a><a href="/cap-dao-xsmb/">45 cặp đảo</a><a href="/tra-cuu-xsmb/">Dò bộ số</a></div></section><section class="panel"><div class="head"><div><p class="eyebrow">MA TRẬN 00–99</p><h2>Hồ sơ từng số</h2></div>{tabs()}</div><div class="grid">{grid}</div><div id="profile" class="profile"><small>Bấm một số 00–99 để xem chi tiết.</small></div></section><section class="panel"><h2>Nhìn nhanh 60 kỳ</h2><div class="scroll"><table><thead><tr><th>Xuất hiện nhiều</th><th>Ngày có mặt</th><th>Nháy</th><th>Gan</th></tr></thead><tbody>{tr1}</tbody></table></div><br><div class="scroll"><table><thead><tr><th>Khoảng vắng dài</th><th>Gan hiện tại</th><th>Lần gần nhất</th><th>Gan max</th></tr></thead><tbody>{tr2}</tbody></table></div></section>'''


def frequency(data: dict[str, Any]) -> str:
    rows=sorted(data['numbers'],key=lambda r:(-r['windows']['60']['days_seen'],-r['windows']['60']['hits'],r['code']))
    tr=''.join(f'<tr><td><b>{r["code"]}</b></td><td>{r["windows"]["7"]["days_seen"]}</td><td>{r["windows"]["30"]["days_seen"]}</td><td>{r["windows"]["60"]["days_seen"]}</td><td>{r["windows"]["100"]["days_seen"]}</td><td>{r["windows"]["365"]["days_seen"]}</td><td>{r["windows"]["60"]["hits"]}</td><td>{r["current_gap"]}</td></tr>' for r in rows)
    return f'<section class="hero"><p class="eyebrow">TẦN SUẤT XSMB</p><h1>Tần suất 00–99 theo 7–365 kỳ</h1><p>“Ngày có mặt” tính một lần cho mỗi ngày có ít nhất một nháy; “nháy” là tổng số lần xuất hiện.</p></section><section class="panel"><div class="scroll"><table><thead><tr><th>Số</th><th>7</th><th>30</th><th>60</th><th>100</th><th>365</th><th>Nháy/60</th><th>Gan</th></tr></thead><tbody>{tr}</tbody></table></div></section>'


def gan(data: dict[str, Any]) -> str:
    rows=sorted(data['numbers'],key=lambda r:(-r['current_gap'],-r['max_gap'],r['code']))
    tr=''.join(f'<tr><td><b>{r["code"]}</b></td><td>{r["current_gap"]}</td><td>{dmy(r["last_seen"])}</td><td>{r["max_gap"]}</td><td>{r["windows"]["60"]["days_seen"]}/60</td><td>{r["windows"]["60"]["hits"]}</td></tr>' for r in rows)
    return f'<section class="hero"><p class="eyebrow">LÔ GAN XSMB</p><h1>Khoảng vắng hiện tại của 00–99</h1><p>Sắp xếp theo số kỳ liên tiếp chưa xuất hiện. Gan là dữ liệu mô tả, không phải tín hiệu bắt buộc phải về.</p></section><section class="panel"><div class="scroll"><table><thead><tr><th>Số</th><th>Gan hiện tại</th><th>Lần gần nhất</th><th>Gan max</th><th>Ngày/60</th><th>Nháy/60</th></tr></thead><tbody>{tr}</tbody></table></div></section>'


def pairs(data: dict[str, Any]) -> str:
    rows=sorted(data['pairs'],key=lambda r:(-r['windows']['60']['days_seen'],-r['windows']['60']['hits'],r['pair']))
    tr=''.join(f'<tr><td><b>{r["pair"]}</b></td><td>{r["windows"]["60"]["days_seen"]}/60</td><td>{r["windows"]["60"]["hits"]}</td><td>{r["windows"]["60"]["both"]}</td><td>{r["current_gap"]}</td><td>{r["max_gap"]}</td><td>{dmy(r["last_seen"])}</td></tr>' for r in rows)
    return f'<section class="hero"><p class="eyebrow">45 CẶP ĐẢO</p><h1>Thống kê toàn bộ 45 cặp đảo XSMB</h1><p>Mỗi cặp chỉ giữ một chiều duy nhất và loại số kép. Đây là bảng mô tả công khai, không phải thứ hạng 4SO.</p></section><section class="panel"><div class="scroll"><table><thead><tr><th>Cặp</th><th>Ngày/60</th><th>Nháy/60</th><th>Cả hai/60</th><th>Gan</th><th>Gan max</th><th>Lần gần nhất</th></tr></thead><tbody>{tr}</tbody></table></div></section>'


def lookup() -> str:
    return '''<section class="hero"><p class="eyebrow">TRA CỨU BỘ SỐ</p><h1>Dò một bộ số trong lịch sử XSMB</h1><p>Nhập ví dụ <b>05, 50, 38, 83</b>; hệ thống liệt kê những kỳ có ít nhất một số xuất hiện và số nháy tương ứng.</p></section><section class="panel"><form id="lookup" class="lookup"><input name="numbers" placeholder="05, 50, 38, 83" inputmode="numeric" required><select name="days"><option value="30">30 kỳ</option><option value="60" selected>60 kỳ</option><option value="100">100 kỳ</option><option value="365">365 kỳ</option></select><button>Dò lịch sử</button></form><div id="lookupOut"></div></section>'''


def patch_nav(root: Path) -> None:
    old='<a href="/thong-ke-lo-to-mien-bac-bang-ai/">Thống kê AI</a>'
    new='<a href="/thong-ke-xsmb/">Thống kê XSMB</a>'
    for page in root.rglob('*.html'):
        text=page.read_text(encoding='utf-8')
        if old in text: page.write_text(text.replace(old,new),encoding='utf-8')


def patch_sitemap(root: Path, paths: list[str], modified: str) -> None:
    p=root/'sitemap.xml'
    if not p.exists(): return
    text=p.read_text(encoding='utf-8')
    add=''.join(f'  <url><loc>{BASE+x}</loc><lastmod>{modified}</lastmod></url>\n' for x in paths if BASE+x not in text)
    if add: p.write_text(text.replace('</urlset>',add+'</urlset>'),encoding='utf-8')


def build(root: Path, history_path: Path=HISTORY, affiliate_path: Path=AFFILIATE) -> dict[str, Any]:
    data=stats(load_history(history_path)); cfg=affiliate_config(affiliate_path); root.mkdir(parents=True,exist_ok=True)
    (root/'statistics-data.json').write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding='utf-8')
    pages=[('/thong-ke-xsmb/','Thống kê XSMB 00–99: tần suất, lô gan, cặp đảo | Lê Miền Bắc','Tra cứu thống kê XSMB 00–99: tần suất nhiều cửa sổ, lô gan, 45 cặp đảo và hồ sơ từng số.',hub(data),'stats-hub'),('/tan-suat-xsmb/','Tần suất XSMB 00–99 theo 7–365 kỳ | Lê Miền Bắc','Bảng tần suất XSMB 00–99 theo nhiều cửa sổ từ lịch sử 27 mã mỗi ngày.',frequency(data),'frequency'),('/lo-gan-xsmb/','Lô gan XSMB: gan hiện tại và gan cực đại | Lê Miền Bắc','Thống kê khoảng vắng 00–99, ngày xuất hiện gần nhất và tần suất 60 kỳ.',gan(data),'gap'),('/cap-dao-xsmb/','Thống kê 45 cặp đảo XSMB | Lê Miền Bắc','Bảng đầy đủ 45 cặp đảo: ngày có mặt, tổng nháy, cả hai cùng xuất hiện và khoảng vắng.',pairs(data),'pairs'),('/tra-cuu-xsmb/','Tra cứu bộ số XSMB theo lịch sử 30–365 kỳ | Lê Miền Bắc','Nhập một hoặc nhiều số 00–99 để dò lịch sử 30, 60, 100 hoặc 365 kỳ.',lookup(),'lookup')]
    for path,title,desc,body,zone in pages:
        target=root/path.strip('/')/'index.html'; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(shell(title,desc,path,data,body,cfg,zone),encoding='utf-8')
    patch_nav(root); patch_sitemap(root,[p[0] for p in pages],data['updated_through'])
    return {'pages':len(pages),'rows':data['row_count'],'updated_through':data['updated_through'],'affiliate_enabled':bool(cfg.get('enabled'))}


def self_test() -> None:
    start=date(2025,1,1); h=[]
    for o in range(420): h.append((start+timedelta(days=o),[f"{(o*7+i*13+i//9)%100:02d}" for i in range(27)]))
    d=stats(h); assert len(d['numbers'])==100 and len(d['pairs'])==45 and len(d['recent_history'])==365
    raw=json.dumps([[x.isoformat(),*c] for x,c in h],separators=(",",":")).encode()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); hp=td/'h.b64'; hp.write_text(base64.b64encode(bz2.compress(raw)).decode()); af=td/'a.json'; af.write_text('{"enabled":false,"offers":[]}'); out=td/'site'; out.mkdir(); (out/'sitemap.xml').write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>')
        r=build(out,hp,af); assert r['pages']==5; assert (out/'thong-ke-xsmb/index.html').exists(); assert 'canonical_codes' not in (out/'statistics-data.json').read_text(); assert BASE+'/thong-ke-xsmb/' in (out/'sitemap.xml').read_text()
    print('PUBLIC_XSMB_STATISTICS_SELF_TEST_OK')


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--output-root',type=Path,default=ROOT/'_site'); p.add_argument('--history-pack',type=Path,default=HISTORY); p.add_argument('--affiliate-config',type=Path,default=AFFILIATE); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    if a.self_test: self_test()
    else: print(json.dumps(build(a.output_root,a.history_pack,a.affiliate_config),ensure_ascii=False))

if __name__=='__main__': main()
