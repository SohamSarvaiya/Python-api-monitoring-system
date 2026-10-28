import httpx
import pytest
from fastapi.testclient import TestClient

from app import checker
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def patch_transport(monkeypatch, handler):
    monkeypatch.setattr(checker, "make_client",
                        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def test_health_and_dashboard(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert "API Monitoring System" in client.get("/").text


def test_monitor_crud_and_validation(client):
    r = client.post("/monitors", json={"name": "a", "url": "https://x.test"})
    assert r.status_code == 201
    mid = r.json()["id"]
    assert client.post("/monitors", json={"name": "bad", "url": "ftp://x"}).status_code == 422
    assert client.post("/monitors", json={"name": "bad", "url": "https://x", "interval_seconds": 1}).status_code == 422
    assert len(client.get("/monitors").json()) == 1
    assert client.post(f"/monitors/{mid}/pause").json()["enabled"] is False
    assert client.delete(f"/monitors/{mid}").status_code == 204
    assert client.get(f"/monitors/{mid}").status_code == 404


def test_check_now_alert_flow_and_report(client, monkeypatch):
    state = {"code": 500}
    patch_transport(monkeypatch, lambda req: httpx.Response(state["code"]))
    mid = client.post("/monitors", json={"name": "svc", "url": "https://svc.test"}).json()["id"]

    results = [client.post(f"/monitors/{mid}/check").json() for _ in range(3)]
    assert [r["alert"] for r in results] == [None, None, "DOWN"]

    state["code"] = 200
    assert client.post(f"/monitors/{mid}/check").json()["alert"] == "RECOVERED"

    assert [a["kind"] for a in client.get("/alerts").json()] == ["RECOVERED", "DOWN"]
    rep = client.get(f"/reports/uptime/{mid}").json()
    assert rep["total_checks"] == 4 and rep["uptime_percent"] == 25.0
    assert len(client.get(f"/monitors/{mid}/checks").json()) == 4


def test_analyze_endpoint_messages(client, monkeypatch):
    patch_transport(monkeypatch, lambda req: httpx.Response(500))
    mid = client.post("/monitors", json={"name": "svc", "url": "https://svc.test"}).json()["id"]
    r = client.post(f"/monitors/{mid}/analyze")
    assert r.json()["status"] == "insufficient_data"
    for _ in range(3):
        client.post(f"/monitors/{mid}/check")
    r = client.post(f"/monitors/{mid}/analyze")
    assert r.status_code == 400 and "API key" in r.json()["detail"]
    assert client.get("/ai/providers").json()["providers"]["openai"]["configured"] is False
