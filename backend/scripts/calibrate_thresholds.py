"""Calibrates the Stage A (embedding) and Stage B (entailment) thresholds against the
labeled sentence-pair set in tests/data/semantic_pairs.json.

Stage A runs locally (sentence-transformers, no API key) and is calibrated for real
every time this script runs. Stage B requires a configured LLM provider API key — if
none is set, that half is skipped with an explicit message rather than faking a result.

Usage:
    .venv/Scripts/python.exe scripts/calibrate_thresholds.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.similarity.embedding import SentenceTransformerSimilarity  # noqa: E402

DATA_PATH = Path(__file__).resolve().parents[1] / "tests" / "data" / "semantic_pairs.json"
THRESHOLD_SWEEP = [round(0.80 + 0.01 * i, 2) for i in range(19)]  # 0.80 .. 0.98


def _confusion_at_threshold(scores: list[float], labels: list[int], threshold: float) -> dict:
    tp = fp = tn = fn = 0
    for score, label in zip(scores, labels):
        predicted_preserved = score >= threshold
        if predicted_preserved and label == 1:
            tp += 1
        elif predicted_preserved and label == 0:
            fp += 1
        elif not predicted_preserved and label == 0:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(labels) if labels else 0.0
    return {"threshold": threshold, "tp": tp, "fp": fp, "tn": tn, "fn": fn, "accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


def calibrate_stage_a(pairs: list[dict]) -> None:
    print("=== Stage A (embedding cosine similarity) ===")
    embedding = SentenceTransformerSimilarity()
    scores = [embedding.score(p["original"], p["revised"]) for p in pairs]
    labels = [p["label"] for p in pairs]

    print(f"{'threshold':>9} {'acc':>6} {'prec':>6} {'recall':>6} {'f1':>6} {'fn (missed alterations)':>24}")
    best = None
    for threshold in THRESHOLD_SWEEP:
        result = _confusion_at_threshold(scores, labels, threshold)
        print(
            f"{result['threshold']:>9} {result['accuracy']:>6.2f} {result['precision']:>6.2f} "
            f"{result['recall']:>6.2f} {result['f1']:>6.2f} {result['fn']:>24}"
        )
        # A missed meaning-alteration (false negative here means a preserved-meaning
        # prediction on an altered pair) is worse than rejecting a genuinely fine rewrite,
        # so prefer the highest-F1 threshold among those with zero missed alterations.
        if result["fn"] == 0 and (best is None or result["f1"] > best["f1"]):
            best = result

    if best is None:
        best = max((_confusion_at_threshold(scores, labels, t) for t in THRESHOLD_SWEEP), key=lambda r: r["f1"])

    print(f"\nSuggested stage_a_threshold: {best['threshold']} (accuracy={best['accuracy']:.2f}, f1={best['f1']:.2f})")
    print("Update validation_configs.stage_a_threshold via a new Alembic data migration to change the default.\n")


_MODEL_BY_PROVIDER = {
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
}


def _pick_configured_provider(settings) -> tuple[str, str] | None:
    """Prefers settings.default_provider if its key is set, else the first configured one."""
    key_by_provider = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "gemini": settings.gemini_api_key,
    }
    if key_by_provider.get(settings.default_provider):
        return settings.default_provider, settings.default_model
    for provider, key in key_by_provider.items():
        if key:
            return provider, _MODEL_BY_PROVIDER[provider]
    return None


async def calibrate_stage_b(pairs: list[dict]) -> None:
    print("=== Stage B (LLM entailment judge) ===")
    settings = get_settings()
    choice = _pick_configured_provider(settings)
    if choice is None:
        print(
            "Skipped: no provider API key configured (OPENAI_API_KEY / ANTHROPIC_API_KEY / "
            "GEMINI_API_KEY all unset). Stage B calibration makes real, billable LLM calls and "
            "needs live credentials — run this script again once a key is set.\n"
        )
        return
    provider, model = choice
    print(f"Using provider={provider} model={model} ({len(pairs)} pairs — this makes {len(pairs)} real, billable API calls)\n")

    from app.ai.factory import get_provider_adapter
    from app.similarity.entailment import LLMEntailmentChecker

    adapter = get_provider_adapter(provider, settings)
    checker = LLMEntailmentChecker(adapter=adapter, model=model)
    scores = [await checker.score(p["original"], p["revised"]) for p in pairs]
    labels = [p["label"] for p in pairs]

    print(f"{'threshold':>9} {'acc':>6} {'prec':>6} {'recall':>6} {'f1':>6}")
    best = max((_confusion_at_threshold(scores, labels, t) for t in THRESHOLD_SWEEP), key=lambda r: r["f1"])
    for threshold in THRESHOLD_SWEEP:
        result = _confusion_at_threshold(scores, labels, threshold)
        print(f"{result['threshold']:>9} {result['accuracy']:>6.2f} {result['precision']:>6.2f} {result['recall']:>6.2f} {result['f1']:>6.2f}")
    print(f"\nSuggested stage_b_threshold: {best['threshold']} (accuracy={best['accuracy']:.2f}, f1={best['f1']:.2f})\n")


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    pairs = data["pairs"]
    print(f"Loaded {len(pairs)} labeled pairs ({sum(p['label'] for p in pairs)} preserved, "
          f"{sum(1 - p['label'] for p in pairs)} altered)\n")

    calibrate_stage_a(pairs)
    asyncio.run(calibrate_stage_b(pairs))


if __name__ == "__main__":
    main()
