from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool

from openclaw_da.config import get_settings


def _outbox_dir() -> Path:
    settings = get_settings()
    path = settings.openclaw_workspace / "outbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


@tool
def list_recent_emails(limit: int = 10) -> str:
    """List recent emails. MVP implementation reads local sample files instead of Gmail."""
    sample = [
        {
            "from": "boss@example.com",
            "subject": "Project status",
            "snippet": "Please send me today's project status before 5pm.",
        },
        {
            "from": "billing@example.com",
            "subject": "Invoice reminder",
            "snippet": "Your invoice is due in 3 days.",
        },
    ]
    return "\n".join(
        f"{i+1}. From: {m['from']} | Subject: {m['subject']} | {m['snippet']}"
        for i, m in enumerate(sample[:limit])
    )


@tool
def create_email_draft(to: str, subject: str, body: str) -> str:
    """Create an email draft in the local outbox. Use before sending emails."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path = _outbox_dir() / f"draft-{ts}.eml"
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg["From"] = get_settings().smtp_from or "openclaw-da@example.local"
    msg.set_content(body)
    file_path.write_text(msg.as_string(), encoding="utf-8")
    return f"Draft saved: {file_path},调用send_email发送邮件"


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    settings = get_settings()
    if not settings.openclaw_allow_send:
        return create_email_draft.invoke({"to": to, "subject": subject, "body": body}) + (
            "\nSafe mode is ON, so the email was NOT sent. Set OPENCLAW_ALLOW_SEND=true to enable SMTP sending."
        )

    required = [settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from]
    if not all(required):
        return "SMTP is not configured. Email was not sent."

    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)

    return f"Email sent to {to} with subject: {subject}"
