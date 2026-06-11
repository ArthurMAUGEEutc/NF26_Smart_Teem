# NF26 — Mise en place d'une solution décisionnelle (DWH Snowflake + Power BI)

Projet universitaire UTC GI04, en collaboration avec **Smart Teem** (cabinet Data & IA). L'objectif est de construire un système d'information décisionnel (SID) complet pour le suivi d'activité d'un établissement de santé hospitalier.

---

## Contexte métier

Le SID ingère des données hospitalières (fichiers `.txt` fournis quotidiennement) et les transforme jusqu'à des tableaux de bord Power BI. Les données couvrent : chambres, patients, personnel, consultations, hospitalisations, médicaments, traitements.

---

## Stack technique

| Outil | Rôle |
|---|---|
| **Snowflake** | Cloud DWH (AWS, Enterprise) |
| **dbt Core** | Transformations SQL (models WRK, SOC) |
| **Apache Airflow** | Orchestration des pipelines |
| **Python / uv** | Scripts d'installation (`SQL/install_sid.py`) et chargement STG (`src/load_data.py`) |
| **Power BI** | Reporting final |
| **GitHub** | Versionning |
| **Notion** | Suivi de projet |
| **Slack** | Échanges internes |
| **Teams** | Échanges client (Smart Teem) |
| **VS Code** | Éditeur |

Dépendance Python : `snowflake-connector-python` (voir [pyproject.toml](pyproject.toml)). Gérer l'env avec `uv`.

---

## Architecture Snowflake

```
Fichiers plats (.txt)
        │
        ▼
  STG (Staging/ODS)          ← Contrôle / Gestion de rejet
        │  (dbt)
        ▼
  WRK (Travail)              ← Qualité / Unification
        │  (dbt)
        ▼
  SOC (Socle/Vue)            ← Historisation
        │
        ▼
  Power BI
```

**TCH** est une base technique transverse qui trace l'exécution de tous les scripts.

---

## Bases de données Snowflake

### STG — Staging (tables recréées à chaque install)
Tables : `CHAMBRE`, `TRAITEMENT`, `PERSONNEL`, `PATIENT`, `CONSULTATION`, `HOSPITALISATION`, `MEDICAMENT`
Script : [SQL/create_stg.sql](SQL/create_stg.sql) — utilise `CREATE OR REPLACE TABLE`

### SOC — Socle (tables conservées si elles existent)
Tables :
- `R_ROOM` — référentiel chambres
- `R_MEDC` — référentiel médicaments
- `R_PART` — référentiel parties (pivot patient/personnel)
- `O_INDV` — individus (patients + personnel)
- `O_STFF` — personnel (rattaché à R_PART)
- `O_TELP` — téléphones (historisée par `STRT_VALD_DTTM`)
- `O_ADDR` — adresses (historisée par `STRT_VALD_DTTM`)
- `O_TRET` — traitements
- `O_CONS` — consultations
- `O_HOSP` — hospitalisations

Script : [SQL/create_soc.sql](SQL/create_soc.sql) — utilise `CREATE TABLE IF NOT EXISTS`

### TCH — Technique (tables de suivi)
Tables :
- `T_SUIV_RUN` — un enregistrement par run global (`EXEC_ID`, `RUN_STRT_DTTM`, `RUN_END_DTTM`, `RUN_STTS_CD`)
- `T_SUIV_TRMT` — un enregistrement par script dans un run (`EXEC_ID`, `SCRPT_NAME`, `EXEC_STRT_DTTM`, `EXEC_END_DTTM`, `EXEC_STTS_CD`)

Script : [SQL/create.tch.sql](SQL/create.tch.sql) — utilise `CREATE TABLE IF NOT EXISTS`

Codes statut : `'ENC'` (en cours), `'OK'`, `'KO'`

---

## Macros SQL (`SQL/macros.sql`)

Les macros encadrent **chaque script de traitement dbt** pour tracer son exécution dans TCH. Paramètres : `:EXEC_ID` (UUID du run), `:SCRPT_NAME` (nom du script).

