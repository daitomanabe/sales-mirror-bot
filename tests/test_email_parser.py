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


def test_saas_sales_email():
    """SaaS tool sales email should be detected."""
    saas = ParsedEmail(
        message_id="<saas@example.com>",
        from_addr="sales@saas-tool.co.jp",
        from_name="SaaSツール営業",
        subject="業務効率化ツールのご案内",
        body=(
            "お世話になっております。\n"
            "貴社の業務効率化に貢献できるクラウドサービスのご案内です。\n"
            "導入実績300社以上、コスト削減30%を実現しています。\n"
            "無料トライアルもございますので、ぜひデモをご覧ください。"
        ),
    )
    assert EmailParser.is_sales_email(saas) is True


def test_partnership_email():
    """Business partnership proposal should be detected."""
    partner = ParsedEmail(
        message_id="<partner@example.com>",
        from_addr="biz@partner-corp.co.jp",
        from_name="事業開発部",
        subject="業務提携のご提案",
        body=(
            "貴社の事業内容を拝見し、弊社との協業の可能性について\n"
            "ご相談させていただきたくご連絡いたしました。\n"
            "アライアンスにより相互の販路拡大が見込めると考えております。"
        ),
    )
    assert EmailParser.is_sales_email(partner) is True


def test_recruitment_email():
    """Recruitment agency email should be detected."""
    recruit = ParsedEmail(
        message_id="<recruit@example.com>",
        from_addr="agent@recruit.co.jp",
        from_name="人材エージェント",
        subject="エンジニア紹介のご案内",
        body=(
            "貴社の採用支援をお手伝いしたくご連絡いたしました。\n"
            "優秀なエンジニア紹介が可能です。\n"
            "ぜひ一度ご相談ください。"
        ),
    )
    assert EmailParser.is_sales_email(recruit) is True


def test_seminar_invitation():
    """Seminar/webinar invitation should be detected."""
    seminar = ParsedEmail(
        message_id="<seminar@example.com>",
        from_addr="event@company.co.jp",
        from_name="セミナー事務局",
        subject="DX推進セミナーへの無料ご招待",
        body=(
            "この度、DX推進に関するウェビナーを開催いたします。\n"
            "業務効率化の最新トレンドについてご案内いたします。\n"
            "ぜひご参加ください。"
        ),
    )
    assert EmailParser.is_sales_email(seminar) is True


def test_emeao_matching_email():
    """EMEAO matching service email should be detected."""
    emeao = ParsedEmail(
        message_id="<emeao@example.com>",
        from_addr="sales@emeao.jp",
        from_name="EMEAO営業",
        subject="AI案件のご紹介",
        body=(
            "お世話になっております。\n"
            "EMEAOの営業担当です。\n"
            "AI開発案件のご相談を複数いただいており、\n"
            "予算500万〜1500万円のご案件をご紹介可能です。\n"
            "ぜひ力をお借りしたいと考えております。"
        ),
    )
    assert EmailParser.is_sales_email(emeao) is True


def test_personal_email_not_detected():
    """Personal email should not trigger sales detection."""
    personal = ParsedEmail(
        message_id="<personal@example.com>",
        from_addr="friend@gmail.com",
        from_name="友人",
        subject="今度飲みに行こう",
        body="久しぶり！来週あたり飲みに行かない？渋谷あたりでどう？",
    )
    assert EmailParser.is_sales_email(personal) is False


def test_delivery_notification_not_detected():
    """Delivery/shipping notification should not trigger sales detection."""
    delivery = ParsedEmail(
        message_id="<delivery@example.com>",
        from_addr="noreply@amazon.co.jp",
        from_name="Amazon.co.jp",
        subject="ご注文の配送状況",
        body="お客様のご注文商品は本日発送されました。配送状況は以下のリンクからご確認ください。",
    )
    assert EmailParser.is_sales_email(delivery) is False
