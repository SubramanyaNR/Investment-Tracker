"""Lightweight structured logging for cache + rate-limit events.

Emits greppable one-liners (`event=<name> k=v ...`) on the `wealthsignal` logger so
cache hit/miss ratios and rate-limit blocks can be validated in production logs
(`/tmp/it-backend.log`). Kept deliberately minimal — no metrics backend.
"""
import logging

logger = logging.getLogger("wealthsignal")

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
