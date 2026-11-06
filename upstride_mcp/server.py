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


# ═════════════════════════════════════════════════════════════════ leads ══

@mcp.tool(annotations=READ)
async def list_leads(
    search: Annotated[Optional[str], Field(description="Filter on name, email or phone")] = None,
    limit: Annotated[int, Field(ge=1, le=500)] = 50,
) -> dict:
    """Leads from public signups and the apply form, newest first."""
    data = await request("GET", "/api/admin/leads")
    leads = data.get("leads", [])
    if search:
        q = search.lower()
        leads = [
            l for l in leads
            if any(q in str(l.get(k, "")).lower() for k in ("name", "email", "phone"))
        ]
    return {"total_matching": len(leads), "leads": leads[:limit]}


# ══════════════════════════════════════════════════════════ site settings ══

@mcp.tool(annotations=READ)
async def get_site_settings() -> dict:
    """Course page settings: live/original price, payment URL, notes, calendar and
    community links, talks order."""
    return await request("GET", "/api/admin/settings")


@mcp.tool(annotations=WRITE)
async def update_site_settings(
    live_price_inr: Optional[int] = None,
    original_price_inr: Optional[int] = None,
    live_payment_url: Optional[str] = None,
    enrollment_note: Optional[str] = None,
    weekend_full_message: Optional[str] = None,
    early_bird_text: Optional[str] = None,
    calendar_link: Optional[str] = None,
    community_link: Optional[str] = None,
    talks_order: Optional[Literal["newest", "oldest"]] = None,
) -> dict:
    """Change course page settings. Pass only the fields to change; changes go live immediately."""
    body = {k: v for k, v in locals().items() if v is not None}
    if not body:
        raise ToolError("Pass at least one setting to change.")
    return await request("PUT", "/api/admin/settings", json=body)


# ═════════════════════════════════════════════════════════════════ blogs ══

class Block(BaseModel):
    """One block of a blog body."""
    type: Literal["heading", "paragraph", "list", "image", "quote", "code"]
    text: Optional[str] = Field(default=None, description="heading / paragraph / quote / code text")
    items: Optional[list[str]] = Field(default=None, description="Bullet items, for type=list")
    url: Optional[str] = Field(default=None, description="Image URL, for type=image")
    caption: Optional[str] = Field(default=None, description="Image caption, for type=image")


async def _find_blog(slug: str) -> dict:
    blogs = await request("GET", "/api/admin/blogs")
    for b in blogs:
        if b["slug"] == slug:
            return b
    raise ToolError(f"No blog with slug '{slug}'. Use list_blogs to see slugs.")


@mcp.tool(annotations=READ)
async def list_blogs(
    include_drafts: bool = True,
) -> list[dict]:
    """All blogs, newest first: slug, title, excerpt, published flag, created date.
    Bodies are left out; use get_blog for the full content."""
    blogs = await request("GET", "/api/admin/blogs")
    return [
        {k: v for k, v in b.items() if k != "blocks"}
        for b in blogs
        if include_drafts or b.get("published")
    ]


@mcp.tool(annotations=READ)
async def get_blog(slug: str) -> dict:
    """One blog with its full body (blocks), drafts included."""
    return await _find_blog(slug)


@mcp.tool(annotations=WRITE)
async def create_blog(
    title: Annotated[str, Field(min_length=1, max_length=200)],
    blocks: Annotated[list[Block], Field(description="Body as ordered blocks")],
    excerpt: Annotated[str, Field(max_length=400, description="Short summary shown on the list page")] = "",
    cover_image: Annotated[Optional[str], Field(description="Cover image URL")] = None,
    published: Annotated[bool, Field(description="False saves it as a draft")] = False,
) -> dict:
    """Write a new blog post. Saved as a draft unless published=True. The slug is
    generated from the title."""
    return await request("POST", "/api/admin/blogs", json={
        "title": title,
        "excerpt": excerpt,
        "cover_image": cover_image,
        "blocks": [b.model_dump() for b in blocks],
        "published": published,
    })


@mcp.tool(annotations=WRITE)
async def update_blog(
    slug: Annotated[str, Field(description="Current slug of the post")],
    title: Optional[str] = None,
    blocks: Annotated[Optional[list[Block]], Field(description="Replaces the whole body when given")] = None,
    excerpt: Optional[str] = None,
    cover_image: Optional[str] = None,
    published: Annotated[Optional[bool], Field(description="True publishes, False unpublishes")] = None,
) -> dict:
    """Edit a blog post. Only the fields you pass change. Changing the title changes the slug."""
    current = await _find_blog(slug)
    body = {
        "title": title if title is not None else current["title"],
        "excerpt": excerpt if excerpt is not None else current.get("excerpt", ""),
        "cover_image": cover_image if cover_image is not None else current.get("cover_image"),
        "blocks": [b.model_dump() for b in blocks] if blocks is not None else current.get("blocks", []),
        "published": published if published is not None else current.get("published", True),
    }
    return await request("PUT", f"/api/admin/blogs/{slug}", json=body)


@mcp.tool(annotations=DESTRUCTIVE)
async def delete_blog(slug: str) -> dict:
    """Permanently delete a blog post. Confirm with the user first."""
    return await request("DELETE", f"/api/admin/blogs/{slug}")
