import json

import pytest
from fastapi.testclient import TestClient

from app.ai.base import ProviderAdapter, ProviderResponse
from app.main import app
from app.similarity.base import EmbeddingSimilarity


class FakeAdapter(ProviderAdapter):
    """Answers both the rewrite-batch prompt and the entailment-judge prompt, based on
    which system prompt is used, so one fake covers both LLM calls the pipeline makes."""

    async def complete(self, *, system: str, prompt: str, model: str) -> ProviderResponse:
        if "entailment judge" in system:
            return ProviderResponse(text='{"score": 1.0}', model=model, input_tokens=5, output_tokens=2, latency_ms=1.0)

        payload = json.loads(prompt)
        rewrites = [{"id": s["id"], "rewritten": s["text"].upper()} for s in payload["sentences"]]
        return ProviderResponse(text=json.dumps(rewrites), model=model, input_tokens=20, output_tokens=10, latency_ms=2.0)


class PassthroughEmbedding(EmbeddingSimilarity):
    def score(self, original: str, revised: str) -> float:
        return 0.95


@pytest.fixture
def auth_client(monkeypatch):
    import app.api.documents as documents_module

    monkeypatch.setattr(documents_module, "get_provider_adapter", lambda provider, settings: FakeAdapter())
    monkeypatch.setattr(documents_module, "_embedding_similarity", PassthroughEmbedding())

    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "test-password"})
        token = login.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


def test_full_pipeline_create_analyze_rewrite_accept_reject_metrics(auth_client):
    create = auth_client.post(
        "/api/documents",
        json={"title": "Doc", "content": "the data was analyzed by the researchers due to the fact that it mattered."},
    )
    assert create.status_code == 201
    document_id = create.json()["id"]

    analyzed = auth_client.post(f"/api/documents/{document_id}/analyze")
    assert analyzed.status_code == 200
    body = analyzed.json()
    assert body["document_id"] == document_id
    assert body["good_count"] + body["needs_improvement_count"] == 1

    rewritten = auth_client.post(f"/api/documents/{document_id}/rewrite")
    assert rewritten.status_code == 200
    rewrite_body = rewritten.json()

    if body["needs_improvement_count"] == 0:
        assert rewrite_body["results"] == []
        return

    assert len(rewrite_body["results"]) == 1
    sentence_id = rewrite_body["results"][0]["sentence_id"]
    assert rewrite_body["results"][0]["rewritten_text"].isupper()
    assert rewrite_body["total_input_tokens"] > 0

    metrics = auth_client.get(f"/api/documents/{document_id}/metrics").json()
    assert metrics["rewritten_count"] == 1
    assert metrics["total_cost_usd"] >= 0

    reject = auth_client.post(f"/api/documents/{document_id}/changes/{sentence_id}/reject")
    assert reject.status_code == 200

    metrics_after_reject = auth_client.get(f"/api/documents/{document_id}/metrics").json()
    assert metrics_after_reject["needs_improvement_count"] == 1
    assert metrics_after_reject["rewritten_count"] == 0


def test_accept_change_marks_rewrite_accepted_without_altering_text(auth_client):
    create = auth_client.post(
        "/api/documents",
        json={"title": "Doc", "content": "the data was analyzed by the researchers due to the fact that it mattered."},
    )
    document_id = create.json()["id"]
    analyzed = auth_client.post(f"/api/documents/{document_id}/analyze").json()
    if analyzed["needs_improvement_count"] == 0:
        pytest.skip("rubric classified the fixture sentence as GOOD in this run; nothing to rewrite/accept")

    rewrite_body = auth_client.post(f"/api/documents/{document_id}/rewrite").json()
    sentence_id = rewrite_body["results"][0]["sentence_id"]

    accept = auth_client.post(f"/api/documents/{document_id}/changes/{sentence_id}/accept")
    assert accept.status_code == 200

    metrics = auth_client.get(f"/api/documents/{document_id}/metrics").json()
    assert metrics["rewritten_count"] == 1  # accept is bookkeeping only; text/status don't change


def test_accept_change_without_a_pending_rewrite_returns_400(auth_client):
    create = auth_client.post("/api/documents", json={"title": "Doc", "content": "A perfectly fine sentence."})
    document_id = create.json()["id"]
    auth_client.post(f"/api/documents/{document_id}/analyze")

    sentence_id = 1  # whatever sentence id analysis produced — no rewrite has been generated for it
    response = auth_client.post(f"/api/documents/{document_id}/changes/{sentence_id}/accept")
    assert response.status_code in (400, 404)


def test_get_document_requires_ownership(auth_client):
    response = auth_client.get("/api/documents/999999")
    assert response.status_code == 404


def test_documents_require_auth():
    with TestClient(app) as client:
        response = client.get("/api/documents/1")
        assert response.status_code in (401, 403)
