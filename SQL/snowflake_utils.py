"""Connexion Snowflake, logging et exécution SQL pour les scripts Python du SID."""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

import snowflake.connector
import yaml

SQL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SQL_DIR.parent
DBT_PROFILE_NAME = "dbt_hopital"
PROFILES_PATH = PROJECT_ROOT / "dbt_hopital" / "profiles.yml"
PROFILES_EXAMPLE_PATH = PROJECT_ROOT / "dbt_hopital" / "profiles.yml.example"

CONNECT_KEYS = frozenset(
    {
        "account",
        "user",
        "password",
        "authenticator",
        "warehouse",
        "role",
        "host",
    }
)
LOG_DIR = PROJECT_ROOT / "logs"
INSTALL_LOG = "installation.log"
PIPELINE_LOG = "pipeline.log"
# Répertoire données locales (surcharge possible via STG_DATA_DIR)
DATA_DIR = PROJECT_ROOT / "Inputs_Projets_NF26_AI07" / "Data Hospital"
HISTORY_DIR = PROJECT_ROOT / "HISTORY"

LOG_FORMAT = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")


def resolve_project_paths() -> tuple[Path, Path]:
    """Retourne (PROJECT_ROOT, SQL_DIR)."""
    return PROJECT_ROOT, SQL_DIR


def is_snowflake_workspace() -> bool:
    """True si le script tourne dans un Workspace / notebook Snowflake (token OAuth)."""
    token_path = os.getenv("SNOWFLAKE_TOKEN_FILE_PATH", "/snowflake/session/token")
    return Path(token_path).is_file()


def running_in_notebook() -> bool:
    """True si le script tourne dans IPython / Notebook Snowflake (%run, cellule Python)."""
    try:
        get_ipython()  # type: ignore[name-defined]
        return True
    except NameError:
        return False


def cli_exit(code: int = 0) -> None:
    """sys.exit en terminal ; no-op en notebook (%run, cellule Python)."""
    if running_in_notebook():
        return
    sys.exit(code)


