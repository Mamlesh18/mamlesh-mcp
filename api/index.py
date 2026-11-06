"""Vercel entry point: the MCP server over streamable HTTP at /mcp.

Every request must carry the MCP_API_KEY, either as
`Authorization: Bearer <key>` (preferred) or `?key=<key>` for clients that
can't set headers. Without it the server would hand admin access to anyone
who finds the URL.

Serverless note: the MCP session manager has to run inside the Starlette
lifespan, and Vercel doesn't reliably run ASGI lifespan events or keep one
event loop across invocations. So each request gets a fresh stateless app
with its lifespan entered just for that request. Building the app is cheap.
"""
from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from upstride_mcp.server import mcp  # noqa: E402


async def _send_json(send, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
    })
    await send({"type": "http.response.body", "body": body})


def _authorized(scope) -> bool:
    expected = os.environ.get("MCP_API_KEY", "")
    if not expected:
        return False
    headers = dict(scope.get("headers") or [])
    auth = headers.get(b"authorization", b"").decode()
    supplied = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not supplied:
        qs = parse_qs((scope.get("query_string") or b"").decode())
        supplied = (qs.get("key") or [""])[0]
    return bool(supplied) and hmac.compare_digest(supplied, expected)


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        # Nothing to set up globally; acknowledge so the runtime doesn't hang.
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    if scope["type"] != "http":
        return

    if scope["path"] in ("/", "/health"):
        await _send_json(send, 200, {"status": "ok", "service": "Upstride Admin MCP", "endpoint": "/mcp"})
        return

    if not os.environ.get("MCP_API_KEY"):
        await _send_json(send, 500, {"error": "MCP_API_KEY is not configured on the server"})
        return
    if not _authorized(scope):
        await _send_json(send, 401, {"error": "unauthorized"})
        return

    mcp_app = mcp.http_app(path="/mcp", stateless_http=True, json_response=True)
    async with mcp_app.router.lifespan_context(mcp_app):
        await mcp_app(scope, receive, send)
