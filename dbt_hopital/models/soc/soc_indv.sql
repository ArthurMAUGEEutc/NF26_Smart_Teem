{{ config(
    alias      = 'O_INDV',
    unique_key = 'PART_ID',
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}
 
-- Jointure avec R_PART pour récupérer le PART_ID
-- PERSONNEL : jointure sur SRC_ID = ID_PERSONNEL et SRC_TYP = FONCTION_PERSONNEL
-- PATIENT : jointure sur SRC_ID = ID_PATIENT  et SRC_TYP = 'Patient'
SELECT
    rp.PART_ID,
    w.INDV_NAME,
    w.INDV_FIRS_NAME,
    w.INDV_STTS_CD,
    w.CRTN_DTTM,
    w.UPDT_DTTM,
    w.BIRT_DT,
    w.BIRT_CITY,
    w.BIRT_CNTR,
    w.SOCL_NUM,
    '{{ invocation_id }}'   AS EXEC_ID
FROM {{ ref('wrk_indv') }} w
INNER JOIN SOC.PUBLIC.R_PART rp
    ON  rp.SRC_ID  = w.SRC_ID
    AND rp.SRC_TYP = w.SRC_TYP