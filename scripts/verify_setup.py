"""Milestone 0 smoke test — run this to prove your environment works.

From the project root, with your virtual environment active:

    python scripts/verify_setup.py

Expected: settings print to screen, and a log line appears in logs/app.log.
"""


from ytauto.config import settings
from ytauto.logging_setup import get_logger

log = get_logger(__name__)


def main() -> None:
    print("=" * 50)
    print("ytauto — Milestone 0 verification")
    print("=" * 50)
    print(f"Project root : {settings.project_root}")
    print(f"Environment  : {settings.app_env}")
    print(f"Log level    : {settings.log_level}")
    print(f"Niche        : {settings.channel_niche}")
    print(f"Data dir     : {settings.data_dir}")
    print(f"Logs dir     : {settings.logs_dir}")

    log.info("Milestone 0 verification ran successfully")
    log.debug("This only appears when LOG_LEVEL=DEBUG")
    print("\nOK — now open logs/app.log and confirm the log line is there.")


if __name__ == "__main__":
    main()
