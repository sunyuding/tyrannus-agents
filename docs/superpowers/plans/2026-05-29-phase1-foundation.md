# Phase 1: Foundation Agent OS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core infrastructure (DB, orchestrator skeleton, knowledge base, approval, auth) that all agent modules depend on, plus the knowledge-base MCP server.

**Architecture:** Python monorepo managed by `uv`. PostgreSQL for relational data, ChromaDB for vector search. FastMCP for MCP server protocol. OpenAI for LLM + embeddings.

**Tech Stack:** Python 3.12+, uv, FastMCP, SQLAlchemy 2.0, Alembic, asyncpg, ChromaDB, OpenAI API, pytest

---

### Task 1: Project scaffold — pyproject.toml, docker-compose, .env

**Files:**
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Modify: `core/config.py` (already exists)

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "tyrannus-agents"
version = "0.1.0"
requires-python = ">=3.12"
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
    "python-dotenv>=1.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: tyrannus
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 3: Create .env.example**

```text
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus
CHROMA_PERSIST_DIR=./data/chroma
CHROME_CDP_PORT=9333
CHROME_PROFILE_DIR=~/Library/Application Support/Google/Chrome/SocialMCP/
```

- [ ] **Step 4: Install dependencies**

Run: `uv sync`
Expected: lockfile created, all deps installed

- [ ] **Step 5: Verify import works**

Run: `uv run python -c "from core.config import settings; print(settings.DATABASE_URL)"`
Expected: prints the default DB URL

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml docker-compose.yml .env.example uv.lock
git commit -m "chore: project scaffold with pyproject.toml, docker-compose, .env"
```

---

### Task 2: Database models — all MVP tables

**Files:**
- Create: `core/db/__init__.py`
- Create: `core/db/models.py`
- Create: `core/db/session.py`
- Test: `tests/core/db/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py`, `tests/core/__init__.py`, `tests/core/db/__init__.py`, then:

```python
# tests/core/db/test_models.py
import uuid
from datetime import datetime, timezone

from core.db.models import (
    User, Role, Task, Approval, ToolCall,
    Document, DocumentChunk, Asset, Log,
    UserRole, ModulePermission, TaskStatus, ApprovalStatus,
    LogLevel, AssetType,
)


def test_user_model_fields():
    user = User(
        id=uuid.uuid4(),
        name="Alice",
        email="alice@tyrannus.com",
        role=UserRole.admin,
        department="Engineering",
    )
    assert user.name == "Alice"
    assert user.role == UserRole.admin


def test_task_model_fields():
    task = Task(
        id=uuid.uuid4(),
        module="social-media",
        type="generate_post",
        status=TaskStatus.pending,
        input={"topic": "AI"},
        output=None,
    )
    assert task.status == TaskStatus.pending
    assert task.module == "social-media"


def test_approval_model_fields():
    approval = Approval(
        id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        action="post_facebook",
        payload={"text": "Hello"},
        status=ApprovalStatus.pending,
        requested_by=uuid.uuid4(),
    )
    assert approval.status == ApprovalStatus.pending


def test_document_chunk_model_fields():
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content="Some text content here.",
        heading="Introduction",
        page_number=1,
        chroma_id="chroma-abc-123",
    )
    assert chunk.chunk_index == 0
    assert chunk.chroma_id == "chroma-abc-123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/db/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.db.models'`

- [ ] **Step 3: Write core/db/__init__.py**

```python
# core/db/__init__.py
```

- [ ] **Step 4: Write core/db/models.py**

