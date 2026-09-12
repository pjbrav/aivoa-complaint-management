"""Generates complaint numbers in the CC-YYYY-##### format shown in the demo."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint


def generate_complaint_number(db: Session) -> str:
    year = datetime.utcnow().year
    prefix = f"CC-{year}-"

    count = db.execute(
        select(func.count(Complaint.id)).where(Complaint.complaint_number.like(f"{prefix}%"))
    ).scalar_one()

    next_seq = count + 1
    return f"{prefix}{next_seq:05d}"
