# AFTERMIND — Module 1: Multi-Source AI Data Ingestion

**Production-grade ingestion pipeline converting business documents (PDF, DOCX, TXT) and audio recordings (MP3, WAV, M4A) into standardized, persistent business memories.**

---

## 1. Scope & Capabilities

Module 1 serves as the foundational data entry point for AFTERMIND. It ingests multi-modal business inputs, validates and cleans text, registers sources into **Module 3 (Persistence)**, and feeds standardized text to **Module 2 (Intelligent Memory Extraction)**.

### Strictly Supported Formats (Core 6)
- **Documents (3 formats):**
  - **`PDF` (`.pdf`):** Extracted using **PyMuPDF (`fitz`)**, parsing text streams, page counts, titles, authors, and creation/modification dates.
  - **`DOCX` (`.docx`):** Extracted via Microsoft Open XML, retrieving all paragraphs (`<w:p>`), text runs (`<w:t>`), and document metadata (`title`, `author`, `revision`, `created_date`).
  - **`TXT` (`.txt`):** Plain text extraction with encoding detection (UTF-8, Latin-1) and binary executable/NUL-byte prevention.
- **Audio & Voice Notes (3 formats):**
  - **`MP3` (`.mp3`):** Verified via ID3/MPEG frame headers.
  - **`WAV` (`.wav`):** Verified via RIFF WAVE headers.
  - **`M4A` (`.m4a`):** Verified via ISO/MP4 `ftyp` box headers.
  - **Transcription Providers:** Real production transcription via **OpenAI Whisper API** (`whisper-1`) or **Google Gemini Multimodal Audio** (`gemini-1.5-flash`). Mock transcription is strictly confined to automated test fixtures and is never used in production.

---

## 2. Architecture & Design Principles

1. **Independent Functionality:** Module 1 runs completely standalone. It parses documents and transcribes audio without requiring a database connection or other modules.
2. **Optional Integrations:** When a database session is provided, sources are persisted into Module 3. When `trigger_extraction=True` and a tenant is provided, text is dispatched to Module 2.
3. **Strict Contract Preservation:**
   - Calls Module 3 using its exact `SourceCreate` schema.
   - Calls Module 2 using its exact `ExtractionRequest` schema.
4. **Security & Validation:**
   - 25 MB document size limit.
   - 50 MB audio size limit.
   - Magic byte header checks and MIME mismatch rejection (e.g. text file renamed to `.pdf` or binary renamed to `.txt`).
   - Unicode normalization (NFC), control character stripping, and whitespace collapsing.
   - Immediate error reporting when API credentials are missing (no silent fake text in production).

---

## 3. Directory Layout

```text
backend/data_ingestion/
├── __init__.py                 # Package declaration and public exports
├── config.py                   # Ingestion settings, file limits, provider selection
├── normalizer.py               # Text normalization, unicode cleaning, length limits
├── schemas.py                  # Pydantic v2 schemas and validation contracts
├── service.py                  # Ingestion orchestrator & integration logic
├── routes.py                   # FastAPI router mounted at /api/ingest
├── README.md                   # Complete module documentation
├── parsers/                    # Document format parsers
│   ├── __init__.py
│   ├── base.py                 # Abstract BaseDocumentParser & DocumentParsingError
│   ├── text_parser.py          # .txt parser with MIME/binary verification
│   ├── pdf_parser.py           # .pdf parser powered by PyMuPDF (fitz)
│   ├── docx_parser.py          # .docx parser extracting paragraphs and XML metadata
│   └── dispatcher.py           # Extension router & file size validation
├── transcribers/               # Audio transcription engine
│   ├── __init__.py
│   ├── base.py                 # Abstract BaseAudioTranscriber & AudioTranscriptionError
│   ├── whisper.py              # OpenAI Whisper API transcriber (via httpx)
│   ├── gemini.py               # Google Gemini audio transcriber (via httpx)
│   ├── mock.py                 # Deterministic test-only transcriber
│   └── manager.py              # Magic byte validation, provider resolution & credential check
└── tests/                      # Automated test suite (37 tests)
    ├── __init__.py
    ├── test_normalizer.py      # Unicode, whitespace, and size constraint tests
    ├── test_parsers.py         # PDF, DOCX, TXT, empty, corrupted, and MIME mismatch tests
    ├── test_audio.py           # MP3, WAV, M4A, missing credentials, and format tests
    ├── test_ingestion_service.py # Standalone & integrated persistence tests
    └── test_routes.py          # FastAPI endpoint integration tests
```

