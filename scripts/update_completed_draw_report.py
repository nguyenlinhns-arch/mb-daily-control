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
    formatted = vi_date(target)
    counts = Counter(codes)
    unique_count = len(counts)
    repeated_count = sum(1 for value in counts.values() if value > 1)
    source_count = len(sources)
    source_names = " · ".join(
        SOURCE_LABELS.get(str(source.get("source", "")), str(source.get("source", "")))
        for source in sorted(sources, key=lambda item: str(item.get("source", "")))
    )
    history_start = vi_date(date.fromisoformat(history_rows[0][0]))
    history_count = len(history_rows)
    digest = hashlib.sha256("|".join(codes).encode()).hexdigest()[:16]
    days = "".join(
        f'<span class="hit" title="Đủ 27/27 ngày {vi_date(date.fromisoformat(row[0]))}">{date.fromisoformat(row[0]).day:02d}</span>'
        for row in recent_rows[-12:]
    )
    return "\n".join(
        [
            START_MARKER,
            '    <section class="evidence-section" id="evidence" aria-labelledby="evidence-title">',
            '      <div class="wrap">',
            f'        <header class="section-heading"><div><p class="eyebrow">BẰNG CHỨNG CÓ THỂ KIỂM TRA</p><h2 id="evidence-title">Dữ liệu được khóa đến {formatted}</h2></div><p>Không dùng dữ liệu của kỳ chưa công bố.</p></header>',
            '        <div class="evidence-grid">',
            f'          <article><span>{history_count}</span><strong>phiên lịch sử</strong><small>Từ {history_start} đến {formatted}</small></article>',
            '          <article><span>27/27</span><strong>bản ghi phiên gần nhất</strong><small>Không thiếu vị trí kết quả</small></article>',
            f'          <article><span>{source_count}</span><strong>nguồn trùng khớp</strong><small>Cùng mã kiểm tra dữ liệu</small></article>',
            '          <article><span>0</span><strong>dòng dữ liệu tương lai</strong><small>Kiểm tra chống nhìn trước</small></article>',
            '        </div>',
            '      </div>',
            '    </section>',
            "",
            '    <section class="product-section" id="methods">',
            '      <div class="wrap product-shell">',
            '        <header class="product-head">',
            f'          <div><p class="eyebrow">PHIÊN ĐÃ CÔNG BỐ · {formatted}</p><h2>7 lớp kiểm định của báo cáo gần nhất</h2></div>',
            '          <a href="/mau-bao-cao.html">Xem báo cáo mẫu đầy đủ →</a>',
            '        </header>',
            "",
            '        <section class="proof-strip" aria-label="Mười hai phiên gần nhất đã kiểm tra nguồn">',
            '          <div><small>12 PHIÊN GẦN NHẤT</small><strong>12/12 phiên đủ dữ liệu</strong></div>',
            f'          <div class="proof-days">{days}</div>',
            '          <p><i></i> Đủ dữ liệu <i></i> Chưa đủ</p>',
            '        </section>',
            "",
            f'        <div class="method-list audit-methods" role="table" aria-label="Bảy lớp kiểm định dữ liệu lịch sử ngày {formatted}">',
            f'          <article role="row"><div><span>01</span><strong>Đối chiếu đa nguồn</strong></div><p><b class="metric-chip">{source_count} nguồn khớp</b><small>Chỉ khóa phiên khi tối thiểu hai nguồn cho cùng 27 mã.</small></p></article>',
            '          <article role="row"><div><span>02</span><strong>Độ đầy đủ</strong></div><p><b class="metric-chip">27/27 bản ghi</b><small>Kiểm tra đúng cấu trúc giải trước khi phân tích.</small></p></article>',
            f'          <article role="row"><div><span>03</span><strong>Độ phân tán</strong></div><p><b class="metric-chip">{unique_count} mã khác nhau</b><small>Đếm số giá trị khác nhau trong phiên đã khóa.</small></p></article>',
            f'          <article role="row"><div><span>04</span><strong>Độ lặp trong phiên</strong></div><p><b class="metric-chip">{repeated_count} mã lặp</b><small>Ghi nhận giá trị xuất hiện từ hai lần trở lên.</small></p></article>',
            '          <article role="row"><div><span>05</span><strong>Cửa sổ ngắn</strong></div><p><b class="metric-chip">7 phiên · 189 dòng</b><small>So sánh biến động gần với nền dài hơn.</small></p></article>',
            '          <article role="row"><div><span>06</span><strong>Nền đối chiếu</strong></div><p><b class="metric-chip">30 phiên · 810 dòng</b><small>Giảm việc diễn giải quá mức từ một vài ngày.</small></p></article>',
            '          <article role="row"><div><span>07</span><strong>Chống nhìn trước</strong></div><p><b class="metric-chip">0 dòng tương lai</b><small>Không đưa dữ liệu chưa tồn tại vào phép tính.</small></p></article>',
            '        </div>',
            "",
            f'        <div class="audit-signature"><div><small>MÃ KIỂM TRA PHIÊN</small><strong>{digest}</strong></div><p><strong>Nguồn đối chiếu:</strong> {source_names}. Mã rút gọn từ SHA-256 của 27 bản ghi đã khóa. <a href="/source-access.json" target="_blank" rel="noopener">Mở hồ sơ nguồn →</a></p></div>',
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
            r'(<body data-report-date=")[^"]+(" data-lock-date=")[^"]+("\s*>)',
            rf'\g<1>{report_formatted}\g<2>{lock_formatted}\g<3>',
            "ngày báo cáo trong body",
        ),
        (
            r'(BÁO CÁO DỮ LIỆU AI NGÀY )\d{2}/\d{2}/\d{4}',
            rf'\g<1>{report_formatted}',
            "tiêu đề ngày báo cáo",
        ),
        (
            r'(<p class="hero-proof-text">)Báo cáo ngày \d{2}/\d{2}/\d{4} chỉ dùng dữ liệu đến \d{2}/\d{2}/\d{4}\.',
            rf'\g<1>Báo cáo ngày {report_formatted} chỉ dùng dữ liệu đến {lock_formatted}.',
            "phạm vi dữ liệu hero",
        ),
        (
            r'(<article><small>BÁO CÁO NGÀY HÔM NAY</small><strong>30\.000đ</strong><p><b>Ngày )\d{2}/\d{2}/\d{4}(\.</b> Một báo cáo đầy đủ, dùng dữ liệu đã khóa đến )\d{2}/\d{2}/\d{4}(\.</p>)',
            rf'\g<1>{report_formatted}\g<2>{lock_formatted}\g<3>',
            "gói báo cáo ngày",
        ),
        (
            r'(<p class="checkout-scope" id="checkout-scope">01 báo cáo ngày )\d{2}/\d{2}/\d{4}( · dữ liệu khóa đến )\d{2}/\d{2}/\d{4}(\.</p>)',
            rf'\g<1>{report_formatted}\g<2>{lock_formatted}\g<3>',
            "phạm vi thanh toán",
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


def update_sample(
    content: str,
    target: date,
    codes: list[str],
    sources: list[dict[str, Any]],
    history_rows: list[list[str]],
) -> str:
    formatted = vi_date(target)
    report_formatted = vi_date(target + timedelta(days=1))
    counts = Counter(codes)
    source_count = len(sources)
    source_names = " · ".join(
        SOURCE_LABELS.get(str(source.get("source", "")), str(source.get("source", "")))
        for source in sorted(sources, key=lambda item: str(item.get("source", "")))
    )
    unique_count = len(counts)
    repeated_count = sum(1 for value in counts.values() if value > 1)
    digest = hashlib.sha256("|".join(codes).encode()).hexdigest()[:16]
    history_count = len(history_rows)
    history_start = vi_date(date.fromisoformat(history_rows[0][0]))
    window_values = {size: summarize_window(history_rows, size) for size in (7, 30, 90)}
    unique_comparison_7 = comparison_phrase(unique_count, window_values[7][0], "trung bình 7 phiên")
    unique_comparison_30 = comparison_phrase(unique_count, window_values[30][0], "trung bình 30 phiên")
    repeat_comparison_30 = comparison_phrase(window_values[7][1], window_values[30][1], "nền 30 phiên")
    repeat_comparison_90 = comparison_phrase(window_values[7][1], window_values[90][1], "nền 90 phiên")
    replacements = (
        (r"(<span data-report-date>).*?(</span>)", rf"\g<1>Ngày báo cáo mẫu: {report_formatted}\g<2>"),
        (r"(<span data-lock-date>).*?(</span>)", rf"\g<1>Khóa nguồn: {formatted}\g<2>"),
        (r"(<span data-history-count>).*?(</span>)", rf"\g<1>{history_count} phiên lịch sử\g<2>"),
        (r"(<span data-source-count>).*?(</span>)", rf"\g<1>{source_count} nguồn trùng khớp\g<2>"),
        (r"(<td data-report-date-value>).*?(</td>)", rf"\g<1>{report_formatted}\g<2>"),
        (r"(<td data-history-range>).*?(</td>)", rf"\g<1>Từ {history_start} đến hết {formatted}\g<2>"),
        (r"(<strong data-history-count-value>).*?(</strong>)", rf"\g<1>{history_count} phiên\g<2>"),
        (r"(<p class=\"sample-caption\" data-report-scope>).*?(</p>)", rf"\g<1>“Báo cáo ngày hôm nay” là báo cáo được lập trong ngày {report_formatted} từ dữ liệu đã tồn tại đến hết ngày {formatted}.\g<2>"),
        (r"(<span data-source-names>).*?(</span>)", rf"\g<1>{source_names}\g<2>"),
        (r"(<strong data-source-count-value>).*?(</strong>)", rf"\g<1>{source_count}\g<2>"),
        (r"(<strong data-lock-date-value>).*?(</strong>)", rf"\g<1>{formatted}\g<2>"),
        (r"(<strong data-digest>).*?(</strong>)", rf"\g<1>{digest}\g<2>"),
        (r"(<span class=\"status-pill status-neutral\" data-locked-session>).*?(</span>)", rf"\g<1>PHIÊN {formatted}\g<2>"),
        (r"(<span class=\"row-chip\" data-source-count-chip>).*?(</span>)", rf"\g<1>{source_count} nguồn\g<2>"),
        (r"(<span class=\"row-chip\" data-unique-count-chip>).*?(</span>)", rf"\g<1>{unique_count} mã\g<2>"),
        (r"(<span class=\"row-chip\" data-repeated-count-chip>).*?(</span>)", rf"\g<1>{repeated_count} mã\g<2>"),
        (r"(<strong data-window-7-unique>).*?(</strong>)", rf"\g<1>{vi_decimal(window_values[7][0])}\g<2>"),
        (r"(<strong data-window-7-repeat>).*?(</strong>)", rf"\g<1>{vi_decimal(window_values[7][1])}\g<2>"),
        (r"(<strong data-window-30-unique>).*?(</strong>)", rf"\g<1>{vi_decimal(window_values[30][0])}\g<2>"),
        (r"(<strong data-window-30-repeat>).*?(</strong>)", rf"\g<1>{vi_decimal(window_values[30][1])}\g<2>"),
        (r"(<strong data-window-90-unique>).*?(</strong>)", rf"\g<1>{vi_decimal(window_values[90][0])}\g<2>"),
        (r"(<strong data-window-90-repeat>).*?(</strong>)", rf"\g<1>{vi_decimal(window_values[90][1])}\g<2>"),
        (r"(<h2 data-conclusion-date>).*?(</h2>)", rf"\g<1>Kết luận ngày {report_formatted}\g<2>"),
        (r"(<p data-finding-verified>).*?(</p>)", rf"\g<1>Phiên {target.strftime('%d/%m')} có {unique_count} giá trị khác nhau và {repeated_count} giá trị lặp; đủ 27/27 bản ghi từ {source_count} nguồn trùng khớp.\g<2>"),
        (r"(<p data-finding-observation>).*?(</p>)", rf"\g<1>Mức đa dạng của phiên gần nhất {unique_comparison_7} và {unique_comparison_30}. Mức lặp của cửa sổ 7 phiên {repeat_comparison_30} và {repeat_comparison_90}.\g<2>"),
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
    access_without_time = {
        "schema_version": "MB_SOURCE_ACCESS_V3_POST_DRAW_ONLY",
        "status": "LOCKED_CROSSCHECKED_PUBLIC",
        "selected": "PUBLIC_MULTI_SOURCE_CROSSCHECK",
        "history_start": rows[0][0],
        "history_end": target.isoformat(),
        "history_rows": len(rows),
        "latest_codes_sha256": hashlib.sha256("|".join(codes).encode()).hexdigest(),
        "source_count": len(sources),
        "sources": [
            {
                "name": str(source.get("source", "")),
                "url": str(source.get("url", "")),
                "codes_sha256": str(source.get("codes_sha256", "")),
            }
            for source in sorted(sources, key=lambda item: str(item.get("source", "")))
        ],
        "policy": "COMPLETED_DRAW_ONLY_FAIL_CLOSED_MINIMUM_TWO_EXACT_SOURCES",
    }
    if ACCESS_FILE.exists():
        existing = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
        existing.pop("locked_at", None)
        if existing == access_without_time:
            return False
    access = {**access_without_time, "locked_at": now.isoformat(timespec="seconds")}
    return write_json_if_changed(ACCESS_FILE, access)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draw-date", help="Ngày đã công bố, định dạng YYYY-MM-DD")
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
        assert "7 lớp kiểm định của báo cáo gần nhất" in block
        assert block.count('role="row"') == 7
        assert "2 nguồn khớp" in block
        assert "27/27 bản ghi" in block
        assert "kỳ tiếp theo" not in block.lower()
        daily_index = update_daily_index(INDEX_FILE.read_text(encoding="utf-8"), sample_target)
        assert 'data-report-date="13/08/2026"' in daily_index
        assert 'data-lock-date="12/08/2026"' in daily_index
        sample_page = update_sample(
            SAMPLE_FILE.read_text(encoding="utf-8"), sample_target, sample_codes, sample_sources, sample_rows
        )
        assert "Ngày báo cáo mẫu: 13/08/2026" in sample_page
        assert "Kết luận ngày 13/08/2026" in sample_page
        print("COMPLETED_DRAW_REPORT_SELF_TEST_OK")
        return

    now = datetime.now(VN)
    target = resolve_target(args.draw_date, now)
    doc, codes, sources = lock_history_through(target)
    recent_rows = [row for row in doc["rows"] if date.fromisoformat(row[0]) <= target][-12:]
    index = INDEX_FILE.read_text(encoding="utf-8")
    updated_index = replace_marked_block(index, build_report_block(target, codes, recent_rows, doc["rows"], sources))
    updated_index = update_daily_index(updated_index, target)
    index_changed = write_text_if_changed(INDEX_FILE, updated_index)
    sample_changed = write_text_if_changed(
        SAMPLE_FILE,
        update_sample(SAMPLE_FILE.read_text(encoding="utf-8"), target, codes, sources, doc["rows"]),
    )
    audit_changed = update_audit(target, codes, sources, now)
    access_changed = update_source_access(doc, target, codes, sources, now)
    print(
        json.dumps(
            {
                "draw_date": target.isoformat(),
                "status": "LOCKED_CROSSCHECKED_PUBLIC",
                "source_count": len(sources),
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
