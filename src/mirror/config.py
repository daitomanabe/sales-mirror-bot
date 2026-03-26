from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # IMAP
    imap_host: str = "imap.example.com"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""

    # SMTP
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Bot identity
    bot_display_name: str = "真鍋 大度"
    bot_company_name: str = "株式会社mmmm"
    bot_email: str = ""
    bot_title: str = "代表取締役"

    # Database
    database_path: str = "data/conversations.db"

    # Polling
    poll_interval_seconds: int = 60

    # Logging
    log_level: str = "INFO"

    # Dry-run mode: generate responses but don't send emails
    dry_run: bool = False

    # Max conversations to track simultaneously
    max_active_conversations: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
