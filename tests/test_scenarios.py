"""Integration tests simulating full conversation flows from the 5 scenarios."""
from datetime import datetime, timedelta

import pytest

from mirror.conversation.state_machine import ConversationStateMachine
from mirror.models import (
    Conversation,
    ConversationStage,
    ExtractedInfo,
    ParsedEmail,
)
from mirror.parser.email_parser import EmailParser


# ── Scenario 1: Readycrew matching service ─────────────────────

READYCREW_EMAIL = ParsedEmail(
    message_id="<rc001@frontier-gr.jp>",
    from_addr="keito.ogawa@frontier-gr.jp",
    from_name="小川 恵人",
    subject="AI開発・導入支援のご相談",
    body=(
        "フロンティア株式会社『レディクル』の小川です。\n"
        "貴社のコーポレートサイトより事業内容を拝見し\n"
        "是非、力をお借りしたいと思いご連絡させていただきました。\n"
        "AI開発・導入支援にご対応いただける企業様をお探しとのことで、\n"
        "直近でご相談いただいている案件の予算感としては、200万～2000万円ほどになります。\n"
        "費用を掛けての新規開拓・販路拡大にご関心があれば、ご挨拶ができれば幸いです。"
    ),
)


# ── Scenario 2: SaaS direct sales ──────────────────────────────

SAAS_EMAIL = ParsedEmail(
    message_id="<saas001@smartflow.co.jp>",
    from_addr="yamada@smartflow.co.jp",
    from_name="山田 真一",
    subject="【SmartFlow】業務プロセス自動化ツールのご案内",
    body=(
        "株式会社スマートフローの山田です。\n"
        "弊社のAI搭載業務プロセス自動化ツール「SmartFlow」のご案内です。\n"
        "ノーコードでワークフロー作成、AI-OCRによる書類の自動読取、\n"
        "ChatGPT連携による自動応答。月額5万円〜。\n"
        "導入企業様では平均40%の業務工数削減を実現しています。\n"
        "無料トライアル（30日間）をご提供しております。\n"
        "導入事例はこちら：https://smartflow.co.jp/cases/"
    ),
)


# ── Scenario 3: Recruitment agency ──────────────────────────────

RECRUITMENT_EMAIL = ParsedEmail(
    message_id="<rec001@techbridge.co.jp>",
    from_addr="sato@techbridge.co.jp",
    from_name="佐藤 美咲",
    subject="エンジニア採用支援のご案内",
    body=(
        "株式会社テックブリッジの佐藤です。\n"
        "貴社のAI開発事業の成長を拝見し、エンジニア紹介のご支援ができればと思いご連絡いたしました。\n"
        "弊社はAI/ML分野に特化した人材紹介会社です。\n"
        "機械学習エンジニア、データサイエンティスト、MLOpsエンジニアのご紹介が可能です。\n"
        "紹介料は理論年収の30〜35%です。\n"
        "まずは貴社の採用状況やご要望をお伺いする場を設けさせていただければ幸いです。"
    ),
)


# ── Scenario 4: Seminar invitation ──────────────────────────────

SEMINAR_EMAIL = ParsedEmail(
    message_id="<sem001@dx-partners.co.jp>",
    from_addr="takahashi@dx-partners.co.jp",
    from_name="高橋 直人",
    subject="【無料ご招待】AI×DX推進セミナー 〜製造業のAI活用最前線〜",
    body=(
        "DXパートナーズ株式会社の高橋です。\n"
        "弊社主催のセミナーに貴社をご招待させていただきたくご連絡いたしました。\n"
        "AI×DX推進セミナー 〜製造業のAI活用最前線〜\n"
        "製造業におけるAI活用の最新動向、予知保全・品質検査AIの導入事例、\n"
        "生成AIを活用したDX推進の実践。\n"
        "セミナー終了後、ご希望の方には個別相談の時間も設けております。"
    ),
)


# ── Scenario 5: Partnership proposal ────────────────────────────

PARTNERSHIP_EMAIL = ParsedEmail(
    message_id="<part001@creative-web.co.jp>",
    from_addr="kimura@creative-web.co.jp",
    from_name="木村 健太",
    subject="AI×Web開発の業務提携のご提案",
    body=(
        "株式会社クリエイティブウェブの木村です。\n"
        "弊社はWebサイト・Webアプリケーション開発を主力とする会社です。\n"
        "クライアント様からWebサービスにAI機能を組み込みたいという\n"
        "ご要望を多数いただいているのですが、AI開発の技術力が社内にないため\n"
        "お断りせざるを得ない状況です。\n"
        "業務提携を結ばせていただき、AI機能が必要な案件を\n"
        "相互にご紹介できる関係を構築できないかと考えております。\n"
        "ご興味がございましたら、一度お話しの場を設けさせていただければ幸いです。"
    ),
)


# ── Sales Detection Tests ───────────────────────────────────────


class TestScenarioDetection:
    """Verify all 5 scenario emails are detected as sales."""

    def test_readycrew_detected(self):
        assert EmailParser.is_sales_email(READYCREW_EMAIL)

    def test_saas_detected(self):
        assert EmailParser.is_sales_email(SAAS_EMAIL)

    def test_recruitment_detected(self):
        assert EmailParser.is_sales_email(RECRUITMENT_EMAIL)

    def test_seminar_detected(self):
        assert EmailParser.is_sales_email(SEMINAR_EMAIL)

    def test_partnership_detected(self):
        assert EmailParser.is_sales_email(PARTNERSHIP_EMAIL)


