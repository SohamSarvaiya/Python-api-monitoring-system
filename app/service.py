"""Glue: run a check, store it, update monitor state, fire alerts on state changes only."""
import asyncio
from typing import Optional

import httpx

from . import alerts, checker, db
from .config import get_settings


def record_result(monitor_id: int, result: dict) -> Optional[dict]:
    """Persist a check result; return an alert dict only when the state flips."""
    m = db.get_monitor(monitor_id)
    if m is None:
        return None
    now = db.iso(db.utcnow())
    db.insert_check(monitor_id, now, result["status_code"], result["response_ms"],
                    result["ok"], result["error"])

    failures = 0 if result["ok"] else m["consecutive_failures"] + 1
    state, alert = m["state"], None
    threshold = get_settings().failure_threshold

    if not result["ok"] and failures >= threshold and state != "down":
        state = "down"
        reason = result["error"] or "unknown error"
        alert = db.insert_alert(
            monitor_id, "DOWN",
            f"🔴 {m['name']} is DOWN ({failures} consecutive failures). "
            f"Last error: {reason}. URL: {m['url']}")
    elif result["ok"] and state == "down":
        state = "up"
        alert = db.insert_alert(
            monitor_id, "RECOVERED",
            f"🟢 {m['name']} has RECOVERED ({result['response_ms']} ms). URL: {m['url']}")
    elif result["ok"] and state == "unknown":
        state = "up"

    db.update_monitor_state(monitor_id, state, failures, now)
    if alert:
        alert["monitor_name"] = m["name"]
    return alert


async def check_and_record(monitor: dict, client: Optional[httpx.AsyncClient] = None) -> dict:
    if client is None:
        async with checker.make_client() as c:
            result = await checker.run_check(c, monitor)
    else:
        result = await checker.run_check(client, monitor)
    alert = await asyncio.to_thread(record_result, monitor["id"], result)
    if alert:
        await alerts.notify(alert)
    return {**result, "alert": alert["kind"] if alert else None}