**Macro début :**
```sql
INSERT INTO TCH.T_SUIV_RUN (EXEC_ID, RUN_STRT_DTTM, RUN_STTS_CD)
VALUES (:EXEC_ID, CURRENT_TIMESTAMP, 'ENC');

INSERT INTO TCH.T_SUIV_TRMT (EXEC_ID, SCRPT_NAME, EXEC_STRT_DTTM, EXEC_STTS_CD)
VALUES (:EXEC_ID, :SCRPT_NAME, CURRENT_TIMESTAMP, 'ENC');
```

**Macro fin OK :**
```sql
UPDATE TCH.T_SUIV_TRMT SET EXEC_END_DTTM = CURRENT_TIMESTAMP, EXEC_STTS_CD = 'OK' WHERE EXEC_ID = :EXEC_ID;
UPDATE TCH.T_SUIV_RUN  SET RUN_END_DTTM  = CURRENT_TIMESTAMP, RUN_STTS_CD  = 'OK' WHERE EXEC_ID = :EXEC_ID;
```

**Macro fin KO :**
```sql
UPDATE TCH.T_SUIV_TRMT SET EXEC_END_DTTM = CURRENT_TIMESTAMP, EXEC_STTS_CD = 'KO' WHERE EXEC_ID = :EXEC_ID;
UPDATE TCH.T_SUIV_RUN  SET RUN_END_DTTM  = CURRENT_TIMESTAMP, RUN_STTS_CD  = 'KO' WHERE EXEC_ID = :EXEC_ID;
```

> **Question ouverte (Lot 2 en cours) :** comment passer les paramètres `:EXEC_ID` et `:SCRPT_NAME` dans le contexte dbt ? Comment appeler les macros au début/fin de chaque model dbt ?

---

## Script d'installation (`SQL/install_sid.py`)

Script Python **idempotent** qui exécute les scripts SQL dans l'ordre :
1. `create_db.sql` — bases STG, SOC, TCH (`IF NOT EXISTS`)
2. `create_stg.sql` — tables STG (`CREATE OR REPLACE`)
3. `create_soc.sql` — tables SOC (`IF NOT EXISTS`)
4. `create_tch.sql` — tables TCH (`IF NOT EXISTS`)

