{{ config(
    alias     = 'WRK_MEDC',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}
 
SELECT DISTINCT
    CD_MEDICAMENT       AS MEDC_CD,
    NOM_MEDICAMENT      AS MEDC_NAME,
    CONDIT_MEDICAMENT   AS MEDC_COND,
    CATG_MEDICAMENT     AS MEDC_CATG,
    MARQUE_FABRI        AS MANF_BRND
FROM STG.PUBLIC.MEDICAMENT