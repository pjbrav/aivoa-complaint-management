"""
Node: Structured State Update (merge).

Takes `extracted_updates` (what the AI proposed) and merges it into
`existing_fields` (what the form currently holds) to produce the new
authoritative field set for this turn. This is a dedicated node — rather
than folding the merge into the extraction node — so that:
  1. correction turns provably only touch the fields the model returned,
     never wiping out unrelated fields already on the form, and
  2. the merged, authoritative fields are what downstream classification
     and risk-assessment nodes reason over, not the raw partial update.
"""
from app.ai.state import ComplaintGraphState

REQUIRED_FOR_COMPLETENESS = [
    "customer_name",
    "complaint_source",
    "product_name",
    "batch_lot_number",
    "affected_quantity",
    "complaint_description",
]


def merge_state_node(state: ComplaintGraphState) -> dict:
    existing = dict(state.get("existing_fields", {}))
    updates = state.get("extracted_updates", {}) or {}

    for key, value in updates.items():
        if isinstance(value, str) and not value.strip():
            continue
        # If the LLM explicitly sent null, clear the stale field rather
        # than preserving the previous complaint`s value.
        existing[key] = value

    return {"existing_fields": existing}
