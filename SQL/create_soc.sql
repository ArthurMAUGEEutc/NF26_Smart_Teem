-- ============================================================
--  Script CREATE TABLE -- Schéma SOC
-- ============================================================

USE DATABASE SOC;

-- ------------------------------------------------------------
--  SOC.R_ROOM
-- ------------------------------------------------------------
CREATE TABLE SOC.R_ROOM (
    ROOM_NUM      INTEGER      NOT NULL,
    ROOM_NAME     VARCHAR(20)  NOT NULL,
    FLOR_NUM      BYTEINT,
    BULD_NAME     VARCHAR(20),
    ROOM_TYP      VARCHAR(10),
    ROOM_DAY_RATE SMALLINT     NOT NULL,
    CRTN_DT       DATE         NOT NULL,
    EXEC_ID       INTEGER      NOT NULL,
    PRIMARY KEY (ROOM_NUM)
);

-- ------------------------------------------------------------
--  SOC.R_PART
-- ------------------------------------------------------------
CREATE TABLE SOC.R_PART (
    PART_ID INTEGER      NOT NULL,
    SRC_ID  INTEGER      NOT NULL,
    SRC_TYP VARCHAR(50)  NOT NULL,
    PRIMARY KEY (PART_ID)
);

-- ------------------------------------------------------------
--  SOC.R_MEDC
-- ------------------------------------------------------------
CREATE TABLE SOC.R_MEDC (
    MEDC_ID   INTEGER      NOT NULL,
    MEDC_CD   VARCHAR(10)  NOT NULL,
    MEDC_NAME VARCHAR(250),
    MEDC_COND VARCHAR(100),
    MEDC_CATG VARCHAR(100) NOT NULL,
    MANF_BRND VARCHAR(100) NOT NULL,
    EXEC_ID   INTEGER      NOT NULL,
    PRIMARY KEY (MEDC_ID)
);

-- ------------------------------------------------------------
--  SOC.O_INDV
-- ------------------------------------------------------------
CREATE TABLE SOC.O_INDV (
    PART_ID        INTEGER      NOT NULL,
    INDV_NAME      VARCHAR(100) NOT NULL,
    INDV_FIRS_NAME VARCHAR(100) NOT NULL,
    INDV_STTS_CD   VARCHAR(10)  NOT NULL,
    CRTN_DTTM      TIMESTAMP(0) NOT NULL,
    UPDT_DTTM      TIMESTAMP(0) NOT NULL,
    BIRT_DT        DATE,
    BIRT_CITY      VARCHAR(100),
    BIRT_CNTR      VARCHAR(100),
    SOCL_NUM       VARCHAR(15),
    EXEC_ID        INTEGER      NOT NULL,
    PRIMARY KEY (PART_ID),
    FOREIGN KEY (PART_ID) REFERENCES SOC.R_PART (PART_ID)
);

-- ------------------------------------------------------------
--  SOC.O_STFF
-- ------------------------------------------------------------
CREATE TABLE SOC.O_STFF (
    PART_ID        INTEGER      NOT NULL,
    WORK_STRT_DTTM TIMESTAMP(0) NOT NULL,
    WORK_END_DTTM  TIMESTAMP(0),
    WORK_END_RESN  VARCHAR(100),
    EXEC_ID        INTEGER      NOT NULL,
    PRIMARY KEY (PART_ID),
    FOREIGN KEY (PART_ID) REFERENCES SOC.R_PART (PART_ID)
);

-- ------------------------------------------------------------
--  SOC.O_TELP
-- ------------------------------------------------------------
CREATE TABLE SOC.O_TELP (
    PART_ID        INTEGER      NOT NULL,
    CNTR_IND       VARCHAR(5),
    TELP_NUM       VARCHAR(20)  NOT NULL,
    STRT_VALD_DTTM TIMESTAMP(0) NOT NULL,
    END_VALD_DTTM  TIMESTAMP(0) NOT NULL,
    EXEC_ID        INTEGER      NOT NULL,
    PRIMARY KEY (PART_ID, STRT_VALD_DTTM),
    FOREIGN KEY (PART_ID) REFERENCES SOC.R_PART (PART_ID)
);

