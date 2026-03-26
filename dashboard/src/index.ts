import { Hono } from 'hono'
import { cors } from 'hono/cors'

type Bindings = {
  DB: D1Database
  DASHBOARD_TITLE: string
  API_TOKEN?: string
}

const app = new Hono<{ Bindings: Bindings }>()

// CORS for API access
app.use('/api/*', cors())

// Auth middleware for write endpoints
app.use('/api/sync/*', async (c, next) => {
  const token = c.req.header('Authorization')?.replace('Bearer ', '')
  if (c.env.API_TOKEN && token !== c.env.API_TOKEN) {
    return c.json({ error: 'Unauthorized' }, 401)
  }
  await next()
})

// ─── Dashboard Overview ──────────────────────────────────────

app.get('/api/stats', async (c) => {
  const db = c.env.DB

  const totalConvs = await db.prepare(
    'SELECT COUNT(*) as count FROM conversations'
  ).first<{ count: number }>()

  const byStage = await db.prepare(
    `SELECT stage, COUNT(*) as count FROM conversations
     GROUP BY stage ORDER BY count DESC`
  ).all()

  const activeConvs = await db.prepare(
    `SELECT COUNT(*) as count FROM conversations
     WHERE stage NOT IN ('closed', 'dead')`
  ).first<{ count: number }>()

  const totalMessages = await db.prepare(
    'SELECT COUNT(*) as count FROM messages'
  ).first<{ count: number }>()

  const totalDocs = await db.prepare(
    'SELECT COUNT(*) as count FROM documents'
  ).first<{ count: number }>()

  // Revenue pipeline: sum of budget_low from extracted_info for active convos
  const pipeline = await db.prepare(
    `SELECT SUM(json_extract(extracted_info_json, '$.budget_low')) as total
     FROM conversations WHERE stage NOT IN ('dead')`
  ).first<{ total: number | null }>()

  const recentActivity = await db.prepare(
    `SELECT c.id, c.company_name, c.stage, m.direction, m.subject, m.sent_at
     FROM messages m JOIN conversations c ON m.conversation_id = c.id
     ORDER BY m.sent_at DESC LIMIT 10`
  ).all()

  return c.json({
    total_conversations: totalConvs?.count ?? 0,
    active_conversations: activeConvs?.count ?? 0,
    total_messages: totalMessages?.count ?? 0,
    total_documents: totalDocs?.count ?? 0,
    pipeline_value: pipeline?.total ?? 0,
    by_stage: byStage.results,
    recent_activity: recentActivity.results,
  })
})

// ─── Conversations List ──────────────────────────────────────

app.get('/api/conversations', async (c) => {
  const db = c.env.DB
  const stage = c.req.query('stage')
  const limit = parseInt(c.req.query('limit') ?? '50')
  const offset = parseInt(c.req.query('offset') ?? '0')

  let query = 'SELECT * FROM conversations'
  const params: unknown[] = []

  if (stage) {
    query += ' WHERE stage = ?'
    params.push(stage)
  }

  query += ' ORDER BY updated_at DESC LIMIT ? OFFSET ?'
  params.push(limit, offset)

  const result = await db.prepare(query).bind(...params).all()

  // Parse JSON fields
  const conversations = result.results.map((row: Record<string, unknown>) => ({
    ...row,
    extracted_info: JSON.parse(row.extracted_info_json as string || '{}'),
    history: JSON.parse(row.history_json as string || '[]'),
  }))

  return c.json({ conversations, count: conversations.length })
})

// ─── Single Conversation Detail ──────────────────────────────

app.get('/api/conversations/:id', async (c) => {
  const db = c.env.DB
  const id = c.req.param('id')

  const conv = await db.prepare(
    'SELECT * FROM conversations WHERE id = ?'
  ).bind(id).first()

  if (!conv) {
    return c.json({ error: 'Conversation not found' }, 404)
  }

  const messages = await db.prepare(
    'SELECT * FROM messages WHERE conversation_id = ? ORDER BY sent_at ASC'
  ).bind(id).all()

  const documents = await db.prepare(
    'SELECT * FROM documents WHERE conversation_id = ? ORDER BY created_at ASC'
  ).bind(id).all()

  return c.json({
    conversation: {
      ...conv,
      extracted_info: JSON.parse(conv.extracted_info_json as string || '{}'),
      history: JSON.parse(conv.history_json as string || '[]'),
    },
    messages: messages.results,
    documents: documents.results,
  })
})

// ─── Analytics ───────────────────────────────────────────────

app.get('/api/analytics', async (c) => {
  const db = c.env.DB

  // Stage funnel: how many conversations reached each stage
  const funnel = await db.prepare(`
    SELECT stage, COUNT(*) as count,
           SUM(json_extract(extracted_info_json, '$.budget_low')) as total_budget
    FROM conversations
    GROUP BY stage
  `).all()

  // Average time between stages (approximate from updated_at)
  const avgDuration = await db.prepare(`
    SELECT stage,
           AVG(julianday(updated_at) - julianday(created_at)) as avg_days
    FROM conversations
    WHERE stage NOT IN ('initial_response')
    GROUP BY stage
  `).all()

  // Top companies by pipeline value
  const topCompanies = await db.prepare(`
    SELECT company_name,
           json_extract(extracted_info_json, '$.budget_low') as budget,
           stage, updated_at
    FROM conversations
    WHERE stage NOT IN ('dead')
    ORDER BY json_extract(extracted_info_json, '$.budget_low') DESC
    LIMIT 10
  `).all()

  // Daily activity (messages per day, last 30 days)
  const dailyActivity = await db.prepare(`
    SELECT date(sent_at) as day, direction, COUNT(*) as count
    FROM messages
    WHERE sent_at >= date('now', '-30 days')
    GROUP BY day, direction
    ORDER BY day ASC
  `).all()

  return c.json({
    funnel: funnel.results,
    avg_duration: avgDuration.results,
    top_companies: topCompanies.results,
    daily_activity: dailyActivity.results,
  })
})

// ─── Sync Endpoint (Bot pushes data here) ────────────────────

app.post('/api/sync/conversations', async (c) => {
  const db = c.env.DB
  const body = await c.req.json<{
    conversations: Array<Record<string, unknown>>
  }>()

  let count = 0
  for (const conv of body.conversations) {
    await db.prepare(`
      INSERT OR REPLACE INTO conversations
      (id, thread_id, email_from, company_name, stage,
       extracted_info_json, history_json,
       created_at, updated_at, next_action_at, last_message_id)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      conv.id, conv.thread_id, conv.email_from, conv.company_name,
      conv.stage, conv.extracted_info_json, conv.history_json,
      conv.created_at, conv.updated_at, conv.next_action_at ?? null,
      conv.last_message_id ?? null
    ).run()
    count++
  }

  await db.prepare(
    'INSERT INTO sync_log (synced_at, record_count) VALUES (?, ?)'
  ).bind(new Date().toISOString(), count).run()

  return c.json({ synced: count })
})

app.post('/api/sync/messages', async (c) => {
  const db = c.env.DB
  const body = await c.req.json<{
    messages: Array<Record<string, unknown>>
  }>()

  let count = 0
  for (const msg of body.messages) {
    await db.prepare(`
      INSERT OR REPLACE INTO messages
      (id, conversation_id, direction, subject, body, message_id, sent_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).bind(
      msg.id, msg.conversation_id, msg.direction, msg.subject,
      msg.body, msg.message_id ?? null, msg.sent_at
    ).run()
    count++
  }

  return c.json({ synced: count })
})

// ─── Health Check ────────────────────────────────────────────

app.get('/api/health', async (c) => {
  const lastSync = await c.env.DB.prepare(
    'SELECT synced_at, record_count FROM sync_log ORDER BY id DESC LIMIT 1'
  ).first()

  return c.json({
    status: 'ok',
    dashboard: c.env.DASHBOARD_TITLE,
    last_sync: lastSync ?? null,
  })
})

export default app
