from __future__ import annotations

import argparse
import signal
from datetime import datetime, timedelta

import prometheus_client
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Settings
from app.ksef.service import KsefService
from app.notifications.factory import build_connectors
from app.runner import run_once
from app.storage.repository import Repository
from app.utils.logger import get_logger, setup_logging


def _build_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KSeF monitor")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["run-once"],
        help="run-once: execute a single check and exit",
    )
    return parser.parse_args()


def main() -> None:
    settings = Settings()
    setup_logging(settings)
    logger = get_logger(__name__)

    logger.info(
        "Starting KSeF monitor",
        extra={"env": settings.KSEF_ENV, "nip": settings.KSEF_NIP},
    )

    ksef_service = KsefService(settings)
    repo = Repository(settings.STORAGE_PATH)
    connectors = build_connectors(settings)

    if settings.METRICS_ENABLED:
        prometheus_client.start_http_server(settings.METRICS_PORT)
        logger.info("Metrics server started on port %d", settings.METRICS_PORT)

    args = _build_parser()

    if args.command == "run-once":
        run_once(ksef_service, repo, connectors, settings.KSEF_NIP)
        return

    _run_scheduler(settings, ksef_service, repo, connectors, logger)


def _next_run_at(hour: int, minute: int) -> datetime:
    now = datetime.now().astimezone()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _run_scheduler(settings, ksef_service, repo, connectors, logger) -> None:
    hour, minute = settings.check_time_parts()
    first_run = _next_run_at(hour, minute)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_once,
        trigger=IntervalTrigger(
            hours=settings.CHECK_INTERVAL_HOURS,
            start_date=first_run,
        ),
        kwargs={
            "ksef_service": ksef_service,
            "repo": repo,
            "connectors": connectors,
            "nip": settings.KSEF_NIP,
        },
        id="ksef_monitor",
        replace_existing=True,
        max_instances=1,
    )

    def _shutdown(signum, frame) -> None:
        logger.info("Shutting down scheduler (signal %d)", signum)
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info(
        "Scheduler started — first run at %s, then every %d hours",
        first_run.isoformat(),
        settings.CHECK_INTERVAL_HOURS,
    )


    run_once(ksef_service, repo, connectors, settings.KSEF_NIP)
    scheduler.start()


if __name__ == "__main__":
    main()
