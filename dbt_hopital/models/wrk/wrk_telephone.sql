{{ config(
    alias     = 'WRK_TELP',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}

SELECT
    ID_PATIENT AS PATN_SRC_ID,
    IND_PAYS_NUM_TELP AS CNTR_IND,
    NUM_TELEPHONE AS TELP_NUM,
    TS_CREATION_PATIENT AS STRT_VALD_DTTM,
    TS_MAJ_PATIENT AS END_VALD_DTTM
FROM STG.PUBLIC.PATIENT
WHERE NUM_TELEPHONE IS NOT NULL