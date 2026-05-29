# Tyrannus Agents — Test Strategy

## Overview

Three test layers: **Unit** (mocked, fast) → **Integration** (real DB + ChromaDB, mocked LLM) → **E2E** (full MCP protocol, real LLM optional). Target coverage: 80%+.

```text
┌──────────────────────────────────────────────────────────┐
│  E2E Tests (MCP protocol, real servers, approval flow)   │  ← slow, CI nightly
├──────────────────────────────────────────────────────────┤
│  Integration Tests (real DB/ChromaDB, mocked OpenAI)     │  ← medium, CI on push
├──────────────────────────────────────────────────────────┤
│  Unit Tests (all deps mocked, pure logic)                │  ← fast, CI on push
└──────────────────────────────────────────────────────────┘
```

## Test Directory Structure

> **Naming convention:** Server directories in the repo use hyphens (`servers/knowledge-base/`,
> `servers/social-media/`, `servers/sales-crm/`). Test directories use Python-safe underscores
> (`tests/servers/knowledge_base/`, `tests/servers/social_media/`, `tests/servers/sales_crm/`)
> because hyphens are invalid in Python package names. The mapping is always
> `s/-/_/` — replace hyphens with underscores.

```text
tests/
├── conftest.py                        # Shared fixtures (DB session, mock OpenAI, etc.)
├── core/
│   ├── db/
│   │   └── test_models.py             # Model field validation, enum values
│   ├── orchestrator/
│   │   ├── test_router.py             # Intent classification, module routing
│   │   ├── test_executor.py           # Tool dispatch, retry, error handling
│   │   └── test_planner.py            # Task decomposition (Phase 2 stub)
│   ├── auth/
│   │   └── test_permissions.py        # Role-based access, module permission checks
│   ├── approval/
│   │   └── test_workflow.py           # Approval request/resolve logic
│   └── knowledge/
│       ├── test_ingest.py             # Chunking, text splitting
│       └── test_search.py            # Search result formatting
├── servers/
│   ├── knowledge_base/
│   │   └── test_service.py            # KB service layer
│   ├── social_media/
│   │   └── test_service.py            # Social media service layer
│   └── sales_crm/
│       └── test_service.py            # Sales CRM service layer
├── integration/
│   ├── test_mcp_servers.py            # MCP server import/registration
│   ├── test_db_lifecycle.py           # Real DB: create/read/update across tables
│   ├── test_knowledge_pipeline.py     # Real ChromaDB: ingest → search round-trip
│   ├── test_approval_db.py            # Real DB: approval workflow end-to-end
│   ├── test_orchestrator_routing.py   # Real DB: intent → route → log audit trail
│   ├── test_auth_permissions.py       # Real DB: role + module permission enforcement
│   └── test_browser_task_queue.py     # Real DB: browser task queue persistence
└── e2e/
    ├── test_kb_mcp_flow.py            # MCP client → KB server → response
    ├── test_social_mcp_flow.py        # MCP client → Social server → draft
    ├── test_sales_crm_mcp_flow.py     # MCP client → Sales CRM server → leads/outreach
    └── test_full_pipeline.py          # Upload doc → generate post → approval → publish
```

---

## Layer 1: Unit Tests

All external dependencies mocked. No DB, no network, no filesystem.

### 1.1 core/db/models — Model Field Validation

| # | Test Case | Input | Expected | Asserts |
|---|-----------|-------|----------|---------|
| 1 | User model fields | `User(name="Alice", email="a@t.com", role=UserRole.admin, department="Eng")` | Instance created | `user.name == "Alice"`, `user.role == UserRole.admin` |
| 2 | Task model with status | `Task(module="social-media", type="generate_post", status=TaskStatus.pending, input={"topic":"AI"})` | Instance created | `task.status == TaskStatus.pending`, `task.module == "social-media"` |
| 3 | Approval model pending | `Approval(task_id=uuid, action="post_facebook", payload={"text":"hi"}, status=ApprovalStatus.pending, requested_by=uuid)` | Instance created | `approval.status == ApprovalStatus.pending` |
| 4 | DocumentChunk fields | `DocumentChunk(document_id=uuid, chunk_index=0, content="text", heading="Intro", page_number=1, chroma_id="abc")` | Instance created | `chunk.chunk_index == 0`, `chunk.chroma_id == "abc"` |
| 5 | Enum values complete | All enum classes | All members present | `UserRole` has 4, `TaskStatus` has 5, `ApprovalStatus` has 3, `LogLevel` has 3, `AssetType` has 6 |

