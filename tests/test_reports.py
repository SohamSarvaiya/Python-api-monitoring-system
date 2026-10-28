from app import db, reports, service

OK = {"status_code": 200, "response_ms": 100.0, "ok": True, "error": None}
FAIL = {"status_code": None, "response_ms": 5000.0, "ok": False, "error": "Timeout after 5s (ReadTimeout)"}


def test_uptime_and_latency():
    m = db.create_monitor("svc", "http://svc.test")
    for r in [OK, OK, OK, FAIL]:
        service.record_result(m["id"], r)
    rep = reports.uptime_report(db.get_monitor(m["id"]), 24)
    assert rep["total_checks"] == 4 and rep["uptime_percent"] == 75.0
    assert rep["latency_ms"]["avg"] == 100.0
    assert rep["error_breakdown"] == {"Timeout after 5s (ReadTimeout)": 1}
    assert len(rep["incidents"]) == 1 and rep["incidents"][0]["ongoing"] is True


def test_empty_report_has_no_fake_numbers():
    m = db.create_monitor("svc", "http://svc.test")
    rep = reports.uptime_report(m, 24)
    assert rep["uptime_percent"] is None and rep["latency_ms"]["avg"] is None
