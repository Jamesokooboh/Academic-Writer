from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RubricVersion, ValidationConfig


def get_active_rubric(db: Session) -> RubricVersion:
    rubric = db.execute(
        select(RubricVersion).where(RubricVersion.active.is_(True)).order_by(RubricVersion.version.desc())
    ).scalars().first()
    if rubric is None:
        raise RuntimeError("No active rubric_versions row found — run migrations.")
    return rubric


def get_active_validation_config(db: Session) -> ValidationConfig:
    config = db.execute(
        select(ValidationConfig).where(ValidationConfig.active.is_(True)).order_by(ValidationConfig.version.desc())
    ).scalars().first()
    if config is None:
        raise RuntimeError("No active validation_configs row found — run migrations.")
    return config
