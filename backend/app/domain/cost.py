# Approximate USD price per 1K tokens (input, output). Not billing-grade — refresh from
# each provider's pricing page when it changes. Unknown models cost 0 (visible as $0 in
# the UI rather than silently wrong).
_PRICE_PER_1K: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (0.003, 0.015),
    "claude-haiku-4-5-20251001": (0.001, 0.005),
    "gpt-4o": (0.0025, 0.010),
    "gpt-4o-mini": (0.00015, 0.0006),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = _PRICE_PER_1K.get(model, (0.0, 0.0))
    return (input_tokens / 1000) * input_price + (output_tokens / 1000) * output_price