### 1.2 core/orchestrator/router — Intent Classification & Module Routing

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 1 | Route social media intent | `"幫我產生一篇 Facebook 貼文"` | Routes to `social-media` module |
| 2 | Route knowledge base intent | `"搜尋公司產品文件"` | Routes to `knowledge-base` module |
| 3 | Route sales CRM intent | `"找一下 SaaS 產業的潛在客戶"` | Routes to `sales-crm` module |
| 4 | Unknown intent fallback | `"今天天氣如何"` | Returns `unknown` or raises clear error |
| 5 | Multi-module hint (Phase 2) | `"查知識庫然後產生貼文"` | Returns ordered list `["knowledge-base", "social-media"]` |

### 1.3 core/orchestrator/executor — Tool Dispatch, Retry, Error Handling

| # | Test Case | Setup | Action | Expected |
|---|-----------|-------|--------|----------|
| 1 | Successful dispatch | Mock tool returns result | `executor.dispatch(tool_name, input)` | Result returned, `tool_calls` row logged |
| 2 | Retry on transient failure | Mock tool fails once, succeeds second call | `executor.dispatch(...)` | Retried with backoff, `retry_count == 1`, success logged |
| 3 | Max retries exceeded | Mock tool always fails | `executor.dispatch(...)` | Raises after max retries, `tool_calls` logged with `success=False` |
| 4 | Exponential backoff timing | Mock tool fails 3 times | Check sleep calls | Backoff intervals increase (1s, 2s, 4s) |
| 5 | Audit trail on every dispatch | Any tool call | Check log entries | Log entry created in `logs` table with module, tool_name, input/output |
| 6 | Approval gate blocks execution | Tool marked as high-risk | `executor.dispatch("post_facebook", ...)` | Creates Approval record, returns `waiting_approval` status |

### 1.4 core/auth/permissions — Role-Based Access Control

| # | Test Case | User Role | Module | Action | Expected |
|---|-----------|-----------|--------|--------|----------|
| 1 | Admin accesses any module | `admin` | `social-media` | `check_access(user, module, "write")` | `True` |
| 2 | Manager accesses own dept | `manager` + Role(module="social-media", perm=approve) | `social-media` | `check_access(...)` | `True` |
| 3 | Manager denied other module | `manager` + Role(module="social-media") | `knowledge-base` | `check_access(...)` | `False` |
| 4 | Employee read own tasks | `employee` + Role(module="sales-crm", perm=read) | `sales-crm` | `check_access(..., "read")` | `True` |
| 5 | Employee cannot approve | `employee` | any | `check_access(..., "approve")` | `False` |
| 6 | Viewer read-only | `viewer` + Role(perm=read) | any | `check_access(..., "write")` | `False` |
| 7 | Wildcard module access | Role(module="*", perm=admin) | any module | `check_access(...)` | `True` |

### 1.5 core/approval/workflow — Approval Logic

| # | Test Case | Setup | Action | Expected |
|---|-----------|-------|--------|----------|
| 1 | Request approval creates pending | Mock DB session | `wf.request_approval(task_id, "post_facebook", payload, user_id)` | `approval.status == ApprovalStatus.pending`, `session.add` called, `session.commit` awaited |
| 2 | Resolve approval → approved | Existing pending Approval in mock session | `wf.resolve(approval_id, approved=True, reviewed_by=uid, note="LGTM")` | `status == approved`, `reviewed_by` set, `reviewer_note == "LGTM"` |
| 3 | Resolve approval → rejected | Existing pending Approval | `wf.resolve(approval_id, approved=False, reviewed_by=uid, note="Too risky")` | `status == rejected` |
| 4 | Resolve already-resolved raises | Approval with `status=approved` | `wf.resolve(...)` | Raises `ValueError("already approved")` |
| 5 | Resolve non-existent raises | `session.get` returns None | `wf.resolve(bad_id, ...)` | Raises `ValueError("not found")` |
| 6 | List pending filters by user | Mock session with `execute` returning approvals | `wf.list_pending(user_id=uid)` | Filter applied, correct list returned |

