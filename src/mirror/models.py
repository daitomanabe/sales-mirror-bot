from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationStage(str, enum.Enum):
    INITIAL_RESPONSE = "initial_response"
    MEETING_SETUP = "meeting_setup"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CONTRACT = "contract"
    IMPLEMENTATION = "implementation"
    BILLING = "billing"
    CLOSED = "closed"
    DEAD = "dead"


class ParsedEmail(BaseModel):
    message_id: str
    from_addr: str
    from_name: str
    to_addr: str = ""
    subject: str
    body: str
    received_at: datetime = Field(default_factory=datetime.now)
    in_reply_to: str | None = None
    references: list[str] = Field(default_factory=list)


class ExtractedInfo(BaseModel):
    company_name: str = ""
    contact_name: str = ""
    contact_email: str = ""
    service_type: str = ""
    budget_low: int | None = None
    budget_high: int | None = None
    platform: str = ""
    urgency: str = "normal"
    summary: str = ""


class Conversation(BaseModel):
    id: int | None = None
    thread_id: str = ""
    email_from: str = ""
    company_name: str = ""
    stage: ConversationStage = ConversationStage.INITIAL_RESPONSE
    extracted_info: ExtractedInfo = Field(default_factory=ExtractedInfo)
    history: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    next_action_at: datetime | None = None
    last_message_id: str | None = None


class GeneratedDocument(BaseModel):
    id: int | None = None
    conversation_id: int
    doc_type: str  # "contract" or "invoice"
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
