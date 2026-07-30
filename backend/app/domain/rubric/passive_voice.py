import re

_BE_FORMS = r"(?:am|is|are|was|were|be|been|being)"
_IRREGULAR_PARTICIPLES = {
    "done", "made", "given", "taken", "shown", "known", "seen", "written", "built",
    "found", "held", "kept", "left", "brought", "bought", "caught", "taught", "thought",
    "sent", "spent", "told", "sold", "said", "paid", "heard", "read", "led", "met",
    "felt", "meant", "understood", "chosen", "broken", "spoken", "driven", "gotten",
    "grown", "drawn", "become", "begun",
}
_PASSIVE_RE = re.compile(rf"\b{_BE_FORMS}\b\s+(?:\w+ly\s+)?(\w+)\b", re.IGNORECASE)


def _is_passive(sentence: str) -> bool:
    for match in _PASSIVE_RE.finditer(sentence):
        word = match.group(1).lower()
        if word.endswith("ed") or word.endswith("en") or word in _IRREGULAR_PARTICIPLES:
            return True
    return False


# ponytail: regex heuristic, not a dependency parse — can false-positive on adjectival
# past participles ("were tired"). Upgrade to spaCy (nsubj:pass) if precision matters more
# than the extra ~500MB model dependency.
def passive_voice_score(sentence: str) -> float:
    return 0.4 if _is_passive(sentence) else 1.0
