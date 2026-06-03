"""
install_sid.py — Script d'installation du SID (Système d'Information Décisionnel)
- Idempotent : peut être exécuté plusieurs fois sans erreur
- Trace toutes les opérations dans logs/installation.log
- Les bases de données ne sont pas recréées si elles existent déjà
- Les tables STG sont recréées (CREATE OR REPLACE)
- Les tables SOC et TCH ne sont pas recréées si elles existent déjà

Exécution Workspace : python SQL/install_sid.py  ou  %run SQL/install_sid.py
"""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import snowflake.connector


class WorkspaceFileHandler(logging.Handler):
    """Buffer mémoire + écriture unique à la fermeture — FS Workspace Snowflake."""

    def __init__(self, log_path: Path):
        super().__init__(level=logging.NOTSET)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._buffer: list[str] = []
        self.write_failed = False
        self.lines_written = 0
        self._closed = False

    def emit(self, record: logging.LogRecord) -> None:
        if self._closed:
            return
        self._buffer.append(self.format(record) + "\n")
        self.lines_written += 1

    def flush(self) -> None:
        pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if not self._buffer:
            return
        try:
            fd = os.open(
                self.log_path,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                mode=0o644,
            )
            try:
                os.write(fd, "".join(self._buffer).encode("utf-8"))
            finally:
                os.close(fd)
        except OSError:
            self.write_failed = True
            print(
                f"[install_sid] Écriture log impossible : {self.log_path}",
                file=sys.stderr,
            )
        self._buffer.clear()


def silence_external_loggers() -> None:
    """Nettoie le logger racine et réduit le bruit du connecteur Snowflake."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            root.removeHandler(handler) 
    for name in ("snowflake.connector", "snowflake", "Snowflake.connector"):
        logging.getLogger(name).setLevel(logging.WARNING)


def verify_log_file(log_path: Path, handler: WorkspaceFileHandler) -> None:
    """Vérifie que le fichier log contient bien toute l'exécution."""
    size = log_path.stat().st_size if log_path.is_file() else 0
    incomplete = handler.write_failed or handler.lines_written < 3
    if size >= 200 and not incomplete:
        print(f"[install_sid] Log fichier OK : {log_path} ({size} octets)")
    elif size > 0 and incomplete:
        print(
            f"[install_sid] Log fichier incomplet : {log_path} ({size} octets). "
            "Consultez la sortie stdout."
        )
    else:
        print(
            f"[install_sid] ATTENTION : pas de log sur disque à {log_path}. "
            "Consultez la sortie stdout."
        )


def resolve_paths() -> tuple[Path, Path]:
    """Retourne (PROJECT_ROOT, SQL_DIR)."""
    try:
        sql_dir = Path(__file__).resolve().parent
        return sql_dir.parent, sql_dir
    except NameError:
        pass

    cwd = Path.cwd().resolve()
    for base in [cwd, *cwd.parents]:
        if (base / "create_db.sql").is_file():
            return base.parent, base
        sql_candidate = base / "SQL"
        if (sql_candidate / "create_db.sql").is_file():
            return base, sql_candidate

    raise FileNotFoundError(
        "Impossible de localiser SQL/create_db.sql. "
        "Exécutez depuis le dossier SQL/ ou la racine du projet."
    )


# ──────────────────────────────────────────────
# Configuration du logging
# ──────────────────────────────────────────────
PROJECT_ROOT, SQL_DIR = resolve_paths()
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "installation.log"

_LOG_FORMAT = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

logger = logging.getLogger("install_sid")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.handlers.clear()

file_handler = WorkspaceFileHandler(LOG_FILE)
file_handler.setFormatter(_LOG_FORMAT)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(_LOG_FORMAT)
logger.addHandler(stream_handler)

silence_external_loggers()

# ──────────────────────────────────────────────
# Ordre d'exécution des scripts SQL
# ──────────────────────────────────────────────
SQL_SCRIPTS = [
    "create_db.sql",
    "create_stg.sql",
    "create_soc.sql",
    "create_tch.sql",
]


def get_snowflake_connection():
    """Connexion Snowflake via le token OAuth du workspace Snowsight."""
    silence_external_loggers()
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
    return [s.strip() for s in sql_text.split(";") if s.strip()]


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

    overall_success = True

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        for script_name in SQL_SCRIPTS:
            script_path = SQL_DIR / script_name
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

    file_handler.close()
    logging.shutdown()
    verify_log_file(LOG_FILE, file_handler)


if __name__ == "__main__":
    main()
