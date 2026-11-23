import logging
import re
import sys
from app.core.config import settings


class SensitiveDataFilter(logging.Filter):
    """Redacts passwords, bearer tokens, secrets, and DB credentials from logs."""

    PATTERNS = [
        # Redact Bearer JWT tokens
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", re.IGNORECASE), r"\1[REDACTED]"),
        # Redact key=value or "key": "value" patterns for sensitive fields
        (re.compile(r'(["\']?(?:password|password_hash|token|access_token|secret|jwt_secret_key|authorization)["\']?\s*[:=]\s*["\']?)([^"\'\s,}]+)', re.IGNORECASE), r"\1[REDACTED]"),
        # Redact database connection string passwords (e.g., postgresql://user:pass@host)
        (re.compile(r"(://[^:\s]+:)([^@\s]+)(@)"), r"\1[REDACTED]\3"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern, replacement in self.PATTERNS:
            message = pattern.sub(replacement, message)
        record.msg = message
        record.args = ()
        return True


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("task_manager")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | env=" + settings.APP_ENV + " | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logging()