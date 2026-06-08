"""
DAG : dag_run_pipeline
Ordonnancement quotidien du pipeline hospitalier (traitement séquentiel jour par jour) :
  run_daily_pipeline.py → curseur date + load_data + dbt run
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

START_DATE = datetime(2026, 4, 29)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_PIPELINE_SCRIPT = os.path.join(PROJECT_ROOT, "src", "run_daily_pipeline.py")


def _run_pipeline() -> None:
    rc = subprocess.run(
        [sys.executable, RUN_PIPELINE_SCRIPT],
        check=False,
    ).returncode
    if rc != 0:
        raise RuntimeError(f"run_daily_pipeline exited with {rc}")

default_args = {
    "owner": "data_team",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_run_pipeline",
    description="Pipeline séquentiel : ingestion STG + dbt (curseur date +1/jour)",
    default_args=default_args,
    start_date=START_DATE,
    schedule="0 6 * * *",
    catchup=False,
    tags=["hopital", "ingestion", "dbt"],
) as dag:

    run_pipeline = PythonOperator(
        task_id="run_pipeline",
        python_callable=_run_pipeline,
    )
