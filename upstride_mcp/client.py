"""Thin async client for the Upstride backend admin API.

Logs in once with the admin credentials from the environment, caches the JWT
for the life of the process (a warm serverless instance reuses it), and logs
in again automatically if the backend ever answers 401.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastmcp.exceptions import ToolError

TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Fields that should never be handed to the model, even though the backend
# returns some of them on user documents.
SENSITIVE_KEYS = {"password_hash", "onboarding_token", "active_session_id", "resume_enhancer_password"}

_token: str | None = None


def _base_url() -> str:
    url = os.environ.get("BASE_URL", "").strip().rstrip("/")
    if not url:
        raise ToolError("BASE_URL is not set in the environment.")
    return url


async def _login(client: httpx.AsyncClient) -> str:
    global _token
    static = os.environ.get("ADMIN_TOKEN", "").strip()
    if static:
        _token = static
        return _token

    email = os.environ.get("ADMIN_EMAIL", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        raise ToolError("Set ADMIN_EMAIL and ADMIN_PASSWORD (or ADMIN_TOKEN) in the environment.")

    r = await client.post(f"{_base_url()}/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        raise ToolError(f"Admin login failed ({r.status_code}): {_detail(r)}")
    data = r.json()
    if (data.get("user") or {}).get("role") != "super_admin":
        raise ToolError("Logged in, but this account is not a super_admin.")
    _token = data["access_token"]
    return _token


def _detail(r: httpx.Response) -> str:
    try:
        body = r.json()
    except ValueError:
        return r.text[:500]
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return str(body)[:500]


def scrub(value: Any) -> Any:
    """Recursively drop sensitive keys from API responses."""
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items() if k not in SENSITIVE_KEYS}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def unwrap(body: Any) -> Any:
    """Most admin routes return {"success": true, "data": {...}}; content
    routes return bare objects. Hand back just the payload either way."""
    if isinstance(body, dict) and body.get("success") is True and "data" in body:
        return body["data"]
    return body


async def request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: Any = None,
) -> Any:
    """Call an admin endpoint and return the unwrapped, scrubbed JSON."""
    global _token
    if params:
        params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        token = _token or await _login(client)
        for attempt in range(2):
            r = await client.request(
                method,
                f"{_base_url()}{path}",
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 401 and attempt == 0 and not os.environ.get("ADMIN_TOKEN"):
                _token = None
                token = await _login(client)
                continue
            break

    if r.status_code >= 400:
        raise ToolError(f"{method} {path} failed ({r.status_code}): {_detail(r)}")
    if not r.content:
        return {"ok": True}
    return scrub(unwrap(r.json()))
