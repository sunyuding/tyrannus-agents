# Tyrannus Agents — Test Strategy

## Overview

Three test layers: **Unit** (mocked, fast) → **Integration** (real DB + ChromaDB, mocked LLM) → **E2E** (full MCP protocol + dashboard, real LLM optional). Target coverage: 80%+.

```text
┌──────────────────────────────────────────────────────────┐
│  E2E Tests (MCP protocol, dashboard, approval flow)      │  ← smoke: CI on push (blocking)
│                                                          │    full: CI nightly (informational)
├──────────────────────────────────────────────────────────┤
│  Integration Tests (real DB/ChromaDB, mocked OpenAI)     │  ← CI on push (blocking)
├──────────────────────────────────────────────────────────┤
│  Unit Tests (all deps mocked, pure logic)                │  ← CI on push (blocking)
└──────────────────────────────────────────────────────────┘
```

---

## Test Modes

All E2E and integration tests run in one of three modes, selected by the
`TEST_MODE` environment variable. **CI defaults to `mock`.** Tests that cannot
run in the current mode are automatically skipped.

| Mode | External Services | When to Use | CI Gate? |
|------|-------------------|-------------|----------|
| **mock** | All external services faked (OpenAI, Chrome, Gmail, social platforms) | Every push / PR | Yes — merge blocker |
| **sandbox** | Real DB + ChromaDB, mocked LLM, fake browser target (local HTML page), no real social accounts | Staging deploy | Yes — staging gate |
| **live** | Real OpenAI API, real Chrome CDP, but **never actually publishes** (approval gate always blocks) | Nightly / manual | No — informational |

### Mode Implementation

```python
# tests/conftest.py
import os
import pytest

TEST_MODE = os.environ.get("TEST_MODE", "mock")

def requires_mode(mode: str):
    """Skip test if current TEST_MODE is less than required."""
    order = {"mock": 0, "sandbox": 1, "live": 2}
    return pytest.mark.skipif(
        order.get(TEST_MODE, 0) < order[mode],
        reason=f"Requires TEST_MODE={mode}, current={TEST_MODE}",
    )

# Usage:
# @requires_mode("sandbox")
# async def test_something_with_real_db(): ...
```

### Controllable External Dependencies

| Dependency | mock mode | sandbox mode | live mode |
|------------|-----------|--------------|-----------|
| OpenAI API | `MockOpenAI` fixture returning deterministic responses | Same mock | Real API with low-token limit |
| PostgreSQL | SQLite in-memory or test DB | Real PostgreSQL (Docker) | Real PostgreSQL |
| ChromaDB | In-memory `chromadb.EphemeralClient()` | Persistent client (temp dir) | Persistent client |
| Chrome CDP | Not started; browser tools return canned responses | Playwright launches headless browser against fake social page | Real Chrome with SocialMCP profile; approval blocks publish |
| Email (SMTP) | Mock SMTP server (aiosmtpd) | Same mock | Same mock (never send real email in any mode) |

---

## Test Directory Structure

> **Naming convention:** Server directories in the repo use hyphens (`servers/knowledge-base/`,
> `servers/social-media/`, `servers/sales-crm/`). Test directories use Python-safe underscores
> (`tests/servers/knowledge_base/`, `tests/servers/social_media/`, `tests/servers/sales_crm/`)
> because hyphens are invalid in Python package names. The mapping is always
> `s/-/_/` — replace hyphens with underscores.

