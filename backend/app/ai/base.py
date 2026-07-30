from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class ProviderAdapter(ABC):
    """Common interface every LLM provider adapter implements.

    Callers never touch a provider's native SDK directly — swapping models or
    providers is a config change (DEFAULT_PROVIDER/DEFAULT_MODEL), not a code change.
    """

    @abstractmethod
    async def complete(self, *, system: str, prompt: str, model: str) -> ProviderResponse:
        ...