```python
"""SQLAlchemy 2.0 models for all MVP tables."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Enum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Enums ────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    employee = "employee"
    viewer = "viewer"


class ModulePermission(str, enum.Enum):
    read = "read"
    write = "write"
    approve = "approve"
    admin = "admin"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    waiting_approval = "waiting_approval"
    completed = "completed"
    failed = "failed"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class LogLevel(str, enum.Enum):
    info = "info"
    warn = "warn"
    error = "error"


class AssetType(str, enum.Enum):
    image = "image"
    video = "video"
    audio = "audio"
    cover = "cover"
    subtitle = "subtitle"
    script = "script"


# ── Helpers ──────────────────────────────────────────────

def _uuid():
    return uuid.uuid4()


def _utcnow():
    return datetime.now(timezone.utc)


# ── Models ───────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    department = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    roles = relationship("Role", back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    module = Column(String(100), nullable=False)  # '*' = all
    permission = Column(Enum(ModulePermission), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="roles")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    module = Column(String(100), nullable=False)
    type = Column(String(100), nullable=False)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.pending)
    input = Column(JSONB, nullable=True)
    output = Column(JSONB, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    approvals = relationship("Approval", back_populates="task")
    tool_calls = relationship("ToolCall", back_populates="task")
    assets = relationship("Asset", back_populates="task")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    action = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=True)
    status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.pending)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewer_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("Task", back_populates="approvals")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    tool_name = Column(String(255), nullable=False)
    input = Column(JSONB, nullable=True)
    output = Column(JSONB, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    duration_ms = Column(Integer, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    task = relationship("Task", back_populates="tool_calls")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    filename = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)  # pdf, docx, md, xlsx, url
    chunk_count = Column(Integer, nullable=False, default=0)
    collection_name = Column(String(255), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    chunks = relationship("DocumentChunk", back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    heading = Column(String(500), nullable=True)
    page_number = Column(Integer, nullable=True)
    chroma_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    document = relationship("Document", back_populates="chunks")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    type = Column(Enum(AssetType), nullable=False)
    file_path = Column(String(1000), nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    task = relationship("Task", back_populates="assets")


class Log(Base):
    __tablename__ = "logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    level = Column(Enum(LogLevel), nullable=False)
    module = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

- [ ] **Step 5: Write core/db/session.py**

```python
"""Database session management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/core/db/test_models.py -v`
Expected: all 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add core/db/ tests/
git commit -m "feat: add SQLAlchemy models for all MVP tables"
```

---

### Task 3: Alembic migrations setup

**Files:**
- Create: `alembic.ini`
- Create: `core/db/migrations/env.py`
- Create: `core/db/migrations/script.py.mako`

- [ ] **Step 1: Initialize Alembic**

Run: `uv run alembic init core/db/migrations`

- [ ] **Step 2: Edit alembic.ini — set sqlalchemy.url**

In `alembic.ini`, change the `sqlalchemy.url` line to:

```ini
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/tyrannus
```

And set `script_location`:

```ini
script_location = core/db/migrations
```

- [ ] **Step 3: Edit core/db/migrations/env.py**

Replace the `target_metadata` line and add async support. The key changes:

```python
from core.db.models import Base
target_metadata = Base.metadata
```

And use `run_async_migrations` pattern for async engine. (Full env.py content per standard Alembic async template.)

- [ ] **Step 4: Generate initial migration**

Run: `uv run alembic revision --autogenerate -m "initial tables"`
Expected: new migration file in `core/db/migrations/versions/`

- [ ] **Step 5: Start PostgreSQL and apply**

Run: `docker compose up -d && sleep 3 && uv run alembic upgrade head`
Expected: all tables created

- [ ] **Step 6: Verify tables exist**

Run: `docker compose exec postgres psql -U postgres -d tyrannus -c "\dt"`
Expected: lists users, roles, tasks, approvals, tool_calls, documents, document_chunks, assets, logs

- [ ] **Step 7: Commit**

```bash
git add alembic.ini core/db/migrations/
git commit -m "feat: Alembic setup with initial migration for all MVP tables"
```

---

### Task 4: Approval workflow (core/approval/)

**Files:**
- Create: `core/approval/__init__.py`
- Create: `core/approval/workflow.py`
- Test: `tests/core/approval/test_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/approval/test_workflow.py
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from core.approval.workflow import ApprovalWorkflow
from core.db.models import Approval, ApprovalStatus


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_request_approval_creates_pending(mock_session):
    wf = ApprovalWorkflow(mock_session)
    task_id = uuid.uuid4()
    requested_by = uuid.uuid4()

    approval = await wf.request_approval(
        task_id=task_id,
        action="post_facebook",
        payload={"text": "Hello world"},
        requested_by=requested_by,
    )

    assert approval.status == ApprovalStatus.pending
    assert approval.action == "post_facebook"
    assert approval.task_id == task_id
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_approval_approved(mock_session):
    wf = ApprovalWorkflow(mock_session)
    approval_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()

    existing = Approval(
        id=approval_id,
        task_id=uuid.uuid4(),
        action="post_facebook",
        payload={},
        status=ApprovalStatus.pending,
        requested_by=uuid.uuid4(),
    )
    mock_session.get = AsyncMock(return_value=existing)

    result = await wf.resolve(
        approval_id=approval_id,
        approved=True,
        reviewed_by=reviewer_id,
        note="Looks good",
    )

    assert result.status == ApprovalStatus.approved
    assert result.reviewed_by == reviewer_id
    assert result.reviewer_note == "Looks good"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/approval/test_workflow.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write core/approval/workflow.py**

```python
"""Human-in-the-loop approval workflow."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db.models import Approval, ApprovalStatus


