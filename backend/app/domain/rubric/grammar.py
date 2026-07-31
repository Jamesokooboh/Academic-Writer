import logging

from app.core.config import get_settings

logger = logging.getLogger("app.rubric.grammar")

_tool = None


def _get_tool():
    global _tool
    if _tool is None:
        import language_tool_python

        url = get_settings().languagetool_url
        if url:
            _tool = language_tool_python.LanguageTool("en-US", remote_server=url)
        else:
            # ponytail: public API (no Java/local server required), rate-limited by
            # languagetool.org. Set LANGUAGETOOL_URL to a self-hosted server if throughput
            # or reliability becomes a problem.
            _tool = language_tool_python.LanguageToolPublicAPI("en-US")
    return _tool


def grammar_score(sentence: str) -> float:
    """1.0 = no detected errors. Degrades gracefully (neutral 1.0) if the external
    grammar service is unreachable or rate-limited, rather than failing the whole
    scoring pass over one external dependency."""
    try:
        matches = _get_tool().check(sentence)
    except Exception:
        logger.warning("grammar_check_unavailable", exc_info=True)
        return 1.0

    words = max(len(sentence.split()), 1)
    error_density = len(matches) / words
    return max(0.0, 1.0 - error_density * 10)
