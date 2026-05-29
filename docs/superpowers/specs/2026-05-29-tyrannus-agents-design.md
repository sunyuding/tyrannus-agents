# Tyrannus Agents — Platform Design Spec

## Overview

Enterprise AI Agent Automation Platform with 8 modular agents, a cross-system
orchestrator foundation, a Next.js admin dashboard, and role-based permissions.
Each agent module is an independent MCP server that can be registered with
Claude Code, Claude Desktop, Codex CLI, or Codex Desktop. Modules share a
common core library (database, RAG knowledge base, browser automation,
approval/audit, permissions).

This spec is the engineering translation of
`docs/8 大 Agent 模組製作流程.docx`. Where trade-offs are made for phased
delivery, they are called out explicitly.

**Target user:** Single company (Tyrannus) internal use.
**LLM provider:** OpenAI API (GPT-4o / GPT-4.1).
**Backend:** Python (FastAPI + FastMCP).
**Frontend:** Next.js admin dashboard (Phase 3).
**Interface (Phase 1-2):** MCP clients (Claude Code / Desktop / Codex).

## Architecture

```text
Users / Managers / Customers
        │
        ▼
┌─────────────────────────────────────────────────┐
│            Next.js Admin Dashboard               │  ← Phase 3
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
├── servers/                           # Independent MCP servers (one per module)
│   ├── knowledge-base/server.py       # Module 7
│   ├── social-media/server.py         # Module 5
│   ├── sales-crm/server.py           # Module 2
│   ├── marketing/server.py           # Module 3
│   ├── customer-service/server.py    # Module 1
│   ├── finance/server.py             # Module 4
│   └── it-support/server.py          # Module 6
│
├── web/                               # Next.js admin dashboard (Phase 3)
│   └── ...
├── docs/
│   ├── 8 大 Agent 模組製作流程.docx
│   └── superpowers/specs/
├── tests/
├── pyproject.toml                     # uv workspace
├── docker-compose.yml                 # PostgreSQL + ChromaDB
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
approval gate + logging. Multi-step decomposition and cross-module chaining
added in Phase 2.

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
```

**Post-MVP Tables (Phase 3+):**

```text
conversations       # Chat session history (for customer service module)
messages            # Individual messages within conversations
reports             # Generated reports (financial, marketing, etc.)
voice_logs          # STT/TTS interaction records
contacts            # CRM contacts / prospects
deals               # CRM deal pipeline
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

### Module 3: Marketing Content (servers/marketing/)

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

| Tool | Input | Output | Approval |
| ---- | ----- | ------ | -------- |
| `search_prospects` | industry, criteria | Company list with basic info | No |
| `enrich_prospect` | company_name or url | Scraped company details | No |
| `qualify_prospect` | prospect_id, icp_criteria | Fit score + reasoning | No |
| `generate_outreach` | prospect_id, template, tone | Personalized email draft | No |
| `send_outreach` | draft_id | Sends email | Yes |
| `log_crm_note` | prospect_id, note | CRM record updated | No |
| `set_followup` | prospect_id, date, action | Reminder created | No |
| `check_replies` | prospect_id or all | Reply status summary | No |
| `generate_next_action` | prospect_id | Suggested next step | No |

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
| Frontend | Next.js (Phase 3) |
| Package Manager | uv |
| Testing | pytest + pytest-asyncio |

## Dependencies

```toml
[project]
dependencies = [
    "mcp[cli]>=1.0",
    "openai>=1.0",
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

## Environment Variables

```text
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tyrannus
CHROMA_PERSIST_DIR=./data/chroma
CHROME_CDP_PORT=9333
CHROME_PROFILE_DIR=~/Library/Application Support/Google/Chrome/SocialMCP/
```

## Local Development

```bash
# Start infrastructure
docker compose up -d  # PostgreSQL + ChromaDB

# Run migrations
uv run alembic upgrade head

# Start Chrome with CDP (for social media module)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9333 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome/SocialMCP/"

# Register MCP servers
claude mcp add tyrannus-kb -- uv run servers/knowledge-base/server.py
claude mcp add tyrannus-social -- uv run servers/social-media/server.py
claude mcp add tyrannus-sales -- uv run servers/sales-crm/server.py
claude mcp add tyrannus-marketing -- uv run servers/marketing/server.py
```

## Implementation Phases

### Phase 1: Foundation (Orchestrator + Knowledge Base)

Per DOCX: build the orchestrator as Day-1 infrastructure, then the knowledge
base as the shared brain for all modules.

1. **Core setup** — pyproject.toml, uv workspace, docker-compose, .env.example
2. **core/db** — All MVP tables (users, roles, tasks, approvals, tool_calls, documents, document_chunks, assets, logs), Alembic migrations
3. **core/orchestrator (skeleton)** — Intent classification, single-module routing, approval gate, audit logging
4. **core/knowledge** — ChromaDB ingest + search + compare + summarize + decision brief
5. **core/approval** — Approval workflow with role-based permissions
6. **core/auth** — Role-based access control
7. **servers/knowledge-base** — MCP server with all KB tools
8. **Integration test** — Upload doc → search → summarize → decision brief

### Phase 2: High-ROI Modules

Per DOCX: knowledge base (done), social media content factory, sales CRM.

1. **core/tools/browser** — Port one-post CDP logic into core
2. **servers/social-media** — Full content generation + approval + publishing pipeline
3. **servers/sales-crm** — Prospect search, outreach generation, CRM logging
4. **servers/marketing** — Campaign strategy, copywriting, content calendar
5. **core/orchestrator (expanded)** — Multi-step decomposition, cross-module chaining
6. **Integration test** — Campaign → post generation → approval → publish; Prospect → outreach → send

### Phase 3: Enterprise Operations + Dashboard

1. **web/** — Next.js admin dashboard (task tracker, approval UI, metrics, tool registry)
2. **servers/customer-service** — FAQ search, order lookup, ticket creation
3. **servers/finance** — Payment matching, overdue detection, reports
4. **servers/it-support** — Access requests, provisioning, audit
5. **core/tools/tts + stt** — Voice I/O for personal assistant mode
6. **core/tools/video** — Video generation, subtitle burning, thumbnail creation
7. **Post-MVP tables** — conversations, messages, reports, voice_logs, contacts, deals

## Security

- All tool calls logged to `tool_calls` table for audit
- All orchestrator decisions logged to `logs` table
- High-risk actions require explicit approval via `core/approval`
- Role-based permissions enforced at module entry points
- No hardcoded secrets — all credentials via environment variables
- Browser sessions use isolated Chrome profile (SocialMCP)
- Database credentials never exposed through MCP tools
- Tool whitelist per module — agents cannot call tools outside their scope
