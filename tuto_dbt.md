# Hopital DW — Setup dbt

Guide dbt complémentaire. Pour l'onboarding global (install, load, pipeline, Airflow), voir [README.md](README.md).

## Prérequis
- Accès au compte Snowflake du projet
- Avoir cloné le repo

---

## 1. Installer dbt

```bash
uv sync
```

Vérifie l'installation :

```bash
uv run dbt --version
```

---

## 2. Créer ton profil de connexion

Le fichier `profiles.yml` contient tes credentials Snowflake. Il est placé **dans le projet** :

```
dbt_hopital/profiles.yml   ← ne jamais committer (gitignoré)
```

**Étapes :**

1. Copie le template :

   **Linux / macOS**
   ```bash
   cp dbt_hopital/profiles.yml.example dbt_hopital/profiles.yml
   ```

   **Windows (PowerShell)**
   ```powershell
   Copy-Item dbt_hopital/profiles.yml.example dbt_hopital/profiles.yml
   ```

2. Ouvre `dbt_hopital/profiles.yml` et remplace les valeurs sous `outputs.local` :
   - `account` : identifiant du compte Snowflake (commun au projet)
   - `user` : ton login Snowflake
   - `password` : ton mot de passe

La cible `workspace` (OAuth) est utilisée automatiquement dans le Workspace Snowflake.

---

## 3. Tester la connexion

```bash
uv run dbt debug --project-dir dbt_hopital --profiles-dir dbt_hopital
```

Si tout est OK tu verras :
```
All checks passed!
```

---

## 4. Lancer les transformations

```bash
uv run dbt run --project-dir dbt_hopital --profiles-dir dbt_hopital
```

Pour un sous-ensemble de modèles :

```bash
uv run dbt run --project-dir dbt_hopital --profiles-dir dbt_hopital --select wrk
```

---

## Pipeline journalier et Airflow

Le chargement STG + `dbt run` séquentiel est orchestré par :

```bash
uv run python src/run_daily_pipeline.py
```

Voir [README.md](README.md) pour Airflow et les variables d'environnement (`STG_DATA_DIR`, `DBT_TARGET`).

---

## En cas de problème

- **`dbt debug` échoue** → vérifie ton user/password dans `dbt_hopital/profiles.yml`
- **`command not found: dbt`** → relance `uv sync`, utilise `uv run dbt`
- **Erreur de permission Snowflake** → vérifie que ton rôle est bien `ACCOUNTADMIN`
- **Scripts Python (`install_sid`, `load_data`)** → utilisent le même `dbt_hopital/profiles.yml` via `snowflake_utils`
- **Logs dbt** → `logs/dbt.log` à la racine du projet (pas dans `dbt_hopital/logs/`)
