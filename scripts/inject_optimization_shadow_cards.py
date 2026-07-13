#!/usr/bin/env python3
"""Inject Xiên Router and Triple Normalizer shadow cards into the static dashboard."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
CURRENT = ROOT / "data" / "optimization-current.json"
START = "<!-- COVERAGE_OPT_SHADOW_START -->"
END = "<!-- COVERAGE_OPT_SHADOW_END -->"


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def vnd(value: Any) -> str:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        number = 0
    return f"{number:,}đ".replace(",", ".")


def tiles(values: list[str], caption: str) -> str:
    if not values:
        return '<div class="empty">Không có cặp/mã Shadow hôm nay</div>'
    return "".join(
        f'<div class="number near"><strong>{esc(value)}</strong><span>{esc(caption)}</span><small>Vốn thật 0đ</small></div>'
        for value in values
    )


def render(doc: dict[str, Any]) -> str:
    router = doc.get("xien2_router") or {}
    normalizer = doc.get("triple_normalizer") or {}
    routed = router.get("status") == "ROUTED_SHADOW"
    router_tone = "near" if routed else "idle"
    router_status = "SHADOW · ROUTER ĐÃ LỌC CẶP" if routed else "SHADOW · TRÙNG BẢN HIỆN HÀNH"
    router_pairs = router.get("router_pairs") or []
    baseline_pairs = router.get("baseline_pairs") or []
    router_reason = (
        f"Baseline {len(baseline_pairs)} cặp; Router {len(router_pairs)} cặp; "
        f"tiết kiệm giả lập {vnd(router.get('capital_saving_vnd', 0))}. "
        "Không thay đổi lệnh thật hoặc độ phủ."
    )

    active_normalizer = normalizer.get("status") == "ACTIVE_TRIPLE_PASS_SHADOW"
    norm_tone = "near" if active_normalizer else "idle"
    norm_status = "SHADOW · TRIPLE-PASS ĐANG HOẠT ĐỘNG" if active_normalizer else "SHADOW · KHÔNG ÁP DỤNG HÔM NAY"
    shadow_points = normalizer.get("shadow_points_by_code") or {}
    norm_values = [f"{code}×{points}" for code, points in shadow_points.items()] if active_normalizer else []
    norm_reason = (
        f"Chỉ hoạt động khi A1, X2 và X3 cùng đạt. Tiết kiệm giả lập "
        f"{vnd(normalizer.get('capital_saving_vnd', 0))}; vốn thật không đổi."
    )

    return f"""{START}
    <article class="method-card {router_tone}">
      <header><span class="symbol">XR</span><div><h3>Xiên 2 Confluence Router V1</h3><p>Challenger Shadow · giữ nguyên ngày phát số</p></div></header>
      <div class="status {router_tone}">{esc(router_status)}</div>
      <div class="numbers">{tiles(router_pairs, '100.000đ/cặp · Shadow')}</div>
      <p class="reason">{esc(router_reason)}</p>
      <footer><span>Cặp baseline <b>{len(baseline_pairs)}</b></span><span>Cặp Router <b>{len(router_pairs)}</b></span><span>Vốn thật <b>0đ</b></span></footer>
    </article>
    <article class="method-card {norm_tone}">
      <header><span class="symbol">TN</span><div><h3>Triple Confluence Normalizer</h3><p>Challenger Shadow · A1 50→30 chỉ khi triple-pass</p></div></header>
      <div class="status {norm_tone}">{esc(norm_status)}</div>
      <div class="numbers">{tiles(norm_values, 'Điểm Shadow')}</div>
      <p class="reason">{esc(norm_reason)}</p>
      <footer><span>Vốn baseline <b>{vnd(normalizer.get('baseline_capital_vnd', 0))}</b></span><span>Vốn Shadow <b>{vnd(normalizer.get('shadow_capital_vnd', 0))}</b></span><span>Vốn thật <b>0đ</b></span></footer>
    </article>
{END}"""


def patch(index: str, block: str) -> str:
    if START in index and END in index:
        left, rest = index.split(START, 1)
        _, right = rest.split(END, 1)
        return left + block + right
    marker = "  </main>"
    if marker not in index:
        raise RuntimeError("Không tìm thấy </main> trong index.html")
    return index.replace(marker, block + "\n" + marker, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    doc = json.loads(CURRENT.read_text(encoding="utf-8"))
    original = INDEX.read_text(encoding="utf-8")
    expected = patch(original, render(doc))
    if args.check:
        if original != expected:
            raise SystemExit("Optimization shadow cards are stale")
        print("OPTIMIZATION_SHADOW_CARDS_OK")
        return
    INDEX.write_text(expected, encoding="utf-8")
    print("OPTIMIZATION_SHADOW_CARDS_WRITTEN")


if __name__ == "__main__":
    main()
