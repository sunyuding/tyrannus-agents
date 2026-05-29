# Tyrannus Agents — Platform Design Spec

## Overview

Enterprise AI Agent platform built as multiple independent MCP servers. Each agent module is a standalone MCP server that can be registered with Claude Code, Claude Desktop, Codex CLI, or Codex Desktop. Modules share a common core library for database, RAG knowledge base, browser automation, and approval workflows.

**Target user:** Single company (Tyrannus) internal use.
**LLM provider:** OpenAI API (GPT-4o / GPT-4.1).
**Backend:** Python (FastAPI-based MCP servers via FastMCP).
**Interface:** MCP clients (Claude Code, Claude Desktop, Codex CLI, Codex Desktop).

## Architecture

```
MCP Clients (Claude Code / Desktop / Codex)
    │
    ├── mcp add tyrannus-social   → servers/social-media/server.py
    ├── mcp add tyrannus-marketing → servers/marketing/server.py
    ├── mcp add tyrannus-kb       → servers/knowledge-base/server.py
    └── ... (future modules)
            │
            ▼
    ┌─────────────────────────────┐
    │       core/ (shared)        │
    │  ┌──────┐ ┌──────────────┐  │
    │  │  db  │ │  knowledge   │  │
    │  │(PG)  │ │  (ChromaDB)  │  │
    │  └──────┘ └──────────────┘  │
    │  ┌──────┐ ┌──────────────┐  │
    │  │tools │ │  approval    │  │
    │  │(CDP) │ │  (HITL)      │  │
    │  └──────┘ └──────────────┘  │
    └─────────────────────────────┘
```

## Project Structure

```
tyrannus-agents/
├── core/                          # Shared library (Python package)
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── session.py             # DB session management
│   │   └── migrations/            # Alembic migrations
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── ingest.py              # Document parsing, chunking, embedding
│   │   ├── search.py              # Semantic search via ChromaDB
│   │   └── summarize.py           # Document summarization
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── browser.py             # Playwright CDP (extends one-post pattern)
│   │   ├── email.py               # SMTP/Gmail sending
│   │   └── file.py                # File read/write/PDF generation
│   ├── approval/
│   │   ├── __init__.py
│   │   └── workflow.py            # Approval request/review/resolve
│   └── config.py                  # Env vars, shared settings
│
├── servers/                       # Independent MCP servers
│   ├── social-media/
│   │   ├── __init__.py
│   │   └── server.py              # Module 5 MCP server
│   ├── marketing/
│   │   ├── __init__.py
│   │   └── server.py              # Module 3 MCP server
│   ├── knowledge-base/
│   │   ├── __init__.py
│   │   └── server.py              # Module 7 MCP server
│   ├── sales-crm/                 # Future: Module 2
│   ├── customer-service/          # Future: Module 1
│   ├── finance/                   # Future: Module 4
│   ├── it-support/                # Future: Module 6
│   └── orchestrator/              # Future: Module 8 meta-orchestrator
│
├── docs/
│   ├── 8 大 Agent 模組製作流程.docx
│   └── superpowers/specs/         # Design specs
├── tests/
│   ├── core/
│   ├── servers/
│   └── conftest.py
├── pyproject.toml                 # uv workspace, dependencies
├── docker-compose.yml             # PostgreSQL + ChromaDB
├── .env.example
├── .gitignore
└── README.md
```

## Core Library

### Database (core/db/)

PostgreSQL via SQLAlchemy 2.0 + Alembic.

**Tables:**

```
tasks
├── id: UUID (PK)
├── module: str (social-media, marketing, knowledge-base, ...)
├── type: str (generate_post, generate_campaign, ...)
├── status: enum (pending, in_progress, completed, failed)
├── input: JSONB
├── output: JSONB
├── created_at: timestamp
└── updated_at: timestamp

approvals
├── id: UUID (PK)
├── task_id: UUID (FK → tasks)
├── action: str (post_facebook, send_email, ...)
├── payload: JSONB (what will be executed)
├── status: enum (pending, approved, rejected)
├── reviewer_note: str (optional)
├── created_at: timestamp
└── resolved_at: timestamp

tool_calls
├── id: UUID (PK)
├── task_id: UUID (FK → tasks, nullable)
├── tool_name: str (browser.post_facebook, email.send, ...)
├── input: JSONB
├── output: JSONB
├── success: bool
├── duration_ms: int
└── created_at: timestamp

documents
├── id: UUID (PK)
├── filename: str
├── source_type: str (pdf, docx, md, xlsx)
├── chunk_count: int
├── collection_name: str (ChromaDB collection)
├── created_at: timestamp
└── updated_at: timestamp
```

### Knowledge Base (core/knowledge/)

ChromaDB for vector storage. OpenAI embeddings (text-embedding-3-small).

- `ingest(file_path: str) -> Document`: Parse file (PDF/DOCX/MD/Excel via unstructured or python-docx/PyPDF2), chunk at 500 tokens with 50 token overlap, preserve heading metadata, embed and store in ChromaDB.
- `search(query: str, top_k: int = 10) -> list[Chunk]`: Semantic search, returns chunks with source file, page number, and relevance score.
- `summarize(doc_id: str) -> str`: Retrieve all chunks for a document, generate summary via OpenAI.

### Browser Tool (core/tools/browser.py)

