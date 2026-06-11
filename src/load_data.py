"""
Chargement quotidien des fichiers plats hospitaliers vers STG (PUT → COPY INTO).
Connexion : profiles.yml — log : logs/pipeline.log.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4


def resolve_sql_dir() -> Path:
    """Localise SQL/ depuis src/load_data.py ou le répertoire courant."""
    try:
        return Path(__file__).resolve().parent.parent / "SQL"
    except NameError:
        pass

    cwd = Path.cwd().resolve()
    for base in [cwd, *cwd.parents]:
        sql_dir = base / "SQL"
        if (sql_dir / "snowflake_utils.py").is_file():
            return sql_dir
        if (base / "src" / "load_data.py").is_file():
            return base / "SQL"

    raise FileNotFoundError(
        "Impossible de localiser SQL/snowflake_utils.py. "
        "Exécutez depuis la racine du projet."
    )


sys.path.insert(0, str(resolve_sql_dir()))

from snowflake_utils import (
    DATA_DIR,
    HISTORY_DIR,
    PIPELINE_LOG,
    SQL_DIR,
    cli_exit,
    execute_sql_file,
    get_snowflake_connection,
    is_snowflake_workspace,
    running_in_notebook,
    setup_logger,
    verify_log_file,
)

logger: logging.Logger | None = None

DEFAULT_LOAD_DATE = "20260429"

SCRPT_NAME = "load_data"
STAGE = "STG.PUBLIC.STG_LOAD_STAGE"
FILE_FORMAT = "STG.PUBLIC.FF_TXT_CSV"

STG_TABLES = [
    "CHAMBRE",
    "CONSULTATION",
    "HOSPITALISATION",
    "MEDICAMENT",
    "PATIENT",
    "PERSONNEL",
    "TRAITEMENT",
]

COPY_SELECT: dict[str, str] = {
    "CHAMBRE": "$1, $2, $3, $4, $5, $6, $7",
    "CONSULTATION": (
        "$1, $2, $3, $4, $5, "
        "$6::INTEGER, $7::INTEGER, $8, $9::INTEGER, "
        "$10, $11, $12, $13"
    ),
    "HOSPITALISATION": "$1, $2, $3, $4, $5, $6::INTEGER, $7",
    "MEDICAMENT": "$1, $2, $3, $4, $5",
    "PATIENT": (
        "$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, "
        "$11, $12, $13, $14, $15, $16, $17"
    ),
    "PERSONNEL": "$1, $2, $3, $4, $5, $6, $7, $8, $9, $10",
    "TRAITEMENT": "$1, $2, $3, $4, $5, $6, $7, $8",
}


def _workspace_data_dir() -> Path:
    """Répertoire data/ dans le Workspace Snowflake (/workspace/<repo>/data)."""
    workspace_root = Path("/workspace")
    if not workspace_root.is_dir():
        raise FileNotFoundError(
            "Workspace Snowflake introuvable (/workspace). "
            "Précisez --data-dir ou STG_DATA_DIR."
        )
    for entry in sorted(workspace_root.iterdir()):
        if entry.is_dir():
            data_path = entry / "data"
            if data_path.is_dir():
                return data_path
    raise FileNotFoundError(
        "Dossier data introuvable sous /workspace. "
        "Précisez --data-dir ou STG_DATA_DIR."
    )


def _default_data_dir() -> Path:
    """STG_DATA_DIR, sinon data/ Workspace ou répertoire local par défaut."""
    env = os.getenv("STG_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    if is_snowflake_workspace():
        return _workspace_data_dir()
    return DATA_DIR.resolve()


def validate_date(date: str) -> str:
    if not re.fullmatch(r"\d{8}", date):
        raise ValueError(f"Date invalide '{date}' — format attendu : YYYYMMDD")
    datetime.strptime(date, "%Y%m%d")
    return date


def data_folder(date: str, data_dir: Path) -> Path:
    return data_dir / f"BDD_HOSPITAL_{date}"


def validate_source_files(date: str, data_dir: Path) -> Path:
    folder = data_folder(date, data_dir)
    if not folder.is_dir():
        raise FileNotFoundError(
            f"Dossier source introuvable : {folder} (parent : {data_dir})"
        )

    missing = [
        f"{table}_{date}.txt"
        for table in STG_TABLES
        if not (folder / f"{table}_{date}.txt").is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Fichiers manquants dans {folder} : {', '.join(missing)}")

    return folder


def suivi_start(cursor, exec_id: str) -> None:
    cursor.execute(
        "INSERT INTO TCH.PUBLIC.T_SUIV_RUN (EXEC_ID, RUN_STRT_DTTM, RUN_STTS_CD) "
        "VALUES (%s, CURRENT_TIMESTAMP, 'ENC')",
        (exec_id,),
    )
    cursor.execute(
        "INSERT INTO TCH.PUBLIC.T_SUIV_TRMT (EXEC_ID, SCRPT_NAME, EXEC_STRT_DTTM, EXEC_STTS_CD) "
        "VALUES (%s, %s, CURRENT_TIMESTAMP, 'ENC')",
        (exec_id, SCRPT_NAME),
    )


def suivi_end(cursor, exec_id: str, status: str) -> None:
    cursor.execute(
        "UPDATE TCH.PUBLIC.T_SUIV_TRMT "
        "SET EXEC_END_DTTM = CURRENT_TIMESTAMP, EXEC_STTS_CD = %s "
        "WHERE EXEC_ID = %s",
        (status, exec_id),
    )
    cursor.execute(
        "UPDATE TCH.PUBLIC.T_SUIV_RUN "
        "SET RUN_END_DTTM = CURRENT_TIMESTAMP, RUN_STTS_CD = %s "
        "WHERE EXEC_ID = %s",
        (status, exec_id),
    )


def stg_has_data(cursor) -> bool:
    for table in STG_TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM STG.PUBLIC.{table}")
        if cursor.fetchone()[0] > 0:
            return True
    return False


def export_table_to_file(cursor, table: str, output_path: Path) -> int:
    cursor.execute(f"SELECT * FROM STG.PUBLIC.{table}")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";", lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow("" if v is None else str(v) for v in row)

    return len(rows)


def snapshot_stg(cursor, snapshot_dir: Path) -> None:
    logger.info(f"Historisation STG → {snapshot_dir}")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for table in STG_TABLES:
        count = export_table_to_file(cursor, table, snapshot_dir / f"{table}.txt")
        logger.info(f"  {table} : {count} lignes exportées")


def purge_history(retention_days: int) -> None:
    if not HISTORY_DIR.exists():
        return

    cutoff = datetime.now() - timedelta(days=retention_days)
    for folder in sorted(HISTORY_DIR.iterdir()):
        if not folder.is_dir():
            continue
        folder_time = datetime.fromtimestamp(folder.stat().st_mtime)
        if folder_time < cutoff:
            shutil.rmtree(folder)
            logger.info(f"Historique purgé : {folder.name} (>{retention_days}j)")


def clear_stage(cursor) -> None:
    cursor.execute(f"REMOVE @{STAGE}")


def _snowflake_put_uri(file_path: Path) -> str:
    """URI file:// pour PUT Snowflake"""
    resolved = file_path.resolve()
    posix = resolved.as_posix()
    if os.name == "nt":
        return f"file:///{posix}"
    return f"file://{posix}"


