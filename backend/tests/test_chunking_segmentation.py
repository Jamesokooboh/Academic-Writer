from app.domain.chunking import chunk_document
from app.domain.segmentation import segment_sentences


def test_chunk_document_splits_on_blank_lines():
    text = "First paragraph sentence one. Sentence two.\n\nSecond paragraph starts here."
    chunks = chunk_document(text)

    assert len(chunks) == 2
    assert chunks[0].order_index == 0
    assert chunks[0].context_tail is None
    assert chunks[1].context_tail == chunks[0].raw_text[-200:]


def test_chunk_document_ignores_extra_blank_lines():
    text = "Para one.\n\n\n\nPara two."
    chunks = chunk_document(text)
    assert len(chunks) == 2
    assert chunks[1].raw_text == "Para two."


def test_segment_sentences_splits_on_boundaries():
    sentences = segment_sentences("The cat sat. The dog ran! Did it work?")
    assert sentences == ["The cat sat.", "The dog ran!", "Did it work?"]


def test_segment_sentences_strips_whitespace_and_drops_empties():
    sentences = segment_sentences("  One sentence.   \n\n  ")
    assert sentences == ["One sentence."]