```text
tests/
├── conftest.py                          # Shared fixtures, TEST_MODE, mock OpenAI
├── core/
│   ├── db/
│   │   └── test_models.py               # Model field validation, enum values
│   ├── orchestrator/
│   │   ├── test_router.py               # Intent classification, module routing
│   │   ├── test_executor.py             # Tool dispatch, retry, error handling
│   │   └── test_planner.py              # Task decomposition (Phase 2 stub)
│   ├── auth/
│   │   └── test_permissions.py          # Role-based access, module permission checks
│   ├── approval/
│   │   └── test_workflow.py             # Approval request/resolve logic
│   ├── knowledge/
│   │   ├── test_ingest.py               # Chunking, text splitting
│   │   └── test_search.py              # Search result formatting
│   └── tool_registry/
│       └── test_registry.py             # Whitelist, enabled toggle, schema validation
├── api/
│   ├── test_tasks_routes.py             # CRUD tasks, status transitions
│   ├── test_approvals_routes.py         # List pending, resolve, audit trail
│   ├── test_logs_routes.py              # Query logs with filters
│   ├── test_tools_routes.py             # Tool registry CRUD, metrics
│   ├── test_documents_routes.py         # KB document management
│   ├── test_users_routes.py             # User management, role assignment
│   ├── test_health_routes.py            # Health and readiness probes
│   └── test_auth_middleware.py          # Auth validation, rate limiting, CORS
├── servers/
│   ├── knowledge_base/
│   │   └── test_service.py              # KB service layer
│   ├── social_media/
│   │   └── test_service.py              # Social media service layer
│   └── sales_crm/
│       └── test_service.py              # Sales CRM service layer
├── integration/
│   ├── test_mcp_servers.py              # MCP server import/registration
│   ├── test_db_lifecycle.py             # Real DB: create/read/update across tables
│   ├── test_knowledge_pipeline.py       # Real ChromaDB: ingest → search round-trip
│   ├── test_approval_db.py              # Real DB: approval workflow end-to-end
│   ├── test_orchestrator_routing.py     # Real DB: intent → route → log audit trail
│   ├── test_auth_permissions.py         # Real DB: role + module permission enforcement
│   ├── test_tool_registry_db.py         # Real DB: tool whitelist enforcement
│   ├── test_browser_task_queue.py       # Real DB: browser task queue persistence
│   ├── test_api_integration.py          # Real DB: FastAPI routes with TestClient
│   └── test_migration_lifecycle.py      # Alembic: upgrade → downgrade → upgrade
├── e2e/
│   ├── test_kb_mcp_flow.py              # MCP client → KB server → response
│   ├── test_social_mcp_flow.py          # MCP client → Social server → draft
│   ├── test_sales_crm_mcp_flow.py       # MCP client → Sales CRM → leads/outreach
│   ├── test_browser_automation.py       # CDP against fake social page
│   ├── test_full_pipeline.py            # Upload doc → generate post → approval → publish
│   └── test_dashboard_e2e.py            # Playwright: dashboard UI flows
├── browser_fixtures/
│   └── fake_social_page.html            # Minimal HTML mimicking Facebook composer
└── phase3/                              # Phase 3 placeholder tests (NOT in CI)
    ├── test_marketing_mcp_flow.py
    ├── test_finance_mcp_flow.py
    └── test_customer_service_mcp_flow.py
```

---

## Phase 1 Blocking Test Matrix

These tests MUST pass before any merge to main. If any fails, the PR is blocked.

| Component | Test File(s) | # Cases | Priority |
|-----------|-------------|---------|----------|
| **DB models + enums** | `core/db/test_models.py` | 5 | P0 |
| **Orchestrator routing** | `core/orchestrator/test_router.py` | 5 | P0 |
| **Orchestrator retry/logging** | `core/orchestrator/test_executor.py` | 6 | P0 |
| **Auth permissions** | `core/auth/test_permissions.py` | 7 | P0 |
| **Approval workflow** | `core/approval/test_workflow.py` | 6 | P0 |
| **Tool registry whitelist** | `core/tool_registry/test_registry.py` | 6 | P0 |
| **Knowledge chunking** | `core/knowledge/test_ingest.py` | 5 | P0 |
| **Knowledge search** | `core/knowledge/test_search.py` | 3 | P0 |
| **API auth middleware** | `api/test_auth_middleware.py` | 5 | P0 |
| **API tasks routes** | `api/test_tasks_routes.py` | 5 | P0 |
| **API approvals routes** | `api/test_approvals_routes.py` | 4 | P0 |
| **API health routes** | `api/test_health_routes.py` | 2 | P0 |
| **KB service** | `servers/knowledge_base/test_service.py` | 3 | P1 |
| **Social media service** | `servers/social_media/test_service.py` | 6 | P1 |
| **Sales CRM service** | `servers/sales_crm/test_service.py` | 5 | P1 |
| **MCP server registration** | `integration/test_mcp_servers.py` | 3 | P1 |
| **DB lifecycle** | `integration/test_db_lifecycle.py` | 10 | P1 |
| **Migration lifecycle** | `integration/test_migration_lifecycle.py` | 3 | P1 |
| **Total** | | **~99** | |

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
| 6 | Approval gate blocks execution | Tool marked as high-risk in registry | `executor.dispatch("post_facebook", ...)` | Creates Approval record, returns `waiting_approval` status |

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

