{{ config(
    alias      = 'O_ADDR',
    unique_key = ['PART_ID', 'STRT_VALD_DTTM'],
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}

SELECT
    p.PART_ID,
    w.STRT_NUM,
    w.STRT_DSC,
    w.COMP_STRT,
    w.POST_CD,
    w.CITY_NAME,
    w.CNTR_NAME,
    w.STRT_VALD_DTTM,
    w.END_VALD_DTTM,
    '{{ invocation_id }}' AS EXEC_ID
FROM {{ ref('wrk_address') }} w
JOIN {{ ref('soc_part') }} p
  ON p.SRC_ID  = w.SRC_ID
 AND p.SRC_TYP = 'Patient'

{% if is_incremental() %}
WHERE NOT EXISTS (
    SELECT 1 FROM {{ this }} s
    WHERE s.PART_ID        = p.PART_ID
      AND s.STRT_VALD_DTTM = w.STRT_VALD_DTTM
)
{% endif %}
