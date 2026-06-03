{# ============================================================
   Macros de suivi d'exécution — base TCH

   Principe :
     - Un EXEC_ID (UUID) est généré par model en variable de session
       Snowflake ($NF26_EXEC_ID), ce qui le rend disponible dans
       tous les hooks du même model sans le passer en paramètre.
     - Les pre-hooks insèrent une ligne ENC dans T_SUIV_RUN et
       T_SUIV_TRMT.
     - Les post-hooks mettent à jour le statut (OK ou KO) et
       l'heure de fin.

   Utilisation dans dbt_project.yml :
     pre-hook:
       - "{{ suivi_set_exec_id() }}"
       - "{{ suivi_insert_run() }}"
       - "{{ suivi_insert_trmt() }}"
     post-hook:
       - "{{ suivi_fin_trmt('OK') }}"
       - "{{ suivi_fin_run('OK') }}"
   ============================================================ #}


{# Génère un UUID unique pour ce model et le stocke en session #}
{% macro suivi_set_exec_id() %}
    SET NF26_EXEC_ID = UUID_STRING()
{% endmacro %}


{# Ouvre un run dans T_SUIV_RUN #}
{% macro suivi_insert_run() %}
    INSERT INTO TCH.PUBLIC.T_SUIV_RUN (EXEC_ID, RUN_STRT_DTTM, RUN_STTS_CD)
    VALUES ($NF26_EXEC_ID, CURRENT_TIMESTAMP, 'ENC')
{% endmacro %}


{# Ouvre un traitement dans T_SUIV_TRMT — model.name = nom du fichier .sql #}
{% macro suivi_insert_trmt() %}
    INSERT INTO TCH.PUBLIC.T_SUIV_TRMT (EXEC_ID, SCRPT_NAME, EXEC_STRT_DTTM, EXEC_STTS_CD)
    VALUES ($NF26_EXEC_ID, '{{ model.name }}', CURRENT_TIMESTAMP, 'ENC')
{% endmacro %}


{# Clôture le traitement dans T_SUIV_TRMT (statut : 'OK' ou 'KO') #}
{% macro suivi_fin_trmt(statut) %}
    UPDATE TCH.PUBLIC.T_SUIV_TRMT
    SET    EXEC_END_DTTM = CURRENT_TIMESTAMP,
           EXEC_STTS_CD  = '{{ statut }}'
    WHERE  EXEC_ID = $NF26_EXEC_ID
{% endmacro %}


{# Clôture le run dans T_SUIV_RUN (statut : 'OK' ou 'KO') #}
{% macro suivi_fin_run(statut) %}
    UPDATE TCH.PUBLIC.T_SUIV_RUN
    SET    RUN_END_DTTM = CURRENT_TIMESTAMP,
           RUN_STTS_CD  = '{{ statut }}'
    WHERE  EXEC_ID = $NF26_EXEC_ID
{% endmacro %}
