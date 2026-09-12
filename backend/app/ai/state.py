"""
Shared state object that flows through every LangGraph node.

Using a single TypedDict as the graph's state (rather than ad-hoc
function arguments) is what makes this "real" LangGraph usage: each node
reads what it needs from state and writes back only its own slice,
and the graph wiring in graph.py determines execution order — the nodes
themselves don't call each other directly.
"""
from typing import Any, TypedDict


class ComplaintGraphState(TypedDict, total=False):
    # --- input ---
    mode: str  # "new_text" | "new_pdf" | "correction"
    raw_input_text: str  # pasted text, extracted PDF text, or chat message
    source_document: str | None  # filename if PDF, else None

    # --- existing state (for corrections) ---
    existing_fields: dict[str, Any]

    # --- candidates for duplicate detection, supplied by the service layer ---
    existing_complaints_summary: list[dict[str, Any]]

    # --- outputs written by nodes ---
    extracted_updates: dict[str, Any]
    confidence: dict[str, float]
    missing_fields: list[str]

    complaint_category: str | None
    complaint_description: str | None

    severity: str
    suggested_next_action: str
    initial_risk_assessment: str

    completeness: dict[str, Any]
    duplicates: list[dict[str, Any]]
    root_cause: dict[str, Any]
    capa: dict[str, Any]
    complaint_summary: str

    assistant_message: str

    # --- error surface (never let an exception kill the whole graph run) ---
    error: str | None