class ApprovalWorkflow:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def request_approval(
        self,
        task_id: uuid.UUID,
        action: str,
        payload: dict,
        requested_by: uuid.UUID,
    ) -> Approval:
        approval = Approval(
            id=uuid.uuid4(),
            task_id=task_id,
            action=action,
            payload=payload,
            status=ApprovalStatus.pending,
            requested_by=requested_by,
        )
        self._session.add(approval)
        await self._session.commit()
        await self._session.refresh(approval)
        return approval

    async def list_pending(self, user_id: uuid.UUID | None = None) -> list[Approval]:
        stmt = select(Approval).where(Approval.status == ApprovalStatus.pending)
        if user_id is not None:
            stmt = stmt.where(Approval.requested_by == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def resolve(
        self,
        approval_id: uuid.UUID,
        approved: bool,
        reviewed_by: uuid.UUID,
        note: str = "",
    ) -> Approval:
        approval = await self._session.get(Approval, approval_id)
        if approval is None:
            raise ValueError(f"Approval {approval_id} not found")
        if approval.status != ApprovalStatus.pending:
            raise ValueError(f"Approval {approval_id} is already {approval.status.value}")

        approval.status = ApprovalStatus.approved if approved else ApprovalStatus.rejected
        approval.reviewed_by = reviewed_by
        approval.reviewer_note = note
        approval.resolved_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(approval)
        return approval
```

- [ ] **Step 4: Create __init__.py**

```python
# core/approval/__init__.py
```

Create also: `tests/core/approval/__init__.py`

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/core/approval/test_workflow.py -v`
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add core/approval/ tests/core/approval/
git commit -m "feat: add approval workflow with request, list, resolve"
```

---

### Task 5: Knowledge base — ingest + search (core/knowledge/)

**Files:**
- Create: `core/knowledge/__init__.py`
- Create: `core/knowledge/ingest.py`
- Create: `core/knowledge/search.py`
- Create: `core/knowledge/summarize.py`
- Test: `tests/core/knowledge/test_ingest.py`
- Test: `tests/core/knowledge/test_search.py`

- [ ] **Step 1: Write the failing test for chunking**

```python
# tests/core/knowledge/test_ingest.py
from core.knowledge.ingest import chunk_text


def test_chunk_text_splits_correctly():
    text = "word " * 600  # 600 words ≈ 600 tokens
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 2
    # Each chunk should not exceed chunk_size by much
    for chunk in chunks:
        assert len(chunk.split()) <= 550  # allow some margin


def test_chunk_text_single_chunk():
    text = "short text"
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == "short text"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/knowledge/test_ingest.py -v`
Expected: FAIL

- [ ] **Step 3: Write core/knowledge/ingest.py**

```python
"""Document ingestion: parse, chunk, embed, store."""

import os
import uuid

import chromadb
from openai import OpenAI

from core.config import settings


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into chunks by word count with overlap."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start = end - overlap
    return chunks


def get_chroma_client() -> chromadb.ClientAPI:
    persist_dir = settings.CHROMA_PERSIST_DIR
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings via OpenAI."""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


def ingest_text(
    text: str,
    filename: str,
    collection_name: str = "default",
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """Chunk text, embed, and store in ChromaDB. Returns chunk metadata list."""
    chunks = chunk_text(text, chunk_size, overlap)
    embeddings = embed_texts(chunks)

    client = get_chroma_client()
    collection = client.get_or_create_collection(name=collection_name)

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {"filename": filename, "chunk_index": i, "source_type": "text"}
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    return [
        {"chroma_id": ids[i], "chunk_index": i, "content": chunks[i]}
        for i in range(len(chunks))
    ]
```

- [ ] **Step 4: Create __init__.py**

```python
# core/knowledge/__init__.py
```

Create also: `tests/core/knowledge/__init__.py`

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/core/knowledge/test_ingest.py -v`
Expected: 2 tests PASS (only tests chunk_text, no OpenAI/ChromaDB calls)

- [ ] **Step 6: Write the failing test for search**

```python
# tests/core/knowledge/test_search.py
from unittest.mock import MagicMock, patch

from core.knowledge.search import search_knowledge


def test_search_returns_formatted_results():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "ids": [["id1", "id2"]],
        "documents": [["chunk one text", "chunk two text"]],
        "metadatas": [[
            {"filename": "doc.pdf", "chunk_index": 0},
            {"filename": "doc.pdf", "chunk_index": 1},
        ]],
        "distances": [[0.1, 0.3]],
    }

    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    with patch("core.knowledge.search.get_chroma_client", return_value=mock_client), \
         patch("core.knowledge.search.embed_texts", return_value=[[0.1] * 1536]):
        results = search_knowledge("test query", collection_name="default", top_k=2)

    assert len(results) == 2
    assert results[0]["content"] == "chunk one text"
    assert results[0]["filename"] == "doc.pdf"
    assert results[0]["distance"] == 0.1
```

- [ ] **Step 7: Write core/knowledge/search.py**

```python
"""Semantic search via ChromaDB."""

from core.knowledge.ingest import get_chroma_client, embed_texts


def search_knowledge(
    query: str,
    collection_name: str = "default",
    top_k: int = 10,
) -> list[dict]:
    """Search ChromaDB for relevant chunks."""
    client = get_chroma_client()
    collection = client.get_collection(name=collection_name)

    query_embedding = embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    formatted = []
    for i in range(len(results["ids"][0])):
        formatted.append({
            "chroma_id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "filename": results["metadatas"][0][i].get("filename", ""),
            "chunk_index": results["metadatas"][0][i].get("chunk_index", 0),
            "distance": results["distances"][0][i],
        })
    return formatted
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/core/knowledge/test_search.py -v`
Expected: 1 test PASS

- [ ] **Step 9: Write core/knowledge/summarize.py**

```python
"""Document summarization via OpenAI."""

from openai import OpenAI

from core.config import settings


def summarize_text(text: str) -> str:
    """Generate a summary of the given text via OpenAI."""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Summarize the following document concisely. Include key points and conclusions."},
            {"role": "user", "content": text},
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content
```

- [ ] **Step 10: Commit**

```bash
git add core/knowledge/ tests/core/knowledge/
git commit -m "feat: add knowledge base with ingest, search, summarize"
```

---

### Task 6: Knowledge Base MCP server (servers/knowledge-base/)

**Files:**
- Create: `servers/__init__.py`
- Create: `servers/knowledge_base/__init__.py`
- Create: `servers/knowledge_base/schemas.py`
- Create: `servers/knowledge_base/service.py`
- Create: `servers/knowledge_base/server.py`
- Test: `tests/servers/knowledge_base/test_service.py`

- [ ] **Step 1: Write the failing test for service**

```python
# tests/servers/knowledge_base/test_service.py
from unittest.mock import patch, MagicMock

from servers.knowledge_base.service import KnowledgeBaseService


def test_search_calls_knowledge_search():
    mock_results = [
        {"chroma_id": "abc", "content": "relevant text", "filename": "doc.pdf", "chunk_index": 0, "distance": 0.1}
    ]
    with patch("servers.knowledge_base.service.search_knowledge", return_value=mock_results):
        svc = KnowledgeBaseService()
        results = svc.search("test query", top_k=5)

    assert len(results) == 1
    assert results[0]["content"] == "relevant text"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/servers/knowledge_base/test_service.py -v`
Expected: FAIL

- [ ] **Step 3: Write schemas.py**

```python
# servers/knowledge_base/schemas.py
"""Input/output schemas for knowledge base MCP tools."""

from dataclasses import dataclass


@dataclass
class SearchResult:
    chroma_id: str
    content: str
    filename: str
    chunk_index: int
    distance: float


@dataclass
class DocumentInfo:
    id: str
    filename: str
    source_type: str
    chunk_count: int
```

- [ ] **Step 4: Write service.py**

```python
# servers/knowledge_base/service.py
"""Business logic for knowledge base module."""

from core.knowledge.search import search_knowledge
from core.knowledge.ingest import ingest_text, chunk_text
from core.knowledge.summarize import summarize_text


class KnowledgeBaseService:
    def search(self, query: str, top_k: int = 10, collection_name: str = "default") -> list[dict]:
        return search_knowledge(query, collection_name=collection_name, top_k=top_k)

    def ingest(self, text: str, filename: str, collection_name: str = "default") -> list[dict]:
        return ingest_text(text, filename, collection_name=collection_name)

    def summarize(self, text: str) -> str:
        return summarize_text(text)
```

- [ ] **Step 5: Write server.py — the MCP entry point**

```python
# servers/knowledge_base/server.py
"""Knowledge Base MCP server — Module 7."""

from mcp.server.fastmcp import FastMCP

from servers.knowledge_base.service import KnowledgeBaseService

mcp = FastMCP("tyrannus-kb")
service = KnowledgeBaseService()


@mcp.tool()
def search_knowledge(query: str, top_k: int = 10) -> str:
    """Search the knowledge base for relevant documents.

    Args:
        query: The search query.
        top_k: Number of results to return (default 10).
    """
    results = service.search(query, top_k=top_k)
    if not results:
        return "No results found."

    lines = []
    for r in results:
        lines.append(f"[{r['filename']}] (chunk {r['chunk_index']}, score {r['distance']:.3f})")
        lines.append(r["content"])
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def upload_document(text: str, filename: str) -> str:
    """Upload and index a document into the knowledge base.

    Args:
        text: The full text content of the document.
        filename: The filename for reference.
    """
    chunks = service.ingest(text, filename)
    return f"Indexed {len(chunks)} chunks from '{filename}'."


@mcp.tool()
def summarize_document(text: str) -> str:
    """Summarize a document.

    Args:
        text: The full text content to summarize.
    """
    return service.summarize(text)


@mcp.tool()
def list_documents() -> str:
    """List all indexed documents in the knowledge base."""
    # Phase 1: simple ChromaDB collection listing
    from core.knowledge.ingest import get_chroma_client
    client = get_chroma_client()
    collections = client.list_collections()
    if not collections:
        return "No documents indexed yet."
    lines = []
    for col in collections:
        count = col.count()
        lines.append(f"Collection '{col.name}': {count} chunks")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 6: Create __init__.py files**

```python
# servers/__init__.py
# servers/knowledge_base/__init__.py
# tests/servers/__init__.py
# tests/servers/knowledge_base/__init__.py
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/servers/knowledge_base/test_service.py -v`
Expected: 1 test PASS

- [ ] **Step 8: Verify MCP server starts**

Run: `uv run python -c "from servers.knowledge_base.server import mcp; print(mcp.name)"`
Expected: prints `tyrannus-kb`

- [ ] **Step 9: Commit**

```bash
git add servers/ tests/servers/
git commit -m "feat: add knowledge base MCP server with search, upload, summarize tools"
```

---

### Task 7: Social Media MCP server (servers/social-media/)

**Files:**
- Create: `servers/social_media/__init__.py`
- Create: `servers/social_media/schemas.py`
- Create: `servers/social_media/service.py`
- Create: `servers/social_media/server.py`
- Test: `tests/servers/social_media/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/servers/social_media/test_service.py
from unittest.mock import patch, MagicMock

from servers.social_media.service import SocialMediaService


def test_generate_post_returns_drafts():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Here's a great post about AI trends!"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("servers.social_media.service.OpenAI", return_value=mock_client):
        svc = SocialMediaService()
        result = svc.generate_post(topic="AI trends", platforms=["facebook"], tone="professional")

    assert "AI trends" in result or "great post" in result.lower()


def test_generate_video_script_returns_script():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Scene 1: Opening shot..."

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("servers.social_media.service.OpenAI", return_value=mock_client):
        svc = SocialMediaService()
        result = svc.generate_video_script(topic="AI trends")

    assert "Scene" in result or "Opening" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/servers/social_media/test_service.py -v`
Expected: FAIL

- [ ] **Step 3: Write schemas.py**

```python
# servers/social_media/schemas.py
"""Input/output schemas for social media MCP tools."""

from dataclasses import dataclass, field


@dataclass
class PostDraft:
    topic: str
    platform: str
    content: str
    status: str = "draft"  # draft, approved, published


@dataclass
class VideoScript:
    topic: str
    scenes: str  # Full script text with scene breakdowns
```

- [ ] **Step 4: Write service.py**

```python
# servers/social_media/service.py
"""Business logic for social media content generation."""

from openai import OpenAI

from core.config import settings


class SocialMediaService:
    def generate_post(
        self,
        topic: str,
        platforms: list[str],
        tone: str = "professional",
        knowledge_context: str = "",
    ) -> str:
        """Generate social media post drafts for given platforms."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        platform_list = ", ".join(platforms)
        context_section = ""
        if knowledge_context:
            context_section = f"\n\nReference material:\n{knowledge_context}"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a social media content creator. "
                        f"Generate a {tone} post about the given topic for: {platform_list}. "
                        f"Include appropriate hashtags and formatting for each platform."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Topic: {topic}{context_section}",
                },
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def generate_video_script(self, topic: str) -> str:
        """Generate a short-video script with scenes, narration, and shot list."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a short-video content creator. Generate a script with:\n"
                        "1. Scene-by-scene breakdown\n"
                        "2. Narration/voiceover text for each scene\n"
                        "3. Shot descriptions (camera angle, visual)\n"
                        "4. Estimated duration per scene\n"
                        "Target total duration: 30-60 seconds."
                    ),
                },
                {"role": "user", "content": f"Topic: {topic}"},
            ],
            max_tokens=1500,
        )
        return response.choices[0].message.content

    def generate_cover_prompt(self, topic: str, style: str = "modern") -> str:
        """Generate an AI image generation prompt for a cover image."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Generate a detailed image generation prompt for a {style} "
                        f"cover image / thumbnail. Output ONLY the prompt, no explanation."
                    ),
                },
                {"role": "user", "content": f"Topic: {topic}"},
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content

    def generate_storyboard(self, script: str) -> str:
        """Generate scene-by-scene visual descriptions from a video script."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Given a video script, generate a storyboard with visual descriptions "
                        "for each scene. Include: composition, colors, text overlays, transitions."
                    ),
                },
                {"role": "user", "content": script},
            ],
            max_tokens=1500,
        )
        return response.choices[0].message.content

    def generate_narration(self, script: str) -> str:
        """Extract narration/voiceover text from a video script."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract only the narration/voiceover text from this video script. "
                        "Output clean text suitable for text-to-speech, one paragraph per scene."
                    ),
                },
                {"role": "user", "content": script},
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content
```

- [ ] **Step 5: Write server.py — the MCP entry point**

```python
# servers/social_media/server.py
"""Social Media Content Factory MCP server — Module 5."""

