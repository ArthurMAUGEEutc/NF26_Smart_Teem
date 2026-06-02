-- Ces macros doivent se placer au début et à la fin des scripts SQL de traitement
-- Pour les paramètres, voir comment ils sont passés. 

-- Macro de début d'exécution
INSERT INTO TCH.T_SUIV_RUN (
    EXEC_ID,
    RUN_STRT_DTTM,
    RUN_STTS_CD
)
VALUES (
    :EXEC_ID,
    CURRENT_TIMESTAMP,
    'ENC'
);

INSERT INTO TCH.T_SUIV_TRMT (
    EXEC_ID,
    SCRPT_NAME,
    EXEC_STRT_DTTM,
    EXEC_STTS_CD
)
VALUES (
    :EXEC_ID,
    :SCRPT_NAME,
    CURRENT_TIMESTAMP,
    'ENC'
);


-- Macro de fin d'exécution OK
UPDATE TCH.T_SUIV_TRMT
SET EXEC_END_DTTM = CURRENT_TIMESTAMP, EXEC_STTS_CD = 'OK' 
WHERE EXEC_ID = :EXEC_ID;

UPDATE TCH.T_SUIV_RUN
SET RUN_END_DTTM = CURRENT_TIMESTAMP, RUN_STTS_CD = 'OK' 
WHERE EXEC_ID = :EXEC_ID;

-- Macro de fin d'exécution en erreur
UPDATE TCH.T_SUIV_TRMT
SET EXEC_END_DTTM = CURRENT_TIMESTAMP, EXEC_STTS_CD = 'KO'
WHERE EXEC_ID = :EXEC_ID;

UPDATE TCH.T_SUIV_RUN
SET RUN_END_DTTM = CURRENT_TIMESTAMP, RUN_STTS_CD = 'KO'
WHERE EXEC_ID = :EXEC_ID;