class WorkspaceFileHandler(logging.Handler):
    """Buffer mémoire ; écriture unique à la fermeture (compatibilité Workspace Snowflake)."""

    def __init__(self, log_path: Path, truncate: bool = False):
        super().__init__(level=logging.NOTSET)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.truncate = truncate
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
            flags = os.O_WRONLY | os.O_CREAT
            flags |= os.O_TRUNC if self.truncate else os.O_APPEND
            fd = os.open(self.log_path, flags, mode=0o644)
            try:
                os.write(fd, "".join(self._buffer).encode("utf-8"))
            finally:
                os.close(fd)
        except OSError:
            self.write_failed = True
            print(
                f"[log] Écriture impossible : {self.log_path} — "
                "historique uniquement sur stdout.",
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


def verify_log_file(
    log_path: Path | str,
    script_name: str = "script",
    handler: WorkspaceFileHandler | None = None,
) -> None:
    """Vérifie que le fichier log contient bien toute l'exécution."""
    path = Path(log_path)
    if not path.is_absolute():
        path = LOG_DIR / path

    prefix = f"[{script_name}]"
    if is_snowflake_workspace():
        return

    size = path.stat().st_size if path.is_file() else 0
    incomplete = handler is not None and (
        handler.write_failed or handler.lines_written < 3
    )
    if size >= 200 and not incomplete:
        print(f"{prefix} Log fichier OK : {path} ({size} octets)")
    elif size > 0 and incomplete:
        print(
            f"{prefix} Log fichier incomplet : {path} ({size} octets). "
            "Consultez la sortie stdout."
        )
    elif size > 0:
        print(f"{prefix} Log fichier OK : {path} ({size} octets)")
    else:
        print(
            f"{prefix} ATTENTION : pas de log sur disque à {path}. "
            "Consultez la sortie stdout."
        )


def setup_logger(
    name: str,
    log_filename: str,
    *,
    truncate: bool = False,
) -> logging.Logger:
    """Configure un logger avec fichier bufferisé + stdout."""
    silence_external_loggers()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    log.propagate = False
    log.handlers.clear()

    file_handler = WorkspaceFileHandler(LOG_DIR / log_filename, truncate=truncate)
    file_handler.setFormatter(LOG_FORMAT)
    log.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(LOG_FORMAT)
    log.addHandler(stream_handler)

    log.file_handler = file_handler  # type: ignore[attr-defined]
    return log


def _profiles_setup_hint() -> str:
    return (
        f"Copiez {PROFILES_EXAMPLE_PATH} vers {PROFILES_PATH} "
        "et renseignez account / user (cible local) et account (cible workspace)."
    )


def resolve_target() -> str:
    """Cible dbt : workspace si token OAuth présent, sinon local (sauf DBT_TARGET)."""
    override = os.getenv("DBT_TARGET", "").strip()
    if override:
        return override
    return "workspace" if is_snowflake_workspace() else "local"


def load_dbt_profile(target: str | None = None) -> dict:
    """Charge la sortie active depuis dbt_hopital/profiles.yml."""
    resolved_target = target or resolve_target()
    if not PROFILES_PATH.is_file():
        raise FileNotFoundError(
            f"Fichier introuvable : {PROFILES_PATH}. {_profiles_setup_hint()}"
        )

    with PROFILES_PATH.open(encoding="utf-8") as f:
        profiles = yaml.safe_load(f) or {}

    profile_block = profiles.get(DBT_PROFILE_NAME)
    if not isinstance(profile_block, dict):
        raise ValueError(
            f"Profil '{DBT_PROFILE_NAME}' manquant dans {PROFILES_PATH}. "
            f"{_profiles_setup_hint()}"
        )

    outputs = profile_block.get("outputs", {})
    if resolved_target not in outputs:
        raise ValueError(
            f"Cible '{resolved_target}' absente dans {PROFILES_PATH}. "
            f"Cibles disponibles : {', '.join(outputs) or '(aucune)'}"
        )

    output = outputs[resolved_target]
    if not isinstance(output, dict):
        raise ValueError(f"Cible '{resolved_target}' invalide dans {PROFILES_PATH}")

    return output


def _validate_profile_values(output: dict, target: str) -> None:
    placeholders = {"VOTRE_ACCOUNT", "VOTRE_USER", ""}
    account = str(output.get("account", "")).strip()
    if account in placeholders:
        raise ValueError(
            f"account non configuré pour la cible '{target}' dans {PROFILES_PATH}. "
            f"{_profiles_setup_hint()}"
        )
    if target == "local":
        user = str(output.get("user", "")).strip()
        if user in placeholders:
            raise ValueError(
                f"user non configuré pour la cible 'local' dans {PROFILES_PATH}. "
                f"{_profiles_setup_hint()}"
            )


def _connect_kwargs_from_profile(output: dict) -> dict:
    kwargs: dict = {}
    for key in CONNECT_KEYS:
        if key not in output:
            continue
        value = output[key]
        if value is None or value == "":
            continue
        if isinstance(value, str) and "{{" in value:
            continue
        kwargs[key] = value
    return kwargs


def _connect_oauth(log: logging.Logger, profile: dict):
    """Workspace Snowflake : token OAuth de session + paramètres du profil workspace."""
    token_path = os.getenv("SNOWFLAKE_TOKEN_FILE_PATH", "/snowflake/session/token")
    try:
        with open(token_path) as f:
            token = f.read().strip()
    except FileNotFoundError:
        log.error(f"Token introuvable : {token_path}")
        raise

    kwargs = _connect_kwargs_from_profile(profile)
    kwargs["authenticator"] = "oauth"
    kwargs["token"] = token

    conn = snowflake.connector.connect(**kwargs)
    log.info("Connexion Snowflake établie (Workspace OAuth).")
    return conn


def _connect_local(log: logging.Logger, profile: dict):
    """PC local : paramètres de la cible local dans profiles.yml."""
    kwargs = _connect_kwargs_from_profile(profile)
    if "user" not in kwargs:
        raise ValueError(
            f"user manquant pour la cible 'local' dans {PROFILES_PATH}. "
            f"{_profiles_setup_hint()}"
        )

    conn = snowflake.connector.connect(**kwargs)
    log.info(
        f"Connexion Snowflake établie (local, {kwargs.get('authenticator')}, "
        f"user={kwargs.get('user')})."
    )
    return conn


def get_snowflake_connection(logger: logging.Logger | None = None):
    """Connexion via dbt_hopital/profiles.yml (cible local ou workspace)."""
    silence_external_loggers()
    log = logger or logging.getLogger(__name__)
    target = resolve_target()
    profile = load_dbt_profile(target=target)
    _validate_profile_values(profile, target)

    if target == "workspace":
        return _connect_oauth(log, profile)
    return _connect_local(log, profile)


def parse_statements(sql_text: str) -> list[str]:
    """Découpe un script SQL en statements (ignore --, respecte les ; dans les chaînes)."""
    sql_text = re.sub(r"--[^\n]*", "", sql_text)

    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    in_double_quote = False
    i = 0

    while i < len(sql_text):
        ch = sql_text[i]

        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(ch)
        elif ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(ch)
        elif ch == ";" and not in_single_quote and not in_double_quote:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(ch)

        i += 1

    last = "".join(current).strip()
    if last:
        statements.append(last)

    return statements


def execute_sql_file(
    cursor,
    script_path: Path,
    logger: logging.Logger | None = None,
) -> bool:
    """Exécute tous les statements d'un fichier SQL."""
    log = logger or logging.getLogger(__name__)
    log.info(f"──── Début exécution : {script_path.name} ────")

    try:
        sql_text = script_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.error(f"Fichier introuvable : {script_path}")
        return False

    statements = parse_statements(sql_text)
    success = True

    for i, stmt in enumerate(statements, start=1):
        try:
            cursor.execute(stmt)
            log.info(f"  [{script_path.name}] Statement {i}/{len(statements)} OK")
        except Exception as e:
            log.error(
                f"  [{script_path.name}] Statement {i}/{len(statements)} ERREUR : {e}"
            )
            log.error(f"  Statement : {stmt[:120]}...")
            success = False

    status = "SUCCÈS" if success else "PARTIEL (voir erreurs ci-dessus)"
    log.info(f"──── Fin exécution : {script_path.name} — {status} ────")
    return success
