import argparse
import asyncio
import logging

from mirror.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="sales-mirror-bot: autonomous sales email counter-agent"
    )
    sub = parser.add_subparsers(dest="command")

    # Default: run the bot
    run_parser = sub.add_parser("run", help="Run the bot (default)")
    run_parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate responses but don't send emails",
    )

    # List conversations
    list_parser = sub.add_parser("list", help="List conversations")
    list_parser.add_argument("--stage", help="Filter by stage")

    # Show conversation detail
    show_parser = sub.add_parser("show", help="Show conversation detail")
    show_parser.add_argument("id", type=int, help="Conversation ID")

    # Export
    export_parser = sub.add_parser("export", help="Export conversations")
    export_parser.add_argument(
        "--format", choices=["json", "csv"], default="json",
        help="Export format (default: json)",
    )

    # Process single email from stdin
    sub.add_parser("process", help="Process a raw email from stdin (dry-run)")

    # Top-level --dry-run for backwards compatibility
    parser.add_argument(
        "--dry-run", action="store_true", dest="global_dry_run",
        help="Generate responses but don't send emails",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handle commands
    if args.command == "list":
        from mirror.cli import list_conversations
        asyncio.run(list_conversations(args.stage))

    elif args.command == "show":
        from mirror.cli import show_conversation
        asyncio.run(show_conversation(args.id))

    elif args.command == "export":
        from mirror.cli import export_conversations
        asyncio.run(export_conversations(args.format))

    elif args.command == "process":
        from mirror.cli import process_stdin_email
        asyncio.run(process_stdin_email())

    else:
        # Default: run the bot
        dry_run = args.global_dry_run or getattr(args, "dry_run", False)
        if dry_run:
            settings.dry_run = True

        from mirror.bot import MirrorBot

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
