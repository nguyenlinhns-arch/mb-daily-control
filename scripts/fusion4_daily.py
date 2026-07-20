#!/usr/bin/env python3
"""Fail-closed daily settlement, Fusion4 planning, Sheets sync and publishing."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

import v32_daily as common


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEMPLATE = ROOT / "templates" / "fusion4-dashboard.html"
STATE_FILE = DATA / "fusion4-state.json"
PLAN_DIR = DATA / "fusion4-plans"
SETTLEMENT_DIR = DATA / "fusion4-settlements"
TX_DIR = DATA / "fusion4-transactions"
ENGINE_SCRIPT = ROOT / "scripts" / "fusion4_engine.py"
CONFIG_ID = "MB_FUSION4_180_PROD_V1_20260719"
METHOD = "MB FUSION4–180"
PIPELINE_VERSION = "MB_FUSION4_180_DAILY_TXN_V1"
VN = timezone(timedelta(hours=7))
WEEKDAYS = (
    "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm",
    "Thứ Sáu", "Thứ Bảy", "Chủ Nhật",
)


class PipelineError(RuntimeError):
    pass


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Không đọc được JSON bắt buộc: {path}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical(value)).hexdigest()


def load_plan(day: date) -> dict:
    plan = read_json(PLAN_DIR / f"{day.isoformat()}.json")
    if plan.get("target_date") != day.isoformat():
        raise PipelineError("Ngày trong lệnh FUSION4 không khớp tên file")
    codes = [common.code2(value) for value in plan.get("codes", [])]
    points = {common.code2(key): int(value)
              for key, value in plan.get("points_by_code", {}).items()}
    if codes != list(points) or len(codes) != 4 or len(set(codes)) != 4:
        raise PipelineError("Lệnh FUSION4 phải có đúng bốn mã có thứ hạng")
    if [points[code] for code in codes] != [50, 50, 50, 30]:
        raise PipelineError("Lệnh FUSION4 phải đúng 50-50-50-30")
    if plan.get("total_points") != 180:
        raise PipelineError("Lệnh FUSION4 phải đúng 180 điểm")
    if plan.get("total_capital_vnd") != 4_140_000:
        raise PipelineError("Vốn FUSION4 không đúng 180×23.000")
    if plan.get("outcome_known_at_selection") is not False:
        raise PipelineError("Lệnh FUSION4 thiếu khóa chống nhìn trước")
    plan["codes"] = codes
    plan["points_by_code"] = points
    return plan


def settle(plan: dict, draw: list[str]) -> dict:
    value = common.settle(plan, draw)
    value.update({
        "method": METHOD,
        "config_id": CONFIG_ID,
        "ledger_scope": "METHOD_THEORETICAL_SEPARATE_FROM_PERSONAL_ACTUAL",
    })
    return value


def empty_actual_period() -> dict:
    return {
        "sessions": 0,
        "wins": 0,
        "losses": 0,
        "current_winning_streak": 0,
        "current_losing_streak": 0,
        "longest_winning_streak": 0,
        "longest_losing_streak": 0,
        "net_profit_vnd": 0,
    }


def update_actual_period(period: dict, settlement: dict) -> dict:
    value = dict(period)
    pnl = int(settlement["pnl_vnd"])
    won = pnl > 0
    lost = pnl < 0
    value["sessions"] = int(value.get("sessions", 0)) + 1
    value["wins"] = int(value.get("wins", 0)) + int(won)
    value["losses"] = int(value.get("losses", 0)) + int(lost)
    value["current_winning_streak"] = (
        int(value.get("current_winning_streak", 0)) + 1 if won else 0
    )
    value["current_losing_streak"] = (
        int(value.get("current_losing_streak", 0)) + 1 if lost else 0
    )
    value["longest_winning_streak"] = max(
        int(value.get("longest_winning_streak", 0)),
        value["current_winning_streak"],
    )
    value["longest_losing_streak"] = max(
        int(value.get("longest_losing_streak", 0)),
        value["current_losing_streak"],
    )
    value["net_profit_vnd"] = int(value.get("net_profit_vnd", 0)) + pnl
    return value


def advance_state(state: dict, settlement: dict) -> dict:
    value = json.loads(json.dumps(state))
    settled_day = date.fromisoformat(settlement["date"])
    month_id = settled_day.strftime("%Y-%m")
    year_id = str(settled_day.year)
    if value.get("current_month_id") != month_id:
        value["current_month_id"] = month_id
        value["current_month"] = common.empty_period()
    if value.get("current_year_id") != year_id:
        value["current_year_id"] = year_id
        value["current_year"] = common.empty_period()
    for key in ("current_month", "current_year", "full"):
        before = value[key]
        updated = common.update_period(before, settlement)
        current_streak = (
            int(before.get("current_losing_streak", 0)) + 1
            if settlement["pnl_vnd"] < 0 else 0
        )
        updated["current_losing_streak"] = current_streak
        updated["longest_losing_streak"] = max(
            int(before.get("longest_losing_streak", 0)), current_streak
        )
        value[key] = updated
    value["settled_through"] = settlement["date"]
    value["last_settlement_hash"] = digest(settlement)
    return value


def advance_personal_actual(state: dict, day: date, operations: list[dict]) -> dict:
    """Advance Linh's actual ledger summary, never the method replay result."""
    value = json.loads(json.dumps(state))
    actual = value["actual"]
    previous_checked = date.fromisoformat(actual["settled_through"])
    if day <= previous_checked:
        raise PipelineError("Sổ thực tế Linh đã đối chiếu đến ngày bằng hoặc mới hơn")
    month_id = day.strftime("%Y-%m")
    if actual.get("current_month_id") != month_id:
        actual["current_month_id"] = month_id
        actual["current_month"] = empty_actual_period()
    pnl_rows = [
        int(operation["pnl_vnd"])
        for operation in operations
        if operation.get("kind") in {
            "UPDATE_PERSONAL_PNL_IF_BLANK",
            "RECORD_PERSONAL_MANUAL_ADJUSTMENT",
        }
        and operation.get("name") == "p1"
    ]
    if pnl_rows:
        daily = {"pnl_vnd": sum(pnl_rows)}
        actual["current_month"] = update_actual_period(
            actual["current_month"], daily
        )
        actual["total"] = update_actual_period(actual["total"], daily)
    actual["settled_through"] = day.isoformat()
    return value


