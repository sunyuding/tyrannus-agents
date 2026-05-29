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

```text
tests/
├── conftest.py                    # Shared fixtures (DB session, mock OpenAI, etc.)
├── core/
│   ├── db/
│   │   └── test_models.py         # Model field validation, enum values
│   ├── approval/
│   │   └── test_workflow.py       # Approval request/resolve logic
│   └── knowledge/
│       ├── test_ingest.py         # Chunking, text splitting
│       └── test_search.py         # Search result formatting
├── servers/
│   ├── knowledge_base/
│   │   └── test_service.py        # KB service layer
│   ├── social_media/
│   │   └── test_service.py        # Social media service layer
│   └── marketing/
│       └── test_service.py        # Marketing service layer
├── integration/
│   ├── test_mcp_servers.py        # MCP server import/registration
│   ├── test_db_lifecycle.py       # Real DB: create/read/update across tables
│   ├── test_knowledge_pipeline.py # Real ChromaDB: ingest → search round-trip
│   └── test_approval_db.py        # Real DB: approval workflow end-to-end
└── e2e/
    ├── test_kb_mcp_flow.py        # MCP client → KB server → response
    ├── test_social_mcp_flow.py    # MCP client → Social server → draft
    └── test_full_pipeline.py      # Upload doc → generate post → approval → publish
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

### 1.2 core/approval/workflow — Approval Logic

| # | Test Case | Setup | Action | Expected |
|---|-----------|-------|--------|----------|
| 1 | Request approval creates pending | Mock DB session | `wf.request_approval(task_id, "post_facebook", payload, user_id)` | `approval.status == ApprovalStatus.pending`, `session.add` called, `session.commit` awaited |
| 2 | Resolve approval → approved | Existing pending Approval in mock session | `wf.resolve(approval_id, approved=True, reviewed_by=uid, note="LGTM")` | `status == approved`, `reviewed_by` set, `reviewer_note == "LGTM"` |
| 3 | Resolve approval → rejected | Existing pending Approval | `wf.resolve(approval_id, approved=False, reviewed_by=uid, note="Too risky")` | `status == rejected` |
| 4 | Resolve already-resolved raises | Approval with `status=approved` | `wf.resolve(...)` | Raises `ValueError("already approved")` |
| 5 | Resolve non-existent raises | `session.get` returns None | `wf.resolve(bad_id, ...)` | Raises `ValueError("not found")` |
| 6 | List pending filters by user | Mock session with `execute` returning approvals | `wf.list_pending(user_id=uid)` | Filter applied, correct list returned |

### 1.3 core/knowledge/ingest — Text Chunking

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 1 | Long text splits correctly | `"word " * 600`, chunk_size=500, overlap=50 | `len(chunks) >= 2`, each chunk ≤ 550 words |
| 2 | Short text stays single chunk | `"short text"` | `len(chunks) == 1`, `chunks[0] == "short text"` |
| 3 | Empty text | `""` | `len(chunks) == 1`, `chunks[0] == ""` |
| 4 | Exact boundary | `"word " * 500` | `len(chunks) == 1` |
| 5 | Overlap correctness | `"word_N " * 600`, check overlap region | Last `overlap` words of chunk N == first `overlap` words of chunk N+1 |

### 1.4 core/knowledge/search — Search Result Formatting

| # | Test Case | Mock ChromaDB Response | Expected |
|---|-----------|----------------------|----------|
| 1 | Formats results correctly | `{"ids":[["id1","id2"]], "documents":[["text1","text2"]], "metadatas":[[{...},{...}]], "distances":[[0.1,0.3]]}` | 2 results, correct fields, `results[0]["distance"] == 0.1` |
| 2 | Empty results | `{"ids":[[]], "documents":[[]], "metadatas":[[]], "distances":[[]]}` | Empty list |
| 3 | Missing metadata fields | Metadata without `filename` | `filename == ""` (default) |

### 1.5 servers/knowledge_base/service — KB Service

| # | Test Case | Mock | Expected |
|---|-----------|------|----------|
| 1 | search delegates to core | Patch `search_knowledge` | Returns mock results |
| 2 | ingest delegates to core | Patch `ingest_text` | Returns chunk list |
| 3 | summarize delegates to core | Patch `summarize_text` | Returns summary string |

### 1.6 servers/social_media/service — Social Media Service

| # | Test Case | Mock OpenAI Response | Expected |
|---|-----------|---------------------|----------|
| 1 | generate_post returns content | `"Great post about AI!"` | Result contains response text |
| 2 | generate_video_script returns script | `"Scene 1: Opening..."` | Result contains "Scene" |
| 3 | generate_cover_prompt returns prompt | `"A modern digital art..."` | Non-empty string returned |
| 4 | generate_storyboard returns visuals | `"Scene 1: Wide shot..."` | Non-empty string returned |
| 5 | generate_narration returns text | `"Welcome to our..."` | Non-empty string returned |
| 6 | generate_post with knowledge_context | Mock response, context="company data" | `knowledge_context` included in prompt |

### 1.7 servers/marketing/service — Marketing Service

| # | Test Case | Mock OpenAI Response | Expected |
|---|-----------|---------------------|----------|
| 1 | analyze_audience returns persona | `"Target: Tech pros 25-40..."` | Contains response text |
| 2 | generate_campaign returns plan | `"Campaign: 30-day launch..."` | Contains response text |
| 3 | generate_copy returns copy | `"Introducing our AI..."` | Non-empty string |
| 4 | generate_schedule returns calendar | `"Day 1: Facebook post..."` | Non-empty string |
| 5 | optimize_content returns suggestions | `"Increase posting frequency..."` | Non-empty string |

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

---

## Layer 3: E2E Tests (MCP Protocol)

Full MCP client-server communication. Tests run against actual MCP servers.

### 3.1 Knowledge Base MCP — `test_kb_mcp_flow.py`

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Upload + search | `upload_document(text="AI trends 2026...", filename="trends.txt")` → `search_knowledge(query="AI trends")` | Search returns chunks from `trends.txt` |
| 2 | List documents after upload | `upload_document(...)` → `list_documents()` | Shows collection with chunk count > 0 |
| 3 | Summarize document | `summarize_document(text="Long article about...")` | Returns coherent summary (mock or real LLM) |
| 4 | Search empty KB | `search_knowledge(query="anything")` | `"No results found."` |

### 3.2 Social Media MCP — `test_social_mcp_flow.py`

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Generate Facebook post | `generate_post(topic="AI 趨勢", platforms="facebook", tone="professional")` | Non-empty post with hashtags |
| 2 | Generate video script | `generate_video_script(topic="Product launch")` | Script with scene descriptions |
| 3 | Generate storyboard from script | `generate_storyboard(script="Scene 1:...")` | Visual descriptions per scene |
| 4 | Generate cover prompt | `generate_cover_prompt(topic="AI", style="modern")` | Image generation prompt text |
| 5 | Post to Facebook (CDP) | `post_to_facebook(text="Test post")` | Chrome not running → error message; Chrome running → approval gate or success |
| 6 | Generate narration | `generate_narration(script="Scene 1:...")` | Clean narration text |

### 3.3 Marketing MCP — `test_marketing_mcp_flow.py`  (Phase 3, placeholder)

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Analyze audience | `analyze_audience(product="AI Platform", industry="SaaS")` | Persona with demographics |
| 2 | Generate campaign | `generate_campaign(product="AI Platform", goal="awareness", budget="$5000")` | Plan with timeline + KPIs |
| 3 | Generate copy | `generate_copy(topic="AI trends", platform="linkedin", tone="professional")` | Platform-optimized copy |
| 4 | Generate schedule | `generate_schedule(campaign_plan="...")` | Content calendar table |

### 3.4 Full Pipeline — `test_full_pipeline.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Document → Post pipeline | `upload_document(company data)` → `search_knowledge("product features")` → `generate_post(topic, knowledge_context=search_results)` | Post grounded in company data |
| 2 | Topic → Video content pipeline | `generate_video_script(topic)` → `generate_storyboard(script)` → `generate_narration(script)` → `generate_cover_prompt(topic)` | All 4 artifacts generated, non-empty |
| 3 | Post with approval gate | `generate_post(...)` → `post_to_facebook(draft)` → approval check | Blocked until approval resolved |

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
| `core/approval/workflow.py` | 95%+ | All branches (approve, reject, errors) |
| `core/knowledge/ingest.py` | 85%+ | chunking logic 100%, ingest with mocked deps |
| `core/knowledge/search.py` | 90%+ | formatting logic, empty results |
| `servers/*/service.py` | 80%+ | All service methods via mocked OpenAI |
| `servers/*/server.py` | 70%+ | MCP tool registration verified |
| **Overall** | **80%+** | |
