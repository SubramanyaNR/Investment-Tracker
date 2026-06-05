"""Lightweight structured logging for cache + rate-limit events.

Emits greppable one-liners (`event=<name> k=v ...`) on the `wealthsignal` logger so
cache hit/miss ratios and rate-limit blocks can be validated in production logs
(`/tmp/it-backend.log`). Kept deliberately minimal — no metrics backend.
"""
import logging
import re

logger = logging.getLogger("wealthsignal")

# Scrub secrets that may appear inside error messages before they are logged.
_DSN_CREDS = re.compile(r"(://)[^:/@\s]+:[^@/\s]+@")          # ://user:pass@host
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]*")  # JWT


def redact(text: str) -> str:
    text = _DSN_CREDS.sub(r"\1***:***@", text)
    text = _JWT.sub("***JWT***", text)
    return text

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_event(event: str, **fields) -> None:
    if fields:
        logger.info("event=%s %s", event, " ".join(f"{k}={v}" for k, v in fields.items()))
    else:
        logger.info("event=%s", event)
