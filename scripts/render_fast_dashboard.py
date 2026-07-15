#!/usr/bin/env python3
"""Render a zero-dependency A1/X2/X3/ROLL7/ROLL30/Xiên 2/Đề dashboard."""
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
    if "ROLL30" in text:
        return "roll30"
    if "ROLL7" in text or "5-OF-7" in text:
        return "roll7"
    if "DE_WATCH" in text or "MB ĐỀ" in text or "ĐẦU/ĐUÔI" in text:
        return "de"
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
    if "NEAR" in text or "GẦN" in text or "THEO DÕI" in text or "WATCH" in text:
        return "near"
    if any(token in text for token in ("EMPTY", "TRỐNG", "NOT_APPLICABLE", "KHÔNG KÍCH HOẠT", "LT2", "PHANH XIÊN", "SHADOW_ONLY_TWO_LO_LOSS")):
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
            "method": "Rescue50 khi A1/X2/X3 đều A0",
            "status": state.get("status") or state.get("summary") or "CHƯA KÍCH HOẠT",
            "visual_status": "PASS" if numbers else "EMPTY",
            "points_per_code": 50,
            "code_count": len(numbers),
            "capital_vnd": state.get("capital_vnd") or 0,
            "reason": state.get("reason") or "Chỉ xét khi cả A1, X2 và X3 đều A0.",
            "numbers": [
                {
                    "code": code,
                    "points": points.get(code, 50),
                    "capital_vnd": int(points.get(code, 50)) * 23000,
                    "role": "ROLL7 Rescue50",
                    "visual_status": "PASS",
                }
                for code in numbers
            ],
        }
    if key == "roll30":
        group = group_by_id(doc, "ROLL30")
        state = doc.get("roll30_status") or group
        numbers = state.get("selected_numbers") or []
        points = state.get("points_by_code") or {}
        return {
            "id": "ROLL30_RESCUE50",
            "label": "MB ROLL30 30/30 · Rescue",
            "method": "Coverage 30/30 · Other50",
            "status": state.get("status") or state.get("summary") or "CHƯA KÍCH HOẠT",
            "visual_status": "PASS" if numbers else "EMPTY",
            "points_per_code": 50,
            "code_count": len(numbers),
            "capital_vnd": state.get("capital_vnd") or 0,
            "reason": state.get("reason") or "Chỉ kích hoạt sau Natural A0 và ROLL7 không phát số.",
            "numbers": [
                {
                    "code": code,
                    "points": points.get(code, 50),
                    "capital_vnd": int(points.get(code, 50)) * 23000,
                    "role": "ROLL30 Rescue50",
                    "visual_status": "PASS",
                }
                for code in numbers
            ],
        }
    if key == "xien2":
        rec = doc.get("xien2_recommendation") or group_by_id(doc, "XIEN", "XIEN2")
        pairs = rec.get("pairs") or rec.get("selected_numbers") or []
        brake = bool(rec.get("brake_active"))
        reference = int(rec.get("reference_capital_per_pair_vnd") or rec.get("capital_per_pair_vnd") or 100000)
        real_per_pair = 0 if brake else int(rec.get("capital_per_pair_vnd") or reference)
        caption = f"Shadow 0đ · chuẩn {vnd(reference)}/cặp" if brake else f"{vnd(real_per_pair)}/cặp"
        return {
            "id": "XIEN2_AUTO_PAIRS",
            "label": "Xiên 2 tự động",
            "method": "Ghép toàn bộ cặp từ số được cấp vốn",
            "status": rec.get("status") or rec.get("summary") or "KHÔNG KÍCH HOẠT",
            "visual_status": "EMPTY" if brake or not pairs else "PASS",
            "points_per_pair": rec.get("points_per_pair") or 100,
            "reference_capital_per_pair_vnd": reference,
            "capital_per_pair_vnd": real_per_pair,
            "code_count": len(pairs),
            "pair_count": len(pairs),
            "paper_capital_vnd": rec.get("paper_capital_vnd") or len(pairs) * reference,
            "capital_vnd": rec.get("capital_vnd") or 0,
            "brake_active": brake,
            "reason": rec.get("reason") or "Cần tối thiểu 02 số được cấp vốn.",
            "numbers": [
                {
                    "code": pair,
                    "points": 0,
                    "caption": caption,
                    "capital_vnd": 0 if brake else real_per_pair,
                    "role": "Xiên 2 Shadow do phanh hai ngày lô thua" if brake else "Xiên 2 tự động · chờ xác nhận",
                    "visual_status": "EMPTY" if brake else "PASS",
                }
                for pair in pairs
            ],
        }
    if key == "de":
        watch = doc.get("de_watchlist") or group_by_id(doc, "DE", "DE_DIGIT")
        return {
            "id": "DE_WATCHLIST",
            "label": "MB Đề · Đầu/đuôi",
            "method": watch.get("method") or "Đề Gan Lead18 / Head-Tail Strict v2",
            "status": watch.get("status") or watch.get("summary") or "A0 · THEO DÕI",
            "visual_status": "NEAR" if watch.get("state") == "PAPER_PASS" else "FAIL",
            "points_per_code": 0,
            "code_count": 0,
            "capital_vnd": 0,
            "reason": watch.get("reason") or "Theo dõi mốc điều kiện; chưa cấp vốn tự động.",
            "numbers": [],
            "candidates": watch.get("candidates") or [],
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
        "numbers": [
            {"code": code, "points": pp, "capital_vnd": pp * 23000, "role": group.get("summary") or ""}
            for code in selected
        ],
    }


