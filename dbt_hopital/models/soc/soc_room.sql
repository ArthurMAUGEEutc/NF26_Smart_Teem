{{ config(
    alias      = 'R_ROOM',
    unique_key = 'ROOM_NUM',
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}
 
SELECT
    w.ROOM_NUM,
    w.ROOM_NAME,
    w.FLOR_NUM,
    w.BULD_NAME,
    w.ROOM_TYP,
    w.ROOM_DAY_RATE,
    w.CRTN_DT,
    '{{ invocation_id }}'   AS EXEC_ID
FROM {{ ref('wrk_room') }} w