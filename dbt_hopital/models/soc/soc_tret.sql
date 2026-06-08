{{ config(
    alias      = 'O_TRET',
    unique_key = 'TRET_ID',
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}

SELECT
    w.TRET_ID,
    m.MEDC_ID,
    w.MEDC_QTY,
    w.DOSG_DSC,
    w.CONS_ID,
    w.TRET_CRTN_DTTM,
    '{{ invocation_id }}'   AS EXEC_ID
FROM {{ ref('wrk_tret') }} w
LEFT JOIN SOC.PUBLIC.R_MEDC m
       ON m.MEDC_CD   = w.MEDC_CD
      AND m.MEDC_CATG = w.MEDC_CATG
      AND m.MANF_BRND = w.MANF_BRND