### 1.6 core/knowledge/ingest — Text Chunking

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 1 | Long text splits correctly | `"word " * 600`, chunk_size=500, overlap=50 | `len(chunks) >= 2`, each chunk ≤ 550 words |
| 2 | Short text stays single chunk | `"short text"` | `len(chunks) == 1`, `chunks[0] == "short text"` |
| 3 | Empty text | `""` | `len(chunks) == 1`, `chunks[0] == ""` |
| 4 | Exact boundary | `"word " * 500` | `len(chunks) == 1` |
| 5 | Overlap correctness | `"word_N " * 600`, check overlap region | Last `overlap` words of chunk N == first `overlap` words of chunk N+1 |

### 1.7 core/knowledge/search — Search Result Formatting

| # | Test Case | Mock ChromaDB Response | Expected |
|---|-----------|----------------------|----------|
| 1 | Formats results correctly | `{"ids":[["id1","id2"]], "documents":[["text1","text2"]], "metadatas":[[{...},{...}]], "distances":[[0.1,0.3]]}` | 2 results, correct fields, `results[0]["distance"] == 0.1` |
| 2 | Empty results | `{"ids":[[]], "documents":[[]], "metadatas":[[]], "distances":[[]]}` | Empty list |
| 3 | Missing metadata fields | Metadata without `filename` | `filename == ""` (default) |

### 1.8 servers/knowledge_base/service — KB Service

| # | Test Case | Mock | Expected |
|---|-----------|------|----------|
| 1 | search delegates to core | Patch `search_knowledge` | Returns mock results |
| 2 | ingest delegates to core | Patch `ingest_text` | Returns chunk list |
| 3 | summarize delegates to core | Patch `summarize_text` | Returns summary string |

### 1.9 servers/social_media/service — Social Media Service

| # | Test Case | Mock OpenAI Response | Expected |
|---|-----------|---------------------|----------|
| 1 | generate_post returns content | `"Great post about AI!"` | Result contains response text |
| 2 | generate_video_script returns script | `"Scene 1: Opening..."` | Result contains "Scene" |
| 3 | generate_cover_prompt returns prompt | `"A modern digital art..."` | Non-empty string returned |
| 4 | generate_storyboard returns visuals | `"Scene 1: Wide shot..."` | Non-empty string returned |
| 5 | generate_narration returns text | `"Welcome to our..."` | Non-empty string returned |
| 6 | generate_post with knowledge_context | Mock response, context="company data" | `knowledge_context` included in prompt |

### 1.10 servers/sales_crm/service — Sales CRM Service

| # | Test Case | Mock OpenAI Response | Expected |
|---|-----------|---------------------|----------|
| 1 | find_leads returns company list | `"1. Acme Corp — SaaS..."` | Contains response text |
| 2 | enrich_company returns details | `"Founded 2018, 50 employees..."` | Non-empty string |
| 3 | score_lead returns score + reasoning | `"Score: 85/100. Reasoning:..."` | Contains "Score" |
| 4 | generate_outreach_email returns draft | `"Subject: Partnership..."` | Non-empty string with "Subject" |
| 5 | generate_next_action returns suggestion | `"Schedule follow-up call..."` | Non-empty string |

---

## Layer 2: Integration Tests

Real PostgreSQL (Docker) + real ChromaDB (temp dir). OpenAI mocked.

**Prerequisites:** `docker compose up -d` + `alembic upgrade head`

