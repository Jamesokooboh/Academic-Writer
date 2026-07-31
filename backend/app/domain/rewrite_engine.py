import json
import logging
from dataclasses import dataclass

from app.ai.base import ProviderAdapter, ProviderResponse
from app.ai.text_parsing import strip_code_fence

logger = logging.getLogger("app.rewrite_engine")

MAX_BATCH_SIZE = 12

SYSTEM_PROMPT = """You are a professional academic editor. Improve grammar, readability, \
flow, sentence variety, passive voice, and wordiness. Remove unnatural AI-sounding phrasing.

Never: invent facts, examples, statistics, citations, or arguments; strengthen or weaken \
claims; change technical terminology or meaning; add unnecessary transitions or adjectives. \
If a sentence cannot be improved without risking a change in meaning, return it unchanged.

If "spelling_variant" is present, the document already uses that convention (e.g. British \
"colour"/"organise" or American "color"/"organize") — preserve it exactly; never convert \
between British and American spelling as part of a rewrite.

You will receive a JSON object with "writing_mode", "rewrite_strength", "spelling_variant" \
(nullable), "context" (the preceding paragraph's tail, for local coherence only — do not \
rewrite it), and "sentences" (a list of {"id": <id>, "text": <text>} to rewrite).

Respond with ONLY a JSON array of {"id": <id>, "rewritten": <text>} — exactly one entry per \
input sentence, same ids, no extra commentary, no markdown fences."""


@dataclass(frozen=True)
class RewriteRequest:
    id: int
    text: str


@dataclass(frozen=True)
class RewriteResult:
    id: int
    rewritten_text: str


def iter_batches(items: list[RewriteRequest], size: int = MAX_BATCH_SIZE):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _build_prompt(
    batch: list[RewriteRequest],
    context: str,
    writing_mode: str,
    rewrite_strength: str,
    spelling_variant: str | None,
) -> str:
    payload = {
        "writing_mode": writing_mode,
        "rewrite_strength": rewrite_strength,
        "spelling_variant": spelling_variant,
        "context": context,
        "sentences": [{"id": r.id, "text": r.text} for r in batch],
    }
    return json.dumps(payload)


async def rewrite_batch(
    adapter: ProviderAdapter,
    model: str,
    batch: list[RewriteRequest],
    context: str,
    writing_mode: str,
    rewrite_strength: str,
    spelling_variant: str | None = None,
) -> tuple[list[RewriteResult], ProviderResponse]:
    prompt = _build_prompt(batch, context, writing_mode, rewrite_strength, spelling_variant)
    response = await adapter.complete(system=SYSTEM_PROMPT, prompt=prompt, model=model)

    try:
        parsed = json.loads(strip_code_fence(response.text))
        by_id = {int(item["id"]): str(item["rewritten"]) for item in parsed}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.warning("rewrite_batch_unparseable_response", extra={"extra_fields": {"raw": response.text}})
        by_id = {}

    # Fail safe: any sentence missing from a malformed response keeps its original text
    # rather than being silently dropped or corrupted.
    results = [RewriteResult(id=r.id, rewritten_text=by_id.get(r.id, r.text)) for r in batch]
    return results, response
