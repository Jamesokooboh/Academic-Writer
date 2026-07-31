import re

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def strip_code_fence(text: str) -> str:
    """Some models wrap JSON responses in markdown code fences despite being told to
    return raw JSON only. Strip a leading/trailing fence, if present, before parsing."""
    return _CODE_FENCE_RE.sub("", text.strip()).strip()
