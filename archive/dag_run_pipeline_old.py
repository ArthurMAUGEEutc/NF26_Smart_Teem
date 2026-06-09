"""
DAG : dag_run_pipeline
Ordonnancement quotidien du pipeline hospitalier :
  1. Ingestion STG  → load_data.py
  2. Transformation → dbt run
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

# Dossier racine du projet dbt 
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBT_PROJECT_DIR = os.path.join(PROJECT_ROOT, "dbt_hopital")

# Dossier où se trouve load_data.py
LOAD_DATA_SCRIPT = os.path.join(PROJECT_ROOT, "src", "load_data.py")

# Chemin vers le profiles.yml (chacun a le sien dans son dossier utilisateur ~/.dbt)
DBT_PROFILES_DIR = os.path.expanduser("~/.dbt")

# Chemin du venv qui contient snowflake-connector-python + dbt-snowflake
PYTHON_BIN = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
DBT_BIN    = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "dbt.exe")

# Arguments par défaut
default_args = {
    "owner": "data_team",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

# Définition du DAG
with DAG(
    dag_id="dag_run_pipeline",
    description="Ingestion STG + alimentation datawarehouse (dbt)",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 6 * * *",   # tous les jours à 6h00
    catchup=False,
    tags=["hopital", "ingestion", "dbt"],
) as dag:

    #Ingestion des données dans STG 
    ingestion_stg = BashOperator(
        task_id="ingestion_stg",
        bash_command=f"{PYTHON_BIN} {LOAD_DATA_SCRIPT}",
    )

    # Alimentation WRK + SOC via dbt
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"{DBT_BIN} run "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    # Dépendance temporelle des tâches, ingestion avant transformation
    ingestion_stg >> dbt_run