def current_methods(doc: dict[str, Any]) -> list[dict[str, Any]]:
    source = list((doc.get("top_signals") or {}).get("methods") or [])
    found = {method_key(item): item for item in source}
    return [found.get(key) or synthesize_method(doc, key) for key in ("a1", "x2", "x3", "roll7", "roll30", "xien2", "de")]


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
    candidates = [
        item for item in (group.get("candidates") or [])
        if str(item.get("component") or "").upper() != "A1_REVERSE50"
    ][:3]
    if not candidates:
        return ""
    rows = []
    for item in candidates:
        metrics = f"Gan {item.get('gan', '—')} · Gmax {item.get('gmax', '—')} · Score {item.get('score', '—')}"
        rows.append(
            f'<div class="watch-row"><b>{esc(item.get("code") or "—")}</b>'
            f'<span>{esc(metrics)}</span><small>Mốc {date_vi(item.get("earliest_eligible_date"))}</small></div>'
        )
    return '<div class="watch"><h4>Top 3 A1 theo dõi</h4>' + "".join(rows) + "</div>"


def de_watch(method: dict[str, Any], doc: dict[str, Any]) -> str:
    candidates = method.get("candidates") or (doc.get("de_watchlist") or {}).get("candidates") or (group_by_id(doc, "DE").get("candidates") or [])
    if not candidates:
        return '<div class="watch"><h4>Danh sách Đề đang theo dõi</h4><div class="empty">Chưa có dữ liệu Đề</div></div>'
    rows = []
    for item in candidates:
        metrics = (
            f"Gan {item.get('gan', '—')} · Gmax {item.get('gmax', '—')} · "
            f"Score {float(item.get('score') or 0):.3f} · Occ30 {item.get('occ30', '—')} · Lead {item.get('lead', '—')}"
        )
        title = item.get("earliest_condition") or item.get("required_gate") or ""
        rows.append(
            f'<div class="de-watch-row" title="{esc(title)}"><div><b>{esc(item.get("code") or "—")}</b>'
            f'<small>{esc(item.get("status") or "WATCH")}</small></div><span>{esc(metrics)}</span>'
            f'<em>Mốc sớm nhất <strong>{date_vi(item.get("earliest_eligible_date"))}</strong></em>'
            f'<p>{esc(item.get("required_gate") or "")}</p></div>'
        )
    return '<div class="watch de-watch"><h4>Danh sách Đề đang theo dõi & mốc có thể vào</h4>' + "".join(rows) + '<small>Mốc là lower bound có điều kiện và được tính lại sau mỗi kỳ khóa.</small></div>'


