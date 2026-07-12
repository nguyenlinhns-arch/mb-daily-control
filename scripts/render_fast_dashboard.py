#!/usr/bin/env python3
"""Render a zero-dependency A1/X2/X3/ROLL7/Xiên 2 dashboard."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data" / "current.json"
INDEX = ROOT / "index.html"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w/edit"


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def date_vi(value: Any) -> str:
    raw = str(value or "")[:10]
    parts = raw.split("-")
    return f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else "—"


def vnd(value: Any, *, signed: bool = False) -> str:
    try:
        number = int(float(value or 0))
    except (TypeError, ValueError):
        number = 0
    prefix = "+" if signed and number > 0 else "−" if signed and number < 0 else ""
    return f"{prefix}{abs(number):,}đ".replace(",", ".")


def method_key(method: dict[str, Any]) -> str:
    text = f"{method.get('id', '')} {method.get('label', '')}".upper()
    if "XIEN" in text or "XIÊN" in text:
        return "xien2"
    if "ROLL7" in text or "5-OF-7" in text:
        return "roll7"
    if "A1" in text:
        return "a1"
    if "X2" in text:
        return "x2"
    if "X3" in text:
        return "x3"
    return "other"


def visual_tone(value: Any) -> str:
    text = str(value or "").upper()
    if "PASS" in text or "KHUYẾN NGHỊ" in text or ("ĐẠT" in text and "KHÔNG" not in text and "GẦN" not in text):
        return "pass"
    if "NEAR" in text or "GẦN" in text:
        return "near"
    if any(token in text for token in ("EMPTY", "TRỐNG", "NOT_APPLICABLE", "KHÔNG KÍCH HOẠT", "LT2")):
        return "idle"
    return "fail"


def group_by_id(doc: dict[str, Any], *wanted: str) -> dict[str, Any]:
    targets = {item.upper() for item in wanted}
    for group in doc.get("groups") or []:
        if str(group.get("id") or "").upper() in targets:
            return group
    return {}


def synthesize_method(doc: dict[str, Any], key: str) -> dict[str, Any]:
    if key == "roll7":
        group = group_by_id(doc, "ROLL7")
        state = doc.get("roll7_status") or group
        numbers = state.get("selected_numbers") or []
        points = state.get("points_by_code") or {}
        return {
            "id": "ROLL7_STATUS",
            "label": "MB ROLL7 · 5-of-7",
            "method": "Rescue30 khi A1/X2/X3 đều A0",
            "status": state.get("status") or state.get("summary") or "CHƯA KÍCH HOẠT",
            "visual_status": "PASS" if numbers else "EMPTY",
            "points_per_code": 30,
            "code_count": len(numbers),
            "capital_vnd": state.get("capital_vnd") or 0,
            "reason": state.get("reason") or "Chỉ xét khi cả A1, X2 và X3 đều A0.",
            "numbers": [
                {"code": code, "points": points.get(code, 30), "capital_vnd": int(points.get(code, 30)) * 23000, "role": "ROLL7 Rescue30", "visual_status": "PASS"}
                for code in numbers
            ],
        }
    if key == "xien2":
        rec = doc.get("xien2_recommendation") or group_by_id(doc, "XIEN", "XIEN2")
        pairs = rec.get("pairs") or rec.get("selected_numbers") or []
        capital_per_pair = int(rec.get("capital_per_pair_vnd") or 100000)
        return {
            "id": "XIEN2_AUTO_PAIRS",
            "label": "Xiên 2 tự động",
            "method": "Ghép toàn bộ cặp từ số được cấp vốn",
            "status": rec.get("status") or rec.get("summary") or "KHÔNG KÍCH HOẠT",
            "visual_status": "PASS" if pairs else "EMPTY",
            "points_per_pair": rec.get("points_per_pair") or 100,
            "capital_per_pair_vnd": capital_per_pair,
            "code_count": len(pairs),
            "pair_count": len(pairs),
            "capital_vnd": rec.get("capital_vnd") or len(pairs) * capital_per_pair,
            "reason": rec.get("reason") or "Cần tối thiểu 02 số được cấp vốn.",
            "numbers": [
                {"code": pair, "points": 0, "caption": f"{vnd(capital_per_pair)}/cặp", "capital_vnd": capital_per_pair, "role": "Xiên 2 tự động · chờ xác nhận", "visual_status": "PASS"}
                for pair in pairs
            ],
        }

    group = group_by_id(doc, key.upper())
    labels = {"a1": "MB A1", "x2": "MB X2", "x3": "MB X3"}
    selected = group.get("selected_numbers") or []
    points_total = int(group.get("points") or 0)
    pp = points_total // len(selected) if selected and points_total else 0
    return {
        "id": key.upper(),
        "label": labels[key],
        "method": group.get("method") or labels[key],
        "status": group.get("status") or "KHÔNG CÓ DỮ LIỆU",
        "visual_status": "PASS" if "PASS" in str(group.get("status") or "").upper() else "FAIL",
        "points_per_code": pp,
        "code_count": len(selected),
        "capital_vnd": group.get("capital_vnd") or 0,
        "reason": group.get("reason") or group.get("summary") or "",
        "numbers": [{"code": code, "points": pp, "capital_vnd": pp * 23000, "role": group.get("summary") or ""} for code in selected],
    }


def current_methods(doc: dict[str, Any]) -> list[dict[str, Any]]:
    source = list((doc.get("top_signals") or {}).get("methods") or [])
    found = {method_key(item): item for item in source}
    return [found.get(key) or synthesize_method(doc, key) for key in ("a1", "x2", "x3", "roll7", "xien2")]


def number_tile(number: dict[str, Any], method: dict[str, Any]) -> str:
    tone = visual_tone(number.get("visual_status") or number.get("status") or method.get("visual_status") or method.get("status"))
    points = int(number.get("points") or 0)
    caption = number.get("caption") or (f"{points} điểm" if points else "0 điểm · theo dõi")
    role = number.get("role") or ""
    return (
        f'<div class="number {tone}" title="{esc(role)}">'
        f'<strong>{esc(number.get("code") or "—")}</strong>'
        f'<span>{esc(caption)}</span>'
        f'<small>{vnd(number.get("capital_vnd") or 0)}</small>'
        "</div>"
    )


def a1_watch(doc: dict[str, Any]) -> str:
    group = group_by_id(doc, "A1")
    candidates = [item for item in (group.get("candidates") or []) if str(item.get("component") or "").upper() != "A1_REVERSE50"][:3]
    if not candidates:
        return ""
    rows = []
    for item in candidates:
        metrics = f"Gan {item.get('gan', '—')} · Gmax {item.get('gmax', '—')} · Score {item.get('score', '—')}"
        rows.append(f'<div class="watch-row"><b>{esc(item.get("code") or "—")}</b><span>{esc(metrics)}</span><small>Mốc {date_vi(item.get("earliest_eligible_date"))}</small></div>')
    return '<div class="watch"><h4>Top 3 A1 theo dõi</h4>' + "".join(rows) + "</div>"


def method_card(method: dict[str, Any], doc: dict[str, Any]) -> str:
    key = method_key(method)
    tone = visual_tone(method.get("visual_status") or method.get("status"))
    symbols = {"a1": "A1", "x2": "X2", "x3": "X3", "roll7": "R7", "xien2": "X2+", "other": "MB"}
    numbers = method.get("numbers") or []
    tiles = "".join(number_tile(item, method) for item in numbers) or '<div class="empty">Không có mã/cặp được khuyến nghị</div>'
    reason = method.get("reason") or method.get("note") or ""
    watch = a1_watch(doc) if key == "a1" else ""
    if key == "xien2":
        first_label = "Vốn/cặp"
        first_value = vnd(method.get("capital_per_pair_vnd") or 100000)
        second_label = "Số cặp"
        second_value = method.get("pair_count") or method.get("code_count") or 0
    else:
        first_label = "Điểm/số"
        first_value = method.get("points_per_code") or 0
        second_label = "Số mã"
        second_value = method.get("code_count") or 0
    return f"""
    <article class="method-card {tone}">
      <header><span class="symbol">{symbols[key]}</span><div><h3>{esc(method.get('label') or method.get('method') or key.upper())}</h3><p>{esc(method.get('method') or '')}</p></div></header>
      <div class="status {tone}">{esc(method.get('status') or '—')}</div>
      <div class="numbers">{tiles}</div>
      {watch}
      <p class="reason">{esc(reason)}</p>
      <footer><span>{esc(first_label)} <b>{esc(first_value)}</b></span><span>{esc(second_label)} <b>{esc(second_value)}</b></span><span>Tổng vốn <b>{vnd(method.get('capital_vnd') or 0)}</b></span></footer>
    </article>"""


def render(doc: dict[str, Any]) -> str:
    target = doc.get("target_date")
    locked = (doc.get("data") or {}).get("locked_through")
    portfolio = doc.get("portfolio") or {}
    pnl = doc.get("pnl_summary") or {}
    pending = doc.get("pending_order") or {}
    xien = doc.get("xien2_recommendation") or {}
    methods = current_methods(doc)
    cards = "".join(method_card(item, doc) for item in methods)
    standard_capital = int(portfolio.get("standard_capital_vnd") or portfolio.get("capital_vnd") or pnl.get("today_pending_capital_vnd") or 0)
    xien_capital = int(xien.get("capital_vnd") or portfolio.get("xien2_recommended_capital_vnd") or 0)
    total_capital = int(portfolio.get("total_recommended_capital_vnd") or standard_capital + xien_capital)
    cumulative = pnl.get("grand_total_pnl_vnd") or 0
    execution = pending.get("status") or portfolio.get("pnl_status") or "—"
    generated = str(doc.get("generated_at") or "").replace("T", " ")[:19]
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#0d2239"><meta name="description" content="MB Daily Control — kế hoạch XSMB kỳ sắp tới"><title>MB Daily Control · {esc(date_vi(target))}</title>
<style>
:root{{--bg:#071421;--panel:#0d2239;--panel2:#122c48;--text:#edf6ff;--muted:#9db0c3;--line:#29425a;--green:#21c482;--red:#ff6470;--amber:#f4c95d}}*{{box-sizing:border-box}}html{{background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}}body{{margin:0}}.wrap{{width:min(1180px,calc(100% - 24px));margin:auto;padding:18px 0 36px}}.bar{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}}.brand{{display:flex;align-items:center;gap:10px}}.logo{{display:grid;place-items:center;width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#1c7cff,#25c58a);font-weight:900}}button,.link{{border:1px solid var(--line);background:#102841;color:var(--text);padding:10px 14px;border-radius:10px;text-decoration:none;font-weight:700;cursor:pointer}}.hero{{background:linear-gradient(135deg,#102a45,#0d2137);border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px}}.eyebrow{{color:#74b5ff;font-weight:800;font-size:12px;letter-spacing:.08em}}h1{{font-size:clamp(26px,4vw,46px);margin:7px 0}}.hero p{{color:var(--muted);margin:6px 0}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}}.stat{{background:#0a1c2e;border:1px solid var(--line);border-radius:12px;padding:12px}}.stat span{{display:block;color:var(--muted);font-size:12px}}.stat b{{display:block;margin-top:5px;font-size:18px}}.methods{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}.method-card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px}}.method-card.pass{{border-color:#1e9d70}}.method-card.fail{{border-color:#9b4050}}.method-card.near{{border-color:#9b812d}}.method-card.idle{{border-color:#5f7080}}.method-card header{{display:flex;gap:11px;align-items:center}}.symbol{{display:grid;place-items:center;min-width:42px;height:42px;border-radius:11px;background:var(--panel2);font-weight:900}}h3{{margin:0;font-size:19px}}.method-card header p{{margin:3px 0 0;color:var(--muted);font-size:12px}}.status{{display:inline-block;margin:12px 0;padding:6px 9px;border-radius:999px;font-size:12px;font-weight:900}}.status.pass{{background:#123e32;color:#69e6b0}}.status.fail{{background:#45202a;color:#ff9ca5}}.status.near{{background:#463b17;color:#ffe083}}.status.idle{{background:#253544;color:#c1cfda}}.numbers{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}}.number,.empty{{min-height:112px;border:1px solid var(--line);border-radius:12px;background:#0a1b2c;padding:10px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}}.number strong{{font-size:34px;line-height:1}}.number span{{font-size:12px;margin-top:8px}}.number small{{color:var(--muted);margin-top:4px}}.number.pass{{border-color:#1f9f71}}.number.fail{{border-color:#713440}}.number.idle{{border-color:#465a6c}}.empty{{grid-column:1/-1;color:var(--muted)}}.reason{{color:var(--muted);font-size:13px;min-height:36px}}.method-card footer{{display:flex;justify-content:space-between;gap:8px;border-top:1px solid var(--line);padding-top:12px;font-size:12px;color:var(--muted)}}.method-card footer b{{display:block;color:var(--text);font-size:14px}}.watch{{border-top:1px dashed var(--line);margin-top:12px;padding-top:10px}}.watch h4{{margin:0 0 7px;font-size:13px}}.watch-row{{display:grid;grid-template-columns:34px 1fr auto;gap:8px;padding:5px 0;font-size:11px;color:var(--muted)}}.watch-row b{{color:var(--text);font-size:14px}}.summary{{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-top:14px;padding:14px;border:1px solid var(--line);border-radius:14px;background:#0b1d30}}.summary small{{color:var(--muted)}}.actions{{display:flex;gap:8px;flex-wrap:wrap}}.foot{{text-align:center;color:var(--muted);font-size:12px;margin-top:18px}}@media(max-width:760px){{.stats{{grid-template-columns:repeat(2,1fr)}}.methods{{grid-template-columns:1fr}}.numbers{{grid-template-columns:repeat(2,1fr)}}.summary{{align-items:flex-start;flex-direction:column}}.watch-row{{grid-template-columns:30px 1fr}}.watch-row small{{grid-column:2}}}}
</style></head>
<body data-static-dashboard="1"><div class="wrap"><div class="bar"><div class="brand"><div class="logo">MB</div><div><b>MB Daily Control</b><div style="color:var(--muted);font-size:12px">XSMB Daily Validation</div></div></div><button type="button" onclick="location.reload()">↻ Làm mới</button></div>
<section class="hero"><div class="eyebrow">KỲ SẮP TỚI · {esc(date_vi(target))}</div><h1>{esc(portfolio.get('title') or (doc.get('top_signals') or {}).get('subtitle') or 'Đang rà soát')}</h1><p>{esc(portfolio.get('reason') or (doc.get('top_signals') or {}).get('note') or '')}</p><div class="stats"><div class="stat"><span>Dữ liệu khóa đến</span><b>{esc(date_vi(locked))}</b></div><div class="stat"><span>Vốn lô + Xiên khuyến nghị</span><b>{vnd(total_capital)}</b></div><div class="stat"><span>Xiên 2</span><b>{esc(len(xien.get('pairs') or []))} cặp · {vnd(xien_capital)}</b></div><div class="stat"><span>Trạng thái lệnh</span><b style="font-size:13px">{esc(execution)}</b></div></div></section>
<main class="methods">{cards}</main><section class="summary"><div><b>Cập nhật {esc(generated or '—')}</b><br><small>Xiên 2 tự động ghép toàn bộ tổ hợp từ các số có vốn; chỉ ghi P/L sau xác nhận đánh.</small></div><div class="actions"><a class="link" href="{SHEET_URL}" target="_blank" rel="noopener">Mở Google Sheet ↗</a></div></section><div class="foot">A1, X2, X3 xét song song; ROLL7 chỉ khi cả ba A0; Xiên 2 tự động khi có từ 02 mã được cấp vốn.</div></div></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    doc = json.loads(CURRENT.read_text(encoding="utf-8"))
    expected = render(doc)
    if args.check:
        if not INDEX.exists() or INDEX.read_text(encoding="utf-8") != expected:
            raise SystemExit("index.html is not synchronized with data/current.json")
        print("FAST_DASHBOARD_OK")
        return
    INDEX.write_text(expected, encoding="utf-8")
    print(f"FAST_DASHBOARD_WRITTEN target={doc.get('target_date')} bytes={len(expected.encode('utf-8'))}")


if __name__ == "__main__":
    main()
