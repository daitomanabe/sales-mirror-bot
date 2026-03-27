from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from mirror.config import settings
from mirror.models import Conversation

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"


class ContractGenerator:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )

    def generate(self, conv: Conversation) -> str:
        template = self._env.get_template("contract.md.j2")
        today = datetime.now()
        info = conv.extracted_info

        return template.render(
            date=today.strftime("%Y年%m月%d日"),
            client_company=info.company_name,
            client_name=info.contact_name,
            provider_company=settings.bot_company_name,
            provider_name=settings.bot_display_name,
            provider_title=settings.bot_title,
            service_description=info.service_type or "AI開発・導入支援業務",
            contract_amount=info.budget_low or 2_000_000,
            contract_amount_formatted=f"{(info.budget_low or 2_000_000):,}",
            start_date=(today + timedelta(days=14)).strftime("%Y年%m月%d日"),
            end_date=(today + timedelta(days=104)).strftime("%Y年%m月%d日"),
            payment_due_days=30,
        )
