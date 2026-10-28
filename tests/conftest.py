import pytest

from app import db


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ENABLE_SCHEDULER", "false")
    monkeypatch.setenv("SEED_DEMO", "false")
    monkeypatch.setenv("FAILURE_THRESHOLD", "3")
    monkeypatch.setenv("AI_MIN_FAILURES", "3")
    monkeypatch.setenv("AI_PROVIDER", "auto")
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
                "ALERT_WEBHOOK_URL", "SMTP_HOST", "ALERT_EMAIL_TO"):
        monkeypatch.delenv(var, raising=False)
    db.init_db()
    yield
