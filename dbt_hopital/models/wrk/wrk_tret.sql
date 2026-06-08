{{ config(
    alias     = 'WRK_TRET',
    pre_hook  = "{{ start_tracking(this.name) }}",
    post_hook = "{{ end_tracking(this.name) }}"
) }}

SELECT
    ID_TRAITEMENT           AS TRET_ID,
    CD_MEDICAMENT           AS MEDC_CD,
    CATG_MEDICAMENT         AS MEDC_CATG,
    MARQUE_FABRI            AS MANF_BRND,
    QTE_MEDICAMENT          AS MEDC_QTY,
    DSC_POSOLOGIE           AS DOSG_DSC,
    ID_CONSULT              AS CONS_ID,
    TS_CREATION_TRAITEMENT  AS TRET_CRTN_DTTM
FROM STG.PUBLIC.TRAITEMENT
