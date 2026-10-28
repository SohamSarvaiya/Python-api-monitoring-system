"""AI-assisted failure analysis.

Design rule: the AI gets *evidence computed from our own data* and must answer with
hypotheses + confidence + what is missing. It is never allowed to present a root cause
as proven, and it is not called at all when there are too few failures to reason about."""
import json
import re
from collections import Counter
from datetime import timedelta
from typing import Optional

import httpx

from .. import db, reports
from ..config import get_settings
from . import providers

DISCLAIMER = ("AI output is a set of hypotheses based only on the monitoring data shown in "
              "'evidence'. It is NOT a confirmed root cause. Verify against server logs, "
              "metrics and recent deployments.")

SYSTEM_PROMPT = """You are an SRE assistant helping interpret API health-check data.
STRICT RULES:
1. You only see HTTP check results (status codes, latency, error strings, timestamps). You do NOT see server logs, code, infrastructure, or deployments.
2. Never state a root cause as fact. Offer *possible* causes only, each with a confidence of "low", "medium" or "high".
3. Use "high" ONLY if the evidence directly and unambiguously shows it (e.g. an explicit DNS-resolution error string repeated in every failure). Otherwise use "low" or "medium".
4. For every cause list the specific evidence from the data that supports it, and what additional data would be needed to confirm it.
5. If the data is too thin or ambiguous, say so plainly in data_limitations rather than guessing.
6. Do not invent numbers, services, or events that are not in the data.

Respond with ONLY a JSON object (no markdown fences) with exactly these keys:
{"summary": str,
 "possible_causes": [{"cause": str, "confidence": "low|medium|high", "supporting_evidence": [str], "needed_to_confirm": [str]}],
 "troubleshooting_steps": [str],
 "data_limitations": [str]}"""


def build_evidence(monitor: dict, hours: int) -> dict:
    since = db.iso(db.utcnow() - timedelta(hours=hours))
    checks = db.get_checks(monitor["id"], since=since)
    failures = [c for c in checks if not c["ok"]]
    report = reports.uptime_report(monitor, hours)
    hour_dist = Counter(c["checked_at"][11:13] for c in failures)
    fail_lat = [c["response_ms"] for c in failures if c["response_ms"] is not None]
    return {
        "monitor": {"name": monitor["name"], "url": monitor["url"], "method": monitor["method"],
                    "interval_seconds": monitor["interval_seconds"],
                    "timeout_seconds": monitor["timeout_seconds"],
                    "expected_status": monitor["expected_status"] or "any 2xx/3xx",
                    "current_state": monitor["state"]},
        "window_hours": hours,
        "total_checks": report["total_checks"],
        "failed_checks": report["failed_checks"],
        "uptime_percent": report["uptime_percent"],
        "latency_ms_of_successful_checks": report["latency_ms"],
        "avg_latency_ms_of_failed_checks": round(sum(fail_lat) / len(fail_lat), 1) if fail_lat else None,
        "error_breakdown": report["error_breakdown"],
        "failures_by_utc_hour": dict(sorted(hour_dist.items())),
        "incidents": report["incidents"][-5:],
        "most_recent_failures": [
            {"at": c["checked_at"], "status": c["status_code"], "ms": c["response_ms"], "error": c["error"]}
            for c in failures[-25:]],
    }


def _parse_json(text: str) -> Optional[dict]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    for candidate in (text, text[text.find("{"): text.rfind("}") + 1]):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except (ValueError, TypeError):
            continue
    return None


async def analyze(monitor: dict, provider: Optional[str] = None, hours: int = 24,
                  language: str = "en", client: Optional[httpx.AsyncClient] = None) -> dict:
    evidence = build_evidence(monitor, hours)
    min_failures = get_settings().ai_min_failures

    if evidence["failed_checks"] < min_failures:
        return {
            "status": "insufficient_data",
            "message": (f"Only {evidence['failed_checks']} failed check(s) in the last {hours}h; "
                        f"at least {min_failures} are needed before AI analysis is meaningful. "
                        "No AI call was made."),
            "evidence": evidence,
        }

    name = providers.resolve_provider(provider)
    lang_note = ("Write all string values in simple Hindi (Devanagari), keeping technical terms "
                 "like HTTP, DNS, timeout in English. Keep JSON keys in English."
                 if language == "hi" else "Write in clear English.")
    user_prompt = f"{lang_note}\n\nMonitoring evidence (JSON):\n{json.dumps(evidence, indent=2)}"

    raw = await providers.complete(name, SYSTEM_PROMPT, user_prompt, client=client)
    parsed = _parse_json(raw)
    return {
        "status": "ok",
        "provider": name,
        "model": providers.configured_providers()[name]["model"],
        "analysis": parsed if parsed is not None else {"raw_text": raw},
        "disclaimer": DISCLAIMER,
        "evidence": evidence,
    }
