# Tyrannus Agents — Platform Design Spec

## Overview

Enterprise AI Agent Automation Platform with 8 modular agents, a cross-system
orchestrator foundation, a Next.js admin dashboard, and role-based permissions.
The 7 business agent modules (Modules 1-7) are independent MCP servers that
can be registered with Claude Code, Claude Desktop, Codex CLI, or Codex
Desktop. Module 8 (Orchestrator) is shared core infrastructure, not a
standalone server. All modules share a common core library (database, RAG
knowledge base, browser automation, approval/audit, permissions).

This spec is the engineering translation of
`docs/8 大 Agent 模組製作流程.docx`. Where trade-offs are made for phased
delivery, they are called out explicitly.

**Target user:** Single company (Tyrannus) internal use.
**LLM provider:** OpenAI API (GPT-4o / GPT-4.1).
**Backend:** Python (FastAPI + FastMCP).
**Frontend:** Next.js admin dashboard (Phase 1 minimal, expanded in Phase 3).
**Interface (Phase 1-2):** MCP clients (Claude Code / Desktop / Codex).

## Architecture

```text
Users / Managers / Customers
        │
        ▼
┌─────────────────────────────────────────────────┐
│            Next.js Admin Dashboard               │  ← Phase 1 minimal
│  (task status, tool registry, metrics, approvals)│
└─────────────────────────────────────────────────┘
        │                       │
        ▼                       ▼
MCP Clients                  REST API
(Claude Code / Desktop)      (FastAPI)
        │                       │
        ▼                       ▼
┌─────────────────────────────────────────────────┐
│         Orchestrator (Module 8 — core)           │  ← Phase 1
│  Task decomposition → tool routing → execution   │
│  Approval gates · retry · logging                │
└─────────────────────────────────────────────────┘
        │
        ├── servers/knowledge-base   (Module 7)
        ├── servers/social-media     (Module 5)
        ├── servers/sales-crm        (Module 2)
        ├── servers/marketing        (Module 3)
        ├── servers/customer-service (Module 1)
        ├── servers/finance          (Module 4)
        └── servers/it-support       (Module 6)
                │
                ▼
┌─────────────────────────────────────────────────┐
│                  Tool Layer                       │
│  API Tools · MCP Tools · Browser Agent (CDP)     │
│  Internal DB · File/Media · Email · TTS/STT      │
└─────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│              Execution Systems                    │
│  CRM · Email · LINE · YouTube · TikTok           │
│  Facebook · Instagram · Stripe · 財務系統         │
│  文件系統 · 影片生成/剪輯工具                      │
└─────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│              Monitoring Layer                     │
│  Logs · Approvals · Retry · Audit · Metrics      │
│  Dashboard                                       │
└─────────────────────────────────────────────────┘
```

## Project Structure

```text
tyrannus-agents/
├── core/                              # Shared library (Python package)
│   ├── orchestrator/                  # Module 8 — task decomposition, routing, retry
│   │   ├── router.py                 # Intent → module routing
│   │   ├── planner.py                # Multi-step task decomposition
│   │   └── executor.py               # Tool dispatch, retry, error handling
│   ├── db/
│   │   ├── models.py                 # SQLAlchemy models (all tables)
│   │   ├── session.py                # DB session management
│   │   └── migrations/               # Alembic migrations
│   ├── knowledge/
│   │   ├── ingest.py                 # Parse, chunk, embed, store
│   │   ├── search.py                 # Semantic search via ChromaDB
│   │   ├── compare.py                # Document comparison
│   │   └── summarize.py              # Document / decision brief summarization
│   ├── tools/
│   │   ├── browser.py                # Playwright CDP (extends one-post)
│   │   ├── email.py                  # SMTP / Gmail API
│   │   ├── file.py                   # File I/O, PDF generation
│   │   ├── tts.py                    # Text-to-Speech (OpenAI TTS API)
│   │   ├── stt.py                    # Speech-to-Text (Whisper API)
│   │   └── video.py                  # Video generation / subtitle helpers
│   ├── approval/
│   │   └── workflow.py               # HITL approval request/review/resolve
│   ├── auth/
│   │   └── permissions.py            # Role-based access control
│   └── config.py                     # Env vars, shared settings
│
├── api/                               # FastAPI REST layer (dashboard backend)
│   ├── server.py                      # FastAPI app, CORS, lifespan
│   ├── deps.py                        # Dependency injection (DB session, current user)
│   ├── middleware/
│   │   ├── auth.py                    # JWT / API key auth middleware
│   │   └── rate_limit.py             # Rate limiting middleware
│   └── routes/
│       ├── tasks.py                   # CRUD tasks, status transitions
│       ├── approvals.py               # List pending, resolve, audit trail
│       ├── logs.py                    # Query logs with filters
│       ├── tools.py                   # Tool registry: list, whitelist, metrics
│       ├── documents.py               # KB document management
│       ├── users.py                   # User management, role assignment
│       └── health.py                  # Health check, readiness probe
│
├── servers/                           # Independent MCP servers (one per module)
│   ├── knowledge-base/               # Module 7
│   │   ├── server.py                 # MCP tool registration & entry point
│   │   ├── service.py                # Business logic
│   │   ├── schemas.py                # Input/output schemas
│   │   └── tests/                    # Module-specific tests
│   ├── social-media/                  # Module 5 (same structure)
│   │   ├── server.py
│   │   ├── service.py
│   │   ├── schemas.py
│   │   └── tests/
│   ├── sales-crm/                     # Module 2 (same structure)
│   │   ├── server.py
│   │   ├── service.py
│   │   ├── schemas.py
│   │   └── tests/
│   ├── marketing/                     # Module 3 — Phase 3
│   ├── customer-service/              # Module 1 — Phase 3
│   ├── finance/                       # Module 4 — Phase 3
│   └── it-support/                    # Module 6 — Phase 3
│
├── web/                               # Next.js admin dashboard (Phase 1 minimal)
│   └── ...
├── docs/
│   ├── 8 大 Agent 模組製作流程.docx
│   └── superpowers/specs/
├── tests/
├── pyproject.toml                     # uv workspace
├── docker-compose.yml                 # PostgreSQL (ChromaDB runs in-process)
├── .env.example
└── README.md
```

