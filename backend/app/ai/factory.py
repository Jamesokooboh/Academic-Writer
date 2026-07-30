from app.ai.anthropic_adapter import AnthropicAdapter
from app.ai.base import ProviderAdapter
from app.ai.gemini_adapter import GeminiAdapter
from app.ai.ollama_adapter import OllamaAdapter
from app.ai.openai_adapter import OpenAIAdapter
from app.core.config import Settings

_PROVIDERS = {"openai", "anthropic", "gemini", "ollama"}


def get_provider_adapter(provider: str, settings: Settings) -> ProviderAdapter:
    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Expected one of {sorted(_PROVIDERS)}.")

    if provider == "openai":
        return OpenAIAdapter(api_key=settings.openai_api_key)
    if provider == "anthropic":
        return AnthropicAdapter(api_key=settings.anthropic_api_key)
    if provider == "gemini":
        return GeminiAdapter(api_key=settings.gemini_api_key)
    return OllamaAdapter(base_url=settings.ollama_base_url)
