"""
Node: Final Complaint Preparation.

The extraction node already drafted a short `assistant_message`
("Got it, I've updated..."). This node doesn't overwrite that — the
correction-confirmation wording from the extraction step is exactly what
the demo shows the Copilot saying. Instead it appends a brief, factual
note when there's something the user should notice (missing required
fields, or a potential duplicate), so the chat stays useful without
turning into a wall of text after every turn.
"""
from app.ai.state import ComplaintGraphState


def finalize_response_node(state: ComplaintGraphState) -> dict:
    base_message = state.get("assistant_message", "").strip()
    extras = []

    missing = state.get("missing_fields", [])
    if missing:
        extras.append(f"Still missing: {', '.join(missing)}.")

    duplicates = state.get("duplicates", [])
    if duplicates:
        top = duplicates[0]
        extras.append(
            f"Note: this looks similar to {top['complaint_number']} "
            f"({int(top['similarity'] * 100)}% match) — worth checking before committing."
        )

    full_message = base_message
    if extras:
        full_message = f"{base_message} {' '.join(extras)}".strip()

    return {"assistant_message": full_message}
