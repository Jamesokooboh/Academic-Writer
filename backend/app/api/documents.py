from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.base import ProviderResponse
from app.ai.factory import get_provider_adapter
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.logging import request_id_var
from app.db.models import ApiUsageLog, Chunk, Document, DocumentVersion, Rewrite, Sentence, SentenceStatus, User
from app.db.repositories import get_active_validation_config
from app.db.session import get_db
from app.domain.cost import estimate_cost_usd
from app.domain.document_export import build_final_text, to_docx, to_markdown, to_pdf
from app.domain.document_import import extract_text
from app.domain.pipeline import analyze_document, rewrite_document
from app.schemas.documents import (
    AnalyzeResult,
    ChunkOut,
    DocumentCreate,
    DocumentMetrics,
    DocumentOut,
    DocumentWithContentOut,
    RewriteResultOut,
    RewriteRunResult,
    SentenceOut,
)
from app.similarity.embedding import SentenceTransformerSimilarity
from app.similarity.entailment import LLMEntailmentChecker
from app.similarity.validator import TwoStageValidator

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Loads the embedding model lazily on first use; shared across requests so it's loaded once.
_embedding_similarity = SentenceTransformerSimilarity()


def _document_query():
    return select(Document).options(
        selectinload(Document.chunks).selectinload(Chunk.sentences).selectinload(Sentence.rewrites)
    )


def _get_document_or_404(db: Session, document_id: int, user: User) -> Document:
    document = db.execute(
        _document_query().where(Document.id == document_id, Document.user_id == user.id)
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _get_sentence_or_404(db: Session, document_id: int, sentence_id: int, user: User) -> Sentence:
    sentence = db.execute(
        select(Sentence)
        .join(Chunk, Sentence.chunk_id == Chunk.id)
        .join(Document, Chunk.document_id == Document.id)
        .where(Sentence.id == sentence_id, Chunk.document_id == document_id, Document.user_id == user.id)
        .options(selectinload(Sentence.rewrites))
    ).scalar_one_or_none()
    if sentence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentence not found")
    return sentence


def _latest_rewrite(sentence: Sentence) -> Rewrite | None:
    if not sentence.rewrites:
        return None
    return max(sentence.rewrites, key=lambda r: r.created_at)


def _latest_content(db: Session, document_id: int) -> str:
    version = db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    ).scalars().first()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document has no content version")
    return version.content


def _chunks_out(document: Document) -> list[ChunkOut]:
    return [
        ChunkOut(
            id=chunk.id,
            order_index=chunk.order_index,
            sentences=[
                SentenceOut.model_validate(s) for s in sorted(chunk.sentences, key=lambda s: s.order_index)
            ],
        )
        for chunk in sorted(document.chunks, key=lambda c: c.order_index)
    ]


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DocumentOut:
    document = Document(
        user_id=user.id,
        title=payload.title,
        writing_mode=payload.writing_mode,
        word_count_mode=payload.word_count_mode,
        rewrite_strength=payload.rewrite_strength,
    )
    db.add(document)
    db.flush()
    db.add(DocumentVersion(document_id=document.id, version_number=1, content=payload.content))
    db.commit()
    db.refresh(document)
    return DocumentOut.model_validate(document)


@router.post("/import", response_model=DocumentWithContentOut, status_code=status.HTTP_201_CREATED)
async def import_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    writing_mode: str = Form("Professional"),
    word_count_mode: str = Form("Balanced"),
    rewrite_strength: str = Form("Very Conservative"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentOut:
    content_bytes = await file.read()
    text = extract_text(file.filename or "untitled.txt", content_bytes)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No extractable text found in the uploaded file"
        )

    document = Document(
        user_id=user.id,
        title=title or (file.filename or "Untitled").rsplit(".", 1)[0],
        writing_mode=writing_mode,
        word_count_mode=word_count_mode,
        rewrite_strength=rewrite_strength,
    )
    db.add(document)
    db.flush()
    db.add(DocumentVersion(document_id=document.id, version_number=1, content=text))
    db.commit()
    db.refresh(document)
    return DocumentWithContentOut(**DocumentOut.model_validate(document).model_dump(), content=text)


_EXPORT_CONTENT_TYPES = {
    "md": "text/markdown",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}
_EXPORT_BUILDERS = {"md": to_markdown, "docx": to_docx, "pdf": to_pdf}


