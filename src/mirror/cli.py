"""CLI management commands for sales-mirror-bot."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import sys
from datetime import datetime

from mirror.db import Database
from mirror.models import ConversationStage

logger = logging.getLogger(__name__)


async def list_conversations(stage: str | None = None) -> None:
    """Print a table of all conversations."""
    db = Database()
    await db.init()

    if stage:
        convs = await db.get_conversations_by_stage(ConversationStage(stage))
    else:
        convs = await db.get_all_conversations()

    if not convs:
        print("No conversations found.")
        await db.close()
        return

    # Header
    print(f"{'ID':>4}  {'Company':<30}  {'Stage':<18}  {'Contact':<20}  {'Budget':>15}  {'Updated'}")
    print("-" * 120)

    for c in convs:
        info = c.extracted_info
        budget = ""
        if info.budget_low:
            budget = f"¥{info.budget_low:,}"
            if info.budget_high:
                budget += f"~¥{info.budget_high:,}"

        print(
            f"{c.id:>4}  {c.company_name:<30}  {c.stage.value:<18}  "
            f"{info.contact_name:<20}  {budget:>15}  {c.updated_at:%Y-%m-%d %H:%M}"
        )

    print(f"\nTotal: {len(convs)} conversations")
    await db.close()


async def show_conversation(conv_id: int) -> None:
    """Show full detail of a single conversation."""
    db = Database()
    await db.init()

    # Find conversation
    all_convs = await db.get_all_conversations()
    conv = next((c for c in all_convs if c.id == conv_id), None)
    if not conv:
        print(f"Conversation #{conv_id} not found.")
        await db.close()
        return

    info = conv.extracted_info
    print(f"=== Conversation #{conv.id} ===")
    print(f"Company:  {conv.company_name}")
    print(f"Contact:  {info.contact_name} <{conv.email_from}>")
    print(f"Stage:    {conv.stage.value}")
    print(f"Platform: {info.platform or '-'}")
    print(f"Service:  {info.service_type or '-'}")
    budget = f"¥{info.budget_low:,}" if info.budget_low else "-"
    if info.budget_high:
        budget += f" ~ ¥{info.budget_high:,}"
    print(f"Budget:   {budget}")
    print(f"Created:  {conv.created_at:%Y-%m-%d %H:%M}")
    print(f"Updated:  {conv.updated_at:%Y-%m-%d %H:%M}")
    print()

    messages = await db.get_messages_for_conversation(conv_id)
    if messages:
        print(f"--- Messages ({len(messages)}) ---")
        for m in messages:
            direction = "← IN " if m["direction"] == "inbound" else "→ OUT"
            print(f"\n{direction}  {m['sent_at']}  {m['subject']}")
            print("-" * 60)
            # Truncate long bodies
            body = m["body"] or ""
            if len(body) > 500:
                body = body[:500] + "...(truncated)"
            print(body)

    await db.close()


async def export_conversations(fmt: str = "json") -> None:
    """Export all conversations to JSON or CSV on stdout."""
    db = Database()
    await db.init()
    convs = await db.get_all_conversations()

    if fmt == "json":
        data = []
        for c in convs:
            messages = await db.get_messages_for_conversation(c.id)
            data.append({
                "id": c.id,
                "company_name": c.company_name,
                "email_from": c.email_from,
                "stage": c.stage.value,
                "extracted_info": c.extracted_info.model_dump(),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "message_count": len(messages),
                "messages": messages,
            })
        print(json.dumps(data, ensure_ascii=False, indent=2))

    elif fmt == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow([
            "id", "company_name", "contact_name", "email_from",
            "stage", "service_type", "budget_low", "budget_high",
            "platform", "created_at", "updated_at",
        ])
        for c in convs:
            info = c.extracted_info
            writer.writerow([
                c.id, c.company_name, info.contact_name, c.email_from,
                c.stage.value, info.service_type, info.budget_low,
                info.budget_high, info.platform,
                c.created_at.isoformat(), c.updated_at.isoformat(),
            ])

    await db.close()


async def process_stdin_email() -> None:
    """Read a raw email from stdin and process it in dry-run mode."""
    from mirror.bot import MirrorBot
    from mirror.mail.imap_client import _parse_message

    raw = sys.stdin.buffer.read()
    if not raw:
        print("No input on stdin. Pipe a raw email to this command.")
        return

    email = _parse_message(raw)
    print(f"Parsed: from={email.from_name} <{email.from_addr}>")
    print(f"Subject: {email.subject}")
    print()

    bot = MirrorBot()
    response = await bot.process_single(email)
    if response:
        print("=== Generated Response ===")
        print(response)
    else:
        print("(No response generated — email may not be classified as sales)")
