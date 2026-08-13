#!/usr/bin/env python3
"""Publish a fail-closed report for an already-completed XSMB draw.

This automation intentionally does not calculate or publish future selections,
betting recommendations, stakes, orders, or financial profit/loss. It only:

1. cross-checks an already-published draw against at least two public sources;
2. appends the locked 27-code result to the repository history;
3. records a non-financial source/audit entry; and
4. refreshes the retrospective seven-layer block on the public website.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from build_public_snapshot import crosscheck_draw, load_history, save_history, validate_rows


ROOT = Path(__file__).resolve().parents[1]
INDEX_FILE = ROOT / "site-v2" / "index.html"
SAMPLE_FILE = ROOT / "site-v2" / "mau-bao-cao.html"
AUDIT_FILE = ROOT / "data" / "completed-draw-audit.json"
ACCESS_FILE = ROOT / "data" / "source-access.json"
HISTORICAL_PROOF_FILE = ROOT / "data" / "public-historical-proof.json"
VN = timezone(timedelta(hours=7))
START_MARKER = "    <!-- COMPLETED_DRAW_REPORT:START -->"
END_MARKER = "    <!-- COMPLETED_DRAW_REPORT:END -->"
SOURCE_LABELS = {
    "kqxs": "KQXS",
    "minhngoc": "Minh Ngọc",
    "xosodaiphat": "Xổ Số Đại Phát",
    "xosothienphu": "Xổ Số Thiên Phú",
}


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def write_json_if_changed(path: Path, value: Any) -> bool:
    content = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def vi_date(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def load_historical_proof() -> dict[str, Any]:
    proof = json.loads(HISTORICAL_PROOF_FILE.read_text(encoding="utf-8"))
    if proof.get("schema_version") != "MB_PUBLIC_HISTORICAL_PROOF_V1_COMPLETED_ONLY":
        raise RuntimeError("Sai schema hồ sơ đối chiếu lịch sử công khai")
    validation = proof.get("validation") or {}
    hit_days = int(validation.get("hit_days") or 0)
    total_days = int(validation.get("total_days") or 0)
    rate_pct = int(validation.get("rate_pct") or 0)
    if total_days <= 0 or round(hit_days * 100 / total_days) != rate_pct:
        raise RuntimeError("Tỷ lệ lịch sử không khớp số ngày đối chiếu")
    recent = proof.get("recent_period") or {}
    days = recent.get("days") or []
    if len(days) != int(recent.get("total_days") or 0):
        raise RuntimeError("Thiếu ngày trong bảng đối chiếu gần nhất")
    if sum(bool(item.get("observed")) for item in days) != int(recent.get("hit_days") or 0):
        raise RuntimeError("Số ngày xuất hiện không khớp bảng đối chiếu")
    layers = (proof.get("method_snapshot") or {}).get("layers") or []
    if len(layers) != 7 or [int(item.get("index") or 0) for item in layers] != list(range(1, 8)):
        raise RuntimeError("Hồ sơ mẫu phải có đúng 7 lớp theo thứ tự")
    return proof


def resolve_target(raw: str | None, now: datetime) -> date:
    target = date.fromisoformat(raw) if raw else now.date()
    if target > now.date():
        raise RuntimeError(f"Không được tạo báo cáo cho ngày tương lai {target}")
    if target == now.date() and now.time() < time(19, 0):
        raise RuntimeError(
            f"Kỳ {target} chưa đến mốc hậu kiểm 19:00 Việt Nam; "
            "không tạo hoặc công bố nội dung trước giờ quay"
        )
    return target


def lock_history_through(target: date) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    doc = load_history()
    rows: list[list[str]] = doc["rows"]
    latest = date.fromisoformat(rows[-1][0])
    if target < latest:
        row = next((item for item in rows if item[0] == target.isoformat()), None)
        if row is None:
            raise RuntimeError(f"History không có phiên {target}")
        codes, sources, _ = crosscheck_draw(target)
        if row[1:] != codes:
            raise RuntimeError(f"Nguồn công khai lệch history đã khóa ngày {target}")
        return doc, codes, sources

    target_codes: list[str] | None = None
    target_sources: list[dict[str, Any]] = []
    cursor = latest + timedelta(days=1)
    while cursor <= target:
        codes, sources, _ = crosscheck_draw(cursor)
        rows.append([cursor.isoformat(), *codes])
        if cursor == target:
            target_codes, target_sources = codes, sources
        cursor += timedelta(days=1)

    if target == latest:
        target_codes, target_sources, _ = crosscheck_draw(target)
        if rows[-1][1:] != target_codes:
            raise RuntimeError(f"Nguồn công khai lệch history đã khóa ngày {target}")

    rows.sort(key=lambda row: row[0])
    validate_rows(rows)
    save_history(doc)
    if target_codes is None:
        raise RuntimeError(f"Không khóa được đủ nguồn cho phiên {target}")
    return doc, target_codes, target_sources


def build_report_block(
    target: date,
    codes: list[str],
    recent_rows: list[list[str]],
    history_rows: list[list[str]],
    sources: list[dict[str, Any]],
) -> str:
    _ = target, codes, recent_rows, history_rows, sources
    proof = load_historical_proof()
    validation = proof["validation"]
    recent = proof["recent_period"]
    recent_window = (
        f'{vi_date(date.fromisoformat(recent["period_start"]))}'
        f'–{vi_date(date.fromisoformat(recent["period_end"]))}'
    )
    day_rows: list[str] = []
    for item in recent["days"]:
        observed = [str(value) for value in item.get("observed") or []]
        observed_numbers = {value.split()[0] for value in observed}
        output_html = "".join(
            '<b'
            + (' class="is-observed"' if str(value) in observed_numbers else "")
            + f'>{esc(value)}</b>'
            for value in item.get("outputs") or []
        )
        observed_html = (
            "".join(f'<span>{esc(value)}</span>' for value in observed)
            if observed
            else '<span class="history-miss">Không xuất hiện</span>'
        )
        day_rows.append(
            f'          <div class="history-day-row" role="row"><time datetime="{esc(item["date"])}">'
            f'{vi_date(date.fromisoformat(item["date"]))}</time><div class="history-outputs">{output_html}</div>'
            f'<strong class="history-observed {"has-observed" if observed else ""}">{observed_html}</strong></div>'
        )
    return "\n".join(
        [
            START_MARKER,
            '    <section class="historical-proof-section" id="statistics">',
            '      <div class="wrap historical-proof-shell">',
            '        <div class="historical-proof-summary">',
            f'          <div class="historical-rate"><p>DỮ LIỆU TỪ 2024 ĐẾN NGÀY HÔM NAY</p><strong>{int(validation["rate_pct"])}%</strong><span>{int(validation["hit_days"])}/{int(validation["total_days"])} ngày có ít nhất một đầu ra xuất hiện</span></div>',
            f'          <div class="historical-proof-copy"><p class="eyebrow">THỐNG KÊ THEO NGÀY</p><h2>Có cả ngày xuất hiện và không xuất hiện</h2><p>Bảng dưới hiển thị đủ {int(recent["total_days"])} ngày đã hoàn tất từ {recent_window}; không chỉ chọn các ngày thuận lợi.</p><div><strong>{int(recent["hit_days"])}/{int(recent["total_days"])} ngày</strong><span>trong giai đoạn gần nhất có đầu ra xuất hiện</span></div></div>',
            '        </div>',
            '        <div class="history-days" role="table" aria-label="Đối chiếu đầu ra theo từng ngày đã hoàn tất">',
            '          <div class="history-day-head" role="row"><span>Ngày</span><span>4 đầu ra đã lưu</span><span>Đối chiếu thực tế</span></div>',
            *day_rows,
            '        </div>',
            f'        <p class="historical-disclaimer"><strong>Cách tính:</strong> {esc(validation["definition"])} Tỷ lệ {int(validation["rate_pct"])}% chỉ mô tả cửa sổ lịch sử đã hoàn tất, không phải xác suất hoặc cam kết cho ngày tiếp theo. <a href="/historical-proof.json" target="_blank" rel="noopener">Hồ sơ thống kê</a> · <a href="/source-access.json" target="_blank" rel="noopener">Hồ sơ nguồn</a>.</p>',
            '      </div>',
            '    </section>',
            END_MARKER,
        ]
    )


def replace_marked_block(content: str, replacement: str) -> str:
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )
    updated, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        raise RuntimeError("Không tìm thấy đúng một khối COMPLETED_DRAW_REPORT trong index.html")
    return updated


def replace_required(content: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Không cập nhật được trường {label}: {pattern}")
    return updated


def update_daily_index(content: str, target: date) -> str:
    """Move the public service to the report prepared from the locked draw."""
    report_date = target + timedelta(days=1)
    report_formatted = vi_date(report_date)
    lock_formatted = vi_date(target)
    replacements = (
        (
            r'(<body[^>]*\bdata-report-date=")[^"]+(" data-lock-date=")[^"]+("\s*>)',
            rf'\g<1>{report_formatted}\g<2>{lock_formatted}\g<3>',
            "ngày báo cáo trong body",
        ),
        (
            r'(BÁO CÁO NGÀY )\d{2}/\d{2}/\d{4}',
            rf'\g<1>{report_formatted}',
            "tiêu đề ngày báo cáo",
        ),
        (
            r'(<p class="hero-proof-text">Báo cáo cho ngày hôm nay \()\d{2}/\d{2}/\d{4}(\)\. Dữ liệu khóa đến hết ngày hôm qua \()\d{2}/\d{2}/\d{4}(\)\.</p>)',
            rf'\g<1>{report_formatted}\g<2>{lock_formatted}\g<3>',
            "phạm vi dữ liệu hero",
        ),
        (
            r'(<p class="checkout-scope" id="checkout-scope">01 báo cáo ngày )\d{2}/\d{2}/\d{4}( · dữ liệu khóa đến )\d{2}/\d{2}/\d{4}(\.</p>)',
            rf'\g<1>{report_formatted}\g<2>{lock_formatted}\g<3>',
            "phạm vi thanh toán",
        ),
        (
            r'(<p class="checkout-scope" id="checkout-modal-scope">01 báo cáo ngày )\d{2}/\d{2}/\d{4}( · dữ liệu khóa đến )\d{2}/\d{2}/\d{4}(\.</p>)',
            rf'\g<1>{report_formatted}\g<2>{lock_formatted}\g<3>',
            "phạm vi thanh toán trong hộp thoại",
        ),
    )
    for pattern, replacement, label in replacements:
        content = replace_required(content, pattern, replacement, label)
    return content


def summarize_window(history_rows: list[list[str]], size: int) -> tuple[float, float]:
    selected = history_rows[-size:]
    if len(selected) != size:
        raise RuntimeError(f"Không đủ {size} phiên để lập cửa sổ báo cáo")
    unique_counts: list[int] = []
    repeated_counts: list[int] = []
    for row in selected:
        counts = Counter(row[1:])
        unique_counts.append(len(counts))
        repeated_counts.append(sum(1 for count in counts.values() if count > 1))
    return sum(unique_counts) / size, sum(repeated_counts) / size


def vi_decimal(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def comparison_phrase(value: float, baseline: float, baseline_label: str) -> str:
    difference = value - baseline
    if abs(difference) < 0.005:
        return f"tương đương {baseline_label}"
    direction = "cao hơn" if difference > 0 else "thấp hơn"
    return f"{direction} {baseline_label} là {vi_decimal(abs(difference))}"


def observed_occurrences(values: list[Any]) -> int:
    total = 0
    for raw in values:
        match = re.search(r"×\s*(\d+)\s*$", str(raw))
        total += int(match.group(1)) if match else 1
    return total


def select_featured_sample(proof: dict[str, Any]) -> dict[str, Any]:
    days = (proof.get("recent_period") or {}).get("days") or []
    candidates = [item for item in days if item.get("observed")]
    if not candidates:
        raise RuntimeError("Không có ngày lịch sử đã hoàn tất để làm mẫu 4SO")
    featured = max(
        candidates,
        key=lambda item: (
            observed_occurrences(item.get("observed") or []),
            len(item.get("observed") or []),
            date.fromisoformat(str(item.get("date"))),
        ),
    )
    outputs = [str(value).zfill(2) for value in featured.get("outputs") or []]
    if len(outputs) != 4 or any(not re.fullmatch(r"\d{2}", value) for value in outputs):
        raise RuntimeError("Ngày mẫu 4SO phải có đúng bốn mã hai chữ số")
    return {**featured, "outputs": outputs}


def update_sample(
    content: str,
    target: date,
    codes: list[str],
    sources: list[dict[str, Any]],
    history_rows: list[list[str]],
) -> str:
    formatted = vi_date(target)
    report_formatted = vi_date(target + timedelta(days=1))
    source_count = len(sources)
    source_names = " · ".join(
        SOURCE_LABELS.get(str(source.get("source", "")), str(source.get("source", "")))
        for source in sorted(sources, key=lambda item: str(item.get("source", "")))
    )
    digest = hashlib.sha256("|".join(codes).encode()).hexdigest()[:16]
    history_count = len(history_rows)
    featured = select_featured_sample(load_historical_proof())
    featured_date = date.fromisoformat(str(featured["date"]))
    featured_formatted = vi_date(featured_date)
    featured_lock = vi_date(featured_date - timedelta(days=1))
    featured_outputs = "".join(f"<strong>{esc(value)}</strong>" for value in featured["outputs"])
    featured_observed = featured.get("observed") or []
    featured_occurrences = observed_occurrences(featured_observed)
    featured_aria = f"Bốn mã trong mẫu lịch sử ngày {featured_date.day} tháng {featured_date.month} năm {featured_date.year}"
    featured_caption = (
        f"Hồ sơ lịch sử đã hoàn tất ngày {featured_formatted} có {len(featured_observed)}/4 đầu ra xuất hiện, "
        f"tổng {featured_occurrences} lượt. Mẫu sẽ tự cập nhật khi có ngày lịch sử nổi bật hơn; "
        "không phải 4SO của ngày hôm nay và không dùng để cam kết hiệu quả."
    )
    replacements = (
        (r"(<span data-report-date>).*?(</span>)", rf"\g<1>Báo cáo cho ngày hôm nay: {report_formatted}\g<2>"),
        (r"(<span data-lock-date>).*?(</span>)", rf"\g<1>Dữ liệu khóa đến hết ngày hôm qua: {formatted}\g<2>"),
        (r"(<span data-history-count>).*?(</span>)", rf"\g<1>{history_count} phiên lịch sử\g<2>"),
        (r"(<span data-source-count>).*?(</span>)", rf"\g<1>{source_count} nguồn khớp\g<2>"),
        (r"(<strong data-history-count-value>).*?(</strong>)", rf"\g<1>{history_count} phiên\g<2>"),
        (r"(<span data-source-names>).*?(</span>)", rf"\g<1>{source_names}\g<2>"),
        (r"(<b data-source-count-value>).*?(</b>)", rf"\g<1>{source_count}\g<2>"),
        (r"(<b data-lock-date-value>).*?(</b>)", rf"\g<1>{formatted}\g<2>"),
        (r"(<span data-digest>).*?(</span>)", rf"\g<1>{digest}\g<2>"),
        (r"(<h2 data-featured-sample-date>).*?(</h2>)", rf"\g<1>4SO ngày {featured_formatted}\g<2>"),
        (r"(<span class=\"sample-status\" data-featured-sample-lock>).*?(</span>)", rf"\g<1>KHÓA {featured_lock}\g<2>"),
        (
            r"(<div class=\"fourso-grid\" data-featured-sample-numbers aria-label=\")[^\"]+(\">).*?(</div>)",
            rf"\g<1>{featured_aria}\g<2>{featured_outputs}\g<3>",
        ),
        (r"(<p class=\"sample-caption\" data-featured-sample-caption>).*?(</p>)", rf"\g<1>{featured_caption}\g<2>"),
    )
    for pattern, replacement in replacements:
        content, count = re.subn(pattern, replacement, content, count=1)
        if count != 1:
            raise RuntimeError(f"Không cập nhật được trường báo cáo mẫu: {pattern}")
    return content


def update_audit(target: date, codes: list[str], sources: list[dict[str, Any]], now: datetime) -> bool:
    if AUDIT_FILE.exists():
        audit = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    else:
        audit = {"schema_version": "MB_COMPLETED_DRAW_AUDIT_V1", "draws": {}}
    counts = Counter(codes)
    record = {
        "status": "LOCKED_CROSSCHECKED_PUBLIC",
        "code_count": len(codes),
        "unique_code_count": len(counts),
        "repeated_code_count": sum(1 for value in counts.values() if value > 1),
        "codes_sha256": hashlib.sha256("|".join(codes).encode()).hexdigest(),
        "source_count": len(sources),
        "sources": sorted(str(source.get("source", "")) for source in sources),
    }
    draws = audit.setdefault("draws", {})
    unchanged = (
        audit.get("latest_completed_draw") == target.isoformat()
        and audit.get("policy") == "POST_DRAW_ONLY_NO_PREDICTIONS_NO_STAKES_NO_FINANCIAL_PNL"
        and draws.get(target.isoformat()) == record
    )
    if unchanged:
        return False
    audit["latest_completed_draw"] = target.isoformat()
    audit["updated_at"] = now.isoformat(timespec="seconds")
    audit["policy"] = "POST_DRAW_ONLY_NO_PREDICTIONS_NO_STAKES_NO_FINANCIAL_PNL"
    draws[target.isoformat()] = record
    return write_json_if_changed(AUDIT_FILE, audit)


def update_source_access(
    doc: dict[str, Any], target: date, codes: list[str], sources: list[dict[str, Any]], now: datetime
) -> bool:
    rows = doc["rows"]
    canonical_hash = hashlib.sha256("|".join(codes).encode()).hexdigest()
    merged_sources = [
        {
            "name": str(source.get("source", "")),
            "url": str(source.get("url", "")),
            "codes_sha256": str(source.get("codes_sha256", "")),
        }
        for source in sources
    ]
    existing: dict[str, Any] = {}
    if ACCESS_FILE.exists():
        existing = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
        # The 19:00 audit can add an official source which the 00:05 public
        # mirror checker does not fetch. Preserve only same-day, same-result
        # evidence so a later refresh cannot downgrade a stronger audit.
        if (
            existing.get("history_end") == target.isoformat()
            and existing.get("latest_codes_sha256") == canonical_hash
        ):
            for source in existing.get("sources") or []:
                normalized = {
                    "name": str(source.get("name", "")),
                    "url": str(source.get("url", "")),
                    "codes_sha256": str(source.get("codes_sha256", "")),
                }
                if normalized["name"] and normalized["url"] and normalized["codes_sha256"] == canonical_hash:
                    merged_sources.append(normalized)
    merged_sources = list({
        (source["name"], source["url"], source["codes_sha256"]): source
        for source in merged_sources
    }.values())
    merged_sources.sort(key=lambda item: (item["name"], item["url"]))
    has_official = any("official" in source["name"].lower() for source in merged_sources)
    access_without_time = {
        "schema_version": "MB_SOURCE_ACCESS_V3_POST_DRAW_ONLY",
        "status": "LOCKED_CROSSCHECKED_PUBLIC",
        "selected": "OFFICIAL_PLUS_MULTI_SOURCE_CROSSCHECK" if has_official else "PUBLIC_MULTI_SOURCE_CROSSCHECK",
        "history_start": rows[0][0],
        "history_end": target.isoformat(),
        "history_rows": len(rows),
        "latest_codes_sha256": canonical_hash,
        "source_count": len(merged_sources),
        "sources": merged_sources,
        "policy": "COMPLETED_DRAW_ONLY_FAIL_CLOSED_MINIMUM_TWO_EXACT_SOURCES",
    }
    if existing:
        existing_without_time = dict(existing)
        existing_without_time.pop("locked_at", None)
        if existing_without_time == access_without_time:
            return False
    access = {**access_without_time, "locked_at": now.isoformat(timespec="seconds")}
    return write_json_if_changed(ACCESS_FILE, access)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draw-date", help="Ngày đã công bố, định dạng YYYY-MM-DD")
    parser.add_argument(
        "--stage-only",
        action="store_true",
        help="Chỉ khóa dữ liệu và nhật ký lúc 19:00; chưa đổi ngày hiển thị trên website",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        sample_codes = [f"{value:02d}" for value in range(27)]
        sample_target = date(2026, 8, 12)
        sample_rows = [
            [(sample_target - timedelta(days=offset)).isoformat(), *sample_codes]
            for offset in range(89, -1, -1)
        ]
        sample_sources = [{"source": "a"}, {"source": "b"}]
        block = build_report_block(sample_target, sample_codes, sample_rows[-12:], sample_rows, sample_sources)
        proof = load_historical_proof()
        proof_validation = proof["validation"]
        assert f'{proof_validation["rate_pct"]}%' in block
        assert f'{proof_validation["hit_days"]}/{proof_validation["total_days"]} ngày' in block
        assert "DỮ LIỆU TỪ 2024 ĐẾN NGÀY HÔM NAY" in block
        assert "ĐỐI CHIẾU LỊCH SỬ" not in block
        assert "Số được lưu theo 7 lớp báo cáo" not in block
        assert 'id="methods"' not in block
        assert block.count('class="history-day-row"') == int(proof["recent_period"]["total_days"])
        assert 'class="historical-method-row' not in block
        assert 'href="/historical-proof.json"' in block
        assert 'href="/source-access.json"' in block
        assert "không phải xác suất hoặc cam kết" in block
        daily_index = update_daily_index(INDEX_FILE.read_text(encoding="utf-8"), sample_target)
        assert 'data-report-date="13/08/2026"' in daily_index
        assert 'data-lock-date="12/08/2026"' in daily_index
        year_end_index = update_daily_index(INDEX_FILE.read_text(encoding="utf-8"), date(2026, 12, 31))
        assert 'data-report-date="01/01/2027"' in year_end_index
        assert 'data-lock-date="31/12/2026"' in year_end_index
        assert "Báo cáo cho ngày hôm nay (01/01/2027)" in year_end_index
        assert "Dữ liệu khóa đến hết ngày hôm qua (31/12/2026)" in year_end_index
        sample_page = update_sample(
            SAMPLE_FILE.read_text(encoding="utf-8"), sample_target, sample_codes, sample_sources, sample_rows
        )
        assert "Báo cáo cho ngày hôm nay: 13/08/2026" in sample_page
        assert "Dữ liệu khóa đến hết ngày hôm qua: 12/08/2026" in sample_page
        assert "4SO ngày 11/08/2026" in sample_page
        assert "<strong>05</strong><strong>91</strong><strong>50</strong><strong>19</strong>" in sample_page
        assert "3/4 đầu ra xuất hiện, tổng 4 lượt" in sample_page
        assert "không phải 4SO của ngày hôm nay" in sample_page
        print("COMPLETED_DRAW_REPORT_SELF_TEST_OK")
        return

    now = datetime.now(VN)
    target = resolve_target(args.draw_date, now)
    doc, codes, sources = lock_history_through(target)
    audit_changed = update_audit(target, codes, sources, now)
    if args.stage_only:
        index_changed = False
        sample_changed = False
        access_changed = False
    else:
        recent_rows = [row for row in doc["rows"] if date.fromisoformat(row[0]) <= target][-12:]
        index = INDEX_FILE.read_text(encoding="utf-8")
        updated_index = replace_marked_block(
            index,
            build_report_block(target, codes, recent_rows, doc["rows"], sources),
        )
        updated_index = update_daily_index(updated_index, target)
        index_changed = write_text_if_changed(INDEX_FILE, updated_index)
        sample_changed = write_text_if_changed(
            SAMPLE_FILE,
            update_sample(SAMPLE_FILE.read_text(encoding="utf-8"), target, codes, sources, doc["rows"]),
        )
        access_changed = update_source_access(doc, target, codes, sources, now)
    print(
        json.dumps(
            {
                "draw_date": target.isoformat(),
                "status": "LOCKED_CROSSCHECKED_PUBLIC",
                "source_count": len(sources),
                "stage_only": args.stage_only,
                "index_changed": index_changed,
                "sample_changed": sample_changed,
                "audit_changed": audit_changed,
                "source_access_changed": access_changed,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
