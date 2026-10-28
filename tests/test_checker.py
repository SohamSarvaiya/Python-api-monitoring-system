import asyncio

import httpx

from app import checker


def run(handler, monitor):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await checker.run_check(c, monitor)
    return asyncio.run(go())


M = {"url": "http://svc.test/health", "method": "GET", "timeout_seconds": 5, "expected_status": None}


def test_success():
    r = run(lambda req: httpx.Response(200), M)
    assert r["ok"] and r["status_code"] == 200 and r["error"] is None and r["response_ms"] >= 0


def test_http_500_is_failure_and_logged():
    r = run(lambda req: httpx.Response(500), M)
    assert not r["ok"] and r["status_code"] == 500 and "HTTP 500" in r["error"]


def test_expected_status_respected():
    assert run(lambda req: httpx.Response(404), {**M, "expected_status": 404})["ok"]
    assert not run(lambda req: httpx.Response(200), {**M, "expected_status": 204})["ok"]


def test_timeout_becomes_data():
    def h(req):
        raise httpx.ReadTimeout("slow", request=req)
    r = run(h, M)
    assert not r["ok"] and r["status_code"] is None and "Timeout" in r["error"]


def test_connect_error_becomes_data():
    def h(req):
        raise httpx.ConnectError("dns failure", request=req)
    r = run(h, M)
    assert not r["ok"] and "ConnectError" in r["error"]
