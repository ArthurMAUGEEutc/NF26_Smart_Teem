{{ config(
    alias     = 'WRK_HOSP',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}

SELECT
    ID_HOSPI            AS HOSP_ID,
    ID_CONSULT          AS CONS_ID,
    NO_CHAMBRE          AS ROOM_NUM,
    TS_DEBUT_HOSPI      AS HOSP_STRT_DTTM,
    TS_FIN_HOSPI        AS HOSP_END_DTTM,
    COUT_HOSPI          AS HOSP_FINL_RATE,
    ID_PERSONNEL_RESP   AS STFF_ID
FROM STG.PUBLIC.HOSPITALISATION
