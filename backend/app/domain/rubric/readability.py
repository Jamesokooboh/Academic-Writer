import textstat

_TARGET_GRADE_BY_WRITING_MODE: dict[str, float] = {
    "Undergraduate": 12,
    "MSc": 14,
    "PhD": 16,
    "Journal Article": 16,
    "MBA": 14,
    "Business Report": 12,
    "Professional": 12,
}
_DEFAULT_TARGET_GRADE = 12


def readability_score(sentence: str, writing_mode: str) -> float:
    """1.0 = at the writing mode's target Flesch-Kincaid grade level; decays with distance."""
    target = _TARGET_GRADE_BY_WRITING_MODE.get(writing_mode, _DEFAULT_TARGET_GRADE)
    grade = textstat.flesch_kincaid_grade(sentence)
    distance = abs(grade - target)
    return max(0.0, 1.0 - distance / 10)
