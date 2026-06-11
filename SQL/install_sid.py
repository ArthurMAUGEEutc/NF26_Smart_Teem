"""
Installation idempotente du SID : bases, tables STG (REPLACE), SOC et TCH (IF NOT EXISTS).
Journal : logs/installation.log — connexion via dbt_hopital/profiles.yml.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from snowflake_utils import (
    INSTALL_LOG,
    LOG_DIR,
    SQL_DIR,
    cli_exit,
    execute_sql_file,
    get_snowflake_connection,
    resolve_project_paths,
    setup_logger,
    verify_log_file,
)

PROJECT_ROOT, _ = resolve_project_paths()
LOG_FILE = LOG_DIR / INSTALL_LOG

logger = setup_logger("install_sid", INSTALL_LOG, truncate=True)

SQL_SCRIPTS = [
    "create_db.sql",
    "create_stg.sql",
    "create_soc.sql",
    "create_tch.sql",
]


def main() -> None:
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("DÉMARRAGE INSTALLATION SID")
    logger.info(f"Date : {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    overall_success = True
    file_handler = logger.file_handler  # type: ignore[attr-defined]

    try:
        conn = get_snowflake_connection(logger)
        cursor = conn.cursor()

        for script_name in SQL_SCRIPTS:
            script_path = SQL_DIR / script_name
            ok = execute_sql_file(cursor, script_path, logger)
            if not ok:
                overall_success = False

        cursor.close()
        conn.close()
        logger.info("Connexion Snowflake fermée.")

    except Exception as e:
        logger.error(f"Erreur critique lors de l'installation : {e}")
        overall_success = False

    duration = datetime.now() - start
    logger.info("=" * 60)
    status = "SUCCÈS" if overall_success else "TERMINÉ AVEC ERREURS"
    logger.info(f"FIN INSTALLATION SID — {status}")
    logger.info(f"Durée totale : {duration}")
    logger.info("=" * 60)

    file_handler.close()
    logging.shutdown()
    verify_log_file(LOG_FILE, "install_sid", handler=file_handler)


if __name__ == "__main__":
    main()
    cli_exit(0)
