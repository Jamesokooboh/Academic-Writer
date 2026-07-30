import pytest

from app.similarity.base import EmbeddingSimilarity, EntailmentChecker
from app.similarity.validator import TwoStageValidator


class FakeEmbedding(EmbeddingSimilarity):
    def __init__(self, value: float):
        self._value = value

    def score(self, original: str, revised: str) -> float:
        return self._value


class FakeEntailment(EntailmentChecker):
    def __init__(self, value: float):
        self._value = value
        self.calls = 0

    async def score(self, original: str, revised: str) -> float:
        self.calls += 1
        return self._value


@pytest.mark.asyncio
async def test_stage_a_failure_skips_stage_b_entirely():
    entailment = FakeEntailment(1.0)
    validator = TwoStageValidator(FakeEmbedding(0.5), entailment, stage_a_threshold=0.9, stage_b_threshold=0.85)

    result = await validator.validate("original", "revised")

    assert result.passed is False
    assert result.stage_a_score == 0.5
    assert result.stage_b_score is None
    assert entailment.calls == 0  # cost control: never call the LLM judge if Stage A already failed


@pytest.mark.asyncio
async def test_both_stages_pass():
    validator = TwoStageValidator(FakeEmbedding(0.95), FakeEntailment(0.9), stage_a_threshold=0.9, stage_b_threshold=0.85)
    result = await validator.validate("original", "revised")
    assert result.passed is True
    assert result.stage_a_score == 0.95
    assert result.stage_b_score == 0.9


@pytest.mark.asyncio
async def test_stage_b_below_threshold_fails_validation():
    validator = TwoStageValidator(FakeEmbedding(0.95), FakeEntailment(0.5), stage_a_threshold=0.9, stage_b_threshold=0.85)
    result = await validator.validate("original", "revised")
    assert result.passed is False
    assert result.stage_b_score == 0.5
