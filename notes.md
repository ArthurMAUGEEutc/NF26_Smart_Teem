Est-ce que c'est normal qu'il y ai des attributs qui sont indiqués comme nullable en staging mais qui sont utilisés comme primary key ? cf. NO_CHAMBRE par exemple
Est-ce qu'il y a besoin de faire un mpd staging ?

O_CONS.TRET_ID est typé TIMESTAMP(0) dans le mapping alors que c'est clairement un INTEGER ? 
O_HOSP.HOSP_FINL_RATE est aussi TIMESTAMP(0) alors que c'est un cout ?

Est-ce qu'on peut déjà avancer sur le deuxième rendu, et on est d'accord que c'est faire les scripts SQL pour créer les tables ? 

A quoi ça correspond la base de travail (elle n'est pas dans le fichier mapping) ? 