## Core Library

### Orchestrator (core/orchestrator/) — Module 8 Foundation

Per DOCX: "第 8 個跨系統流程編排 Agent 應從第一天做成底層架構". The orchestrator
is built as core infrastructure from Phase 1, not as a future module.

**Responsibilities:**

- **Intent classification**: Determine which module(s) a user request maps to.
- **Task decomposition**: Break complex requests into ordered sub-tasks.
- **Tool routing**: Dispatch sub-tasks to the correct module server.
- **Approval gates**: Insert human review checkpoints for high-risk actions.
- **Retry & error handling**: Retry failed tool calls with backoff; log failures.
- **Audit trail**: Every decision and tool call is logged.

**Phase 1 scope (skeleton):** Intent classification + single-module routing +
approval gate + retry with exponential backoff + error handling + audit
logging. Multi-step decomposition and cross-module chaining added in Phase 2.

### Database (core/db/)

PostgreSQL via SQLAlchemy 2.0 + Alembic.

**MVP Tables (Phase 1):**

```text
users
├── id: UUID (PK)
├── name: str
├── email: str (unique)
├── role: enum (admin, manager, employee, viewer)
├── department: str
├── created_at: timestamp
└── updated_at: timestamp

roles
├── id: UUID (PK)
├── user_id: UUID (FK → users)
├── module: str (which module the user can access; '*' = all)
├── permission: enum (read, write, approve, admin)
└── created_at: timestamp

tasks
├── id: UUID (PK)
├── parent_task_id: UUID (FK → tasks, nullable; for sub-task hierarchy)
├── module: str (social-media, marketing, knowledge-base, ...)
├── type: str (generate_post, generate_campaign, ...)
├── status: enum (pending, in_progress, waiting_approval, completed, failed)
├── input: JSONB
├── output: JSONB
├── assigned_to: UUID (FK → users, nullable)
├── created_at: timestamp
└── updated_at: timestamp

approvals
├── id: UUID (PK)
├── task_id: UUID (FK → tasks)
├── action: str (post_facebook, send_email, ...)
├── payload: JSONB
├── status: enum (pending, approved, rejected)
├── requested_by: UUID (FK → users)
├── reviewed_by: UUID (FK → users, nullable)
├── reviewer_note: str
├── created_at: timestamp
└── resolved_at: timestamp

tool_calls
├── id: UUID (PK)
├── task_id: UUID (FK → tasks, nullable)
├── tool_name: str
├── input: JSONB
├── output: JSONB
├── success: bool
├── duration_ms: int
├── retry_count: int
└── created_at: timestamp

documents
├── id: UUID (PK)
├── filename: str
├── source_type: str (pdf, docx, md, xlsx, url)
├── chunk_count: int
├── collection_name: str (ChromaDB collection)
├── uploaded_by: UUID (FK → users, nullable)
├── created_at: timestamp
└── updated_at: timestamp

document_chunks
├── id: UUID (PK)
├── document_id: UUID (FK → documents)
├── chunk_index: int
├── content: text
├── heading: str (nullable)
├── page_number: int (nullable)
├── chroma_id: str (ChromaDB vector ID)
└── created_at: timestamp

assets
├── id: UUID (PK)
├── task_id: UUID (FK → tasks, nullable)
├── type: enum (image, video, audio, cover, subtitle, script)
├── file_path: str
├── metadata: JSONB (duration, resolution, format, etc.)
└── created_at: timestamp

logs
├── id: UUID (PK)
├── task_id: UUID (FK → tasks, nullable)
├── level: enum (info, warn, error)
├── module: str
├── message: text
├── context: JSONB
└── created_at: timestamp

tool_registry
├── id: UUID (PK)
├── module: str (which MCP server owns this tool)
├── tool_name: str (unique)
├── description: text
├── input_schema: JSONB
├── requires_approval: bool
├── allowed_roles: JSONB (list of roles that can invoke)
├── enabled: bool (whitelist toggle)
├── created_at: timestamp
└── updated_at: timestamp

browser_tasks
├── id: UUID (PK)
├── task_id: UUID (FK → tasks, nullable)
├── action: str (post_facebook, post_instagram, read_notifications, ...)
├── payload: JSONB
├── status: enum (queued, running, completed, failed, cancelled)
├── screenshot_path: str (nullable; captured on completion or failure)
├── error_message: text (nullable)
├── retry_count: int
├── timeout_ms: int (default 30000)
├── created_at: timestamp
└── completed_at: timestamp (nullable)

scheduled_posts
├── id: UUID (PK)
├── task_id: UUID (FK → tasks)
├── platform: str (facebook, instagram, youtube, tiktok)
├── draft_content: JSONB (text, images, video_id, etc.)
├── publish_at: timestamp
├── status: enum (scheduled, published, failed, cancelled)
├── published_url: str (nullable)
├── created_at: timestamp
└── updated_at: timestamp

published_posts
├── id: UUID (PK)
├── scheduled_post_id: UUID (FK → scheduled_posts, nullable)
├── platform: str
├── platform_post_id: str (nullable; external platform ID)
├── published_url: str (nullable)
├── published_at: timestamp
├── engagement: JSONB (nullable; likes, shares, comments, views)
└── created_at: timestamp

contacts
├── id: UUID (PK)
├── company_name: str
├── contact_name: str (nullable)
├── email: str (nullable)
├── phone: str (nullable)
├── industry: str (nullable)
├── source: str (find_leads, manual, import)
├── icp_score: int (nullable; 0-100)
├── icp_reasoning: text (nullable)
├── status: enum (new, contacted, replied, qualified, lost)
├── metadata: JSONB (enriched company data)
├── created_at: timestamp
└── updated_at: timestamp

followups
├── id: UUID (PK)
├── contact_id: UUID (FK → contacts)
├── scheduled_date: date
├── action: str (call, email, meeting, demo)
├── status: enum (pending, completed, skipped)
├── note: text (nullable)
├── created_at: timestamp
└── completed_at: timestamp (nullable)

metrics_snapshots
├── id: UUID (PK)
├── module: str
├── metric_type: str (engagement, conversion, pipeline, etc.)
├── data: JSONB (metric payload)
├── period_start: timestamp
├── period_end: timestamp
└── created_at: timestamp
```

