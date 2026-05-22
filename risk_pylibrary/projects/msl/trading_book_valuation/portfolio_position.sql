-- Step 1: Generate Date Range
WITH start_date AS (
SELECT 
    MIN(convert_timezone('Europe/Berlin', sb_trade.booked_ts)::timestamp_ntz::date) AS sdate
from
    teams_prd.asset_hub.pbl_curr__share_booking as sb_trade
where
sb_trade.securities_account_number = 9800003301  
),


date_range AS (
SELECT (SELECT sdate FROM start_date) AS date_column
    UNION ALL
SELECT DATEADD(DAY, 1, date_column)
    FROM date_range
WHERE DATEADD(DAY, 1, date_column) <= CURRENT_DATE()-1
),

data_table as (
SELECT 
    date_column as report_date,
FROM date_range
WHERE DAYOFWEEK(date_column) NOT IN (0,6)
),

trades as (
    select
        convert_timezone('Europe/Berlin', sb_trade.booked_ts)::timestamp_ntz as trade_ts,
        sb_trade.instrument_id as instrument_id,
        iff(sb_trade.booking_direction = 'DEBIT', -1 * sb_trade.net_size, sb_trade.net_size) as quantity
    from
        teams_prd.asset_hub.pbl_curr__share_booking as sb_trade
    where
        convert_timezone('Europe/Berlin', sb_trade.booked_ts)::date between '2024-01-01' and current_date() - 1
        and sb_trade.securities_account_number = 9800003301
),

tr_grouped as (
    select
        tr.trade_ts::date as report_date,
        tr.instrument_id as instrument_id,
        sum(tr.quantity) as quantity
    from
        trades as tr
    group by all
),

final_positions as (
    select
        tr_grp.report_date as report_date,
        '9800003601' as sec_acc_no,
        tr_grp.instrument_id as instrument_id,
        sum(tr_grp.quantity) over (
            partition by tr_grp.instrument_id
            order by tr_grp.report_date
            rows unbounded preceding
        ) as quantity
    from
        tr_grouped as tr_grp
),


-- Generate All Date-Instrument Combinations
all_dates as (
    select
        d.report_date,
        f.instrument_id
    from
        (select distinct instrument_id from final_positions) f
    cross join
        data_table d
),

-- Left Join with final_positions & Front-fill Quantity
final_filled as (
    select
        ad.report_date,
        '9800003601' as sec_acc_no,
        ad.instrument_id,
        coalesce(fp.quantity, 
                 last_value(fp.quantity ignore nulls) over (
                     partition by ad.instrument_id order by ad.report_date rows between unbounded preceding and current row
                 )
        ) as quantity
    from all_dates ad
    left join final_positions fp
    on ad.instrument_id = fp.instrument_id
    and ad.report_date = fp.report_date
)


select
    *,
    concat(
        'trad-9800003301',
        to_char(report_date, 'yyyymmdd'),
        '-',
        coalesce(to_char(instrument_id), '')
        ) as surrogate_key
from
    final_filled
where
    QUANTITY IS NOT NULL;


WITH RECURSIVE date_range AS (
    SELECT DATE(CURRENT_DATE()-20) AS date_column
    UNION ALL
    SELECT DATEADD(DAY, 1, date_column)
    FROM date_range
    WHERE DATEADD(DAY, 1, date_column) <= CURRENT_DATE()-1
),

data_table as (
SELECT 
    date_column as report_date,
FROM date_range
WHERE DAYOFWEEK(date_column) NOT IN (0,6)
)

SELECT * FROM data_table;



SELECT 
    * 
FROM 
    TEAM_PRD.RISK_FUNCTION_TRANSFORM.TRF__RISK_FUNCTION_MRM_BOOK_9800003601_DAILY_EXPOSURES 
WHERE REPORT_DATE='2025-03-17';


select
    convert_timezone('Europe/Berlin', sb_trade.booked_ts)::date as trade_ts,
    COUNT(*),
    SUM(iff(sb_trade.booking_direction = 'DEBIT', 1, 0)) as sell,
    SUM(iff(sb_trade.booking_direction = 'CREDIT', 1, 0)) as buy
from
    teams_prd.asset_hub.pbl_curr__share_booking as sb_trade
where
    convert_timezone('Europe/Berlin', sb_trade.booked_ts)::date between '2024-01-01' and current_date() - 1
    and sb_trade.securities_account_number = 9800003301
    and sb_trade.INSTRUMENT_ID='US67066G1040'
GROUP BY 1;



SELECT * FROM TEAMS_PRD.CORE_MART.MRT_CURR__INSTRUMENTS LIMIT 10;