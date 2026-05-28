-- ============================================================
--  Script CREATE TABLE -- Schéma TCH
-- ============================================================

USE DATABASE TCH;

-- ------------------------------------------------------------
--  TCH.T_SUIV_RUN
--  (créée en premier car référencée par T_SUIV_TRMT)
-- ------------------------------------------------------------
CREATE TABLE TCH.T_SUIV_RUN (
    RUN_ID        INTEGER      NOT NULL,
    RUN_STRT_DTTM TIMESTAMP(0) NOT NULL,
    RUN_END_DTTM  TIMESTAMP(0),
    RUN_STTS_CD   VARCHAR(10)  NOT NULL,
    PRIMARY KEY (RUN_ID)
);

-- ------------------------------------------------------------
--  TCH.T_SUIV_TRMT
-- ------------------------------------------------------------
CREATE TABLE TCH.T_SUIV_TRMT (
    RUN_ID         INTEGER      NOT NULL,
    EXEC_ID        INTEGER      NOT NULL,
    SCRPT_NAME     VARCHAR(250) NOT NULL,
    EXEC_STRT_DTTM TIMESTAMP(0) NOT NULL,
    EXEC_END_DTTM  TIMESTAMP(0),
    EXEC_STTS_CD   VARCHAR(10)  NOT NULL,
    PRIMARY KEY (EXEC_ID),
    FOREIGN KEY (RUN_ID) REFERENCES TCH.T_SUIV_RUN (RUN_ID)
);