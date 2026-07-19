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
    settlement = current["latest_settlement"]
    month = current["backtest"]["current_month"]
    year = current["backtest"]["current_year"]
    target = date.fromisoformat(plan["target_date"])
    locked = date.fromisoformat(plan["data_lock_date"])
    settled = date.fromisoformat(settlement["date"])
    ranks = [1, 2, 3, 4]
    hit_codes = settlement.get("hit_codes", [])
    settlement_replay = str(settlement.get("status", "")).startswith("BACKTEST_")
    replacements = {
        "AUDIT_ID": current["audit_id"],
        "DATA_LOCK_DMY": locked.strftime("%d/%m/%Y"),
        "DATA_LOCK_DM": locked.strftime("%d/%m"),
        "TARGET_WEEKDAY": WEEKDAYS[target.weekday()],
        "TARGET_DMY": target.strftime("%d/%m/%Y"),
        "TARGET_DM": target.strftime("%d/%m"),
        "NUMBERS_HTML": "\n          ".join(
            f'<div class="number"><b>{escape(code)}</b><span>{plan["points_by_code"][code]} ĐIỂM · HẠNG {rank}</span></div>'
            for rank, code in zip(ranks, plan["codes"])
        ),
        "PLAN_WIDTH": "4",
        "TOTAL_POINTS": "180",
        "CAPITAL_VND": fmt_vnd(plan["total_capital_vnd"]),
        "COPY_PLAN": escape(
            f"{target.strftime('%d/%m/%Y')}: "
            + ", ".join(f"{code}×{plan['points_by_code'][code]}" for code in plan["codes"])
            + f" điểm — tổng 180 điểm — vốn {fmt_vnd(plan['total_capital_vnd'])}",
            quote=True,
        ),
        "SETTLEMENT_DMY": settled.strftime("%d/%m/%Y"),
        "SETTLEMENT_HEADING": "Kiểm định" if settlement_replay else "Quyết toán",
        "SETTLEMENT_SET_LABEL": "Bộ số replay" if settlement_replay else "Bộ số",
        "SETTLEMENT_NOTE": (
            "Replay nhân quả; đây là sổ phương pháp, tách biệt lệnh thực tế trong sổ 5 người và không công khai dữ liệu cá nhân."
            if settlement_replay else
            "Lệnh phương pháp đã khóa từ kỳ trước; kết quả được đối chiếu đủ 27/27. Sổ 5 người chỉ quyết toán các lệnh thực tế đã tồn tại."
        ),
        "SETTLEMENT_CODES": "–".join(settlement["codes"]),
        "SETTLEMENT_HITS": (
            "Mã trúng: " + ", ".join(hit_codes) + f" · {settlement['hit_units']} nháy"
            if hit_codes else "Không có mã trúng"
        ),
        "SETTLEMENT_CAPITAL": fmt_vnd(settlement["capital_vnd"]),
        "SETTLEMENT_PAYOUT": fmt_vnd(settlement["payout_vnd"]),
        "SETTLEMENT_PAYOUT_NOTE": (
            " + ".join(
                f"{code} × {settlement['points_by_code'][code]} điểm × "
                f"{settlement['hits_by_code'][code]} nháy"
                for code in hit_codes
            ) + " × 80.000đ"
            if settlement_replay and hit_codes else
            "80.000đ/điểm/nháy"
        ),
        "SETTLEMENT_PNL_CLASS": "green" if settlement["pnl_vnd"] >= 0 else "red",
        "SETTLEMENT_PNL": fmt_vnd(settlement["pnl_vnd"], signed=True),
        "SETTLEMENT_ROI": pct(settlement["roi_pct"]),
        "MONTH_PERIOD": f"01–{locked.strftime('%d/%m')}",
        "MONTH_HIT_RATE": pct(month["hit_day_rate_pct"]),
        "MONTH_HIT_DAYS": str(month["hit_days"]),
        "MONTH_SESSIONS": str(month["sessions"]),
        "MONTH_PROFIT_RATE": pct(month["profit_day_rate_pct"]),
        "MONTH_PROFIT_DAYS": str(month["profit_days"]),
        "MONTH_NET": fmt_million(month["net_profit_vnd"], signed=True),
        "MONTH_NET_CLASS": "green" if month["net_profit_vnd"] >= 0 else "red",
        "MONTH_CAPITAL": fmt_million(month["capital_vnd"]),
        "MONTH_PF": (
            f"{month['profit_factor']:.4f}".replace(".", ",")
            if month.get("profit_factor") is not None else "—"
        ),
        "MONTH_ROI": pct(month["roi_pct"], 4),
        "MONTH_ROI_CLASS": "green" if month["roi_pct"] >= 0 else "red",
        "MONTH_MAXDD": fmt_million(month["max_drawdown_vnd"]),
        "YEAR_SESSIONS": str(year["sessions"]),
        "YEAR_HIT_DAYS": str(year["hit_days"]),
        "YEAR_HIT_RATE": pct(year["hit_day_rate_pct"], 4),
        "YEAR_PROFIT_RATE": pct(year["profit_day_rate_pct"], 4),
        "YEAR_NET": fmt_million(year["net_profit_vnd"], signed=True),
        "YEAR_NET_CLASS": "green" if year["net_profit_vnd"] >= 0 else "red",
        "YEAR_CAPITAL": fmt_million(year["capital_vnd"]),
        "YEAR_ROI": pct(year["roi_pct"], 4),
        "YEAR_ROI_CLASS": "green" if year["roi_pct"] >= 0 else "red",
        "YEAR_MAXDD": fmt_million(year["max_drawdown_vnd"]),
        "YEAR_STREAK": str(year["longest_losing_streak"]),
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
                        snapshot: dict, input_hash: str) -> dict:
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
    immutable = {
        "pipeline_version": PIPELINE_VERSION, "target_date": target.isoformat(),
        "previous_plan_hash": digest(previous_plan),
        "history_prefix_hash": digest(prefix), "state_before_hash": digest(state_before),
        "personal_inputs_hash": common.personal_input_fingerprint(snapshot, previous),
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
    state = advance_state(state_before, settlement)
    engine_workbook = output / "private" / "engine-input.xlsx"
    common.write_truncated_engine_workbook(history, previous, engine_workbook)
    engine = run_engine(previous, engine_workbook, output)
    plan = make_plan(engine, target, previous)
    current = public_payload(target, plan, settlement, state, engine, input_hash)
    html = render(current)
    snapshot["draw"] = history[previous]
    sheets = build_sheet_payload(target, plan, settlement, snapshot, input_hash)
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
    args = parser.parse_args()
    try:
        args.func(args)
    except (PipelineError, common.PipelineError) as exc:
        print(f"FUSION4_PIPELINE_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