def ledger_total(entry: dict) -> int:
    if "ledger_total_pnl_vnd" in entry:
        return int(entry["ledger_total_pnl_vnd"])
    total = 0
    for row in entry.get("rows", []):
        padded = list(row) + [None] * max(0, 5 - len(row))
        if padded[4] not in (None, ""):
            total += int(float(padded[4]))
    return total


def reconcile_group_actual(state: dict, day: date, snapshot: dict,
                           operations: list[dict]) -> dict:
    """Reconcile the privacy-safe aggregate of all five actual ledgers."""
    value = json.loads(json.dumps(state))
    people = snapshot.get("people", [])
    names = [entry.get("name") for entry in people]
    if len(names) != 5 or len(set(names)) != 5 or set(names) != set(common.PEOPLE):
        raise PipelineError("Không đủ đúng 5 sổ cá nhân để tính lãi/lỗ tổng")
    total = sum(ledger_total(entry) for entry in people)
    by_name = {entry["name"]: entry for entry in people}
    for operation in operations:
        if operation.get("kind") != "UPDATE_PERSONAL_PNL_IF_BLANK":
            continue
        if "pnl_was_blank" in operation:
            was_blank = operation["pnl_was_blank"] is True
        else:
            entry = by_name[operation["name"]]
            row_number = int(operation["row"])
            rows = entry.get("rows", [])
            row = rows[row_number - 1] if row_number <= len(rows) else []
            padded = list(row) + [None] * max(0, 5 - len(row))
            was_blank = padded[4] in (None, "")
        if was_blank:
            total += int(operation["pnl_vnd"])
    value["group_actual_pnl"] = {
        "source": "AGGREGATE_5_PERSON_GOOGLE_SHEETS_LEDGERS",
        "people_count": 5,
        "settled_through": day.isoformat(),
        "net_profit_vnd": total,
    }
    return value


