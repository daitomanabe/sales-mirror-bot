from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from mirror.config import settings
from mirror.conversation.handlers import StageHandler
from mirror.conversation.state_machine import ConversationStateMachine
from mirror.db import Database
from mirror.mail.imap_client import ImapMonitor
from mirror.mail.smtp_client import SmtpSender
from mirror.models import Conversation, ConversationStage, ParsedEmail
from mirror.parser.email_parser import EmailParser

logger = logging.getLogger(__name__)


class MirrorBot:
    def __init__(self) -> None:
        self._db = Database()
        self._imap = ImapMonitor()
        self._smtp = SmtpSender()
        self._parser = EmailParser()
        self._handler = StageHandler()

    async def start(self) -> None:
        """Start the bot: initialize DB and run poll + follow-up loops."""
        await self._db.init()
        if settings.dry_run:
            logger.info("MirrorBot starting in DRY-RUN mode (no emails will be sent)")
        else:
            logger.info("MirrorBot starting in LIVE mode")

        await asyncio.gather(
            self._imap.poll_loop(self._handle_email),
            self._follow_up_loop(),
        )

    async def process_single(self, email: ParsedEmail) -> str | None:
        """Process a single email and return the generated response (for testing).

        This always runs in dry-run mode regardless of settings.
        """
        await self._db.init()
        return await self._handle_email(email, force_dry_run=True)

    async def _handle_email(
        self, email: ParsedEmail, force_dry_run: bool = False
    ) -> str | None:
        """Core pipeline: parse → classify → find/create conversation → respond."""
        dry_run = settings.dry_run or force_dry_run

        logger.info(
            "Processing email from %s <%s>: %s",
            email.from_name,
            email.from_addr,
            email.subject,
        )

        # Step 1: Check if this is a sales email
        if not EmailParser.is_sales_email(email):
            logger.info("Skipping non-sales email: %s", email.subject)
            return None

        # Step 2: Extract structured info
        info = await self._parser.extract(email)
        logger.info(
            "Extracted: company=%s, contact=%s, budget=%s-%s, platform=%s",
            info.company_name,
            info.contact_name,
            info.budget_low,
            info.budget_high,
            info.platform,
        )

        # Step 3: Find or create conversation
        thread_id = self._resolve_thread_id(email)
        conv = await self._db.get_conversation_by_thread(thread_id)

        if conv is None:
            # Check active conversation limit
            active_stages = [
                s for s in ConversationStage
                if s not in (ConversationStage.CLOSED, ConversationStage.DEAD)
            ]
            active_count = 0
            for stage in active_stages:
                convs = await self._db.get_conversations_by_stage(stage)
                active_count += len(convs)

            if active_count >= settings.max_active_conversations:
                logger.warning(
                    "Max active conversations (%d) reached, skipping",
                    settings.max_active_conversations,
                )
                return None

            conv = Conversation(
                thread_id=thread_id,
                email_from=email.from_addr,
                company_name=info.company_name,
                extracted_info=info,
            )
            conv_id = await self._db.upsert_conversation(conv)
            conv.id = conv_id
            logger.info(
                "New conversation created: #%d with %s", conv_id, info.company_name
            )
        else:
            # Update extracted info if we got better data
            if info.budget_low and not conv.extracted_info.budget_low:
                conv.extracted_info = info
            logger.info(
                "Existing conversation #%d, stage=%s", conv.id, conv.stage.value
            )

        # Step 4: Generate response
        subject, body = await self._handler.handle_inbound(conv, email)
        signed_body = self._add_signature(body)

        # Step 5: Send via SMTP (or log in dry-run mode)
        if dry_run:
            logger.info(
                "DRY-RUN — Would send to: %s\nSubject: %s\n\n%s",
                email.from_addr,
                subject,
                signed_body,
            )
            new_message_id = f"<dry-run-{uuid.uuid4()}@mirror>"
        else:
            references = list(email.references)
            if email.message_id:
                references.append(email.message_id)

            new_message_id = await self._smtp.send(
                to=email.from_addr,
                subject=subject,
                body=signed_body,
                in_reply_to=email.message_id,
                references=references,
            )

        conv.last_message_id = new_message_id

        # Step 6: Persist conversation and message records
        await self._db.upsert_conversation(conv)
        await self._db.add_message(
            conv.id, "inbound", email.subject, email.body, email.message_id
        )
        await self._db.add_message(
            conv.id, "outbound", subject, body, new_message_id
        )

        logger.info(
            "Replied to %s [stage=%s]: %s",
            email.from_addr,
            conv.stage.value,
            subject,
        )
        return body

    async def _follow_up_loop(self) -> None:
        """Periodically check for stale conversations and send follow-ups."""
        while True:
            await asyncio.sleep(3600)  # Check every hour
            try:
                pending = await self._db.get_pending_actions(datetime.now())
                for conv in pending:
                    if ConversationStateMachine.should_abandon(conv):
                        conv.stage = ConversationStage.DEAD
                        await self._db.upsert_conversation(conv)
                        logger.info("Abandoned conversation #%d", conv.id)
                        continue

                    subject, body = await self._handler.handle_follow_up(conv)

                    if settings.dry_run:
                        logger.info(
                            "DRY-RUN follow-up for #%d:\n%s\n%s",
                            conv.id,
                            subject,
                            body,
                        )
                        new_message_id = f"<dry-run-{uuid.uuid4()}@mirror>"
                    else:
                        references = []
                        if conv.last_message_id:
                            references.append(conv.last_message_id)

                        new_message_id = await self._smtp.send(
                            to=conv.email_from,
                            subject=subject,
                            body=self._add_signature(body),
                            in_reply_to=conv.last_message_id,
                            references=references,
                        )

                    conv.last_message_id = new_message_id
                    await self._db.upsert_conversation(conv)
                    await self._db.add_message(
                        conv.id, "outbound", subject, body, new_message_id
                    )
                    logger.info("Follow-up sent for conversation #%d", conv.id)

            except Exception:
                logger.exception("Error in follow-up loop")

    @staticmethod
    def _resolve_thread_id(email: ParsedEmail) -> str:
        """Determine the thread ID from email headers."""
        if email.references:
            return email.references[0]
        if email.in_reply_to:
            return email.in_reply_to
        return email.message_id

    @staticmethod
    def _add_signature(body: str) -> str:
        """Append standard email signature."""
        return (
            f"{body}\n\n"
            f"--\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{settings.bot_company_name}\n"
            f"{settings.bot_title}　{settings.bot_display_name}\n"
            f"Email: {settings.bot_email}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )
