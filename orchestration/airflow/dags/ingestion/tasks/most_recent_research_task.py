import structlog

from logging.config import dictConfig

from shared.utils.constants import (
    LOGGING_CONFIG,
)

dictConfig(LOGGING_CONFIG)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

TASK_NAME = "most_recent_research"


def run(**context: dict):
    logger.info(f"Running {TASK_NAME} task", task_name=TASK_NAME, date=context["execution_date"], run_id=context["run_id"])