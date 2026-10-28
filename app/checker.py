"""Performs one HTTP check. Never raises: every failure mode becomes data."""
import time
from typing import Optional

import httpx


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "python-api-monitoring-system/1.0"},
    )


def status_ok(status: int, expected: Optional[int]) -> bool:
    return status == expected if expected else 200 <= status < 400


async def run_check(client: httpx.AsyncClient, monitor: dict) -> dict:
    timeout = monitor.get("timeout_seconds") or 10
    expected = monitor.get("expected_status")
    status: Optional[int] = None
    error: Optional[str] = None
    start = time.perf_counter()
    try:
        resp = await client.request(monitor.get("method", "GET"), monitor["url"], timeout=timeout)
        status = resp.status_code
    except httpx.TimeoutException as e:
        error = f"Timeout after {timeout}s ({type(e).__name__})"
    except httpx.HTTPError as e:
        error = f"{type(e).__name__}: {e}".strip(": ")
    except Exception as e:  # invalid URL schemes etc.
        error = f"{type(e).__name__}: {e}"
    elapsed = round((time.perf_counter() - start) * 1000, 1)

    ok = error is None and status is not None and status_ok(status, expected)
    if error is None and not ok:
        error = f"HTTP {status} (expected {expected or '2xx/3xx'})"
    return {"status_code": status, "response_ms": elapsed, "ok": ok, "error": error}
