"""Logging configuration utilities for structured logging with structlog."""

from __future__ import annotations

import logging
from typing import Optional

import structlog


def setup_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Configure application-wide logging with structlog."""

    level = (level or "INFO").upper()

    timestamper = structlog.processors.TimeStamper(fmt="iso", key="timestamp")
    pre_chain = [
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        timestamper,
    ]

    renderer: structlog.typing.Processor
    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=pre_chain,
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            *pre_chain,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
