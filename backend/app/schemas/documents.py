from datetime import datetime

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    title: str
    content: str
    writing_mode: str = "Professional"
    word_count_mode: str = "Balanced"
    rewrite_strength: str = "Very Conservative"


class DocumentOut(BaseModel):
    id: int
    title: str
    writing_mode: str
    word_count_mode: str
    rewrite_strength: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentWithContentOut(DocumentOut):
    content: str


class SentenceOut(BaseModel):
    id: int
    order_index: int
    original_text: str
    rewritten_text: str | None
    status: str
    quality_score: float | None
    quality_breakdown: dict[str, float] | None

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    id: int
    order_index: int
    sentences: list[SentenceOut]

    model_config = {"from_attributes": True}


class AnalyzeResult(BaseModel):
    document_id: int
    chunks: list[ChunkOut]
    good_count: int
    needs_improvement_count: int


class RewriteResultOut(BaseModel):
    sentence_id: int
    original_text: str
    rewritten_text: str
    stage_a_score: float
    stage_b_score: float | None
    passed_validation: bool


class RewriteRunResult(BaseModel):
    document_id: int
    results: list[RewriteResultOut]
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float


class DocumentMetrics(BaseModel):
    good_count: int
    needs_improvement_count: int
    rewritten_count: int
    average_stage_a_score: float | None
    average_stage_b_score: float | None
    original_word_count: int
    rewritten_word_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
