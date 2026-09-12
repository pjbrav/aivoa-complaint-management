"""
Generates a realistic-looking pharmaceutical customer complaint PDF for
demo purposes, matching the "Zenith Life Sciences / Metformin API /
foreign matter contamination" scenario from the reference demo.

This is fictional demonstration data only — no real company, patient, or
product batch information. Run once to produce demo_data/*.pdf.
"""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

styles = getSampleStyleSheet()
title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=16, spaceAfter=4)
subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], textColor=colors.HexColor("#64748b"), fontSize=10)
heading_style = ParagraphStyle("HeadingCustom", parent=styles["Heading2"], fontSize=11, spaceBefore=14, spaceAfter=6)
body_style = ParagraphStyle("BodyCustom", parent=styles["Normal"], fontSize=10, leading=14)


def build_zenith_pdf(path: str):
    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    story = []

    story.append(Paragraph("Zenith Life Sciences Pvt. Ltd.", title_style))
    story.append(Paragraph("Customer Quality Complaint Report", subtitle_style))
    story.append(Spacer(1, 14))

    meta_table = Table(
        [
            ["Complaint Reference:", "CC-2026-00154", "Date Reported:", "12 July 2026"],
            ["Reported Via:", "Email", "Reported By:", "Quality Assurance, Zenith Life Sciences"],
        ],
        colWidths=[1.5 * inch, 2.0 * inch, 1.3 * inch, 1.7 * inch],
    )
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)

    story.append(Paragraph("Product & Batch Details", heading_style))
    product_table = Table(
        [
            ["Product Name", "Metformin Hydrochloride API"],
            ["Grade / Specification", "IP/BP"],
            ["Batch / Lot Number", "MFH260712A"],
            ["Affected Quantity", "25 kg (1 HDPE Drum)"],
            ["Manufacturing Date", "25 June 2026"],
            ["Expiry Date", "Not Provided"],
            ["Originating Site / Block", "Manufacturing"],
            ["Impacted Material", "HDPE Drum (Primary Packaging)"],
        ],
        colWidths=[2.2 * inch, 4.3 * inch],
    )
    product_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d5dd")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f6f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(product_table)

    story.append(Paragraph("Complaint Narrative", heading_style))
    story.append(Paragraph(
        "During incoming quality inspection at our facility, our QC team observed multiple dark "
        "foreign particles inside one sealed HDPE drum of the above-referenced Metformin "
        "Hydrochloride API batch. The drum itself showed no visible external damage, tampering, "
        "or evidence of a compromised seal prior to opening. The affected drum has been "
        "quarantined and segregated from usable stock pending investigation. No other drums "
        "from the same shipment showed similar defects upon visual inspection, but we are "
        "requesting a full investigation given the potential quality impact of foreign matter "
        "contamination in an active pharmaceutical ingredient.",
        body_style,
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "We request a formal investigation, root cause analysis, and confirmation of corrective "
        "and preventive actions, along with a decision on replacement or credit for the affected "
        "quantity.",
        body_style,
    ))

    story.append(Paragraph("Immediate Action Taken", heading_style))
    story.append(Paragraph(
        "Affected drum quarantined. Remaining stock from the same batch placed on hold pending "
        "manufacturer response. Photographs of the foreign particles available upon request.",
        body_style,
    ))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "This document is fictional demonstration data created for the AIVOA AI Product Engineer "
        "assignment and does not represent a real company, product, or event.",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7.5, textColor=colors.HexColor("#94a3b8")),
    ))

    doc.build(story)


if __name__ == "__main__":
    build_zenith_pdf("/home/claude/aivoa-complaints/demo_data/zenith_life_sciences_CC-2026-00154.pdf")
    print("PDF created.")
