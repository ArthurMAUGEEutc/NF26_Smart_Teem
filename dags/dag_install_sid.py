"""
DAG d'installation du SID : exécute install_sid.py pour créer les bases et tables.
Pas de schedule — à déclencher manuellement depuis l'UI Airflow.
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import PythonOperator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(PROJECT_ROOT, "SQL")


def _task_install_sid(**context) -> None:
    script = os.path.join(SQL_DIR, "install_sid.py")
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
        cwd=SQL_DIR,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        raise AirflowException(
            f"install_sid.py a échoué (code {result.returncode})"
        )


default_args = {
    "owner": "data_team",
    "depends_on_past": False,
    "retries": 0,
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_install_sid",
    description="Installation idempotente du SID (bases + tables Snowflake)",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["hopital", "installation", "sid"],
) as dag:

    install_sid = PythonOperator(
        task_id="install_sid",
        python_callable=_task_install_sid,
    )
