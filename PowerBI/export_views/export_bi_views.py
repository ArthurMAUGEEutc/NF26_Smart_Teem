"""
export_bi_views.py — Export des vues Power BI en fichiers CSV
"""

from __future__ import annotations

import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

_SQL_DIR = Path(__file__).resolve().parents[2] / "SQL"
if str(_SQL_DIR) not in sys.path: sys.path.insert(0, str(_SQL_DIR))

from snowflake_utils import (
    LOG_DIR,
    cli_exit,
    get_snowflake_connection,
    setup_logger,
    verify_log_file,
)

LOG_FILE = LOG_DIR / "export_bi_views.log"
EXPORT_DIR = Path(__file__).resolve().parent / "exports"

logger = setup_logger("export_bi_views", "export_bi_views.log")

VIEWS = [
    "V_KPI_AGE_MOYEN_PATHO",
    "V_KPI_MEDIC_PRESCRIT_PATHO",
    "V_KPI_CHAMBRES_PATHO",
    "V_KPI_MEDECINS_PATHO",
    "V_KPI_HOSPI_AU_MOINS_UNE_NUIT",
    "V_KPI_TOUTES_CHAMBRES",
    "V_KPI_CHAMBRES_OCCUPEES",
]


def export_view(cursor, view_name: str, export_dir: Path) -> bool:
    """Exporte une vue SOC en fichier CSV dans export_dir"""
    output_path = export_dir / f"{view_name}.csv"
    try:
        logger.info(f"  Export de {view_name}...")
        cursor.execute(f"SELECT * FROM SOC.PUBLIC.{view_name}")
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(columns)
            writer.writerows(rows)

        logger.info(f"  {view_name} → {output_path.name} ({len(rows)} lignes)")
        return True

    except Exception as e:
        logger.error(f"  Erreur export {view_name} : {e}")
        return False


def main() -> None:
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("DÉMARRAGE EXPORT VUES POWER BI")
    logger.info(f"Date : {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Dossier d'export : {EXPORT_DIR}")

    success = True
    file_handler = logger.file_handler

    try:
        conn = get_snowflake_connection(logger)
        cursor = conn.cursor()

        for view_name in VIEWS:
            ok = export_view(cursor, view_name, EXPORT_DIR)
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
    logger.info(f"FIN EXPORT — {status}")
    logger.info(f"Durée totale : {duration}")
    logger.info("=" * 60)

    file_handler.close()
    logging.shutdown()
    verify_log_file(LOG_FILE, "export_bi_views", handler=file_handler)


if __name__ == "__main__":
    main()
    cli_exit(0)