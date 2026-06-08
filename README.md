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

Log : `logs/load_data.log`

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

Log dbt : `logs/dbt.log` (configuré dans `dbt_hopital/dbt_project.yml`).

Guide détaillé dbt : [tuto_dbt.md](tuto_dbt.md)

---

## 6. Pipeline journalier (load + dbt + curseur date)

Traite **un jour** à la fois : charge STG, exécute `dbt run`, avance le curseur de +1 jour en cas de succès.

```bash
uv run python src/run_daily_pipeline.py
```

Comportement :

1. Lit la date dans `logs/pipeline_date_cursor.txt` (défaut `20260429` si absent)
2. Vérifie la présence des 7 fichiers `.txt` du jour
3. Si fichiers absents → échec, curseur inchangé
4. Sinon → load STG → `dbt run` → curseur +1 jour

Log : `logs/run_daily_pipeline.log`

Réinitialiser le parcours : supprimer `logs/pipeline_date_cursor.txt`.

---

## 7. Airflow (orchestration optionnelle)

Le DAG `dag_run_pipeline` planifie le pipeline journalier à **6h00** et peut aussi être déclenché manuellement.

### Démarrer Airflow

**Linux / macOS**

```bash
./run_airflow.sh
```

**Windows (PowerShell)**

```powershell
.\run_airflow.ps1
```

**Alternative (toutes plateformes)**

```bash
# Linux / macOS
export AIRFLOW_HOME="$(pwd)"
uv run airflow standalone
```

```powershell
# Windows PowerShell
$env:AIRFLOW_HOME = (Get-Location).Path
uv run airflow standalone
```

Au premier lancement, un login/mot de passe admin s'affiche dans le terminal.  
Interface web : http://localhost:8080

### Déclencher le pipeline manuellement

```bash
export AIRFLOW_HOME="$(pwd)"   # ou $env:AIRFLOW_HOME sur Windows
uv run airflow dags trigger dag_run_pipeline
```

Ou via l'UI : DAG **dag_run_pipeline** → **Trigger**.

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
src/                    ← load_data.py, run_daily_pipeline.py
dbt_hopital/            ← projet dbt (models, macros, profiles.yml)
dags/                   ← DAG Airflow
logs/                   ← logs applicatifs (gitignoré)
```

---

## Documentation complémentaire

- [CLAUDE.md](CLAUDE.md) — architecture, MPD, lots projet
- [tuto_dbt.md](tuto_dbt.md) — setup dbt détaillé
