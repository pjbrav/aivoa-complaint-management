"""
Nodes 2-3: Complaint Information Extraction.

Two node functions sharing one Groq call pattern — split because they use
different prompts and, in the new-complaint case, feed the "raw text"
straight from paste/PDF, while the correction case also injects the
current field state so the model knows what it's amending.

Both nodes write ONLY `extracted_updates` / `confidence` / a draft
`assistant_message` — they never touch `existing_fields` directly. The
actual merge into the authoritative field set happens later in
`merge_state`, which keeps "what did the AI propose" separate from "what
did we accept," matching the human-in-the-loop requirement.
"""
from app.ai.groq_client import call_groq_json, GroqUnavailableError, GroqMalformedResponseError
from app.ai.prompts.extraction import (
    build_new_complaint_prompt,
    build_correction_prompt,
    build_extraction_user_prompt,
)
from app.ai.state import ComplaintGraphState
from app.config import get_settings

settings = get_settings()


def extract_new_complaint_node(state: ComplaintGraphState) -> dict:
    raw_text = state.get("raw_input_text", "").strip()
    if not raw_text:
        return {
            "extracted_updates": {},
            "confidence": {},
            "assistant_message": "I didn't receive any complaint text to analyze. Please paste the complaint or upload a document.",
            "error": "empty_input",
        }
    try:
        result = call_groq_json(
            system_prompt=build_new_complaint_prompt(),
            user_prompt=build_extraction_user_prompt(raw_text),
            model=settings.groq_primary_model,
        )
    except (GroqUnavailableError, GroqMalformedResponseError) as exc:
        return {
            "extracted_updates": {},
            "confidence": {},
            "assistant_message": f"I couldn't process that complaint right now ({exc}). Please try again in a moment.",
            "error": str(exc),
        }

    return {
        "extracted_updates": result.get("updates", {}),
        "confidence": result.get("confidence", {}),
        "assistant_message": result.get("message", "I've extracted the available details from the complaint."),
        "error": None,
    }


def extract_correction_node(state: ComplaintGraphState) -> dict:
    raw_text = state.get("raw_input_text", "").strip()
    existing_fields = state.get("existing_fields", {})
    if not raw_text:
        return {
            "extracted_updates": {},
            "confidence": {},
            "assistant_message": "Could you clarify what you'd like to change?",
            "error": "empty_input",
        }
    try:
        result = call_groq_json(
            system_prompt=build_correction_prompt(),
            user_prompt=build_extraction_user_prompt(raw_text, existing_fields),
            model=settings.groq_primary_model,
        )
    except (GroqUnavailableError, GroqMalformedResponseError) as exc:
        return {
            "extracted_updates": {},
            "confidence": {},
            "assistant_message": f"I couldn't process that update right now ({exc}). Please try again.",
            "error": str(exc),
        }

    return {
        "extracted_updates": result.get("updates", {}),
        "confidence": result.get("confidence", {}),
        "assistant_message": result.get("message", "I've updated the form with your correction."),
        "error": None,
    }
