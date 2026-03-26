import asyncio
import logging

from mirror.bot import MirrorBot
from mirror.config import settings


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("mirror")
    logger.info("Starting sales-mirror-bot...")
    logger.info("Bot identity: %s (%s)", settings.bot_display_name, settings.bot_company_name)
    logger.info("Monitoring: %s@%s", settings.imap_user, settings.imap_host)

    bot = MirrorBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
