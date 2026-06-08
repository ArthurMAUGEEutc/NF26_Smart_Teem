# Lance Airflow avec AIRFLOW_HOME pointant sur la racine du projet (Windows).
$env:AIRFLOW_HOME = $PSScriptRoot
Set-Location $PSScriptRoot
uv run airflow standalone
