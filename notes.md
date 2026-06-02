
Problèmes : 

- O_CONS.TRET_ID est typé TIMESTAMP(0) dans le mapping alors que c'est un INTEGER ?
- O_HOSP.HOSP_FINL_RATE est aussi TIMESTAMP(0) alors que c'est un cout 
- Est-ce que c'est normal qu'il y ai des attributs qui sont indiqués comme nullable en staging mais qui sont utilisés comme primary key ou juste marqués comme not null ? cf. NO_CHAMBRE par exemple


A quoi ça correspond la base de travail (elle n'est pas dans le fichier mapping) ? 

Pour le lot 2 : 
- Développement du script de création des bases de donnée : créer 3 bases : STG et pour socle SOC et TCH
- Développement des scripts de création des tables (un script par base de données) => utiliser le MPD stg et socle
- Développement du scripts ‘install_sid.py’ d’exécution de l’installation du SID => script qui appelle les scripts sql créés précédemment pour tout créer