_AI_PHRASES = [
    "it's important to note", "it is important to note", "delve into", "in today's fast-paced world",
    "in the realm of", "navigate the complexities", "unlock the potential", "a testament to",
    "plays a pivotal role", "in conclusion, it is evident that", "shed light on",
    "underscore the importance", "furthermore, it is worth mentioning", "as we delve deeper",
    "in an increasingly", "stands as a", "serves as a reminder", "it is worth noting that",
]


def ai_phrasing_score(sentence: str) -> float:
    lowered = sentence.lower()
    hits = sum(1 for phrase in _AI_PHRASES if phrase in lowered)
    return max(0.0, 1.0 - hits * 0.5)