### 1.6 core/tool_registry — Tool Whitelist & Schema

| # | Test Case | Setup | Action | Expected |
|---|-----------|-------|--------|----------|
| 1 | Registered tool dispatches | Tool in registry, `enabled=True` | `registry.get_tool("search_knowledge")` | Returns tool metadata |
| 2 | Disabled tool blocked | Tool in registry, `enabled=False` | `registry.get_tool(...)` | Raises `ToolDisabledError` |
| 3 | Unregistered tool rejected | Tool not in registry | `registry.get_tool("unknown_tool")` | Raises `ToolNotFoundError` |
| 4 | Approval flag checked | Tool with `requires_approval=True` | `registry.requires_approval("post_facebook")` | Returns `True` |
| 5 | Role whitelist enforced | Tool with `allowed_roles=["admin","manager"]` | `registry.check_role("employee", "post_facebook")` | Returns `False` |
| 6 | Module scope enforced | Tool registered to module "social-media" | `registry.check_module("knowledge-base", "post_facebook")` | Returns `False` |

### 1.7 core/knowledge/ingest — Text Chunking

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 1 | Long text splits correctly | `"word " * 600`, chunk_size=500, overlap=50 | `len(chunks) >= 2`, each chunk ≤ 550 words |
| 2 | Short text stays single chunk | `"short text"` | `len(chunks) == 1`, `chunks[0] == "short text"` |
| 3 | Empty text | `""` | `len(chunks) == 1`, `chunks[0] == ""` |
| 4 | Exact boundary | `"word " * 500` | `len(chunks) == 1` |
| 5 | Overlap correctness | `"word_N " * 600`, check overlap region | Last `overlap` words of chunk N == first `overlap` words of chunk N+1 |

### 1.8 core/knowledge/search — Search Result Formatting

| # | Test Case | Mock ChromaDB Response | Expected |
|---|-----------|----------------------|----------|
| 1 | Formats results correctly | `{"ids":[["id1","id2"]], "documents":[["text1","text2"]], "metadatas":[[{...},{...}]], "distances":[[0.1,0.3]]}` | 2 results, correct fields, `results[0]["distance"] == 0.1` |
| 2 | Empty results | `{"ids":[[]], "documents":[[]], "metadatas":[[]], "distances":[[]]}` | Empty list |
| 3 | Missing metadata fields | Metadata without `filename` | `filename == ""` (default) |

### 1.9 API Routes — Unit Tests (TestClient with mocked DB)

| # | Test File | Test Case | Expected |
|---|-----------|-----------|----------|
| 1 | `test_auth_middleware.py` | Request without auth header | 401 Unauthorized |
| 2 | `test_auth_middleware.py` | Request with invalid API key | 401 Unauthorized |
| 3 | `test_auth_middleware.py` | Request with valid API key | 200, user context set |
| 4 | `test_auth_middleware.py` | Rate limit exceeded | 429 Too Many Requests with Retry-After |
| 5 | `test_auth_middleware.py` | CORS preflight from allowed origin | 200 with correct headers |
| 6 | `test_tasks_routes.py` | GET /api/tasks returns paginated list | 200, `meta.total`, `data` array |
| 7 | `test_tasks_routes.py` | GET /api/tasks?module=social-media filters | 200, all tasks are social-media |
| 8 | `test_tasks_routes.py` | POST /api/tasks creates task | 201, task in response |
| 9 | `test_tasks_routes.py` | PATCH /api/tasks/{id} updates status | 200, status changed |
| 10 | `test_tasks_routes.py` | GET /api/tasks/{id} with sub-tasks | 200, includes approvals/tool_calls |
| 11 | `test_approvals_routes.py` | GET /api/approvals lists pending | 200, only pending items |
| 12 | `test_approvals_routes.py` | POST /api/approvals/{id}/resolve approve | 200, status=approved |
| 13 | `test_approvals_routes.py` | POST /api/approvals/{id}/resolve without approve perm | 403 Forbidden |
| 14 | `test_approvals_routes.py` | POST /api/approvals/{id}/resolve already resolved | 400 Bad Request |
| 15 | `test_health_routes.py` | GET /health | 200 `{"status":"ok"}` |
| 16 | `test_health_routes.py` | GET /ready (DB up) | 200 `{"status":"ready"}` |
| 17 | `test_tools_routes.py` | GET /api/tools lists registry | 200, tools with module/enabled |
| 18 | `test_tools_routes.py` | PATCH /api/tools/{id} toggle enabled (admin) | 200, enabled toggled |
| 19 | `test_tools_routes.py` | PATCH /api/tools/{id} toggle enabled (non-admin) | 403 Forbidden |
| 20 | `test_logs_routes.py` | GET /api/logs?level=error | 200, only error logs |
| 21 | `test_documents_routes.py` | DELETE /api/documents/{id} without confirm | 400, requires confirm:true |

