WITH deduped AS (
    SELECT *
    FROM backend_prd.private_markets.public_trade
    WHERE "executed_at" IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY "trade_id" ORDER BY "executed_at" DESC) = 1
)
SELECT
    "executed_at"::date,
    --"block_order_id",
    "instrument_id",
    "execution_price" AS price,
    SUM("execution_size") AS quantity,
    SUM(IFF("type"='BUY', "execution_size", -1*"execution_size")) AS quantity_signed,
    SUM(CASE WHEN "type"='BUY' THEN "execution_size" ELSE 0 END) AS quantity_signed_buy,
    SUM(CASE WHEN "type"='SELL' THEN -1*"execution_size" ELSE 0 END) AS quantity_signed_sell
FROM deduped
WHERE
"instrument_id"='LU3170240538'
GROUP BY 1, 2, 3
ORDER BY 1 DESC;


WITH deduped AS (
    SELECT *
    FROM backend_prd.private_markets.public_order
    WHERE "executed_at" IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY "parent_order_id" ORDER BY "executed_at" DESC) = 1
)
SELECT
    "executed_at",
    "block_order_id",
    "instrument_id",
    "executed_price" AS price,
    SUM("executed_size") AS quantity,
    SUM(IFF("type"='BUY', "executed_size", -1*"executed_size")) AS quantity_signed
FROM deduped
WHERE
"instrument_id"='LU3170240538'
--AND
--"status"='EXECUTED'
AND
"decision_by_type" IS NOT NULL
--AND
--"failure_reason" IS NULL
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC;


SELECT 
    po.*,
    IFF("type"='BUY', "executed_size", -1*"executed_size") AS executed_size_signed
FROM backend_prd.private_markets.public_order as po
WHERE
"block_order_id"='17b81736-9b31-4b01-8d30-3a98d785e028';


SELECT *
FROM backend_prd.private_markets.public_order
LIMIT 1;


SELECT
*
FROM
backend_prd.private_markets.public_trade
WHERE
"executed_at"::date = '2025-08-29'
QUALIFY ROW_NUMBER() OVER (PARTITION BY "trade_id" ORDER BY "executed_at" DESC) = 1;


select 
count(*) over (partition by surrogate_key) as cnt, *
from 
--ZZCLONE_FB_PRD_ZZ_TEAMS_PRD.risk_function_transform.trf__risk_function_mrm_book_9800005401_daily_exposures
teams_prd.risk_function_transform.trf__risk_function_mrm_book_total_exposures
--teams_prd.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation--trf__risk_function_mrm_book_9800005401_daily_exposures
order by cnt desc, surrogate_key;

SELECT
MAX(SEQ_DATE)
FROM
BACKEND_PRD.FXMM.POSITIONS_V0_1;

SELECT
MIN(SEQ_TIME)
FROM
BACKEND_PRD.FXMM.POSITIONS_V0_2
WHERE
SEQ_DATE = (SELECT MIN(SEQ_DATE) FROM BACKEND_PRD.FXMM.POSITIONS_V0_2);


SELECT
MAX(SEQ_TIME)
FROM
BACKEND_PRD.FXMM.POSITIONS_V0_1
WHERE
SEQ_DATE = (SELECT MAX(SEQ_DATE) FROM BACKEND_PRD.FXMM.POSITIONS_V0_1);

SELECT
*
FROM
backend_prd.private_markets.public_order
WHERE
"failure_reason" IS NOT NULL;


SELECT
*
FROM
backend_prd.private_markets.public_trade
LIMIT 1;


select
pos.extraction_timestamp,                               -- keep for QUALIFY ordering
pos.extraction_timestamp::date as report_date,
pos.instrument_id,
coalesce(pos.gross_long, 0) - coalesce(pos.gross_short, 0) as quantity
from TEAMS_PRD.source_portfolio.src__dim__portfolio__position pos
where pos.sec_acc_no = 9800001301;

SELECT
MIN("extraction_timestamp")
FROM
BACKEND_PRD.portfolio.anonymized_position
LIMIT 1;



with src as (
  select
    pos.extraction_timestamp,                               -- keep for QUALIFY ordering
    pos.extraction_timestamp::date as report_date,
    pos.instrument_id,
    coalesce(pos.gross_long, 0) - coalesce(pos.gross_short, 0) as quantity
  from TEAMS_PRD.source_portfolio.src__dim__portfolio__position pos
  where pos.sec_acc_no = 9800001301
    and pos.extraction_timestamp::date >= ml.min_dt
    and pos.extraction_timestamp::date <= current_date() - 1 -- skip today's partials
),

