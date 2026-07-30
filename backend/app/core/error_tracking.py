import logging

logger = logging.getLogger("app.error_tracking")


def init_error_tracking(dsn: str | None) -> None:
    """No-op if no DSN is configured; wires Sentry otherwise."""
    if not dsn:
        logger.info("error_tracking_disabled")
        return

    import sentry_sdk

    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)
    logger.info("error_tracking_enabled")
