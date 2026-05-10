import logging
import sys

from datetime import datetime


class CustomFormatter(logging.Formatter):
    """
    Structured log format for better debugging and observability.
    """

    def format(self, record):

        log_data = {
            "time": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }

        return str(log_data)


def setup_logging():
    """
    Configures global logging for the entire application.
    """

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomFormatter())

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
    )