**Post-MVP Tables (Phase 3+):**

```text
conversations       # Chat session history (for customer service module)
messages            # Individual messages within conversations
reports             # Generated reports (financial, marketing, etc.)
voice_logs          # STT/TTS interaction records
deals               # CRM deal pipeline (contacts already in Phase 1)
```

### Knowledge Base (core/knowledge/)

ChromaDB for vector storage. OpenAI embeddings (text-embedding-3-small).

- `ingest(file_path) -> Document`: Parse (PDF/DOCX/MD/Excel), chunk at 500 tokens / 50 overlap, preserve headings, embed, store in ChromaDB. Write metadata to `documents` + `document_chunks` tables.
- `search(query, top_k=10, filters=None) -> list[Chunk]`: Semantic search with source attribution (file, page, heading, relevance score).
- `compare(doc_id_a, doc_id_b) -> ComparisonResult`: Side-by-side document comparison highlighting differences.
- `summarize(doc_id) -> str`: Full-document summary via OpenAI.
- `generate_decision_brief(query, context_docs) -> str`: Structured decision brief grounded in retrieved documents, with cited sources.

### Browser Tool (core/tools/browser.py)

Extends the one-post Playwright CDP pattern:

- Connect to Chrome on port 9333 with SocialMCP profile
- Reuse one-post's `post_facebook` and `post_instagram` functions
- Add: `post_with_image`, `post_video`, `read_notifications`, `read_messenger`
- Extensible for any web app without API (e.g., admin consoles for IT module)
- All browser actions logged to `tool_calls` table

### Approval Workflow (core/approval/)

