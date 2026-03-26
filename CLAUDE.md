# CLAUDE.md

## Project Overview

**sales-mirror-bot** is an autonomous counter-agent system that converts incoming spam/sales emails into revenue. An AI bot responds as an "ideal client," autonomously negotiating deals, executing contracts, and collecting referral fees or kickbacks — all without human intervention.

Motto: "営業ボットには、営業ボットを。" (Answer a sales bot with a sales bot.)

## Repository Structure

```
sales-mirror-bot/
├── README.md                          # Project overview (Japanese/English)
├── CLAUDE.md                          # This file — AI assistant guide
├── pyproject.toml                     # Python project config & dependencies
├── .env.example                       # Environment variable template
├── .gitignore
├── src/mirror/                        # Main package
│   ├── __main__.py                    # CLI entry point
│   ├── bot.py                         # Main orchestrator (MirrorBot)
│   ├── config.py                      # pydantic-settings configuration
│   ├── models.py                      # Data models (Pydantic)
│   ├── db.py                          # Async SQLite persistence
│   ├── mail/
│   │   ├── imap_client.py             # IMAP polling for inbound emails
│   │   └── smtp_client.py             # SMTP sending with thread headers
│   ├── parser/
│   │   └── email_parser.py            # GPT-4o email extraction + classification
│   ├── llm/
│   │   └── openai_client.py           # LLM response generation (stage-aware)
│   ├── conversation/
│   │   ├── state_machine.py           # 7-stage pipeline + transitions
│   │   └── handlers.py               # Per-stage response orchestration
│   └── documents/
│       ├── contract_generator.py      # 業務委託契約書 generation
│       └── invoice_generator.py       # 請求書 generation
├── prompts/                           # LLM prompt files (plain text)
│   ├── system.txt                     # Bot persona (tech company CEO)
│   ├── parse_email.txt                # Structured extraction prompt
│   ├── generate_response.txt          # Stage-specific generation guide
│   └── negotiation_strategy.txt       # Pricing negotiation tactics
├── templates/                         # Jinja2 templates
│   ├── contract.md.j2                 # Japanese business contract
│   └── invoice.md.j2                  # Japanese invoice format
└── tests/
    ├── conftest.py                    # Fixtures (sample emails, test DB)
    ├── test_db.py                     # Database CRUD tests
    ├── test_state_machine.py          # Stage transition logic tests
    ├── test_email_parser.py           # Sales email classification tests
    └── test_documents.py              # Contract/invoice generation tests
```

## Tech Stack

- **Python 3.11+** with asyncio
- **OpenAI GPT-4o** — email parsing and response generation
- **aioimaplib / aiosmtplib** — async email I/O
- **aiosqlite** — conversation state persistence
- **Pydantic v2** — data models and settings
- **Jinja2** — document templates (contracts, invoices)

## Architecture

### Conversation Pipeline

```
Inbound Email (IMAP)
  → Sales Detection (keyword heuristics)
  → Structured Extraction (GPT-4o)
  → Thread Resolution (Message-ID / References)
  → State Machine Advance
  → Response Generation (GPT-4o, stage-aware)
  → Document Attachment (contract/invoice at appropriate stages)
  → Send Reply (SMTP with threading headers)
  → Persist to SQLite
```

### Conversation Stages

1. **initial_response** — Express strong interest, ask for details
2. **meeting_setup** — Propose online meeting dates
3. **proposal** — Review proposal, request formal quote
4. **negotiation** — Counter-offer, then agree (2 rounds)
5. **contract** — Send 業務委託契約書 draft, propose e-signature
6. **implementation** — Discuss kickoff, milestones, communication
7. **billing** — Send 請求書, confirm payment terms

### Follow-up System

A background loop checks hourly for stale conversations and sends nudge emails. Conversations with no reply for 14 days are marked dead.

## Development Commands

```bash
# Install (with dev dependencies)
pip install -e ".[dev]"

# Run the bot
python -m mirror
# or: sales-mirror-bot

# Run tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_state_machine.py -v
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `IMAP_HOST` / `IMAP_PORT` | IMAP server for incoming mail |
| `IMAP_USER` / `IMAP_PASSWORD` | IMAP credentials |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server for outgoing mail |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP credentials |
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o) |
| `BOT_DISPLAY_NAME` | Bot's display name in emails |
| `BOT_COMPANY_NAME` | Bot's company name |
| `BOT_EMAIL` | Bot's email address |
| `BOT_TITLE` | Bot's job title |
| `DATABASE_PATH` | SQLite DB path (default: `data/conversations.db`) |
| `POLL_INTERVAL_SECONDS` | IMAP poll interval (default: 60) |
| `LOG_LEVEL` | Logging level (default: INFO) |

## Git Conventions

- **Default branch:** `main`
- **Commit messages:** Short, descriptive (English preferred for git history)
- **Branch naming:** `feature/<description>` or `fix/<description>`

## Key Guidelines for AI Assistants

- This project is bilingual — README and user-facing text are primarily in Japanese; code and git history should use English
- Prompts are stored as plain text files in `prompts/` — edit them directly without code changes
- The system prompt in `prompts/system.txt` defines the bot's persona — changes here affect all responses
- Stage transition logic is in `conversation/state_machine.py` — keep it deterministic
- LLM calls are in `parser/email_parser.py` (extraction) and `llm/openai_client.py` (generation) — these are the only files that call OpenAI
- Templates in `templates/` use Jinja2 syntax — variables come from `Conversation.extracted_info`
- Security: this system handles email credentials and payment info — never log sensitive data
- Do not add dependencies without justification
- Respect the project's experimental/satirical tone while keeping code professional
