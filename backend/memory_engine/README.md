# AFTERMIND - Module 3: Connected Long-Term Memory & Semantic Search

**Persistent business memory infrastructure and RAG-based semantic retrieval engine for AFTERMIND.**

This module enables AFTERMIND to store, organize, connect, and retrieve business knowledge across multiple meetings, voice notes, and documents. It preserves source references, manages decision evolution timelines, and provides multi-tenant semantic search and RAG answering with verifiable source citations.

---

## Architecture Overview

```
backend/
├── memory_engine/
│   ├── __init__.py               # Module package declaration
│   ├── config.py                 # Configuration (pgvector, dimensions, API keys)
│   ├── database.py               # Database engine, session, & pgvector init
│   ├── models.py                 # SQLAlchemy models (Sources, Memories, Companies, etc.)
│   ├── schemas.py                # Pydantic v2 validation contracts
│   ├── embedding_service.py      # OpenAI, Gemini, & local semantic vector generator
│   ├── vector_search.py          # pgvector & cosine similarity search engine
│   ├── memory_service.py         # Business logic, tenant isolation, memory CRUD
│   ├── relationship_service.py   # Memory relationships & decision timeline traversal
│   ├── rag_engine.py             # Grounded RAG retrieval, context builder & citations
│   ├── routes.py                 # FastAPI endpoints
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_memory_engine.py # Comprehensive automated test suite
│   └── README.md                 # Module documentation
```

---

## Core Capabilities

### 1. PostgreSQL with pgvector & Dual-Mode Compatibility
- **Production / Supabase**: Uses PostgreSQL with the `pgvector` extension (`vector(1536)`). Automatically executes `CREATE EXTENSION IF NOT EXISTS vector;` on startup.
- **Local / CI Testing**: Seamlessly supports SQLite fallback with vectorized cosine similarity in NumPy, allowing tests to run anywhere with zero external infrastructure dependencies.

### 2. Multi-Tenant Company Isolation
Every memory, search request, and RAG query is strictly isolated by `company_id`. Company B can never search, view, or synthesize answers using Company A's business memories.

### 3. Persistent Memory Across Multiple Meetings
Connects memories across conversations (e.g., *Meeting 1: Project Kickoff* -> *Meeting 2: Payment Gateway Addition* -> *Meeting 3: Schedule Adjustment*), linking decisions to common client and project entities.

### 4. Decision Evolution & Change Tracking (No Silent Overwrites)
When a decision is revised:
- Previous memory is updated to status `superseded`.
- New memory points to `previous_memory_id` and records `change_reason`.
- A `supersedes` relationship is created in the relationship graph.
- The timeline can be traced back chronologically via `GET /api/memories/{memory_id}/history`.

### 5. Grounded RAG Engine with Source Citations
- Extracts top-k relevant memories via vector similarity.
- Builds an authenticated, grounded prompt context.
- Generates answers using Gemini / OpenAI (or grounded synthesis fallback).
- Returns explicit `SourceReference` citations (Source Title, Type, Memory ID, Timestamp).
- If information is unavailable, clearly states: *"I could not find any recorded business memories or discussions regarding this query for your company."*

---

## Database Schema (PostgreSQL + pgvector)

```mermaid
erDiagram
    COMPANIES ||--o{ PROJECTS : has
    COMPANIES ||--o{ PEOPLE : employs
    COMPANIES ||--o{ SOURCES : owns
    COMPANIES ||--o{ MEMORIES : owns
    PROJECTS ||--o{ SOURCES : contains
    PROJECTS ||--o{ MEMORIES : contains
    PEOPLE ||--o{ SOURCES : authors
    PEOPLE ||--o{ MEMORIES : authors
    SOURCES ||--o{ MEMORIES : generates
    MEMORIES ||--o{ MEMORY_RELATIONSHIPS : connects
```

### Table Definitions

