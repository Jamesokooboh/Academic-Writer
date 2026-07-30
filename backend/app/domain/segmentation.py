import pysbd

_segmenter = pysbd.Segmenter(language="en", clean=False)


def segment_sentences(text: str) -> list[str]:
    return [s.strip() for s in _segmenter.segment(text) if s.strip()]
