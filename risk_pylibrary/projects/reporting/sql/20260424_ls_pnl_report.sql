with pos as (
    SELECT
        INSTRUMENT_ID,
        QUANTITY,
        MKT_MID_EUR
    FROM
        TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation
),

rpnl as (
        SELECT
            INSTRUMENT_ID,
            SUM(
                CASE
                    WHEN  THEN RPNL
                    WHEN <condition_2> THEN RPNL
                    ELSE 0
                END
            ) AS RPNL
        FROM
            TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__MRM_TRADING_BOOK_PNL
        WHERE
            REPORT_DATE::date >= '2024-10-01' AND REPORT_DATE::date <= '2025-09-30'
            AND SEC_ACC_NO IN (<values>)
            AND DATA_SRC_PRIMARY IN (<values>)
        GROUP BY
            INSTRUMENT_ID
)

SELECT
    INSTRUMENT_ID,
    SUM(QUANTITY),
    SUM(MKT_MID_EUR)
FROM
    pos
WHERE
    QUANTITY <> 0
GROUP BY 1;