# CLAUDE.md

## Project Overview

**sales-mirror-bot** is an autonomous counter-agent system that converts incoming spam/sales emails into revenue. An AI bot responds as an "ideal client," autonomously negotiating deals, executing contracts, and collecting referral fees or kickbacks — all without human intervention.

Motto: "営業ボットには、営業ボットを。" (Answer a sales bot with a sales bot.)

**Status:** Early stage — planning/documentation phase. No implementation code exists yet.

## Repository Structure

```
sales-mirror-bot/
├── README.md          # Project overview and feature description (Japanese/English)
└── CLAUDE.md          # This file — AI assistant guide
```

## Planned Tech Stack

- **Language Models:** GPT-4o, Gemini 1.5 Pro (sales-psychology-focused prompt engineering)
- **Mail Integration:** IMAP/SMTP monitoring for incoming sales emails
- **Legal-Tech:** Electronic contract APIs (CloudSign planned)
- **Payments:** Stripe, Crypto Wallet for automated revenue collection
- **Primary Language:** Japanese (with English documentation)

## Planned Core Features

1. **Recursive Sales Response** — Generate "high-interest" replies matching the sender's sales intensity
2. **Autonomous Negotiation** — Bot-driven price negotiation for AI development/consulting deals
3. **Smart Contract Execution** — Auto-sign contracts via e-signature APIs
4. **Revenue Mirroring** — Capture referral fees, project budgets, or charge agent fees back to the sender

## Development Workflow

No build system, test framework, or CI/CD pipeline is configured yet. When implementation begins:

- Define commands here (build, test, lint, format)
- Document environment variables and `.env` setup
- Add CI/CD configuration details

## Git Conventions

- **Default branch:** `main`
- **Commit messages:** Short, descriptive (English preferred for git history)
- **Branch naming:** `feature/<description>` or `fix/<description>`

## Key Guidelines for AI Assistants

- This project is bilingual — README and user-facing text are primarily in Japanese; code and git history should use English
- No implementation code exists yet; when contributing, propose a clear project structure before writing code
- Respect the project's experimental/satirical tone while keeping code professional
- Do not add dependencies without justification
- Keep security in mind — this system will handle email credentials, payment APIs, and contract signing
