from __future__ import annotations

import logging
from pathlib import Path

from openai import AsyncOpenAI

from mirror.config import settings
from mirror.models import Conversation, ConversationStage, ParsedEmail

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.warning("Prompt file not found: %s", path)
    return ""


# Stage-specific instruction overlays
STAGE_INSTRUCTIONS: dict[ConversationStage, str] = {
    ConversationStage.INITIAL_RESPONSE: (
        "これは最初の返信です。強い興味を示し、具体的なサービス内容や案件について"
        "詳しく聞いてください。打ち合わせの可能性を示唆してください。"
        "丁寧かつ前向きなビジネストーンで。"
    ),
    ConversationStage.MEETING_SETUP: (
        "打ち合わせの日程調整をしてください。"
        "来週の候補日を2-3提示し、オンライン会議（Zoom/Google Meet）を提案してください。"
        "具体的な時間帯を挙げてください。"
    ),
    ConversationStage.PROPOSAL: (
        "提案内容を確認し、前向きに検討していることを伝えてください。"
        "具体的な要件や期待するスコープについて質問してください。"
        "見積もりや提案書の提出を依頼してください。"
    ),
    ConversationStage.NEGOTIATION: (
        "価格交渉のフェーズです。提示された金額に対し、"
        "若干の値引きまたは追加サービスを求めてください。"
        "ただし、合理的な範囲で。2回目のやりとりで合意に近づけてください。"
    ),
    ConversationStage.CONTRACT: (
        "条件に合意し、契約の準備に進みましょう。"
        "契約書のドラフトを送付する旨を伝えてください。"
        "電子署名での締結を提案してください。"
    ),
    ConversationStage.IMPLEMENTATION: (
        "契約が成立しました。プロジェクトの進行について話し合ってください。"
        "キックオフミーティングの日程、成果物のスケジュール、"
        "連絡体制について確認してください。"
    ),
    ConversationStage.BILLING: (
        "プロジェクトが完了または中間マイルストーンに達しました。"
        "請求書を送付する旨を伝え、支払い条件を確認してください。"
        "紹介料やエージェント費用についても触れてください。"
    ),
}


class LlmClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_response(
        self,
        conv: Conversation,
        latest_email: ParsedEmail | None = None,
        is_follow_up: bool = False,
    ) -> str:
        """Generate a response email body for the current conversation stage."""
        system_prompt = _load_prompt("system.txt")
        stage_instruction = STAGE_INSTRUCTIONS.get(conv.stage, "")

        # Build context from conversation history
        messages = [{"role": "system", "content": system_prompt}]

        # Load generation guide and negotiation strategy
        generation_guide = _load_prompt("generate_response.txt")
        negotiation_strategy = _load_prompt("negotiation_strategy.txt")

        # Add stage-specific instruction
        stage_context = (
            f"現在のステージ: {conv.stage.value}\n"
            f"指示: {stage_instruction}\n"
            f"相手の会社: {conv.extracted_info.company_name}\n"
            f"担当者: {conv.extracted_info.contact_name}\n"
            f"サービス種類: {conv.extracted_info.service_type}\n"
            f"予算: {conv.extracted_info.budget_low}〜{conv.extracted_info.budget_high}円\n"
            f"プラットフォーム: {conv.extracted_info.platform}\n"
        )
        if generation_guide:
            stage_context += f"\n---\n{generation_guide}"
        if conv.stage == ConversationStage.NEGOTIATION and negotiation_strategy:
            stage_context += f"\n---\n交渉戦略:\n{negotiation_strategy}"

        messages.append({"role": "system", "content": stage_context})

        # Add conversation history
        for entry in conv.history[-10:]:  # Keep last 10 messages for context
            role = "user" if entry.get("direction") == "inbound" else "assistant"
            messages.append({"role": role, "content": entry.get("body", "")})

        # Add the latest inbound email if present
        if latest_email:
            messages.append({"role": "user", "content": latest_email.body})

        # Add follow-up instruction if this is a nudge
        if is_follow_up:
            messages.append({
                "role": "system",
                "content": (
                    "相手からの返信がありません。丁寧にフォローアップしてください。"
                    "催促ではなく、追加情報の提供や別の切り口での提案を行ってください。"
                ),
            })

        response = await self._client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
        )

        return response.choices[0].message.content.strip()
