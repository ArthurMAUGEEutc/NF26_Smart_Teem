import logging
import os
import glob
from datetime import datetime
from snowflake.snowpark import Session

def get_workspace_dir() -> str:
    workspace_root = "/workspace"
    entries = os.listdir(workspace_root)
    for entry in entries:
        full_path = os.path.join(workspace_root, entry)
        if os.path.isdir(full_path):
            return full_path
    raise RuntimeError("Impossible de trouver le dossier workspace")

WORKSPACE_DIR    = get_workspace_dir()
DATA_DIR         = os.path.join(WORKSPACE_DIR, "data")
STAGE_NAME       = "STG.PUBLIC.STG_LOAD"
FILE_FORMAT_NAME = "STG.PUBLIC.FF_CSV_SEMICOLON"

FILE_TABLE_MAPPING = [
    {"prefix": "CHAMBRE",         "table": "STG.PUBLIC.CHAMBRE"},
    {"prefix": "TRAITEMENT",      "table": "STG.PUBLIC.TRAITEMENT"},
    {"prefix": "PERSONNEL",       "table": "STG.PUBLIC.PERSONNEL"},
    {"prefix": "PATIENT",         "table": "STG.PUBLIC.PATIENT"},
    {"prefix": "CONSULTATION",    "table": "STG.PUBLIC.CONSULTATION"},
    {"prefix": "HOSPITALISATION", "table": "STG.PUBLIC.HOSPITALISATION"},
    {"prefix": "MEDICAMENT",      "table": "STG.PUBLIC.MEDICAMENT"},
]


def create_stage_and_format(session):
    session.sql(f"CREATE STAGE IF NOT EXISTS {STAGE_NAME}").collect()
    session.sql(f"""
        CREATE OR REPLACE FILE FORMAT {FILE_FORMAT_NAME}
            TYPE                = 'CSV'
            FIELD_DELIMITER     = ';'
            SKIP_HEADER         = 1
            NULL_IF             = ('', 'NULL', 'null')
            EMPTY_FIELD_AS_NULL = TRUE
            DATE_FORMAT         = 'YYYY-MM-DD'
            TIMESTAMP_FORMAT    = 'YYYY-MM-DD HH24:MI:SS'
    """).collect()


def find_file(prefix: str) -> str | None:
    matches = glob.glob(os.path.join(DATA_DIR, f"{prefix}_*.txt"))
    if not matches:
        return None
    return sorted(matches)[-1]

def upload_and_load(session, prefix: str, table: str) -> bool:
    filepath = find_file(prefix)
    if not filepath:
        print(f"[{prefix}] Fichier introuvable")
        return False

    filename = os.path.basename(filepath)
    print(f"[{prefix}] Fichier trouvé : {filename}")

    try:
        result = session.file.put(
            local_file_name=f"file://{filepath}",
            stage_location=f"@{STAGE_NAME}",
            auto_compress=False,
            overwrite=True,
        )
        print(f"[{prefix}] PUT → {result[0].status}")
    except Exception as e:
        print(f"[{prefix}] Échec PUT : {e}")
        return False

    # COPY INTO spécifique pour PERSONNEL (dates sans heure → TIMESTAMP)
    if prefix == "PERSONNEL":
        copy_sql = f"""
            COPY INTO {table} (
                ID_PERSONNEL, NOM_PERSONNEL, PRENOM_PERSONNEL,
                FONCTION_PERSONNEL, TS_DEBUT_ACTIVITE, TS_FIN_ACTIVITE,
                RAISON_FIN_ACTIVITE, TS_CREATION_PERSONNEL, TS_MAJ_PERSONNEL,
                CD_STATUT_PERSONNEL
            )
            FROM (
                SELECT
                    $1::INTEGER,
                    $2::VARCHAR,
                    $3::VARCHAR,
                    $4::VARCHAR,
                    $5::TIMESTAMP,
                    $6::TIMESTAMP,
                    $7::VARCHAR,
                    TRY_TO_TIMESTAMP($8, 'YYYY-MM-DD'),
                    TRY_TO_TIMESTAMP($9, 'YYYY-MM-DD'),
                    $10::VARCHAR
                FROM @{STAGE_NAME}/{filename}
            )
            FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT_NAME}')
            ON_ERROR    = 'CONTINUE'
            PURGE       = FALSE
        """
    else:
        copy_sql = f"""
            COPY INTO {table}
            FROM @{STAGE_NAME}/{filename}
            FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT_NAME}')
            ON_ERROR    = 'CONTINUE'
            PURGE       = FALSE
        """

    try:
        rows = session.sql(copy_sql).collect()
        for row in rows:
            row_dict = row.as_dict()
            print(f"[{prefix}] {row_dict}")
        return True
    except Exception as e:
        print(f"[{prefix}] Échec COPY INTO : {type(e).__name__} : {e}")
        return False
        
def main(session: Session) -> str:
    if not os.path.exists(DATA_DIR):
        return "ERREUR"

    create_stage_and_format(session)

    overall_success = True
    for mapping in FILE_TABLE_MAPPING:
        ok = upload_and_load(session, mapping["prefix"], mapping["table"])
        if not ok:
            overall_success = False

    status = "SUCCÈS" if overall_success else "TERMINÉ AVEC ERREURS"
    return status


if __name__ == "__main__":
    session = Session.builder.getOrCreate()
    main(session)