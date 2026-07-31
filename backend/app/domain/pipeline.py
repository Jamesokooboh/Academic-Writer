import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.base import ProviderAdapter, ProviderResponse
from app.db.models import ApiUsageLog, Chunk, Document, Rewrite, Sentence, SentenceStatus
from app.db.repositories import get_active_rubric
from app.domain.chunking import chunk_document
from app.domain.cost import estimate_cost_usd
from app.domain.rewrite_engine import RewriteRequest, iter_batches, rewrite_batch
from app.domain.rubric.scorer import RubricWeights, score_sentence
from app.domain.segmentation import segment_sentences
from app.domain.spelling import detect_spelling_variant
from app.similarity.validator import TwoStageValidator

logger = logging.getLogger("app.pipeline")


@dataclass(frozen=True)
class RewriteOutcome:
    sentence_id: int
    original_text: str
    rewritten_text: str
    stage_a_score: float
    stage_b_score: float | None


def _log_usage(db: Session, document_id: int, request_id: str, provider: str, response: ProviderResponse) -> None:
    db.add(
        ApiUsageLog(
            document_id=document_id,
            request_id=request_id,
            provider=provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
            cost_usd=estimate_cost_usd(response.model, response.input_tokens, response.output_tokens),
        )
    )


def analyze_document(db: Session, document: Document, content: str) -> None:
    """Chunks + segments + scores the document, replacing any prior analysis in place."""
    rubric = get_active_rubric(db)
    weights = RubricWeights.from_dict(rubric.weights)

    for chunk in list(document.chunks):
        db.delete(chunk)
    db.flush()

    for chunk_data in chunk_document(content):
        chunk = Chunk(
            document_id=document.id,
            order_index=chunk_data.order_index,
            raw_text=chunk_data.raw_text,
            context_tail=chunk_data.context_tail,
        )
        db.add(chunk)
        db.flush()

        for sentence_index, sentence_text in enumerate(segment_sentences(chunk_data.raw_text)):
            scored = score_sentence(sentence_text, document.writing_mode, weights, rubric.threshold)
            db.add(
                Sentence(
                    chunk_id=chunk.id,
                    order_index=sentence_index,
                    original_text=sentence_text,
                    status=SentenceStatus.NEEDS_IMPROVEMENT if scored.needs_improvement else SentenceStatus.GOOD,
                    quality_score=scored.composite,
                    quality_breakdown=scored.breakdown,
                )
            )

    db.commit()


async def rewrite_document(
    db: Session,
    document: Document,
    adapter: ProviderAdapter,
    provider_name: str,
    model: str,
    validator: TwoStageValidator,
    request_id: str,
) -> list[RewriteOutcome]:
    """Batches every NEEDS_IMPROVEMENT sentence per chunk, rewrites, validates, and
    persists the result. Sentences that fail validation keep their original text."""
    outcomes: list[RewriteOutcome] = []
    spelling_variant = detect_spelling_variant("\n\n".join(c.raw_text for c in document.chunks))

    for chunk in sorted(document.chunks, key=lambda c: c.order_index):
        pending = [s for s in sorted(chunk.sentences, key=lambda s: s.order_index) if s.status == SentenceStatus.NEEDS_IMPROVEMENT]
        if not pending:
            continue

        sentences_by_id = {s.id: s for s in pending}
        requests = [RewriteRequest(id=s.id, text=s.original_text) for s in pending]

        for batch in iter_batches(requests):
            results, response = await rewrite_batch(
                adapter=adapter,
                model=model,
                batch=batch,
                context=chunk.context_tail or "",
                writing_mode=document.writing_mode,
                rewrite_strength=document.rewrite_strength,
                spelling_variant=spelling_variant,
            )
            _log_usage(db, document.id, request_id, provider_name, response)

            for result in results:
                sentence = sentences_by_id[result.id]
                if result.rewritten_text.strip() == sentence.original_text.strip():
                    continue  # model chose not to change it — nothing to validate or persist

                validation = await validator.validate(sentence.original_text, result.rewritten_text)
                db.add(
                    Rewrite(
                        sentence_id=sentence.id,
                        model_used=model,
                        stage_a_score=validation.stage_a_score,
                        stage_b_score=validation.stage_b_score,
                        passed_validation=validation.passed,
                        accepted=None,
                    )
                )

                if not validation.passed:
                    continue  # discard: original sentence stays unchanged

                sentence.rewritten_text = result.rewritten_text
                sentence.status = SentenceStatus.REWRITTEN
                outcomes.append(
                    RewriteOutcome(
                        sentence_id=sentence.id,
                        original_text=sentence.original_text,
                        rewritten_text=result.rewritten_text,
                        stage_a_score=validation.stage_a_score,
                        stage_b_score=validation.stage_b_score,
                    )
                )

    db.commit()
    return outcomes
