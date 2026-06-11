"""
Pipeline quotidien : ingestion STG puis dbt run.
Date métier = ds_nodash ; reprise des échecs antérieurs au run suivant.
"""

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import PythonOperator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_SRC = os.path.join(PROJECT_ROOT, "src")
_SQL = os.path.join(PROJECT_ROOT, "SQL")
for _path in (_SRC, _SQL):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from pipeline_common import (  # noqa: E402
    finalize_pipeline_log,
    get_pipeline_logger,
    resolve_dates_for_run,
    run_dbt_for_dates,
    run_ingestion_for_dates,
    should_truncate_pipeline_log,
    validate_dates,
)


def _pull_dates(ti, current_date: str) -> list[str]:
    dates = ti.xcom_pull(task_ids="resolve_dates")
    return dates if dates else [current_date]


def _task_resolve_dates(**context) -> list[str]:
    current_date = context["ds_nodash"]
    truncate = should_truncate_pipeline_log(**context)
    log = get_pipeline_logger(truncate=truncate)
    dates = resolve_dates_for_run(current_date)
    run_id = getattr(context.get("dag_run"), "run_id", "?")
    log.info("=" * 60)
    if not truncate:
        log.info(f"DAG RUN (backfill) — run_id={run_id}")
    log.info(f"DÉMARRAGE DAG — date métier={current_date}")
    log.info(f"Dates à traiter : {dates}")
    log.info("=" * 60)
    finalize_pipeline_log(log)
    return dates


def _task_validate_date(**context) -> dict[str, bool]:
    ti = context["ti"]
    current_date = context["ds_nodash"]
    dates = _pull_dates(ti, current_date)
    log = get_pipeline_logger(truncate=False)
    results = validate_dates(dates, logger=log)
    if not results.get(current_date, False):
        finalize_pipeline_log(log)
        raise AirflowException(
            f"Validation échouée pour la date métier {current_date}"
        )
    finalize_pipeline_log(log)
    return results


def _task_ingestion_stg(**context) -> dict[str, bool]:
    ti = context["ti"]
    current_date = context["ds_nodash"]
    dates = _pull_dates(ti, current_date)
    validation = ti.xcom_pull(task_ids="validate_date") or {}
    dates_to_load = [d for d in dates if validation.get(d, True)]

    log = get_pipeline_logger(truncate=False)
    results = run_ingestion_for_dates(dates_to_load, logger=log)
    if not results.get(current_date, False):
        failed_retries = [
            d for d, ok in results.items() if not ok and d != current_date
        ]
        detail = f" reprises en échec : {failed_retries}" if failed_retries else ""
        finalize_pipeline_log(log)
        raise AirflowException(
            f"Ingestion STG échouée pour la date métier {current_date}.{detail}"
        )
    finalize_pipeline_log(log)
    return results


def _task_dbt_run(**context) -> None:
    ti = context["ti"]
    current_date = context["ds_nodash"]
    dates = _pull_dates(ti, current_date)
    ingestion_results = ti.xcom_pull(task_ids="ingestion_stg") or {}

    log = get_pipeline_logger(truncate=False)
    results = run_dbt_for_dates(dates, ingestion_results, logger=log)
    if not results.get(current_date, False):
        failed_retries = [
            d for d, ok in results.items() if not ok and d != current_date
        ]
        detail = f" reprises en échec : {failed_retries}" if failed_retries else ""
        finalize_pipeline_log(log)
        raise AirflowException(
            f"dbt run échoué pour la date métier {current_date}.{detail}"
        )
    log.info("=" * 60)
    log.info(f"FIN DAG — date métier={current_date} — SUCCÈS")
    log.info("=" * 60)
    finalize_pipeline_log(log)


default_args = {
    "owner": "data_team",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_run_pipeline",
    description="Ingestion STG + alimentation datawarehouse (dbt)",
    default_args=default_args,
    start_date=datetime(2026, 4, 29),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["hopital", "ingestion", "dbt"],
) as dag:

    resolve_dates = PythonOperator(
        task_id="resolve_dates",
        python_callable=_task_resolve_dates,
    )

    validate_date = PythonOperator(
        task_id="validate_date",
        python_callable=_task_validate_date,
    )

    ingestion_stg = PythonOperator(
        task_id="ingestion_stg",
        python_callable=_task_ingestion_stg,
    )

    dbt_run = PythonOperator(
        task_id="dbt_run",
        python_callable=_task_dbt_run,
    )

    resolve_dates >> validate_date >> ingestion_stg >> dbt_run
