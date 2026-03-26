"""Meeting scheduler: generates plausible meeting date proposals."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from openai import AsyncOpenAI

from mirror.config import settings

logger = logging.getLogger(__name__)

DATE_EXTRACTION_PROMPT = """\
以下のメール本文から、打ち合わせの日程に関する情報を抽出してください。
JSON形式で返してください。

抽出する項目:
- proposed_dates: 提案されている日程のリスト。各要素は {"date": "YYYY-MM-DD", "time": "HH:MM", "note": "備考"} の形式。提案がなければ空リスト
- meeting_format: 会議形式 ("online", "offline", "unspecified")
- meeting_tool: ツール名 ("zoom", "google_meet", "teams", "unspecified")
- meeting_url: 会議URLがあれば。なければ null
- duration_minutes: 想定所要時間（分）。不明なら null
- confirmed_date: 確定された日程があれば {"date": "YYYY-MM-DD", "time": "HH:MM"}。なければ null

JSONのみを返してください。
"""


class MeetingScheduler:
    """Extract meeting dates from emails and generate proposals."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract_dates(self, email_body: str) -> dict:
        """Extract meeting-related info from an email."""
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": DATE_EXTRACTION_PROMPT},
                    {"role": "user", "content": email_body},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            logger.exception("Failed to extract dates")
            return {}

    @staticmethod
    def generate_proposals(base_date: datetime | None = None, count: int = 3) -> list[dict]:
        """Generate plausible meeting date proposals for next week.

        Returns dates that:
        - Are on weekdays (Mon-Fri)
        - Start from next week
        - Have business-hour time slots
        """
        if base_date is None:
            base_date = datetime.now()

        # Start from next Monday
        days_until_monday = (7 - base_date.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = base_date + timedelta(days=days_until_monday)

        # Business hour slots
        time_slots = ["10:00", "11:00", "14:00", "15:00", "16:00"]
        proposals = []
        slot_idx = 0

        for day_offset in range(5):  # Mon-Fri
            if len(proposals) >= count:
                break
            day = next_monday + timedelta(days=day_offset)
            proposals.append({
                "date": day.strftime("%Y-%m-%d"),
                "weekday": ["月", "火", "水", "木", "金"][day.weekday()],
                "time": time_slots[slot_idx % len(time_slots)],
                "display": f"{day.month}月{day.day}日（{'月火水木金'[day.weekday()]}）{time_slots[slot_idx % len(time_slots)]}〜",
            })
            slot_idx += 1

        return proposals

    @staticmethod
    def format_proposals(proposals: list[dict], duration: int = 30) -> str:
        """Format date proposals as Japanese business text."""
        lines = ["以下の候補日ではいかがでしょうか：\n"]
        for p in proposals:
            lines.append(f"- {p['display']}{p['time']}〜{duration}分程度")
        lines.append("\nオンライン（Zoom/Google Meet）での実施を想定しております。")
        return "\n".join(lines)
