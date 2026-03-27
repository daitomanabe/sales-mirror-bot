from __future__ import annotations

from datetime import datetime, timedelta

from mirror.models import Conversation, ConversationStage

# Stage transition order
STAGE_ORDER: list[ConversationStage] = [
    ConversationStage.INITIAL_RESPONSE,
    ConversationStage.MEETING_SETUP,
    ConversationStage.PROPOSAL,
    ConversationStage.NEGOTIATION,
    ConversationStage.CONTRACT,
    ConversationStage.IMPLEMENTATION,
    ConversationStage.BILLING,
    ConversationStage.CLOSED,
]

# Minimum inbound messages needed before advancing from each stage
MIN_EXCHANGES_TO_ADVANCE: dict[ConversationStage, int] = {
    ConversationStage.INITIAL_RESPONSE: 1,
    ConversationStage.MEETING_SETUP: 1,
    ConversationStage.PROPOSAL: 1,
    ConversationStage.NEGOTIATION: 2,
    ConversationStage.CONTRACT: 1,
    ConversationStage.IMPLEMENTATION: 2,
    ConversationStage.BILLING: 1,
}

# Days without reply before sending follow-up
FOLLOW_UP_DELAYS: dict[ConversationStage, timedelta] = {
    ConversationStage.INITIAL_RESPONSE: timedelta(days=2),
    ConversationStage.MEETING_SETUP: timedelta(days=2),
    ConversationStage.PROPOSAL: timedelta(days=3),
    ConversationStage.NEGOTIATION: timedelta(days=3),
    ConversationStage.CONTRACT: timedelta(days=2),
    ConversationStage.IMPLEMENTATION: timedelta(days=5),
    ConversationStage.BILLING: timedelta(days=3),
}

# Days without any reply before abandoning the conversation
ABANDON_AFTER_DAYS = 14


class ConversationStateMachine:
    @staticmethod
    def next_stage(current: ConversationStage) -> ConversationStage | None:
        """Return the next stage in the pipeline, or None if terminal."""
        try:
            idx = STAGE_ORDER.index(current)
            if idx + 1 < len(STAGE_ORDER):
                return STAGE_ORDER[idx + 1]
        except ValueError:
            pass
        return None

    @staticmethod
    def count_inbound(conv: Conversation) -> int:
        """Count inbound messages at the current stage."""
        return sum(
            1
            for h in conv.history
            if h.get("direction") == "inbound" and h.get("stage") == conv.stage.value
        )

    @classmethod
    def can_advance(cls, conv: Conversation) -> bool:
        """Check if we have enough exchanges to move to the next stage."""
        if conv.stage in (ConversationStage.CLOSED, ConversationStage.DEAD):
            return False
        min_required = MIN_EXCHANGES_TO_ADVANCE.get(conv.stage, 1)
        return cls.count_inbound(conv) >= min_required

    @classmethod
    def advance(cls, conv: Conversation) -> Conversation:
        """Advance the conversation to the next stage if possible."""
        if not cls.can_advance(conv):
            return conv
        nxt = cls.next_stage(conv.stage)
        if nxt:
            conv.stage = nxt
            conv.next_action_at = datetime.now() + cls.get_follow_up_delay(nxt)
        return conv

    @staticmethod
    def should_abandon(conv: Conversation) -> bool:
        """Check if the conversation has gone stale."""
        if conv.stage in (ConversationStage.CLOSED, ConversationStage.DEAD):
            return False
        elapsed = datetime.now() - conv.updated_at
        return elapsed > timedelta(days=ABANDON_AFTER_DAYS)

    @staticmethod
    def get_follow_up_delay(stage: ConversationStage) -> timedelta:
        return FOLLOW_UP_DELAYS.get(stage, timedelta(days=3))
