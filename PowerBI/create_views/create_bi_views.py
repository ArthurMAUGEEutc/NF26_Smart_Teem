"""
create_bi_views.py, création des vues pour Power BI sur Snowflake
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

# Ajout du dossier SQL au path pour importer snowflake_utils
_SQL_DIR = Path(__file__).resolve().parents[2] / "SQL"
if str(_SQL_DIR) not in sys.path: sys.path.insert(0, str(_SQL_DIR))

from snowflake_utils import (
    LOG_DIR,
    cli_exit,
    execute_sql_file,
    get_snowflake_connection,
    setup_logger,
    verify_log_file,
)

VIEWS_SQL = Path(__file__).resolve().parent / "create_views.sql"
LOG_FILE = LOG_DIR / "create_bi_views.log"

logger = setup_logger("create_bi_views", "create_bi_views.log")


def main() -> None:
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("DÉMARRAGE CRÉATION VUES POWER BI")
    logger.info(f"Date : {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    success = True
    file_handler = logger.file_handler  

    try:
        conn = get_snowflake_connection(logger)
        cursor = conn.cursor()

        ok = execute_sql_file(cursor, VIEWS_SQL, logger)
        if not ok:
            success = False

        cursor.close()
        conn.close()
        logger.info("Connexion Snowflake fermée.")

    except Exception as e:
        logger.error(f"Erreur critique : {e}")
        success = False

    duration = datetime.now() - start
    logger.info("=" * 60)
    status = "SUCCÈS" if success else "TERMINÉ AVEC ERREURS"
    logger.info(f"FIN CRÉATION VUES — {status}")
    logger.info(f"Durée totale : {duration}")
    logger.info("=" * 60)

    file_handler.close()
    logging.shutdown()
    verify_log_file(LOG_FILE, "create_bi_views", handler=file_handler)


if __name__ == "__main__":
    main()
    cli_exit(0)
