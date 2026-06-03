import logging
import os
import re
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

import snowflake.connector

# ──────────────────────────────────────────────
# Configuration du logging (en mémoire, écriture dans un fichier à la toute fin
# ──────────────────────────────────────────────
# Accumuler les logs dans un flux mémoire
log_buffer = StringIO()
handler = logging.StreamHandler(log_buffer)
handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)

logger = logging.getLogger()

# Nettoyage des handlers du Notebook
if logger.hasHandlers():
    logger.handlers.clear()

logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Optionnel : logging console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

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
    sql_text = re.sub(r"--[^\n]*", "", sql_text)
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    return statements


def execute_script(cursor, script_path: Path) -> bool:
    """Exécute tous les statements d'un fichier SQL."""
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

    # ──────────────────────────────────────────────
    # ÉCRITURE FINALE DU FICHIER (contourner le bug snowflake)
    # ──────────────────────────────────────────────
    logging.shutdown()
    
    # On récupère tout ce qui a été loggé en mémoire
    final_logs = log_buffer.getvalue()
    
    # On l'écrit d'un seul coup 
    log_file_path = base_dir / "installation.log"
    log_file_path.write_text(final_logs, encoding="utf-8")
    
    print(f"\n[OK] Fichier de log créé avec succès dans le workspace : {log_file_path}")
    # Toujours terminer sans erreur (code 0)
    sys.exit(0)


if __name__ == "__main__":
    main()