# ── State Machine Flow Tests ────────────────────────────────────


class TestFullPipelineFlow:
    """Simulate full conversation flows through the state machine."""

    def _advance_through(self, start_stage, exchanges_per_stage):
        """Advance a conversation through multiple stages."""
        conv = Conversation(
            id=1,
            thread_id="<test@example.com>",
            email_from="test@example.com",
            company_name="Test Corp",
            stage=start_stage,
            extracted_info=ExtractedInfo(
                company_name="Test Corp",
                budget_low=5_000_000,
            ),
        )
        stages_visited = [conv.stage]

        for stage, count in exchanges_per_stage:
            conv.stage = stage
            for i in range(count):
                conv.history.append({
                    "direction": "inbound",
                    "stage": stage.value,
                    "body": f"Message {i}",
                })
            if ConversationStateMachine.can_advance(conv):
                ConversationStateMachine.advance(conv)
                stages_visited.append(conv.stage)

        return conv, stages_visited

    def test_readycrew_full_pipeline(self):
        """Scenario 1: Full 7-stage pipeline."""
        conv, stages = self._advance_through(
            ConversationStage.INITIAL_RESPONSE,
            [
                (ConversationStage.INITIAL_RESPONSE, 1),
                (ConversationStage.MEETING_SETUP, 1),
                (ConversationStage.PROPOSAL, 1),
                (ConversationStage.NEGOTIATION, 2),  # 2 rounds
                (ConversationStage.CONTRACT, 1),
                (ConversationStage.IMPLEMENTATION, 2),
                (ConversationStage.BILLING, 1),
            ],
        )
        assert ConversationStage.INITIAL_RESPONSE in stages
        assert ConversationStage.BILLING in stages
        assert conv.stage == ConversationStage.CLOSED

    def test_negotiation_requires_two_rounds(self):
        """Negotiation needs 2 inbound messages to advance."""
        conv = Conversation(
            id=1,
            thread_id="<neg@example.com>",
            email_from="test@example.com",
            company_name="Test",
            stage=ConversationStage.NEGOTIATION,
            history=[
                {"direction": "inbound", "stage": "negotiation", "body": "Round 1"},
            ],
        )
        assert not ConversationStateMachine.can_advance(conv)

        conv.history.append(
            {"direction": "inbound", "stage": "negotiation", "body": "Round 2"}
        )
        assert ConversationStateMachine.can_advance(conv)

    def test_abandonment_after_14_days(self):
        """Conversation with no reply for 14 days should be abandoned."""
        conv = Conversation(
            id=1,
            thread_id="<stale@example.com>",
            email_from="test@example.com",
            company_name="Ghost Corp",
            stage=ConversationStage.MEETING_SETUP,
            updated_at=datetime.now() - timedelta(days=15),
        )
        assert ConversationStateMachine.should_abandon(conv)

    def test_not_abandoned_if_recent(self):
        conv = Conversation(
            id=1,
            thread_id="<fresh@example.com>",
            email_from="test@example.com",
            company_name="Active Corp",
            stage=ConversationStage.PROPOSAL,
            updated_at=datetime.now() - timedelta(days=3),
        )
        assert not ConversationStateMachine.should_abandon(conv)


# ── Document Generation Tests ───────────────────────────────────


class TestScenarioDocuments:
    """Test document generation with scenario-specific data."""

    def test_readycrew_contract(self):
        from mirror.documents.contract_generator import ContractGenerator

        conv = Conversation(
            id=1,
            thread_id="<rc@frontier.jp>",
            email_from="ogawa@frontier-gr.jp",
            company_name="フロンティア株式会社",
            stage=ConversationStage.CONTRACT,
            extracted_info=ExtractedInfo(
                company_name="フロンティア株式会社",
                contact_name="小川 恵人",
                service_type="AI開発・導入支援パートナー契約",
                budget_low=10_500_000,
            ),
        )
        contract = ContractGenerator().generate(conv)
        assert "フロンティア株式会社" in contract
        assert "10,500,000" in contract
        assert "業務委託契約書" in contract

    def test_saas_reverse_invoice(self):
        from mirror.documents.invoice_generator import InvoiceGenerator

        conv = Conversation(
            id=2,
            thread_id="<saas@smartflow.jp>",
            email_from="suzuki@smartflow.co.jp",
            company_name="株式会社スマートフロー",
            stage=ConversationStage.BILLING,
            extracted_info=ExtractedInfo(
                company_name="株式会社スマートフロー",
                contact_name="鈴木",
                service_type="AI-OCR精度改善コンサルティング",
                budget_low=600_000,
            ),
        )
        invoice = InvoiceGenerator().generate(conv, 600_000)
        assert "スマートフロー" in invoice
        assert "600,000" in invoice
        assert "60,000" in invoice  # 10% tax

    def test_recruitment_monthly_invoice(self):
        from mirror.documents.invoice_generator import InvoiceGenerator

        conv = Conversation(
            id=3,
            thread_id="<rec@techbridge.jp>",
            email_from="tanaka@techbridge.co.jp",
            company_name="株式会社テックブリッジ",
            stage=ConversationStage.BILLING,
            extracted_info=ExtractedInfo(
                company_name="株式会社テックブリッジ",
                contact_name="田中",
                service_type="MLエンジニアチーム準委任契約",
                budget_low=3_000_000,
            ),
        )
        invoice = InvoiceGenerator().generate(conv, 3_000_000)
        assert "テックブリッジ" in invoice
        assert "3,000,000" in invoice
