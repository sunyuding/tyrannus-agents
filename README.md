# Tyrannus Agents

Enterprise AI Agent Automation Platform — 8 modular agents for business automation.

## Architecture

```
User → Frontend → Agent Orchestrator → Task Router
  → Tool Layer (API / MCP / Browser Agent / DB / File)
  → Execution Systems (CRM / Email / LINE / YouTube / TikTok / FB / IG / Stripe ...)
  → Monitoring (Logs / Approval / Retry / Audit / Metrics / Dashboard)
```

## 8 Agent Modules

| # | Module | Purpose |
|---|--------|---------|
| 1 | Customer Service & Success | Auto-handle customer issues, check orders, create tickets |
| 2 | Sales Development & CRM | Find prospects, generate outreach, update CRM |
| 3 | Marketing Content & Publishing | Multi-platform marketing content generation |
| 4 | Finance, Invoicing & Reporting | Collections, invoices, reminders, financial reports |
| 5 | Social Media Content Factory | Topic → copy → video → subtitles → cover → publish |
| 6 | IT Support & Access Management | Accounts, permissions, troubleshooting |
| 7 | Knowledge Base & Decision Assistant | RAG document search, summarization, decision support (brain of all other agents) |
| 8 | Cross-System Orchestration | Multi-tool continuous task execution (foundation layer) |

## Implementation Phases

### Phase 1: Foundation
- Agent Orchestrator (Module 8) — task routing, tool registry, approval workflow

### Phase 2: High-ROI Modules
- Knowledge Base (Module 7) — RAG search, document Q&A
- Social Media Factory (Module 5) — content generation & publishing
- Sales CRM (Module 2) — prospecting & outreach

### Phase 3: Enterprise Operations
- Customer Service (Module 1)
- Finance (Module 4)
- IT Support (Module 6)
- Marketing (Module 3)

## MVP Scope

1. Knowledge base Q&A (RAG)
2. Social media content generation & publishing
3. Human-in-the-loop approval workflow

## Tech Stack

- **Frontend**: Next.js
- **Backend**: FastAPI or Node.js
- **Database**: PostgreSQL
- **Vector DB**: For RAG knowledge base
- **Tools**: MCP / API / Browser Agent (Playwright)

## Project Structure

```
tyrannus-agents/
├── README.md
├── docs/                  # Original design documents
├── packages/
│   ├── orchestrator/      # Core agent orchestrator (Module 8)
│   ├── knowledge-base/    # RAG & document search (Module 7)
│   ├── social-media/      # Content generation & publishing (Module 5)
│   ├── sales-crm/         # Sales development (Module 2)
│   ├── customer-service/  # Customer support (Module 1)
│   ├── finance/           # Invoicing & reporting (Module 4)
│   ├── it-support/        # IT & access management (Module 6)
│   └── marketing/         # Marketing content (Module 3)
├── tools/                 # Shared MCP/API/Browser tools
├── web/                   # Next.js admin dashboard
└── infra/                 # Docker, CI/CD, deployment
```

## License

MIT
