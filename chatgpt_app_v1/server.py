from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer
from mcp_types import ToolAnnotations

from mb_engine import MBEngineService

mcp = MCPServer("MB TOP2+ Engine v1")
service = MBEngineService()

READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
WRITE_IDEMPOTENT = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)


@mcp.tool(name="run_day", title="Run MB TOP2+ Day", annotations=WRITE_IDEMPOTENT)
def run_day(target_date: str) -> dict[str, Any]:
    """Use this when the user asks to calculate MB TOP2+ for one target day. Runs in isolation, validates, and returns a draft run_id; it does not freeze production."""
    return service.run_day(target_date)


@mcp.tool(name="freeze_day", title="Freeze MB TOP2+ Day", annotations=WRITE_IDEMPOTENT)
def freeze_day(target_date: str, run_id: str) -> dict[str, Any]:
    """Use this after a validated run is accepted. Commits exactly that run as immutable PRE_DRAW_FROZEN and refuses conflicting re-freezes."""
    return service.freeze_day(target_date, run_id)


@mcp.tool(name="get_day", title="Get Frozen Day", annotations=READ_ONLY)
def get_day(target_date: str) -> dict[str, Any]:
    """Use this to read the frozen and settlement state for a target day."""
    return service.get_day(target_date)


@mcp.tool(name="get_candidates", title="Get Candidate Ranking", annotations=READ_ONLY)
def get_candidates(target_date: str, limit: int = 10, run_id: str | None = None) -> dict[str, Any]:
    """Use this to inspect the deterministic FUSION67 candidate ranking for a frozen day or a validated draft run."""
    return service.get_candidates(target_date, limit, run_id)


@mcp.tool(name="get_hot_cold", title="Get HOT COLD", annotations=READ_ONLY)
def get_hot_cold(target_date: str, run_id: str | None = None) -> dict[str, Any]:
    """Use this to inspect STRONG HOT, FAST HOT and COLD method states calculated before the draw."""
    return service.get_hot_cold(target_date, run_id)


@mcp.tool(name="get_method_audit", title="Get Method Audit", annotations=READ_ONLY)
def get_method_audit(target_date: str, method: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    """Use this to inspect all 67 method outputs or one exact method, including role, state, windows and P/L evidence."""
    return service.get_method_audit(target_date, method, run_id)


@mcp.tool(name="audit_day", title="Audit MB TOP2+ Day", annotations=READ_ONLY)
def audit_day(target_date: str, run_id: str | None = None) -> dict[str, Any]:
    """Use this to read validator results for a validated draft or an immutable frozen day."""
    return service.audit_day(target_date, run_id)


@mcp.tool(name="settle_day", title="Settle MB TOP2+ Day", annotations=WRITE_IDEMPOTENT)
def settle_day(target_date: str, draw: list[int], sources: list[str], full_prizes: list[str] | None = None) -> dict[str, Any]:
    """Use this only after the draw is independently verified by at least two sources. Settles the frozen pick and records data for T+1; it never edits the frozen pick."""
    return service.settle_day(target_date, draw, sources, full_prizes)


@mcp.tool(name="prospective_status", title="Prospective Status", annotations=READ_ONLY)
def prospective_status() -> dict[str, Any]:
    """Use this to inspect frozen/settled days and the prospective research clock without changing production."""
    return service.prospective_status()


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
