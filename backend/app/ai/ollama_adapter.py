import time

import httpx

from app.ai.base import ProviderAdapter, ProviderResponse


class OllamaAdapter(ProviderAdapter):
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    async def complete(self, *, system: str, prompt: str, model: str) -> ProviderResponse:
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
        response.raise_for_status()
        data = response.json()
        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResponse(
            text=data["message"]["content"],
            model=model,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )
