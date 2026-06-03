"""
install_sid.py — Script d'installation du SID (Système d'Information Décisionnel)
- Idempotent : peut être exécuté plusieurs fois sans erreur
- Trace toutes les opérations dans installation.log
- Les bases de données ne sont pas recréées si elles existent déjà
- Les tables STG sont recréées (CREATE OR REPLACE)
- Les tables SOC et TCH ne sont pas recréées si elles existent déjà
"""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import snowflake.connector

# ──────────────────────────────────────────────
# Configuration du logging
# ──────────────────────────────────────────────
LOG_FILE = Path("installation.log")

handler = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

print("LOG PATH =", LOG_FILE)
logger.info("TEST LOG")

# ──────────────────────────────────────────────
# Ordre d'exécution des scripts SQL
# ──────────────────────────────────────────────
SQL_SCRIPTS = [
    "create_db.sql",   # Création des bases (IF NOT EXISTS)
    "create_stg.sql",  # Tables STG (CREATE OR REPLACE)
    "create_soc.sql",  # Tables SOC (IF NOT EXISTS)
    "create_tch.sql",  # Tables TCH (IF NOT EXISTS)
]


def get_snowflake_connection():
    """Connexion Snowflake via le token OAuth du workspace Snowsight."""
    token_path = os.getenv("SNOWFLAKE_TOKEN_FILE_PATH", "/snowflake/session/token")
    try:
        with open(token_path) as f:
            token = f.read().strip()
    except FileNotFoundError:
        logger.error(f"Token introuvable : {token_path}")
        raise

    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
        host=os.getenv("SNOWFLAKE_HOST", ""),
        authenticator="oauth",
        token=token,
        warehouse="COMPUTE_WH",
        role="ACCOUNTADMIN",
    )
    logger.info("Connexion Snowflake établie.")
    return conn


def parse_statements(sql_text: str) -> list[str]:
    """Découpe le fichier SQL en statements individuels (ignore les commentaires)."""
    # Supprimer les commentaires de ligne
    sql_text = re.sub(r"--[^\n]*", "", sql_text)
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    return statements


def execute_script(cursor, script_path: Path) -> bool:
    """
    Exécute tous les statements d'un fichier SQL.
    Retourne True si tout s'est bien passé, False sinon.
    """
    logger.info(f"──── Début exécution : {script_path.name} ────")

    try:
        sql_text = script_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error(f"Fichier introuvable : {script_path}")
        return False

    statements = parse_statements(sql_text)
    success = True

    for i, stmt in enumerate(statements, start=1):
        try:
            cursor.execute(stmt)
            logger.info(f"  [{script_path.name}] Statement {i}/{len(statements)} OK")
        except Exception as e:
            logger.error(f"  [{script_path.name}] Statement {i}/{len(statements)} ERREUR : {e}")
            logger.error(f"  Statement : {stmt[:120]}...")
            success = False

    status = "SUCCÈS" if success else "PARTIEL (voir erreurs ci-dessus)"
    logger.info(f"──── Fin exécution : {script_path.name} — {status} ────")
    return success


def main():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("DÉMARRAGE INSTALLATION SID")
    logger.info(f"Date : {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    base_dir = Path.cwd()
    overall_success = True

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        for script_name in SQL_SCRIPTS:
            script_path = base_dir / script_name
            ok = execute_script(cursor, script_path)
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

    logging.shutdown()
    # Toujours terminer sans erreur (code 0)
    sys.exit(0)


if __name__ == "__main__":
    main()
