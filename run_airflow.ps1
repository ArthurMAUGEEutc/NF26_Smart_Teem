# Lance Airflow avec AIRFLOW_HOME pointant sur la racine du projet,
# quel que soit l'emplacement où le projet est cloné.
$env:AIRFLOW_HOME = $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\airflow.exe" standalone
