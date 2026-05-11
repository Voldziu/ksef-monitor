from __future__ import annotations

import time

from prometheus_client import Counter, Gauge, Histogram

from app.models import MonitorResult

cycle_runs_total = Counter(
    "ksef_cycle_runs_total",
    "Total number of monitor cycles executed",
)

invoices_new_total = Counter(
    "ksef_invoices_new_total",
    "Total number of new invoices detected",
)

invoices_skipped_total = Counter(
    "ksef_invoices_skipped_total",
    "Total number of invoices skipped (already seen)",
)

cycle_errors_total = Counter(
    "ksef_cycle_errors_total",
    "Total number of errors during cycles",
    labelnames=["connector"],
)

cycle_duration_seconds = Histogram(
    "ksef_cycle_duration_seconds",
    "Duration of a single monitor cycle in seconds",
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
)

last_cycle_timestamp = Gauge(
    "ksef_last_cycle_timestamp",
    "Unix timestamp of the last completed monitor cycle",
)


def record_cycle(result: MonitorResult, duration: float) -> None:
    cycle_runs_total.inc()
    invoices_new_total.inc(result.new_count)
    invoices_skipped_total.inc(result.skipped_count)
    cycle_duration_seconds.observe(duration)
    last_cycle_timestamp.set(time.time())

    for error in result.errors:
        connector_name = error.split(":")[0].strip() if ":" in error else "unknown"
        cycle_errors_total.labels(connector=connector_name).inc()