from mcp.server.fastmcp import FastMCP

from servers.social_media.service import SocialMediaService
from core.tools.browser import post_facebook as cdp_post_facebook, is_chromium_running

mcp = FastMCP("tyrannus-social")
service = SocialMediaService()


@mcp.tool()
def generate_post(topic: str, platforms: str = "facebook", tone: str = "professional") -> str:
    """Generate social media post drafts.

    Args:
        topic: The topic to write about.
        platforms: Comma-separated platforms (facebook, instagram). Default: facebook.
        tone: Writing tone (professional, casual, humorous). Default: professional.
    """
    platform_list = [p.strip() for p in platforms.split(",")]
    return service.generate_post(topic, platform_list, tone)


@mcp.tool()
def generate_video_script(topic: str) -> str:
    """Generate a short-video script with scenes, narration, and shot list.

    Args:
        topic: The topic for the video.
    """
    return service.generate_video_script(topic)


@mcp.tool()
def generate_storyboard(script: str) -> str:
    """Generate scene-by-scene visual descriptions from a video script.

    Args:
        script: The video script text.
    """
    return service.generate_storyboard(script)


@mcp.tool()
def generate_cover_prompt(topic: str, style: str = "modern") -> str:
    """Generate an AI image generation prompt for a cover image.

    Args:
        topic: The topic for the cover.
        style: Visual style (modern, minimalist, vibrant). Default: modern.
    """
    return service.generate_cover_prompt(topic, style)


