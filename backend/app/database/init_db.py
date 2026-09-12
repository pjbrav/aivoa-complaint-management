"""
Creates all tables and seeds:
  - one demo Reviewer
  - two COMMITTED demo complaints matching the reference video's two
    scenarios (Amoxicillin / discoloration, and Metformin API / foreign
    matter), so duplicate detection and the complaint list have
    something realistic to show immediately on a fresh clone.

Run with:  python -m app.database.init_db
"""
from datetime import datetime, timedelta

from app.database.session import Base, engine, SessionLocal
from app.models.complaint import (
    Complaint, ComplaintAuditLog, Reviewer, ComplaintStatus, Severity, AuditEventType,
)
import app.models  # noqa: F401  (ensures all models are registered on Base.metadata)


def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        reviewer = db.query(Reviewer).filter_by(email="priya.menon@aivoa.demo").first()
        if not reviewer:
            reviewer = Reviewer(name="Priya Menon", role="QA Reviewer", email="priya.menon@aivoa.demo")
            db.add(reviewer)
            db.flush()

        if db.query(Complaint).count() == 0:
            now = datetime.utcnow()

            c1 = Complaint(
                complaint_number="CC-2026-00001",
                status=ComplaintStatus.COMMITTED,
                complaint_source="Pharmacy",
                customer_name="Apollo Pharmacy",
                product_name="Amoxicillin Capsules",
                product_strength_grade="500 mg",
                batch_lot_number="AMX240602",
                affected_quantity="12 capsules",
                manufacturing_date="March 2026",
                expiry_date="February 2028",
                originating_site_block="Manufacturing",
                impacted_npm="Primary Packaging (Bottle)",
                complaint_category="Product Defect - Discoloration",
                complaint_description=(
                    "Apollo Pharmacy reported 12 discolored capsules in a sealed bottle. "
                    "Requesting investigation and replacement."
                ),
                severity=Severity.MAJOR,
                suggested_next_action="Route to QA Investigation & Issue Replacement",
                initial_risk_assessment=(
                    "Potential moisture ingress or primary packaging seal failure leading to "
                    "capsule discoloration. Requires investigation."
                ),
                confidence={"product_name": 0.97, "batch_lot_number": 0.95},
                missing_fields=[],
                created_at=now - timedelta(days=6),
                committed_at=now - timedelta(days=6),
                committed_by_id=reviewer.id,
            )

            c2 = Complaint(
                complaint_number="CC-2026-00154",
                status=ComplaintStatus.COMMITTED,
                complaint_source="Email",
                customer_name="Zenith Life Sciences",
                product_name="Metformin Hydrochloride API",
                product_strength_grade="IP/BP",
                batch_lot_number="MFH260712A",
                affected_quantity="25 kg (1 HDPE Drum)",
                manufacturing_date="25 June 2026",
                expiry_date="Not Provided",
                originating_site_block="Manufacturing",
                impacted_npm="HDPE Drum",
                complaint_category="Foreign Matter Contamination",
                complaint_description=(
                    "Zenith Life Sciences reported multiple dark foreign particles inside one "
                    "sealed HDPE drum during incoming quality inspection. The drum had no visible "
                    "external damage. Material quarantined."
                ),
                severity=Severity.CRITICAL,
                suggested_next_action="Laboratory Investigation & Manufacturing Review",
                initial_risk_assessment=(
                    "Potential foreign matter contamination with high impact to API quality. "
                    "Requires laboratory investigation and manufacturing process review."
                ),
                source_document="Zenith_Life_Sciences_CC-2026-00154.pdf",
                confidence={"product_name": 0.94, "batch_lot_number": 0.9},
                missing_fields=[],
                created_at=now - timedelta(days=2),
                committed_at=now - timedelta(days=2),
                committed_by_id=reviewer.id,
            )

            db.add_all([c1, c2])
            db.flush()

            for complaint in (c1, c2):
                db.add(ComplaintAuditLog(
                    complaint_id=complaint.id, event_type=AuditEventType.COMPLAINT_CREATED,
                    description="Seed demo complaint created.", actor="System",
                ))
                db.add(ComplaintAuditLog(
                    complaint_id=complaint.id, event_type=AuditEventType.COMPLAINT_COMMITTED,
                    description=f"Complaint {complaint.complaint_number} committed to QMS ledger by {reviewer.name}.",
                    actor=reviewer.name,
                ))

        db.commit()
        print("Database initialized and seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