-- pick the latest snapshot per (date, instrument)
positions as (
  select
    report_date,
    instrument_id,
    quantity
  from src
  qualify row_number()
           over (partition by report_date, instrument_id
                 order by extraction_timestamp desc) = 1
)

select
  p.report_date,
  '9800001301' as sec_acc_no,
  p.instrument_id,
  p.quantity,
  'ptf_src' as data_src_primary,
  concat(
    'trad-',
    to_char(p.report_date, 'yyyymmdd'),
    '-9800001301-ptf_src-',
    coalesce(to_varchar(p.instrument_id), '')
  ) as surrogate_key
from positions p;

SELECT
REPORT_DATE::date as report_date,
9800001301 as sec_acc_no,
instrument_id,
price,
quantity,
(price*quantity) as mkt_mid_eur
FROM
TEAMS_PRD.RISK_DATA.MR_PORT_POS
WHERE
REPORT_DATE::date='2022-09-30';


SELECT
    inq.TIMESTAMP,
    date_trunc('seconds',convert_timezone('UTC','Europe/London',TO_TIMESTAMP(inq.TIMESTAMP/1e9))) AS inq_seq_time,
    inq.source,
    inq.isin as inq_instrument_id,
    p.instrument_id as intra_instrument_id,
    IFF(inq.NOTIONAL<0,'Sell','Buy') AS inq_side,
    p.intra_side,
    inq.NOTIONAL AS inq_qty_ccy,
    inq.VOLUME AS inq_qty_eur,
    p.intra_qty,                         
    inq.PRICE AS inq_price,
    1/p.intra_price                        
FROM
    TIBERIUS_PRD.TRADING_PLATFORM_EXTERNAL_SOURCES.fxmm_inquisitor_enriched_trades AS inq
LEFT JOIN 
    (SELECT
        date_trunc('seconds',SEQ_TIME) AS intra_seq_date,
        isin as instrument_id,
        SIDE AS intra_side,
        QTY AS intra_qty,
        PRICE AS intra_price
    FROM
        BACKEND_PRD.FXMM.hourly_executions_v0_4
    WHERE
        TRADING_ACCOUNT = 1200
        AND SEQ_DATE = '2025-11-15'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY SEQ_NO ORDER BY SEQ_TIME DESC) = 1
    ORDER BY SEQ_TIME) AS p
ON p.intra_seq_date = date_trunc('seconds',convert_timezone('UTC','Europe/London',TO_TIMESTAMP(inq.TIMESTAMP/1e9)))
WHERE
    inq.DAY_PART = '2025-11-15'
    AND inq.SOURCE <> 'SYNTHETIC'
    AND inq.TRADINGACCOUNT = 1200
ORDER BY 1;


SELECT
    SEQ_TIME AS intra_seq_date,
    SIDE AS intra_side,
    QTY AS intra_qty,
    PRICE AS intra_price
FROM
    BACKEND_PRD.FXMM.hourly_executions_v0_4
WHERE
    TRADING_ACCOUNT = 1200
    AND SEQ_DATE = '2025-11-15'
QUALIFY ROW_NUMBER() OVER (PARTITION BY SEQ_NO ORDER BY SEQ_TIME DESC) = 1
ORDER BY SEQ_TIME;


SELECT
    convert_timezone('UTC','Europe/London',TO_TIMESTAMP(inq.TIMESTAMP/1e9))
FROM
    TIBERIUS_PRD.TRADING_PLATFORM_EXTERNAL_SOURCES.fxmm_inquisitor_enriched_trades AS inq
WHERE
    inq.DAY_PART = '2025-11-15'
    AND inq.SOURCE <> 'SYNTHETIC'
    AND inq.TRADINGACCOUNT = 1200
ORDER BY 1;

SELECT
*
FROM
    BACKEND_PRD.FXMM.hourly_executions_v0_4
LIMIT 1;


SELECT
    *
FROM
    TIBERIUS_PRD.TRADING_PLATFORM_EXTERNAL_SOURCES.fxmm_inquisitor_enriched_trades
LIMIT 1;