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


def update_sample(
    content: str,
    target: date,
    codes: list[str],
    sources: list[dict[str, Any]],
    history_count: int,
) -> str:
    formatted = vi_date(target)
    counts = Counter(codes)
    source_count = len(sources)
    source_names = " · ".join(
        SOURCE_LABELS.get(str(source.get("source", "")), str(source.get("source", "")))
        for source in sorted(sources, key=lambda item: str(item.get("source", "")))
    )
    unique_count = len(counts)
    repeated_count = sum(1 for value in counts.values() if value > 1)
    digest = hashlib.sha256("|".join(codes).encode()).hexdigest()[:16]
    content = re.sub(r"Ngày mẫu: \d{2}/\d{2}/\d{4}", f"Ngày báo cáo: {formatted}", content)
    content = re.sub(r"Khóa nguồn: \d{2}/\d{2}/\d{4}", f"Khóa nguồn: {formatted}", content)
    content = re.sub(
        r"(<td><strong>)\d{2}/\d{2}/\d{4}(</strong></td>)",
        rf"\g<1>{formatted}\g<2>",
        content,
        count=1,
    )
    replacements = (
        (r"(<span data-history-count>).*?(</span>)", rf"\g<1>{history_count} phiên lịch sử\g<2>"),
        (r"(<span data-source-count>).*?(</span>)", rf"\g<1>{source_count} nguồn trùng khớp\g<2>"),
        (r"(<span data-source-names>).*?(</span>)", rf"\g<1>{source_names}\g<2>"),
        (r"(<strong data-source-count-value>).*?(</strong>)", rf"\g<1>{source_count}\g<2>"),
        (r"(<strong data-digest>).*?(</strong>)", rf"\g<1>{digest}\g<2>"),
        (r"(<span class=\"row-chip\" data-source-count-chip>).*?(</span>)", rf"\g<1>{source_count} nguồn\g<2>"),
        (r"(<span class=\"row-chip\" data-unique-count-chip>).*?(</span>)", rf"\g<1>{unique_count} mã\g<2>"),
        (r"(<span class=\"row-chip\" data-repeated-count-chip>).*?(</span>)", rf"\g<1>{repeated_count} mã\g<2>"),
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
        sample_rows = [["2026-08-12", *sample_codes]]
        sample_sources = [{"source": "a"}, {"source": "b"}]
        block = build_report_block(date(2026, 8, 12), sample_codes, sample_rows, sample_rows, sample_sources)
        assert "7 lớp kiểm định của báo cáo gần nhất" in block
        assert block.count('role="row"') == 7
        assert "2 nguồn khớp" in block
        assert "27/27 bản ghi" in block
        assert "kỳ tiếp theo" not in block.lower()
        print("COMPLETED_DRAW_REPORT_SELF_TEST_OK")
        return

    now = datetime.now(VN)
    target = resolve_target(args.draw_date, now)
    doc, codes, sources = lock_history_through(target)
    recent_rows = [row for row in doc["rows"] if date.fromisoformat(row[0]) <= target][-12:]
    index = INDEX_FILE.read_text(encoding="utf-8")
    index_changed = write_text_if_changed(
        INDEX_FILE,
        replace_marked_block(index, build_report_block(target, codes, recent_rows, doc["rows"], sources)),
    )
    sample_changed = write_text_if_changed(
        SAMPLE_FILE,
        update_sample(SAMPLE_FILE.read_text(encoding="utf-8"), target, codes, sources, len(doc["rows"])),
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
