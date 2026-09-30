"""Email delivery service abstraction for NETRAKON AI.

Supports production SMTP delivery and safe local development email preview sink.
"""

import os
import smtplib
import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Outbox file for development email inspection
DEV_OUTBOX_PATH = Path(__file__).resolve().parent.parent.parent / "dev_email_outbox.log"


def send_password_reset_email(to_email: str, to_name: str, reset_token: str) -> bool:
    """Send password reset link email to requesting user's registered address."""
    frontend_base = settings.frontend_url.split(",")[0].rstrip("/")
    reset_url = f"{frontend_base}/reset-password?token={reset_token}"

    subject = "NetraKon AI — Password Reset Authorization"
    body_text = f"""Hello {to_name},

A password reset request for your NetraKon AI account ({to_email}) was approved by a Main Administrator.

Please use the secure link below to reset your password:
{reset_url}

Note:
- This link is valid for 15 minutes.
- This link can only be used once.
- If you did not request a password reset, please contact your Security Administrator immediately.

NetraKon AI Border Intelligence System
"""

    # 1. Production SMTP Flow (when SMTP host is configured)
    if settings.smtp_host:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            msg["To"] = f"{to_name} <{to_email}>"

            part = MIMEText(body_text, "plain")
            msg.attach(part)

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                server.ehlo()
                if settings.smtp_port == 587:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())

            logger.info("Password reset email dispatched successfully to registered user.")
            return True
        except Exception:
            logger.error("SMTP delivery failed for password reset request.")
            return False

    # 2. Local Development Email Preview Sink
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        preview_entry = (
            f"================================================================================\n"
            f"NETRAKON AI — DEVELOPMENT EMAIL OUTBOX PREVIEW\n"
            f"Timestamp   : {now_iso}\n"
            f"Target Email: {to_email} (User: {to_name})\n"
            f"From        : {settings.smtp_from_name} <{settings.smtp_from_email}>\n"
            f"Subject     : {subject}\n"
            f"--------------------------------------------------------------------------------\n"
            f"{body_text}"
            f"================================================================================\n\n"
        )
        with open(DEV_OUTBOX_PATH, "a", encoding="utf-8") as f:
            f.write(preview_entry)
        logger.info("Development email preview recorded in dev_email_outbox.log.")
        return True
    except Exception:
        logger.error("Failed to write development email preview outbox.")
        return False
