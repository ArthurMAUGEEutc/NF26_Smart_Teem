{{ config(
    alias      = 'O_CONS',
    unique_key = 'CONS_ID',
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}

SELECT
    w.CONS_ID,
    ps.PART_ID          AS STFF_ID,
    pp.PART_ID          AS PATN_ID,
    w.CONS_STRT_DTTM,
    w.CONS_END_DTTM,
    w.PATN_WEGH,
    w.PATN_TEMP,
    w.TEMP_UNIT,
    w.BLD_PRSS,
    w.PATH_DSC,
    w.DIBT_IND,
    w.TRET_ID,
    w.HOSP_IND,
    '{{ invocation_id }}' AS EXEC_ID
FROM {{ ref('wrk_consultation') }} w
JOIN {{ ref('soc_part') }} ps
  ON ps.SRC_ID  = w.STFF_SRC_ID
 AND ps.SRC_TYP != 'Patient'
JOIN {{ ref('soc_part') }} pp
  ON pp.SRC_ID  = w.PATN_SRC_ID
 AND pp.SRC_TYP = 'Patient'

{% if is_incremental() %}
WHERE w.CONS_ID NOT IN (SELECT CONS_ID FROM {{ this }})
{% endif %}
