"""
API routes.

Kept intentionally thin: parse/validate the HTTP request, delegate to
app.services.complaint_service, translate service-layer exceptions into
proper HTTP errors, return a Pydantic response model. No AI or DB logic
lives here.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.groq_client import GroqUnavailableError, GroqMalformedResponseError
from app.config import get_settings
from app.database.session import get_db
from app.models.complaint import Complaint, ComplaintAuditLog
from app.schemas.complaint import (
    ProcessTextRequest,
    ChatRequest,
    ChatResponse,
    ExtractionResponse,
    CommitRequest,
    CommitResponse,
    ComplaintOut,
    ComplaintFields,
    AuditEventOut,
)
from app.services import complaint_service
from app.utils.pdf_extraction import extract_text_from_pdf, PDFExtractionError

router = APIRouter(prefix="/api/complaints", tags=["complaints"])
settings = get_settings()

ALLOWED_PDF_TYPES = {"application/pdf"}


def _handle_ai_errors(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (GroqUnavailableError, GroqMalformedResponseError) as exc:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/process-text", response_model=ExtractionResponse)
def process_text(payload: ProcessTextRequest, db: Session = Depends(get_db)):
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Complaint text cannot be empty.")
    return _handle_ai_errors(complaint_service.process_new_text_complaint, db, payload.text)


@router.post("/process-pdf", response_model=ExtractionResponse)
async def process_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_PDF_TYPES and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_mb}MB limit.")

    try:
        extracted_text = extract_text_from_pdf(contents)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail="No extractable text found in this PDF. It may be a scanned image — "
            "production OCR is out of scope for this MVP. Try pasting the complaint text instead.",
        )

    return _handle_ai_errors(complaint_service.process_new_pdf_complaint, db, extracted_text, file.filename)


@router.post("/chat", response_model=ExtractionResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    return _handle_ai_errors(complaint_service.process_chat_correction, db, payload.complaint_id, payload.message)


@router.post("/commit", response_model=CommitResponse)
def commit(payload: CommitRequest, db: Session = Depends(get_db)):
    return _handle_ai_errors(
        complaint_service.commit_complaint, db, payload.complaint_id, payload.fields, payload.reviewer_name
    )


@router.get("/{complaint_id}", response_model=ExtractionResponse)
def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    return _handle_ai_errors(complaint_service.get_full_state, db, complaint_id)


@router.get("/{complaint_id}/audit-log", response_model=list[AuditEventOut])
def get_audit_log(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    events = db.execute(
        select(ComplaintAuditLog)
        .where(ComplaintAuditLog.complaint_id == complaint_id)
        .order_by(ComplaintAuditLog.created_at)
    ).scalars().all()
    return events


@router.get("", response_model=list[ComplaintOut])
def list_complaints(db: Session = Depends(get_db)):
    complaints = db.execute(select(Complaint).order_by(Complaint.created_at.desc())).scalars().all()
    out = []
    for c in complaints:
        out.append(ComplaintOut(
            id=c.id,
            complaint_number=c.complaint_number,
            status=c.status.value,
            fields=ComplaintFields(
                complaint_source=c.complaint_source, customer_name=c.customer_name,
                product_name=c.product_name, product_strength_grade=c.product_strength_grade,
                batch_lot_number=c.batch_lot_number, affected_quantity=c.affected_quantity,
                manufacturing_date=c.manufacturing_date, expiry_date=c.expiry_date,
                originating_site_block=c.originating_site_block, impacted_npm=c.impacted_npm,
                complaint_category=c.complaint_category, complaint_description=c.complaint_description,
                severity=c.severity.value if c.severity else None,
                suggested_next_action=c.suggested_next_action,
                initial_risk_assessment=c.initial_risk_assessment,
                source_document=c.source_document,
            ),
            confidence=c.confidence or {},
            missing_fields=c.missing_fields or [],
            created_at=c.created_at,
            updated_at=c.updated_at,
            committed_at=c.committed_at,
        ))
    return out
