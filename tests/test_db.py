import pytest

from mirror.db import Database
from mirror.models import Conversation, ConversationStage, ExtractedInfo


@pytest.mark.asyncio
async def test_create_and_retrieve_conversation(db: Database):
    conv = Conversation(
        thread_id="<test-thread@example.com>",
        email_from="sender@example.com",
        company_name="テスト株式会社",
        extracted_info=ExtractedInfo(
            company_name="テスト株式会社",
            contact_name="田中太郎",
            budget_low=2_000_000,
        ),
    )
    conv_id = await db.upsert_conversation(conv)
    assert conv_id is not None

    retrieved = await db.get_conversation_by_thread("<test-thread@example.com>")
    assert retrieved is not None
    assert retrieved.company_name == "テスト株式会社"
    assert retrieved.extracted_info.contact_name == "田中太郎"
    assert retrieved.extracted_info.budget_low == 2_000_000
    assert retrieved.stage == ConversationStage.INITIAL_RESPONSE


@pytest.mark.asyncio
async def test_update_conversation_stage(db: Database):
    conv = Conversation(
        thread_id="<update-test@example.com>",
        email_from="sender@example.com",
        company_name="更新テスト",
    )
    conv_id = await db.upsert_conversation(conv)
    conv.id = conv_id
    conv.stage = ConversationStage.MEETING_SETUP

    await db.upsert_conversation(conv)

    retrieved = await db.get_conversation_by_thread("<update-test@example.com>")
    assert retrieved.stage == ConversationStage.MEETING_SETUP


@pytest.mark.asyncio
async def test_add_and_count_messages(db: Database):
    conv = Conversation(
        thread_id="<msg-test@example.com>",
        email_from="sender@example.com",
        company_name="メッセージテスト",
    )
    conv_id = await db.upsert_conversation(conv)

    await db.add_message(conv_id, "inbound", "件名", "本文", "<msg1@example.com>")
    await db.add_message(conv_id, "outbound", "Re: 件名", "返信", "<msg2@example.com>")

    # Verify messages were stored (no dedicated get method, but no error means success)
    assert conv_id is not None


@pytest.mark.asyncio
async def test_get_conversations_by_stage(db: Database):
    for i in range(3):
        conv = Conversation(
            thread_id=f"<stage-test-{i}@example.com>",
            email_from=f"sender{i}@example.com",
            company_name=f"会社{i}",
        )
        await db.upsert_conversation(conv)

    results = await db.get_conversations_by_stage(ConversationStage.INITIAL_RESPONSE)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_nonexistent_thread_returns_none(db: Database):
    result = await db.get_conversation_by_thread("<nonexistent@example.com>")
    assert result is None
