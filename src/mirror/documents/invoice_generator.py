from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from mirror.config import settings
from mirror.models import Conversation

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"


class InvoiceGenerator:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )

    def generate(self, conv: Conversation, amount: int) -> str:
        template = self._env.get_template("invoice.md.j2")
        today = datetime.now()
        info = conv.extracted_info

        # Generate a deterministic invoice number from conversation
        hash_input = f"{conv.thread_id}-{today.strftime('%Y%m')}"
        invoice_number = "INV-" + hashlib.sha256(
            hash_input.encode()
        ).hexdigest()[:8].upper()

        tax_rate = 0.10
        tax_amount = int(amount * tax_rate)
        total = amount + tax_amount

        return template.render(
            invoice_number=invoice_number,
            date=today.strftime("%Y年%m月%d日"),
            due_date=(today + timedelta(days=30)).strftime("%Y年%m月%d日"),
            client_company=info.company_name,
            client_name=info.contact_name,
            provider_company=settings.bot_company_name,
            provider_name=settings.bot_display_name,
            provider_email=settings.bot_email,
            service_description=info.service_type or "AI開発・導入支援業務",
            amount=amount,
            amount_formatted=f"{amount:,}",
            tax_rate=int(tax_rate * 100),
            tax_amount=tax_amount,
            tax_amount_formatted=f"{tax_amount:,}",
            total=total,
            total_formatted=f"{total:,}",
        )
