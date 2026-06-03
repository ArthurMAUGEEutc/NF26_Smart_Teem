-- ============================================================
-- Création des tables de la base TCH (Technique)
-- Les tables TCH ne sont PAS recréées si elles existent déjà
-- ============================================================

USE ROLE ACCOUNTADMIN;

CREATE SCHEMA IF NOT EXISTS TCH.PUBLIC;

-- Table T_SUIV_RUN (Suivi des runs d'exécution)
CREATE TABLE IF NOT EXISTS TCH.PUBLIC.T_SUIV_RUN (
    EXEC_ID         CHAR(36)      NOT NULL,
    RUN_STRT_DTTM   TIMESTAMP(0)  NOT NULL,
    RUN_END_DTTM    TIMESTAMP(0),
    RUN_STTS_CD     VARCHAR(10)   NOT NULL,
    PRIMARY KEY (EXEC_ID)
);

-- Table T_SUIV_TRMT (Suivi des traitements par run)
CREATE TABLE IF NOT EXISTS TCH.PUBLIC.T_SUIV_TRMT (
    EXEC_ID         CHAR(36)      NOT NULL,
    SCRPT_NAME      VARCHAR(250)  NOT NULL,
    EXEC_STRT_DTTM  TIMESTAMP(0)  NOT NULL,
    EXEC_END_DTTM   TIMESTAMP(0),
    EXEC_STTS_CD    VARCHAR(10)   NOT NULL,
    PRIMARY KEY (EXEC_ID),
    FOREIGN KEY (EXEC_ID) REFERENCES TCH.PUBLIC.T_SUIV_RUN(EXEC_ID)
);
