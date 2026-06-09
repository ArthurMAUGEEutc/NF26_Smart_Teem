{{ config(
    alias     = 'WRK_STFF',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}

SELECT
    p.ID_PERSONNEL          AS SRC_ID,
    p.FONCTION_PERSONNEL    AS SRC_TYP,
    p.TS_DEBUT_ACTIVITE     AS WORK_STRT_DTTM,
    p.TS_FIN_ACTIVITE       AS WORK_END_DTTM,
    p.RAISON_FIN_ACTIVITE   AS WORK_END_RESN
FROM STG.PUBLIC.PERSONNEL p
