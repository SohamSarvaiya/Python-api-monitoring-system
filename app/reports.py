"""Uptime / latency reports computed only from stored checks."""
import math
from collections import Counter
from datetime import timedelta
from typing import Optional

from . import db


def _percentile(sorted_vals: list, pct: float) -> Optional[float]:
    if not sorted_vals:
        return None
    k = max(0, math.ceil(pct / 100 * len(sorted_vals)) - 1)
    return sorted_vals[k]


def uptime_report(monitor: dict, hours: int = 24) -> dict:
    since = db.iso(db.utcnow() - timedelta(hours=hours))
    checks = db.get_checks(monitor["id"], since=since)
    total = len(checks)
    ok_count = sum(1 for c in checks if c["ok"])
    lat = sorted(c["response_ms"] for c in checks if c["ok"] and c["response_ms"] is not None)

    errors = Counter(c["error"] or f"HTTP {c['status_code']}" for c in checks if not c["ok"])

    incidents, current = [], None
    for c in checks:
        if not c["ok"]:
            if current is None:
                current = {"started_at": c["checked_at"], "checks_failed": 0, "last_error": None}
            current["checks_failed"] += 1
            current["last_error"] = c["error"]
            current["ended_at"] = c["checked_at"]
            current["ongoing"] = True
        elif current is not None:
            current["ongoing"] = False
            incidents.append(current)
            current = None
    if current is not None:
        incidents.append(current)

    return {
        "monitor_id": monitor["id"],
        "name": monitor["name"],
        "url": monitor["url"],
        "state": monitor["state"],
        "window_hours": hours,
        "total_checks": total,
        "successful_checks": ok_count,
        "failed_checks": total - ok_count,
        "uptime_percent": round(ok_count / total * 100, 3) if total else None,
        "latency_ms": {
            "avg": round(sum(lat) / len(lat), 1) if lat else None,
            "min": lat[0] if lat else None,
            "p95": _percentile(lat, 95),
            "max": lat[-1] if lat else None,
        },
        "error_breakdown": dict(errors.most_common()),
        "incidents": incidents[-20:],
        "note": "Uptime is estimated from sampled checks, not continuous measurement.",
    }


def all_reports(hours: int = 24) -> list:
    return [uptime_report(m, hours) for m in db.list_monitors()]
