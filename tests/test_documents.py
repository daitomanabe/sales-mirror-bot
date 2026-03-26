from mirror.documents.contract_generator import ContractGenerator
from mirror.documents.invoice_generator import InvoiceGenerator
from mirror.models import Conversation, ExtractedInfo


def _make_conversation() -> Conversation:
    return Conversation(
        id=1,
        thread_id="<doc-test@example.com>",
        email_from="test@frontier-gr.jp",
        company_name="フロンティア株式会社",
        extracted_info=ExtractedInfo(
            company_name="フロンティア株式会社",
            contact_name="小川 恵人",
            service_type="AI開発・導入支援",
            budget_low=5_000_000,
            budget_high=10_000_000,
        ),
    )


def test_contract_generation():
    gen = ContractGenerator()
    conv = _make_conversation()
    result = gen.generate(conv)

    assert "業務委託契約書" in result
    assert "フロンティア株式会社" in result
    assert "AI開発・導入支援" in result
    assert "5,000,000" in result
    assert "第1条" in result
    assert "第10条" in result


def test_invoice_generation():
    gen = InvoiceGenerator()
    conv = _make_conversation()
    result = gen.generate(conv, amount=5_000_000)

    assert "請求書" in result
    assert "INV-" in result
    assert "フロンティア株式会社" in result
    assert "5,000,000" in result
    assert "500,000" in result  # 10% tax
    assert "5,500,000" in result  # total
