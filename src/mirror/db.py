from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import aiosqlite

from mirror.config import settings
from mirror.models import (
    Conversation,
    ConversationStage,
    ExtractedInfo,
    GeneratedDocument,
)

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT UNIQUE NOT NULL,
    email_from TEXT NOT NULL,
    company_name TEXT NOT NULL DEFAULT '',
    stage TEXT NOT NULL DEFAULT 'initial_response',
    extracted_info_json TEXT NOT NULL DEFAULT '{}',
    history_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    next_action_at TEXT,
    last_message_id TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    direction TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    message_id TEXT,
    sent_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
"""


class Database:
    def __init__(self, db_path: str | None = None):
        self._path = db_path or settings.database_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()
        logger.info("Database initialized at %s", self._path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    # ── Conversations ──────────────────────────────────────────

    async def upsert_conversation(self, conv: Conversation) -> int:
        now = datetime.now().isoformat()
        if conv.id is None:
            cursor = await self._db.execute(
                """INSERT INTO conversations
                   (thread_id, email_from, company_name, stage,
                    extracted_info_json, history_json,
                    created_at, updated_at, next_action_at, last_message_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    conv.thread_id,
                    conv.email_from,
                    conv.company_name,
                    conv.stage.value,
                    conv.extracted_info.model_dump_json(),
                    json.dumps(conv.history, ensure_ascii=False),
                    conv.created_at.isoformat(),
                    now,
                    conv.next_action_at.isoformat() if conv.next_action_at else None,
                    conv.last_message_id,
                ),
            )
            await self._db.commit()
            return cursor.lastrowid
        else:
            await self._db.execute(
                """UPDATE conversations SET
                   stage=?, extracted_info_json=?, history_json=?,
                   updated_at=?, next_action_at=?, last_message_id=?
                   WHERE id=?""",
                (
                    conv.stage.value,
                    conv.extracted_info.model_dump_json(),
                    json.dumps(conv.history, ensure_ascii=False),
                    now,
                    conv.next_action_at.isoformat() if conv.next_action_at else None,
                    conv.last_message_id,
                    conv.id,
                ),
            )
            await self._db.commit()
            return conv.id

    async def get_conversation_by_thread(self, thread_id: str) -> Conversation | None:
        async with self._db.execute(
            "SELECT * FROM conversations WHERE thread_id=?", (thread_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_conversation(row)

    async def get_conversations_by_stage(
        self, stage: ConversationStage
    ) -> list[Conversation]:
        async with self._db.execute(
            "SELECT * FROM conversations WHERE stage=?", (stage.value,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_conversation(r) for r in rows]

    async def get_pending_actions(self, before: datetime) -> list[Conversation]:
        async with self._db.execute(
            """SELECT * FROM conversations
               WHERE next_action_at IS NOT NULL AND next_action_at <= ?
               AND stage NOT IN ('closed', 'dead')""",
            (before.isoformat(),),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_conversation(r) for r in rows]

    # ── Messages ───────────────────────────────────────────────

    async def add_message(
        self,
        conversation_id: int,
        direction: str,
        subject: str,
        body: str,
        message_id: str | None = None,
    ) -> None:
        await self._db.execute(
            """INSERT INTO messages
               (conversation_id, direction, subject, body, message_id, sent_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                conversation_id,
                direction,
                subject,
                body,
                message_id,
                datetime.now().isoformat(),
            ),
        )
        await self._db.commit()

    # ── Documents ──────────────────────────────────────────────

    async def save_document(self, doc: GeneratedDocument) -> int:
        cursor = await self._db.execute(
            """INSERT INTO documents
               (conversation_id, doc_type, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                doc.conversation_id,
                doc.doc_type,
                doc.content,
                doc.created_at.isoformat(),
            ),
        )
        await self._db.commit()
        return cursor.lastrowid

    # ── Dedup / Rate Limiting ─────────────────────────────────

    async def has_message(self, message_id: str) -> bool:
        """Check if we've already processed a message with this ID."""
        async with self._db.execute(
            "SELECT 1 FROM messages WHERE message_id = ? LIMIT 1", (message_id,)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def count_outbound_since(self, since: datetime) -> int:
        """Count outbound messages sent since a given time (for rate limiting)."""
        async with self._db.execute(
            """SELECT COUNT(*) as cnt FROM messages
               WHERE direction = 'outbound' AND sent_at >= ?""",
            (since.isoformat(),),
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def get_all_conversations(self) -> list[Conversation]:
        """Return all conversations (for export)."""
        async with self._db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_conversation(r) for r in rows]

    async def get_messages_for_conversation(
        self, conversation_id: int
    ) -> list[dict]:
        """Return all messages for a conversation."""
        async with self._db.execute(
            """SELECT * FROM messages WHERE conversation_id = ?
               ORDER BY sent_at ASC""",
            (conversation_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _row_to_conversation(row) -> Conversation:
        return Conversation(
            id=row["id"],
            thread_id=row["thread_id"],
            email_from=row["email_from"],
            company_name=row["company_name"],
            stage=ConversationStage(row["stage"]),
            extracted_info=ExtractedInfo.model_validate_json(
                row["extracted_info_json"]
            ),
            history=json.loads(row["history_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            next_action_at=(
                datetime.fromisoformat(row["next_action_at"])
                if row["next_action_at"]
                else None
            ),
            last_message_id=row["last_message_id"],
        )
