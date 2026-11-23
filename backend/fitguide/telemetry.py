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
