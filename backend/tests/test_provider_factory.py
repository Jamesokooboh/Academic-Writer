import pytest

from app.ai.anthropic_adapter import AnthropicAdapter
from app.ai.factory import get_provider_adapter
from app.ai.gemini_adapter import GeminiAdapter
from app.ai.ollama_adapter import OllamaAdapter
from app.ai.openai_adapter import OpenAIAdapter
from app.core.config import Settings


def _settings() -> Settings:
    return Settings(openai_api_key="sk-test", anthropic_api_key="test-key", gemini_api_key="test-key")


@pytest.mark.parametrize(
    "provider,expected_type",
    [
        ("openai", OpenAIAdapter),
        ("anthropic", AnthropicAdapter),
        ("gemini", GeminiAdapter),
        ("ollama", OllamaAdapter),
    ],
)
def test_get_provider_adapter_returns_expected_type(provider, expected_type):
    adapter = get_provider_adapter(provider, _settings())
    assert isinstance(adapter, expected_type)


def test_get_provider_adapter_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_provider_adapter("not-a-provider", _settings())
