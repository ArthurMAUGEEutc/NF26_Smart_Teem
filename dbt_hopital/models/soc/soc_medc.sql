{{ config(
    alias      = 'R_MEDC',
    pre_hook   = "{{ start_tracking(this.name) }}",
    post_hook  = "{{ end_tracking(this.name) }}"
) }}

WITH existing_max AS (
    SELECT COALESCE(MAX(MEDC_ID), 0) AS max_id
    FROM SOC.PUBLIC.R_MEDC
),
new_rows AS (
    SELECT w.*
    FROM {{ ref('wrk_medc') }} w
    WHERE NOT EXISTS (
        SELECT 1
        FROM {{ this }} s -- this : variable dbt qui référence la table courante
        WHERE s.MEDC_CD = w.MEDC_CD
          AND s.MEDC_CATG = w.MEDC_CATG
          AND s.MANF_BRND = w.MANF_BRND
    )
)
SELECT
    m.max_id + ROW_NUMBER() OVER (ORDER BY n.MEDC_CD, n.MEDC_CATG, n.MANF_BRND) AS MEDC_ID,
    n.MEDC_CD,
    n.MEDC_NAME,
    n.MEDC_COND,
    n.MEDC_CATG,
    n.MANF_BRND,
    '{{ invocation_id }}' AS EXEC_ID
FROM new_rows n
CROSS JOIN existing_max m