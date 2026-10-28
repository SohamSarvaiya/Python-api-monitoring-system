"""Alert delivery. Console log + DB row are always on; webhook and email are opt-in."""
import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

import httpx

from .config import get_settings

log = logging.getLogger("monitor.alerts")


async def notify(alert: dict, client: Optional[httpx.AsyncClient] = None) -> list[str]:
    """Deliver an alert to every configured channel. Returns the channels that worked."""
    s = get_settings()
    delivered = ["console"]
    log.warning("ALERT [%s] %s", alert["kind"], alert["message"])

    if s.alert_webhook_url:
        try:
            payload = {"text": alert["message"], "content": alert["message"], "kind": alert["kind"]}
            if client is None:
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.post(s.alert_webhook_url, json=payload)
            else:
                r = await client.post(s.alert_webhook_url, json=payload, timeout=10)
            r.raise_for_status()
            delivered.append("webhook")
        except Exception as e:
            log.error("Webhook delivery failed: %s", e)

    if s.smtp_host and s.alert_email_to:
        try:
            await asyncio.to_thread(_send_email, alert)
            delivered.append("email")
        except Exception as e:
            log.error("Email delivery failed: %s", e)
    return delivered


def _send_email(alert: dict) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["Subject"] = f"[API Monitor] {alert['kind']}: {alert.get('monitor_name', '')}".strip()
    msg["From"] = s.smtp_from or s.smtp_user
    msg["To"] = s.alert_email_to
    msg.set_content(alert["message"])
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
