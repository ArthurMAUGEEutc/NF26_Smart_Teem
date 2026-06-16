"""
Pipeline manuel : ingestion STG puis dbt run.
Aucune exécution automatique (schedule=None).
Déclencher depuis l'UI avec les paramètres date_debut / date_fin.
"""

import os
import re
import sys
from datetime import date, datetime, timedelta

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import Param

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


def _to_yyyymmdd(value: date | str | None) -> str:
    """Convertit une date UI (YYYY-MM-DD, date ou YYYYMMDD) en YYYYMMDD."""
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    text = str(value).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d{8}", text):
        return text
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text.replace("-", "")
    raise AirflowException(f"Date invalide : {value!r} (attendu YYYY-MM-DD)")


def _run_period(context) -> tuple[str, str, str]:
    """Retourne (date_debut, date_fin, date_principale) depuis les params du trigger."""
    params = context.get("params") or {}
    debut = _to_yyyymmdd(params.get("date_debut"))
    fin = _to_yyyymmdd(params.get("date_fin"))
    if not debut:
        raise AirflowException("Paramètre date_debut obligatoire")
    if not fin:
        fin = debut
    return debut, fin, fin


def _pull_dates(ti, debut: str, fin: str) -> list[str]:
    dates = ti.xcom_pull(task_ids="resolve_dates")
    if dates:
        return dates
    return resolve_dates_for_run(fin, date_debut=debut, date_fin=fin)


def _task_resolve_dates(**context) -> list[str]:
    debut, fin, anchor = _run_period(context)
    truncate = should_truncate_pipeline_log(**context)
    log = get_pipeline_logger(truncate=truncate)
    dates = resolve_dates_for_run(anchor, date_debut=debut, date_fin=fin)
    run_id = getattr(context.get("dag_run"), "run_id", "?")
    log.info("=" * 60)
    log.info(f"DÉMARRAGE DAG — run_id={run_id}")
    log.info(f"Période demandée : {debut} → {fin} (date principale={anchor})")
    log.info(f"Dates à traiter : {dates}")
    log.info("=" * 60)
    finalize_pipeline_log(log)
    return dates


def _task_validate_date(**context) -> dict[str, bool]:
    ti = context["ti"]
    debut, fin, anchor = _run_period(context)
    dates = _pull_dates(ti, debut, fin)
    log = get_pipeline_logger(truncate=False)
    results = validate_dates(dates, logger=log)
    if not results.get(anchor, False):
        finalize_pipeline_log(log)
        raise AirflowException(
            f"Validation échouée pour la date principale {anchor}"
        )
    finalize_pipeline_log(log)
    return results


def _task_ingestion_stg(**context) -> dict[str, bool]:
    ti = context["ti"]
    debut, fin, anchor = _run_period(context)
    dates = _pull_dates(ti, debut, fin)
    validation = ti.xcom_pull(task_ids="validate_date") or {}
    dates_to_load = [d for d in dates if validation.get(d, True)]

    log = get_pipeline_logger(truncate=False)
    results = run_ingestion_for_dates(dates_to_load, logger=log)
    if not results.get(anchor, False):
        failed_retries = [
            d for d, ok in results.items() if not ok and d != anchor
        ]
        detail = f" reprises en échec : {failed_retries}" if failed_retries else ""
        finalize_pipeline_log(log)
        raise AirflowException(
            f"Ingestion STG échouée pour la date principale {anchor}.{detail}"
        )
    finalize_pipeline_log(log)
    return results


def _task_dbt_run(**context) -> None:
    ti = context["ti"]
    debut, fin, anchor = _run_period(context)
    dates = _pull_dates(ti, debut, fin)
    ingestion_results = ti.xcom_pull(task_ids="ingestion_stg") or {}

    log = get_pipeline_logger(truncate=False)
    results = run_dbt_for_dates(dates, ingestion_results, logger=log)
    if not results.get(anchor, False):
        failed_retries = [
            d for d, ok in results.items() if not ok and d != anchor
        ]
        detail = f" reprises en échec : {failed_retries}" if failed_retries else ""
        finalize_pipeline_log(log)
        raise AirflowException(
            f"dbt run échoué pour la date principale {anchor}.{detail}"
        )
    log.info("=" * 60)
    log.info(f"FIN DAG — période {debut} → {fin} — SUCCÈS")
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
    description="Ingestion STG + alimentation datawarehouse (dbt) — déclenchement manuel",
    default_args=default_args,
    start_date=datetime(2026, 4, 29),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    params={
        "date_debut": Param(
            type="string",
            format="date",
            description="Date de début",
        ),
        "date_fin": Param(
            type=["string", "null"],
            format="date",
            default=None,
            description="Date de fin (vide = même jour que le début)",
        ),
    },
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