- `request_approval(task_id, action, payload, requested_by) -> Approval`
- `list_pending(user_id=None) -> list[Approval]`
- `resolve(approval_id, approved, reviewed_by, note) -> Approval`
- High-risk actions: publishing posts, sending emails, financial operations, access changes.
- Approval respects role permissions: only users with `approve` permission for the relevant module can resolve.

### Auth & Permissions (core/auth/)

Role-based access control matching DOCX §權限分級:

| Role | Can access | Can approve |
| ---- | ---------- | ----------- |
| admin | All modules, all data | Yes |
| manager | Own department modules | Yes |
| employee | Assigned modules, own tasks | No |
| viewer | Read-only on permitted modules | No |

## MCP Server Modules

### Module 7: Knowledge Base (servers/knowledge-base/)

Registered as `tyrannus-kb`. The "brain" of all other modules.

**Tools:**

| Tool | Input | Output |
| ---- | ----- | ------ |
| `upload_document` | file_path: str | Document metadata + chunk count |
| `search_knowledge` | query: str, top_k: int, filters: dict | Relevant chunks with source attribution |
| `compare_documents` | doc_id_a: str, doc_id_b: str | Comparison result with diff highlights |
| `summarize_document` | doc_id: str | Document summary |
| `generate_decision_brief` | query: str, doc_ids: list | Structured brief with cited sources |
| `list_documents` | source_type: str (optional) | All indexed documents |

Other modules import `core.knowledge.search` to ground their outputs in company data.

### Module 5: Social Media Content Factory (servers/social-media/)

Registered as `tyrannus-social`. Extends one-post.

> Engineering note: This module corresponds to DOCX Module 5 (自媒體文案影片生成與
> 自動發布) plus the publishing capability of DOCX Module 3 (行銷內容生產與發布).
> The marketing module (below) handles strategy and copy; this module handles
> asset creation and publishing.

**Tools (MVP — Phase 2):**

| Tool | Input | Output | Approval |
| ---- | ----- | ------ | -------- |
| `generate_post` | topic, platforms, tone, knowledge_query (optional) | Multi-platform drafts | No |
| `generate_video_script` | topic | Script with scenes, narration, shot list | No |
| `generate_storyboard` | script_id | Scene-by-scene visual descriptions | No |
| `generate_cover_prompt` | topic, style | AI image generation prompt | No |
| `generate_narration` | script_id | Narration text for TTS | No |
| `generate_subtitles` | video_id or narration_id | SRT subtitle file | No |
| `list_drafts` | status (optional) | Draft list | No |
| `approve_draft` | draft_id | Marks as approved | No |
| `post_facebook` | draft_id or text | Post result | Yes |
| `post_instagram` | draft_id or text | Post result | Yes |
| `schedule_post` | draft_id, publish_at | Scheduled task | No |

**Post-MVP tools (Phase 3+):**

| Tool | Description |
| ---- | ----------- |
| `call_tts` | Text-to-Speech via OpenAI TTS API → audio asset |
| `call_video_generator` | Generate video from script + assets |
| `add_subtitles_to_video` | Burn subtitles into video |
| `generate_thumbnail` | Platform-specific thumbnail from cover prompt |
| `collect_metrics` | Scrape engagement data from published posts |
| `optimize_next_batch` | Analyze metrics → generate optimized content suggestions |
| `post_youtube` | Publish to YouTube via API |
| `post_tiktok` | Publish to TikTok via API or CDP |

**Task states (per DOCX):**
`drafting_copy → creating_script → generating_assets → editing_video → waiting_review → publishing → collecting_metrics → optimizing_next_batch`

**Flow:**

1. User: "幫我產生一篇關於 AI 趨勢的 Facebook 貼文"
2. Orchestrator routes to social-media module
3. `generate_post(topic="AI 趨勢", platforms=["facebook"])` → draft saved to DB
4. User reviews, says "發布"
5. `post_facebook(draft_id=...)` → approval gate → awaiting approval
6. User approves → Browser CDP publishes → status=published

### Module 3: Marketing Content (servers/marketing/) — Phase 3

Registered as `tyrannus-marketing`.

> Engineering note: This module covers the strategy, audience analysis, and
> copywriting aspects of DOCX Module 3. Publishing and asset creation are
> handled by Module 5 (social-media). Together they cover the full DOCX
> Module 3 + Module 5 scope.

**Tools:**

| Tool | Input | Output | Approval |
| ---- | ----- | ------ | -------- |
| `analyze_audience` | product, industry | Audience persona | No |
| `generate_campaign` | product, goal, budget, duration | Campaign plan with timeline, channels, KPIs | No |
| `generate_copy` | topic, platform, tone, knowledge_query (optional) | Marketing copy | No |
| `generate_schedule` | campaign_id | Content calendar | No |
| `optimize_content` | metrics | Optimization suggestions | No |
| `collect_campaign_metrics` | campaign_id | Aggregated performance data | No |

