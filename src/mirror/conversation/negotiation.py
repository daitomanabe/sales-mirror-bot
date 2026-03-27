"""Negotiation engine: tracks offers, counter-offers, and budget strategy."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

from openai import AsyncOpenAI

from mirror.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Offer:
    """A single offer or counter-offer in a negotiation."""
    amount: int
    proposed_by: str  # "us" or "them"
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    accepted: bool = False


@dataclass
class NegotiationState:
    """Tracks the full negotiation history for a conversation."""
    their_initial_budget_low: int = 0
    their_initial_budget_high: int = 0
    our_target: int = 0  # What we aim for
    our_floor: int = 0   # Minimum we accept
    offers: list[Offer] = field(default_factory=list)
    round_count: int = 0
    strategy: str = "standard"  # standard, aggressive, concede, reverse

    @property
    def latest_offer(self) -> Offer | None:
        return self.offers[-1] if self.offers else None

    @property
    def their_latest(self) -> Offer | None:
        for o in reversed(self.offers):
            if o.proposed_by == "them":
                return o
        return None

    @property
    def our_latest(self) -> Offer | None:
        for o in reversed(self.offers):
            if o.proposed_by == "us":
                return o
        return None

    def add_offer(self, amount: int, proposed_by: str, description: str = "") -> None:
        self.offers.append(Offer(
            amount=amount, proposed_by=proposed_by, description=description
        ))
        if proposed_by == "them":
            self.round_count += 1

    def should_concede(self) -> bool:
        """After 2 rounds, we should move toward agreement."""
        return self.round_count >= 2

    def calc_counter_offer(self) -> int:
        """Calculate our counter-offer based on strategy."""
        their = self.their_latest
        if not their:
            return self.our_target

        if self.should_concede():
            # Move 80% toward their position
            gap = their.amount - self.our_target
            return self.our_target + int(gap * 0.8)

        if self.strategy == "aggressive":
            # Ask for 10-15% discount
            return int(their.amount * 0.87)
        elif self.strategy == "reverse":
            # We're selling — start high, come down slowly
            if self.our_latest:
                return int(self.our_latest.amount * 0.93)
            return self.our_target
        else:
            # Standard: ask for 5-10% discount
            return int(their.amount * 0.92)

    def to_dict(self) -> dict:
        return {
            "their_initial_budget_low": self.their_initial_budget_low,
            "their_initial_budget_high": self.their_initial_budget_high,
            "our_target": self.our_target,
            "our_floor": self.our_floor,
            "offers": [
                {"amount": o.amount, "proposed_by": o.proposed_by,
                 "description": o.description, "timestamp": o.timestamp,
                 "accepted": o.accepted}
                for o in self.offers
            ],
            "round_count": self.round_count,
            "strategy": self.strategy,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NegotiationState:
        state = cls(
            their_initial_budget_low=data.get("their_initial_budget_low", 0),
            their_initial_budget_high=data.get("their_initial_budget_high", 0),
            our_target=data.get("our_target", 0),
            our_floor=data.get("our_floor", 0),
            round_count=data.get("round_count", 0),
            strategy=data.get("strategy", "standard"),
        )
        for o in data.get("offers", []):
            state.offers.append(Offer(**o))
        return state


OFFER_EXTRACTION_PROMPT = """\
以下のメール本文から、金額に関する情報を抽出してください。
JSON形式で返してください。

抽出する項目:
- amount: 提示されている金額（円単位の整数）。複数ある場合は合計額。不明なら null
- is_counter_offer: 値引き要求や条件変更の提案か (true/false)
- discount_request: 値引き率や金額の指定があれば記載。なければ null
- new_terms: 支払い条件や期間の変更提案があれば記載。なければ null
- acceptance_signal: 合意・承諾のシグナルがあるか (true/false)
- summary: 金額交渉に関する要旨（日本語1文）

JSONのみを返してください。
"""


class NegotiationEngine:
    """Analyzes inbound emails for negotiation signals and generates strategy."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze_offer(self, email_body: str) -> dict:
        """Extract offer/counter-offer details from an email."""
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": OFFER_EXTRACTION_PROMPT},
                    {"role": "user", "content": email_body},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            logger.exception("Failed to analyze offer")
            return {}

    @staticmethod
    def init_state(budget_low: int, budget_high: int, strategy: str = "standard") -> NegotiationState:
        """Initialize negotiation state from extracted info."""
        state = NegotiationState(
            their_initial_budget_low=budget_low,
            their_initial_budget_high=budget_high,
            strategy=strategy,
        )
        # Our target: middle-to-lower end of their range
        if budget_low and budget_high:
            state.our_target = budget_low + (budget_high - budget_low) // 3
            state.our_floor = int(budget_low * 0.85)
        elif budget_low:
            state.our_target = budget_low
            state.our_floor = int(budget_low * 0.85)
        return state

    def build_negotiation_context(self, state: NegotiationState) -> str:
        """Build context string for LLM about current negotiation state."""
        lines = [
            f"【交渉状況】",
            f"相手の初期予算: ¥{state.their_initial_budget_low:,}〜¥{state.their_initial_budget_high:,}",
            f"こちらの目標金額: ¥{state.our_target:,}",
            f"最低ライン: ¥{state.our_floor:,}",
            f"交渉ラウンド: {state.round_count}回目",
            f"戦略: {state.strategy}",
        ]

        if state.offers:
            lines.append("\n【オファー履歴】")
            for i, o in enumerate(state.offers, 1):
                who = "相手" if o.proposed_by == "them" else "こちら"
                status = "✓合意" if o.accepted else ""
                lines.append(f"  {i}. {who}: ¥{o.amount:,} {o.description} {status}")

        if state.should_concede():
            counter = state.calc_counter_offer()
            lines.append(f"\n→ 合意に近づけるべき段階。推奨金額: ¥{counter:,}")
        elif state.our_latest:
            counter = state.calc_counter_offer()
            lines.append(f"\n→ カウンターオファー推奨: ¥{counter:,}")

        return "\n".join(lines)
