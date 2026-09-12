"""
Complaint service layer.

This is the "clean separation" the assignment asks for:

    FastAPI route  ->  service function (this file)  ->  LangGraph  ->  Groq
                                    |
                                    v
                                 Database

Routes stay thin (parse request, call service, return response). All
business logic — creating drafts, running the graph, diffing corrections
for the audit log, committing — lives here so it's testable independent
of HTTP and independent of the AI graph's internals.
"""
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.ai.graph import run_complaint_graph
from app.config import get_settings
from app.models.complaint import (
    Complaint,
    ComplaintAttachment,
    ComplaintAuditLog,
    AIAssessment,
    Reviewer,
    ComplaintStatus,
    AuditEventType,
    Severity,
)
from app.schemas.complaint import (
    ComplaintFields,
    ExtractionResponse,
    RiskAssessment,
    CompletenessResult,
    DuplicateMatch,
    RootCauseSuggestion,
    CAPASuggestion,
    ChatResponse,
    CommitResponse,
)
from app.utils.complaint_numbering import generate_complaint_number

settings = get_settings()

COMPLAINT_FIELD_KEYS = [
    "complaint_source", "customer_name", "product_name", "product_strength_grade",
    "batch_lot_number", "affected_quantity", "manufacturing_date", "expiry_date",
    "originating_site_block", "impacted_npm", "complaint_category", "complaint_description",
]


def _severity_enum(value: str | None) -> Severity:
    if not value:
        return Severity.NOT_ASSESSED
    try:
        return Severity(value)
    except ValueError:
        return Severity.NOT_ASSESSED


def _complaint_to_dict(complaint: Complaint) -> dict:
    return {key: getattr(complaint, key) for key in COMPLAINT_FIELD_KEYS}


def _apply_state_to_complaint(complaint: Complaint, result: dict) -> list[tuple[str, str | None, str | None]]:
    """Writes graph result fields onto the ORM object; returns a list of
    (field, old_value, new_value) tuples for fields that actually changed,
    so the caller can write precise audit log entries."""
    changes = []
    merged_fields = dict(result.get("existing_fields", {}))
    merged_fields["complaint_category"] = result.get("complaint_category") or merged_fields.get("complaint_category")
    merged_fields["complaint_description"] = result.get("complaint_description") or merged_fields.get("complaint_description")

    for key in COMPLAINT_FIELD_KEYS:
        new_value = merged_fields.get(key)
        old_value = getattr(complaint, key)
        if new_value is not None and new_value != old_value:
            changes.append((key, old_value, new_value))
            setattr(complaint, key, new_value)

    complaint.severity = _severity_enum(result.get("severity"))
    complaint.suggested_next_action = result.get("suggested_next_action")
    complaint.initial_risk_assessment = result.get("initial_risk_assessment")
    complaint.missing_fields = result.get("missing_fields", [])
    complaint.confidence = result.get("confidence", complaint.confidence or {})

    if complaint.missing_fields:
        complaint.status = ComplaintStatus.DRAFT
    else:
        complaint.status = ComplaintStatus.READY_TO_COMMIT

    return changes


def _get_duplicate_candidates(db: Session, exclude_id: str | None) -> list[dict]:
    stmt = select(Complaint).order_by(Complaint.created_at.desc()).limit(50)
    complaints = db.execute(stmt).scalars().all()
    return [
        {
            "id": c.id,
            "complaint_number": c.complaint_number,
            "product_name": c.product_name,
            "batch_lot_number": c.batch_lot_number,
            "customer_name": c.customer_name,
            "complaint_category": c.complaint_category,
        }
        for c in complaints
        if c.id != exclude_id
    ]


def _log_audit(db: Session, complaint: Complaint, event_type: AuditEventType, description: str, actor: str = "AIVOA Copilot", metadata: dict | None = None):
    db.add(
        ComplaintAuditLog(
            complaint_id=complaint.id,
            event_type=event_type,
            description=description,
            actor=actor,
            event_metadata=metadata or {},
        )
    )


def _build_extraction_response(complaint: Complaint, result: dict) -> ExtractionResponse:
    return ExtractionResponse(
        complaint_id=complaint.id,
        complaint_number=complaint.complaint_number,
        fields=ComplaintFields(**_complaint_to_dict(complaint)),
        confidence=complaint.confidence or {},
        missing_fields=complaint.missing_fields or [],
        risk_assessment=RiskAssessment(
            severity=complaint.severity.value if complaint.severity else "Not Assessed",
            suggested_next_action=complaint.suggested_next_action or "Not Provided",
            initial_risk_assessment=complaint.initial_risk_assessment or "Not Provided",
        ),
        completeness=CompletenessResult(**result.get("completeness", {"complete": False, "missing_fields": []})),
        duplicates=[DuplicateMatch(**d) for d in result.get("duplicates", [])],
        root_cause=RootCauseSuggestion(**result.get("root_cause", {})) if result.get("root_cause") else None,
        capa=CAPASuggestion(**result.get("capa", {})) if result.get("capa") else None,
        assistant_message=result.get("assistant_message", ""),
        status=complaint.status.value,
    )


def process_new_text_complaint(db: Session, text: str) -> ExtractionResponse:
    complaint = Complaint(
        complaint_number=generate_complaint_number(db),
        status=ComplaintStatus.DRAFT,
        source_document=None,
    )
    db.add(complaint)
    db.flush()  # assign complaint.id without committing the transaction yet

    _log_audit(db, complaint, AuditEventType.COMPLAINT_CREATED, "Complaint draft created from pasted text.", actor="System")

    result = run_complaint_graph({
        "mode": "new_text",
        "raw_input_text": text,
        "existing_fields": {},
        "existing_complaints_summary": _get_duplicate_candidates(db, None),
    })

    changes = _apply_state_to_complaint(complaint, result)
    _log_audit(
        db, complaint, AuditEventType.AI_EXTRACTION,
        f"AI extracted {len(changes)} field(s) from pasted complaint text.",
        metadata={"fields": [c[0] for c in changes]},
    )
    _log_audit(
        db, complaint, AuditEventType.RISK_ASSESSMENT_GENERATED,
        f"AI risk assessment: {complaint.severity.value} — {complaint.suggested_next_action}",
    )

    db.add(AIAssessment(
        complaint_id=complaint.id, model_used=settings.groq_primary_model, stage="extraction",
        raw_output=result.get("extracted_updates", {}), confidence=result.get("confidence", {}),
    ))

    db.commit()
    db.refresh(complaint)
    return _build_extraction_response(complaint, result)


def process_new_pdf_complaint(db: Session, extracted_text: str, filename: str) -> ExtractionResponse:
    complaint = Complaint(
        complaint_number=generate_complaint_number(db),
        status=ComplaintStatus.DRAFT,
        source_document=filename,
    )
    db.add(complaint)
    db.flush()

    db.add(ComplaintAttachment(
        complaint_id=complaint.id, filename=filename, file_type="application/pdf",
        extracted_text_preview=extracted_text[:1000],
    ))
    _log_audit(db, complaint, AuditEventType.COMPLAINT_CREATED, f"Complaint draft created from uploaded PDF '{filename}'.", actor="System")

    result = run_complaint_graph({
        "mode": "new_pdf",
        "raw_input_text": extracted_text,
        "existing_fields": {},
        "existing_complaints_summary": _get_duplicate_candidates(db, None),
        "source_document": filename,
    })

    changes = _apply_state_to_complaint(complaint, result)
    _log_audit(
        db, complaint, AuditEventType.AI_EXTRACTION,
        f"AI extracted {len(changes)} field(s) from PDF '{filename}' via text extraction.",
        metadata={"fields": [c[0] for c in changes]},
    )
    _log_audit(
        db, complaint, AuditEventType.RISK_ASSESSMENT_GENERATED,
        f"AI risk assessment: {complaint.severity.value} — {complaint.suggested_next_action}",
    )

    db.add(AIAssessment(
        complaint_id=complaint.id, model_used=settings.groq_primary_model, stage="extraction",
        raw_output=result.get("extracted_updates", {}), confidence=result.get("confidence", {}),
    ))

    db.commit()
    db.refresh(complaint)
    return _build_extraction_response(complaint, result)


def process_chat_correction(db: Session, complaint_id: str, message: str) -> ExtractionResponse:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise ValueError(f"Complaint {complaint_id} not found")

    result = run_complaint_graph({
        "mode": "correction",
        "raw_input_text": message,
        "existing_fields": _complaint_to_dict(complaint),
        "existing_complaints_summary": _get_duplicate_candidates(db, complaint.id),
    })

    changes = _apply_state_to_complaint(complaint, result)
    for field, old_value, new_value in changes:
        _log_audit(
            db, complaint, AuditEventType.FIELD_CORRECTED,
            f"{field.replace('_', ' ').title()} changed from '{old_value or 'empty'}' to '{new_value}'.",
            actor="User via AIVOA Copilot",
            metadata={"field": field, "old_value": old_value, "new_value": new_value},
        )
    # The LangGraph pipeline re-runs classification and risk assessment on
    # every correction turn (not just field extraction), since a
    # correction can change what the complaint fundamentally is (e.g.
    # swapping in a different product entirely). Log that distinctly so
    # the audit trail shows *why* severity/category may have changed even
    # though the user's message didn't explicitly ask to reclassify.
    _log_audit(
        db, complaint, AuditEventType.RISK_ASSESSMENT_GENERATED,
        f"AI re-assessed risk after correction: {complaint.severity.value} — {complaint.suggested_next_action}",
    )

    db.add(AIAssessment(
        complaint_id=complaint.id, model_used=settings.groq_primary_model, stage="correction",
        raw_output=result.get("extracted_updates", {}), confidence=result.get("confidence", {}),
    ))

    db.commit()
    db.refresh(complaint)

    # Returning the SAME full-snapshot shape as process-text/process-pdf
    # (not just the changed fields) is deliberate: the backend recomputes
    # classification, risk assessment, duplicates, root cause, and CAPA on
    # every correction turn — a partial "just the diff" response would let
    # the frontend show stale risk/category data after a correction that
    # changes what the complaint fundamentally is.
    return _build_extraction_response(complaint, result)


def get_full_state(db: Session, complaint_id: str) -> ExtractionResponse:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise ValueError(f"Complaint {complaint_id} not found")
    fake_result = {
        "completeness": {"complete": not complaint.missing_fields, "missing_fields": complaint.missing_fields or []},
        "duplicates": [],
        "root_cause": None,
        "capa": None,
        "assistant_message": "",
    }
    return _build_extraction_response(complaint, fake_result)


def commit_complaint(db: Session, complaint_id: str, fields: ComplaintFields, reviewer_name: str) -> CommitResponse:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise ValueError(f"Complaint {complaint_id} not found")

    # Apply any last-mile edits the reviewer made directly in the form
    # before committing (human-in-the-loop: the user's final edits win).
    for key in COMPLAINT_FIELD_KEYS:
        value = getattr(fields, key, None)
        if value is not None:
            setattr(complaint, key, value)

    reviewer = db.execute(select(Reviewer).where(Reviewer.name == reviewer_name)).scalar_one_or_none()
    if reviewer is None:
        reviewer = Reviewer(name=reviewer_name, email=f"{reviewer_name.lower().replace(' ', '.')}@aivoa.demo", role="QA Reviewer")
        db.add(reviewer)
        db.flush()

    complaint.status = ComplaintStatus.COMMITTED
    complaint.committed_at = datetime.utcnow()
    complaint.committed_by_id = reviewer.id

    _log_audit(
        db, complaint, AuditEventType.COMPLAINT_COMMITTED,
        f"Complaint {complaint.complaint_number} committed to QMS ledger by {reviewer_name}.",
        actor=reviewer_name,
    )

    db.commit()
    db.refresh(complaint)

    return CommitResponse(
        complaint_id=complaint.id,
        complaint_number=complaint.complaint_number,
        status=complaint.status.value,
        committed_at=complaint.committed_at,
    )
