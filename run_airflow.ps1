# Lance Airflow avec AIRFLOW_HOME pointant sur la racine du projet (Windows).
$env:AIRFLOW_HOME = $PSScriptRoot
$env:AIRFLOW__API__HOST = "127.0.0.1"
$env:AIRFLOW__API__PORT = "8080"
$env:AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS = "true"
Set-Location $PSScriptRoot

Write-Host "UI : http://127.0.0.1:8080"
Write-Host "Mot de passe admin (si besoin) : $env:AIRFLOW_HOME\standalone_admin_password.txt"
Write-Host "Logs : $env:AIRFLOW_HOME\logs\"
Write-Host "Diagnostic : .\scripts\check_airflow_ui.ps1"
Write-Host ""

uv run airflow standalone
