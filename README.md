# Projet NF26 - Collaboration avec Smart Teem 

Système d'information décisionnel hostpitalier. Workflow : ingestion fichiers plats STG → transformations dbt (WRK -> SOC) → Power BI.  
Stack : Snowflake, dbt Core, Apache Airflow, Python (`uv`).

**Plateformes supportées :** Linux, macOS, Windows (PowerShell).

Toutes les commandes ci-dessous s'exécutent **depuis la racine du dépôt**, sauf indication contraire.

---

## Contenu du livrable

| Lot | Contenu | Dossiers / Fichiers |
|-----|---------|---------------------|
| **Lot 1** — Environnement + MPD | Modèles physiques de données + documentation | `MPD/`, `env_projet.md` |
| **Lot 2** — Installation SID + Ingestion STG | Scripts de création des bases/tables + chargement STG | `SQL/`, `src/load_data.py` |
| **Lot 3** — Alimentation DWH + Orchestration | Projet dbt, DAGs Airflow, scripts pipeline | `dbt_hopital/`, `dags/`, `src/`, `run_airflow.ps1`, `run_airflow.sh`, `pyproject.toml`, `uv.lock` |
| **Lot 4** — Power BI | Vues SQL, exports CSV, dashboard | `PowerBI/` |

---

## Prérequis

