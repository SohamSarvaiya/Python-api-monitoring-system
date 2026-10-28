"""Settings are read from environment (.env supported) on every call, which keeps tests simple."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int(name: str, default: int) -> int:
    try:
        return int(_str(name, str(default)) or default)
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    db_path: str
    enable_scheduler: bool
    seed_demo: bool
    failure_threshold: int
    retention_days: int
    alert_webhook_url: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    alert_email_to: str
    ai_provider: str
    ai_min_failures: int
    ai_timeout: int
    anthropic_api_key: str
    anthropic_model: str
    openai_api_key: str
    openai_model: str
    gemini_api_key: str
    gemini_model: str


def get_settings() -> Settings:
    return Settings(
        db_path=_str("DB_PATH", "data/monitor.db"),
        enable_scheduler=_bool("ENABLE_SCHEDULER", True),
        seed_demo=_bool("SEED_DEMO", True),
        failure_threshold=max(1, _int("FAILURE_THRESHOLD", 3)),
        retention_days=max(1, _int("RETENTION_DAYS", 30)),
        alert_webhook_url=_str("ALERT_WEBHOOK_URL"),
        smtp_host=_str("SMTP_HOST"),
        smtp_port=_int("SMTP_PORT", 587),
        smtp_user=_str("SMTP_USER"),
        smtp_password=_str("SMTP_PASSWORD"),
        smtp_from=_str("SMTP_FROM"),
        alert_email_to=_str("ALERT_EMAIL_TO"),
        ai_provider=_str("AI_PROVIDER", "auto").lower() or "auto",
        ai_min_failures=max(1, _int("AI_MIN_FAILURES", 3)),
        ai_timeout=_int("AI_TIMEOUT", 60),
        anthropic_api_key=_str("ANTHROPIC_API_KEY"),
        anthropic_model=_str("ANTHROPIC_MODEL", "claude-haiku-5-5"),
        openai_api_key=_str("OPENAI_API_KEY"),
        openai_model=_str("OPENAI_MODEL", "gpt-4o-mini"),
        gemini_api_key=_str("GEMINI_API_KEY") or _str("GOOGLE_API_KEY"),
        gemini_model=_str("GEMINI_MODEL", "gemini-flash-latest"),
    )