def run_engine(source_end: date, source_xlsx: Path, output_dir: Path) -> dict:
    output = output_dir / "private" / "fusion4-engine-plan.json"
    command = [
        sys.executable, str(ENGINE_SCRIPT), "--source-xlsx", str(source_xlsx),
        "--source-end", source_end.isoformat(), "--output", str(output),
    ]
    completed = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        raise PipelineError(
            "Fusion4 engine thất bại: " + (completed.stderr or completed.stdout)[-1200:]
        )
    return read_json(output)


def make_plan(engine: dict, target: date, data_lock: date) -> dict:
    if engine.get("target_date") != target.isoformat():
        raise PipelineError("Ngày engine FUSION4 không khớp ngày mục tiêu")
    if engine.get("source_end") != data_lock.isoformat():
        raise PipelineError("Khóa dữ liệu engine FUSION4 không khớp")
    if engine.get("config_id") != CONFIG_ID:
        raise PipelineError("Config ID engine FUSION4 không khớp")
    codes = [common.code2(code) for code in engine.get("codes", [])]
    points = {common.code2(key): int(value)
              for key, value in engine.get("points_by_code", {}).items()}
    if codes != list(points) or [points[code] for code in codes] != [50, 50, 50, 30]:
        raise PipelineError("Engine trả lệnh không đúng thứ hạng 50-50-50-30")
    if engine.get("outcome_known_at_selection") is not False:
        raise PipelineError("Engine FUSION4 báo kết quả mục tiêu đã biết")
    return {
        "target_date": target.isoformat(),
        "data_lock_date": data_lock.isoformat(),
        "status": "LOCKED_WAITING_RESULT",
        "method": METHOD,
        "config_id": CONFIG_ID,
        "codes": codes,
        "number_of_codes": 4,
        "ranked_points": [50, 50, 50, 30],
        "points_by_code": points,
        "total_points": 180,
        "cost_per_point_vnd": common.COST_PER_POINT,
        "total_capital_vnd": 4_140_000,
        "maximum_loss_vnd": 4_140_000,
        "core_100_enabled": False,
        "other_50_enabled": False,
        "outcome_known_at_selection": False,
        "selection_input_hash": engine["selection_input_hash"],
    }


def fmt_vnd(value: int, signed: bool = False) -> str:
    prefix = "+" if signed and value > 0 else ""
    return (prefix + f"{value:,}đ").replace(",", ".")


def fmt_million(value: int, signed: bool = False) -> str:
    prefix = "+" if signed and value > 0 else ""
    text = f"{abs(value)/1_000_000:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 else prefix
    return sign + text + "tr"


def pct(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}%".replace(".", ",")


