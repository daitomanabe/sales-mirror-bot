from mirror.models import ParsedEmail
from mirror.parser.email_parser import EmailParser


def test_is_sales_email_positive(sample_readycrew_email: ParsedEmail):
    """Readycrew email should be classified as sales."""
    assert EmailParser.is_sales_email(sample_readycrew_email) is True


def test_is_sales_email_negative():
    """A normal business email should not be classified as sales."""
    normal = ParsedEmail(
        message_id="<normal@example.com>",
        from_addr="colleague@example.com",
        from_name="同僚",
        subject="来週のミーティングについて",
        body="来週の定例ミーティングの時間を変更したいのですが、ご都合いかがでしょうか。",
    )
    assert EmailParser.is_sales_email(normal) is False


def test_is_sales_email_matching_keywords():
    """Email with multiple sales keywords should be detected."""
    sales = ParsedEmail(
        message_id="<sales@example.com>",
        from_addr="sales@example.com",
        from_name="営業担当",
        subject="ご紹介の件",
        body="案件のご相談です。予算は300万円ほどです。ご紹介させていただければ。",
    )
    assert EmailParser.is_sales_email(sales) is True