Contraintes respectées :
- Toujours termine avec `sys.exit(0)` (jamais d'erreur fatale)
- Logue tout dans `logs/installation.log`
- Connexion via [`dbt_hopital/profiles.yml`](dbt_hopital/profiles.yml) (cible `local` ou `workspace`)
- Module partagé : [`SQL/snowflake_utils.py`](SQL/snowflake_utils.py)

### Exécution

Depuis la racine du dépôt (Linux, macOS, Windows — voir [README.md](README.md)) :

```bash
cp dbt_hopital/profiles.yml.example dbt_hopital/profiles.yml   # une fois, renseigner credentials
uv run python SQL/install_sid.py
uv run python src/load_data.py --date 20260429
uv run dbt run --project-dir dbt_hopital --profiles-dir dbt_hopital
```

---

## Chargement STG (`src/load_data.py`)

Script Python qui charge les fichiers `.txt` d'**un seul jour** dans les tables STG via `PUT` + `COPY INTO` (local ou Workspace) :
- Source : `Inputs_Projets_NF26_AI07/Data Hospital/BDD_HOSPITAL_{YYYYMMDD}/` (ou `STG_DATA_DIR`, ou `/workspace/.../data`)
- Stage : `STG.PUBLIC.STG_LOAD_STAGE` (voir [`SQL/create_stg_stage.sql`](SQL/create_stg_stage.sql))
- Log : `logs/pipeline.log`
- Suivi TCH : entrées dans `TCH.PUBLIC.T_SUIV_RUN` / `T_SUIV_TRMT`
- Historisation : snapshot STG dans `HISTORY/` avant truncate (rétention configurable, défaut 2 jours)

Arguments CLI :
- `--date YYYYMMDD` (obligatoire)
- `--retention-days N` (défaut 2, ou env `STG_HISTORY_RETENTION_DAYS`)
- `--skip-history` (désactive l'historisation)

---

## Orchestration Airflow (`dags/dag_run_pipeline.py`)

DAG `schedule=@daily`, `catchup=False` — déclenchement manuel ou backfill (DAG en pause par défaut recommandé). Tâches :

`resolve_dates` → `validate_date` → `ingestion_stg` → `dbt_run` ([`src/pipeline_common.py`](src/pipeline_common.py))

Date métier par DagRun : **`ds_nodash`** (logical date). Période multi-jours : **backfill** = un DagRun par jour, séquentiel (`max_active_runs=1`, `depends_on_past=False`).

Comportement par DagRun :

1. Construit la liste des dates : échecs antérieurs (`logs/pipeline_failed_dates.txt`) + `ds_nodash`
2. Pour chaque date : validation fichiers → `load_data_day` → `dbt run`
3. Continue même si une reprise échoue ; le DagRun échoue seulement si `ds_nodash` échoue
4. Si J échoue, J+1 est quand même lancé et retente J avant de traiter J+1

[`src/run_daily_pipeline.py`](src/run_daily_pipeline.py) est **indépendant** du DAG (date fixe `LOCAL_RUN_DATE`). [`src/pipeline_common.py`](src/pipeline_common.py) et [`src/pipeline_failed_dates.py`](src/pipeline_failed_dates.py) centralisent l'exécution et la reprise.

Lancement Airflow : `./run_airflow.sh` (Linux/macOS), `.\run_airflow.ps1` (Windows). UI : http://127.0.0.1:8080. Voir [README.md](README.md).

Logs pipeline (DAG, simulateur local, `load_data.py` CLI) : `logs/pipeline.log` (tronqué au trigger manuel d'un jour ou exécution locale ; append entre DagRuns d'un backfill).

Logs Airflow (UI) : `.airflow/logs/` (hors dossier `logs/` applicatif).

---

## Données sources

Répertoire : [Inputs_Projets_NF26_AI07/Data Hospital/](Inputs_Projets_NF26_AI07/Data%20Hospital/)
Format : fichiers `.txt` nommés `{TABLE}_{YYYYMMDD}.txt`, un dossier par jour.
Tables : `CHAMBRE`, `CONSULTATION`, `HOSPITALISATION`, `MEDICAMENT`, `PATIENT`, `PERSONNEL`, `TRAITEMENT`

---

## Découpage en lots

| Lot | Périmètre | Statut |
|---|---|---|
| **Lot 1** | Install env + conception MPD | Terminé |
| **Lot 2** | Installation SID + ingestion STG + macros + models WRK/SOC (ROOM, PARTY, MEDICINE) | **En cours** |
| **Lot 3** | Models WRK/SOC : HOSPITALIZATION, CONSULTATION, ADDRESS, TELEPHONE, STAFF, INDIVIDUAL, TREATMENT | À faire |
| **Lot 4** | Vues SOC → export CSV/XLSX → tableaux de bord Power BI | À faire |

### Détail Lot 2 (en cours)

- **2.1** Installation du SID → `install_sid.py` + scripts SQL ✓
- **2.2** Ingestion STG → `src/load_data.py` + `SQL/create_stg_stage.sql` ✓
- **2.3** Macros de suivi d'exécution + models dbt WRK/SOC pour ROOM, PARTY, MEDICINE ← **focus actuel**

---

## Planning sprints

| Sprint | Dates | Contenu |
|---|---|---|
| Kick-off / Sprint 1 | 21/05 | Présentation + Lot 1 |
| Sprint 2 | 28/05 | Fin Lot 1 + début Lot 2 |
| Sprint 3 | 03/06 | Fin Lot 2 + début Lot 3 |
| Sprint 4 | 09/06 | Fin Lot 3 + début Lot 4 |
| Fin projet | 16/06 | Fin Lot 4 |
| Soutenances | 18/06 | — |

---

## MPD

Fichiers dans [MPD/](MPD/) :
- `socle.dbml` / `socle.dbdiagram` / `socle.puml` — modèle SOC
- `stg.dbml` / `stg.dbdiagram` — modèle STG

---

## Règles importantes

- Le script `install_sid.py` est **idempotent** : peut tourner plusieurs fois sans casser quoi que ce soit
- Les bases STG et WRK sont gérées par dbt (recréées)
- Les tables SOC et TCH ne sont jamais droppées
- Toutes les exécutions (install + traitements) doivent être tracées dans un fichier `.log`
- Le suivi TCH est **obligatoire** pour tous les models dbt (Lots 2 et 3)
