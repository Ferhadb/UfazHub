"""Outbound email: enqueue an arq job; the worker sends via SMTP (or logs it in dev)."""

import logging
import smtplib
from email.message import EmailMessage

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

log = logging.getLogger("app.mail")
outbox: list[dict] = []  # APP_ENV=test captures mail here instead of enqueuing


async def send_mail(to: str, subject: str, body: str) -> None:
    msg = {"to": to, "subject": subject, "body": body}
    if settings.APP_ENV == "test":
        outbox.append(msg)
        return
    if settings.is_dev and not settings.SMTP_USERNAME:
        deliver(to, subject, body)  # dev without SMTP: log the link, no worker needed
        return
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await pool.enqueue_job("send_email", **msg)
        await pool.aclose()
    except Exception:  # a mail outage must not fail signup; the user can resend
        log.exception("could not enqueue email to %s", to)


def deliver(to: str, subject: str, body: str) -> None:
    """Blocking SMTP send; the arq job runs it in a thread. Logged when SMTP is unconfigured."""
    if not settings.SMTP_USERNAME:
        log.info("email (not sent, SMTP unset) to=%s subject=%s\n%s", to, subject, body)
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = settings.MAIL_FROM, to, subject
    m.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
        s.starttls()
        s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        s.send_message(m)
