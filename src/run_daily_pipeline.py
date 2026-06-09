"""
run_daily_pipeline.py — Exécution locale pour un jour (indépendant du DAG Airflow)

Charge STG et lance dbt run pour LOCAL_RUN_DATE (modifiable dans ce fichier).

  python src/run_daily_pipeline.py
"""

from __future__ import annotations

from pipeline_common import project_root, run_dbt, run_ingestion, setup_paths

LOCAL_RUN_DATE = "20260429"

LOG_BASENAME = "run_daily_pipeline.log"


def _finalize_logger(logger) -> None:
    from snowflake_utils import verify_log_file

    file_handler = getattr(logger, "file_handler", None)
    if file_handler and not getattr(file_handler, "_closed", False):
        file_handler.close()
    verify_log_file(LOG_BASENAME, "run_daily_pipeline", handler=file_handler)


def main() -> int:
    root, _sql_dir = setup_paths()

    from load_data import _default_data_dir, validate_date, validate_source_files  # noqa: E402
    from snowflake_utils import setup_logger  # noqa: E402

    logger = setup_logger("run_daily_pipeline", LOG_BASENAME)
    data_dir = _default_data_dir()
    dbt_project = root / "dbt_hopital"

    try:
        date = validate_date(LOCAL_RUN_DATE)
        validate_source_files(date, data_dir)
    except (ValueError, FileNotFoundError) as exc:
        msg = f"Aucun jeu de fichiers complet pour {LOCAL_RUN_DATE} — load et dbt ignorés."
        logger.error(f"{msg} Détail : {exc}")
        print(f"[run_daily_pipeline] ERREUR : {msg}")
        _finalize_logger(logger)
        return 1

    logger.info("=" * 60)
    logger.info(f"DÉMARRAGE PIPELINE LOCAL — date={date}")
    logger.info(f"Répertoire données : {data_dir}")
    logger.info("=" * 60)
    print(f"[run_daily_pipeline] Date à traiter : {date}")

    if not run_ingestion(date):
        logger.error(f"Échec load_data pour la date {date}")
        print(f"[run_daily_pipeline] ERREUR : échec chargement STG pour {date}")
        _finalize_logger(logger)
        return 1

    logger.info("Lancement dbt run")
    print(f"[run_daily_pipeline] dbt run — projet {dbt_project}")
    rc = run_dbt(root)
    if rc != 0:
        logger.error(f"dbt run échoué (code {rc})")
        print(f"[run_daily_pipeline] ERREUR : dbt run code {rc}")
        _finalize_logger(logger)
        return rc

    logger.info(f"SUCCÈS pour {date}")
    logger.info("=" * 60)
    print(f"[run_daily_pipeline] SUCCÈS — date traitée : {date}")
    _finalize_logger(logger)
    return 0


if __name__ == "__main__":
    _setup_paths()
    from snowflake_utils import cli_exit  

    cli_exit(main())
