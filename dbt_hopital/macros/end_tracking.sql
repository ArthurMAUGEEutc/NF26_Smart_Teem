{% macro end_tracking(model_name, status='OK') %}

    -- Mise à jour de T_SUIV_TRMT pour ce model
    UPDATE TCH.PUBLIC.T_SUIV_TRMT
    SET
        EXEC_END_DTTM  = CURRENT_TIMESTAMP(),
        EXEC_STTS_CD   = '{{ status }}'
    WHERE EXEC_ID    = '{{ invocation_id }}'
      AND SCRPT_NAME = '{{ model_name }}';

    -- Mise à jour de T_SUIV_RUN
    -- On marque OK seulement si tous les traitements du run sont OK
    -- Sinon on marque KO
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