### 2.1 Database Lifecycle — `test_db_lifecycle.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Create and read User | Insert User → commit → query by email | User found with correct fields |
| 2 | Create Task with parent | Insert parent Task → insert child with `parent_task_id` | Child's `parent_task_id` matches parent |
| 3 | Task status transitions | Create pending → update to `in_progress` → `completed` | Status matches at each step |
| 4 | Create Approval linked to Task | Insert Task → insert Approval with `task_id` | FK relationship intact, `approval.task.module == "social-media"` |
| 5 | Create Document + Chunks | Insert Document → insert 3 DocumentChunks | `doc.chunks` has length 3, chunk_index 0-2 |
| 6 | Log entry with JSON context | Insert Log with `context={"key": "value"}` | JSONB stored and retrieved correctly |
| 7 | ToolCall with duration | Insert ToolCall with `duration_ms=150` | Retrieved with correct duration |
| 8 | Asset linked to Task | Insert Task → insert Asset | `asset.task.id == task.id` |
| 9 | Role permission check | Insert User + Role(module="social-media", permission=write) | Role retrieved via `user.roles` |
| 10 | Unique email constraint | Insert two Users with same email | Raises `IntegrityError` |

### 2.2 Knowledge Pipeline — `test_knowledge_pipeline.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Ingest + search round-trip | Mock OpenAI embeddings → `ingest_text("AI is great", "test.txt")` → `search_knowledge("AI")` | Returns chunks from `test.txt` |
| 2 | Multiple docs, filtered search | Ingest doc A + doc B into same collection → search | Returns results from both docs |
| 3 | Different collections isolated | Ingest into "col_a" and "col_b" → search "col_a" | Only "col_a" results returned |
| 4 | Empty collection search | Search on empty collection | Empty list, no error |
| 5 | Large document chunking | Ingest 10,000-word doc → verify chunk count | `chunk_count >= 20` (at 500 words/chunk) |

### 2.3 Approval with Real DB — `test_approval_db.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Full approval lifecycle | Create user → create task → `request_approval` → `list_pending` → `resolve(approved)` | Status transitions: `pending → approved` |
| 2 | Reject flow | Create approval → resolve(rejected, note="Not ready") | `status == rejected`, `reviewer_note == "Not ready"` |
| 3 | Multiple pending approvals | Create 3 approvals → `list_pending()` | Returns 3 items |
| 4 | Resolve sets timestamps | Create → resolve | `resolved_at` is not None, `resolved_at > created_at` |

### 2.4 Orchestrator Routing — `test_orchestrator_routing.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Route and log audit trail | Send intent → router classifies → executor dispatches mock tool | `logs` table has routing decision entry, `tool_calls` has dispatch record |
| 2 | Retry persists to DB | Mock tool fails once → retries → succeeds | `tool_calls.retry_count == 1`, `success == True` |
| 3 | Failed dispatch logged | Mock tool always fails | `tool_calls.success == False`, `logs` has error entry |
| 4 | Approval gate creates record | Dispatch high-risk tool | `approvals` table has new pending record, `tasks.status == waiting_approval` |

### 2.5 Auth Permissions — `test_auth_permissions.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Admin bypasses all checks | Create admin user → check any module | Access granted |
| 2 | Manager scoped to module | Create manager + Role(module="social-media") → check social-media vs knowledge-base | social-media granted, knowledge-base denied |
| 3 | Employee cannot write without role | Create employee without write role → attempt write | Denied |
| 4 | Wildcard role grants all modules | Create user + Role(module="*", perm=admin) → check any module | Granted |

### 2.6 Browser Task Queue — `test_browser_task_queue.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Task queued and persisted | Create browser task (post_facebook) → commit | Task in DB with `status=pending` |
| 2 | Task status updated after execution | Execute task → update status | `status=completed`, `tool_calls` has duration_ms |
| 3 | Failed task logged | Simulate browser error | `status=failed`, `logs` has error context with screenshot path |
| 4 | Queue ordering | Create 3 tasks → fetch pending ordered by created_at | Returns in FIFO order |

---

## Layer 3: E2E Tests (MCP Protocol)

Full MCP client-server communication. Tests run against actual MCP servers.

> **Tool signatures below match the design spec tool tables.** Where the spec
> defines `file_path` or `doc_id` inputs, tests use those — not raw text.

