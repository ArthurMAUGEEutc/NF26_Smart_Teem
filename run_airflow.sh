#!/usr/bin/env bash
# Lance Airflow avec AIRFLOW_HOME = racine du dépôt (Linux / macOS).
set -euo pipefail
cd "$(dirname "$0")"
export AIRFLOW_HOME="$(pwd)"
exec uv run airflow standalone
