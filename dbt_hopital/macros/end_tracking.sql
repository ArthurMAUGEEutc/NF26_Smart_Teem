{% macro end_tracking(model_name, status='OK') %}

    UPDATE TCH.PUBLIC.T_SUIV_TRMT
    SET
        EXEC_END_DTTM  = CURRENT_TIMESTAMP(),
        EXEC_STTS_CD   = '{{ status }}'
    WHERE EXEC_ID    = '{{ invocation_id }}'
      AND SCRPT_NAME = '{{ model_name }}';

    -- RUN_STTS_CD = KO si au moins un traitement du run est en échec
    UPDATE TCH.PUBLIC.T_SUIV_RUN
    SET
        RUN_END_DTTM = CURRENT_TIMESTAMP(),
        RUN_STTS_CD  = CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM TCH.PUBLIC.T_SUIV_TRMT
                                WHERE EXEC_ID      = '{{ invocation_id }}'
                                  AND EXEC_STTS_CD = 'KO'
                            ) THEN 'KO'
                            ELSE '{{ status }}'
                       END
    WHERE EXEC_ID = '{{ invocation_id }}';

{% endmacro %}