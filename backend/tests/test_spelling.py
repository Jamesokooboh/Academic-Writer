from app.domain.spelling import detect_spelling_variant


def test_detects_british_english():
    text = "The colour of the organisation's behaviour was analysed in the centre report."
    assert detect_spelling_variant(text) == "British English"


def test_detects_american_english():
    text = "The color of the organization's behavior was analyzed in the center report."
    assert detect_spelling_variant(text) == "American English"


def test_returns_none_when_no_signal():
    assert detect_spelling_variant("The cat sat on the mat and looked at the door.") is None


def test_returns_none_when_tied():
    text = "colour color organise organize"
    assert detect_spelling_variant(text) is None
