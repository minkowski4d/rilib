
-- Get Intra Day Executions
with exec_intra_ranked as (
    select
        e.*,
        ROW_NUMBER() OVER (
            PARTITION BY TRADING_ACCOUNT, ISIN, EXEC_ID
            ORDER BY SEQ_TIME DESC, SEQ_NO DESC
        ) AS rn
    from
        BACKEND_PRD.MM.hourly_executions_v0_4 as e
    where
        1 = 1
        AND TRADING_ACCOUNT = 200
        AND ISIN = 'US0231351067'
        AND SEQ_TIME::timestamp_ntz::date = '2025-12-17'
        AND LAST_CORRECTED_OR_CANCELLED_SEQ_NO IS NULL
    ORDER BY SEQ_TIME
),

exec_intra_ranked_filtered as (
    select
        *
    from
        exec_intra_ranked
    where
        rn=1)

SELECt 
    convert_timezone('UTC','Europe/Berlin',SEQ_TIME::timestamp_ntz) AS SEQ_TIME_CEST,
    ISIN,
    IFF(SIDE='Sell',-1*QTY,QTY) AS QUANTITY_SIGNED
FROM 
    exec_intra_ranked_filtered 
ORDER BY SEQ_TIME;


SELECT
    SEQ_TIME,
    REALISED_POSITION
FROM
    TEAMS_PRD.MM_MART.MRT__MM__POSITIONS
WHERE
    ISIN = 'US0231351067'
    AND TRADING_ACCOUNT = 200
    AND SEQ_TIME::date = '2025-12-17'
ORDER BY SEQ_TIME;


SELECT
    TO_TIMESTAMP(CLOSETIMESTAMP/1e9)::DATE AS ddate,
    ISIN AS symbol,
    CLOSEPRICE * EURRATE AS price
FROM TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_msl_prices_tib_strat
WHERE CLOSEPRICE IS NOT NULL
    AND EURRATE IS NOT NULL
    AND CLOSESIZE <> 0
    AND TO_TIMESTAMP(CLOSETIMESTAMP/1e9)::DATE BETWEEN %(start)s AND %(end)s
QUALIFY ROW_NUMBER() OVER (PARTITION BY TO_TIMESTAMP(CLOSETIMESTAMP/1e9)::DATE, ISIN ORDER BY CLOSESIZE DESC) = 1
ORDER BY 1,2;


SELECT
MAX(TO_TIMESTAMP(CLOSETIMESTAMP/1e9)::DATE)
FROM TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_msl_prices_tib_strat;


