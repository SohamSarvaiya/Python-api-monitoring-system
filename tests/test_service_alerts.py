import asyncio

from app import db, service

FAIL = {"status_code": 500, "response_ms": 12.0, "ok": False, "error": "HTTP 500"}
OK = {"status_code": 200, "response_ms": 30.0, "ok": True, "error": None}


def mk():
    return db.create_monitor("svc", "http://svc.test")


def test_down_alert_only_after_threshold_and_only_once():
    m = mk()
    assert service.record_result(m["id"], FAIL) is None
    assert service.record_result(m["id"], FAIL) is None
    a = service.record_result(m["id"], FAIL)
    assert a and a["kind"] == "DOWN"
    assert service.record_result(m["id"], FAIL) is None  # no alert storm
    assert db.get_monitor(m["id"])["state"] == "down"


def test_recovery_alert():
    m = mk()
    for _ in range(3):
        service.record_result(m["id"], FAIL)
    a = service.record_result(m["id"], OK)
    assert a and a["kind"] == "RECOVERED"
    assert db.get_monitor(m["id"])["state"] == "up"
    assert [x["kind"] for x in db.list_alerts()] == ["RECOVERED", "DOWN"]


def test_blip_below_threshold_resets_counter():
    m = mk()
    service.record_result(m["id"], FAIL)
    service.record_result(m["id"], OK)
    service.record_result(m["id"], FAIL)
    service.record_result(m["id"], FAIL)
    assert db.list_alerts() == []


def test_webhook_called_on_alert(monkeypatch):
    import httpx
    from app import alerts
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "http://hook.test/x")
    seen = []

    def handler(req):
        seen.append(req.content)
        return httpx.Response(200)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await alerts.notify({"kind": "DOWN", "message": "boom"}, client=c)

    assert asyncio.run(go()) == ["console", "webhook"] and seen
