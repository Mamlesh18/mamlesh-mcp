"""Upstride admin MCP server — the admin-panel actions worth having in chat.

Groups: dashboard, students, leads, site settings, blogs, papershelf,
guest lectures (talks), about-page profile, WhatsApp batches (read-only).
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from .client import request

mcp = FastMCP(
    "Upstride Admin",
    instructions=(
        "Admin tools for the Upstride / mamlesh.me backend: dashboard numbers, students, "
        "leads, site settings, blogs, papershelf, guest lectures (talks) and the about-page "
        "profile. Read tools are safe. Ask the user before calling any delete_* tool."
    ),
)

READ = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False)
SENDS_EMAIL = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)


# ═════════════════════════════════════════════════════════════ dashboard ══

@mcp.tool(annotations=READ)
async def get_admin_stats() -> dict:
    """Student and lead counts: total, active, paid, pending password change, total leads."""
    return await request("GET", "/api/admin/stats")


@mcp.tool(annotations=READ)
async def get_site_analytics(
    days: Annotated[int, Field(ge=1, le=365, description="Window for the daily pageview series")] = 30,
) -> dict:
    """Site analytics: visitors (total/today/7d), pageviews, top paths, daily series,
    revenue, paid student count, blog/paper counts and the 10 most recent signups."""
    return await request("GET", "/api/admin/analytics", params={"days": days})
