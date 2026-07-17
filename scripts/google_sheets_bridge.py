#!/usr/bin/env python3
"""Authenticated Google Sheets snapshot/apply bridge for the V32 transaction.

The bridge intentionally has no public-web fallback.  A missing credential,
missing tab, conflicting row, or failed readback exits non-zero before Pages is
updated.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from openpyxl import Workbook


SOURCE_SHEET_ID = "1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w"
SOURCE_HISTORY_TAB = "MB_History_27"
SOURCE_HISTORY_MIRROR_TAB = "MB_History_27_IMPORT"
SOURCE_PLAN_TAB = "V32_Daily_Plan"
SOURCE_SETTLEMENT_TAB = "V32_Daily_Settlement"
SOURCE_LOG_TAB = "V32_Automation_Log"
PNL_LOG_TAB = "Nhật ký tự động V32"
PNL_CONFIG_TAB = "Tự động hóa V32"
PEOPLE_KEYS = ("p1", "p2", "p3", "p4", "p5")
SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)


class BridgeError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical(value)).hexdigest()


def load_credentials():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise BridgeError("Thiếu secret GOOGLE_SERVICE_ACCOUNT_JSON")
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BridgeError("GOOGLE_SERVICE_ACCOUNT_JSON không phải JSON hợp lệ") from exc
    required = {"client_email", "private_key", "token_uri"}
    missing = sorted(required - set(info))
    if missing:
        raise BridgeError(f"Service account JSON thiếu: {', '.join(missing)}")
    return service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )


def sheets_service():
    return build("sheets", "v4", credentials=load_credentials(), cache_discovery=False)


def get_values(service, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueRenderOption="UNFORMATTED_VALUE",
            dateTimeRenderOption="SERIAL_NUMBER",
        )
        .execute()
    )
    return result.get("values", [])


def metadata_titles(service, spreadsheet_id: str) -> set[str]:
    result = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title")
        .execute()
    )
    return {item["properties"]["title"] for item in result.get("sheets", [])}


def quote_tab(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


def snapshot(args: argparse.Namespace) -> None:
    service = sheets_service()
    pnl_id = args.pnl_sheet_id or os.environ.get("MB_PNL_SHEET_ID", "").strip()
    if not pnl_id:
        raise BridgeError("Thiếu secret MB_PNL_SHEET_ID")
    source_titles = metadata_titles(service, args.source_sheet_id)
    pnl_titles = metadata_titles(service, pnl_id)
    required_source = {
        SOURCE_HISTORY_TAB, SOURCE_HISTORY_MIRROR_TAB,
        SOURCE_PLAN_TAB, SOURCE_SETTLEMENT_TAB, SOURCE_LOG_TAB,
    }
    missing_source = sorted(required_source - source_titles)
    required_pnl = {PNL_LOG_TAB, PNL_CONFIG_TAB}
    missing_pnl = sorted(required_pnl - pnl_titles)
    if missing_source or missing_pnl:
        raise BridgeError(
            f"Thiếu tab nguồn={missing_source}; thiếu tab P/L hệ thống={missing_pnl}"
        )

    history = get_values(
        service, args.source_sheet_id, f"{quote_tab(SOURCE_HISTORY_TAB)}!A1:AB3000"
    )
    mirror = get_values(
        service, args.source_sheet_id,
        f"{quote_tab(SOURCE_HISTORY_MIRROR_TAB)}!A1:AB3000",
    )
    if len(history) < 2:
        raise BridgeError("MB_History_27 không có dữ liệu")
    if canonical(history) != canonical(mirror):
        raise BridgeError("Hai tab lịch sử nguồn không khớp tuyệt đối; dừng fail-closed")
    wb = Workbook()
    ws = wb.active
    ws.title = SOURCE_HISTORY_TAB
    for row in history:
        ws.append(list(row[:28]))
    output_xlsx = Path(args.output_xlsx)
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_xlsx)

    config = get_values(service, pnl_id, f"{quote_tab(PNL_CONFIG_TAB)}!A7:B11")
    bindings = {}
    for row in config:
        if len(row) >= 2:
            bindings[str(row[0]).strip()] = str(row[1]).strip()
    if set(bindings) != set(PEOPLE_KEYS) or len(set(bindings.values())) != 5:
        raise BridgeError("Cấu hình P/L phải ánh xạ đúng p1..p5 tới 5 tab duy nhất")
    missing_tabs = sorted(set(bindings.values()) - pnl_titles)
    if missing_tabs:
        raise BridgeError(f"Có {len(missing_tabs)} tab cá nhân cấu hình nhưng không tồn tại")
    settlement_date = args.settlement_date
    people = []
    for key in PEOPLE_KEYS:
        tab = bindings[key]
        dates = get_values(service, pnl_id, f"{quote_tab(tab)}!A6:A1005")
        row_numbers = [
            offset for offset, row in enumerate(dates, start=6)
            if row and parse_date(row[0]) == settlement_date
        ]
        sparse_rows: list[list[Any]] = []
        if row_numbers:
            sparse_rows = [[] for _ in range(max(row_numbers))]
            for row_number in row_numbers:
                values = get_values(
                    service, pnl_id,
                    f"{quote_tab(tab)}!A{row_number}:H{row_number}",
                )
                if values:
                    sparse_rows[row_number - 1] = values[0]
        people.append({"name": key, "sheet_name": tab, "rows": sparse_rows})
    private = {
        "schema_version": "MB_V32_PNL_SNAPSHOT_V1",
        "private": True,
        "source_sheet_id": args.source_sheet_id,
        "pnl_sheet_id": pnl_id,
        "source_crosscheck": "MB_History_27_EQ_MB_History_27_IMPORT",
        "people": people,
    }
    output_json = Path(args.output_pnl_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(private, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"GOOGLE_SHEETS_SNAPSHOT_OK rows={len(history) - 1} people={len(people)}")


def parse_date(value: Any) -> str | None:
    if isinstance(value, (int, float)):
        origin = datetime(1899, 12, 30)
        return (origin + timedelta(days=float(value))).date().isoformat()
    text = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def pad(row: list[Any], width: int) -> list[Any]:
    return list(row) + [None] * max(0, width - len(row))


def find_operation_row(rows: list[list[Any]], operation_id: str) -> int | None:
    for index, row in enumerate(rows, start=1):
        if operation_id in {str(value) for value in row}:
            return index
    return None


def find_date_row(rows: list[list[Any]], target_date: str) -> int | None:
    for index, row in enumerate(rows, start=1):
        if row and parse_date(row[0]) == target_date:
            return index
    return None


def json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_row(operation: dict) -> tuple[str, list[Any]]:
    record = operation["record"]
    common = [
        record["date"], record["status"], record["method"],
        ", ".join(record["codes"]), json_cell(record["points_by_code"]),
        record["total_points"], record["capital_vnd"],
    ]
    if operation["kind"] == "UPSERT_SOURCE_PLAN":
        return SOURCE_PLAN_TAB, common + [
            record["source_date"], record["input_hash"], operation["operation_id"],
            operation["row_hash"], record["created_at"],
        ]
    if operation["kind"] == "UPSERT_SOURCE_SETTLEMENT":
        return SOURCE_SETTLEMENT_TAB, common + [
            record["payout_vnd"], record["pnl_vnd"], record["hit_units"],
            record["source_date"], record["input_hash"], operation["operation_id"],
            operation["row_hash"], record["created_at"],
        ]
    raise BridgeError(f"Loại source operation không hỗ trợ: {operation['kind']}")


def update_range(service, spreadsheet_id: str, range_name: str, values: list[list[Any]]) -> None:
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body={"majorDimension": "ROWS", "values": values},
        )
        .execute()
    )


def append_row(service, spreadsheet_id: str, tab: str, row: list[Any]) -> None:
    (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=f"{quote_tab(tab)}!A:Z",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"majorDimension": "ROWS", "values": [row]},
        )
        .execute()
    )


def verify_source_operation(service, spreadsheet_id: str, tab: str, operation: dict) -> None:
    rows = get_values(service, spreadsheet_id, f"{quote_tab(tab)}!A1:O3000")
    row_index = find_operation_row(rows, operation["operation_id"])
    if row_index is None:
        raise BridgeError(f"Không đọc lại được operation {operation['operation_id']}")
    row = rows[row_index - 1]
    if operation["row_hash"] not in {str(value) for value in row}:
        raise BridgeError(f"Readback sai row_hash tại {tab}!{row_index}")


def apply_source_operation(service, spreadsheet_id: str, operation: dict) -> None:
    tab, row = source_row(operation)
    rows = get_values(service, spreadsheet_id, f"{quote_tab(tab)}!A1:O3000")
    existing_op = find_operation_row(rows, operation["operation_id"])
    existing_date = find_date_row(rows[1:], operation["record"]["date"])
    if existing_date is not None:
        existing_date += 1
    if existing_op is None and existing_date is not None:
        raise BridgeError(
            f"Xung đột ngày {operation['record']['date']} tại {tab}!{existing_date}"
        )
    if existing_op is None:
        append_row(service, spreadsheet_id, tab, row)
    verify_source_operation(service, spreadsheet_id, tab, operation)


def apply_personal_operation(service, pnl_id: str, operation: dict) -> None:
    tab = operation["sheet_name"]
    row_number = int(operation["row"])
    range_name = f"{quote_tab(tab)}!A{row_number}:H{row_number}"
    rows = get_values(service, pnl_id, range_name)
    if not rows:
        raise BridgeError(f"Dòng cá nhân biến mất: op={operation['operation_id'][:12]}")
    row = pad(rows[0], 8)
    if digest(row[:4]) != operation["expected_a_to_d_hash"]:
        raise BridgeError(f"Input cá nhân đã thay đổi: op={operation['operation_id'][:12]}")
    current = row[4]
    if current not in (None, ""):
        try:
            current = int(float(current))
        except (TypeError, ValueError):
            raise BridgeError(f"P/L hiện có không phải số: op={operation['operation_id'][:12]}")
        if current != operation["pnl_vnd"]:
            raise BridgeError(f"P/L hiện có xung đột: op={operation['operation_id'][:12]}")
    note = str(row[7] or "").strip()
    marker = f"[V32:{operation['operation_id'][:12]}]"
    if marker not in note:
        note = (note + (" | " if note else "") + marker + " " + operation["note"])
    update_range(
        service, pnl_id, f"{quote_tab(tab)}!E{row_number}:E{row_number}",
        [[operation["pnl_vnd"]]],
    )
    update_range(
        service, pnl_id, f"{quote_tab(tab)}!H{row_number}:H{row_number}", [[note]]
    )
    check = pad(get_values(service, pnl_id, range_name)[0], 8)
    if int(float(check[4])) != operation["pnl_vnd"] or marker not in str(check[7]):
        raise BridgeError(f"Readback cá nhân thất bại: op={operation['operation_id'][:12]}")


def append_log(
    service, spreadsheet_id: str, tab: str, payload: dict,
    operation: dict, status: str,
) -> None:
    rows = get_values(service, spreadsheet_id, f"{quote_tab(tab)}!A1:H5000")
    existing = find_operation_row(rows, operation["operation_id"])
    expected = [
        payload["target_date"], payload["input_hash"], payload["payload_hash"],
        operation["operation_id"], operation["kind"], status,
    ]
    if existing is not None:
        row = pad(rows[existing - 1], 8)
        if [str(value) for value in row[1:7]] != [str(value) for value in expected]:
            raise BridgeError(f"Log operation hiện có xung đột: {operation['operation_id'][:12]}")
        return
    append_row(service, spreadsheet_id, tab, [
        datetime.now().astimezone().isoformat(timespec="seconds"),
        payload["target_date"], payload["input_hash"], payload["payload_hash"],
        operation["operation_id"], operation["kind"], status,
        operation.get("sheet_name", "source"),
    ])
    verified = get_values(service, spreadsheet_id, f"{quote_tab(tab)}!A1:H5000")
    verified_row = find_operation_row(verified, operation["operation_id"])
    if verified_row is None:
        raise BridgeError(f"Không đọc lại được log operation {operation['operation_id'][:12]}")
    row = pad(verified[verified_row - 1], 8)
    if [str(value) for value in row[1:7]] != [str(value) for value in expected]:
        raise BridgeError(f"Readback log sai nội dung: {operation['operation_id'][:12]}")


def apply(args: argparse.Namespace) -> None:
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    receipt_path = Path(args.receipt)
    if payload.get("noop"):
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps({
                "status": "NOOP", "payload_hash": payload["payload_hash"],
                "target_date": payload["target_date"],
                "input_hash": payload["input_hash"], "operation_ids": [],
            }, indent=2) + "\n", encoding="utf-8"
        )
        print("GOOGLE_SHEETS_APPLY_NOOP")
        return
    if payload.get("blocked_personal_rows"):
        raise BridgeError(
            f"Có {len(payload['blocked_personal_rows'])} dòng P/L cá nhân "
            "mơ hồ/xung đột; chi tiết chỉ nằm trong snapshot private"
        )
    if digest(payload.get("operations", [])) != payload.get("payload_hash"):
        raise BridgeError("Payload hash không khớp")
    pnl_id = args.pnl_sheet_id or os.environ.get("MB_PNL_SHEET_ID", "").strip()
    if not pnl_id:
        raise BridgeError("Thiếu secret MB_PNL_SHEET_ID")
    service = sheets_service()
    operation_ids = []
    for operation in payload["operations"]:
        kind = operation["kind"]
        if kind.startswith("UPSERT_SOURCE_"):
            apply_source_operation(service, args.source_sheet_id, operation)
            append_log(
                service, args.source_sheet_id, SOURCE_LOG_TAB,
                payload, operation, "APPLIED_READBACK_VERIFIED",
            )
        elif kind == "UPDATE_PERSONAL_PNL_IF_BLANK":
            apply_personal_operation(service, pnl_id, operation)
            append_log(
                service, pnl_id, PNL_LOG_TAB,
                payload, operation, "APPLIED_READBACK_VERIFIED",
            )
        elif kind == "LOG_PERSONAL_NO_ORDER":
            append_log(
                service, pnl_id, PNL_LOG_TAB,
                payload, operation, "NO_ORDER_ROW_PNL_NOT_INFERRED",
            )
        else:
            raise BridgeError(f"Operation không hỗ trợ: {kind}")
        operation_ids.append(operation["operation_id"])
    receipt = {
        "schema_version": "MB_V32_SHEETS_RECEIPT_V1",
        "status": "APPLIED_READBACK_VERIFIED",
        "target_date": payload["target_date"],
        "input_hash": payload["input_hash"],
        "payload_hash": payload["payload_hash"],
        "operation_ids": operation_ids,
        "verified_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"GOOGLE_SHEETS_APPLIED_AND_VERIFIED operations={len(operation_ids)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--source-sheet-id", default=SOURCE_SHEET_ID)
    snap.add_argument("--pnl-sheet-id")
    snap.add_argument("--settlement-date", required=True)
    snap.add_argument("--output-xlsx", required=True)
    snap.add_argument("--output-pnl-json", required=True)
    snap.set_defaults(func=snapshot)
    writer = sub.add_parser("apply")
    writer.add_argument("--source-sheet-id", default=SOURCE_SHEET_ID)
    writer.add_argument("--pnl-sheet-id")
    writer.add_argument("--payload", required=True)
    writer.add_argument("--receipt", required=True)
    writer.set_defaults(func=apply)
    args = parser.parse_args()
    try:
        args.func(args)
    except BridgeError as exc:
        print(f"GOOGLE_SHEETS_BRIDGE_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
