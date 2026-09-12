# Interview Prep — Design Decisions Explained

## Why LangGraph, and is it "really" being used?

The pipeline is a `StateGraph` (`app/ai/graph.py`) over a shared `ComplaintGraphState` TypedDict, with:
- A genuine **conditional branch**: `input_router` routes to `extract_new` or `extract_correction` depending on whether a draft already exists, since those two cases need different prompts and different handling of "what changed."
- **12 distinct nodes**, each independently testable and each writing only its own slice of state: routing, extraction (x2), merge, classification, risk assessment, completeness, duplicate detection, root cause, CAPA, summary, finalize.
- A clear reason this isn't "one LLM call in a wrapper": classification and risk assessment use different models (`gemma2-9b-it` vs `llama-3.3-70b-versatile`) and different prompts; completeness and duplicate detection are deliberately **not** LLM calls at all (see below); several nodes catch and degrade independently so one failing model call doesn't take down the whole pipeline.

If asked "what would happen if you added a new node" — e.g. a "sentiment/urgency detector" — the answer is: add a node function, register it, insert an edge. Nothing else changes. That's the value LangGraph is providing here over a single big function.

## Why not use an LLM for completeness checking or duplicate detection?

Completeness is "which of these ~6 known fields are non-empty" — a deterministic rule. An LLM call would add latency, cost, and a new failure mode (a malformed-JSON retry loop) for zero benefit. Duplicate detection is similar: weighted field-overlap (product, batch, customer, category) is fully explainable to a QA reviewer ("why did it flag this?" → "same product, same customer, similar batch"), whereas an embedding-similarity black box would be harder to defend in a regulated-adjacent context and is explicit over-engineering for an MVP the assignment says shouldn't be over-built.

## Why Redux (not just component state or Context)?

The Copilot is explicitly *not* a chatbot bolted onto a form — it's described in the assignment as needing to **change structured application state** from a conversation. That means:
- Chat-driven updates and manual form edits both need to land in the exact same state shape, so `updateFieldLocally` (manual edit) and the `fulfilled` reducers for `submitComplaintText` / `sendCopilotMessage` (AI-driven edit) all operate on the same `fields` object.
- Every consumer (form inputs, risk card, status badge, commit button) needs to react consistently to that one source of truth without prop-drilling through a form/chat split.
- A single slice makes the "never scrape chat text to populate fields" requirement structurally true: reducers only ever accept typed `updates` objects from thunk payloads, never raw strings.

## Why FastAPI, and why is the API layer so thin?

FastAPI gives free request/response validation via Pydantic (`schemas/complaint.py`), which is the same validation layer LangGraph's structured output is checked against — one schema, two enforcement points. Routes in `api/complaints.py` do nothing but parse input, call a service function, and translate exceptions to HTTP status codes; all business logic (creating drafts, running the graph, diffing corrections for the audit log, committing) lives in `services/complaint_service.py` so it's testable without spinning up HTTP at all.

## Why structured JSON outputs instead of parsing free text?

Every extraction/classification/risk prompt (`ai/prompts/*.py`) instructs the model to return one JSON object matching a specific shape, and `groq_client.call_groq_json` strips markdown fences, extracts the outermost `{...}`, and retries once with a stricter instruction if parsing fails. This is what lets the frontend do a **structural merge** (`mergeFields` in `complaintSlice.js`) instead of regex-scraping a sentence like "I've updated the batch number to X" — which would be fragile, unlocalizable, and impossible to attach a confidence score to.

## Why human-in-the-loop, concretely (not just as a slogan)?

- Every form field is a controlled `<input>`/`<textarea>` (`FormField.jsx`) — AI output is never rendered read-only.
- The Commit button is the only path to `ComplaintStatus.COMMITTED`; nothing auto-commits.
- `commit_complaint` in the service layer takes the **fields as submitted at commit time**, not the last AI extraction — so if a reviewer edited a field after extraction, their edit wins.
- Missing fields are never invented: the extraction prompts explicitly forbid guessing, and the schema/DB default is `null`/"Not Provided", never a plausible-sounding fabrication.

## How does PDF processing actually work, and what are its limits?

`utils/pdf_extraction.py` uses `pdfplumber` to pull embedded text per page. This works well for the kind of text-based complaint report/email-attachment PDF the assignment's own reference scenario uses (verified against a generated demo PDF — see `demo_data/`). It will **not** extract text from a scanned/image-only PDF; in that case the extracted text is empty and the API returns a 422 with a clear message rather than silently proceeding with nothing, or worse, letting the LLM hallucinate content from an empty prompt. Production OCR (e.g. Tesseract, cloud OCR APIs) is explicitly called out as out of scope by the assignment.

## How do corrections work without corrupting the rest of the form?

Two things make this safe:
1. The correction prompt (`ai/prompts/extraction.py::build_correction_prompt`) explicitly instructs the model to return **only the fields the message addresses**, given the current field state as context.
2. `merge_state_node` merges `extracted_updates` onto `existing_fields` field-by-field, skipping `None`/empty values — so even if the model over-returns, empty/null values never overwrite real data. This was also verified live: submitting a batch/quantity correction only changed those two fields; category, product name, etc. stayed intact (see the audit log's `FIELD_CORRECTED` events, which record old→new per field).

## How does risk classification work, and what are its limits?

`assess_risk_node` calls Groq with a prompt giving severity guidance (Critical = contamination/patient-safety risk, Major = contained quality defects, Minor = cosmetic/labeling) and asks for a suggested next action plus a 1–2 sentence hypothesis explicitly framed as requiring investigation. It intentionally uses `llama-3.3-70b-versatile` first (falling back to `gemma2-9b-it`) since risk framing benefits from the stronger model's reasoning more than pure field extraction does. This is decision support, not a diagnosis — every risk-assessment prompt and every place it's rendered in the UI labels it as AI-suggested, requiring QA sign-off.

## How does database persistence/auditability work?

Four tables: `complaints` (current/latest structured state, DRAFT → READY_TO_COMMIT → COMMITTED), `complaint_attachments`, `complaint_audit_log` (append-only: created, AI extraction, field corrected, risk assessment generated, committed — each with actor and metadata), and `ai_assessments` (raw model output + confidence per AI pass, kept separate from the "accepted" fields so you can show what the model actually said vs. what the human kept). This was verified live: committing a complaint produces a queryable audit trail showing every step with timestamps.

## What would you change/extend given more time?

- Real authentication/session management instead of a passed-in reviewer name
- Vector-embedding-based duplicate detection once complaint volume justifies the added complexity
- Streaming LLM responses to the chat UI instead of waiting for the full JSON payload
- A proper OCR fallback path (flagged, not silently skipped) for scanned PDFs
- Structured LangGraph unit tests per node (currently verified via live end-to-end requests during development, not a checked-in test suite)
