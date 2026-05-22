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
        AND SEQ_TIME::timestamp_ntz::date >= '2025-12-17'
        AND LAST_CORRECTED_OR_CANCELLED_SEQ_NO IS NULL
    ORDER BY SEQ_TIME
),

exec_intra_ranked_filtered as (
    select
        *
    from
        exec_intra_ranked
    where
        rn=1
    ORDEr BY SEQ_TIME
),


base_tr as (
    SELECT
    convert_timezone('UTC','Europe/Berlin',SEQ_TIME::timestamp_ntz) AS SEQ_TIME_CEST,
    ISIN as INSTRUMENT_ID,
    IFF(SIDE='Sell',-1*QTY,QTY) AS QUANTITY_SIGNED
FROM 
    exec_intra_ranked_filtered 
),

dbt_trades AS (
    SELECT
        SEQ_TIME_CEST,
        INSTRUMENT_ID,
        SUM(QUANTITY_SIGNED)
            OVER (PARTITION BY INSTRUMENT_ID
            ORDER BY SEQ_TIME_CEST
            ROWS UNBOUNDED PRECEDING) AS RISK_QTY_DBT_EXPOSURES
    FROM
        TEAMS_PRD.RISK_FUNCTION_TRANSFORM.trf__risk_function_mrm_book_9800001601_intraday_trades
    WHERE
        INSTRUMENT_ID = 'US0231351067'
        AND SEQ_TIME_CEST::date >= '2025-12-17'
),

opening_pos AS (
    SELECT REALISED_POSITION AS opening_position
    FROM TEAMS_PRD.MM_MART.MRT__MM__POSITIONS
    WHERE ISIN = 'US0231351067'
      AND TRADING_ACCOUNT = 200
      AND SEQ_TIME::date >= '2025-12-17'
    ORDER BY SEQ_TIME
    LIMIT 1
),

base AS (
    SELECT
        a.SEQ_TIME_CEST AS SEQ_TIME,
        SUM(a.QUANTITY_SIGNED)
            OVER (PARTITION BY a.INSTRUMENT_ID
            ORDER BY a.SEQ_TIME_CEST
            ROWS UNBOUNDED PRECEDING) AS RISK_QTY_TRADES_EXPOSURE,
        b.QUANTITY_SIGNED_CUMULATIVE,
        d.RISK_QTY_DBT_EXPOSURES
    FROM base_tr AS a
    LEFT JOIN (
        SELECT
            SEQ_TIME_CEST,
            INSTRUMENT_ID,
            QUANTITY_SIGNED_CUMULATIVE
        FROM
            TEAMS_PRD.RISK_FUNCTION_TRANSFORM.trf__risk_function_mrm_book_9800001601_intraday_exposure
        WHERE
            INSTRUMENT_ID = 'US0231351067'
            AND SEQ_TIME_CEST::date >= '2025-12-17'
    ) b ON a.SEQ_TIME_CEST = b.SEQ_TIME_CEST AND a.INSTRUMENT_ID = b.INSTRUMENT_ID
    LEFT JOIN dbt_trades d ON a.SEQ_TIME_CEST = d.SEQ_TIME_CEST
)

SELECT
    b.SEQ_TIME::date AS DDATE,
    SUM(b.QUANTITY_SIGNED_CUMULATIVE)                             AS DBT_EXPOSURE_POSITION,
    SUM(o.opening_position + b.RISK_QTY_TRADES_EXPOSURE) AS RISK_TRADES_POSITION,
    SUM(o.opening_position + b.RISK_QTY_DBT_EXPOSURES)   AS RISK_DBT_POSITION
FROM base b
CROSS JOIN opening_pos o
GROUP BY 1
ORDER BY DDATE;



SELECT
*
from
    BACKEND_PRD.TROMSO.hourly_executions_v0_4 as e
LIMIT 1;