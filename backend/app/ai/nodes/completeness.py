"""
Node: Validation / Completeness Check.

Deliberately deterministic (no LLM call) — completeness is just "which
required fields are missing," and using an LLM for that would add cost,
latency, and a new failure mode for something a simple rule handles
perfectly. This mirrors the "AI Pipeline" guidance: not every node needs
to be an LLM call, only the ones that genuinely need language
understanding.
"""
from app.ai.nodes.merge_state import REQUIRED_FOR_COMPLETENESS
from app.ai.state import ComplaintGraphState

FIELD_LABELS = {
    "customer_name": "Customer Name",
    "complaint_source": "Complaint Source",
    "product_name": "Product Name",
    "batch_lot_number": "Batch / Lot Number",
    "affected_quantity": "Affected Quantity",
    "complaint_description": "Complaint Description",
}


def check_completeness_node(state: ComplaintGraphState) -> dict:
    fields = dict(state.get("existing_fields", {}))
    fields["complaint_description"] = state.get("complaint_description") or fields.get("complaint_description")

    missing = []
    for key in REQUIRED_FOR_COMPLETENESS:
        value = fields.get(key)
        if not value or (isinstance(value, str) and value.strip().lower() in ("", "not provided")):
            missing.append(FIELD_LABELS.get(key, key))

    return {
        "missing_fields": missing,
        "completeness": {"complete": len(missing) == 0, "missing_fields": missing},
    }
