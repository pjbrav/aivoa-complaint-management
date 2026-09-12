"""
Bonus nodes: Root Cause Recommendation, CAPA Recommendation, Complaint
Summary. Grouped in one file since each is a small, single-purpose Groq
call with an identical shape — splitting them into three files would add
navigation overhead without adding clarity.

All three are explicitly advisory: prompts instruct the model to frame
output as suggestions for QA review, never as confirmed facts, per the
assignment's AI safety requirements.
"""
from app.ai.groq_client import call_groq_json, GroqUnavailableError, GroqMalformedResponseError
from app.ai.prompts.bonus import (
    ROOT_CAUSE_SYSTEM_PROMPT,
    CAPA_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    build_bonus_user_prompt,
)
from app.ai.state import ComplaintGraphState
from app.config import get_settings

settings = get_settings()


def _current_fields(state: ComplaintGraphState) -> dict:
    fields = dict(state.get("existing_fields", {}))
    fields["complaint_category"] = state.get("complaint_category")
    fields["complaint_description"] = state.get("complaint_description")
    return fields


def root_cause_node(state: ComplaintGraphState) -> dict:
    fields = _current_fields(state)
    if not fields.get("complaint_category"):
        return {"root_cause": {"suggested_investigation_areas": [], "disclaimer": "Not enough information yet."}}
    try:
        result = call_groq_json(
            system_prompt=ROOT_CAUSE_SYSTEM_PROMPT,
            user_prompt=build_bonus_user_prompt(fields),
            model=settings.groq_primary_model,
        )
        result["disclaimer"] = "AI-suggested investigation areas — not confirmed root causes. Requires QA investigation."
        return {"root_cause": result}
    except (GroqUnavailableError, GroqMalformedResponseError):
        return {"root_cause": {"suggested_investigation_areas": [], "disclaimer": "Unavailable — AI service error."}}


def capa_node(state: ComplaintGraphState) -> dict:
    fields = _current_fields(state)
    if not fields.get("complaint_category"):
        return {"capa": {"corrective_actions": [], "preventive_actions": [], "disclaimer": "Not enough information yet."}}
    try:
        result = call_groq_json(
            system_prompt=CAPA_SYSTEM_PROMPT,
            user_prompt=build_bonus_user_prompt(fields),
            model=settings.groq_primary_model,
        )
        result["disclaimer"] = "AI-generated recommendation requiring QA review and approval."
        return {"capa": result}
    except (GroqUnavailableError, GroqMalformedResponseError):
        return {"capa": {"corrective_actions": [], "preventive_actions": [], "disclaimer": "Unavailable — AI service error."}}


def summary_node(state: ComplaintGraphState) -> dict:
    fields = _current_fields(state)
    if not fields.get("product_name"):
        return {"complaint_summary": ""}
    try:
        result = call_groq_json(
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            user_prompt=build_bonus_user_prompt(fields),
            model=settings.groq_primary_model,
        )
        return {"complaint_summary": result.get("summary", "")}
    except (GroqUnavailableError, GroqMalformedResponseError):
        return {"complaint_summary": ""}