def method_card(method: dict[str, Any], doc: dict[str, Any]) -> str:
    key = method_key(method)
    tone = visual_tone(method.get("visual_status") or method.get("status"))
    symbols = {"a1": "A1", "x2": "X2", "x3": "X3", "roll7": "R7", "roll30": "R30", "xien2": "X2+", "de": "ĐỀ", "other": "MB"}
    numbers = method.get("numbers") or []
    tiles = "".join(number_tile(item, method) for item in numbers)
    if key == "de":
        tiles = '<div class="empty">Chưa có lệnh Đề tiền thật · vốn 0đ</div>'
    elif not tiles:
        tiles = '<div class="empty">Không có mã/cặp được khuyến nghị</div>'
    reason = method.get("reason") or method.get("note") or ""
    watch = a1_watch(doc) if key == "a1" else de_watch(method, doc) if key == "de" else ""

    if key == "xien2":
        if method.get("brake_active"):
            first_label, first_value = "Vốn thật/cặp", vnd(0)
            second_label, second_value = "Cặp Shadow", method.get("pair_count") or method.get("code_count") or 0
        else:
            first_label, first_value = "Vốn/cặp", vnd(method.get("capital_per_pair_vnd") or 100000)
            second_label, second_value = "Số cặp", method.get("pair_count") or method.get("code_count") or 0
    elif key == "de":
        first_label, first_value = "Điểm thật", 0
        second_label, second_value = "Ứng viên", len(method.get("candidates") or (doc.get("de_watchlist") or {}).get("candidates") or [])
    else:
        first_label, first_value = "Điểm/số", method.get("points_per_code") or 0
        second_label, second_value = "Số mã", method.get("code_count") or 0

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
    standard_capital = int(portfolio.get("standard_capital_vnd") or portfolio.get("capital_vnd") or pnl.get("today_pending_standard_capital_vnd") or pnl.get("today_pending_capital_vnd") or 0)
    xien_capital = int(xien.get("capital_vnd") or portfolio.get("xien2_recommended_capital_vnd") or 0)
    total_capital = standard_capital + xien_capital
    execution = pending.get("status") or portfolio.get("pnl_status") or "—"
    generated = str(doc.get("generated_at") or "").replace("T", " ")[:19]
    xien_pairs = len(xien.get("pairs") or [])
    xien_stat = f"Shadow {xien_pairs} cặp · 0đ" if xien.get("brake_active") else f"{xien_pairs} cặp · {vnd(xien_capital)}"
    summary_note = (
        "Xiên 2 đang bị phanh sau hai ngày lô có lệnh liên tiếp cùng âm; các cặp chỉ Shadow 0đ."
        if xien.get("brake_active")
        else "Đề hiển thị danh sách đang theo dõi và mốc sớm nhất có thể xét; mốc luôn có điều kiện."
    )
    sync_meta = (
        f"Report_Run_ID={doc.get('report_run_id') or '—'} · "
        f"Config_ID={doc.get('config_id') or '—'} · "
        f"Data_Lock_Date={locked or '—'} · "
        f"Content_Hash={doc.get('content_hash') or '—'}"
    )

    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#0d2239"><meta name="description" content="MB Daily Control — kế hoạch XSMB kỳ sắp tới"><title>MB Daily Control · {esc(date_vi(target))}</title>
