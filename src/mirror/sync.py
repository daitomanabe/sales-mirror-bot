"""Sync local SQLite data to the Cloudflare D1 dashboard."""
from __future__ import annotations

import json
import logging

import httpx

from mirror.config import settings
from mirror.db import Database

logger = logging.getLogger(__name__)


class DashboardSync:
    """Push conversation data from local SQLite to the Cloudflare dashboard API."""

    def __init__(self, dashboard_url: str, api_token: str) -> None:
        self._url = dashboard_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_token}"}

    async def sync_all(self, db: Database) -> None:
        """Push all conversations and messages to the dashboard."""
        try:
            await self._sync_conversations(db)
            await self._sync_messages(db)
            logger.info("Dashboard sync completed")
        except Exception:
            logger.exception("Dashboard sync failed")

    async def _sync_conversations(self, db: Database) -> None:
        rows = []
        async with db._db.execute("SELECT * FROM conversations") as cursor:
            async for row in cursor:
                rows.append({
                    "id": row["id"],
                    "thread_id": row["thread_id"],
                    "email_from": row["email_from"],
                    "company_name": row["company_name"],
                    "stage": row["stage"],
                    "extracted_info_json": row["extracted_info_json"],
                    "history_json": row["history_json"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "next_action_at": row["next_action_at"],
                    "last_message_id": row["last_message_id"],
                })

        if rows:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._url}/api/sync/conversations",
                    json={"conversations": rows},
                    headers=self._headers,
                    timeout=30,
                )
                resp.raise_for_status()
                logger.info("Synced %d conversations", len(rows))

    async def _sync_messages(self, db: Database) -> None:
        rows = []
        async with db._db.execute("SELECT * FROM messages") as cursor:
            async for row in cursor:
                rows.append({
                    "id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "direction": row["direction"],
                    "subject": row["subject"],
                    "body": row["body"],
                    "message_id": row["message_id"],
                    "sent_at": row["sent_at"],
                })

        if rows:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._url}/api/sync/messages",
                    json={"messages": rows},
                    headers=self._headers,
                    timeout=30,
                )
                resp.raise_for_status()
                logger.info("Synced %d messages", len(rows))
