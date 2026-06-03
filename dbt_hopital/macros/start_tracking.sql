{% macro start_tracking(model_name) %}

    -- Insertion dans T_SUIV_RUN (si pas déjà fait pour ce run)
    INSERT INTO TCH.PUBLIC.T_SUIV_RUN (
        EXEC_ID,
        RUN_STRT_DTTM,
        RUN_STTS_CD
    )
    SELECT
        '{{ invocation_id }}',
        CURRENT_TIMESTAMP(),
        'ENC'
    WHERE NOT EXISTS (
        SELECT 1
        FROM TCH.PUBLIC.T_SUIV_RUN
        WHERE EXEC_ID = '{{ invocation_id }}'
    );

    -- Insertion dans T_SUIV_TRMT pour ce model
    INSERT INTO TCH.PUBLIC.T_SUIV_TRMT (
        EXEC_ID,
        SCRPT_NAME,
        EXEC_STRT_DTTM,
        EXEC_STTS_CD
    )
    VALUES (
        '{{ invocation_id }}',
        '{{ model_name }}',
        CURRENT_TIMESTAMP(),
        'ENC'
    );

{% endmacro %}