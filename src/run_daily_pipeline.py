"""Pipeline local : ingestion STG + dbt run pour LOCAL_RUN_DATE (hors Airflow)."""

from __future__ import annotations

from pipeline_common import (
    finalize_pipeline_log,
    get_pipeline_logger,
    project_root,
    run_dbt,
    run_ingestion,
    setup_paths,
)

LOCAL_RUN_DATE = "20260429"


def main() -> int:
    root, _sql_dir = setup_paths()

    from load_data import _default_data_dir, validate_date, validate_source_files  # noqa: E402

    log = get_pipeline_logger(truncate=True)
    data_dir = _default_data_dir()
    dbt_project = root / "dbt_hopital"

    try:
        date = validate_date(LOCAL_RUN_DATE)
        validate_source_files(date, data_dir)
    except (ValueError, FileNotFoundError) as exc:
        msg = f"Aucun jeu de fichiers complet pour {LOCAL_RUN_DATE} — load et dbt ignorés."
        log.error(f"{msg} Détail : {exc}")
        print(f"[run_daily_pipeline] ERREUR : {msg}")
        finalize_pipeline_log(log)
        return 1

    log.info("=" * 60)
    log.info(f"DÉMARRAGE PIPELINE LOCAL — date={date}")
    log.info(f"Répertoire données : {data_dir}")
    log.info("=" * 60)
    print(f"[run_daily_pipeline] Date à traiter : {date}")

    if not run_ingestion(date, log_truncate=False):
        log.error(f"Échec load_data pour la date {date}")
        print(f"[run_daily_pipeline] ERREUR : échec chargement STG pour {date}")
        finalize_pipeline_log(log)
        return 1

    log.info("Lancement dbt run")
    print(f"[run_daily_pipeline] dbt run — projet {dbt_project}")
    rc = run_dbt(root, date=date, logger=log)
    if rc != 0:
        log.error(f"dbt run échoué (code {rc})")
        print(f"[run_daily_pipeline] ERREUR : dbt run code {rc}")
        finalize_pipeline_log(log)
        return rc

    log.info(f"SUCCÈS pour {date}")
    log.info("=" * 60)
    print(f"[run_daily_pipeline] SUCCÈS — date traitée : {date}")
    finalize_pipeline_log(log)
    return 0


if __name__ == "__main__":
    setup_paths()
    from snowflake_utils import cli_exit

    cli_exit(main())
