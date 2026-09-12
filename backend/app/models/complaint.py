"""
Database schema for the QMS complaint demonstration ledger.

Design notes (implementation choices, not AIVOA requirements):
- `Complaint` holds the current/latest structured state of a complaint,
  including while it's still in draft (pre-commit). `status` distinguishes
  DRAFT vs COMMITTED so the "Pending Triage" / "Ready to Commit" /
  "Committed" badges map directly to a DB field.
- `ComplaintAttachment` supports one-to-many because a complaint could in
  principle have more than one supporting document, even though the MVP
  demo only shows a single PDF.
- `ComplaintAuditLog` is an append-only trail: every AI extraction, user
  correction, risk assessment, and commit action writes a row here. This
  is what makes the prototype "auditable" without claiming to be a
  validated regulatory system.
- `AIAssessment` stores each risk/classification result Groq produced,
  including the raw model name and confidence map, separate from the
  complaint's "accepted" values — so we keep history of what the AI
  suggested vs. what the human ultimately kept.
- `Reviewer` is an intentionally minimal stand-in for auth. This MVP does
  not implement real authentication (out of scope for an intake demo);
  a single demo reviewer is seeded and referenced by committed complaints.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ComplaintStatus(str, enum.Enum):
    DRAFT = "DRAFT"                # AI extracted / being reviewed, not yet committed
    READY_TO_COMMIT = "READY_TO_COMMIT"
    COMMITTED = "COMMITTED"


class Severity(str, enum.Enum):
    MINOR = "Minor"
    MAJOR = "Major"
    CRITICAL = "Critical"
    NOT_ASSESSED = "Not Assessed"


class Reviewer(Base):
    __tablename__ = "reviewers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80), default="QA Reviewer")
    email: Mapped[str] = mapped_column(String(200), unique=True)

    complaints: Mapped[list["Complaint"]] = relationship(back_populates="committed_by")


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    complaint_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    # e.g. CC-2026-00154

    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus), default=ComplaintStatus.DRAFT
    )

    # --- Section 1: Origin & Customer ---
    complaint_source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- Section 2: Product & Batch ---
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_strength_grade: Mapped[str | None] = mapped_column(String(120), nullable=True)
    batch_lot_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    affected_quantity: Mapped[str | None] = mapped_column(String(120), nullable=True)
    manufacturing_date: Mapped[str | None] = mapped_column(String(60), nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # --- Section 3: Facility & Material Impact ---
    originating_site_block: Mapped[str | None] = mapped_column(String(120), nullable=True)
    impacted_npm: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- Section 4: Defect Analysis ---
    complaint_category: Mapped[str | None] = mapped_column(String(150), nullable=True)
    complaint_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- AI Risk Assessment (latest accepted values) ---
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.NOT_ASSESSED)
    suggested_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_risk_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Provenance / AI metadata ---
    source_document: Mapped[str | None] = mapped_column(String(300), nullable=True)
    confidence: Mapped[dict] = mapped_column(JSON, default=dict)
    missing_fields: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    committed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    committed_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("reviewers.id"), nullable=True
    )
    committed_by: Mapped["Reviewer | None"] = relationship(back_populates="complaints")

    attachments: Mapped[list["ComplaintAttachment"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list["ComplaintAuditLog"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintAuditLog.created_at"
    )
    ai_assessments: Mapped[list["AIAssessment"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="AIAssessment.created_at"
    )


class ComplaintAttachment(Base):
    __tablename__ = "complaint_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    complaint_id: Mapped[str] = mapped_column(String(36), ForeignKey("complaints.id"))
    filename: Mapped[str] = mapped_column(String(300))
    file_type: Mapped[str] = mapped_column(String(50))
    extracted_text_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complaint: Mapped["Complaint"] = relationship(back_populates="attachments")


class AuditEventType(str, enum.Enum):
    COMPLAINT_CREATED = "COMPLAINT_CREATED"
    AI_EXTRACTION = "AI_EXTRACTION"
    FIELD_CORRECTED = "FIELD_CORRECTED"
    RISK_ASSESSMENT_GENERATED = "RISK_ASSESSMENT_GENERATED"
    COMPLETENESS_CHECKED = "COMPLETENESS_CHECKED"
    DUPLICATE_CHECKED = "DUPLICATE_CHECKED"
    COMPLAINT_COMMITTED = "COMPLAINT_COMMITTED"


class ComplaintAuditLog(Base):
    __tablename__ = "complaint_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    complaint_id: Mapped[str] = mapped_column(String(36), ForeignKey("complaints.id"))
    event_type: Mapped[AuditEventType] = mapped_column(Enum(AuditEventType))
    description: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(120), default="AIVOA Copilot")
    # "AIVOA Copilot" for AI-driven events, reviewer name/email for human actions
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complaint: Mapped["Complaint"] = relationship(back_populates="audit_events")


class AIAssessment(Base):
    """
    Historical record of each AI risk/classification pass, kept separate
    from the complaint's current accepted fields. Lets us show, in an
    interview, "here's what the model actually returned at 10:04:32,
    and here's what the human kept."
    """
    __tablename__ = "ai_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    complaint_id: Mapped[str] = mapped_column(String(36), ForeignKey("complaints.id"))
    model_used: Mapped[str] = mapped_column(String(80))
    stage: Mapped[str] = mapped_column(String(60))
    # e.g. "extraction", "classification", "risk_assessment", "correction"
    raw_output: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complaint: Mapped["Complaint"] = relationship(back_populates="ai_assessments")
