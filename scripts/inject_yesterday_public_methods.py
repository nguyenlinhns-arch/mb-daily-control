#!/usr/bin/env python3
"""Inject yesterday's public-method recommendations and settled outcome after the latest XSMB result.

Only the six non-paid public methods are included. Recommendations are rebuilt
with history ending at T-1 and then settled against T, so the public block is
prospective evidence rather than a post-outcome selection. Paid/current 4SO
outputs are never read by this module.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import build_public_methods as public_methods
import build_statistics_site as statistics

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "MB_PUBLIC_METHOD_YESTERDAY_SETTLEMENT_V1"
MARKER = 'data-yesterday-public-methods="true"'
STYLE_ID = "lm-yesterday-public-methods-style"
RESULT_HEADING = "<h2>27 mã kỳ gần nhất</h2>"
TOOLS_HEADING = "<h2>Công cụ thống kê XSMB</h2>"
FORBIDDEN = re.compile(r"(?:canonical|final)[_-]?(?:codes|pairs)|\b4SO\b", re.I)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def dmy(value: str) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def build_doc(history: list[tuple[date, list[str]]]) -> dict[str, Any]:
    if len(history) < 182:
        raise ValueError("History too short for yesterday public-method settlement")
    result_date, actual_codes = history[-1]
    prior = history[:-1]
    if prior[-1][0] != result_date - timedelta(days=1):
        raise ValueError("Yesterday public-method data lock is not T-1")

    recommendation = public_methods.build_payload(prior, result_date)
    if recommendation.get("outcome_known_at_selection") is not False:
        raise ValueError("Public recommendation is not prospective")
    if recommendation.get("data_lock") != (result_date - timedelta(days=1)).isoformat():
        raise ValueError("Public recommendation data lock mismatch")

    actual = Counter(actual_codes)
    rows: list[dict[str, Any]] = []
    method_hit_count = 0
    for method in recommendation.get("methods") or []:
        mid = str(method.get("id") or "")
        name = str(method.get("name") or mid)
        if "4SO" in mid.upper() or "4SO" in name.upper():
            raise ValueError("Paid 4SO leaked into yesterday public methods")
        numbers = [str(value).zfill(2)[-2:] for value in (method.get("numbers") or [])]
        if not numbers or any(not re.fullmatch(r"\d{2}", value) for value in numbers):
            raise ValueError(f"Invalid recommendation for {mid}")
        hits = [{"number": number, "count": int(actual[number])} for number in numbers if actual[number] > 0]
        if hits:
            method_hit_count += 1
        rows.append({
            "id": mid,
            "name": name,
            "numbers": numbers,
            "hits": hits,
            "status": "hit" if hits else "miss",
        })

    payload: dict[str, Any] = {
        "schema_version": SCHEMA,
        "recommendation_date": result_date.isoformat(),
        "data_lock": (result_date - timedelta(days=1)).isoformat(),
        "result_date": result_date.isoformat(),
        "source_status": recommendation.get("source_status"),
        "source_row_count": recommendation.get("source_row_count"),
        "source_sha256": recommendation.get("source_sha256"),
        "outcome_known_at_selection": False,
        "method_count": len(rows),
        "method_hit_count": method_hit_count,
        "methods": rows,
    }
    if len(rows) != 6:
        raise ValueError(f"Expected 6 public methods, found {len(rows)}")
    if FORBIDDEN.search(json.dumps(payload, ensure_ascii=False)):
        raise ValueError("Forbidden paid/canonical field in yesterday public-method payload")
    return payload


STYLE = r'''<style id="lm-yesterday-public-methods-style">
.portal-home .lm-yday-methods{padding:5px 0 15px}.portal-home .lm-yday-shell{background:#fff;border:1px solid #dfe4e9;border-radius:17px;box-shadow:0 5px 20px rgba(17,35,50,.045);overflow:hidden}.portal-home .lm-yday-head{padding:15px 16px 12px;border-bottom:1px solid #edf0f2;display:flex;align-items:flex-end;justify-content:space-between;gap:14px}.portal-home .lm-yday-head h2{margin:0;color:#142231;font-size:21px;line-height:1.2}.portal-home .lm-yday-head p{margin:4px 0 0;color:#6b7883;font-size:11.5px;line-height:1.45}.portal-home .lm-yday-summary{flex:0 0 auto;padding:7px 10px;border-radius:999px;background:#f3f6f4;color:#44624c;font-size:11px;font-weight:900;white-space:nowrap}.portal-home .lm-yday-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0}.portal-home .lm-yday-card{min-width:0;padding:13px 15px;border-bottom:1px solid #edf0f2}.portal-home .lm-yday-card:nth-child(odd){border-right:1px solid #edf0f2}.portal-home .lm-yday-card-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}.portal-home .lm-yday-card-head b{font-size:13px;color:#263847}.portal-home .lm-yday-status{padding:4px 7px;border-radius:999px;background:#f5f2f2;color:#78696b;font-size:9px;font-weight:950;letter-spacing:.02em;white-space:nowrap}.portal-home .lm-yday-status.is-hit{background:#e8f4eb;color:#376947}.portal-home .lm-yday-row{display:grid;grid-template-columns:116px minmax(0,1fr);gap:9px;align-items:start;margin-top:6px}.portal-home .lm-yday-label{padding-top:5px;color:#89949c;font-size:9px;font-weight:850;text-transform:uppercase;letter-spacing:.04em}.portal-home .lm-yday-balls{display:flex;gap:5px;flex-wrap:wrap}.portal-home .lm-yday-ball{width:29px;height:29px;display:grid;place-items:center;border:1px solid #dce2e7;border-radius:50%;background:#fbfcfd;color:#283b4a;font-size:11px;font-weight:950;font-variant-numeric:tabular-nums}.portal-home .lm-yday-ball.is-hit{border-color:#b9d9c1;background:#edf8f0;color:#2f6840}.portal-home .lm-yday-result{min-height:29px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;color:#66747f;font-size:11px}.portal-home .lm-yday-result strong{padding:4px 7px;border-radius:8px;background:#edf8f0;color:#326744;font-size:10.5px}.portal-home .lm-yday-foot{padding:10px 15px 12px;background:#fafbfc;color:#79858e;font-size:9.5px;line-height:1.45}.portal-home .lm-yday-foot b{color:#5e6a73}
@media(max-width:700px){.portal-home .lm-yday-methods{padding:3px 0 11px}.portal-home .lm-yday-shell{border-radius:14px}.portal-home .lm-yday-head{padding:12px;display:block}.portal-home .lm-yday-head h2{font-size:18px}.portal-home .lm-yday-head p{font-size:10.5px}.portal-home .lm-yday-summary{display:inline-flex;margin-top:8px;font-size:10px;padding:5px 8px}.portal-home .lm-yday-grid{grid-template-columns:1fr}.portal-home .lm-yday-card{padding:11px 12px;border-right:0!important}.portal-home .lm-yday-card-head{margin-bottom:7px}.portal-home .lm-yday-card-head b{font-size:12px}.portal-home .lm-yday-row{grid-template-columns:94px minmax(0,1fr);gap:7px;margin-top:5px}.portal-home .lm-yday-label{font-size:8.5px}.portal-home .lm-yday-ball{width:28px;height:28px;font-size:11px}.portal-home .lm-yday-result{font-size:10.5px}.portal-home .lm-yday-foot{padding:9px 12px;font-size:9px}}
@media(max-width:390px){.portal-home .lm-yday-row{grid-template-columns:82px minmax(0,1fr)}.portal-home .lm-yday-card{padding:10px}.portal-home .lm-yday-ball{width:27px;height:27px}}
</style>'''


def render(payload: dict[str, Any]) -> str:
    rec_date = str(payload["recommendation_date"])
    lock_date = str(payload["data_lock"])
    methods = payload.get("methods") or []
    cards: list[str] = []
    for method in methods:
        hit_numbers = {str(hit["number"]): int(hit["count"]) for hit in method.get("hits") or []}
        balls = "".join(
            f'<span class="lm-yday-ball {"is-hit" if number in hit_numbers else ""}">{esc(number)}</span>'
            for number in method.get("numbers") or []
        )
        hits = method.get("hits") or []
        if hits:
            result = "".join(f'<strong>{esc(hit["number"])} × {int(hit["count"])}</strong>' for hit in hits)
        else:
            result = '<span>Không xuất hiện trong 27 mã.</span>'
        cards.append(
            f'<article class="lm-yday-card"><div class="lm-yday-card-head"><b>{esc(method["name"])}</b>'
            f'<span class="lm-yday-status {"is-hit" if hits else ""}">{"CÓ XUẤT HIỆN" if hits else "CHƯA XUẤT HIỆN"}</span></div>'
            f'<div class="lm-yday-row"><span class="lm-yday-label">Số khuyến nghị</span><div class="lm-yday-balls">{balls}</div></div>'
            f'<div class="lm-yday-row"><span class="lm-yday-label">Kết quả khuyến nghị</span><div class="lm-yday-result">{result}</div></div></article>'
        )
    return (
        f'<section class="portal-section lm-yday-methods" {MARKER}><div class="portal-wrap"><div class="lm-yday-shell">'
        f'<div class="lm-yday-head"><div><h2>Số khuyến nghị hôm qua các phương pháp</h2>'
        f'<p>Khuyến nghị ngày {dmy(rec_date)} được tạo bằng dữ liệu khóa đến {dmy(lock_date)}, trước khi có kết quả ngày {dmy(rec_date)}.</p></div>'
        f'<span class="lm-yday-summary">{int(payload["method_hit_count"])}/{int(payload["method_count"])} phương pháp có số xuất hiện</span></div>'
        f'<div class="lm-yday-grid">{"".join(cards)}</div>'
        f'<div class="lm-yday-foot"><b>Nguyên tắc đối chiếu:</b> chỉ đánh dấu số đã nằm trong khuyến nghị trước kết quả và sau đó xuất hiện trong 27 mã ngày {dmy(rec_date)}; số nháy được ghi theo số lần xuất hiện thực tế. Đây là dữ liệu đối chiếu lịch sử, không phải cam kết cho ngày tiếp theo.</div>'
        f'</div></div></section>'
    )


def result_section(text: str) -> tuple[int, int] | None:
    """Find the latest-result section in BODY, never a CSS class name in HEAD."""
    body = text.find("<body")
    if body < 0:
        return None
    pos = text.find(RESULT_HEADING, body)
    if pos < 0:
        match = re.search(r"<h2>\s*27\s+mã\s+kỳ\s+gần\s+nhất\s*</h2>", text[body:], flags=re.I)
        if not match:
            return None
        pos = body + match.start()
    start = text.rfind("<section", body, pos)
    end = text.find("</section>", pos)
    if start < 0 or end < 0:
        return None
    return start, end + len("</section>")


def inject(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    home = root / "index.html"
    if not home.is_file():
        raise FileNotFoundError(home)
    text = home.read_text(encoding="utf-8")
    block = render(payload)
    if f'id="{STYLE_ID}"' not in text:
        if "</head>" not in text:
            raise ValueError("Homepage missing </head>")
        text = text.replace("</head>", STYLE + "\n</head>", 1)

    existing = re.search(r'<section\b[^>]*data-yesterday-public-methods="true"[^>]*>.*?</section>', text, flags=re.I | re.S)
    if existing:
        text = text[:existing.start()] + block + text[existing.end():]
    else:
        result = result_section(text)
        if not result:
            raise ValueError("Latest XSMB result section not found")
        _, end = result
        text = text[:end] + block + text[end:]

    body = text.find("<body")
    result_pos = text.find(RESULT_HEADING, body)
    marker_pos = text.find(MARKER, body)
    tools_pos = text.find(TOOLS_HEADING, body)
    if result_pos < 0 or marker_pos < 0 or tools_pos < 0:
        raise ValueError("Homepage ordering markers missing after yesterday proof injection")
    if not (result_pos < marker_pos < tools_pos):
        raise ValueError("Yesterday method proof is not immediately in the result-to-tools flow")
    if FORBIDDEN.search(block):
        raise ValueError("Forbidden 4SO/canonical content in public yesterday block")

    home.write_text(text, encoding="utf-8")
    (root / "yesterday-public-methods.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "status": "PASS",
        "recommendation_date": payload["recommendation_date"],
        "data_lock": payload["data_lock"],
        "methods": payload["method_count"],
        "methods_with_hits": payload["method_hit_count"],
    }


def apply(root: Path) -> dict[str, Any]:
    payload = build_doc(statistics.load_history())
    stats_path = root / "statistics-data.json"
    if stats_path.is_file():
        stats_doc = json.loads(stats_path.read_text(encoding="utf-8"))
        if str(stats_doc.get("updated_through")) != payload["result_date"]:
            raise ValueError("Yesterday public-method result date does not match statistics data lock")
    return inject(root, payload)


def self_test() -> None:
    import tempfile

    start = date(2025, 12, 1)
    history: list[tuple[date, list[str]]] = []
    for offset in range(260):
        codes = [f"{(offset * 11 + index * 17) % 100:02d}" for index in range(27)]
        history.append((start + timedelta(days=offset), codes))
    payload = build_doc(history)
    assert payload["method_count"] == 6
    assert payload["data_lock"] == (history[-1][0] - timedelta(days=1)).isoformat()
    assert payload["outcome_known_at_selection"] is False
    assert "4SO" not in json.dumps(payload, ensure_ascii=False)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Intentionally place the old class name in HEAD first: the production
        # locator must anchor to the visible result heading in BODY instead.
        (root / "index.html").write_text(
            '<html><head><style>.portal-result-card{padding:10px}</style></head><body class="portal-home"><main>'
            '<section class="portal-section"><div><h2>27 mã kỳ gần nhất</h2></div><div class="portal-result-card">latest</div></section>'
            '<section class="portal-section"><h2>Công cụ thống kê XSMB</h2></section>'
            '</main></body></html>', encoding="utf-8"
        )
        result = inject(root, payload)
        output = (root / "index.html").read_text(encoding="utf-8")
        assert result["methods"] == 6
        assert MARKER in output
        body = output.find("<body")
        assert output.find(RESULT_HEADING, body) < output.find(MARKER, body) < output.find(TOOLS_HEADING, body)
        assert (root / "yesterday-public-methods.json").is_file()
    print("YESTERDAY_PUBLIC_METHODS_SELF_TEST_OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT / "_site")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(apply(args.output_root.resolve()), ensure_ascii=False))


if __name__ == "__main__":
    main()
