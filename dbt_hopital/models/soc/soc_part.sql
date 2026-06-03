{{ config(
    alias      = 'R_PART',
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}

WITH existing_max AS (
    SELECT COALESCE(MAX(PART_ID), 0) AS max_id
    FROM SOC.PUBLIC.R_PART
),
new_rows AS (
    SELECT w.*
    FROM {{ ref('wrk_part') }} w
    WHERE NOT EXISTS (
        SELECT 1
        FROM {{ this }} s
        WHERE s.SRC_ID  = w.SRC_ID
        AND s.SRC_TYP = w.SRC_TYP
    )
)
SELECT
    m.max_id + ROW_NUMBER() OVER (ORDER BY n.SRC_TYP, n.SRC_ID)  AS PART_ID,
    n.SRC_ID,
    n.SRC_TYP
FROM new_rows n
CROSS JOIN existing_max m