Extends the one-post Playwright CDP pattern:
- Connect to Chrome on port 9333 with SocialMCP profile
- Reuse one-post's `post_facebook` and `post_instagram` functions
- Add: `post_with_image`, `post_video`, `read_notifications`, `read_messenger`
- All browser actions logged to `tool_calls` table

### Approval Workflow (core/approval/)

- `request_approval(task_id, action, payload) -> Approval`: Create pending approval.
- `list_pending() -> list[Approval]`: Get all pending approvals.
- `resolve(approval_id, approved: bool, note: str) -> Approval`: Approve or reject.
- High-risk actions that require approval: publishing posts, sending emails, financial operations.

## MCP Server Modules

### Module 5: Social Media Content Factory (servers/social-media/)

MCP server registered as `tyrannus-social`.

**Tools:**

| Tool | Input | Output | Approval Required |
|------|-------|--------|-------------------|
| `generate_post` | topic: str, platforms: list[str] | Multi-platform drafts (JSONB) | No |
| `generate_video_script` | topic: str | Script with scenes, narration, shots | No |
| `generate_cover_prompt` | topic: str, style: str | AI image generation prompt | No |
| `list_drafts` | status: str (optional) | List of draft posts | No |
| `approve_draft` | draft_id: str | Marks draft as approved | No |
| `post_facebook` | draft_id: str OR text: str | Post result | Yes |
| `post_instagram` | draft_id: str OR text: str | Post result | Yes |
| `schedule_post` | draft_id: str, publish_at: datetime | Scheduled task | No |

**Flow:**
1. User says: "幫我產生一篇關於 AI 趨勢的 Facebook 貼文"
2. `generate_post(topic="AI 趨勢", platforms=["facebook"])` → generates draft, saves to DB with status=draft
3. User reviews draft, says "發布" or "修改一下語氣"
4. `post_facebook(draft_id=...)` → checks approval status; if not approved, creates approval request and returns "awaiting approval"
5. User: `approve_draft(draft_id=...)` → marks draft as approved in DB
6. `post_facebook(draft_id=...)` → draft is approved, Browser CDP publishes to Facebook, status=published

### Module 3: Marketing Content (servers/marketing/)

MCP server registered as `tyrannus-marketing`.

**Tools:**

| Tool | Input | Output | Approval Required |
|------|-------|--------|-------------------|
| `analyze_audience` | product: str, industry: str | Audience persona (demographics, pain points, channels) | No |
| `generate_campaign` | product: str, goal: str, budget: str | Campaign plan with timeline, channels, KPIs | No |
| `generate_copy` | topic: str, platform: str, tone: str | Marketing copy for specified platform | No |
| `generate_schedule` | campaign_id: str | Content calendar (dates, platforms, content types) | No |
| `optimize_content` | metrics: dict | Optimization suggestions based on performance data | No |

**Integration with Module 5:** Marketing generates strategy and copy → Social Media handles publishing. They share the same `tasks` and `documents` tables.

### Module 7: Knowledge Base (servers/knowledge-base/) — MVP Subset

MCP server registered as `tyrannus-kb`.

**Tools (MVP only):**

| Tool | Input | Output |
|------|-------|--------|
| `upload_document` | file_path: str | Document metadata + chunk count |
| `search_knowledge` | query: str, top_k: int | Relevant chunks with sources |
| `summarize_document` | doc_id: str | Document summary |
| `list_documents` | — | All indexed documents |

This module is the "brain" — other modules can import `core.knowledge.search` to ground their outputs in company data.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| MCP Framework | FastMCP (mcp[cli]) |
| LLM | OpenAI API (gpt-4o) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (persistent, local) |
| Relational DB | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 + Alembic |
| Browser Automation | Playwright (CDP, port 9333) |
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
]
```

## Environment Variables

```
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
claude mcp add tyrannus-social -- uv run servers/social-media/server.py
claude mcp add tyrannus-marketing -- uv run servers/marketing/server.py
claude mcp add tyrannus-kb -- uv run servers/knowledge-base/server.py
```

## MVP Implementation Order

1. **Core setup** — pyproject.toml, uv workspace, docker-compose, DB models, Alembic
2. **core/knowledge** — ChromaDB ingest + search (enables RAG for all modules)
3. **core/tools/browser** — Port one-post CDP logic into core
4. **core/approval** — Simple approval workflow
5. **servers/knowledge-base** — MCP server with upload, search, summarize tools
6. **servers/social-media** — MCP server with generate_post, post_facebook, approve_draft
7. **servers/marketing** — MCP server with generate_campaign, generate_copy
8. **Integration test** — End-to-end: generate campaign → generate post → approve → publish

## Future Modules (Post-MVP)

| Module | Priority | Notes |
|--------|----------|-------|
| Sales CRM (#2) | High | Email outreach, CRM integration |
| Customer Service (#1) | Medium | Requires chat/ticket system |
| Finance (#4) | Medium | Requires accounting data integration |
| IT Support (#6) | Low | Internal tooling |
| Orchestrator (#8) | Low | Meta-agent that routes across modules |

## Security

- All tool calls logged to `tool_calls` table for audit
- High-risk actions require explicit approval via `core/approval`
- No hardcoded secrets — all credentials via environment variables
- Browser sessions use isolated Chrome profile (SocialMCP)
- Database credentials never exposed through MCP tools
