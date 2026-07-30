import logging

from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import User

logger = logging.getLogger("app.db")

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_admin_user() -> None:
    """Bootstraps the single admin account from env vars if the users table is empty."""
    if not settings.admin_email or not settings.admin_password:
        logger.info("admin_bootstrap_skipped_no_credentials")
        return

    db: Session = SessionLocal()
    try:
        existing = db.execute(select(User).limit(1)).scalar_one_or_none()
        if existing is not None:
            return
        db.add(User(email=settings.admin_email, password_hash=hash_password(settings.admin_password)))
        db.commit()
        logger.info("admin_bootstrap_created", extra={"extra_fields": {"email": settings.admin_email}})
    except OperationalError:
        logger.warning("admin_bootstrap_failed_run_migrations_first")
    finally:
        db.close()
