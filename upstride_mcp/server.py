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


# ══════════════════════════════════════════════════════════════ students ══

@mcp.tool(annotations=READ)
async def list_students(
    search: Annotated[Optional[str], Field(description="Case-insensitive match on name or email")] = None,
    paid: Annotated[Optional[bool], Field(description="True = paid only, False = unpaid only, omit = all")] = None,
    page: Annotated[int, Field(ge=1)] = 1,
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
) -> dict:
    """List students, newest first, with pagination. Use paid=True to see paying students."""
    params = {"page": page, "limit": limit, "search": search}
    if paid is not None:
        params["paid"] = "true" if paid else "false"
    return await request("GET", "/api/admin/students", params=params)


@mcp.tool(annotations=READ)
async def get_student_login_sessions(
    student_id: Annotated[str, Field(description="Student id from list_students")],
) -> dict:
    """Last 20 logins for a student: IP, city/country, user agent, and how long each
    session lasted. Useful for spotting a shared account."""
    return await request("GET", f"/api/admin/students/{student_id}/sessions")


@mcp.tool(annotations=WRITE)
async def set_student_active(
    student_id: Annotated[str, Field(description="Student id from list_students")],
    is_active: Annotated[bool, Field(description="False blocks the student from logging in")],
) -> dict:
    """Activate or deactivate a student account."""
    return await request("PATCH", f"/api/admin/students/{student_id}", json={"is_active": is_active})


@mcp.tool(annotations=SENDS_EMAIL)
async def resend_enrollment_email(
    student_id: Annotated[str, Field(description="Student id from list_students")],
) -> dict:
    """Re-send the AI Masterclass enrollment confirmation email to a paid student and
    report the SMTP result."""
    return await request("POST", f"/api/admin/students/{student_id}/resend-confirmation")