### 1.10 servers/knowledge_base/service — KB Service

| # | Test Case | Mock | Expected |
|---|-----------|------|----------|
| 1 | search delegates to core | Patch `search_knowledge` | Returns mock results |
| 2 | ingest delegates to core | Patch `ingest_text` | Returns chunk list |
| 3 | summarize delegates to core | Patch `summarize_text` | Returns summary string |

### 1.11 servers/social_media/service — Social Media Service

| # | Test Case | Mock OpenAI Response | Expected |
|---|-----------|---------------------|----------|
| 1 | generate_post returns content | `"Great post about AI!"` | Result contains response text |
| 2 | generate_video_script returns script | `"Scene 1: Opening..."` | Result contains "Scene" |
| 3 | generate_cover_prompt returns prompt | `"A modern digital art..."` | Non-empty string returned |
| 4 | generate_storyboard returns visuals | `"Scene 1: Wide shot..."` | Non-empty string returned |
| 5 | generate_narration returns text | `"Welcome to our..."` | Non-empty string returned |
| 6 | generate_post with knowledge_context | Mock response, context="company data" | `knowledge_context` included in prompt |

### 1.12 servers/sales_crm/service — Sales CRM Service

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

### 2.2 New Tables — `test_db_lifecycle.py` (continued)

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 11 | ToolRegistry CRUD | Insert tool → query → toggle enabled | `enabled` toggled, `updated_at` changed |
| 12 | BrowserTask lifecycle | Insert browser_task(queued) → update to running → completed | Status transitions, `completed_at` set |
| 13 | ScheduledPost + PublishedPost | Create scheduled → publish → create published_post | FK chain intact |
| 14 | Contact + Followup | Create contact → create followup → complete followup | `followup.status == completed` |
| 15 | MetricsSnapshot | Insert metrics_snapshot with JSONB data | Retrieved with correct period/data |

### 2.3 Knowledge Pipeline — `test_knowledge_pipeline.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Ingest + search round-trip | Mock OpenAI embeddings → `ingest_text(...)` → `search_knowledge(...)` | Returns chunks from ingested doc |
| 2 | Multiple docs, filtered search | Ingest doc A + doc B into same collection → search | Returns results from both docs |
| 3 | Different collections isolated | Ingest into "col_a" and "col_b" → search "col_a" | Only "col_a" results returned |
| 4 | Empty collection search | Search on empty collection | Empty list, no error |
| 5 | Large document chunking | Ingest 10,000-word doc → verify chunk count | `chunk_count >= 20` (at 500 words/chunk) |

### 2.4 Approval with Real DB — `test_approval_db.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Full approval lifecycle | Create user → create task → `request_approval` → `list_pending` → `resolve(approved)` | Status transitions: `pending → approved` |
| 2 | Reject flow | Create approval → resolve(rejected, note="Not ready") | `status == rejected`, `reviewer_note == "Not ready"` |
| 3 | Multiple pending approvals | Create 3 approvals → `list_pending()` | Returns 3 items |
| 4 | Resolve sets timestamps | Create → resolve | `resolved_at` is not None, `resolved_at > created_at` |

### 2.5 Orchestrator Routing — `test_orchestrator_routing.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Route and log audit trail | Send intent → router classifies → executor dispatches mock tool | `logs` table has routing decision entry, `tool_calls` has dispatch record |
| 2 | Retry persists to DB | Mock tool fails once → retries → succeeds | `tool_calls.retry_count == 1`, `success == True` |
| 3 | Failed dispatch logged | Mock tool always fails | `tool_calls.success == False`, `logs` has error entry |
| 4 | Approval gate creates record | Dispatch high-risk tool | `approvals` table has new pending record, `tasks.status == waiting_approval` |