1. **`companies`**: `id` (UUID), `name`, `domain`, `created_at`, `updated_at`
2. **`projects`**: `id` (UUID), `company_id` (FK), `name`, `description`, `status`, `created_at`
3. **`people`**: `id` (UUID), `company_id` (FK), `name`, `email`, `role`, `created_at`
4. **`sources`**: `id` (UUID), `company_id` (FK), `project_id` (FK), `author_id` (FK), `title`, `source_type` (`meeting`, `voice_note`, `document`, `email`, `chat`), `raw_content`, `meta_info`, `created_at`
5. **`memories`**: `id` (UUID), `company_id` (FK), `project_id` (FK), `source_id` (FK), `author_id` (FK), `memory_type` (`decision`, `client_requirement`, `employee_commitment`, `important_deadline`, `meeting_discussion`, `general_info`), `title`, `content`, `status` (`active`, `superseded`, `modified`, `completed`, `cancelled`), `confidence`, `previous_memory_id` (FK to memories), `change_reason`, `tags`, `meta_info`, `embedding` (`vector(1536)`), `created_at`, `updated_at`
6. **`memory_relationships`**: `id` (UUID), `from_memory_id` (FK), `to_memory_id` (FK), `relationship_type` (`supersedes`, `updates`, `contradicts`, `depends_on`, `relates_to`, `derived_from`), `description`, `confidence`, `created_at`

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/companies/` | Register a client company / tenant |
| `POST` | `/api/projects/` | Register a project under a company |
| `POST` | `/api/people/` | Register an employee or stakeholder |
| `POST` | `/api/sources/` | Register an original document, meeting, or voice note |
| `POST` | `/api/memories/` | Ingest structured memory with vector embedding & source link |
| `GET` | `/api/memories/` | List company memories with filters (`project_id`, `memory_type`, `status`) |
| `GET` | `/api/memories/{id}` | Get memory with source reference and project context |
| `GET` | `/api/memories/{id}/history` | Trace chronological decision evolution & superseded chain |
| `POST` | `/api/search/` | Semantic natural language vector search |
| `POST` | `/api/chat/` | Grounded RAG question answering with source citations |
| `GET` | `/api/companies/{id}/memories` | Get all memories for a company |
| `GET` | `/api/projects/{id}/memories` | Get all memories for a project |
| `POST` | `/api/relationships/` | Create directed relationship between memories |

---

## Configuration & Environment Variables

Create or update `.env` in `backend/`:

```env
# Database (PostgreSQL / Supabase)
DATABASE_URL=postgresql+psycopg://postgres:yourpassword@localhost:5432/aftermind

# Or for local SQLite testing:
# DATABASE_URL=sqlite:///./aftermind_memory.db

# Vector Dimension
VECTOR_DIMENSION=1536

# LLM & Embedding Providers
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_PROVIDER=auto    # 'auto', 'gemini', 'openai', or 'local'
LLM_PROVIDER=auto          # 'auto', 'gemini', 'openai', or 'heuristic'

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

---

## Running and Testing the Module

### 1. Activate Environment
```bash
# Windows
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 2. Run Test Suite
```bash
python -m pytest memory_engine/tests/test_memory_engine.py -v
```

All 7 test suites validate:
1. Embedding generation & cosine discrimination
2. Memory insertion & source reference traceability
3. Multi-meeting persistence across 3 consecutive meetings
4. Semantic vector search
5. Multi-tenant company isolation security
6. Grounded RAG generation with source citations & missing data handling
7. FastAPI endpoint responses via TestClient

### 3. Start the API Server
```bash
uvicorn main:app --reload --port 8000
```
Interactive API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Integration Contracts for Team Members

### 1. Integrating with Dhanesh (Memory Extraction Module)
Dhanesh's module extracts structured items from transcripts. Send extracted items to:
`POST /api/memories/`
```json
{
  "company_id": "c1a2b3c4-...",
  "project_id": "p5e6f7g8-...",
  "source_id": "s9h0i1j2-...",
  "memory_type": "decision",
  "title": "Selected Stripe Payment Gateway",
  "content": "ABC Technologies decided to use Stripe as the primary payment processor.",
  "status": "active",
  "confidence": 0.98,
  "previous_memory_id": null,
  "change_reason": null,
  "tags": ["payment", "stripe", "architecture"]
}
```

### 2. Integrating with Nirmal (Commitment Tracker)
Nirmal's module queries active employee commitments and deadlines:
`GET /api/memories/?company_id={company_id}&memory_type=employee_commitment&status=active`
Or for deadlines:
`GET /api/memories/?company_id={company_id}&memory_type=important_deadline&status=active`

### 3. Integrating with Amrita (AI Assistant & Chat UI)
Amrita's AI Assistant can query the business memory RAG pipeline directly:
`POST /api/chat/`
```json
{
  "question": "What is the latest launch deadline agreed with ABC Technologies?",
  "company_id": "c1a2b3c4-...",
  "include_superseded": false
}
```
Response:
```json
{
  "question": "What is the latest launch deadline agreed with ABC Technologies?",
  "answer": "Based on the recorded memories from 'Meeting 3: Scope & Schedule Adjustment':\n- Extended Project Launch Deadline: Project launch deadline rescheduled to December 20, 2026.",
  "sources": [
    {
      "source_id": "s9h0i1j2-...",
      "source_title": "Meeting 3: Scope & Schedule Adjustment",
      "source_type": "meeting",
      "memory_id": "m4a5b6c7-...",
      "memory_title": "Extended Project Launch Deadline",
      "memory_type": "important_deadline",
      "content_snippet": "Project launch deadline rescheduled to December 20, 2026...",
      "timestamp": "2026-10-31T21:40:00"
    }
  ],
  "retrieved_memories_count": 1,
  "is_grounded": true
}
```