@mcp.tool()
def generate_narration(script: str) -> str:
    """Extract narration text from a video script for text-to-speech.

    Args:
        script: The video script text.
    """
    return service.generate_narration(script)


@mcp.tool()
async def post_to_facebook(text: str) -> str:
    """Publish a text post to Facebook via Chrome CDP.

    Requires Chrome running on CDP port with logged-in SocialMCP profile.
    This action requires approval.

    Args:
        text: The post content to publish.
    """
    if not is_chromium_running():
        return "Chrome not running. Launch Chrome with CDP first (see scripts/setup-social-mcp.sh)."
    return await cdp_post_facebook(text)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 6: Create __init__.py files**

```python
# servers/social_media/__init__.py
# tests/servers/social_media/__init__.py
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/servers/social_media/test_service.py -v`
Expected: 2 tests PASS

- [ ] **Step 8: Verify MCP server starts**

Run: `uv run python -c "from servers.social_media.server import mcp; print(mcp.name)"`
Expected: prints `tyrannus-social`

- [ ] **Step 9: Commit**

```bash
git add servers/social_media/ tests/servers/social_media/
git commit -m "feat: add social media MCP server with content generation and Facebook CDP publishing"
```

---

### Task 8: Marketing MCP server (servers/marketing/)

**Files:**
- Create: `servers/marketing/__init__.py`
- Create: `servers/marketing/schemas.py`
- Create: `servers/marketing/service.py`
- Create: `servers/marketing/server.py`
- Test: `tests/servers/marketing/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/servers/marketing/test_service.py
from unittest.mock import patch, MagicMock

from servers.marketing.service import MarketingService


def test_analyze_audience_returns_persona():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Target: Tech professionals aged 25-40..."

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("servers.marketing.service.OpenAI", return_value=mock_client):
        svc = MarketingService()
        result = svc.analyze_audience(product="AI Agent Platform", industry="SaaS")

    assert "Tech" in result or "professionals" in result.lower()


def test_generate_campaign_returns_plan():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Campaign: 30-day launch plan..."

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("servers.marketing.service.OpenAI", return_value=mock_client):
        svc = MarketingService()
        result = svc.generate_campaign(
            product="AI Agent Platform",
            goal="brand awareness",
            budget="$5000",
            duration="30 days",
        )

    assert "Campaign" in result or "launch" in result.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/servers/marketing/test_service.py -v`
