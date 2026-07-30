import time

from anthropic import AsyncAnthropic

from app.ai.base import ProviderAdapter, ProviderResponse


class AnthropicAdapter(ProviderAdapter):
    def __init__(self, api_key: str | None):
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(self, *, system: str, prompt: str, model: str) -> ProviderResponse:
        start = time.perf_counter()
        response = await self._client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        text = "".join(block.text for block in response.content if block.type == "text")
        return ProviderResponse(
            text=text,
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
        )
