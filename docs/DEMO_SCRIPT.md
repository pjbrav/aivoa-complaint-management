# Demo Script (5–10 minutes)

A suggested walkthrough matching what the assignment asks the submission video to cover: user input → frontend → API → backend → LangGraph → LLM → structured output → form → risk assessment → user review → QMS ledger.

## 1. Introduction (30s)
"This is AIVOA's Customer Complaint Management System — an AI-assisted intake and triage tool for pharmaceutical customer complaints. Left side is the structured QMS form, right side is the AIVOA Copilot."

## 2. Text complaint walkthrough (2 min)
- Paste `demo_data/demo1_text_complaint.txt` into the Copilot.
- Narrate while it processes: "This hits `POST /api/complaints/process-text`, which creates a draft `Complaint` row, then runs it through the LangGraph pipeline — input router, extraction against gemma2-9b-it, classification, risk assessment, completeness check, duplicate detection."
- Point out: form populates from **structured JSON**, not by parsing the chat message. Show the `ExtractionResponse` schema in `schemas/complaint.py`.
- Point out the Risk Assessment card: severity, suggested next action, hypothesis — labeled as decision support.
- If a seeded duplicate complaint exists (`CC-2026-00001`), point out the duplicate-detection note in the chat.

## 3. Conversational correction (1.5 min)
- Paste `demo_data/demo1_correction_message.txt` ("the batch number is BMX240602...").
- Show the request now goes to `POST /api/complaints/chat` because `complaintId` is already set (see `CopilotPanel.jsx`'s `handleSend`).
- Point out only the batch and quantity fields changed — everything else on the form stayed intact. Open the audit log (`GET /api/complaints/{id}/audit-log`) to show the `FIELD_CORRECTED` event with old/new values.

## 4. PDF complaint walkthrough (2 min)
- Drag `demo_data/zenith_life_sciences_CC-2026-00154.pdf` onto the drop zone.
- Narrate: "This hits `POST /api/complaints/process-pdf`. We extract embedded text with pdfplumber — no OCR needed since this is a text-based PDF, which the assignment says is sufficient for the MVP — then feed that text through the same LangGraph pipeline as the text path."
- Show the form populate with the Metformin API / foreign matter scenario, Critical severity.
- Optionally demonstrate `demo_data/demo2_correction_message.txt` to show a correction on a PDF-derived complaint too.

## 5. Human-in-the-loop editing (1 min)
- Manually edit a field directly in the form (e.g. tweak the complaint description).
- Point out this is a controlled React input dispatching straight to Redux — AI suggestions are never read-only.

## 6. Commit to QMS Ledger (1 min)
- Click "Commit to QMS Ledger."
- Show the status badge change to "Committed," the confirmation message with the generated complaint number, and query `GET /api/complaints` to show it now appears in the ledger list.
- Pull up the full audit trail for that complaint end-to-end: created → AI extraction → risk assessment → (corrections) → committed.

## 7. Error resilience (optional, 30s)
- Briefly mention: if `GROQ_API_KEY` is missing/invalid or Groq is unreachable, the pipeline degrades gracefully — show `groq_client.py`'s retry/error handling and a form showing "Not Assessed"/"Not Provided" rather than crashing.

## 8. Code walkthrough close (1–2 min)
- Show `ai/graph.py`: the actual LangGraph `StateGraph` with its conditional branch (new complaint vs. correction) and linear pipeline of typed nodes.
- Show `complaintSlice.js`: one Redux slice as the single source of truth, thunks calling the API layer, reducers merging structured updates.
- Close: "Every AI action is logged to an audit trail, every AI output is editable, and nothing is committed to the ledger without a human review step."
