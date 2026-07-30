import json
import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_REDACT_KEYS = {"password", "token", "api_key", "authorization", "secret"}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update({k: v for k, v in extra.items() if k.lower() not in _REDACT_KEYS})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def log_event(logger: logging.Logger, level: int, message: str, **fields) -> None:
    logger.log(level, message, extra={"extra_fields": fields})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Assigns a request id and logs method/path/status/latency as structured JSON."""

    def __init__(self, app, logger_name: str = "app.request"):
        super().__init__(app)
        self._logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next):
        token = request_id_var.set(str(uuid.uuid4()))
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log_event(
                self._logger,
                logging.ERROR,
                "request_failed",
                method=request.method,
                path=request.url.path,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )
            raise
        else:
            log_event(
                self._logger,
                logging.INFO,
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )
            response.headers["X-Request-ID"] = request_id_var.get()
            return response
        finally:
            request_id_var.reset(token)
