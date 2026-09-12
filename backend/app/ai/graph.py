"""
The LangGraph complaint-processing graph.

This is the actual orchestration layer the assignment asks for: distinct
nodes with a defined data contract (ComplaintGraphState) wired together
by a StateGraph, with a real conditional branch (new complaint vs.
correction) rather than one monolithic LLM call.

Graph shape:

    input_router
        ├─(new)────────▶ extract_new ───┐
        └─(correction)─▶ extract_correction ┘
                                          ▼
                                     merge_state
                                          ▼
                                   classify_complaint
                                          ▼
                                    assess_risk
                                          ▼
                                 check_completeness
                                          ▼
                                 detect_duplicates
                                          ▼
                                  suggest_root_cause
                                          ▼
                                    suggest_capa
                                          ▼
                                      summarize
                                          ▼
                                   finalize_response
                                          ▼
                                         END

Each node is intentionally small and independently testable — see
ai/nodes/*.py. `build_graph()` is called once and the compiled graph is
reused across requests (LangGraph graphs are stateless/reentrant; request
-specific data lives entirely in the ComplaintGraphState passed to
`.invoke()`).
"""
from langgraph.graph import StateGraph, END

from app.ai.state import ComplaintGraphState
from app.ai.nodes.input_router import input_router_node, route_after_input
from app.ai.nodes.extraction import extract_new_complaint_node, extract_correction_node
from app.ai.nodes.merge_state import merge_state_node
from app.ai.nodes.classification import classify_complaint_node
from app.ai.nodes.risk_assessment import assess_risk_node
from app.ai.nodes.completeness import check_completeness_node
from app.ai.nodes.duplicate_detection import detect_duplicates_node
from app.ai.nodes.bonus_nodes import root_cause_node, capa_node, summary_node
from app.ai.nodes.finalize import finalize_response_node


def build_graph():
    graph = StateGraph(ComplaintGraphState)

    graph.add_node("input_router", input_router_node)
    graph.add_node("extract_new", extract_new_complaint_node)
    graph.add_node("extract_correction", extract_correction_node)
    graph.add_node("merge_state", merge_state_node)
    graph.add_node("classify_complaint", classify_complaint_node)
    graph.add_node("assess_risk", assess_risk_node)
    graph.add_node("check_completeness", check_completeness_node)
    graph.add_node("detect_duplicates", detect_duplicates_node)
    graph.add_node("suggest_root_cause", root_cause_node)
    graph.add_node("suggest_capa", capa_node)
    graph.add_node("summarize", summary_node)
    graph.add_node("finalize_response", finalize_response_node)

    graph.set_entry_point("input_router")

    graph.add_conditional_edges(
        "input_router",
        route_after_input,
        {"extract_new": "extract_new", "extract_correction": "extract_correction"},
    )

    graph.add_edge("extract_new", "merge_state")
    graph.add_edge("extract_correction", "merge_state")
    graph.add_edge("merge_state", "classify_complaint")
    graph.add_edge("classify_complaint", "assess_risk")
    graph.add_edge("assess_risk", "check_completeness")
    graph.add_edge("check_completeness", "detect_duplicates")
    graph.add_edge("detect_duplicates", "suggest_root_cause")
    graph.add_edge("suggest_root_cause", "suggest_capa")
    graph.add_edge("suggest_capa", "summarize")
    graph.add_edge("summarize", "finalize_response")
    graph.add_edge("finalize_response", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_complaint_graph(initial_state: ComplaintGraphState) -> ComplaintGraphState:
    """Synchronous entry point used by the service layer."""
    graph = get_compiled_graph()
    result = graph.invoke(initial_state)
    return result