-- ------------------------------------------------------------
--  SOC.O_ADDR
-- ------------------------------------------------------------
CREATE TABLE SOC.O_ADDR (
    PART_ID        INTEGER      NOT NULL,
    STRT_NUM       VARCHAR(10)  NOT NULL,
    STRT_DSC       VARCHAR(250) NOT NULL,
    COMP_STRT      VARCHAR(250),
    POST_CD        VARCHAR(10)  NOT NULL,
    CITY_NAME      VARCHAR(100),
    CNTR_NAME      VARCHAR(100),
    STRT_VALD_DTTM TIMESTAMP(0) NOT NULL,
    END_VALD_DTTM  TIMESTAMP(0) NOT NULL,
    EXEC_ID        INTEGER      NOT NULL,
    PRIMARY KEY (PART_ID, STRT_VALD_DTTM),
    FOREIGN KEY (PART_ID) REFERENCES SOC.R_PART (PART_ID)
);

-- ------------------------------------------------------------
--  SOC.O_CONS
-- ------------------------------------------------------------
CREATE TABLE SOC.O_CONS (
    CONS_ID        INTEGER      NOT NULL,
    STFF_ID        INTEGER      NOT NULL,
    PATN_ID        INTEGER      NOT NULL,
    CONS_STRT_DTTM TIMESTAMP(0) NOT NULL,
    CONS_END_DTTM  TIMESTAMP(0) NOT NULL,
    PATN_WEGH      INTEGER      NOT NULL,
    PATN_TEMP      INTEGER,
    TEMP_UNIT      VARCHAR(15),
    BLD_PRSS       INTEGER,
    PATH_DSC       VARCHAR(250),
    DIBT_IND       BYTEINT,
    TRET_ID        TIMESTAMP(0),
    HOSP_IND       BYTEINT,
    EXEC_ID        INTEGER      NOT NULL,
    PRIMARY KEY (CONS_ID),
    FOREIGN KEY (STFF_ID) REFERENCES SOC.R_PART (PART_ID),
    FOREIGN KEY (PATN_ID) REFERENCES SOC.R_PART (PART_ID)
);

-- ------------------------------------------------------------
--  SOC.O_TRET
-- ------------------------------------------------------------
CREATE TABLE SOC.O_TRET (
    TRET_ID        INTEGER      NOT NULL,
    MEDC_ID        INTEGER,
    MEDC_QTY       SMALLINT,
    DOSG_DSC       VARCHAR(100) NOT NULL,
    CONS_ID        INTEGER      NOT NULL,
    TRET_CRTN_DTTM TIMESTAMP(0) NOT NULL,
    EXEC_ID        INTEGER      NOT NULL,
    PRIMARY KEY (TRET_ID),
    FOREIGN KEY (MEDC_ID) REFERENCES SOC.R_MEDC (MEDC_ID),
    FOREIGN KEY (CONS_ID) REFERENCES SOC.O_CONS (CONS_ID)
);

-- ------------------------------------------------------------
--  SOC.O_HOSP
-- ------------------------------------------------------------
CREATE TABLE SOC.O_HOSP (
    HOSP_ID        INTEGER      NOT NULL,
    CONS_ID        INTEGER      NOT NULL,
    ROOM_NUM       SMALLINT     NOT NULL,
    HOSP_STRT_DTTM TIMESTAMP(0) NOT NULL,
    HOSP_END_DTTM  TIMESTAMP(0) NOT NULL,
    HOSP_FINL_RATE TIMESTAMP(0) NOT NULL,
    STFF_ID        INTEGER      NOT NULL,
    EXEC_ID        INTEGER      NOT NULL,
    PRIMARY KEY (HOSP_ID),
    FOREIGN KEY (CONS_ID)  REFERENCES SOC.O_CONS (CONS_ID),
    FOREIGN KEY (ROOM_NUM) REFERENCES SOC.R_ROOM (ROOM_NUM),
    FOREIGN KEY (STFF_ID)  REFERENCES SOC.R_PART (PART_ID)
);