### Module 2: Sales Development & CRM (servers/sales-crm/)

Registered as `tyrannus-sales`.

**Tools (MVP — Phase 2):**

Tool names follow DOCX §銷售開發與 CRM Agent.

| Tool | Input | Output | Approval |
| ---- | ----- | ------ | -------- |
| `find_leads` | industry, criteria | Company list with basic info | No |
| `enrich_company` | company_name or url | Scraped company details | No |
| `score_lead` | lead_id, icp_criteria | Fit score + reasoning | No |
| `generate_outreach_email` | lead_id, template, tone | Personalized email draft | No |
| `send_email` | draft_id | Sends email | Yes |
| `update_crm` | lead_id, note | CRM record updated | No |
| `schedule_followup` | lead_id, date, action | Reminder created | No |
| `check_replies` | lead_id or all | Reply status summary | No |
| `generate_next_action` | lead_id | Suggested next step | No |

**Post-MVP:** Full CRM integration (HubSpot / custom), pipeline dashboard, deal tracking.

### Module 1: Customer Service (Phase 3)

| Tool | Description |
| ---- | ----------- |
| `classify_issue` | Classify incoming customer message |
| `search_faq` | Search knowledge base for answer |
| `lookup_order` | Query order status via API |
| `generate_reply` | Draft customer response |
| `escalate_to_human` | Transfer to human agent |
| `create_ticket` | Open support ticket |

### Module 4: Finance (Phase 3)

| Tool | Description |
| ---- | ----------- |
| `import_payments` | Import payment records |
| `match_invoices` | Match invoices to contracts |
| `find_overdue` | Identify overdue accounts |
| `generate_reminder` | Draft collection email |
| `generate_monthly_report` | Financial summary report |
| `generate_cashflow_alert` | Cash flow risk warnings |

### Module 6: IT Support (Phase 3)

| Tool | Description |
| ---- | ----------- |
| `classify_request` | Classify IT request type |
| `check_permissions` | Verify user's current access |
| `evaluate_access_request` | Check against permission rules |
| `provision_access` | Grant access via API or Browser Agent |
| `create_audit_record` | Log access change for compliance |

## REST API Layer (Dashboard Backend)

The Next.js dashboard and any external integrations communicate with the backend
via a FastAPI REST API. This is the HTTP surface for CRUD operations, approvals,
logs, and tool registry management.

### API Server (`api/server.py`)

FastAPI app with:
- CORS configured for dashboard origin (`http://localhost:3000` dev, configurable prod)
- Lifespan handler: connect DB engine on startup, dispose on shutdown
- Auth middleware: JWT or API-key header validation
- Rate limiting: per-IP and per-user token bucket (configurable via env)
- Health endpoints: `/health` (liveness), `/ready` (DB + ChromaDB reachable)

### Routes

| Route | Method | Description | Auth |
|-------|--------|-------------|------|
| **Tasks** | | | |
| `GET /api/tasks` | GET | List tasks (paginated, filterable by module/status/assignee) | read |
| `GET /api/tasks/{id}` | GET | Get task detail with sub-tasks, approvals, tool_calls | read |
| `POST /api/tasks` | POST | Create task (manual trigger) | write |
| `PATCH /api/tasks/{id}` | PATCH | Update task status/assignment | write |
| **Approvals** | | | |
| `GET /api/approvals` | GET | List pending approvals (filterable by module) | read |
| `GET /api/approvals/{id}` | GET | Get approval detail with task context | read |
| `POST /api/approvals/{id}/resolve` | POST | Approve or reject (body: `{approved, note}`) | approve |
| **Logs** | | | |
| `GET /api/logs` | GET | Query logs (filterable by level/module/task_id, paginated) | read |
| **Tool Registry** | | | |
| `GET /api/tools` | GET | List registered tools (with module, approval flag, enabled) | read |
| `PATCH /api/tools/{id}` | PATCH | Toggle enabled, update allowed_roles | admin |
| `GET /api/tools/metrics` | GET | Tool call counts, avg duration, failure rate per tool | read |
| **Documents** | | | |
| `GET /api/documents` | GET | List indexed documents | read |
| `GET /api/documents/{id}` | GET | Document detail with chunk count | read |
| `DELETE /api/documents/{id}` | DELETE | Remove document and chunks from DB + ChromaDB | admin |
| **Users** | | | |
| `GET /api/users` | GET | List users | admin |
| `POST /api/users` | POST | Create user with role | admin |
| `PATCH /api/users/{id}` | PATCH | Update role/department | admin |
| **Health** | | | |
| `GET /health` | GET | Liveness probe (always 200) | none |
| `GET /ready` | GET | Readiness (DB + ChromaDB reachable) | none |

### API Response Envelope