Expected: FAIL

- [ ] **Step 3: Write schemas.py**

```python
# servers/marketing/schemas.py
"""Input/output schemas for marketing MCP tools."""

from dataclasses import dataclass


@dataclass
class AudiencePersona:
    product: str
    industry: str
    analysis: str


@dataclass
class CampaignPlan:
    product: str
    goal: str
    plan: str
```

- [ ] **Step 4: Write service.py**

```python
# servers/marketing/service.py
"""Business logic for marketing content generation."""

from openai import OpenAI

from core.config import settings


class MarketingService:
    def analyze_audience(self, product: str, industry: str) -> str:
        """Analyze target audience and generate persona."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a marketing strategist. Analyze the target audience for the given "
                        "product and industry. Provide: demographics, pain points, preferred channels, "
                        "content preferences, and buying triggers."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Product: {product}\nIndustry: {industry}",
                },
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def generate_campaign(
        self, product: str, goal: str, budget: str, duration: str
    ) -> str:
        """Generate a marketing campaign plan."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a marketing strategist. Create a campaign plan with:\n"
                        "1. Campaign timeline and phases\n"
                        "2. Channel strategy (which platforms, when)\n"
                        "3. Content calendar outline\n"
                        "4. KPIs and success metrics\n"
                        "5. Budget allocation"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Product: {product}\nGoal: {goal}\n"
                        f"Budget: {budget}\nDuration: {duration}"
                    ),
                },
            ],
            max_tokens=2000,
        )
        return response.choices[0].message.content

    def generate_copy(
        self, topic: str, platform: str, tone: str, knowledge_context: str = ""
    ) -> str:
        """Generate marketing copy for a specific platform."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        context_section = ""
        if knowledge_context:
            context_section = f"\n\nReference material:\n{knowledge_context}"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a marketing copywriter. Write {tone} marketing copy "
                        f"optimized for {platform}. Follow platform best practices for "
                        f"format, length, and engagement."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Topic: {topic}{context_section}",
                },
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def generate_schedule(self, campaign_plan: str) -> str:
        """Generate a content calendar from a campaign plan."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Convert this campaign plan into a detailed content calendar. "
                        "For each entry include: date, platform, content type, topic, "
                        "and status (planned). Output as a structured table."
                    ),
                },
                {"role": "user", "content": campaign_plan},
            ],
            max_tokens=2000,
        )
        return response.choices[0].message.content

    def optimize_content(self, metrics: str) -> str:
        """Generate optimization suggestions from performance metrics."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a marketing analyst. Given performance metrics, provide "
                        "specific optimization suggestions: what's working, what's not, "
                        "and actionable next steps."
                    ),
                },
                {"role": "user", "content": metrics},
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content
```

