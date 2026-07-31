from app.ai.text_parsing import strip_code_fence


def test_strips_json_fence():
    assert strip_code_fence('```json\n{"score": 1.0}\n```') == '{"score": 1.0}'


def test_strips_bare_fence():
    assert strip_code_fence('```\n{"score": 1.0}\n```') == '{"score": 1.0}'


def test_leaves_plain_json_unchanged():
    assert strip_code_fence('{"score": 1.0}') == '{"score": 1.0}'
