from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.core.config import get_settings
from app.core.error_tracking import init_error_tracking
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.db.session import ensure_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    init_error_tracking(settings.sentry_dsn)
    ensure_admin_user()
    yield


app = FastAPI(title="Academic Writing Editor API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
