import logging
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from . import db, reports, service
from .ai import analyzer, providers
from .config import get_settings
from .dashboard import DASHBOARD_HTML
from .scheduler import Scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DEMO_MONITORS = [
    ("GitHub API", "https://api.github.com", 30, None),
    ("Example.com", "https://example.com", 30, None),
    ("Always-failing demo (HTTP 500)", "https://httpbin.org/status/500", 15, None),
    ("Slow endpoint demo (3s delay)", "https://httpbin.org/delay/3", 30, None),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    s = get_settings()
    if s.seed_demo and not db.list_monitors():
        for name, url, interval, expected in DEMO_MONITORS:
            db.create_monitor(name, url, interval_seconds=interval, expected_status=expected)
    scheduler = Scheduler()
    if s.enable_scheduler:
        scheduler.start()
    app.state.scheduler = scheduler
    yield
    await scheduler.stop()


app = FastAPI(title="Python API Monitoring System", version="1.0.0", lifespan=lifespan)


class MonitorIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str
    method: Literal["GET", "HEAD", "POST"] = "GET"
    interval_seconds: int = Field(60, ge=5, le=86400)
    timeout_seconds: int = Field(10, ge=1, le=120)
    expected_status: Optional[int] = Field(None, ge=100, le=599)
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def _http_url(cls, v: str) -> str:
        v = v.strip()
        if not v.lower().startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v


def _monitor_or_404(monitor_id: int) -> dict:
    m = db.get_monitor(monitor_id)
    if not m:
        raise HTTPException(404, "Monitor not found")
    return m


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return DASHBOARD_HTML


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- monitors ----------
@app.post("/monitors", status_code=201)
def create_monitor(body: MonitorIn):
    return db.create_monitor(**body.model_dump())


@app.get("/monitors")
def list_monitors():
    return db.list_monitors()


@app.get("/monitors/{monitor_id}")
def get_monitor(monitor_id: int):
    return _monitor_or_404(monitor_id)


@app.delete("/monitors/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: int):
    if not db.delete_monitor(monitor_id):
        raise HTTPException(404, "Monitor not found")


@app.post("/monitors/{monitor_id}/pause")
def pause(monitor_id: int):
    _monitor_or_404(monitor_id)
    return db.set_enabled(monitor_id, False)


@app.post("/monitors/{monitor_id}/resume")
def resume(monitor_id: int):
    _monitor_or_404(monitor_id)
    return db.set_enabled(monitor_id, True)


@app.post("/monitors/{monitor_id}/check")
async def check_now(monitor_id: int):
    m = _monitor_or_404(monitor_id)
    return await service.check_and_record(m)


@app.get("/monitors/{monitor_id}/checks")
def get_checks(monitor_id: int, limit: int = Query(100, ge=1, le=1000)):
    _monitor_or_404(monitor_id)
    return db.get_checks(monitor_id, limit=limit, newest_first=True)


# ---------- alerts & reports ----------
@app.get("/alerts")
def get_alerts(limit: int = Query(50, ge=1, le=500), monitor_id: Optional[int] = None):
    return db.list_alerts(limit, monitor_id)


@app.get("/reports/uptime")
def uptime_all(hours: int = Query(24, ge=1, le=24 * 30)):
    return reports.all_reports(hours)


@app.get("/reports/uptime/{monitor_id}")
def uptime_one(monitor_id: int, hours: int = Query(24, ge=1, le=24 * 30)):
    return reports.uptime_report(_monitor_or_404(monitor_id), hours)


# ---------- AI ----------
@app.get("/ai/providers")
def ai_providers():
    return {"selected": get_settings().ai_provider, "providers": providers.configured_providers()}


@app.post("/monitors/{monitor_id}/analyze")
async def analyze_monitor(monitor_id: int,
                          provider: Optional[str] = Query(None, description="auto|anthropic|openai|gemini"),
                          hours: int = Query(24, ge=1, le=24 * 30),
                          language: Literal["en", "hi"] = "en"):
    m = _monitor_or_404(monitor_id)
    try:
        return await analyzer.analyze(m, provider=provider, hours=hours, language=language)
    except providers.AINotConfigured as e:
        raise HTTPException(400, str(e))
    except providers.AIError as e:
        raise HTTPException(502, str(e))
