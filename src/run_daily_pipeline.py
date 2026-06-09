"""
run_daily_pipeline.py — Orchestrateur DAG (traitement séquentiel jour par jour)

Lit/écrit logs/pipeline_date_cursor.txt, charge STG pour la date courante, lance dbt run,
puis avance le curseur de +1 jour en cas de succès.

  python src/run_daily_pipeline.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PIPELINE_INITIAL_DATE = "20260429"
CURSOR_BASENAME = "pipeline_date_cursor.txt"
LOG_BASENAME = "run_daily_pipeline.log"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _setup_paths() -> tuple[Path, Path]:
    root = _project_root()
    sql_dir = root / "SQL"
    src_dir = root / "src"
    if str(sql_dir) not in sys.path:
        sys.path.insert(0, str(sql_dir))
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return root, sql_dir


def advance_date(yyyymmdd: str) -> str:
    dt = datetime.strptime(yyyymmdd, "%Y%m%d")
    return (dt + timedelta(days=1)).strftime("%Y%m%d")


def read_cursor(cursor_file: Path) -> str:
    if cursor_file.is_file():
        text = cursor_file.read_text(encoding="utf-8").strip()
        if text:
            return text
    return PIPELINE_INITIAL_DATE


def write_cursor(cursor_file: Path, date: str) -> None:
    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    cursor_file.write_text(f"{date}\n", encoding="utf-8")


def resolve_dbt_bin(project_root: Path) -> str:
    found = shutil.which("dbt")
    if found:
        return found
    for candidate in (
        project_root / ".venv" / "bin" / "dbt",
        project_root / ".venv" / "Scripts" / "dbt.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return "dbt"


def _finalize_logger(logger) -> None:
    from snowflake_utils import verify_log_file

    file_handler = getattr(logger, "file_handler", None)
    if file_handler and not getattr(file_handler, "_closed", False):
        file_handler.close()
    verify_log_file(LOG_BASENAME, "run_daily_pipeline", handler=file_handler)


def main() -> int:
    project_root, _sql_dir = _setup_paths()

    from snowflake_utils import LOG_DIR, setup_logger  # noqa: E402
    from load_data import (  # noqa: E402
        _default_data_dir,
        load_data_day,
        validate_date,
        validate_source_files,
    )

    logger = setup_logger("run_daily_pipeline", LOG_BASENAME)
    cursor_file = LOG_DIR / CURSOR_BASENAME
    date = validate_date(read_cursor(cursor_file))
    data_dir = _default_data_dir()
    dbt_project = project_root / "dbt_hopital"

    logger.info("=" * 60)
    logger.info(f"DÉMARRAGE PIPELINE QUOTIDIEN — date={date}")
    logger.info(f"Curseur : {cursor_file}")
    logger.info(f"Répertoire données : {data_dir}")
    logger.info("=" * 60)
    print(f"[run_daily_pipeline] Date à traiter : {date}")

    try:
        validate_source_files(date, data_dir)
    except FileNotFoundError as exc:
        msg = (
            f"Aucun jeu de fichiers complet pour la date {date} — "
            f"load et dbt ignorés, curseur inchangé ({cursor_file})."
        )
        logger.error(f"{msg} Détail : {exc}")
        print(f"[run_daily_pipeline] ERREUR : {msg}")
        _finalize_logger(logger)
        return 1

    if not load_data_day(date, data_dir=data_dir):
        logger.error(f"Échec load_data pour la date {date} — curseur inchangé")
        print(f"[run_daily_pipeline] ERREUR : échec chargement STG pour {date}")
        _finalize_logger(logger)
        return 1

    dbt_bin = resolve_dbt_bin(project_root)
    logger.info(f"Lancement dbt run ({dbt_bin})")
    print(f"[run_daily_pipeline] dbt run — projet {dbt_project}")
    result = subprocess.run(
        [
            dbt_bin,
            "run",
            "--project-dir",
            str(dbt_project),
            "--profiles-dir",
            str(dbt_project),
        ],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        logger.error(
            f"dbt run échoué (code {result.returncode}) — curseur inchangé"
        )
        print(f"[run_daily_pipeline] ERREUR : dbt run code {result.returncode}")
        _finalize_logger(logger)
        return result.returncode

    next_date = advance_date(date)
    write_cursor(cursor_file, next_date)
    logger.info(f"SUCCÈS pour {date} — curseur avancé vers {next_date}")
    logger.info("=" * 60)
    print(f"[run_daily_pipeline] SUCCÈS — prochaine date : {next_date}")
    _finalize_logger(logger)
    return 0


if __name__ == "__main__":
    _setup_paths()
    from snowflake_utils import cli_exit  

    cli_exit(main())
