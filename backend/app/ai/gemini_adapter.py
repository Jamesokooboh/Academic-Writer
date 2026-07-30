import time

from google import genai
from google.genai import types

from app.ai.base import ProviderAdapter, ProviderResponse


class GeminiAdapter(ProviderAdapter):
    def __init__(self, api_key: str | None):
        self._client = genai.Client(api_key=api_key)

    async def complete(self, *, system: str, prompt: str, model: str) -> ProviderResponse:
        start = time.perf_counter()
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system),
        )
        latency_ms = (time.perf_counter() - start) * 1000
        usage = response.usage_metadata
        return ProviderResponse(
            text=response.text,
            model=model,
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
            latency_ms=latency_ms,
        )
