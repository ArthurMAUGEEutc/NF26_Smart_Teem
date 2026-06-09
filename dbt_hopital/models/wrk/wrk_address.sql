{{ config(
    alias     = 'WRK_ADDR',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}

SELECT
    ID_PATIENT              AS SRC_ID,
    NUM_VOIE                AS STRT_NUM,
    DSC_VOIE                AS STRT_DSC,
    CMPL_VOIE               AS COMP_STRT,
    CD_POSTAL               AS POST_CD,
    VILLE                   AS CITY_NAME,
    PAYS                    AS CNTR_NAME,
    TS_CREATION_PATIENT     AS STRT_VALD_DTTM,
    '9999-12-31 23:59:59'::TIMESTAMP AS END_VALD_DTTM
FROM STG.PUBLIC.PATIENT
WHERE NUM_VOIE IS NOT NULL