- [uv](https://docs.astral.sh/uv/) installé
- Accès Snowflake (Compte projet, rôle `ACCOUNTADMIN`)
- Données sources dans `Inputs_Projets_NF26_AI07/Data Hospital/` (ou chemin personnalisé avec positionnement de la variable d'environnement `STG_DATA_DIR`)

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

Dans le **Workspace Snowflake**, la cible `workspace` est sélectionnée automatiquement :
- Les scripts Python (`install_sid.py`, `load_data.py`) lisent le token OAuth depuis `/snowflake/session/token` (fichier de session injecté par Snowflake) — aucune variable d'environnement à configurer.
- `dbt run` utilise la valeur `token: "{{ env_var('SNOWFLAKE_OAUTH_TOKEN') }}"` définie dans `profiles.yml` — la variable `SNOWFLAKE_OAUTH_TOKEN` doit être présente dans l'environnement du Workspace.

---

## 3. Installation du SID (bases + tables)

Script idempotent (log : `logs/installation.log`).

**Via Airflow (recommandé)** : démarrer Airflow (voir [§ 7](#7-airflow-orchestration)), puis déclencher manuellement le DAG `dag_install_sid` depuis l'UI (pas de schedule, trigger manuel uniquement).

**En CLI** :

```bash
uv run python SQL/install_sid.py
```

---

## 4. Chargement STG (un jour)

Charge les fichiers `.txt` d'une journée dans STG via PUT → COPY INTO. Le script crée le stage Snowflake automatiquement si besoin, historise STG dans `HISTORY/` avant de le tronquer, puis trace l'exécution dans TCH.

**En CLI :**

```bash
uv run python src/load_data.py --date 20260429
```

**Via Airflow :** le DAG `dag_run_pipeline` appelle `load_data` en interne — voir [§ 7](#7-airflow-orchestration).

Arguments :

- `--date YYYYMMDD` / `-d` — jour à charger (optionnel, défaut : `20260429`)
- `--data-dir CHEMIN` — dossier parent contenant `BDD_HOSPITAL_YYYYMMDD/` (défaut : `STG_DATA_DIR` ou `Inputs_Projets_NF26_AI07/Data Hospital/`)
- `--retention-days N` — rétention des snapshots dans `HISTORY/` (défaut : 2)
- `--skip-history` — désactive le snapshot avant truncate

Log : `logs/pipeline.log` (tronqué en exécution CLI ou trigger manuel Airflow ; append entre DagRuns d'un rattrapage)

---

## 5. Transformations dbt

dbt lit la connexion Snowflake depuis `dbt_hopital/profiles.yml` (même fichier que les scripts Python). Il transforme les données STG en deux couches :

- **WRK** (`+materialized: table`) — recrée la table à chaque `dbt run` depuis STG
- **SOC** (`+materialized: incremental`) — insère uniquement les nouvelles lignes, conserve l'historique

Chaque model trace son exécution dans TCH via les macros `start_tracking` / `end_tracking` (utilise `invocation_id` comme `EXEC_ID`).

**Tester la connexion :**

```bash
uv run dbt debug --project-dir dbt_hopital --profiles-dir dbt_hopital
```

**Lancer tous les modèles :**

```bash
uv run dbt run --project-dir dbt_hopital --profiles-dir dbt_hopital
```

**Lancer un seul modèle :**

```bash
uv run dbt run --project-dir dbt_hopital --profiles-dir dbt_hopital --select wrk_room
```

**Logs :** en CLI directe, dbt écrit sous `dbt_hopital/target/dbt_logs/`. Via le DAG ou `run_daily_pipeline`, la sortie est intégrée dans `logs/pipeline.log`.

---

## 6. Pipeline journalier local (indépendant du DAG)

[`src/run_daily_pipeline.py`](src/run_daily_pipeline.py) exécute **un jour** du pipeline sans Airflow. La date est fixée dans le code (`LOCAL_RUN_DATE`, défaut `20260429`).

```bash
uv run python src/run_daily_pipeline.py
```

Étapes :

1. Valide `LOCAL_RUN_DATE` et la présence des fichiers `.txt` du jour
2. Si fichiers absents → échec
3. Sinon → load STG → `dbt run`

Log : `logs/pipeline.log`

Pour traiter un autre jour : modifier `LOCAL_RUN_DATE` dans `src/run_daily_pipeline.py`.

---

## 7. Airflow (orchestration complète)

Le DAG `dag_run_pipeline` tourne selon deux modes :

**Mode normal (quotidien)** — `schedule=@daily`, `catchup=False`  
Le DAG se déclenche automatiquement chaque nuit à minuit UTC. Il traite la journée courante en passant par le pipeline complet dans l'ordre :

`resolve_dates` → `validate_date` → `ingestion_stg` → `dbt_run`

Pour chaque jour : validation des fichiers sources → chargement STG → `dbt run`. STG est tronqué et rechargé avant chaque dbt run.

**Mode rattrapage (plage de jours)**  
Pour traiter plusieurs jours d'un coup, utiliser le rattrapage Airflow. Chaque jour génère un DagRun indépendant. Les DagRuns s'enchaînent **séquentiellement** (`max_active_runs=1`) : le jour J doit terminer entièrement (validation → STG → dbt) avant que le jour J+1 commence.

**Reprise sur erreur**  
Si le jour J échoue, il est enregistré dans `logs/pipeline_failed_dates.txt`. Au DagRun suivant (J+1), le DAG retraite d'abord les jours en échec avant de traiter J+1. Un échec de reprise ne bloque pas J+1.

**Retry automatique** : 1 retry avec délai de 5 minutes (`retries=1, retry_delay=5min`).

**Log applicatif** : `logs/pipeline.log` — tronqué au trigger manuel ou en mode quotidien ; chaque DagRun de rattrapage s'ajoute en append. Supprimer le fichier avant un nouveau rattrapage pour repartir à zéro.

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
export AIRFLOW__API__PORT="8080"
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS="true"
export AIRFLOW__LOGGING__BASE_LOG_FOLDER="${AIRFLOW_HOME}/.airflow/logs"
uv run airflow standalone
```

Interface web : **http://127.0.0.1:8080** (préférer `127.0.0.1` à `localhost`).

### Déclencher le pipeline manuellement

**Un seul jour**

Depuis l'UI : ouvrir le DAG `dag_run_pipeline` → bouton **Trigger** → choisir **Single run** → renseigner la date métier à traiter (format `YYYY-MM-DD`).

Depuis la CLI :

```bash
export AIRFLOW_HOME="$(pwd)"
uv run airflow dags trigger dag_run_pipeline -l 2026-04-29
```

**Plusieurs jours**

Depuis l'UI : ouvrir le DAG `dag_run_pipeline` → bouton **Trigger** → choisir **Backfill** → renseigner la date de début et la date de fin.

Depuis la CLI :

```bash
export AIRFLOW_HOME="$(pwd)"

# Vérification sans exécuter (dry-run)
uv run airflow backfill create --dag-id dag_run_pipeline \
  --from-date 2026-04-29 --to-date 2026-05-10 --dry-run

# Exécution réelle (traite du 29/04 au 10/05 inclus)
uv run airflow backfill create --dag-id dag_run_pipeline \
  --from-date 2026-04-29 --to-date 2026-05-10 \
  --reprocess-behavior none
```

---

## Variables d'environnement

| Variable | Usage |
|----------|--------|
| `STG_DATA_DIR` | Chemin vers le dossier `Data Hospital` (ex. `C:\data\Data Hospital` sur Windows) |
| `DBT_TARGET` | Forcer la cible dbt : `local` ou `workspace` |
| `AIRFLOW_HOME` | Racine du dépôt (obligatoire pour Airflow ; défini par les scripts `run_airflow.*`) |
| `STG_HISTORY_RETENTION_DAYS` | Rétention des snapshots STG dans `HISTORY/` |

---

## Détail de l'arborescence

```
Inputs_Projets_NF26_AI07/Data Hospital/BDD_HOSPITAL_YYYYMMDD/  ← fichiers sources (.txt)
SQL/                    ← scripts de création des bases et tables (create_db, create_stg, create_soc, create_tch, create_stg_stage) + install_sid.py + snowflake_utils.py
src/                    ← scripts Python du pipeline (load_data.py, pipeline_common.py, pipeline_failed_dates.py, run_daily_pipeline.py)
dags/                   ← scripts DAG airflow (dag_run_pipeline.py, dag_install_sid.py)
dbt_hopital/            ← projet dbt (models WRK + SOC, macros, profiles.yml)
MPD/                    ← modèles de données STG et SOC 
PowerBI/                ← création des vues SQL (create_views/), exports du contenu des vues en CSV (export_views/exports/), dashboard .pbix
logs/                   ← fichiers de logs générés par l'ensemble des traitements du projet
```


