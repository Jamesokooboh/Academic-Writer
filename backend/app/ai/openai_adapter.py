import time

from openai import AsyncOpenAI

from app.ai.base import ProviderAdapter, ProviderResponse


class OpenAIAdapter(ProviderAdapter):
    def __init__(self, api_key: str | None):
        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(self, *, system: str, prompt: str, model: str) -> ProviderResponse:
        start = time.perf_counter()
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        usage = response.usage
        return ProviderResponse(
            text=response.choices[0].message.content or "",
            model=model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )
