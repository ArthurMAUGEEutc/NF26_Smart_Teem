#!/usr/bin/env bash
# Lance Airflow avec AIRFLOW_HOME = racine du dépôt (Linux / macOS).
set -euo pipefail
cd "$(dirname "$0")"
export AIRFLOW_HOME="$(pwd)"
export AIRFLOW__API__HOST="127.0.0.1"
export AIRFLOW__API__PORT="8080"
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS="true"

echo "UI : http://127.0.0.1:8080"
echo "Logs : ${AIRFLOW_HOME}/logs/"
echo "Diagnostic : ./scripts/check_airflow_ui.sh"
echo ""

exec uv run airflow standalone