def render(current: dict) -> str:
    plan = current["plan"]
    actual = current["actual_performance"]
    month = actual["current_month"]
    total = actual["total"]
    target = date.fromisoformat(plan["target_date"])
    locked = date.fromisoformat(plan["data_lock_date"])
    tracking_start = date.fromisoformat(actual["tracking_start_date"])
    actual_settled = date.fromisoformat(actual["settled_through"])
    ranks = [1, 2, 3, 4]
    replacements = {
        "AUDIT_ID": current["audit_id"],
        "DATA_LOCK_DMY": locked.strftime("%d/%m/%Y"),
        "TARGET_WEEKDAY": WEEKDAYS[target.weekday()],
        "TARGET_DMY": target.strftime("%d/%m/%Y"),
        "NUMBERS_HTML": "\n          ".join(
            f'<article class="number"><span>HẠNG {rank}</span><b>{escape(code)}</b>'
            f'<strong>{plan["points_by_code"][code]} điểm</strong></article>'
            for rank, code in zip(ranks, plan["codes"])
        ),
        "TOTAL_POINTS": "180",
        "CAPITAL_VND": fmt_vnd(plan["total_capital_vnd"]),
        "COPY_PLAN": escape(
            f"{target.strftime('%d/%m/%Y')}: "
            + ", ".join(f"{code}×{plan['points_by_code'][code]}" for code in plan["codes"])
            + f" điểm — tổng 180 điểm — vốn {fmt_vnd(plan['total_capital_vnd'])}",
            quote=True,
        ),
        "ACTUAL_START_DMY": tracking_start.strftime("%d/%m/%Y"),
        "ACTUAL_SETTLED_DMY": actual_settled.strftime("%d/%m/%Y"),
        "ACTUAL_STATUS": f"Đã đối chiếu Google Sheets đến {actual_settled.strftime('%d/%m/%Y')}",
        "MONTH_LABEL": f"Tháng {actual['current_month_id'][5:7]}/{actual['current_month_id'][:4]}",
        "MONTH_WINS": str(month["wins"]),
        "MONTH_LOSSES": str(month["losses"]),
        "MONTH_WIN_STREAK": str(month["longest_winning_streak"]),
        "MONTH_LOSS_STREAK": str(month["longest_losing_streak"]),
        "MONTH_PNL": fmt_vnd(month["net_profit_vnd"], signed=True),
        "MONTH_PNL_CLASS": "positive" if month["net_profit_vnd"] >= 0 else "negative",
        "TOTAL_WINS": str(total["wins"]),
        "TOTAL_LOSSES": str(total["losses"]),
        "TOTAL_WIN_STREAK": str(total["longest_winning_streak"]),
        "TOTAL_LOSS_STREAK": str(total["longest_losing_streak"]),
        "TOTAL_PNL": fmt_vnd(total["net_profit_vnd"], signed=True),
        "TOTAL_PNL_CLASS": "positive" if total["net_profit_vnd"] >= 0 else "negative",
    }
    html = TEMPLATE.read_text(encoding="utf-8")
    for key, value in replacements.items():
        html = html.replace("{{" + key + "}}", str(value))
    leftovers = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", html)))
    if leftovers:
        raise PipelineError(f"Template FUSION4 còn biến chưa thay: {leftovers}")
    return html


def source_operation(kind: str, record: dict) -> dict:
    core = {"kind": kind, "record": record}
    return {
        "kind": kind, "operation_id": digest(core),
        "row_hash": digest(record), "record": record,
    }


def build_sheet_payload(target: date, plan: dict, settlement: dict,
                        snapshot: dict, input_hash: str,
                        personal: list[dict] | None = None,
                        blocked: list[dict] | None = None) -> dict:
    # Stable across the scheduled retries so operation IDs remain idempotent.
    created = f"{(target - timedelta(days=1)).isoformat()}T19:15:00+07:00"
    settlement_record = {
        "record_type": "SETTLEMENT", "date": settlement["date"],
        "status": settlement["status"], "method": METHOD,
        "codes": settlement["codes"], "points_by_code": settlement["points_by_code"],
        "total_points": settlement["total_points"],
        "capital_vnd": settlement["capital_vnd"],
        "payout_vnd": settlement["payout_vnd"], "pnl_vnd": settlement["pnl_vnd"],
        "hit_units": settlement["hit_units"], "source_date": settlement["date"],
        "input_hash": input_hash, "created_at": created,
    }
    plan_record = {
        "record_type": "PLAN", "date": plan["target_date"],
        "status": plan["status"], "method": METHOD, "codes": plan["codes"],
        "points_by_code": plan["points_by_code"], "total_points": plan["total_points"],
        "capital_vnd": plan["total_capital_vnd"], "payout_vnd": None,
        "pnl_vnd": None, "hit_units": None, "source_date": plan["data_lock_date"],
        "input_hash": input_hash, "created_at": created,
    }
    if personal is None or blocked is None:
        personal, blocked = common.personal_operations(
            snapshot, date.fromisoformat(settlement["date"]), snapshot["draw"]
        )
    for operation in personal:
        if operation.get("note"):
            operation["note"] = operation["note"].replace(
                "Tự động V32 06:00", "Tự động FUSION4 19:15"
            )
            operation_core = {
                key: value for key, value in operation.items()
                if key != "operation_id"
            }
            operation["operation_id"] = digest(operation_core)
    operations = [
        source_operation("UPSERT_SOURCE_SETTLEMENT", settlement_record),
        *personal,
        source_operation("UPSERT_SOURCE_PLAN", plan_record),
    ]
    return {
        "schema_version": "MB_FUSION4_SHEETS_TXN_V1",
        "private": True, "must_not_publish_to_pages": True,
        "target_date": target.isoformat(), "input_hash": input_hash,
        "operations": operations, "blocked_personal_rows": blocked,
        "payload_hash": digest(operations),
    }


