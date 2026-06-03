{{ config(
    alias     = 'WRK_PART',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}
 
SELECT DISTINCT
    ID_PERSONNEL        AS SRC_ID,
    FONCTION_PERSONNEL  AS SRC_TYP
FROM STG.PUBLIC.PERSONNEL
 
UNION
 
SELECT DISTINCT
    ID_PATIENT          AS SRC_ID,
    'Patient'           AS SRC_TYP
FROM STG.PUBLIC.PATIENT
 