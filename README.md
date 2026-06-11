# NF26 Smart Teem — SID hospitalier

Système d'information décisionnel : ingestion STG → transformations dbt (WRK/SOC) → Power BI.  
Stack : Snowflake, dbt Core, Apache Airflow, Python (`uv`).

**Plateformes supportées :** Linux, macOS, Windows (PowerShell).

Toutes les commandes ci-dessous s'exécutent **depuis la racine du dépôt**, sauf indication contraire.

---

## Prérequis

- [uv](https://docs.astral.sh/uv/) installé
- Accès Snowflake (compte projet, rôle `ACCOUNTADMIN`)
- Données sources dans `Inputs_Projets_NF26_AI07/Data Hospital/` (ou chemin personnalisé via `STG_DATA_DIR`)

---

## 1. Installation de l'environnement

```bash
uv sync
```

Vérifier dbt :

```bash
uv run dbt --version
```

---

## 2. Profil Snowflake (`dbt_hopital/profiles.yml`)

Copier le template (ne jamais committer `profiles.yml`) :

**Linux / macOS**

```bash
cp dbt_hopital/profiles.yml.example dbt_hopital/profiles.yml
```

**Windows (PowerShell)**

```powershell
Copy-Item dbt_hopital/profiles.yml.example dbt_hopital/profiles.yml
```

Éditer `dbt_hopital/profiles.yml` : renseigner `account`, `user`, `password` sous `outputs.local`.

Dans le **Workspace Snowflake**, la cible `workspace` (OAuth) est sélectionnée automatiquement si le token est présent.

---

## 3. Installation du SID (bases + tables)

Script idempotent (log : `logs/installation.log`) :

```bash
uv run python SQL/install_sid.py
```

---

## 4. Chargement STG (un jour)

```bash
uv run python src/load_data.py --date 20260429
```

Arguments utiles :

- `--retention-days N` — rétention historique STG (défaut 2)
- `--skip-history` — désactive le snapshot avant truncate
- `--data-dir CHEMIN` — dossier parent contenant `BDD_HOSPITAL_YYYYMMDD/`

Log : `logs/pipeline.log` (tronqué au trigger manuel d'un jour ; append entre DagRuns d'un backfill)

---

## 5. Transformations dbt

Tester la connexion :

```bash
uv run dbt debug --project-dir dbt_hopital --profiles-dir dbt_hopital
```

Lancer les modèles :

```bash
uv run dbt run --project-dir dbt_hopital --profiles-dir dbt_hopital
```

Via le pipeline (`run_daily_pipeline` ou DAG), la sortie dbt est intégrée dans `logs/pipeline.log`. En CLI directe, dbt écrit sous `dbt_hopital/target/dbt_logs/`.

Guide détaillé dbt : [tuto_dbt.md](tuto_dbt.md)

---

## 6. Pipeline journalier local (indépendant du DAG)

[`src/run_daily_pipeline.py`](src/run_daily_pipeline.py) exécute **un jour** du pipeline sans Airflow. La date est fixée dans le code (`LOCAL_RUN_DATE`, défaut `20260429`) — indépendante du DAG et d'Airflow.

```bash
uv run python src/run_daily_pipeline.py
```

Étapes :

1. Valide `LOCAL_RUN_DATE` et la présence des 7 fichiers `.txt` du jour
2. Si fichiers absents → échec
3. Sinon → load STG → `dbt run`

Log : `logs/pipeline.log`

Pour traiter un autre jour : modifier `LOCAL_RUN_DATE` dans `src/run_daily_pipeline.py`.

---

## 7. Airflow (orchestration)

Le DAG [`dags/dag_run_pipeline.py`](dags/dag_run_pipeline.py) utilise `schedule=@daily` avec `catchup=False` : pas de rattrapage automatique au démarrage. En pratique, le laisser **en pause** et le déclencher par **exécution manuelle** ou **backfill**. Tâches visibles dans l'UI :

`resolve_dates` → `validate_date` → `ingestion_stg` → `dbt_run`

- **Date métier** : `ds_nodash` (logical date du DagRun, ex. `20260429`) — toujours la renseigner au trigger
- **Par date** : validation fichiers → `load_data.py` → `dbt run`
- **Période multi-jours** : backfill = un DagRun par jour, séquentiel (`max_active_runs=1`)
- **Reprise sur erreur** : si le jour J échoue, le jour J+1 est quand même lancé ; au run J+1, les dates en échec antérieures sont retraitées avant J+1 (registre : `logs/pipeline_failed_dates.txt`)
- **Log applicatif** : `logs/pipeline.log` (tronqué au trigger manuel d'un jour ; chaque DagRun de backfill s'ajoute avec un séparateur ; supprimer le fichier avant un nouveau backfill pour repartir à zéro)

Le DAG n'appelle pas `run_daily_pipeline.py`.

### Démarrer Airflow

**Linux / macOS**

```bash
chmod +x run_airflow.sh scripts/check_airflow_ui.sh   # une fois
./run_airflow.sh
```

**Windows (PowerShell)**

```powershell
.\run_airflow.ps1
```

Les scripts `run_airflow.*` configurent `AIRFLOW_HOME`, l'écoute sur `127.0.0.1:8080` et affichent l'URL au démarrage.

**Alternative (toutes plateformes)**

```bash
export AIRFLOW_HOME="$(pwd)"
export AIRFLOW__API__HOST="127.0.0.1"
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS="true"
export AIRFLOW__LOGGING__BASE_LOG_FOLDER="${AIRFLOW_HOME}/.airflow/logs"
uv run airflow standalone
```

Interface web : **http://127.0.0.1:8080** (préférer `127.0.0.1` à `localhost`).

### Dépannage UI

```bash
./scripts/check_airflow_ui.sh          # Linux / macOS
.\scripts\check_airflow_ui.ps1         # Windows
```

- Si Airflow tourne dans **screen** : `screen -r` pour voir les logs et le mot de passe admin
- Mot de passe : `standalone_admin_password.txt` à la racine du dépôt (`AIRFLOW_HOME`)
- Ne pas lancer deux instances (port 8080 déjà utilisé)

### Déclencher le pipeline

**Un seul jour** (UI : Trigger → **Single run** + logical date, ou CLI) :

```bash
export AIRFLOW_HOME="$(pwd)"
uv run airflow dags trigger dag_run_pipeline -l 2026-04-29
```

**Plusieurs jours** (UI : Trigger → **Backfill** avec plage début/fin ; CLI) :

```bash
export AIRFLOW_HOME="$(pwd)"

# Vérification (dry-run)
uv run airflow backfill create --dag-id dag_run_pipeline \
  --from-date 2026-04-29 --to-date 2026-05-10 --dry-run

# Exécution (29/04 → 10/05 inclus ; to-date = dernier jour traité)
uv run airflow backfill create --dag-id dag_run_pipeline \
  --from-date 2026-04-29 --to-date 2026-05-10 \
  --reprocess-behavior none
```

Chaque DagRun traite la date métier de sa logical date (+ reprises des jours en échec antérieurs). L'enchaînement est séquentiel (`max_active_runs=1`).

---

## Variables d'environnement

| Variable | Usage |
|----------|--------|
| `STG_DATA_DIR` | Chemin vers le dossier `Data Hospital` (ex. `C:\data\Data Hospital` sur Windows) |
| `DBT_TARGET` | Forcer la cible dbt : `local` ou `workspace` |
| `AIRFLOW_HOME` | Racine du dépôt (obligatoire pour Airflow ; défini par les scripts `run_airflow.*`) |
| `STG_HISTORY_RETENTION_DAYS` | Rétention des snapshots STG dans `HISTORY/` |

---

## Arborescence utile

```
Inputs_Projets_NF26_AI07/Data Hospital/BDD_HOSPITAL_YYYYMMDD/  ← fichiers sources
SQL/                    ← scripts DDL + install_sid.py
src/                    ← load_data.py, pipeline_common.py, run_daily_pipeline.py
scripts/                ← check_airflow_ui.sh / .ps1
dags/                   ← dag_run_pipeline.py
dbt_hopital/            ← projet dbt (models, macros, profiles.yml)
dags/                   ← DAG Airflow
logs/                   ← installation.log + pipeline.log (+ pipeline_failed_dates.txt)
.airflow/logs/          ← logs techniques Airflow (gitignoré)
```

---

## Documentation complémentaire

- [CLAUDE.md](CLAUDE.md) — architecture, MPD, lots projet
- [tuto_dbt.md](tuto_dbt.md) — setup dbt détaillé
