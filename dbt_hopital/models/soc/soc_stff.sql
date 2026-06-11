{{ config(
    alias      = 'O_STFF',
    unique_key = 'PART_ID',
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}

SELECT
    rp.PART_ID,
    w.WORK_STRT_DTTM,
    w.WORK_END_DTTM,
    w.WORK_END_RESN,
    '{{ invocation_id }}'   AS EXEC_ID
FROM {{ ref('wrk_stff') }} w
INNER JOIN {{ ref('soc_part') }} rp
    ON  rp.SRC_ID  = w.SRC_ID
    AND rp.SRC_TYP = w.SRC_TYP
