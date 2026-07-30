import io


def _extract_docx(content: bytes) -> str:
    import docx

    document = docx.Document(io.BytesIO(content))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())


def _extract_plain_text(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


_EXTRACTORS = {
    ".docx": _extract_docx,
    ".pdf": _extract_pdf,
}


def extract_text(filename: str, content: bytes) -> str:
    """Dispatches on file extension. Unknown extensions (.md, .txt, etc.) are treated
    as plain UTF-8 text, which is exactly what Markdown prose already is."""
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    extractor = _EXTRACTORS.get(suffix, _extract_plain_text)
    return extractor(content)