### 2.6 Auth Permissions — `test_auth_permissions.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Admin bypasses all checks | Create admin user → check any module | Access granted |
| 2 | Manager scoped to module | Create manager + Role(module="social-media") → check social-media vs knowledge-base | social-media granted, knowledge-base denied |
| 3 | Employee cannot write without role | Create employee without write role → attempt write | Denied |
| 4 | Wildcard role grants all modules | Create user + Role(module="*", perm=admin) → check any module | Granted |

### 2.7 Tool Registry — `test_tool_registry_db.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Register tool and query | Insert tool_registry row → query by tool_name | Found with correct module, schema |
| 2 | Disabled tool blocks dispatch | Insert tool with `enabled=False` → attempt dispatch via executor | Dispatch raises `ToolDisabledError`, logs entry |
| 3 | Approval flag propagates | Insert tool with `requires_approval=True` → dispatch | Creates approval record before execution |
| 4 | Role whitelist enforced in DB | Insert tool with `allowed_roles=["admin"]` → check employee access | Returns `False` |

### 2.8 Browser Task Queue — `test_browser_task_queue.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Task queued and persisted | Create browser_task(post_facebook) → commit | Task in DB with `status=queued` |
| 2 | Task status updated after execution | Execute task → update status | `status=completed`, `completed_at` set |
| 3 | Failed task logged | Simulate browser error | `status=failed`, `error_message` set, `screenshot_path` populated |
| 4 | Queue ordering | Create 3 tasks → fetch queued ordered by created_at | Returns in FIFO order |
| 5 | Timeout enforced | Create task with `timeout_ms=100` → simulate slow execution | `status=failed`, `error_message` contains "timeout" |

### 2.9 API Integration — `test_api_integration.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Tasks CRUD round-trip | POST → GET → PATCH → GET | All transitions visible |
| 2 | Approvals resolve via API | Create task + approval in DB → POST /api/approvals/{id}/resolve | Approval resolved, task status updated |
| 3 | Tool registry admin toggle | GET /api/tools → PATCH toggle enabled → GET | Tool disabled |
| 4 | Logs query with filters | Insert logs → GET /api/logs?level=error&module=social-media | Only matching logs returned |
| 5 | Pagination works | Insert 50 tasks → GET /api/tasks?page=2&limit=10 | Returns 10 items, `meta.total=50`, `meta.page=2` |

### 2.10 Migration Lifecycle — `test_migration_lifecycle.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Upgrade from empty | `alembic upgrade head` on fresh DB | All tables created, no errors |
| 2 | Downgrade to base | `alembic downgrade base` | All tables dropped |
| 3 | Round-trip | upgrade head → downgrade base → upgrade head | No migration drift or errors |

---

## Layer 3: E2E Tests (MCP Protocol + Dashboard)

Full MCP client-server communication and dashboard UI tests.

> **Tool signatures below match the design spec tool tables.** Where the spec
> defines `file_path` or `doc_id` inputs, tests use those — not raw text.

### 3.1 Knowledge Base MCP — `test_kb_mcp_flow.py`

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Upload + search | `upload_document(file_path="/tmp/trends.txt")` → `search_knowledge(query="AI trends", top_k=5)` | Search returns chunks with source attribution |
| 2 | List documents after upload | `upload_document(file_path=...)` → `list_documents()` | Shows document with chunk count > 0 |
| 3 | Summarize document | `summarize_document(doc_id="<uuid>")` | Returns coherent summary |
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
| 7 | Post to Facebook (approval gate) | `post_facebook(draft_id="<uuid>")` | Creates pending approval, does NOT publish |
| 8 | Post to Facebook (no Chrome) | `post_facebook(draft_id="<uuid>")` with no Chrome running | `"Chrome not running..."` error |
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

### 3.4 Browser Automation — `test_browser_automation.py`

