{{ config(
    alias      = 'O_HOSP',
    unique_key = 'HOSP_ID',
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}

SELECT
    w.HOSP_ID,
    w.CONS_ID,
    w.ROOM_NUM,
    w.HOSP_STRT_DTTM,
    w.HOSP_END_DTTM,
    w.HOSP_FINL_RATE,
    w.STFF_ID,
    '{{ invocation_id }}' AS EXEC_ID
FROM {{ ref('wrk_hospitalization') }} w

{% if is_incremental() %}
WHERE w.HOSP_ID NOT IN (SELECT HOSP_ID FROM {{ this }})
{% endif %}
