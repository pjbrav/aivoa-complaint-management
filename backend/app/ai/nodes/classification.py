"""Node: Complaint Classification.

Runs only when there's enough signal to classify (a product/defect
mention) — for pure corrections that only touch e.g. batch number, we
still re-classify since the description may reference it, but this stays
cheap because we reuse the merged field state rather than the full raw
history.
"""
from app.ai.groq_client import call_groq_json, GroqUnavailableError, GroqMalformedResponseError
from app.ai.prompts.classification import CLASSIFICATION_SYSTEM_PROMPT, build_classification_user_prompt
from app.ai.state import ComplaintGraphState
from app.config import get_settings

settings = get_settings()


def classify_complaint_node(state: ComplaintGraphState) -> dict:
    fields = state.get("existing_fields", {})
    raw_text = state.get("raw_input_text", "")

    if not fields.get("product_name") and not raw_text:
        return {
            "complaint_category": fields.get("complaint_category"),
            "complaint_description": fields.get("complaint_description"),
        }

    try:
        result = call_groq_json(
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            user_prompt=build_classification_user_prompt(fields, raw_text),
            model=settings.groq_primary_model,
        )
    except (GroqUnavailableError, GroqMalformedResponseError):
        # Non-fatal: classification failing shouldn't block the rest of the
        # pipeline. Keep whatever category/description already existed.
        return {
            "complaint_category": fields.get("complaint_category") or "Not Provided",
            "complaint_description": fields.get("complaint_description"),
        }

    return {
        "complaint_category": result.get("complaint_category", fields.get("complaint_category")),
        "complaint_description": result.get("complaint_description", fields.get("complaint_description")),
    }
