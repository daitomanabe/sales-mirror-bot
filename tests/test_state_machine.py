from datetime import datetime, timedelta

from mirror.conversation.state_machine import ConversationStateMachine
from mirror.models import Conversation, ConversationStage, ExtractedInfo


def _make_conv(
    stage: ConversationStage = ConversationStage.INITIAL_RESPONSE,
    inbound_count: int = 0,
) -> Conversation:
    """Create a test conversation with N inbound messages at the given stage."""
    history = []
    for i in range(inbound_count):
        history.append({
            "direction": "inbound",
            "stage": stage.value,
            "body": f"Test message {i}",
        })
    return Conversation(
        id=1,
        thread_id="<test@example.com>",
        email_from="test@example.com",
        company_name="Test Co",
        stage=stage,
        extracted_info=ExtractedInfo(),
        history=history,
        updated_at=datetime.now(),
    )


def test_next_stage():
    sm = ConversationStateMachine
    assert sm.next_stage(ConversationStage.INITIAL_RESPONSE) == ConversationStage.MEETING_SETUP
    assert sm.next_stage(ConversationStage.MEETING_SETUP) == ConversationStage.PROPOSAL
    assert sm.next_stage(ConversationStage.PROPOSAL) == ConversationStage.NEGOTIATION
    assert sm.next_stage(ConversationStage.NEGOTIATION) == ConversationStage.CONTRACT
    assert sm.next_stage(ConversationStage.CONTRACT) == ConversationStage.IMPLEMENTATION
    assert sm.next_stage(ConversationStage.IMPLEMENTATION) == ConversationStage.BILLING
    assert sm.next_stage(ConversationStage.BILLING) == ConversationStage.CLOSED
    assert sm.next_stage(ConversationStage.CLOSED) is None


def test_can_advance_with_enough_exchanges():
    conv = _make_conv(ConversationStage.INITIAL_RESPONSE, inbound_count=1)
    assert ConversationStateMachine.can_advance(conv) is True


def test_cannot_advance_without_exchanges():
    conv = _make_conv(ConversationStage.INITIAL_RESPONSE, inbound_count=0)
    assert ConversationStateMachine.can_advance(conv) is False


def test_negotiation_needs_two_exchanges():
    conv = _make_conv(ConversationStage.NEGOTIATION, inbound_count=1)
    assert ConversationStateMachine.can_advance(conv) is False

    conv = _make_conv(ConversationStage.NEGOTIATION, inbound_count=2)
    assert ConversationStateMachine.can_advance(conv) is True


def test_advance_changes_stage():
    conv = _make_conv(ConversationStage.INITIAL_RESPONSE, inbound_count=1)
    ConversationStateMachine.advance(conv)
    assert conv.stage == ConversationStage.MEETING_SETUP


def test_cannot_advance_dead():
    conv = _make_conv(ConversationStage.DEAD, inbound_count=5)
    assert ConversationStateMachine.can_advance(conv) is False


def test_should_abandon_stale():
    conv = _make_conv()
    conv.updated_at = datetime.now() - timedelta(days=15)
    assert ConversationStateMachine.should_abandon(conv) is True


def test_should_not_abandon_recent():
    conv = _make_conv()
    conv.updated_at = datetime.now() - timedelta(days=1)
    assert ConversationStateMachine.should_abandon(conv) is False