All API responses use a consistent format:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { "total": 42, "page": 1, "limit": 20 }
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "error": { "code": "FORBIDDEN", "message": "Insufficient permissions" },
  "meta": null
}
```

### Auth Middleware

- **Phase 1:** API key in `Authorization: Bearer <key>` header. Keys stored in env,
  mapped to user IDs. Simple but sufficient for single-company internal use.
- **Phase 3:** JWT tokens issued by a login endpoint, refresh token rotation,
  session management.

### Rate Limiting

- Default: 100 requests/min per IP, 300 requests/min per authenticated user.
- Configurable via `API_RATE_LIMIT_PER_IP` and `API_RATE_LIMIT_PER_USER` env vars.
- Returns `429 Too Many Requests` with `Retry-After` header.

## Tech Stack

| Component | Technology |
| --------- | ---------- |
| Language | Python 3.12+ |
| MCP Framework | FastMCP (mcp[cli]) |
| LLM | OpenAI API (gpt-4o) |
| Embeddings | OpenAI text-embedding-3-small |
| TTS | OpenAI TTS API |
| STT | OpenAI Whisper API |
| Vector DB | ChromaDB (persistent, local) |
| Relational DB | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 + Alembic |
| Browser Automation | Playwright (CDP, port 9333) |
| Frontend | Next.js 14+ (Phase 1 minimal, Phase 3 expanded) |
| Frontend Runtime | Node.js 20+ |
| Backend Package Manager | uv |
| Frontend Package Manager | pnpm |
| Testing (backend) | pytest + pytest-asyncio |
| Testing (frontend) | Vitest + Playwright |

## Dependencies

**Backend (pyproject.toml):**

```toml
[project]
dependencies = [
    "mcp[cli]>=1.0",
    "openai>=1.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pyjwt>=2.9",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.13",
    "asyncpg>=0.29",
    "chromadb>=0.5",
    "playwright>=1.40",
    "python-docx>=1.0",
    "pypdf2>=3.0",
    "unstructured>=0.10",
    "python-dotenv>=1.0",
    "httpx>=0.27",
]
```

**Frontend (web/package.json — key dependencies):**

```json
{
  "dependencies": {
    "next": "^14.0",
    "react": "^18.0",
    "react-dom": "^18.0",
    "@tanstack/react-query": "^5.0",
    "tailwindcss": "^3.4"
  }
}
```

## Environment Variables

```text
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tyrannus
CHROMA_PERSIST_DIR=./data/chroma
CHROME_CDP_PORT=9333
CHROME_PROFILE_DIR=~/Library/Application Support/Google/Chrome/SocialMCP/

# API server
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=tyrannus-dev-key-change-me
API_CORS_ORIGINS=http://localhost:3000
API_RATE_LIMIT_PER_IP=100
API_RATE_LIMIT_PER_USER=300

# Deployment
ENV=development  # development | staging | production
LOG_LEVEL=INFO
```

## Local Development

```bash
# Start infrastructure
docker compose up -d  # PostgreSQL (ChromaDB runs in-process, no separate service needed)

# Run migrations
uv run alembic upgrade head

# Start Chrome with CDP (for social media module)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9333 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome/SocialMCP/"

# Register MCP servers (Phase 1-2)
claude mcp add tyrannus-kb -- uv run servers/knowledge-base/server.py
claude mcp add tyrannus-social -- uv run servers/social-media/server.py
claude mcp add tyrannus-sales -- uv run servers/sales-crm/server.py

# Phase 3 servers (register when implemented)
# claude mcp add tyrannus-marketing -- uv run servers/marketing/server.py
# claude mcp add tyrannus-cs -- uv run servers/customer-service/server.py
# claude mcp add tyrannus-finance -- uv run servers/finance/server.py
# claude mcp add tyrannus-it -- uv run servers/it-support/server.py

# Start API server
uv run uvicorn api.server:app --reload --port 8000
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs

# Start minimal dashboard (Phase 1)
cd web && pnpm install && pnpm dev
# Dashboard available at http://localhost:3000 (proxies API to :8000)
```

## MVP Scope

The fastest useful version follows the DOCX MVP target:

1. **Knowledge Base Agent** — upload documents and answer questions with cited sources.
2. **Self-Media Agent** — input a topic and generate copy, short-video script, storyboard, narration, cover prompt, and platform captions.
3. **Publishing Schedule Agent** — route approved drafts to scheduled or immediate publishing through API or Browser Agent.
4. **Minimal Dashboard** — show task status, approvals, published results, and failures.

MVP flow:

```text
Upload document / input topic
→ Agent reads knowledge base
→ Generate self-media content
→ Generate short-video script
→ Generate cover prompt
→ Generate platform captions
→ Human review
→ API publish or Browser Agent publish
→ Dashboard displays result
```

## Implementation Phases

### Phase 1: Foundation Agent OS

Per DOCX: build the orchestrator as Day-1 infrastructure, then the knowledge
base as the shared brain for all modules.

1. **Core setup** — pyproject.toml, uv workspace, docker-compose, .env.example, Dockerfiles
2. **core/db** — All Phase 1 tables (users, roles, tasks, approvals, tool_calls, documents, document_chunks, assets, logs, tool_registry, browser_tasks, scheduled_posts, published_posts, contacts, followups, metrics_snapshots), Alembic migrations
3. **core/orchestrator (skeleton)** — Intent classification, single-module routing, approval gate, retry/error handling with backoff, audit logging
4. **core/knowledge** — ChromaDB ingest + search + compare + summarize + decision brief
5. **core/approval** — Approval workflow with role-based permissions
6. **core/auth** — Role-based access control
7. **core/tool_registry** — Module/tool schema registration, whitelist, permission mapping, enabled toggle
8. **Browser Agent task layer** — Queue model (browser_tasks table), task status, screenshot/log hooks, timeout/retry policy
9. **api/** — FastAPI REST layer with auth middleware, rate limiting, all CRUD routes for dashboard
10. **web/** — Minimal Next.js dashboard for tasks, approvals, logs, and tool registry
11. **servers/knowledge-base** — MCP server with all KB tools
12. **Integration test** — Upload doc → search → summarize → decision brief
13. **CI/CD pipeline** — lint, typecheck, unit, integration, frontend build, migration check, Docker build, security scan

### Phase 2: High-ROI Modules

Per DOCX: knowledge base (done in Phase 1), self-media content factory, and sales CRM.

1. **core/tools/browser** — Port one-post CDP logic into core
2. **servers/social-media** — Full content generation + approval + publishing pipeline
3. **servers/sales-crm** — Prospect search, outreach generation, CRM logging
4. **Publishing schedule workflow** — Schedule approved content to Facebook, Instagram, YouTube/TikTok post-MVP hooks
5. **core/orchestrator (expanded)** — Multi-step decomposition, cross-module chaining
6. **Integration test** — Topic/document → post/video script/cover prompt → approval → publish; Prospect → outreach → send

### Phase 3: Enterprise Operations + Dashboard

1. **web/** — Expand dashboard with metrics, retries, module health, and CRM/content views
2. **servers/customer-service** — FAQ search, order lookup, ticket creation
3. **servers/marketing** — Campaign strategy, copywriting, content calendar, metrics optimization
4. **servers/finance** — Payment matching, overdue detection, reports
5. **servers/it-support** — Access requests, provisioning, audit
6. **core/tools/tts + stt** — Voice I/O for personal assistant mode
7. **core/tools/video** — Video generation, subtitle burning, thumbnail creation
8. **Post-MVP tables** — conversations, messages, reports, voice_logs, deals

## Deployment

### Container Images

```text
# Backend (API + MCP servers)
Dockerfile.backend
├── Base: python:3.12-slim
├── Install: uv, system deps (libpq-dev for asyncpg)
├── Copy: pyproject.toml, uv.lock, core/, api/, servers/
├── CMD: uvicorn api.server:app --host 0.0.0.0 --port 8000
└── HEALTHCHECK: curl -f http://localhost:8000/health

