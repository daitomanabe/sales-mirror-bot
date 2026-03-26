from __future__ import annotations

import asyncio
import email
import email.header
import email.utils
import logging
from datetime import datetime

from aioimaplib import IMAP4_SSL

from mirror.config import settings
from mirror.models import ParsedEmail

logger = logging.getLogger(__name__)


def _decode_header(raw: str | None) -> str:
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return "".join(decoded)


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback to text/html if no text/plain
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        return ""


def _parse_references(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [ref.strip() for ref in raw.split() if ref.strip()]


def _parse_message(raw_bytes: bytes) -> ParsedEmail:
    msg = email.message_from_bytes(raw_bytes)
    from_name, from_addr = email.utils.parseaddr(msg.get("From", ""))
    _, to_addr = email.utils.parseaddr(msg.get("To", ""))

    date_str = msg.get("Date", "")
    try:
        received_at = email.utils.parsedate_to_datetime(date_str)
    except Exception:
        received_at = datetime.now()

    return ParsedEmail(
        message_id=msg.get("Message-ID", ""),
        from_addr=from_addr,
        from_name=_decode_header(from_name) or from_addr,
        to_addr=to_addr,
        subject=_decode_header(msg.get("Subject", "")),
        body=_extract_body(msg),
        received_at=received_at,
        in_reply_to=msg.get("In-Reply-To"),
        references=_parse_references(msg.get("References")),
    )


class ImapMonitor:
    def __init__(self) -> None:
        self._client: IMAP4_SSL | None = None

    async def connect(self) -> None:
        self._client = IMAP4_SSL(host=settings.imap_host, port=settings.imap_port)
        await self._client.wait_hello_from_server()
        await self._client.login(settings.imap_user, settings.imap_password)
        await self._client.select("INBOX")
        logger.info("IMAP connected to %s", settings.imap_host)

    async def poll_unseen(self) -> list[ParsedEmail]:
        if not self._client:
            await self.connect()

        _, data = await self._client.search("UNSEEN")
        if not data or not data[0]:
            return []

        uids = data[0].split()
        results: list[ParsedEmail] = []

        for uid in uids:
            try:
                _, msg_data = await self._client.fetch(uid.decode(), "(RFC822)")
                # msg_data is a list; the raw email is in the second element
                for item in msg_data:
                    if isinstance(item, tuple) and len(item) == 2:
                        raw_email = item[1]
                        if isinstance(raw_email, bytes):
                            parsed = _parse_message(raw_email)
                            results.append(parsed)
                            break
            except Exception:
                logger.exception("Failed to fetch/parse UID %s", uid)

        logger.info("Polled %d unseen messages", len(results))
        return results

    async def poll_loop(self, callback) -> None:
        """Run forever, polling for new emails and invoking callback for each."""
        while True:
            try:
                emails = await self.poll_unseen()
                for mail in emails:
                    try:
                        await callback(mail)
                    except Exception:
                        logger.exception("Error handling email %s", mail.message_id)
            except Exception:
                logger.exception("IMAP poll error, reconnecting...")
                self._client = None
                await asyncio.sleep(5)
                try:
                    await self.connect()
                except Exception:
                    logger.exception("Reconnection failed")

            await asyncio.sleep(settings.poll_interval_seconds)

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.logout()
            except Exception:
                pass
            self._client = None
