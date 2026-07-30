from abc import ABC, abstractmethod


class EmbeddingSimilarity(ABC):
    @abstractmethod
    def score(self, original: str, revised: str) -> float:
        """Cosine similarity in [-1, 1] (typically [0, 1] for natural-language sentences)."""


class EntailmentChecker(ABC):
    @abstractmethod
    async def score(self, original: str, revised: str) -> float:
        """Bidirectional entailment confidence in [0, 1]; 1.0 = fully equivalent meaning."""
