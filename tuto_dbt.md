# Hopital DW — Setup dbt

## Prérequis
- Python installé sur ton PC
- Accès au compte Snowflake du projet
- Avoir cloné le repo GitLab

---

## 1. Installer dbt

```bash
pip install dbt-snowflake
```

Vérifie l'installation :
```bash
dbt --version
```

---

## 2. Créer ton profil de connexion

Copie le fichier exemple fourni dans le repo :
(~ = C:\Users\ton_nom\ sur windows et /Users/ton_nom/ sur mac)

```bash
cp profiles.yml.example ~/.dbt/profiles.yml
```

Ouvre `~/.dbt/profiles.yml` et remplace les valeurs : 

```yaml
dbt_hopital:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "woalaur-yb99371"   # identifiant du compte Snowflake (ne pas modifier)
      user: "ton_user"             # ton identifiant Snowflake (prénom en majuscule)
      password: "ton_password"     # ton mot de passe Snowflake
      role: ACCOUNTADMIN
      warehouse: COMPUTE_WH
      database: SOC
      schema: PUBLIC
      threads: 4
```

---

## 3. Tester la connexion

Place-toi dans le dossier du projet dbt :

```bash
cd dbt_hopital
```

Lance le test de connexion :

```bash
dbt debug
```

Si tout est OK tu verras :
```
All checks passed!
```

## En cas de problème

- **`dbt debug` échoue** → vérifie ton user/password dans `~/.dbt/profiles.yml`
- **`command not found: dbt`** → relance `pip install dbt-snowflake`
- **Erreur de permission Snowflake** → vérifie que ton rôle est bien `ACCOUNTADMIN`