import json
import logging
from typing import Callable

from app.ai.base import ProviderAdapter, ProviderResponse
from app.similarity.base import EntailmentChecker

logger = logging.getLogger("app.similarity.entailment")

_SYSTEM_PROMPT = (
    "You are a strict semantic entailment judge. Given an original sentence and a revised "
    "sentence, decide whether they express exactly the same meaning in both directions "
    "(original entails revised, AND revised entails original) — no added, removed, or "
    "altered facts, claims, or qualifiers. "
    'Respond with ONLY a JSON object: {"score": <float 0.0-1.0>}. '
    "1.0 = fully equivalent meaning, 0.0 = meaning clearly diverges. No other text."
)


class LLMEntailmentChecker(EntailmentChecker):
    """Stage B: a hosted-LLM judge, per the Phase 1 design decision to use one when a
    good local NLI model isn't configured. Reuses the same ProviderAdapter as rewriting."""

    def __init__(self, adapter: ProviderAdapter, model: str, on_usage: Callable[[ProviderResponse], None] | None = None):
        self._adapter = adapter
        self._model = model
        self._on_usage = on_usage

    async def score(self, original: str, revised: str) -> float:
        prompt = f"Original: {original}\nRevised: {revised}"
        response = await self._adapter.complete(system=_SYSTEM_PROMPT, prompt=prompt, model=self._model)
        if self._on_usage:
            self._on_usage(response)
        try:
            data = json.loads(response.text.strip())
            return max(0.0, min(1.0, float(data["score"])))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            logger.warning("entailment_judge_unparseable_response", extra={"extra_fields": {"raw": response.text}})
            # Fail closed: an unparseable judge response means we can't confirm meaning
            # was preserved, so treat it as a failed check rather than assuming success.
            return 0.0
