# AFTERMIND - Module 4: Smart Commitment & Decision Tracker

Turns the memories stored by Module 3 into trackable work: who owes what, by when, what is overdue, what is due soon, and which deadlines or decisions changed between meetings.

It **reads** commitments and decisions through Module 3's `memory_service` (same database, same `company_id` tenant isolation). It does not store its own copy of the data and does not change any Module 2 or Module 3 file.

---

## Integration (2 minutes)

1. Copy this folder to `backend/commitment_tracker/`.
2. Add one dependency to `backend/requirements.txt`:
   ```
   python-dateutil>=2.8.2
   ```
3. Mount the router in `backend/main.py` (needs Srajan's approval, it is his file):
   ```python
   from commitment_tracker.routes import router as tracker_router   # with the other imports
   ...
   # Mount Module 4 Commitment & Decision Tracker routes
   app.include_router(tracker_router)                               # after the other include_router lines
   ```
4. Optional settings (defaults shown) in `backend/.env`:
   ```env
   TRACKER_DUE_SOON_DAYS=3
   TRACKER_DEFAULT_UPCOMING_DAYS=7
   ```
   No new database tables are needed.

---

## Structure

```
backend/commitment_tracker/
├── __init__.py
├── config.py            # TRACKER_* settings
├── deadline_parser.py   # "15 November 2026", "next Friday", "in 2 weeks" -> date
├── schemas.py           # Pydantic response/request models
├── tracker_logic.py     # database-free logic: status, grouping, reminders, change detection
├── tracker_service.py   # reads via Module 3 memory_service; one write (mark completed)
├── routes.py            # FastAPI endpoints under /api/tracker
├── tests/
│   ├── test_tracker_logic.py        # no database needed
│   └── test_tracker_service_api.py  # in-memory SQLite + TestClient
└── README.md
```

---

## What it reads from Module 2 / Module 3

| Need | Where it comes from |
|---|---|
| Commitments | `memories` rows with `memory_type = employee_commitment`, status `active`, `modified` or `completed` |
| Owner | `meta_info.person` (set by Module 2), otherwise the memory author's name (`people` table) |
| Deadline | `meta_info.deadline` (the original phrase kept by Module 2), converted to a date by `deadline_parser.py` |
| History of changes | Module 3's `previous_memory_id` chain via `memory_service.get_memory_history` (not re-implemented) |
| Superseded versions | Hidden from the tracker; only the latest version of a commitment is "open work" |

### Status rules

| `tracker_status` | Meaning |
|---|---|
| `overdue` | deadline is before today |
| `due_soon` | due today or within `TRACKER_DUE_SOON_DAYS` (default 3) |
| `pending` | deadline further away |
| `no_deadline` | no deadline, or the phrase could not be understood (see `deadline_needs_review`) |
| `completed` | Module 3 status is `completed` |

### Deadline understanding

Resolved: `15 November 2026`, `November 15, 2026`, `15 Nov`, `by 15th of November`, `2026-11-20`, `15/11/2026` (day first), `November 2026` (end of month), `tomorrow`, `in 3 days`, `in 2 weeks`, `Friday`, `next Friday`, `end of the month`, `end of week`.

Relative phrases are resolved against the day the memory was **recorded** (`created_at`), not against today. A date without a year uses the next occurrence on or after that day.

Not resolved (returned with `deadline: null`, `deadline_needs_review: true`, so nobody is told "no deadline" when one was spoken): `by Q3`, `soon`, `ASAP`, `next week`.

---

## API (all endpoints need `company_id`)

Every GET also accepts `project_id` where it makes sense, and `as_of=YYYY-MM-DD` to evaluate deadlines on a given day (handy for the demo and tests).

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/tracker/summary` | Counts: open, overdue, due_soon, pending, no_deadline, completed, needs_review |
| `GET` | `/api/tracker/commitments` | All commitments. Filters: `owner`, `status`, `include_completed` |
| `GET` | `/api/tracker/overdue` | Overdue, most overdue first |
| `GET` | `/api/tracker/upcoming?within_days=7` | Due in the next N days, soonest first |
| `GET` | `/api/tracker/by-owner` | Open work per person (people with overdue work first) |
| `GET` | `/api/tracker/reminders?within_days=3` | Reminder messages: overdue first, then due soon |
| `GET` | `/api/tracker/commitments/{id}/changes` | Deadline / owner changes across meetings |
| `GET` | `/api/tracker/decision-changes` | Revised decisions with all earlier versions |
| `POST` | `/api/tracker/commitments/{id}/complete` | Mark a commitment completed. Body: `{"company_id": "...", "note": "optional"}` |

Errors: `404` unknown commitment or wrong company, `409` commitment already superseded/cancelled, `422` invalid input.

### Example: the "15 November to 20 November" case

`GET /api/tracker/commitments/{id}/changes?company_id=...`
```json
{
  "memory_id": "m3...",
  "title": "Complete the project",
  "current_deadline": "2026-11-20",
  "versions_count": 2,
  "changes": [
    {
      "field": "deadline",
      "old_value": "2026-11-15",
      "new_value": "2026-11-20",
      "reason": "Extra security testing needed",
      "source_title": "Meeting 3: Schedule Adjustment",
      "changed_at": "2026-10-30T09:00:00"
    }
  ]
}
```
And `GET /api/tracker/commitments` shows the latest version with `"is_revised": true` and `"previous_deadline": "2026-11-15"`.

### Example: reminders

```json
[
  {"severity": "overdue", "days_left": -3,
   "message": "OVERDUE by 3 days: Aman - Send budget estimate (was due 28 Oct 2026)"},
  {"severity": "due_soon", "days_left": 2,
   "message": "DUE in 2 days: Riya - Share revised proposal (02 Nov 2026)"}
]
```

### For Amrita (dashboard)

- Header cards: `GET /summary`
- Pending/overdue table: `GET /commitments` (use `tracker_status` for badge colour)
- Per-employee view: `GET /by-owner`
- Notification bell: `GET /reminders`
- "Deadline moved" badge: `is_revised` + `previous_deadline` on each commitment, details from `/commitments/{id}/changes`
- Meeting preparation report: `GET /commitments?project_id=...&include_completed=false` and `GET /decision-changes?project_id=...`

---

## Run and test

From `backend/` (the folder that contains `main.py`):

```bash
pip install -r requirements.txt
python -m pytest commitment_tracker/tests -v       # all tests
uvicorn main:app --reload --port 8000              # then open http://localhost:8000/docs
```

`test_tracker_logic.py` needs no database. `test_tracker_service_api.py` uses in-memory SQLite exactly like Module 3's tests (so no PostgreSQL is required) and is skipped automatically if FastAPI/SQLAlchemy are not installed. It covers: status classification, owner fallback, unresolved deadlines, deadline change history, decision changes, reminders, completing commitments, company isolation, input validation, and a full Module 2 payload -> Module 3 API -> Module 4 flow.

---

## Design decisions and limits (please read before integrating)

- **Deadlines are free text.** Module 2 keeps the spoken phrase on purpose; Module 4 resolves it. Phrases that cannot be resolved are flagged, not guessed.
- **Relative dates are anchored to ingestion time**, because Module 3 has no "meeting date" field. If a transcript is uploaded days after the meeting, "next Friday" is resolved from the upload day. Adding a `meeting_date` to `meta_info` (Module 1/2) would fix this; the parser already takes an anchor date.
- **The one write:** `POST .../complete` sets `memories.status = 'completed'` and stores `completed_at` / `completion_note` in `meta_info`. Module 3 already defines `completed` as a status but has no API to set it. If Srajan adds `memory_service.update_status(...)`, `complete_commitment` in `tracker_service.py` should call that instead.
- **Owner is a name string**, taken from Module 2's `person`. It is not linked to a `people` row unless the memory has an `author_id`.
- **Reminders are pull-based.** The endpoint returns messages; sending email/WhatsApp or running a scheduler is not part of this module.
- **Same task, different wording** across meetings is only treated as one commitment when Module 2/3 links them with `previous_memory_id`. Module 4 does not guess matches by text similarity.