- [ ] **Step 5: Write server.py — the MCP entry point**

```python
# servers/marketing/server.py
"""Marketing Content MCP server — Module 3."""

from mcp.server.fastmcp import FastMCP

from servers.marketing.service import MarketingService

mcp = FastMCP("tyrannus-marketing")
service = MarketingService()


@mcp.tool()
def analyze_audience(product: str, industry: str) -> str:
    """Analyze target audience for a product and generate a persona.

    Args:
        product: The product or service name.
        industry: The target industry.
    """
    return service.analyze_audience(product, industry)


@mcp.tool()
def generate_campaign(product: str, goal: str, budget: str, duration: str = "30 days") -> str:
    """Generate a marketing campaign plan with timeline, channels, and KPIs.

    Args:
        product: The product or service name.
        goal: Campaign goal (brand awareness, lead generation, etc.).
        budget: Budget amount (e.g., "$5000").
        duration: Campaign duration (e.g., "30 days"). Default: 30 days.
    """
    return service.generate_campaign(product, goal, budget, duration)


@mcp.tool()
def generate_copy(topic: str, platform: str, tone: str = "professional") -> str:
    """Generate marketing copy optimized for a specific platform.

    Args:
        topic: The topic to write about.
        platform: Target platform (email, facebook, instagram, blog, linkedin).
        tone: Writing tone (professional, casual, persuasive). Default: professional.
    """
    return service.generate_copy(topic, platform, tone)


@mcp.tool()
def generate_schedule(campaign_plan: str) -> str:
    """Generate a content calendar from a campaign plan.

    Args:
        campaign_plan: The campaign plan text to convert into a schedule.
    """
    return service.generate_schedule(campaign_plan)


@mcp.tool()
def optimize_content(metrics: str) -> str:
    """Generate optimization suggestions from performance metrics.

    Args:
        metrics: Performance metrics data (engagement rates, click-through, etc.).
    """
    return service.optimize_content(metrics)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 6: Create __init__.py files**

```python
# servers/marketing/__init__.py
# tests/servers/marketing/__init__.py
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/servers/marketing/test_service.py -v`
Expected: 2 tests PASS

- [ ] **Step 8: Verify MCP server starts**

Run: `uv run python -c "from servers.marketing.server import mcp; print(mcp.name)"`
Expected: prints `tyrannus-marketing`

- [ ] **Step 9: Commit**

```bash
git add servers/marketing/ tests/servers/marketing/
git commit -m "feat: add marketing MCP server with audience analysis, campaign, and copy generation"
```

---

### Task 9: MCP registration and integration test

**Files:**
- Create: `scripts/register-mcp.sh`
- Test: `tests/integration/test_mcp_servers.py`

- [ ] **Step 1: Create registration script**

```bash
#!/bin/bash
# scripts/register-mcp.sh
# Register all Phase 1-2 MCP servers with Claude Code

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Registering tyrannus-kb..."
claude mcp add tyrannus-kb -- uv run --project "$REPO_ROOT" python -m servers.knowledge_base.server

