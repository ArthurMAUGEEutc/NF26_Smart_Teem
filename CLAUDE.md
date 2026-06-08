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
| **Python / uv** | Scripts d'installation (`SQL/install_sid.py`) et chargement STG (`dbt/load_stg.py`) |
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
- Connexion via OAuth token Snowflake (`SNOWFLAKE_TOKEN_FILE_PATH`)
- Module partagé : [`SQL/snowflake_utils.py`](SQL/snowflake_utils.py)

### Exécution (Workspace Snowflake)

```bash
python SQL/install_sid.py
python dbt/load_stg.py --date 20260429
cd dbt && dbt run
```

---

## Chargement STG (`dbt/load_stg.py`)

Script Python qui charge les fichiers `.txt` d'**un seul jour** dans les tables STG via `PUT` + `COPY INTO` :
- Source : `Inputs_Projets_NF26_AI07/Data Hospital/BDD_HOSPITAL_{YYYYMMDD}/`
- Stage : `STG.PUBLIC.STG_LOAD_STAGE` (voir [`SQL/create_stg_stage.sql`](SQL/create_stg_stage.sql))
- Log : `logs/load_stg.log`
- Suivi TCH : entrées dans `TCH.PUBLIC.T_SUIV_RUN` / `T_SUIV_TRMT`
- Historisation : snapshot STG dans `HISTORY/` avant truncate (rétention configurable, défaut 2 jours)

Arguments CLI :
- `--date YYYYMMDD` (obligatoire)
- `--retention-days N` (défaut 2, ou env `STG_HISTORY_RETENTION_DAYS`)
- `--skip-history` (désactive l'historisation)

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
- **2.2** Ingestion STG → `dbt/load_stg.py` + `SQL/create_stg_stage.sql` ✓
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
