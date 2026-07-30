_FILLER_PHRASES = [
    "due to the fact that", "in order to", "at this point in time", "in the event that",
    "for the purpose of", "with regard to", "in spite of the fact that", "a large number of",
    "it is important to note that", "it should be noted that", "in a manner of speaking",
    "on a daily basis", "in the near future", "at the present time",
]
_NOMINALIZATION_SUFFIXES = ("tion", "ment", "ance", "ence", "sion")
_MIN_NOMINALIZATION_LENGTH = 7


def redundancy_score(sentence: str) -> float:
    lowered = sentence.lower()
    filler_hits = sum(1 for phrase in _FILLER_PHRASES if phrase in lowered)

    words = sentence.split()
    nominalizations = sum(
        1
        for word in words
        if len(word) >= _MIN_NOMINALIZATION_LENGTH and word.lower().rstrip(".,;:").endswith(_NOMINALIZATION_SUFFIXES)
    )

    word_count = max(len(words), 1)
    density = (filler_hits * 3 + nominalizations) / word_count
    return max(0.0, 1.0 - density * 5)
