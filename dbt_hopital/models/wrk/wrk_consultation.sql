{{ config(
    alias     = 'WRK_CONS',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}

SELECT
    ID_CONSULT                                          AS CONS_ID,
    ID_PERSONNEL                                        AS STFF_SRC_ID,
    ID_PATIENT                                          AS PATN_SRC_ID,
    TS_DEBUT_CONSULT                                    AS CONS_STRT_DTTM,
    TS_FIN_CONSULT                                      AS CONS_END_DTTM,
    POIDS_PATIENT                                       AS PATN_WEGH,
    TEMP_PATIENT                                        AS PATN_TEMP,
    UNIT_TEMP                                           AS TEMP_UNIT,
    TENSION_PATIENT                                     AS BLD_PRSS,
    DSC_PATHO                                           AS PATH_DSC,
    CASE WHEN INDIC_DIABETE = 'OUI' THEN 1 ELSE 0 END  AS DIBT_IND,
    ID_TRAITEMENT                                       AS TRET_ID,
    CASE WHEN INDIC_HOSPI   = 'OUI' THEN 1 ELSE 0 END  AS HOSP_IND
FROM STG.PUBLIC.CONSULTATION