Uses a **fake social page** (`tests/browser_fixtures/fake_social_page.html`) instead
of real Facebook. Playwright launches headless Chrome and navigates to the local fixture.

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Composer opens | Navigate to fake page → click composer button | Dialog appears |
| 2 | Text entered | Open composer → type message | Content visible in editor |
| 3 | Post button clicked | Open composer → type → click Post | Dialog closes, success logged |
| 4 | Screenshot captured on success | Complete post flow | Screenshot saved to artifacts dir |
| 5 | Screenshot captured on failure | Simulate broken page → attempt post | `browser_tasks.screenshot_path` set |
| 6 | Timeout triggers failure | Set `timeout_ms=100` → slow page | `status=failed`, error="timeout" |
| 7 | Retry on transient failure | Page loads slow first time, fast on retry | `retry_count=1`, `status=completed` |

### 3.5 Dashboard E2E — `test_dashboard_e2e.py`

Playwright tests against the Next.js dashboard. API backed by test DB.

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Task list renders | Seed tasks → open dashboard → navigate to tasks | Task list visible with correct count |
| 2 | Task detail shows sub-items | Click task row | Shows approvals, tool_calls, logs for that task |
| 3 | Approval flow | Seed pending approval → open approvals page → click Approve | Approval status changes, task status updates |
| 4 | Approval rejection | Seed pending → Reject with note | Status=rejected, note visible |
| 5 | Tool registry view | Seed tool_registry → open tools page | Tools listed with enabled/disabled toggle |
| 6 | Tool toggle (admin) | Click disable toggle as admin | Tool shows disabled, API confirms |
| 7 | Error state display | Seed failed task → open task detail | Shows error message, retry count, failed tool_calls |
| 8 | Log viewer with filters | Seed logs → open logs page → filter by error level | Only error logs shown |

### 3.6 Full Pipeline — `test_full_pipeline.py`

| # | Test Case | Steps | Verification |
|---|-----------|-------|--------------|
| 1 | Document → Post pipeline | `upload_document(file_path=...)` → `search_knowledge(query="product features")` → `generate_post(topic=..., knowledge_query="product features")` | Post grounded in company data |
| 2 | Topic → Video content pipeline | `generate_video_script(topic)` → `generate_storyboard(script_id)` → `generate_narration(script_id)` → `generate_cover_prompt(topic)` | All 4 artifacts generated, non-empty |
| 3 | Post with approval gate | `generate_post(...)` → `post_facebook(draft_id=...)` → approval check | Blocked until approval resolved |
| 4 | CRM outreach pipeline | `find_leads(industry, criteria)` → `score_lead(lead_id, icp)` → `generate_outreach_email(lead_id, ...)` → `send_email(draft_id)` → approval gate | Lead scored, email drafted, blocked at send |
| 5 | Orchestrator routes intent E2E | Send natural language request → orchestrator classifies → dispatches to correct module → returns result | Correct module invoked, audit trail in DB |
| 6 | Dashboard reflects pipeline state | Run pipeline #3 → open dashboard → check task/approval status | Dashboard shows correct statuses at each stage |

### 3.7 Marketing MCP — Phase 3 placeholder

> **Not active in Phase 1-2.** These tests live in `tests/phase3/` and are
> excluded from CI until the marketing module is built.

| # | Test Case | MCP Tool Call | Expected Response |
|---|-----------|--------------|-------------------|
| 1 | Analyze audience | `analyze_audience(product="AI Platform", industry="SaaS")` | Persona with demographics |
| 2 | Generate campaign | `generate_campaign(product="AI Platform", goal="awareness", budget="$5000", duration="30 days")` | Plan with timeline + KPIs |
| 3 | Generate copy | `generate_copy(topic="AI trends", platform="linkedin", tone="professional")` | Platform-optimized copy |
| 4 | Generate schedule | `generate_schedule(campaign_id="<uuid>")` | Content calendar table |
| 5 | Optimize content | `optimize_content(metrics="CTR 2.1%, engagement 4.5%...")` | Optimization suggestions |
| 6 | Collect campaign metrics | `collect_campaign_metrics(campaign_id="<uuid>")` | Aggregated performance data |

---

## Fixtures & Helpers (`tests/conftest.py`)

```python
# Key shared fixtures

TEST_MODE = os.environ.get("TEST_MODE", "mock")

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
    """Mock tool registry with whitelisted tools per module."""

@pytest.fixture
def api_client():
    """FastAPI TestClient with auth header pre-set."""

@pytest.fixture
def fake_social_page(tmp_path):
    """Serve fake_social_page.html on a local port for browser tests."""

@pytest.fixture
def headless_browser():
    """Playwright headless Chromium for browser automation tests."""
```

