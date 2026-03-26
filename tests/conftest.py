from __future__ import annotations

from datetime import datetime

import pytest

from mirror.db import Database
from mirror.models import ExtractedInfo, ParsedEmail


@pytest.fixture
def sample_readycrew_email() -> ParsedEmail:
    """A realistic Readycrew-style sales email for testing."""
    return ParsedEmail(
        message_id="<abc123@frontier-gr.jp>",
        from_addr="keito.ogawa@frontier-gr.jp",
        from_name="小川 恵人",
        to_addr="test@example.com",
        subject="AI開発・導入支援のご相談",
        body=(
            "株式会社mmmm\n"
            "代表取締役　真鍋 大度 様\n\n"
            "お世話になります。\n"
            "フロンティア株式会社『レディクル』の小川です。\n\n"
            "突然のご連絡失礼いたします。\n\n"
            "貴社のコーポレートサイトより事業内容を拝見し\n"
            "是非、力をお借りしたいと思いご連絡させていただきました。\n\n"
            "現在、弊社のお付き合いのある大手メーカー様や中堅、中小企業様から、\n"
            "AI開発・導入支援にご対応いただける企業様をお探しとのことで、\n"
            "貴社の事業内容と親和性の高いご相談を日々いただいております。\n\n"
            "直近でご相談いただいている案件の予算感としては、200万～2000万円ほどになります。\n"
            "貴社に内容やタイミングが合えばご紹介させていただければと考えております。\n\n"
            "今後のご方針として、費用を掛けての新規開拓・販路拡大にご関心があれば、\n"
            "直近でいただいているご相談の開示を交えたご挨拶ができれば幸いです。\n"
        ),
        received_at=datetime(2026, 3, 26, 10, 0, 0),
    )


@pytest.fixture
def sample_extracted_info() -> ExtractedInfo:
    return ExtractedInfo(
        company_name="フロンティア株式会社",
        contact_name="小川 恵人",
        contact_email="keito.ogawa@frontier-gr.jp",
        service_type="AI開発・導入支援マッチング",
        budget_low=2_000_000,
        budget_high=20_000_000,
        platform="レディクル",
        urgency="normal",
        summary="AI開発・導入支援の案件紹介サービス。予算200万〜2000万円。",
    )


@pytest.fixture
async def db(tmp_path):
    """In-memory (tmpdir) database for testing."""
    database = Database(str(tmp_path / "test.db"))
    await database.init()
    yield database
    await database.close()
