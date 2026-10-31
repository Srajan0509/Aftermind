# AFTERMIND Module 2 — Intelligent Memory Extraction

Converts standardized text from Module 1 into validated business memories for Module 3.

## Scope

Included:
- Decision extraction
- Employee commitment extraction
- Client requirement extraction
- Deadline extraction
- Entity extraction (people, companies, projects, organizations, financial amounts, dates)
- Structured Pydantic validation
- OpenAI and Gemini provider support
- FastAPI endpoint and tests

Not included:
- File/audio ingestion (Module 1)
- PostgreSQL writes, embeddings, vector search, RAG (Module 3)
- Commitment monitoring, reminders, reporting (Module 4)

## Folder layout

```text
backend/memory_extraction/
├── __init__.py
├── config.py
├── prompts.py
├── llm_client.py
├── schemas.py
├── extractor.py
├── entity_extractor.py
├── decision_extractor.py
├── commitment_extractor.py
├── routes.py
├── README.md
└── tests/
```

## Setup

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Add these variables to `backend/.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini

# Or use Gemini:
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your_key
# GEMINI_MODEL=gemini-2.0-flash

MAX_INPUT_CHARACTERS=100000
LLM_TIMEOUT_SECONDS=45
```

Never commit `.env` or API keys.

## Run

The Module 2 router is mounted by `backend/main.py`.

```powershell
uvicorn main:app --reload --port 8000
```

Swagger: http://localhost:8000/docs

## API

`POST /api/extraction/extract`

Example request:

```json
{
  "company_id": "company-uuid",
  "source_id": "registered-source-uuid",
  "project_id": "project-uuid",
  "filename": "meeting-notes.txt",
  "source_type": "meeting",
  "extracted_text": "We decided to use React. Priya will send the proposal by Monday. The client requires SSO."
}
```

`company_id` and `source_id` must refer to records in Module 3. In particular, register the source through Module 3's `POST /api/sources/` before storing extracted memories.

The response contains:
- `memories`: validated atomic memories
- `entities`: unique entity mentions
- `module3_payloads`: ready-to-submit payloads for Module 3's `POST /api/memories/`
- `memories_count`
- `confidence_note`

Each memory contains `memory_type`, `title`, `content`, `person`, `company`, `project`, `deadline`, `confidence`, `tags`, `entities`, and `meta_info`.

## Module 3 integration

The extraction endpoint does not write to the database. It returns ready-to-submit Module 3-compatible payloads in `module3_payloads`.

For each item in `module3_payloads`, call Module 3's `POST /api/memories/` with:
- `company_id`
- `source_id`
- `memory_type`
- `title`
- `content`
- `status`
- `confidence`
- `tags`
- `meta_info`

The helper `ExtractedMemory.to_memory_create_payload(request)` maps a memory into that shape. `person`, `deadline`, project/company mentions and entity mentions are retained inside `meta_info` because Module 3's current `MemoryCreate` schema has no dedicated top-level fields for them.

## Error handling

- 413: input exceeds configured character limit
- 502: provider request failed or returned invalid/invalidly structured JSON
- 503: selected provider API key is missing
- 422: request validation failed

LLM confidence is a rough model estimate, not a calibrated probability. The extractor never intentionally fills missing names or dates.

## Tests

From `backend/`:

```powershell
python -m pytest memory_extraction/tests -v
```