### 3.1 Knowledge Base MCP — `test_kb_mcp_flow.py`

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Upload + search | `upload_document(file_path="/tmp/trends.txt")` → `search_knowledge(query="AI trends", top_k=5)` | Search returns chunks with source attribution |
| 2 | List documents after upload | `upload_document(file_path=...)` → `list_documents()` | Shows document with chunk count > 0 |
| 3 | Summarize document | `summarize_document(doc_id="<uuid>")` | Returns coherent summary (mock or real LLM) |
| 4 | Compare documents | `compare_documents(doc_id_a="<uuid>", doc_id_b="<uuid>")` | Returns diff highlights |
| 5 | Generate decision brief | `generate_decision_brief(query="Which vendor?", doc_ids=["<uuid>","<uuid>"])` | Brief with cited sources |
| 6 | Search empty KB | `search_knowledge(query="anything")` | `"No results found."` |

### 3.2 Social Media MCP — `test_social_mcp_flow.py`

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Generate Facebook post | `generate_post(topic="AI 趨勢", platforms="facebook", tone="professional")` | Non-empty post with hashtags |
| 2 | Generate video script | `generate_video_script(topic="Product launch")` | Script with scene descriptions |
| 3 | Generate storyboard | `generate_storyboard(script_id="<uuid>")` | Visual descriptions per scene |
| 4 | Generate cover prompt | `generate_cover_prompt(topic="AI", style="modern")` | Image generation prompt text |
| 5 | Generate narration | `generate_narration(script_id="<uuid>")` | Clean narration text for TTS |
| 6 | Generate subtitles | `generate_subtitles(narration_id="<uuid>")` | SRT subtitle content |
| 7 | Post to Facebook (CDP) | `post_facebook(draft_id="<uuid>")` | Approval gate → `waiting_approval`; after approval → success or Chrome error |
| 8 | Post to Facebook (no Chrome) | `post_facebook(draft_id="<uuid>")` with no Chrome running | `"Chrome not running..."` error message |
| 9 | Schedule post | `schedule_post(draft_id="<uuid>", publish_at="2026-06-01T10:00:00Z")` | Scheduled task created |

### 3.3 Sales CRM MCP — `test_sales_crm_mcp_flow.py`

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Find leads | `find_leads(industry="SaaS", criteria="50+ employees")` | Company list with basic info |
| 2 | Enrich company | `enrich_company(company_name="Acme Corp")` | Scraped company details |
| 3 | Score lead | `score_lead(lead_id="<uuid>", icp_criteria="B2B SaaS, 50-200 employees")` | Fit score + reasoning |
| 4 | Generate outreach email | `generate_outreach_email(lead_id="<uuid>", template="intro", tone="professional")` | Personalized email draft |
| 5 | Send email (approval gate) | `send_email(draft_id="<uuid>")` | Approval required → `waiting_approval` |
| 6 | Update CRM | `update_crm(lead_id="<uuid>", note="Positive response")` | CRM record updated confirmation |
| 7 | Schedule followup | `schedule_followup(lead_id="<uuid>", date="2026-06-05", action="call")` | Reminder created |
| 8 | Check replies | `check_replies(lead_id="<uuid>")` | Reply status summary |
| 9 | Generate next action | `generate_next_action(lead_id="<uuid>")` | Suggested next step |

### 3.4 Marketing MCP — Phase 3 placeholder

> **Not active in Phase 1-2.** These tests are defined for future implementation
> and should NOT be included in the CI test suite until the marketing module is built.

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Analyze audience | `analyze_audience(product="AI Platform", industry="SaaS")` | Persona with demographics |
| 2 | Generate campaign | `generate_campaign(product="AI Platform", goal="awareness", budget="$5000", duration="30 days")` | Plan with timeline + KPIs |
| 3 | Generate copy | `generate_copy(topic="AI trends", platform="linkedin", tone="professional")` | Platform-optimized copy |
| 4 | Generate schedule | `generate_schedule(campaign_id="<uuid>")` | Content calendar table |
| 5 | Optimize content | `optimize_content(metrics="CTR 2.1%, engagement 4.5%...")` | Optimization suggestions |
| 6 | Collect campaign metrics | `collect_campaign_metrics(campaign_id="<uuid>")` | Aggregated performance data |

