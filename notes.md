Pour le lot 2 : 
- Développement du script de création des bases de donnée : créer 3 bases : STG et pour socle SOC et TCH
- Développement des scripts de création des tables (un script par base de données) => utiliser le MPD stg et socle
- Développement du script `SQL/install_sid.py` d'exécution de l'installation du SID
- Développement du script `src/load_data.py` de chargement STG depuis les fichiers `.txt` (local et workspace)
- Développement des macros : comment on passe les paramètres ? comment on lance les macros ? 

Est-ce qu'il faut que les fichiers load_data et install_sid on les run depuis un terminal et qu'ils se connectent à snowflake,
ou est-ce qu'on peut les lancer directement dans un workspace snowflake ? 

supprimer public_public

Pour le lot 3 : 
- dag airflow d'ordonnancement de l'installation / dag airflow d'ordonnancement de l'ingestion et alimentation du datawarehouse
- faire les models restants en s'assurant d'ajouter les macros
- Les exécutions doivent être tracées dans un fichier .log => je pense que ça se gère dans airflow


- Traitement chronologique jour par jour : `src/run_daily_pipeline.py` + curseur `logs/pipeline_date_cursor.txt` (DAG `dag_run_pipeline`, +1 jour à chaque run réussi à 6h, départ `20260429`)
