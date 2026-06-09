{{ config(
    alias     = 'O_TELP',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}

SELECT
    p.PART_ID,
    w.CNTR_IND,
    w.TELP_NUM,
    w.STRT_VALD_DTTM,
    w.END_VALD_DTTM,
    '{{ invocation_id }}' AS EXEC_ID
FROM {{ ref('wrk_telephone') }} w
JOIN SOC.PUBLIC.R_PART p
  ON p.SRC_ID  = w.PATN_SRC_ID
 AND p.SRC_TYP = 'Patient'

{% if is_incremental() %}
WHERE NOT EXISTS (
    SELECT 1
    FROM {{ this }} t
    WHERE t.PART_ID       = p.PART_ID
      AND t.STRT_VALD_DTTM = w.STRT_VALD_DTTM
)
{% endif %}