@router.get("/{document_id}/export")
def export_document(
    document_id: int, format: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    if format not in _EXPORT_BUILDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{format}'. Use one of: {sorted(_EXPORT_BUILDERS)}",
        )

    document = _get_document_or_404(db, document_id, user)
    text = build_final_text(document)
    body = _EXPORT_BUILDERS[format](text)
    return Response(
        content=body,
        media_type=_EXPORT_CONTENT_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{document.title}.{format}"'},
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DocumentOut:
    return DocumentOut.model_validate(_get_document_or_404(db, document_id, user))


@router.post("/{document_id}/analyze", response_model=AnalyzeResult)
def analyze(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AnalyzeResult:
    document = _get_document_or_404(db, document_id, user)
    content = _latest_content(db, document_id)
    analyze_document(db, document, content)

    document = _get_document_or_404(db, document_id, user)
    good = sum(1 for c in document.chunks for s in c.sentences if s.status == SentenceStatus.GOOD)
    needs = sum(1 for c in document.chunks for s in c.sentences if s.status == SentenceStatus.NEEDS_IMPROVEMENT)
    return AnalyzeResult(
        document_id=document.id, chunks=_chunks_out(document), good_count=good, needs_improvement_count=needs
    )


@router.post("/{document_id}/rewrite", response_model=RewriteRunResult)
async def rewrite(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> RewriteRunResult:
    document = _get_document_or_404(db, document_id, user)
    settings = get_settings()
    validation_config = get_active_validation_config(db)
    request_id = request_id_var.get()

    adapter = get_provider_adapter(settings.default_provider, settings)

    def _log_entailment_usage(response: ProviderResponse) -> None:
        db.add(
            ApiUsageLog(
                document_id=document.id,
                request_id=request_id,
                provider=settings.default_provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                cost_usd=estimate_cost_usd(response.model, response.input_tokens, response.output_tokens),
            )
        )

    validator = TwoStageValidator(
        embedding=_embedding_similarity,
        entailment=LLMEntailmentChecker(adapter=adapter, model=settings.default_model, on_usage=_log_entailment_usage),
        stage_a_threshold=validation_config.stage_a_threshold,
        stage_b_threshold=validation_config.stage_b_threshold,
    )

    outcomes = await rewrite_document(
        db=db,
        document=document,
        adapter=adapter,
        provider_name=settings.default_provider,
        model=settings.default_model,
        validator=validator,
        request_id=request_id,
    )

    totals = db.execute(
        select(
            func.coalesce(func.sum(ApiUsageLog.input_tokens), 0),
            func.coalesce(func.sum(ApiUsageLog.output_tokens), 0),
            func.coalesce(func.sum(ApiUsageLog.cost_usd), 0.0),
        ).where(ApiUsageLog.document_id == document.id, ApiUsageLog.request_id == request_id)
    ).one()

    results_out = [
        RewriteResultOut(
            sentence_id=o.sentence_id,
            original_text=o.original_text,
            rewritten_text=o.rewritten_text,
            stage_a_score=o.stage_a_score,
            stage_b_score=o.stage_b_score,
            passed_validation=True,
        )
        for o in outcomes
    ]
    return RewriteRunResult(
        document_id=document.id,
        results=results_out,
        total_input_tokens=int(totals[0]),
        total_output_tokens=int(totals[1]),
        total_cost_usd=float(totals[2]),
    )


@router.post("/{document_id}/changes/{sentence_id}/accept")
def accept_change(
    document_id: int, sentence_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    sentence = _get_sentence_or_404(db, document_id, sentence_id, user)
    latest = _latest_rewrite(sentence)
    if latest is None or not latest.passed_validation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending rewrite to accept")
    latest.accepted = True
    db.commit()
    return {"detail": "accepted"}


@router.post("/{document_id}/changes/{sentence_id}/reject")
def reject_change(
    document_id: int, sentence_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    sentence = _get_sentence_or_404(db, document_id, sentence_id, user)
    latest = _latest_rewrite(sentence)
    if latest is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending rewrite to reject")
    latest.accepted = False
    sentence.rewritten_text = None
    sentence.status = SentenceStatus.NEEDS_IMPROVEMENT
    db.commit()
    return {"detail": "rejected"}


@router.get("/{document_id}/metrics", response_model=DocumentMetrics)
def metrics(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DocumentMetrics:
    document = _get_document_or_404(db, document_id, user)

    good = needs = rewritten = 0
    original_words = rewritten_words = 0
    stage_a_scores: list[float] = []
    stage_b_scores: list[float] = []

    for chunk in document.chunks:
        for sentence in chunk.sentences:
            if sentence.status == SentenceStatus.GOOD:
                good += 1
            elif sentence.status == SentenceStatus.NEEDS_IMPROVEMENT:
                needs += 1
            else:
                rewritten += 1
            original_words += len(sentence.original_text.split())
            rewritten_words += len((sentence.rewritten_text or sentence.original_text).split())
            for r in sentence.rewrites:
                stage_a_scores.append(r.stage_a_score)
                if r.stage_b_score is not None:
                    stage_b_scores.append(r.stage_b_score)

    totals = db.execute(
        select(
            func.coalesce(func.sum(ApiUsageLog.input_tokens), 0),
            func.coalesce(func.sum(ApiUsageLog.output_tokens), 0),
            func.coalesce(func.sum(ApiUsageLog.cost_usd), 0.0),
        ).where(ApiUsageLog.document_id == document.id)
    ).one()

    return DocumentMetrics(
        good_count=good,
        needs_improvement_count=needs,
        rewritten_count=rewritten,
        average_stage_a_score=(sum(stage_a_scores) / len(stage_a_scores)) if stage_a_scores else None,
        average_stage_b_score=(sum(stage_b_scores) / len(stage_b_scores)) if stage_b_scores else None,
        original_word_count=original_words,
        rewritten_word_count=rewritten_words,
        total_input_tokens=int(totals[0]),
        total_output_tokens=int(totals[1]),
        total_cost_usd=float(totals[2]),
    )
