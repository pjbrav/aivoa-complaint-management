"""Node: Risk Assessment.

Uses the stronger llama-3.3-70b-versatile model when available, since
risk framing benefits from more reasoning than field extraction does —
this is the one node where the assignment's "may also consider
llama-3.3-70b-versatile for context" guidance is applied. Falls back to
the primary model if the secondary one errors.
"""
from app.ai.groq_client import call_groq_json, GroqUnavailableError, GroqMalformedResponseError
from app.ai.prompts.classification import RISK_ASSESSMENT_SYSTEM_PROMPT, build_risk_user_prompt
from app.ai.state import ComplaintGraphState
from app.config import get_settings

settings = get_settings()


def assess_risk_node(state: ComplaintGraphState) -> dict:
    fields = dict(state.get("existing_fields", {}))
    fields["complaint_category"] = state.get("complaint_category")
    fields["complaint_description"] = state.get("complaint_description")

    if not fields.get("complaint_category"):
        return {
            "severity": "Not Assessed",
            "suggested_next_action": "Not Provided",
            "initial_risk_assessment": "Not Provided — insufficient information to assess risk yet.",
        }

    user_prompt = build_risk_user_prompt(fields)

    try:
        result = call_groq_json(
            system_prompt=RISK_ASSESSMENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=settings.groq_secondary_model,
            temperature=0.2,
        )
    except (GroqUnavailableError, GroqMalformedResponseError):
        try:
            result = call_groq_json(
                system_prompt=RISK_ASSESSMENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=settings.groq_primary_model,
                temperature=0.2,
            )
        except (GroqUnavailableError, GroqMalformedResponseError):
            return {
                "severity": "Not Assessed",
                "suggested_next_action": "Manual QA review required — AI risk assessment unavailable.",
                "initial_risk_assessment": "Not Provided — AI service unavailable.",
            }

    return {
        "severity": result.get("severity", "Not Assessed"),
        "suggested_next_action": result.get("suggested_next_action", "Not Provided"),
        "initial_risk_assessment": result.get("initial_risk_assessment", "Not Provided"),
    }
