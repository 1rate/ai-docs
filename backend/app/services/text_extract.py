from io import BytesIO

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text(*, raw: bytes, content_type: str, filename: str) -> str:
    lowered = filename.lower()
    if content_type == "application/pdf" or lowered.endswith(".pdf"):
        return _from_pdf(raw)
    if (
        content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or lowered.endswith(".docx")
    ):
        return _from_docx(raw)
    if content_type.startswith("text/") or lowered.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported file for indexing: {content_type}")


def _from_pdf(raw: bytes) -> str:
    reader = PdfReader(BytesIO(raw))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    return "\n".join(parts).strip()


def _from_docx(raw: bytes) -> str:
    document = DocxDocument(BytesIO(raw))
    parts = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    return "\n".join(parts).strip()