def public_payload(target: date, plan: dict, settlement: dict, state: dict,
                   engine: dict, input_hash: str) -> dict:
    return {
        "schema_version": "MB_FUSION4_180_WEB_V1",
        "audit_id": f"MB-{target.strftime('%Y%m%d')}-FUSION4-180",
        "generated_at": datetime.now(VN).isoformat(timespec="seconds"),
        "timezone": "Asia/Bangkok",
        "method": {
            "short_name": METHOD, "official_name": METHOD,
            "config_id": CONFIG_ID, "status": "PRODUCTION_OFFICIAL",
            "locked_from": "2026-07-19",
            "ranking_formula": engine["ranking"]["formula"],
            "a1_role": engine["ranking"]["a1_role"],
            "promotion_note": "Chỉ thay khi nhánh mới vượt kiểm định nhân quả và tiêu chí rủi ro đã khóa.",
        },
        "plan": plan,
        "overlay": {
            "active": False, "eligible_width": False,
            "normalized_margin": 0, "activation_threshold": 1,
            "decision": "DISABLED_BY_FIXED_FUSION4",
        },
        "stake_policy": [
            {"rank_from": 1, "rank_to": 3, "points_per_code": 50},
            {"rank_from": 4, "rank_to": 4, "points_per_code": 30},
        ],
        "latest_settlement": settlement,
        "actual_performance": state["actual"],
        "group_actual_pnl": state["group_actual_pnl"],
        "backtest": {
            "current_month": state["current_month"],
            "current_year": state["current_year"],
            "full": state["full"],
        },
        "constraints": {
            "fixed_total_codes": 4, "maximum_total_points": 180,
            "duplicate_codes": 0, "martingale": False,
            "same_day_outcome_leakage": False,
            "personal_actual_pnl_is_separate": True,
            "public_group_pnl_is_aggregate_only": True,
        },
        "audit": {
            "source_history_primary_equals_mirror": True,
            "source_history_date": settlement["date"], "source_result_units": 27,
            "input_hash": input_hash, "selection_input_hash": plan["selection_input_hash"],
            "static_voter_manifest_sha256": engine["ranking"]["static_voter_manifest_sha256"],
            "plan_replayed_from_locked_source": True,
            "capital_formula_verified": True, "target_outcome_used": False,
            "causality": engine["causality"],
            "disclaimer": "Backtest là số liệu lịch sử, không bảo đảm kết quả tương lai.",
        },
        "automation": {
            "pipeline_version": PIPELINE_VERSION,
            "schedule": "19:15 Asia/Bangkok",
            "status": "PREPARED_SHEETS_REQUIRED_BEFORE_PUBLISH",
            "personal_ledger_policy": "ONLY_SETTLE_EXISTING_ACTUAL_ORDERS",
            "website_pnl_source": "PERSONAL_AND_5_LEDGER_ACTUALS",
        },
    }