# Frontend (Next.js dashboard)
Dockerfile.web
├── Base: node:20-slim (build stage) + node:20-slim (runtime)
├── Install: pnpm
├── Build: pnpm install && pnpm build
├── CMD: pnpm start
└── HEALTHCHECK: curl -f http://localhost:3000
```

### Docker Compose (Production-like)

> ChromaDB uses `PersistentClient` (in-process, file-based). No separate
> ChromaDB server is needed. The `chromadata` volume persists the index.

```yaml
services:
  postgres:
    image: postgres:16
    volumes: [pgdata:/var/lib/postgresql/data]
    environment: [POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]
    healthcheck:
      test: pg_isready -U postgres
      interval: 5s

  api:
    build: { dockerfile: Dockerfile.backend }
    depends_on: { postgres: { condition: service_healthy } }
    environment: [DATABASE_URL, OPENAI_API_KEY, API_KEY, CHROMA_PERSIST_DIR=/data/chroma]
    volumes: [chromadata:/data/chroma]
    ports: ["8000:8000"]
    healthcheck:
      test: curl -f http://localhost:8000/health
      interval: 10s

  web:
    build: { dockerfile: Dockerfile.web }
    depends_on: [api]
    environment: [NEXT_PUBLIC_API_URL=http://api:8000]
    ports: ["3000:3000"]
    healthcheck:
      test: curl -f http://localhost:3000
      interval: 10s

volumes:
  pgdata:
  chromadata:
```

### Environment Tiers

| Variable | Development | Staging | Production |
|----------|-------------|---------|------------|
| `ENV` | development | staging | production |
| `DATABASE_URL` | localhost:5432/tyrannus | staging-db/tyrannus | prod-db/tyrannus |
| `API_KEY` | dev-key | rotated staging key | rotated prod key |
| `OPENAI_API_KEY` | personal key | org staging key | org prod key |
| `LOG_LEVEL` | DEBUG | INFO | INFO |
| `API_CORS_ORIGINS` | `http://localhost:3000` | staging domain | prod domain |

### Database Operations

- **Migrations:** `alembic upgrade head` run before every deployment. No destructive migrations without explicit approval.
- **Backup:** PostgreSQL `pg_dump` daily (staging), hourly (production). Stored in object storage.
- **Restore:** Tested monthly. Documented in `scripts/db-restore.sh`.
- **ChromaDB persistence:** Volume mount at `CHROMA_PERSIST_DIR`. Backed up alongside PostgreSQL.

### Health Checks

| Endpoint | Check | Healthy Response |
|----------|-------|------------------|
| `GET /health` | API process alive | `200 {"status": "ok"}` |
| `GET /ready` | DB connection + ChromaDB reachable | `200 {"status": "ready", "db": "ok", "chroma": "ok"}` |

### Release Workflow

```text
Code merged to main
  │
  ▼
CI Pipeline (automated)
  ├── Stage 1: lint + typecheck (backend + frontend)
  ├── Stage 2: unit tests (backend + frontend + build)
  ├── Stage 3: integration tests (real DB)
  ├── Stage 4: migration round-trip check
  ├── Stage 5: Docker image build
  ├── Stage 6: security scan (pip-audit, bandit, secret grep)
  └── Stage 7: E2E smoke (backend MCP + frontend Playwright)
  │
  ▼
All gates pass?
  │ No → PR blocked, fix required
  │ Yes ↓
  ▼
Deploy to staging (automated)
  ├── docker compose up (staging env)
  ├── alembic upgrade head
  ├── POST /ready → 200?
  └── Run E2E smoke against staging
  │
  ▼
Staging smoke passes?
  │ No → Rollback staging, alert team
  │ Yes ↓
  ▼
Manual approval (team lead / PM)
  │
  ▼
Deploy to production
  ├── docker compose up (prod env)
  ├── alembic upgrade head
  ├── POST /ready → 200?
  ├── POST /health → 200?
  └── Canary: monitor error rate for 10 min
  │
  ▼
Post-deploy healthy?
  │ No → Rollback: docker compose down + alembic downgrade -1
  │ Yes → Done ✓
```

### Log Retention

- Development: stdout only, no retention.
- Staging: 7 days in `logs` table, structured JSON to stdout.
- Production: 90 days in `logs` table, structured JSON to stdout (forwarded to log aggregator).
- `logs` table rows are append-only. No UPDATE or DELETE permitted on logs (enforced by DB trigger or application-level check).

## Security

### Principles

- All tool calls logged to `tool_calls` table for audit
- All orchestrator decisions logged to `logs` table
- High-risk actions require explicit approval via `core/approval`
- Role-based permissions enforced at module entry points
- No hardcoded secrets — all credentials via environment variables
- Browser sessions use isolated Chrome profile (SocialMCP)
- Database credentials never exposed through MCP tools
- Tool whitelist per module — agents cannot call tools outside their scope

### Pre-Launch Security Checklist

| # | Requirement | Enforcement |
|---|-------------|-------------|
| 1 | Tool whitelist enforced in code | `tool_registry.enabled` checked before every dispatch; unknown tools rejected |
| 2 | Role-based access control tested | Unit + integration tests for all role × module × permission combos |
| 3 | Approval required for high-risk actions | `tool_registry.requires_approval == True` for: publish, send_email, finance ops, access changes |
| 4 | Audit log immutable | `logs` table: no UPDATE/DELETE allowed; append-only enforced |
| 5 | No secrets in logs | `context` JSONB scrubbed of `*_key`, `*_token`, `*_password` fields before insert |
| 6 | API auth on all non-health endpoints | Auth middleware rejects unauthenticated requests with 401 |
| 7 | Rate limiting on API | Per-IP and per-user limits; 429 returned when exceeded |
| 8 | Destructive actions require double confirmation | Delete endpoints (documents, users) require `confirm: true` in request body |
| 9 | No credential exposure through MCP tools | MCP tool outputs never contain DB connection strings, API keys, or tokens |
| 10 | Browser CDP isolated | Chrome runs in SocialMCP profile only; CDP port not exposed externally |
| 11 | CORS restricted | API only accepts requests from configured `API_CORS_ORIGINS` |
| 12 | Input validation at boundaries | All API route handlers validate input with Pydantic models; reject malformed requests |
