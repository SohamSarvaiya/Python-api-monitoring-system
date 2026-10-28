import asyncio
import json

import httpx
import pytest

from app import db, service
from app.ai import analyzer, providers

FAIL = {"status_code": 503, "response_ms": 40.0, "ok": False, "error": "HTTP 503 (expected 2xx/3xx)"}
GOOD_JSON = json.dumps({"summary": "s", "possible_causes": [], "troubleshooting_steps": [], "data_limitations": []})


def monitor_with_failures(n):
    m = db.create_monitor("svc", "http://svc.test")
    for _ in range(n):
        service.record_result(m["id"], FAIL)
    return db.get_monitor(m["id"])


def mock_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_insufficient_data_never_calls_ai(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    m = monitor_with_failures(2)

    def handler(req):
        raise AssertionError("AI must not be called with too little data")

    async def go():
        async with mock_client(handler) as c:
            return await analyzer.analyze(m, client=c)

    r = asyncio.run(go())
    assert r["status"] == "insufficient_data"


def test_no_key_raises_helpful_error():
    m = monitor_with_failures(3)
    with pytest.raises(providers.AINotConfigured):
        asyncio.run(analyzer.analyze(m))


def test_auto_picks_first_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert providers.resolve_provider() == "gemini"
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    assert providers.resolve_provider() == "openai"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    assert providers.resolve_provider() == "anthropic"
    assert providers.resolve_provider("gemini") == "gemini"


def test_anthropic_request_and_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    seen = {}

    def handler(req):
        seen["url"], seen["key"] = str(req.url), req.headers["x-api-key"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"content": [{"type": "text", "text": GOOD_JSON}]})

    m = monitor_with_failures(3)

    async def go():
        async with mock_client(handler) as c:
            return await analyzer.analyze(m, client=c)

    r = asyncio.run(go())
    assert r["status"] == "ok" and r["provider"] == "anthropic" and r["analysis"]["summary"] == "s"
    assert seen["url"] == "https://api.anthropic.com/v1/messages" and seen["key"] == "ak"
    assert "Never state a root cause as fact" in seen["body"]["system"]
    assert "disclaimer" in r and "NOT a confirmed root cause" in r["disclaimer"]


def test_openai_request_and_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "ok")
    seen = {}

    def handler(req):
        seen["url"], seen["auth"] = str(req.url), req.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "```json\n" + GOOD_JSON + "\n```"}}]})

    async def go():
        async with mock_client(handler) as c:
            return await providers.complete("openai", "sys", "usr", client=c)

    text = asyncio.run(go())
    assert seen["url"].endswith("/v1/chat/completions") and seen["auth"] == "Bearer ok"
    assert analyzer._parse_json(text)["summary"] == "s"  # fenced JSON still parsed


def test_gemini_request_and_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gk")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    seen = {}

    def handler(req):
        seen["url"], seen["key"] = str(req.url), req.headers["x-goog-api-key"]
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": GOOD_JSON}]}}]})

    async def go():
        async with mock_client(handler) as c:
            return await providers.complete("gemini", "sys", "usr", client=c)

    assert asyncio.run(go()) == GOOD_JSON
    assert seen["url"].endswith("/models/gemini-test:generateContent") and seen["key"] == "gk"
    assert "key=" not in seen["url"]  # key travels in a header, not the URL


def test_provider_http_error_is_readable(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "bad")

    def handler(req):
        return httpx.Response(401, json={"error": {"message": "Incorrect API key"}})

    async def go():
        async with mock_client(handler) as c:
            return await providers.complete("openai", "s", "u", client=c)

    with pytest.raises(providers.AIError, match="check the API key"):
        asyncio.run(go())


def test_non_json_reply_is_kept_as_raw_text(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    m = monitor_with_failures(3)

    def handler(req):
        return httpx.Response(200, json={"choices": [{"message": {"content": "plain words"}}]})

    async def go():
        async with mock_client(handler) as c:
            return await analyzer.analyze(m, client=c)

    assert asyncio.run(go())["analysis"] == {"raw_text": "plain words"}
