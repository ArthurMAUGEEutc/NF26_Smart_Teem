"""Dates métier en échec — reprise automatique au run suivant (logs/pipeline_failed_dates.txt)."""

from __future__ import annotations

from pathlib import Path

from pipeline_common import project_root

FAILED_DATES_FILE = project_root() / "logs" / "pipeline_failed_dates.txt"


def _read_dates() -> set[str]:
    if not FAILED_DATES_FILE.is_file():
        return set()
    dates: set[str] = set()
    for line in FAILED_DATES_FILE.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value:
            dates.add(value)
    return dates


def _write_dates(dates: set[str]) -> None:
    FAILED_DATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if dates:
        content = "\n".join(sorted(dates)) + "\n"
    else:
        content = ""
    FAILED_DATES_FILE.write_text(content, encoding="utf-8")


def get_pending_before(date: str) -> list[str]:
    """Dates en échec strictement antérieures à ``date``, triées."""
    return sorted(d for d in _read_dates() if d < date)


def mark_ok(date: str) -> None:
    dates = _read_dates()
    if date in dates:
        dates.remove(date)
        _write_dates(dates)


def mark_failed(date: str) -> None:
    dates = _read_dates()
    if date not in dates:
        dates.add(date)
        _write_dates(dates)
