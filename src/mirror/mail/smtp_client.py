from __future__ import annotations

import logging
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

import aiosmtplib

from mirror.config import settings

logger = logging.getLogger(__name__)


class SmtpSender:
    async def send(
        self,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
    ) -> str:
        """Send an email and return the generated Message-ID."""
        message_id = f"<{uuid.uuid4()}@{settings.smtp_host}>"

        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((settings.bot_display_name, settings.bot_email))
        msg["To"] = to
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = message_id

        # Threading headers — critical for email thread continuity
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = " ".join(references)

        msg.attach(MIMEText(body, "plain", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )

        logger.info("Sent email to %s: %s (ID: %s)", to, subject, message_id)
        return message_id
