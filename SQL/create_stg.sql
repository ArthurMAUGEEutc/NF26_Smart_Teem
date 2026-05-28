-- ============================================================
--  MPD Staging -- Script CREATE TABLE
--  Database : STG
-- ============================================================

USE DATABASE STG;

-- ------------------------------------------------------------
--  STG.CHAMBRE
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS STG.PUBLIC.CHAMBRE (
    NO_CHAMBRE    INTEGER,
    NOM_CHAMBRE   VARCHAR(20),
    NO_ETAGE      BYTEINT      NOT NULL,
    NOM_BATIMENT  VARCHAR(20)  NOT NULL,
    TYPE_CHAMBRE  VARCHAR(10)  NOT NULL,
    PRIX_JOUR     SMALLINT,
    DT_CREATION   DATE
);

-- ------------------------------------------------------------
--  STG.TRAITEMENT
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS STG.PUBLIC.TRAITEMENT (
    ID_TRAITEMENT          INTEGER,
    CD_MEDICAMENT          INTEGER,
    CATG_MEDICAMENT        VARCHAR(100),
    MARQUE_FABRI           VARCHAR(100),
    QTE_MEDICAMENT         SMALLINT     NOT NULL,
    DSC_POSOLOGIE          VARCHAR(100),
    ID_CONSULT             INTEGER,
    TS_CREATION_TRAITEMENT TIMESTAMP(0)
);

-- ------------------------------------------------------------
--  STG.PERSONNEL
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS STG.PUBLIC.PERSONNEL (
    ID_PERSONNEL          INTEGER,
    NOM_PERSONNEL         VARCHAR(100),
    PRENOM_PERSONNEL      VARCHAR(100),
    FONCTION_PERSONNEL    VARCHAR(50),
    TS_DEBUT_ACTIVITE     TIMESTAMP(0),
    TS_FIN_ACTIVITE       TIMESTAMP(0)  NOT NULL,
    RAISON_FIN_ACTIVITE   VARCHAR(100)  NOT NULL,
    TS_CREATION_PERSONNEL TIMESTAMP(0),
    TS_MAJ_PERSONNEL      TIMESTAMP(0),
    CD_STATUT_PERSONNEL   VARCHAR(10)
);

-- ------------------------------------------------------------
--  STG.PATIENT
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS STG.PUBLIC.PATIENT (
    ID_PATIENT          INTEGER,
    NOM_PATIENT         VARCHAR(100),
    PRENOM_PATIENT      VARCHAR(100),
    DT_NAISS            DATE          NOT NULL,
    VILLE_NAISS         VARCHAR(100)  NOT NULL,
    PAYS_NAISS          VARCHAR(100)  NOT NULL,
    NUM_SECU            VARCHAR(15)   NOT NULL,
    IND_PAYS_NUM_TELP   VARCHAR(5)    NOT NULL,
    NUM_TELEPHONE       VARCHAR(20)   NOT NULL,
    NUM_VOIE            VARCHAR(10)   NOT NULL,
    DSC_VOIE            VARCHAR(250)  NOT NULL,
    CMPL_VOIE           VARCHAR(250)  NOT NULL,
    CD_POSTAL           VARCHAR(10)   NOT NULL,
    VILLE               VARCHAR(100)  NOT NULL,
    PAYS                VARCHAR(100)  NOT NULL,
    TS_CREATION_PATIENT TIMESTAMP(0),
    TS_MAJ_PATIENT      TIMESTAMP(0)
);

-- ------------------------------------------------------------
--  STG.CONSULTATION
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS STG.PUBLIC.CONSULTATION (
    ID_CONSULT       INTEGER,
    ID_PERSONNEL     INTEGER,
    ID_PATIENT       INTEGER,
    TS_DEBUT_CONSULT TIMESTAMP(0),
    TS_FIN_CONSULT   TIMESTAMP(0),
    POIDS_PATIENT    INTEGER,
    TEMP_PATIENT     INTEGER      NOT NULL,
    UNIT_TEMP        VARCHAR(15)  NOT NULL,
    TENSION_PATIENT  INTEGER      NOT NULL,
    DSC_PATHO        VARCHAR(250) NOT NULL,
    INDIC_DIABETE    VARCHAR(10)  NOT NULL,
    ID_TRAITEMENT    INTEGER      NOT NULL,
    INDIC_HOSPI      VARCHAR(10)  NOT NULL
);

-- ------------------------------------------------------------
--  STG.HOSPITALISATION
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS STG.PUBLIC.HOSPITALISATION (
    ID_HOSPI          INTEGER,
    ID_CONSULT        INTEGER,
    NO_CHAMBRE        SMALLINT,
    TS_DEBUT_HOSPI    TIMESTAMP(0),
    TS_FIN_HOSPI      TIMESTAMP(0) NOT NULL,
    COUT_HOSPI        TIMESTAMP(0) NOT NULL,
    ID_PERSONNEL_RESP INTEGER
);

-- ------------------------------------------------------------
--  STG.MEDICAMENT
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS STG.PUBLIC.MEDICAMENT (
    CD_MEDICAMENT     VARCHAR(10),
    NOM_MEDICAMENT    VARCHAR(250) NOT NULL,
    CONDIT_MEDICAMENT VARCHAR(100) NOT NULL,
    CATG_MEDICAMENT   VARCHAR(100),
    MARQUE_FABRI      VARCHAR(100)
);