def prepare(args: argparse.Namespace) -> None:
    target = date.fromisoformat(args.target_date)
    previous = target - timedelta(days=1)
    output = Path(args.output).resolve()
    source = Path(args.source_xlsx).resolve()
    snapshot = read_json(Path(args.pnl_snapshot))
    history = common.load_history(source)
    if previous not in history:
        raise PipelineError(f"Chưa có kỳ {previous} đủ 27/27")
    previous_plan = load_plan(previous)
    state_before = read_json(STATE_FILE)
    expected_through = (previous - timedelta(days=1)).isoformat()
    if state_before.get("settled_through") != expected_through:
        raise PipelineError(
            f"State đang đến {state_before.get('settled_through')}, cần {expected_through}"
        )
    prefix = [[day.isoformat(), history[day]] for day in sorted(history) if day <= previous]
    ledger_totals = [
        {"name": entry.get("name"), "pnl_vnd": ledger_total(entry)}
        for entry in snapshot.get("people", [])
    ]
    immutable = {
        "pipeline_version": PIPELINE_VERSION, "target_date": target.isoformat(),
        "previous_plan_hash": digest(previous_plan),
        "history_prefix_hash": digest(prefix), "state_before_hash": digest(state_before),
        "personal_inputs_hash": common.personal_input_fingerprint(snapshot, previous),
        "personal_ledger_totals_hash": digest(ledger_totals),
        "template_hash": sha256(TEMPLATE.read_bytes()).hexdigest(),
        "pipeline_code_hash": sha256(Path(__file__).read_bytes()).hexdigest(),
        "engine_wrapper_hash": sha256(ENGINE_SCRIPT.read_bytes()).hexdigest(),
    }
    input_hash = digest(immutable)
    committed = TX_DIR / f"{target.isoformat()}.json"
    if committed.exists():
        old = read_json(committed)
        if old.get("status") == "COMMITTED" and old.get("input_hash") == input_hash:
            write_json(output / "prepared.json", {
                "status": "NOOP_ALREADY_COMMITTED", "target_date": str(target),
                "input_hash": input_hash, "noop": True,
            })
            write_json(output / "private" / "sheets_payload.json", {
                "schema_version": "MB_FUSION4_SHEETS_TXN_V1", "target_date": str(target),
                "input_hash": input_hash, "operations": [], "payload_hash": digest([]),
                "noop": True,
            })
            return
        raise PipelineError("Transaction FUSION4 cùng ngày đã tồn tại nhưng xung đột")

    settlement = settle(previous_plan, history[previous])
    snapshot["draw"] = history[previous]
    personal, blocked = common.personal_operations(snapshot, previous, snapshot["draw"])
    state = advance_state(state_before, settlement)
    state = advance_personal_actual(state, previous, personal)
    state = reconcile_group_actual(state, previous, snapshot, personal)
    engine_workbook = output / "private" / "engine-input.xlsx"
    common.write_truncated_engine_workbook(history, previous, engine_workbook)
    engine = run_engine(previous, engine_workbook, output)
    plan = make_plan(engine, target, previous)
    current = public_payload(target, plan, settlement, state, engine, input_hash)
    html = render(current)
    sheets = build_sheet_payload(
        target, plan, settlement, snapshot, input_hash, personal, blocked
    )
    transaction = {
        "pipeline_version": PIPELINE_VERSION, "status": "PREPARED",
        "target_date": str(target), "previous_date": str(previous),
        "input_hash": input_hash, "immutable": immutable,
        "settlement_hash": digest(settlement), "plan_hash": digest(plan),
        "public_json_hash": digest(current),
        "public_html_hash": sha256(html.encode()).hexdigest(),
        "state_after_hash": digest(state), "sheets_payload_hash": sheets["payload_hash"],
        "sheets_operation_ids": [item["operation_id"] for item in sheets["operations"]],
        "prepared_at": datetime.now(VN).isoformat(timespec="seconds"),
    }
    repo = output / "repo"
    write_text(repo / "index.html", html)
    write_json(repo / "data" / "current.json", current)
    write_json(repo / "data" / "fusion4-state.json", state)
    write_json(repo / "data" / "fusion4-plans" / f"{target}.json", plan)
    write_json(repo / "data" / "fusion4-settlements" / f"{previous}.json", settlement)
    write_json(repo / "data" / "fusion4-transactions" / f"{target}.json", transaction)
    write_json(output / "private" / "sheets_payload.json", sheets)
    write_json(output / "prepared.json", {
        **transaction, "noop": False,
        "repo_files": sorted(str(path.relative_to(repo)) for path in repo.rglob("*") if path.is_file()),
    })
    print(f"FUSION4_PREPARED={target}")


