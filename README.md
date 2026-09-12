# AIVOA — AI-Powered Customer Complaint Management System

An AI-assisted pharmaceutical customer complaint intake and triage prototype, built for the AIVOA Round 1 AI Product Engineer (Interns) assignment.

> **Scope disclaimer:** This is an engineering prototype built for a hiring assignment. It does **not** claim regulatory compliance, FDA approval, GMP certification, or production-grade OCR. It is a demonstration of the requested AI-assisted workflow using the mandated stack.

## What this is

> UNSTRUCTURED CUSTOMER COMPLAINT → AI UNDERSTANDING → STRUCTURED QMS DATA → RISK-BASED TRIAGE → HUMAN REVIEW → AUDITABLE COMPLAINT RECORD

A QA user pastes a raw customer complaint (email/pharmacy note) or uploads a PDF complaint report into the **AIVOA Copilot**. The Copilot — backed by a LangGraph pipeline calling Groq's `gemma2-9b-it` (and `llama-3.3-70b-versatile` for risk assessment) — extracts structured fields, classifies the defect, and produces an AI risk assessment, all of which populate the **Log Customer Complaint** form on the left. The user can correct any field conversationally ("actually the batch number is X") or by editing the form directly, then commits the reviewed complaint to a demonstration QMS ledger with a full audit trail.

## Tech stack (as mandated by the assignment)

| Layer | Technology |
|---|---|
| Frontend | React + Redux Toolkit, Google Inter |
| Backend | Python + FastAPI |
| AI orchestration | LangGraph |
| LLM | Groq — `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (risk assessment) |
| Database | PostgreSQL (MySQL also supported via `DATABASE_URL`) |

## Project structure

```
backend/
  app/
    main.py                 # FastAPI app entrypoint
    config.py                # env-var driven settings
    api/complaints.py        # thin HTTP routes
    services/complaint_service.py  # business logic: DB <-> LangGraph glue
    ai/
      graph.py                # LangGraph StateGraph wiring
      state.py                # shared graph state (TypedDict)
      groq_client.py           # Groq SDK wrapper, structured JSON + retry
      nodes/                   # one file per graph node
      prompts/                 # prompt templates per stage
    models/complaint.py       # SQLAlchemy models (Complaint, audit log, etc.)
    schemas/complaint.py      # Pydantic request/response contracts
    database/                 # session + init/seed script
    utils/                    # PDF extraction, complaint numbering
frontend/
  src/
    App.jsx                   # two-column layout
    store/slices/complaintSlice.js   # single source of truth for form/chat state
    services/api.js            # axios calls to the backend
    components/                # ComplaintForm, CopilotPanel, RiskAssessmentCard, etc.
demo_data/
  generate_demo_pdf.py         # generates a realistic fictional complaint PDF
  zenith_life_sciences_CC-2026-00154.pdf
  demo1_text_complaint.txt     # paste-in demo text (Amoxicillin / Apollo Pharmacy)
  demo1_correction_message.txt
  demo2_correction_message.txt
docker-compose.yml            # optional local Postgres
```

## Running it locally

### 1. Database

Easiest: `docker compose up -d` to start a local Postgres on `localhost:5432` (user/pass `postgres`/`postgres`, db `aivoa_complaints`). Or point `DATABASE_URL` at any MySQL/Postgres instance you already have.

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # or your preferred env tool
pip install -r requirements.txt --break-system-packages   # or omit the flag if not needed
cp .env.example .env
# edit .env: set GROQ_API_KEY (https://console.groq.com/keys) and DATABASE_URL
python -m app.database.init_db     # creates tables + seeds 2 demo complaints
uvicorn app.main:app --reload --port 8000
```

Backend now runs at `http://localhost:8000`. Interactive API docs at `/docs`.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # defaults are fine for local dev (Vite proxies /api -> :8000)
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api/*` to the backend.

## Demo scenarios

Two ready-to-use scenarios matching the reference demo:

1. **Text complaint** — paste the contents of `demo_data/demo1_text_complaint.txt` into the Copilot. Watch the form populate, then paste `demo_data/demo1_correction_message.txt` to see the batch/quantity correction applied in place.
2. **PDF complaint** — drag `demo_data/zenith_life_sciences_CC-2026-00154.pdf` onto the Copilot's drop zone. Watch the "Extracting..." state, then the form populate with the Metformin API / foreign matter contamination scenario. Follow up with `demo_data/demo2_correction_message.txt` to demonstrate a correction on a PDF-derived complaint.

The seed script (`init_db.py`) also pre-loads two **committed** complaints so the duplicate-detection feature has something to match against immediately — submitting demo 1's text again should surface `CC-2026-00001` as a likely duplicate.

## Core features implemented

- Paste-text and PDF-upload complaint intake
- LangGraph pipeline: input routing → extraction → merge → classification → risk assessment → completeness check → duplicate detection → root cause → CAPA → summary → response finalization
- Conversational corrections that patch only the fields addressed, never wiping unrelated form data
- Structured JSON contract between AI, backend, and Redux — the frontend never scrapes chat text to populate the form
- AI Copilot Risk Assessment card (severity, suggested next action, hypothesis) — explicitly labeled as decision support
- Commit-to-QMS-Ledger workflow with complaint numbering (`CC-YYYY-#####`) and an append-only audit log
- Graceful degradation: a missing/invalid Groq key or an unreachable API never crashes a request — the UI shows a clear message and "Not Assessed"/"Not Provided" defaults instead

## Bonus AI features implemented

- **Completeness checker** — deterministic (no LLM needed) check against required fields, surfaced as a banner and in `missing_fields`
- **Duplicate complaint detection** — weighted field-overlap scoring against recent complaints (product, batch, customer, category)
- **Root cause recommendation** — AI-suggested investigation areas, explicitly labeled as non-definitive
- **CAPA recommendation** — draft corrective/preventive actions for QA review
- **Complaint summary** — short natural-language summary of the complaint

## Known limitations (by design, per assignment scope)

- PDF processing extracts embedded text only (via `pdfplumber`); scanned/image-only PDFs are explicitly out of scope and surface a clear error rather than silently failing.
- Duplicate detection uses deterministic field-overlap scoring, not vector embeddings — appropriate for MVP scale and fully explainable to a QA reviewer.
- Authentication is a single demo reviewer name passed at commit time; no real auth/session system.
- All AI outputs are explicitly framed as decision support requiring human review, per the assignment's AI-safety requirements — nothing here should be read as a validated regulatory system.

## Further reading

- `docs/DEMO_SCRIPT.md` — a 5–10 minute walkthrough script for the submission video
- `docs/INTERVIEW_PREP.md` — design-decision explanations (why LangGraph, why Redux, why structured outputs, etc.) for defending the implementation