### 3.5 Full Pipeline — `test_full_pipeline.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Document → Post pipeline | `upload_document(file_path=...)` → `search_knowledge(query="product features")` → `generate_post(topic=..., knowledge_query="product features")` | Post grounded in company data |
| 2 | Topic → Video content pipeline | `generate_video_script(topic)` → `generate_storyboard(script_id)` → `generate_narration(script_id)` → `generate_cover_prompt(topic)` | All 4 artifacts generated, non-empty |
| 3 | Post with approval gate | `generate_post(...)` → `post_facebook(draft_id=...)` → approval check | Blocked until approval resolved |
| 4 | CRM outreach pipeline | `find_leads(industry, criteria)` → `score_lead(lead_id, icp)` → `generate_outreach_email(lead_id, ...)` → `send_email(draft_id)` → approval gate | Lead scored, email drafted, blocked at send |
| 5 | Orchestrator routes intent E2E | Send natural language request → orchestrator classifies → dispatches to correct module → returns result | Correct module invoked, audit trail in DB |

---

## Fixtures & Helpers (`tests/conftest.py`)

```python
# Key shared fixtures

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that returns configurable responses."""

@pytest.fixture
async def db_session():
    """Real async DB session for integration tests (uses test database)."""

@pytest.fixture
def temp_chroma_dir(tmp_path):
    """Temporary ChromaDB directory for integration tests."""

@pytest.fixture
def mock_openai_embeddings():
    """Patch embed_texts to return deterministic vectors (no API calls)."""

@pytest.fixture
def sample_user():
    """Pre-built User instance for tests."""

@pytest.fixture
def sample_task():
    """Pre-built Task instance for tests."""

@pytest.fixture
def admin_user():
    """User with admin role + wildcard module access."""

@pytest.fixture
def manager_user():
    """User with manager role + specific module Role entries."""

@pytest.fixture
def mock_tool_registry():
    """Mock MCP tool registry with whitelisted tools per module."""
```

---

## Running Tests

```bash
# Unit tests only (fast, no Docker needed)
uv run pytest tests/core/ tests/servers/ -v --ignore=tests/integration --ignore=tests/e2e

# Integration tests (requires Docker)
docker compose up -d
uv run alembic upgrade head
uv run pytest tests/integration/ -v

# E2E tests (requires Docker + optional Chrome CDP for social media)
uv run pytest tests/e2e/ -v

# Full suite with coverage
uv run pytest --cov=core --cov=servers --cov-report=term-missing -v

# Single module
uv run pytest tests/servers/social_media/ -v

# Skip Phase 3 placeholder tests
uv run pytest tests/ -v --ignore=tests/e2e/test_marketing_mcp_flow.py
```

---

## CI Configuration (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run pytest tests/core/ tests/servers/ -v --ignore=tests/integration --ignore=tests/e2e --cov=core --cov=servers

  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: tyrannus_test
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_test
      - run: uv run pytest tests/integration/ -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_test
```

---

## Coverage Targets

| Module | Target | Notes |
|--------|--------|-------|
| `core/db/models.py` | 90%+ | All models instantiable, all enums tested |
| `core/orchestrator/` | 85%+ | Routing, retry, audit logging, approval gate |
| `core/auth/permissions.py` | 90%+ | All role × module × permission combinations |
| `core/approval/workflow.py` | 95%+ | All branches (approve, reject, errors) |
| `core/knowledge/ingest.py` | 85%+ | Chunking logic 100%, ingest with mocked deps |
| `core/knowledge/search.py` | 90%+ | Formatting logic, empty results |
| `servers/knowledge_base/` | 80%+ | All service methods + MCP tool registration |
| `servers/social_media/` | 80%+ | All service methods via mocked OpenAI |
| `servers/sales_crm/` | 80%+ | All service methods via mocked OpenAI |
| `servers/*/server.py` | 70%+ | MCP tool registration verified |
| **Overall** | **80%+** | |