<style>
:root{{--bg:#071421;--panel:#0d2239;--panel2:#122c48;--text:#edf6ff;--muted:#9db0c3;--line:#29425a;--green:#21c482;--red:#ff6470;--amber:#f4c95d}}*{{box-sizing:border-box}}html{{background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}}body{{margin:0}}.wrap{{width:min(1180px,calc(100% - 24px));margin:auto;padding:18px 0 36px}}.bar{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}}.brand{{display:flex;align-items:center;gap:10px}}.logo{{display:grid;place-items:center;width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#1c7cff,#25c58a);font-weight:900}}button,.link{{border:1px solid var(--line);background:#102841;color:var(--text);padding:10px 14px;border-radius:10px;text-decoration:none;font-weight:700;cursor:pointer}}.hero{{background:linear-gradient(135deg,#102a45,#0d2137);border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px}}.eyebrow{{color:#74b5ff;font-weight:800;font-size:12px;letter-spacing:.08em}}h1{{font-size:clamp(26px,4vw,46px);margin:7px 0}}.hero p{{color:var(--muted);margin:6px 0}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}}.stat{{background:#0a1c2e;border:1px solid var(--line);border-radius:12px;padding:12px}}.stat span{{display:block;color:var(--muted);font-size:12px}}.stat b{{display:block;margin-top:5px;font-size:18px}}.methods{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}.method-card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px}}.method-card.pass{{border-color:#1e9d70}}.method-card.fail{{border-color:#9b4050}}.method-card.near{{border-color:#9b812d}}.method-card.idle{{border-color:#5f7080}}.method-card header{{display:flex;gap:11px;align-items:center}}.symbol{{display:grid;place-items:center;min-width:42px;height:42px;border-radius:11px;background:var(--panel2);font-weight:900}}h3{{margin:0;font-size:19px}}.method-card header p{{margin:3px 0 0;color:var(--muted);font-size:12px}}.status{{display:inline-block;margin:12px 0;padding:6px 9px;border-radius:999px;font-size:12px;font-weight:900}}.status.pass{{background:#123e32;color:#69e6b0}}.status.fail{{background:#45202a;color:#ff9ca5}}.status.near{{background:#463b17;color:#ffe083}}.status.idle{{background:#253544;color:#c1cfda}}.numbers{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}}.number,.empty{{min-height:112px;border:1px solid var(--line);border-radius:12px;background:#0a1b2c;padding:10px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}}.number strong{{font-size:34px;line-height:1}}.number span{{font-size:12px;margin-top:8px}}.number small{{color:var(--muted);margin-top:4px}}.number.pass{{border-color:#1f9f71}}.number.fail{{border-color:#713440}}.number.near{{border-color:#9b812d}}.number.idle{{border-color:#465a6c}}.empty{{grid-column:1/-1;color:var(--muted)}}.reason{{color:var(--muted);font-size:13px;min-height:36px}}.method-card footer{{display:flex;justify-content:space-between;gap:8px;border-top:1px solid var(--line);padding-top:12px;font-size:12px;color:var(--muted)}}.method-card footer b{{display:block;color:var(--text);font-size:14px}}.watch{{border-top:1px dashed var(--line);margin-top:12px;padding-top:10px}}.watch h4{{margin:0 0 7px;font-size:13px}}.watch-row{{display:grid;grid-template-columns:74px 1fr auto;gap:8px;padding:7px 0;font-size:11px;color:var(--muted)}}.watch-row b{{color:var(--text);font-size:14px}}.de-watch-row{{display:grid;grid-template-columns:90px 1fr auto;gap:8px;padding:10px 0;border-bottom:1px solid var(--line);align-items:center}}.de-watch-row b{{display:block;font-size:17px;color:var(--text)}}.de-watch-row small{{color:var(--muted);font-size:10px}}.de-watch-row span{{font-size:12px;color:var(--muted)}}.de-watch-row em{{font-style:normal;font-size:11px;color:var(--amber);text-align:right}}.de-watch-row p{{grid-column:1/-1;margin:0;color:var(--muted);font-size:10px}}.summary{{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-top:14px;padding:14px;border:1px solid var(--line);border-radius:14px;background:#0b1d30}}.summary small{{color:var(--muted)}}.actions{{display:flex;gap:8px;flex-wrap:wrap}}.foot{{text-align:center;color:var(--muted);font-size:12px;margin-top:18px}}@media(max-width:760px){{.stats{{grid-template-columns:repeat(2,1fr)}}.methods{{grid-template-columns:1fr}}.numbers{{grid-template-columns:repeat(2,1fr)}}.summary{{align-items:flex-start;flex-direction:column}}.watch-row{{grid-template-columns:66px 1fr}}.de-watch-row{{grid-template-columns:80px 1fr}}.de-watch-row em{{grid-column:2;text-align:left}}}}
</style></head>
<body data-static-dashboard="1"><div class="wrap"><div class="bar"><div class="brand"><div class="logo">MB</div><div><b>MB Daily Control</b><div style="color:var(--muted);font-size:12px">XSMB Daily Validation</div></div></div><button type="button" onclick="location.reload()">↻ Làm mới</button></div>
<section class="hero"><div class="eyebrow">KỲ SẮP TỚI · {esc(date_vi(target))}</div><h1>{esc(portfolio.get('title') or (doc.get('top_signals') or {}).get('subtitle') or 'Đang rà soát')}</h1><p>{esc(portfolio.get('reason') or (doc.get('top_signals') or {}).get('note') or '')}</p><div class="stats"><div class="stat"><span>Dữ liệu khóa đến</span><b>{esc(date_vi(locked))}</b></div><div class="stat"><span>Vốn thật kỳ tới</span><b>{vnd(total_capital)}</b></div><div class="stat"><span>Xiên 2</span><b>{esc(xien_stat)}</b></div><div class="stat"><span>Trạng thái lệnh</span><b style="font-size:13px">{esc(execution)}</b></div></div></section>
<main class="methods">{cards}</main><section class="summary"><div><b>Cập nhật {esc(generated or '—')}</b><br><small>{esc(summary_note)}</small><br><small style="overflow-wrap:anywhere">{esc(sync_meta)}</small></div><div class="actions"><a class="link" href="{SHEET_URL}" target="_blank" rel="noopener">Mở Google Sheet ↗</a></div></section><div class="foot">MB ROLL30 30/30 Production – Core100/Other50 · Natural xét song song; Natural A0 thì ROLL7 trước, ROLL30 sau; không martingale, không cộng giỏ phụ.</div></div></body></html>
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
