import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.db.models import RubricVersion, ValidationConfig  # noqa: E402

_DEFAULT_WEIGHTS = {
    "grammar": 0.30,
    "readability": 0.20,
    "passive_voice": 0.15,
    "redundancy": 0.15,
    "ai_phrasing": 0.20,
}


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(engine)

    db = SessionLocal()
    db.add(RubricVersion(version=1, weights=_DEFAULT_WEIGHTS, threshold=0.75, active=True))
    db.add(ValidationConfig(version=1, stage_a_threshold=0.90, stage_b_threshold=0.85, active=True))
    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    os.close(_db_fd)
    os.remove(_db_path)


@pytest.fixture(autouse=True)
def _no_real_grammar_check(monkeypatch):
    """Grammar scoring calls a rate-limited external service (languagetool.org).
    Tests must never depend on that network call, so stub it with zero errors by default."""
    from app.domain.rubric import grammar

    class _FakeTool:
        def check(self, _sentence: str) -> list:
            return []

    monkeypatch.setattr(grammar, "_tool", _FakeTool())
    monkeypatch.setattr(grammar, "_get_tool", lambda: grammar._tool)
