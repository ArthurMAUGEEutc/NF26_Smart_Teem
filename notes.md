
Est-ce qu'il y a besoin de faire un mpd staging ? = > NON  

Problèmes : 

- O_CONS.TRET_ID est typé TIMESTAMP(0) dans le mapping alors que c'est un INTEGER ?
- O_HOSP.HOSP_FINL_RATE est aussi TIMESTAMP(0) alors que c'est un cout 
- Est-ce que c'est normal qu'il y ai des attributs qui sont indiqués comme nullable en staging mais qui sont utilisés comme primary key ou juste marqués comme not null ? cf. NO_CHAMBRE par exemple


A quoi ça correspond la base de travail (elle n'est pas dans le fichier mapping) ? 