---

## Frontend Test Requirements

The minimal Phase 1 dashboard must pass these checks in CI.

### Test Stack

| Tool | Purpose |
|------|---------|
| Vitest | Unit/component tests |
| Playwright | E2E browser tests |
| ESLint | Lint |
| TypeScript | Type checking |

### CI Commands

```bash
cd web
pnpm install
pnpm lint          # ESLint
pnpm type-check    # tsc --noEmit
pnpm test          # Vitest unit tests
pnpm build         # Next.js production build (catches build errors)
pnpm playwright test  # Dashboard E2E tests
```

### Frontend Test Cases

| # | Test File | Test Case | Type |
|---|-----------|-----------|------|
| 1 | `web/__tests__/api-client.test.ts` | API client handles 401 → redirect to login | Unit |
| 2 | `web/__tests__/api-client.test.ts` | API client includes auth header | Unit |
| 3 | `web/__tests__/api-client.test.ts` | API client handles pagination meta | Unit |
| 4 | `web/__tests__/components/task-list.test.tsx` | Task list renders items | Component |
| 5 | `web/__tests__/components/approval-card.test.tsx` | Approval card shows approve/reject buttons | Component |
| 6 | `web/__tests__/components/tool-toggle.test.tsx` | Tool toggle switches enabled state | Component |
| 7 | `web/e2e/tasks.spec.ts` | Navigate to tasks, see list | E2E |
| 8 | `web/e2e/approvals.spec.ts` | Approve a pending item | E2E |
| 9 | `web/e2e/tools.spec.ts` | Toggle tool disabled | E2E |
| 10 | `web/e2e/error-states.spec.ts` | Failed task shows error details | E2E |

### API Mock Layer

Frontend E2E tests run against a mock API server (MSW or similar) in `mock` mode,
or against the real FastAPI server in `sandbox` mode. This is configured via
`NEXT_PUBLIC_API_URL` environment variable.

---

## Running Tests

```bash
# Unit tests only (fast, no Docker needed)
TEST_MODE=mock uv run pytest tests/core/ tests/servers/ tests/api/ -v \
  --ignore=tests/integration --ignore=tests/e2e --ignore=tests/phase3

# Integration tests (requires Docker)
docker compose up -d
uv run alembic upgrade head
TEST_MODE=sandbox uv run pytest tests/integration/ -v

# E2E tests — mock mode (no real external services)
TEST_MODE=mock uv run pytest tests/e2e/ -v

# E2E tests — sandbox mode (real DB, fake browser page)
TEST_MODE=sandbox uv run pytest tests/e2e/ -v

# E2E tests — live mode (real OpenAI, real Chrome, manual/nightly only)
TEST_MODE=live uv run pytest tests/e2e/ -v

# Full backend suite with coverage
TEST_MODE=mock uv run pytest --cov=core --cov=servers --cov=api --cov-report=term-missing -v \
  --ignore=tests/phase3

# Frontend
cd web && pnpm lint && pnpm type-check && pnpm test && pnpm build && pnpm playwright test

# Single module
uv run pytest tests/servers/social_media/ -v

# Skip Phase 3 placeholder tests
uv run pytest tests/ -v --ignore=tests/phase3
```

---

## CI/CD Pipeline — Full Release Gates

> **ChromaDB note:** ChromaDB uses `PersistentClient` (in-process, file-based).
> No separate ChromaDB service is needed in Docker or CI. Tests use
> `EphemeralClient()` (mock mode) or `PersistentClient(tmp_path)` (sandbox mode).
> The `/ready` endpoint checks ChromaDB by attempting to list collections on
> the in-process client.

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on: [push, pull_request]

