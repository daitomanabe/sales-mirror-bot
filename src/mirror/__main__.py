import argparse
import asyncio
import logging

from mirror.bot import MirrorBot
from mirror.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="sales-mirror-bot: autonomous sales email counter-agent"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate responses but don't send emails",
    )
    args = parser.parse_args()

    if args.dry_run:
        settings.dry_run = True

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("mirror")
    logger.info("Starting sales-mirror-bot...")
    logger.info(
        "Bot: %s (%s) | Mode: %s",
        settings.bot_display_name,
        settings.bot_company_name,
        "DRY-RUN" if settings.dry_run else "LIVE",
    )
    logger.info("Monitoring: %s@%s", settings.imap_user, settings.imap_host)

    bot = MirrorBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