def finalize(args: argparse.Namespace) -> None:
    output = Path(args.output).resolve()
    prepared = read_json(output / "prepared.json")
    receipt = read_json(Path(args.receipt))
    if prepared.get("noop"):
        if receipt.get("status") != "NOOP":
            raise PipelineError("Receipt NOOP không hợp lệ")
        return
    if receipt.get("status") != "APPLIED_READBACK_VERIFIED":
        raise PipelineError("Google Sheets chưa được ghi/đọc lại đầy đủ")
    for key in ("target_date", "input_hash", "payload_hash"):
        expected_key = "sheets_payload_hash" if key == "payload_hash" else key
        if receipt.get(key) != prepared.get(expected_key):
            raise PipelineError(f"Receipt FUSION4 sai {key}")
    if receipt.get("operation_ids") != prepared["sheets_operation_ids"]:
        raise PipelineError("Receipt FUSION4 sai operation IDs")
    repo = output / "repo"
    declared = set(prepared["repo_files"])
    actual = {str(path.relative_to(repo)) for path in repo.rglob("*") if path.is_file()}
    if actual != declared or any(path.is_symlink() for path in repo.rglob("*")):
        raise PipelineError("Staging FUSION4 thiếu/thừa file hoặc có symlink")
    current_path = repo / "data" / "current.json"
    current = read_json(current_path)
    current["automation"]["status"] = "SHEETS_APPLIED_READBACK_VERIFIED_READY_TO_PUBLISH"
    current["automation"]["sheets_receipt_hash"] = digest(receipt)
    write_json(current_path, current)
    write_text(repo / "index.html", render(current))
    tx_rel = Path("data") / "fusion4-transactions" / f"{prepared['target_date']}.json"
    transaction = read_json(repo / tx_rel)
    transaction.update({
        "status": "COMMITTED", "sheets_receipt_hash": digest(receipt),
        "sheets_operation_ids": receipt["operation_ids"],
        "final_public_json_hash": digest(current),
        "final_public_html_hash": sha256((repo / "index.html").read_bytes()).hexdigest(),
        "committed_at": datetime.now(VN).isoformat(timespec="seconds"),
    })
    write_json(repo / tx_rel, transaction)
    for relative in sorted(declared - {str(tx_rel)}) + [str(tx_rel)]:
        source = repo / relative
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    print(f"FUSION4_FINALIZED={prepared['target_date']}")


def verify_seed(_: argparse.Namespace) -> None:
    state = read_json(STATE_FILE)
    current = read_json(DATA / "current.json")
    plan = load_plan(date.fromisoformat(current["plan"]["target_date"]))
    if state["settled_through"] != current["plan"]["data_lock_date"]:
        raise PipelineError("State và current FUSION4 lệch ngày")
    if plan != current["plan"]:
        raise PipelineError("Plan file và current FUSION4 lệch nội dung")
    print("FUSION4_SEED_OK")


def render_current(_: argparse.Namespace) -> None:
    """Render the public page from the already-verified current payload."""
    current = read_json(DATA / "current.json")
    write_text(ROOT / "index.html", render(current))
    print(f"FUSION4_RENDERED={current['plan']['target_date']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--target-date", required=True)
    prepare_parser.add_argument("--source-xlsx", required=True)
    prepare_parser.add_argument("--pnl-snapshot", required=True)
    prepare_parser.add_argument("--output", required=True)
    prepare_parser.set_defaults(func=prepare)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("--output", required=True)
    finalize_parser.add_argument("--receipt", required=True)
    finalize_parser.set_defaults(func=finalize)
    verify_parser = sub.add_parser("verify-seed")
    verify_parser.set_defaults(func=verify_seed)
    render_parser = sub.add_parser("render-current")
    render_parser.set_defaults(func=render_current)
    args = parser.parse_args()
    try:
        args.func(args)
    except (PipelineError, common.PipelineError) as exc:
        print(f"FUSION4_PIPELINE_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
