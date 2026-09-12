"""
Node 1: Input Router.

Decides whether this graph run is a brand-new complaint extraction or a
correction/follow-up against an existing draft. This is a genuine branch
point used by graph.py's conditional edge — not just a formality — because
downstream extraction uses a different prompt for each case (see
ai/prompts/extraction.py), and bonus nodes (duplicate detection) only make
sense to run on new complaints, not on every correction turn.
"""
from app.ai.state import ComplaintGraphState


def input_router_node(state: ComplaintGraphState) -> dict:
    mode = state.get("mode", "new_text")
    if mode not in ("new_text", "new_pdf", "correction"):
        mode = "new_text"
    return {"mode": mode, "error": None}


def route_after_input(state: ComplaintGraphState) -> str:
    """Conditional edge function: returns the name of the next node."""
    return "extract_correction" if state.get("mode") == "correction" else "extract_new"
