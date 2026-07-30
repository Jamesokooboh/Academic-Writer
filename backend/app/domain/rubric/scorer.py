from dataclasses import dataclass, field

from app.domain.rubric.ai_phrasing import ai_phrasing_score
from app.domain.rubric.grammar import grammar_score
from app.domain.rubric.passive_voice import passive_voice_score
from app.domain.rubric.readability import readability_score
from app.domain.rubric.redundancy import redundancy_score


@dataclass(frozen=True)
class RubricWeights:
    grammar: float = 0.30
    readability: float = 0.20
    passive_voice: float = 0.15
    redundancy: float = 0.15
    ai_phrasing: float = 0.20

    @classmethod
    def from_dict(cls, weights: dict[str, float]) -> "RubricWeights":
        return cls(**{k: weights[k] for k in _FIELD_NAMES if k in weights})


_FIELD_NAMES = ("grammar", "readability", "passive_voice", "redundancy", "ai_phrasing")


@dataclass(frozen=True)
class ScoredSentence:
    composite: float
    breakdown: dict[str, float] = field(default_factory=dict)
    needs_improvement: bool = False


def score_sentence(sentence: str, writing_mode: str, weights: RubricWeights, threshold: float) -> ScoredSentence:
    breakdown = {
        "grammar": grammar_score(sentence),
        "readability": readability_score(sentence, writing_mode),
        "passive_voice": passive_voice_score(sentence),
        "redundancy": redundancy_score(sentence),
        "ai_phrasing": ai_phrasing_score(sentence),
    }
    composite = sum(breakdown[name] * getattr(weights, name) for name in _FIELD_NAMES)
    return ScoredSentence(composite=composite, breakdown=breakdown, needs_improvement=composite < threshold)
