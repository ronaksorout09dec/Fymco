import logging

from pythonjsonlogger.json import JsonFormatter

from app.core.config import get_settings


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(get_settings().log_level.upper())

