import json
import uuid

import pytest

from app.ai.base import ProviderAdapter, ProviderResponse
from app.db.models import Chunk, Document, DocumentVersion, Rewrite, Sentence, SentenceStatus, User
from app.db.session import SessionLocal
from app.domain.pipeline import analyze_document, rewrite_document
from app.similarity.base import EmbeddingSimilarity, EntailmentChecker
from app.similarity.validator import TwoStageValidator


class AlwaysAcceptEntailment(EntailmentChecker):
    async def score(self, original: str, revised: str) -> float:
        return 1.0


class AlwaysRejectEntailment(EntailmentChecker):
    async def score(self, original: str, revised: str) -> float:
        return 0.0


class PassthroughEmbedding(EmbeddingSimilarity):
    def score(self, original: str, revised: str) -> float:
        return 1.0


class UppercaseRewriteAdapter(ProviderAdapter):
    async def complete(self, *, system: str, prompt: str, model: str) -> ProviderResponse:
        payload = json.loads(prompt)
        rewrites = [{"id": s["id"], "rewritten": s["text"].upper()} for s in payload["sentences"]]
        return ProviderResponse(text=json.dumps(rewrites), model=model, input_tokens=20, output_tokens=10, latency_ms=2.0)


def _make_document(db) -> Document:
    user = User(email=f"test-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    document = Document(
        user_id=user.id,
        title="Test doc",
        writing_mode="Professional",
        word_count_mode="Balanced",
        rewrite_strength="Very Conservative",
    )
    db.add(document)
    db.flush()
    return document


def test_analyze_document_persists_chunks_and_sentences():
    db = SessionLocal()
    try:
        document = _make_document(db)
        content = "First paragraph, one sentence.\n\nSecond paragraph. Two sentences here."
        db.add(DocumentVersion(document_id=document.id, version_number=1, content=content))
        db.commit()

        analyze_document(db, document, content)

        db.refresh(document)
        assert len(document.chunks) == 2
        sentences = [s for c in document.chunks for s in c.sentences]
        assert len(sentences) == 3
        for sentence in sentences:
            assert sentence.status in (SentenceStatus.GOOD, SentenceStatus.NEEDS_IMPROVEMENT)
            assert sentence.quality_breakdown is not None
    finally:
        db.close()


def _add_needs_improvement_sentence(db: SessionLocal, document: Document, text: str) -> Sentence:
    chunk = Chunk(document_id=document.id, order_index=0, raw_text=text, context_tail=None)
    db.add(chunk)
    db.flush()
    sentence = Sentence(chunk_id=chunk.id, order_index=0, original_text=text, status=SentenceStatus.NEEDS_IMPROVEMENT)
    db.add(sentence)
    db.commit()
    db.refresh(document)
    return sentence


@pytest.mark.asyncio
async def test_rewrite_document_applies_and_persists_validated_rewrite():
    db = SessionLocal()
    try:
        document = _make_document(db)
        db.commit()
        sentence = _add_needs_improvement_sentence(db, document, "the data was analyzed.")

        validator = TwoStageValidator(PassthroughEmbedding(), AlwaysAcceptEntailment(), stage_a_threshold=0.9, stage_b_threshold=0.85)
        outcomes = await rewrite_document(
            db=db,
            document=document,
            adapter=UppercaseRewriteAdapter(),
            provider_name="fake",
            model="fake-model",
            validator=validator,
            request_id="test-request",
        )

        assert len(outcomes) == 1
        assert outcomes[0].rewritten_text == "THE DATA WAS ANALYZED."

        db.refresh(sentence)
        assert sentence.status == SentenceStatus.REWRITTEN
        assert sentence.rewritten_text == "THE DATA WAS ANALYZED."

        rewrites = db.query(Rewrite).filter(Rewrite.sentence_id == sentence.id).all()
        assert len(rewrites) == 1
        assert rewrites[0].passed_validation is True
    finally:
        db.close()


@pytest.mark.asyncio
async def test_rewrite_document_discards_rewrite_that_fails_validation():
    db = SessionLocal()
    try:
        document = _make_document(db)
        db.commit()
        sentence = _add_needs_improvement_sentence(db, document, "the data was analyzed.")

        validator = TwoStageValidator(PassthroughEmbedding(), AlwaysRejectEntailment(), stage_a_threshold=0.9, stage_b_threshold=0.85)
        outcomes = await rewrite_document(
            db=db,
            document=document,
            adapter=UppercaseRewriteAdapter(),
            provider_name="fake",
            model="fake-model",
            validator=validator,
            request_id="test-request",
        )

        assert outcomes == []

        db.refresh(sentence)
        assert sentence.status == SentenceStatus.NEEDS_IMPROVEMENT
        assert sentence.rewritten_text is None

        rewrites = db.query(Rewrite).filter(Rewrite.sentence_id == sentence.id).all()
        assert len(rewrites) == 1
        assert rewrites[0].passed_validation is False
    finally:
        db.close()
