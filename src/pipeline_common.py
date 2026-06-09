"""
Utilitaires techniques partagés (ingestion, dbt, binaires).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def setup_paths() -> tuple[Path, Path]:
    root = project_root()
    sql_dir = root / "SQL"
    src_dir = root / "src"
    if str(sql_dir) not in sys.path:
        sys.path.insert(0, str(sql_dir))
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return root, sql_dir


def resolve_python_bin(root: Path | None = None) -> str:
    if sys.executable:
        return sys.executable
    root = root or project_root()
    for candidate in (
        root / ".venv" / "bin" / "python",
        root / ".venv" / "Scripts" / "python.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return "python"


def resolve_dbt_bin(root: Path | None = None) -> str:
    found = shutil.which("dbt")
    if found:
        return found
    root = root or project_root()
    for candidate in (
        root / ".venv" / "bin" / "dbt",
        root / ".venv" / "Scripts" / "dbt.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return "dbt"


def validate_date_for_load(date: str) -> str:
    """Valide la date et la présence des fichiers sources pour un jour donné."""
    from load_data import _default_data_dir, validate_date, validate_source_files

    validated = validate_date(date)
    validate_source_files(validated, _default_data_dir())
    return validated


def run_ingestion(date: str) -> bool:
    from load_data import _default_data_dir, load_data_day

    return load_data_day(date, data_dir=_default_data_dir())


def run_dbt(root: Path | None = None) -> int:
    root = root or project_root()
    dbt_project = root / "dbt_hopital"
    dbt_bin = resolve_dbt_bin(root)
    result = subprocess.run(
        [
            dbt_bin,
            "run",
            "--project-dir",
            str(dbt_project),
            "--profiles-dir",
            str(dbt_project),
        ],
        cwd=root,
        check=False,
    )
    return result.returncode
