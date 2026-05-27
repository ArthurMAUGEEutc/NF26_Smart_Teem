Est-ce que c'est normal qu'il y ai des attributs qui sont indiqués comme nullable en staging mais qui sont utilisés comme primary key ? cf. NO_CHAMBRE par exemple
Est-ce qu'il y a besoin de faire un mpd staging ?

La table R_PART est centrale — elle regroupe personnel et patients sous un identifiant unique PART_ID. Toutes les tables opérationnelles (O_INDV, O_STFF, O_TELP, O_ADDR, O_CONS, O_HOSP) y font référence. Cela génère plusieurs relations depuis R_PART vers O_CONS (une pour le personnel, une pour le patient) — dbdiagram.io les affichera comme deux flèches distinctes, ce qui est correct.
Deux anomalies de type héritées du mapping que tu devrais signaler :

O_CONS.TRET_ID est typé TIMESTAMP(0) dans le mapping alors que c'est clairement un INTEGER
O_HOSP.HOSP_FINL_RATE est aussi TIMESTAMP(0) alors que c'est un coût financier → probablement DECIMAL(10,2)

Les tables O_TELP et O_ADDR ont une PK composite (PART_ID, STRT_VALD_DTTM) — c'est une modélisation d'historisation SCD de type 2 light, où chaque changement d'adresse ou de téléphone crée une nouvelle ligne datée.