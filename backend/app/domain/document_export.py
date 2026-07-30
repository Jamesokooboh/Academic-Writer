import io

from app.db.models import Document, SentenceStatus

_UNICODE_TO_ASCII = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "--", "…": "...",
}


def build_final_text(document: Document) -> str:
    """The current draft: rewritten text where a validated rewrite is applied, original
    text everywhere else (including rejected or not-yet-reviewed rewrites)."""
    paragraphs = []
    for chunk in sorted(document.chunks, key=lambda c: c.order_index):
        sentences = sorted(chunk.sentences, key=lambda s: s.order_index)
        effective = [
            s.rewritten_text if s.status == SentenceStatus.REWRITTEN and s.rewritten_text else s.original_text
            for s in sentences
        ]
        if effective:
            paragraphs.append(" ".join(effective))
    return "\n\n".join(paragraphs)


def to_markdown(text: str) -> bytes:
    return text.encode("utf-8")


def to_docx(text: str) -> bytes:
    import docx

    document = docx.Document()
    for paragraph in text.split("\n\n"):
        document.add_paragraph(paragraph)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


# ponytail: core PDF fonts only cover latin-1/cp1252, so smart quotes/dashes are mapped to
# ASCII and anything else is dropped. Upgrade to a bundled Unicode TTF (fpdf2 add_font) if
# non-Latin text needs to round-trip exactly.
def _pdf_safe(text: str) -> str:
    for unicode_char, ascii_char in _UNICODE_TO_ASCII.items():
        text = text.replace(unicode_char, ascii_char)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def to_pdf(text: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=11)
    for paragraph in text.split("\n\n"):
        pdf.multi_cell(0, 8, _pdf_safe(paragraph))
        pdf.ln(4)
    return bytes(pdf.output())
