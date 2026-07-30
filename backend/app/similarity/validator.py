from dataclasses import dataclass

from app.similarity.base import EmbeddingSimilarity, EntailmentChecker


@dataclass(frozen=True)
class ValidationResult:
    stage_a_score: float
    stage_b_score: float | None
    passed: bool


class TwoStageValidator:
    """Stage A (cheap embedding filter) gates Stage B (LLM entailment judge) so a
    clearly-divergent rewrite never costs a Stage B call."""

    def __init__(
        self,
        embedding: EmbeddingSimilarity,
        entailment: EntailmentChecker,
        stage_a_threshold: float,
        stage_b_threshold: float,
    ):
        self._embedding = embedding
        self._entailment = entailment
        self._stage_a_threshold = stage_a_threshold
        self._stage_b_threshold = stage_b_threshold

    async def validate(self, original: str, revised: str) -> ValidationResult:
        stage_a_score = self._embedding.score(original, revised)
        if stage_a_score < self._stage_a_threshold:
            return ValidationResult(stage_a_score=stage_a_score, stage_b_score=None, passed=False)

        stage_b_score = await self._entailment.score(original, revised)
        return ValidationResult(
            stage_a_score=stage_a_score,
            stage_b_score=stage_b_score,
            passed=stage_b_score >= self._stage_b_threshold,
        )
