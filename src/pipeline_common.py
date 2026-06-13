"""Orchestration partagée : validation, ingestion STG, dbt, logging pipeline."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ANSI_ESCAPE = re.compile(r"\x1B\[[0-9;]*m")


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def setup_paths() -> tuple[Path, Path]:
    root = project_root()
    sql_dir = root / "SQL"
    src_dir = root / "src"
    if str(sql_dir) not in sys.path:
        sys.path.insert(0, str(sql_dir))
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return root, sql_dir


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def get_pipeline_logger(truncate: bool = False) -> logging.Logger:
    setup_paths()
    from snowflake_utils import PIPELINE_LOG, setup_logger

    return setup_logger("pipeline", PIPELINE_LOG, truncate=truncate)


def should_truncate_pipeline_log(**context) -> bool:
    """Tronque pipeline.log au trigger manuel ; append en backfill."""
    dag_run = context.get("dag_run")
    if dag_run is None:
        return True
    run_id = getattr(dag_run, "run_id", "") or ""
    return run_id.startswith("manual__")


def finalize_pipeline_log(logger: logging.Logger | None = None) -> None:
    setup_paths()
    from snowflake_utils import PIPELINE_LOG, verify_log_file

    log = logger or get_pipeline_logger()
    file_handler = getattr(log, "file_handler", None)
    if file_handler and not getattr(file_handler, "_closed", False):
        file_handler.close()
    verify_log_file(PIPELINE_LOG, "pipeline", handler=file_handler)


def resolve_python_bin(root: Path | None = None) -> str:
    if sys.executable:
        return sys.executable
    root = root or project_root()
    for candidate in (
        root / ".venv" / "bin" / "python",
        root / ".venv" / "Scripts" / "python.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return "python"


def resolve_dbt_bin(root: Path | None = None) -> str:
    found = shutil.which("dbt")
    if found:
        return found
    root = root or project_root()
    for candidate in (
        root / ".venv" / "bin" / "dbt",
        root / ".venv" / "Scripts" / "dbt.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return "dbt"


def _log_dbt_output(log: logging.Logger, text: str | None) -> None:
    if not text:
        return
    for line in text.splitlines():
        cleaned = strip_ansi(line).strip()
        if not cleaned:
            continue
        lower = cleaned.lower()
        if "[error" in lower or lower.startswith("error"):
            log.error(cleaned)
        elif "[warn" in lower or lower.startswith("warning"):
            log.warning(cleaned)
        else:
            log.info(cleaned)


def validate_date_for_load(date: str) -> str:
    """Valide la date et la présence des fichiers sources pour un jour donné."""
    from load_data import _default_data_dir, validate_date, validate_source_files

    validated = validate_date(date)
    validate_source_files(validated, _default_data_dir())
    return validated


def run_ingestion(date: str, log_truncate: bool = False) -> bool:
    from load_data import _default_data_dir, load_data_day

    return load_data_day(
        date,
        data_dir=_default_data_dir(),
        log_truncate=log_truncate,
        finalize_log_file=False,
    )


def run_dbt(
    root: Path | None = None,
    date: str | None = None,
    logger: logging.Logger | None = None,
) -> int:
    root = root or project_root()
    dbt_project = root / "dbt_hopital"
    dbt_log_dir = dbt_project / "target" / "dbt_logs"
    dbt_log_dir.mkdir(parents=True, exist_ok=True)
    dbt_bin = resolve_dbt_bin(root)
    log = logger or get_pipeline_logger(truncate=False)

    if date:
        log.info(f"──── dbt run — date={date} ────")
    else:
        log.info("──── dbt run ────")

    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["DBT_LOG_PATH"] = str(dbt_log_dir)

    result = subprocess.run(
        [
            dbt_bin,
            "run",
            "--project-dir",
            str(dbt_project),
            "--profiles-dir",
            str(dbt_project),
            "--log-path",
            str(dbt_log_dir),
            "--log-level",
            "info",
            "--log-format",
            "text",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    _log_dbt_output(log, result.stdout)
    _log_dbt_output(log, result.stderr)

    if result.returncode != 0:
        log.error(f"dbt run échoué (code {result.returncode})")
    else:
        log.info("dbt run terminé avec succès")

    return result.returncode


def resolve_dates_for_run(current_date: str) -> list[str]:
    """Construction de la liste des dates à traiter 
    avec reprises en échec antérieures + date du DagRun."""
    from pipeline_failed_dates import get_pending_before

    dates = get_pending_before(current_date)
    if current_date not in dates:
        dates.append(current_date)
    return sorted(set(dates))


def validate_dates(
    dates: list[str],
    logger: logging.Logger | None = None,
) -> dict[str, bool]:
    """Valide chaque date ; continue même si une reprise échoue."""
    from pipeline_failed_dates import mark_failed

    log = logger or get_pipeline_logger(truncate=False)
    log.info("──── Validation des fichiers sources ────")
    results: dict[str, bool] = {}
    for date in dates:
        try:
            validate_date_for_load(date)
            results[date] = True
            log.info(f"  {date} : OK")
        except (ValueError, FileNotFoundError) as exc:
            results[date] = False
            mark_failed(date)
            log.error(f"  {date} : ÉCHEC — {exc}")
    return results


def run_ingestion_for_dates(
    dates: list[str],
    logger: logging.Logger | None = None,
) -> dict[str, bool]:
    """Charge STG pour chaque date validée en amont ; continue sur échec de reprise."""
    log = logger or get_pipeline_logger(truncate=False)
    log.info("──── Ingestion STG ────")
    results: dict[str, bool] = {}
    for date in dates:
        ok = run_ingestion(date)
        results[date] = ok
        status = "OK" if ok else "ÉCHEC"
        log.info(f"  {date} : {status}")
    return results


def run_dbt_for_dates(
    dates: list[str],
    ingestion_results: dict[str, bool],
    root: Path | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, bool]:
    """dbt par date ingérée ; recharge STG si besoin (truncate à chaque load)."""
    from pipeline_failed_dates import mark_failed, mark_ok

    root = root or project_root()
    log = logger or get_pipeline_logger(truncate=False)
    log.info("──── Transformations dbt ────")
    results: dict[str, bool] = {}
    last_date = dates[-1] if dates else None
    for date in dates:
        if not ingestion_results.get(date, False):
            results[date] = False
            mark_failed(date)
            log.error(f"  {date} : dbt ignoré (ingestion en échec)")
            continue

        if date != last_date and not run_ingestion(date):
            results[date] = False
            mark_failed(date)
            log.error(f"  {date} : dbt ignoré (rechargement STG en échec)")
            continue

        ok = run_dbt(root, date=date, logger=log) == 0
        results[date] = ok
        if ok:
            mark_ok(date)
            log.info(f"  {date} : OK")
        else:
            mark_failed(date)
            log.error(f"  {date} : ÉCHEC")
    return results
