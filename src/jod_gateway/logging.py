import logging
import os

import structlog


def setup_logging(level: str = "INFO") -> None:
    env = os.environ.get("JOD_ENV", "prod")
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    structlog.reset_defaults()

    shared: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if env == "dev":
        processors = shared + [
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = shared + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
    )