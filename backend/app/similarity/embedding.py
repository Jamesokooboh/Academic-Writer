from app.similarity.base import EmbeddingSimilarity


class SentenceTransformerSimilarity(EmbeddingSimilarity):
    """Local, no-API-cost Stage A pre-filter. Model loads lazily on first use so
    importing this module never requires the (large) model download."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def score(self, original: str, revised: str) -> float:
        from sentence_transformers import util

        model = self._get_model()
        embeddings = model.encode([original, revised], convert_to_tensor=True)
        return float(util.cos_sim(embeddings[0], embeddings[1]))
