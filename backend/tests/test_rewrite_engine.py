import json

import pytest

from app.ai.base import ProviderAdapter, ProviderResponse
from app.domain.rewrite_engine import MAX_BATCH_SIZE, RewriteRequest, iter_batches, rewrite_batch


class FakeAdapter(ProviderAdapter):
    def __init__(self, response_text: str):
        self._response_text = response_text

    async def complete(self, *, system: str, prompt: str, model: str) -> ProviderResponse:
        return ProviderResponse(text=self._response_text, model=model, input_tokens=10, output_tokens=5, latency_ms=1.0)


def test_iter_batches_splits_at_max_size():
    items = [RewriteRequest(id=i, text=f"s{i}") for i in range(30)]
    batches = list(iter_batches(items))
    assert len(batches) == 3
    assert all(len(b) <= MAX_BATCH_SIZE for b in batches)
    assert sum(len(b) for b in batches) == 30


@pytest.mark.asyncio
async def test_rewrite_batch_maps_results_by_id():
    batch = [RewriteRequest(id=1, text="Original one."), RewriteRequest(id=2, text="Original two.")]
    response_text = json.dumps([{"id": 1, "rewritten": "Rewritten one."}, {"id": 2, "rewritten": "Rewritten two."}])
    adapter = FakeAdapter(response_text)

    results, response = await rewrite_batch(adapter, "fake-model", batch, context="", writing_mode="Professional", rewrite_strength="Balanced")

    assert results[0].id == 1 and results[0].rewritten_text == "Rewritten one."
    assert results[1].id == 2 and results[1].rewritten_text == "Rewritten two."
    assert response.input_tokens == 10


@pytest.mark.asyncio
async def test_rewrite_batch_falls_back_to_original_on_malformed_response():
    batch = [RewriteRequest(id=1, text="Original one.")]
    adapter = FakeAdapter("not json at all")

    results, _ = await rewrite_batch(adapter, "fake-model", batch, context="", writing_mode="Professional", rewrite_strength="Balanced")

    assert results[0].rewritten_text == "Original one."


@pytest.mark.asyncio
async def test_rewrite_batch_keeps_original_for_missing_id():
    batch = [RewriteRequest(id=1, text="Original one."), RewriteRequest(id=2, text="Original two.")]
    response_text = json.dumps([{"id": 1, "rewritten": "Rewritten one."}])
    adapter = FakeAdapter(response_text)

    results, _ = await rewrite_batch(adapter, "fake-model", batch, context="", writing_mode="Professional", rewrite_strength="Balanced")

    assert results[1].rewritten_text == "Original two."