---

## 4. Configuration & Environment Variables

Create or update `.env` in `backend/`:

```env
# Audio Transcription Provider ('auto', 'whisper', or 'gemini')
AUDIO_TRANSCRIBER_PROVIDER=auto

# API Credentials for Real Transcription
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Model Selection
OPENAI_WHISPER_MODEL=whisper-1
GEMINI_AUDIO_MODEL=gemini-1.5-flash

# Size Limits
MAX_DOCUMENT_SIZE_BYTES=26214400   # 25 MB
MAX_AUDIO_SIZE_BYTES=52428800      # 50 MB
MAX_TEXT_CHARACTERS=100000         # 100k chars
```

---

## 5. API Endpoints Reference

All endpoints are mounted under `/api/ingest`:

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `POST` | `/api/ingest/text` | Direct ingestion of text transcripts, notes, and chat logs | `201 Created` |
| `POST` | `/api/ingest/document` | Multipart document upload (`.pdf`, `.docx`, `.txt`) | `201 Created` |
| `POST` | `/api/ingest/audio` | Multipart audio upload (`.mp3`, `.wav`, `.m4a`) | `201 Created` |
| `POST` | `/api/ingest/pipeline` | Unified pipeline: Ingest $\to$ Save in Module 3 $\to$ Extract in Module 2 | `201 Created` |
| `GET` | `/api/ingest/health` | Capability check and supported file formats reporting | `200 OK` |

---

## 6. Integration Guide for Team Members

### Integrating with Srajan (Module 3 — Memory Engine & Persistence)
When persisting sources to the database, Module 1 constructs `SourceCreate`:
```python
SourceCreate(
    company_id="company-uuid",
    project_id="project-uuid",        # Optional
    author_id="person-uuid",          # Optional
    title="Executive Board Meeting",
    source_type=SourceType.MEETING,   # meeting, voice_note, document, email, chat
    raw_content=cleaned_text,
    meta_info={
        "file_type": "pdf",
        "page_count": 4,
        "character_count": 3520,
        "word_count": 520
    }
)
```
Module 3 returns the registered `Source` object with its unique `id` (`source_id`).

### Integrating with Dhanesh (Module 2 — Intelligent Memory Extraction)
When `trigger_extraction=True`, Module 1 forwards the cleaned text to Module 2 via `ExtractionRequest`:
```python
ExtractionRequest(
    company_id="company-uuid",
    source_id="registered-source-uuid",
    extracted_text=cleaned_text,
    filename="specs.pdf",
    source_type="document",
    project_id="project-uuid",
    author_id="person-uuid",
    metadata={...}
)
```
Module 2 returns atomic memories (`decisions`, `commitments`, `requirements`, `deadlines`) and `module3_payloads`.

---

## 7. Running Automated Tests

Run the complete Module 1 test suite from `backend/`:

```powershell
python -m pytest data_ingestion/tests -v
```

All 37 tests cover:
- **PyMuPDF PDF parsing:** valid rendering, page counting, and metadata extraction.
- **DOCX parsing:** paragraph structure, Open XML metadata (`title`, `author`, `revision`).
- **TXT parsing:** whitespace, encoding, and binary detection.
- **MIME mismatch detection:** e.g. text file renamed to `.pdf` or binary saved as `.txt`.
- **Audio transcription:** `.mp3`, `.wav`, `.m4a` format verification.
- **Credential security:** raises explicit error when API keys are missing in production.
- **Standalone execution:** parses cleanly without requiring database access.
- **Database persistence:** verifies insertion into Module 3 `Source` records.
