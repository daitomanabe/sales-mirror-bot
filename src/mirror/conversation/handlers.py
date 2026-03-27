from __future__ import annotations

import logging
from datetime import datetime

from mirror.config import settings
from mirror.conversation.state_machine import ConversationStateMachine
from mirror.documents.contract_generator import ContractGenerator
from mirror.documents.invoice_generator import InvoiceGenerator
from mirror.llm.openai_client import LlmClient
from mirror.models import Conversation, ConversationStage, ParsedEmail

logger = logging.getLogger(__name__)


class StageHandler:
    def __init__(self) -> None:
        self._llm = LlmClient()
        self._contract_gen = ContractGenerator()
        self._invoice_gen = InvoiceGenerator()

    async def handle_inbound(
        self, conv: Conversation, email: ParsedEmail
    ) -> tuple[str, str]:
        """Handle an inbound email and produce a reply (subject, body)."""
        # Record inbound in history
        conv.history.append({
            "direction": "inbound",
            "stage": conv.stage.value,
            "body": email.body,
            "subject": email.subject,
            "from": email.from_addr,
            "at": datetime.now().isoformat(),
        })

        # Check if we should advance stage
        if ConversationStateMachine.can_advance(conv):
            ConversationStateMachine.advance(conv)

        # Generate response based on current stage
        body = await self._llm.generate_response(conv, latest_email=email)

        # Attach documents at specific stages
        if conv.stage == ConversationStage.CONTRACT:
            contract = self._contract_gen.generate(conv)
            body += "\n\n" + "=" * 40 + "\n【業務委託契約書（ドラフト）】\n" + "=" * 40 + "\n\n" + contract

        elif conv.stage == ConversationStage.BILLING:
            amount = conv.extracted_info.budget_low or 2_000_000
            invoice = self._invoice_gen.generate(conv, amount)
            body += "\n\n" + "=" * 40 + "\n【請求書】\n" + "=" * 40 + "\n\n" + invoice

        # Build reply subject
        subject = self._build_subject(email.subject, conv.stage)

        # Record outbound in history
        conv.history.append({
            "direction": "outbound",
            "stage": conv.stage.value,
            "body": body,
            "subject": subject,
            "at": datetime.now().isoformat(),
        })

        # Set follow-up timer
        delay = ConversationStateMachine.get_follow_up_delay(conv.stage)
        conv.next_action_at = datetime.now() + delay
        conv.updated_at = datetime.now()

        return subject, body

    async def handle_follow_up(self, conv: Conversation) -> tuple[str, str]:
        """Generate a follow-up email for a stale conversation."""
        body = await self._llm.generate_response(conv, is_follow_up=True)

        subject = f"Re: {conv.extracted_info.summary or 'ご相談の件'}"

        conv.history.append({
            "direction": "outbound",
            "stage": conv.stage.value,
            "body": body,
            "subject": subject,
            "at": datetime.now().isoformat(),
            "type": "follow_up",
        })

        # Reset follow-up timer
        delay = ConversationStateMachine.get_follow_up_delay(conv.stage)
        conv.next_action_at = datetime.now() + delay
        conv.updated_at = datetime.now()

        return subject, body

    @staticmethod
    def _build_subject(original_subject: str, stage: ConversationStage) -> str:
        """Build reply subject line."""
        clean = original_subject.strip()
        if not clean.lower().startswith("re:"):
            clean = f"Re: {clean}"
        return clean
