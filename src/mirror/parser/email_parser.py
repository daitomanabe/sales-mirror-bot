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
- service_type: 提案されているサービスの種類（例: "AI開発支援", "マッチングサービス", "コンサルティング", "SaaS営業", "人材紹介", "Web制作"）
- budget_low: 予算の下限（数値、万円単位を円に変換。例: 200万→2000000）。不明なら null
- budget_high: 予算の上限（数値、円）。不明なら null
- platform: プラットフォーム名（例: "レディクル", "readycrew", "EMEAO", "ビジネスマッチ", "比較ビズ"）。不明なら空文字
- urgency: 緊急度 ("high", "normal", "low")
- summary: メールの要旨を1-2文で（日本語）
- email_type: メールの種類を以下から選択:
  "matching" (マッチングサービスからの案件紹介),
  "direct_sales" (SaaS/ツールの直接営業),
  "partnership" (業務提携・パートナーシップ提案),
  "recruitment" (人材紹介・採用関連),
  "seminar" (セミナー・ウェビナー招待),
  "other" (その他)

JSONのみを返してください。マークダウンや説明は不要です。
"""

# Keywords indicating various types of sales/matching emails
SALES_KEYWORDS = [
    # マッチングサービス系
    "ご紹介", "ご案内", "ご提案", "ご相談", "お力添え",
    "力をお借り", "マッチング", "レディクル", "readycrew",
    "EMEAO", "ビジネスマッチ", "比較ビズ", "発注ナビ",
    # 営業一般
    "新規開拓", "販路拡大", "案件", "予算",
    "ご挨拶", "事業内容を拝見", "親和性",
    "費用対効果", "導入実績", "無料トライアル",
    # SaaS営業
    "資料請求", "デモ", "導入事例", "コスト削減",
    "業務効率化", "DX推進", "クラウド",
    # パートナーシップ
    "業務提携", "協業", "アライアンス", "代理店",
    # 人材系
    "人材紹介", "採用支援", "エンジニア紹介",
    # セミナー
    "ウェビナー", "セミナー", "無料ご招待",
]


class EmailParser:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract(self, mail: ParsedEmail) -> ExtractedInfo:
        """Extract structured info from a sales email using GPT-4o."""
        content = (
            f"件名: {mail.subject}\n"
            f"送信者: {mail.from_name} <{mail.from_addr}>\n\n"
            f"{mail.body}"
        )

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

            # Remove email_type from data (not in ExtractedInfo model yet)
            data.pop("email_type", None)

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
