# mamlesh-mcp

MCP server for the Upstride / mamlesh.me admin panel, built with FastMCP. It calls
the backend at `BASE_URL` as the super admin.

## Tools (25)

| Group | Tools |
|---|---|
| Dashboard | `get_admin_stats`, `get_site_analytics(days)` |
| Students | `list_students(search, paid, page, limit)`, `get_student_login_sessions(student_id)`, `set_student_active(student_id, is_active)`, `resend_enrollment_email(student_id)` |
| Leads | `list_leads(search, limit)` |
| Site settings | `get_site_settings`, `update_site_settings(...)` |
| Blogs | `list_blogs`, `get_blog(slug)`, `create_blog(title, blocks, excerpt, cover_image, published)`, `update_blog(slug, ...)`, `delete_blog(slug)` |
| Papershelf | `list_papers`, `add_paper(title, url, kind, date)`, `update_paper(paper_id, ...)`, `delete_paper(paper_id)` |
| Guest lectures | `list_talks`, `add_talk(date, title, venue, link)`, `update_talk(talk_id, ...)`, `delete_talk(talk_id)` |
| Profile | `get_profile`, `update_profile(...)` |
| WhatsApp batches | `list_whatsapp_batches` |

`update_*` tools take only the fields you want to change; the server merges them
with the current record. New blogs are drafts unless `published=true`.

## Environment

Copy `.env.example` to `.env`:

| Var | Purpose |
|---|---|
| `BASE_URL` | Backend URL |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Super admin login (or set `ADMIN_TOKEN` to a JWT) |
| `MCP_API_KEY` | Secret clients send as `Authorization: Bearer <key>` (HTTP only) |

## Run locally

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
python main.py        # stdio
python main.py http   # http://127.0.0.1:8000/mcp
```

## Deploy to Vercel

```bash
vercel                       # link + preview deploy
vercel env add BASE_URL
vercel env add ADMIN_EMAIL
vercel env add ADMIN_PASSWORD
vercel env add MCP_API_KEY   # e.g. python -c "import secrets;print(secrets.token_urlsafe(32))"
vercel --prod
```

The endpoint is `https://<project>.vercel.app/mcp`. Add it to Claude Code with:

```bash
claude mcp add --transport http upstride https://<project>.vercel.app/mcp \
  --header "Authorization: Bearer <MCP_API_KEY>"
```

Clients that can't send headers can use `https://<project>.vercel.app/mcp?key=<MCP_API_KEY>`.
Keep that URL private, since it contains the key.
