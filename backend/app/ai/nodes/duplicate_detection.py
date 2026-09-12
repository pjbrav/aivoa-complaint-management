"""
Node: Duplicate Complaint Detection (bonus).

Deliberately implemented as deterministic field-overlap scoring rather
than embeddings/vector search: the assignment explicitly says not to
over-engineer, and for an intake MVP, "same product + same or close
batch + same customer + same category" is both explainable to a QA
reviewer and good enough to flag candidates for human investigation
(which is all this feature promises to do — never auto-reject).

`existing_complaints_summary` is populated by the service layer with a
lightweight projection of recent complaints from the DB before the graph
runs, so this node never talks to the database directly (keeps AI nodes
DB-agnostic and testable in isolation).
"""
from app.ai.state import ComplaintGraphState

WEIGHTS = {
    "product_name": 0.35,
    "batch_lot_number": 0.30,
    "customer_name": 0.20,
    "complaint_category": 0.15,
}


def _norm(value) -> str:
    return (value or "").strip().lower()


def _score(a: dict, b: dict) -> tuple[float, list[str]]:
    score = 0.0
    matched = []
    for field, weight in WEIGHTS.items():
        va, vb = _norm(a.get(field)), _norm(b.get(field))
        if va and vb and va == vb:
            score += weight
            matched.append(field)
        elif va and vb and (va in vb or vb in va) and len(va) > 3:
            score += weight * 0.6
            matched.append(field)
    return score, matched


def detect_duplicates_node(state: ComplaintGraphState) -> dict:
    current = dict(state.get("existing_fields", {}))
    current["complaint_category"] = state.get("complaint_category")
    candidates = state.get("existing_complaints_summary", []) or []

    matches = []
    for candidate in candidates:
        score, matched_fields = _score(current, candidate)
        if score >= 0.5:
            matches.append(
                {
                    "complaint_id": candidate.get("id"),
                    "complaint_number": candidate.get("complaint_number"),
                    "similarity": round(score, 2),
                    "matched_on": matched_fields,
                }
            )

    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return {"duplicates": matches[:3]}
