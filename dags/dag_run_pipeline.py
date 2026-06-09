"""
DAG : dag_run_pipeline
Pipeline hospitalier (sans planification automatique) :
  1. Ingestion STG  → load_data.py
  2. Transformation → dbt run

Déclenchement : exécution manuelle ou rattrapage (backfill) uniquement.
Date métier : ds_nodash (data_interval_start) fourni par Airflow.
Période multi-jours : mode Rattrapage (backfill) = un DagRun par jour.
"""

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBT_PROJECT_DIR = os.path.join(PROJECT_ROOT, "dbt_hopital")
LOAD_DATA_SCRIPT = os.path.join(PROJECT_ROOT, "src", "load_data.py")

_SRC = os.path.join(PROJECT_ROOT, "src")
_SQL = os.path.join(PROJECT_ROOT, "SQL")
for _path in (_SRC, _SQL):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from pipeline_common import (  # noqa: E402
    resolve_dbt_bin,
    resolve_python_bin,
    validate_date_for_load,
)

PYTHON_BIN = resolve_python_bin()
DBT_BIN = resolve_dbt_bin()


def _task_validate_date(**context) -> str:
    return validate_date_for_load(context["ds_nodash"])


default_args = {
    "owner": "data_team",
    "depends_on_past": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_run_pipeline",
    description="Ingestion STG + alimentation datawarehouse (dbt)",
    default_args=default_args,
    start_date=datetime(2026, 4, 29),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["hopital", "ingestion", "dbt"],
) as dag:

    validate_date = PythonOperator(
        task_id="validate_date",
        python_callable=_task_validate_date,
    )

    ingestion_stg = BashOperator(
        task_id="ingestion_stg",
        bash_command=(
            f'"{PYTHON_BIN}" "{LOAD_DATA_SCRIPT}" '
            '--date "{{ ti.xcom_pull(task_ids=\'validate_date\') }}"'
        ),
        cwd=PROJECT_ROOT,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f'"{DBT_BIN}" run '
            f'--project-dir "{DBT_PROJECT_DIR}" '
            f'--profiles-dir "{DBT_PROJECT_DIR}"'
        ),
        cwd=PROJECT_ROOT,
    )

    validate_date >> ingestion_stg >> dbt_run