def put_file(cursor, file_path: Path) -> None:
    uri = _snowflake_put_uri(file_path)
    cursor.execute(
        f"PUT '{uri}' @{STAGE} AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
    )


def copy_into_table(cursor, table: str, filename: str) -> int:
    select_cols = COPY_SELECT[table]
    sql = f"""
        COPY INTO STG.PUBLIC.{table}
        FROM (
            SELECT {select_cols}
            FROM @{STAGE}
        )
        FILES = ('{filename}')
        FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT}')
        ON_ERROR = 'ABORT_STATEMENT'
    """
    cursor.execute(sql)
    rows_loaded = 0
    for row in cursor.fetchall():
        if len(row) >= 4 and row[3] is not None:
            rows_loaded += int(row[3])
    return rows_loaded


def truncate_stg(cursor) -> None:
    for table in STG_TABLES:
        cursor.execute(f"TRUNCATE TABLE STG.PUBLIC.{table}")
        logger.info(f"  TRUNCATE STG.PUBLIC.{table}")


def load_data_day(
    date: str,
    data_dir: Path | str | None = None,
    retention_days: int | None = None,
    skip_history: bool = False,
    log_truncate: bool = False,
    finalize_log_file: bool | None = None,
) -> bool:
    """Charge les fichiers du jour (YYYYMMDD) dans STG. Retourne True si succès."""
    global logger
    date = validate_date(date)
    resolved_data_dir = (
        Path(data_dir).expanduser().resolve() if data_dir else _default_data_dir()
    )
    if retention_days is None:
        retention_days = int(os.getenv("STG_HISTORY_RETENTION_DAYS", "2"))
    if finalize_log_file is None:
        finalize_log_file = log_truncate

    logger = _ensure_file_handler(log_truncate)
    folder = validate_source_files(date, resolved_data_dir)
    exec_id = str(uuid4())
    start = datetime.now()

    print(f"[load_data] Démarrage — date={date}")
    print(f"[load_data] Répertoire données : {resolved_data_dir}")
    print(f"[load_data] Dossier source : {folder}")

    logger.info("=" * 60)
    logger.info(f"DÉMARRAGE CHARGEMENT STG — date={date}")
    logger.info(f"Répertoire données : {resolved_data_dir}")
    logger.info(f"Dossier source : {folder}")
    logger.info(f"EXEC_ID={exec_id}")
    logger.info("=" * 60)

    conn = None
    success = False

    try:
        conn = get_snowflake_connection(logger)
        cursor = conn.cursor()

        execute_sql_file(cursor, SQL_DIR / "create_stg_stage.sql", logger)
        suivi_start(cursor, exec_id)

        if not skip_history and stg_has_data(cursor):
            snapshot_name = f"STG_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            snapshot_stg(cursor, HISTORY_DIR / snapshot_name)
            purge_history(retention_days)

        truncate_stg(cursor)
        clear_stage(cursor)

        for table in STG_TABLES:
            filename = f"{table}_{date}.txt"
            file_path = folder / filename
            logger.info(f"Chargement {table} ← {filename}")
            print(f"[load_data] {table} ← {filename}")
            put_file(cursor, file_path)
            rows = copy_into_table(cursor, table, filename)
            logger.info(f"  {table} : {rows} lignes chargées")
            print(f"[load_data]   → {rows} lignes")
            clear_stage(cursor)

        suivi_end(cursor, exec_id, "OK")
        cursor.close()
        conn.close()
        success = True

    except Exception as e:
        logger.error(f"Erreur chargement STG : {e}")
        print(f"[load_data] ERREUR : {e}")
        if conn is not None:
            try:
                cursor = conn.cursor()
                suivi_end(cursor, exec_id, "KO")
                cursor.close()
                conn.close()
            except Exception as inner:
                logger.error(f"Erreur clôture suivi TCH : {inner}")

    duration = datetime.now() - start
    logger.info("=" * 60)
    status = "SUCCÈS" if success else "ÉCHEC"
    logger.info(f"FIN CHARGEMENT STG — {status} — durée {duration}")
    logger.info("=" * 60)
    print(f"[load_data] FIN — {status} — durée {duration}")
    if finalize_log_file:
        finalize_log()
    return success