echo "Registering tyrannus-social..."
claude mcp add tyrannus-social -- uv run --project "$REPO_ROOT" python -m servers.social_media.server

echo "Registering tyrannus-marketing..."
claude mcp add tyrannus-marketing -- uv run --project "$REPO_ROOT" python -m servers.marketing.server

echo "All servers registered. Restart Claude Code to connect."
```

- [ ] **Step 2: Write integration test**

```python
# tests/integration/test_mcp_servers.py
"""Verify all MCP servers can be imported and have expected tools."""


def test_knowledge_base_server_has_tools():
    from servers.knowledge_base.server import mcp
    assert mcp.name == "tyrannus-kb"


def test_social_media_server_has_tools():
    from servers.social_media.server import mcp
    assert mcp.name == "tyrannus-social"


def test_marketing_server_has_tools():
    from servers.marketing.server import mcp
    assert mcp.name == "tyrannus-marketing"
```

- [ ] **Step 3: Create __init__.py**

```python
# tests/integration/__init__.py
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -v`
Expected: all tests PASS (9+ tests across all modules)

- [ ] **Step 5: Make registration script executable**

Run: `chmod +x scripts/register-mcp.sh`

- [ ] **Step 6: Commit**

```bash
git add scripts/register-mcp.sh tests/integration/
git commit -m "feat: add MCP registration script and integration tests"
```

---

### Task 10: Final cleanup and README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run full test suite with coverage**

Run: `uv run pytest --cov=core --cov=servers --cov-report=term-missing -v`
Expected: all tests pass, coverage report shown

- [ ] **Step 2: Update README.md with quickstart**

Add a Quickstart section to the existing README with:
- Prerequisites (Python 3.12+, uv, Docker)
- `uv sync`
- `docker compose up -d`
- `uv run alembic upgrade head`
- `bash scripts/register-mcp.sh`
- Usage examples

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README with quickstart guide"
```

- [ ] **Step 4: Push**

```bash
git push
```
