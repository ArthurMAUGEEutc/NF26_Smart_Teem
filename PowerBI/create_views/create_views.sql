-- Création des vues pour export des données branchées ensuite sur PowerBI
-- Les vues ne contiennent pas de filtre de date car le filtrage est géré côté Power BI via des slicers.

USE ROLE ACCOUNTADMIN;
USE DATABASE SOC;
USE SCHEMA PUBLIC;

-- VUE 1 : Âge moyen des patients par pathologie et par période
-- KPI : "Quel a été l'âge moyen des patients qui ont eu une certaine Pathologie durant une certaine période ?"

CREATE OR REPLACE VIEW SOC.PUBLIC.V_KPI_AGE_MOYEN_PATHO AS
SELECT
    c.CONS_ID,
    c.PATH_DSC AS PATHOLOGIE,
    c.CONS_STRT_DTTM AS DATE_CONSULTATION,
    i.PART_ID AS PATIENT_ID,
    i.INDV_NAME AS NOM_PATIENT,
    i.INDV_FIRS_NAME AS PRENOM_PATIENT,
    i.BIRT_DT AS DATE_NAISSANCE,
    DATEDIFF('year', i.BIRT_DT, c.CONS_STRT_DTTM) AS AGE_A_CONSULTATION
FROM SOC.PUBLIC.O_CONS c
JOIN SOC.PUBLIC.O_INDV i ON c.PATN_ID = i.PART_ID
WHERE c.PATH_DSC IS NOT NULL
  AND i.BIRT_DT  IS NOT NULL;

-- VUE 2 : Médicament le plus prescrit par pathologie et période
-- KPI : "Quel Médicament a été le plus prescrit (en terme de quantité) pour une 
-- certaine Pathologie durant une certaine période ?"

CREATE OR REPLACE VIEW SOC.PUBLIC.V_KPI_MEDIC_PRESCRIT_PATHO AS
SELECT
    c.CONS_ID,
    c.PATH_DSC AS PATHOLOGIE,
    c.CONS_STRT_DTTM AS DATE_CONSULTATION,
    t.TRET_ID,
    m.MEDC_ID,
    m.MEDC_NAME AS NOM_MEDICAMENT,
    m.MEDC_CATG AS CATEGORIE_MEDICAMENT,
    t.MEDC_QTY AS QUANTITE
FROM SOC.PUBLIC.O_CONS c
JOIN SOC.PUBLIC.O_TRET t  ON c.TRET_ID  = t.TRET_ID
JOIN SOC.PUBLIC.R_MEDC m  ON t.MEDC_ID  = m.MEDC_ID
WHERE c.PATH_DSC IS NOT NULL
  AND t.MEDC_QTY IS NOT NULL;

-- VUE 3 : Chambres ayant accueilli des patients par pathologie
-- KPI : "Combien de chambres ont accueilli des patients diagnostiqués d'une 
-- certaine Pathologie durant une certaine période ?"

CREATE OR REPLACE VIEW SOC.PUBLIC.V_KPI_CHAMBRES_PATHO AS
SELECT
    c.CONS_ID,
    c.PATH_DSC AS PATHOLOGIE,
    c.CONS_STRT_DTTM AS DATE_CONSULTATION,
    h.HOSP_ID,
    h.HOSP_STRT_DTTM AS DEBUT_HOSPI,
    h.HOSP_END_DTTM AS FIN_HOSPI,
    r.ROOM_NUM,
    r.ROOM_NAME,
    r.FLOR_NUM,
    r.BULD_NAME,
    r.ROOM_TYP
FROM SOC.PUBLIC.O_CONS c
JOIN SOC.PUBLIC.O_HOSP h  ON c.CONS_ID  = h.CONS_ID
JOIN SOC.PUBLIC.R_ROOM r  ON h.ROOM_NUM = r.ROOM_NUM
WHERE c.PATH_DSC IS NOT NULL;


-- VUE 4 : Proportion de médecins par spécialité ayant diagnostiqué une pathologie
-- KPI : "Quelle est la proportion de médecins (par spécialité) qui ont diagnostiqué une 
-- certaine Pathologie durant une certaine période ?"

CREATE OR REPLACE VIEW SOC.PUBLIC.V_KPI_MEDECINS_PATHO AS
SELECT
    c.CONS_ID,
    c.PATH_DSC AS PATHOLOGIE,
    c.CONS_STRT_DTTM AS DATE_CONSULTATION,
    i.PART_ID AS MEDECIN_ID,
    i.INDV_NAME AS NOM_MEDECIN,
    i.INDV_FIRS_NAME AS PRENOM_MEDECIN,
    p.SRC_TYP AS SPECIALITE
FROM SOC.PUBLIC.O_CONS c
JOIN SOC.PUBLIC.O_INDV i ON c.STFF_ID = i.PART_ID
JOIN SOC.PUBLIC.R_PART p ON p.PART_ID = i.PART_ID
WHERE c.PATH_DSC IS NOT NULL;


-- VUE 5 : Proportion de patients hospitalisés au moins une nuit
-- KPI : "Quelle est la proportion de patients hospitalisés qui sont restés au moins 
-- une nuit durant une certaine période ?"

CREATE OR REPLACE VIEW SOC.PUBLIC.V_KPI_HOSPI_AU_MOINS_UNE_NUIT AS
SELECT
    h.HOSP_ID,
    h.CONS_ID,
    h.ROOM_NUM,
    h.HOSP_STRT_DTTM AS DEBUT_HOSPI,
    h.HOSP_END_DTTM AS FIN_HOSPI,
    DATEDIFF('hour', h.HOSP_STRT_DTTM, h.HOSP_END_DTTM) AS DUREE_HEURES,
    CASE
        WHEN DATEDIFF('hour', h.HOSP_STRT_DTTM, h.HOSP_END_DTTM) >= 24
        THEN 1
        ELSE 0
    END AS INDIC_AU_MOINS_UNE_NUIT
FROM SOC.PUBLIC.O_HOSP h;

-- VUE 6 : Chambres non occupées sur une période
-- KPI : "Combien de chambres n'ont pas été occupées durant une certaine période ?"

-- Toutes les chambres (pour le total)
CREATE OR REPLACE VIEW SOC.PUBLIC.V_KPI_TOUTES_CHAMBRES AS
SELECT
    ROOM_NUM,
    ROOM_NAME,
    FLOR_NUM,
    BULD_NAME,
    ROOM_TYP
FROM SOC.PUBLIC.R_ROOM;

-- Chambres avec leurs hospitalisations (pour les occupées)
CREATE OR REPLACE VIEW SOC.PUBLIC.V_KPI_CHAMBRES_OCCUPEES AS
SELECT
    r.ROOM_NUM,
    r.ROOM_NAME,
    r.FLOR_NUM,
    r.BULD_NAME,
    r.ROOM_TYP,
    h.HOSP_ID,
    h.HOSP_STRT_DTTM,
    h.HOSP_END_DTTM
FROM SOC.PUBLIC.R_ROOM r
JOIN SOC.PUBLIC.O_HOSP h ON r.ROOM_NUM = h.ROOM_NUM;