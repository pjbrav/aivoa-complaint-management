"""
Pydantic schemas.

`ComplaintFields` is the single structured representation of a complaint
that flows through the whole system: LangGraph extraction nodes return it,
FastAPI validates it, and the frontend receives it as plain JSON to
populate Redux state. Using ONE shape everywhere is what lets the Copilot
"update the form" instead of just replying in the chat: the AI always
answers with `{ updates: <partial ComplaintFields>, message, confidence }`
and the frontend merges `updates` into its existing state.

Every field is optional because at intake time we often only have partial
information — we do NOT allow the model to invent values for fields it
doesn't have evidence for. Missing values should arrive as null / "Not
Provided", never a fabricated guess (see ai/prompts/extraction.py).
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ComplaintFields(BaseModel):
    """Partial or complete structured complaint. Used both as the LLM's
    structured-output target and as the API's request/response payload."""

    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None

    product_name: Optional[str] = None
    product_strength_grade: Optional[str] = None
    batch_lot_number: Optional[str] = None
    affected_quantity: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None

    originating_site_block: Optional[str] = None
    impacted_npm: Optional[str] = None

    complaint_category: Optional[str] = None
    complaint_description: Optional[str] = None

    severity: Optional[str] = None
    suggested_next_action: Optional[str] = None
    initial_risk_assessment: Optional[str] = None

    source_document: Optional[str] = None


class RiskAssessment(BaseModel):
    severity: str = "Not Assessed"
    suggested_next_action: str = "Not Provided"
    initial_risk_assessment: str = "Not Provided"


class CompletenessResult(BaseModel):
    complete: bool
    missing_fields: list[str] = Field(default_factory=list)


class DuplicateMatch(BaseModel):
    complaint_id: str
    complaint_number: str
    similarity: float
    matched_on: list[str] = Field(default_factory=list)


class RootCauseSuggestion(BaseModel):
    suggested_investigation_areas: list[str] = Field(default_factory=list)
    disclaimer: str = "AI-suggested investigation areas — not confirmed root causes. Requires QA investigation."


class CAPASuggestion(BaseModel):
    corrective_actions: list[str] = Field(default_factory=list)
    preventive_actions: list[str] = Field(default_factory=list)
    disclaimer: str = "AI-generated recommendation requiring QA review and approval."


class ComplaintSummary(BaseModel):
    summary: str


class ProcessTextRequest(BaseModel):
    text: str
    complaint_id: Optional[str] = None
    # if provided, this is treated as a correction/continuation of an
    # existing draft rather than a brand-new complaint


class ChatRequest(BaseModel):
    complaint_id: str
    message: str


class ChatResponse(BaseModel):
    message: str
    updates: ComplaintFields = Field(default_factory=ComplaintFields)
    confidence: dict[str, float] = Field(default_factory=dict)


class ExtractionResponse(BaseModel):
    complaint_id: str
    complaint_number: str
    fields: ComplaintFields
    confidence: dict[str, float] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    risk_assessment: RiskAssessment
    completeness: CompletenessResult
    duplicates: list[DuplicateMatch] = Field(default_factory=list)
    root_cause: Optional[RootCauseSuggestion] = None
    capa: Optional[CAPASuggestion] = None
    assistant_message: str
    status: str


class CommitRequest(BaseModel):
    complaint_id: str
    fields: ComplaintFields
    reviewer_name: str = "Demo QA Reviewer"


class CommitResponse(BaseModel):
    complaint_id: str
    complaint_number: str
    status: str
    committed_at: datetime


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_type: str
    description: str
    actor: str
    created_at: datetime
    event_metadata: dict = Field(default_factory=dict)


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    complaint_number: str
    status: str
    fields: ComplaintFields
    confidence: dict = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    committed_at: Optional[datetime] = None