def _ensure_file_handler(log_truncate: bool = False) -> logging.Logger:
    """Réouvre le handler fichier après une exécution précédente (notebook)."""
    global logger
    active = logger or logging.getLogger("pipeline")
    fh = getattr(active, "file_handler", None)
    if fh is not None and not getattr(fh, "_closed", False):
        return active

    logger = setup_logger("pipeline", PIPELINE_LOG, truncate=log_truncate)
    return logger


def finalize_log() -> None:
    """Écrit le buffer log sur disque et affiche le résumé."""
    active = logger or logging.getLogger("pipeline")
    file_handler = getattr(active, "file_handler", None)
    if file_handler and not getattr(file_handler, "_closed", False):
        file_handler.close()
    verify_log_file(PIPELINE_LOG, "pipeline", handler=file_handler)


def _resolve_load_date(cli_date: str | None) -> str:
    return cli_date if cli_date else DEFAULT_LOAD_DATE


def _resolve_data_dir(cli_path: str | None) -> Path:
    return Path(cli_path).expanduser().resolve() if cli_path else _default_data_dir()


def _cli_argv() -> list[str]:
    argv = sys.argv[1:]
    if argv and "ipykernel" in argv[0]:
        argv = argv[1:]
    return argv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Charger les fichiers plats d'un jour dans STG (local ou Workspace)"
    )
    parser.add_argument(
        "--date",
        "-d",
        help=f"Jour au format YYYYMMDD (défaut : {DEFAULT_LOAD_DATE})",
    )
    parser.add_argument(
        "--data-dir",
        help="Répertoire parent des dossiers BDD_HOSPITAL_*",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.getenv("STG_HISTORY_RETENTION_DAYS", "2")),
        help="Rétention des snapshots HISTORY/ (défaut : 2)",
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Ne pas historiser STG avant truncate",
    )

    raw = list(argv) if argv is not None else _cli_argv()
    if running_in_notebook():
        args, _unknown = parser.parse_known_args(raw)
    else:
        args = parser.parse_args(raw)
    load_date = _resolve_load_date(args.date)
    load_data_dir = _resolve_data_dir(args.data_dir)

    if not args.date:
        print(f"[load_data] Aucune date fournie — DEFAULT_LOAD_DATE={load_date}")
    if not args.data_dir:
        print(f"[load_data] Aucun --data-dir — défaut={load_data_dir}")

    try:
        ok = load_data_day(
            date=load_date,
            data_dir=load_data_dir,
            retention_days=args.retention_days,
            skip_history=args.skip_history,
            log_truncate=True,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        _ensure_file_handler(log_truncate=True).error(str(e))
        print(f"[load_data] ERREUR : {e}")
        finalize_log()
        return 1

    return 0 if ok else 1


if __name__ == "__main__":
    cli_exit(main())