jobs:
  # ── Stage 1: Lint & Typecheck (fast, catch syntax issues) ──
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run ruff check .
      - run: uv run mypy core/ api/ servers/ --ignore-missing-imports

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd web && pnpm install
      - run: cd web && pnpm lint
      - run: cd web && pnpm type-check

  # ── Stage 2: Unit Tests (no Docker, fast) ──
  backend-unit:
    needs: backend-lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: >
          TEST_MODE=mock uv run pytest
          tests/core/ tests/servers/ tests/api/ -v
          --ignore=tests/integration --ignore=tests/e2e --ignore=tests/phase3
          --cov=core --cov=servers --cov=api --cov-report=xml
      - uses: codecov/codecov-action@v4

  frontend-unit:
    needs: frontend-lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd web && pnpm install
      - run: cd web && pnpm test -- --coverage
      - run: cd web && pnpm build

  # ── Stage 3: Integration Tests (real DB, Docker) ──
  backend-integration:
    needs: backend-unit
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: tyrannus_test
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_test
      - run: >
          TEST_MODE=sandbox uv run pytest tests/integration/ -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_test

  # ── Stage 4: Migration Check ──
  migration-check:
    needs: backend-unit
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: tyrannus_migration_test }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_migration_test
      - run: uv run alembic downgrade base
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_migration_test
      - run: uv run alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_migration_test

  # ── Stage 5: Docker Build ──
  docker-build:
    needs: [backend-integration, frontend-unit, migration-check]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -f Dockerfile.backend -t tyrannus-api:test .
      - run: docker build -f Dockerfile.web -t tyrannus-web:test .

  # ── Stage 6: Security Scan ──
  security-scan:
    needs: backend-unit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run pip-audit
      - run: uv run bandit -r core/ api/ servers/ -ll
      - name: Check no secrets in code
        run: |
          ! grep -rn 'sk-[a-zA-Z0-9]\{20,\}' core/ api/ servers/ --include='*.py'

  # ── Stage 7a: Backend E2E Smoke (blocking) ──
  backend-e2e-smoke:
    needs: [backend-integration]
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: tyrannus_e2e }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: uv run alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_e2e
      - run: >
          TEST_MODE=sandbox uv run pytest
          tests/e2e/test_kb_mcp_flow.py
          tests/e2e/test_full_pipeline.py::test_post_with_approval_gate
          tests/e2e/test_browser_automation.py
          -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_e2e

  # ── Stage 7b: Frontend E2E ──
  frontend-e2e:
    needs: [backend-integration, frontend-unit]
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: tyrannus_e2e }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: uv sync --dev
      - run: uv run alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_e2e
      - run: uv run uvicorn api.server:app --port 8000 &
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus_e2e
          API_KEY: test-ci-key
      - run: cd web && pnpm install && pnpm build
      - run: cd web && npx playwright install --with-deps chromium
      - run: cd web && pnpm playwright test
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000

  # ── Nightly: Live E2E (not a merge gate) ──
  # Runs with TEST_MODE=live, real OpenAI, real Chrome CDP
  # Configured separately in .github/workflows/nightly.yml
  # NOT a blocking gate — informational only
```

### Release Gate Summary

| Gate | Stage | Blocks Merge? | Blocks Deploy? |
|------|-------|---------------|----------------|
| Backend lint + typecheck | 1 | Yes | Yes |
| Frontend lint + typecheck | 1 | Yes | Yes |
| Backend unit tests | 2 | Yes | Yes |
| Frontend unit tests + build | 2 | Yes | Yes |
| Backend integration tests | 3 | Yes | Yes |
| Migration round-trip | 4 | Yes | Yes |
| Docker image builds | 5 | No | Yes |
| Security scan (pip-audit, bandit, secret grep) | 6 | Yes | Yes |
| Backend E2E smoke (KB, approval, fake publish) | 7a | Yes | Yes |
| Frontend E2E (Playwright) | 7b | No | Yes (staging) |
| Staging deploy + smoke | post-merge | N/A | Yes (production) |
| Live E2E (nightly) | nightly | No | No |
| **Manual approval** | post-staging | N/A | Yes (production) |
| Post-deploy health check | post-prod | N/A | Rollback if fails |

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
| `core/tool_registry/` | 90%+ | Whitelist, enable/disable, role check, module scope |
| `api/` | 80%+ | All routes, auth middleware, error handling |
| `servers/knowledge_base/` | 80%+ | All service methods + MCP tool registration |
| `servers/social_media/` | 80%+ | All service methods via mocked OpenAI |
| `servers/sales_crm/` | 80%+ | All service methods via mocked OpenAI |
| `servers/*/server.py` | 70%+ | MCP tool registration verified |
| **Overall** | **80%+** | |
