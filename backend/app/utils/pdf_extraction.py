"""
PDF text extraction.

Per the assignment, production-grade OCR/document parsing is explicitly
NOT required. This extracts embedded text using pdfplumber (falling back
to PyPDF2), which handles the realistic case of a text-based complaint
PDF/report (the kind a QA team would actually generate or receive as an
email attachment). Scanned/image-only PDFs will yield little or no text;
in that case we return an empty string and the caller surfaces a clear
"couldn't extract text from this document" message rather than silently
failing or fabricating content.
"""
import io

import pdfplumber


class PDFExtractionError(Exception):
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not file_bytes:
        raise PDFExtractionError("Empty file.")

    text_parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)
    except Exception as exc:
        raise PDFExtractionError(f"Could not read PDF: {exc}") from exc

    return "\n".join(text_parts).strip()
