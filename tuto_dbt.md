# Hopital DW — Setup dbt

## Prérequis
- Accès au compte Snowflake du projet
- Avoir cloné le repo 

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

Le fichier `profiles.yml` contient tes credentials Snowflake. Il doit être placé dans ton dossier personnel, dans un sous-dossier `.dbt` :
 
| Système | Emplacement |
|---|---|
| Windows | `C:\Users\ton_nom\.dbt\profiles.yml` |
| Mac | `/Users/ton_nom/.dbt/profiles.yml` |
| Linux | `/home/ton_nom/.dbt/profiles.yml` |

**Étapes :**
 
1. Crée le dossier `.dbt` dans ton dossier personnel s'il n'existe pas
2. Copie le fichier `profiles.yml.example` du repo dans ce dossier
3. Renomme-le `profiles.yml`
4. Ouvre-le et remplace les valeurs :

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