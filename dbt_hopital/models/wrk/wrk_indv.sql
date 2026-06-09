{{ config(
    alias     = 'WRK_INDV',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}
 
SELECT
    p.ID_PERSONNEL          AS SRC_ID,
    p.FONCTION_PERSONNEL    AS SRC_TYP,
    p.NOM_PERSONNEL         AS INDV_NAME,
    p.PRENOM_PERSONNEL      AS INDV_FIRS_NAME,
    p.CD_STATUT_PERSONNEL   AS INDV_STTS_CD,
    p.TS_CREATION_PERSONNEL AS CRTN_DTTM,
    p.TS_MAJ_PERSONNEL      AS UPDT_DTTM,
    NULL                    AS BIRT_DT,
    NULL                    AS BIRT_CITY,
    NULL                    AS BIRT_CNTR,
    NULL                    AS SOCL_NUM
FROM STG.PUBLIC.PERSONNEL p
 
UNION ALL
 
SELECT
    p.ID_PATIENT            AS SRC_ID,
    'Patient'               AS SRC_TYP,
    p.NOM_PATIENT           AS INDV_NAME,
    p.PRENOM_PATIENT        AS INDV_FIRS_NAME,
    'Actif'                 AS INDV_STTS_CD,
    p.TS_CREATION_PATIENT   AS CRTN_DTTM,
    p.TS_MAJ_PATIENT        AS UPDT_DTTM,
    p.DT_NAISS              AS BIRT_DT,
    p.VILLE_NAISS           AS BIRT_CITY,
    p.PAYS_NAISS            AS BIRT_CNTR,
    p.NUM_SECU              AS SOCL_NUM
FROM STG.PUBLIC.PATIENT p
