"""Optional visit log for the demo owner. Off unless VISIT_LOG_WEBHOOK_URL is set.
It sends ONLY: event name, UTC time and (if the visitor typed one) the first name. No health data, no IP, no chat text.
Point it at something you own (a Google Apps Script web app writing to a Sheet, a Discord webhook, etc.)."""
from __future__ import annotations
import datetime as dt
import httpx
from .config import get_settings


async def log_visit(event: str, name: str = "") -> bool:
    url = get_settings().visit_webhook
    if not url:
        return False
    payload = {"event": event[:40], "time": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "name": name[:40]}
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.post(url, json=payload)
            return r.status_code < 400
    except httpx.HTTPError:
        return False
