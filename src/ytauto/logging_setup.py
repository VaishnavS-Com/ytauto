"""Project-wide logging configuration.

WHY NOT print()?
----------------
`print` gives you text with no timestamp, no severity, no source, and no
record on disk. When a pipeline runs unattended at 3 AM (which is the whole
point of automation), logs are the ONLY way to know what happened.

Every module gets its logger the same way:

    from ytauto.logging_setup import get_logger
    log = get_logger(__name__)
    log.info("Fetched 25 trending topics")

`__name__` makes each log line show which module produced it.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from ytauto.config import settings

# Log line format: time | level | module | message
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

_configured = False  # module-level guard so setup runs only once


def _configure_root() -> None:
    """Attach console + rotating-file handlers to the root logger (once)."""
    global _configured
    if _configured:
        return

    settings.ensure_dirs()  # logs/ must exist before the file handler opens

    root = logging.getLogger()
    root.setLevel(settings.log_level)

    formatter = logging.Formatter(_FORMAT)

    # 1) Console — what you see while developing.
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # 2) Rotating file — permanent record. When app.log reaches 1 MB it is
    #    renamed app.log.1 and a fresh file starts; max 5 backups are kept.
    #    Without rotation, log files grow forever and fill the disk.
    file_handler = RotatingFileHandler(
        settings.logs_dir / "app.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, configuring the logging system on first call."""
    _configure_root()
    return logging.getLogger(name)
