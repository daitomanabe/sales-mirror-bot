# Sales Mirror Bot — Dashboard

Cloudflare Workers + D1 + Hono dashboard for monitoring bot conversations.

## Setup

```bash
cd dashboard

# Install dependencies
npm install

# Create D1 database
wrangler d1 create mirror-db
# Copy the database_id to wrangler.jsonc

# Initialize schema
wrangler d1 execute mirror-db --file=./schema.sql

# Set API token (for sync authentication)
wrangler secret put API_TOKEN

# Local development
npm run dev

# Deploy
npm run deploy
```

## Architecture

- **Hono** — lightweight web framework for API routing
- **D1** — Cloudflare's serverless SQLite for data storage
- **Workers Static Assets** — serves the dashboard UI
- **Bot Sync** — the Python bot pushes data to `/api/sync/*` endpoints

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stats` | Dashboard overview (totals, funnel, recent activity) |
| GET | `/api/conversations` | List conversations (filter by `?stage=`) |
| GET | `/api/conversations/:id` | Conversation detail with messages and documents |
| GET | `/api/analytics` | Funnel analytics, top companies, daily activity |
| POST | `/api/sync/conversations` | Sync conversations from bot (auth required) |
| POST | `/api/sync/messages` | Sync messages from bot (auth required) |
| GET | `/api/health` | Health check with last sync time |
