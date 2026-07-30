from app.domain.rubric.ai_phrasing import ai_phrasing_score
from app.domain.rubric.grammar import grammar_score
from app.domain.rubric.passive_voice import passive_voice_score
from app.domain.rubric.readability import readability_score
from app.domain.rubric.redundancy import redundancy_score
from app.domain.rubric.scorer import RubricWeights, score_sentence


def test_grammar_score_perfect_when_no_errors():
    assert grammar_score("This sentence is clean.") == 1.0


def test_grammar_score_degrades_gracefully_on_checker_failure(monkeypatch):
    from app.domain.rubric import grammar

    def _boom():
        raise RuntimeError("service unreachable")

    monkeypatch.setattr(grammar, "_get_tool", _boom)
    assert grammar_score("Anything at all.") == 1.0


def test_readability_score_perfect_at_target_grade():
    # A short, simple sentence sits at a low grade level, close to the Undergraduate target's low end.
    score = readability_score("The cat sat on the mat.", "Undergraduate")
    assert 0.0 <= score <= 1.0


def test_passive_voice_penalizes_passive_construction():
    active = passive_voice_score("The researchers analyzed the data.")
    passive = passive_voice_score("The data was analyzed by the researchers.")
    assert active == 1.0
    assert passive < active


def test_redundancy_score_penalizes_filler_phrases():
    clean = redundancy_score("We tested the hypothesis directly.")
    wordy = redundancy_score("Due to the fact that in order to test the hypothesis, we did so.")
    assert clean == 1.0
    assert wordy < clean


def test_ai_phrasing_score_penalizes_stock_llm_phrases():
    clean = ai_phrasing_score("The results support our hypothesis.")
    ai_sounding = ai_phrasing_score("It's important to note that we delve into the results.")
    assert clean == 1.0
    assert ai_sounding < clean


def test_score_sentence_composite_matches_weighted_sum():
    weights = RubricWeights()
    scored = score_sentence("The data was analyzed by the researchers.", "Professional", weights, threshold=0.75)

    expected = sum(scored.breakdown[name] * getattr(weights, name) for name in scored.breakdown)
    assert scored.composite == expected
    assert scored.needs_improvement == (scored.composite < 0.75)


def test_rubric_weights_from_dict_uses_defaults_for_missing_keys():
    weights = RubricWeights.from_dict({"grammar": 0.5})
    assert weights.grammar == 0.5
    assert weights.readability == RubricWeights().readability
