from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from mirror.config import settings
from mirror.models import ExtractedInfo, ParsedEmail

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
あなたは営業メール分析の専門家です。
以下のメールから情報を抽出し、JSON形式で返してください。

抽出する項目:
- company_name: 送信者の会社名
- contact_name: 送信者の氏名
- contact_email: 送信者のメールアドレス
- service_type: 提案されているサービスの種類（例: "AI開発支援", "マッチングサービス", "コンサルティング"）
- budget_low: 予算の下限（数値、万円単位を円に変換。例: 200万→2000000）。不明なら null
- budget_high: 予算の上限（数値、円）。不明なら null
- platform: プラットフォーム名（例: "レディクル", "readycrew"）。不明なら空文字
- urgency: 緊急度 ("high", "normal", "low")
- summary: メールの要旨を1-2文で（日本語）

JSONのみを返してください。マークダウンや説明は不要です。
"""

SALES_KEYWORDS = [
    "ご紹介", "ご案内", "ご提案", "ご相談", "お力添え",
    "力をお借り", "マッチング", "レディクル", "readycrew",
    "新規開拓", "販路拡大", "案件", "予算",
    "ご挨拶", "事業内容を拝見", "親和性",
]


class EmailParser:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract(self, mail: ParsedEmail) -> ExtractedInfo:
        """Extract structured info from a sales email using GPT-4o."""
        content = f"件名: {mail.subject}\n送信者: {mail.from_name} <{mail.from_addr}>\n\n{mail.body}"

        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": content},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)

            # Fill in contact_email from mail headers if not extracted
            if not data.get("contact_email"):
                data["contact_email"] = mail.from_addr

            return ExtractedInfo(**data)

        except Exception:
            logger.exception("Failed to extract info from email %s", mail.message_id)
            return ExtractedInfo(
                contact_name=mail.from_name,
                contact_email=mail.from_addr,
            )

    @staticmethod
    def is_sales_email(mail: ParsedEmail) -> bool:
        """Heuristic check: does this look like a sales/matching email?"""
        text = (mail.subject + " " + mail.body).lower()
        matches = sum(1 for kw in SALES_KEYWORDS if kw.lower() in text)
        return matches >= 2
