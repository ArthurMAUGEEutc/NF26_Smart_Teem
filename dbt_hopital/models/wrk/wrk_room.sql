{{ config(
    alias     = 'WRK_ROOM',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}
 
SELECT
    NO_CHAMBRE      AS ROOM_NUM,
    NOM_CHAMBRE     AS ROOM_NAME,
    NO_ETAGE        AS FLOR_NUM,
    NOM_BATIMENT    AS BULD_NAME,
    TYPE_CHAMBRE    AS ROOM_TYP,
    PRIX_JOUR       AS ROOM_DAY_RATE,
    DT_CREATION     AS CRTN_DT
FROM STG.PUBLIC.CHAMBRE