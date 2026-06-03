Pour le lot 2 : 
- Développement du script de création des bases de donnée : créer 3 bases : STG et pour socle SOC et TCH
- Développement des scripts de création des tables (un script par base de données) => utiliser le MPD stg et socle
- Développement du scripts ‘install_sid.py’ d’exécution de l’installation du SID => script qui appelle les scripts sql créés précédemment pour tout créer
- Développement des macros : comment on passe les paramètres ? comment on lance les macros ? 

Est-ce qu'il faut que les fichiers load_data et install_sid on les run depuis un terminal et qu'ils se connectent à snowflake,
ou est-ce qu'on peut les lancer directement dans un workspace snowflake ? 

supprimer public_public

Pour le lot 3 : 
- dag airflow d’ordonnancement de l’installation / dag airflow d’ordonnancement de l’ingestion et alimentation du datawarehouse
- faire les models restants en s'assurant d'ajouter les macros
- Les exécutions doivent être tracées dans un fichier .log => je pense que ça se gère dans airflow

Tâches à se répartir : 
- Models des 7 tables (wrk + soc) = 14 modèles à faire
- Airflows : 2 DAGs (je pense bien 2 personnes pour comprendre airflow + faire)