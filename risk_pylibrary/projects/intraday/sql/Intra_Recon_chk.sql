with eod_position as (
    select
        TRADING_ACCOUNT,
        SEC_ACC_NO,
        INSTRUMENT_ID,
        PRICE_CURRENCY,
        REALISED_POSITION,
        row_number() over (
            partition by TRADING_ACCOUNT, SEC_ACC_NO, INSTRUMENT_ID
            order by SEQ_TIME_CEST desc
        ) as rn
    from ZZCLONE_FB_PRD_ZZ_TEAMS_PRD.risk_function_transform.trf__risk_function_mrm_book_total_intraday_exposure
    where SEQ_TIME_CEST::date <= '2026-04-23'
    and TRADING_ACCOUNT=200
),

t_minus_1 as (
    select * exclude rn
    from eod_position
    where rn = 1
),

val_t_minus_1 as (
    select
        INSTRUMENT_ID,
        QUANTITY
    from TEAMS_PRD.risk_function_publish.pbl__risk_function_mrm_book_trading_valuation
    where REPORT_DATE = '2026-04-23'
    and SEC_ACC_NO = 9800001601
)

select
    t.*,
    v.QUANTITY                          as val_quantity,
    t.REALISED_POSITION - v.QUANTITY    as delta
from t_minus_1 as t
left join val_t_minus_1 as v
    on t.INSTRUMENT_ID = v.INSTRUMENT_ID
WHERE
    delta <> 0;


-------
select
    SEQ_TIME_CEST,
    TRADING_ACCOUNT,
    SEC_ACC_NO,
    INSTRUMENT_ID,
    PRICE_CURRENCY,
    REALISED_POSITION,
    row_number() over (
        partition by TRADING_ACCOUNT, SEC_ACC_NO, INSTRUMENT_ID
        order by SEQ_TIME_CEST desc
    ) as rn
from ZZCLONE_FB_PRD_ZZ_TEAMS_PRD.risk_function_transform.trf__risk_function_mrm_book_total_intraday_exposure
where SEQ_TIME_CEST::date < current_date()-9
and trading_account=200;

SELECT
date_trunc('minute', SEQ_TIME_CEST)     as cest_minute,
TRADING_ACCOUNT,
SEC_ACC_NO,
INSTRUMENT_ID,
PRICE_CURRENCY,
REALISED_POSITION,
row_number() over (
    partition by TRADING_ACCOUNT, SEC_ACC_NO, INSTRUMENT_ID,
                    date_trunc('minute', SEQ_TIME_CEST)
    order by SEQ_TIME_CEST desc
) as rn
from ZZCLONE_FB_PRD_ZZ_TEAMS_PRD.risk_function_transform.trf__risk_function_mrm_book_total_intraday_exposure
where SEQ_TIME_CEST::date = current_date()-9
AND trading_account=200
AND instrument_id='US5949181045';



select
    INSTRUMENT_ID,
    CEST_MINUTE,
    MID_PRICE
from TEAMS_PRD.risk_function_publish.pbl__risk_function_mrm_book_msl_prices_intraday
where 
CEST_MINUTE::date = current_date() - 9
AND
instrument_id='US5949181045';

select
    INSTRUMENT_ID,
    QUANTITY
from TEAMS_PRD.risk_function_publish.pbl__risk_function_mrm_book_trading_valuation
where REPORT_DATE = current_date() - 2
and SEC_ACC_NO = '9800001601';

SELECT
distinct(CEST_MINUTE::date)
FROM
ZZCLONE_FB_PRD_ZZ_TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation_intraday
;

SELECT 
DISTINCT(SEC_ACC_NO)
FROM
TEAMS_PRD.risk_function_publish.pbl__risk_function_mrm_book_trading_valuation
WHERE
REPORT_DATE='2026-04-23';


select
    INSTRUMENT_ID,
    QUANTITY
from TEAMS_PRD.risk_function_publish.pbl__risk_function_mrm_book_trading_valuation
where REPORT_DATE = '2026-04-29'
and SEC_ACC_NO = '9800001601';




select
    *
    ,row_number() over (partition by seq_date, isin, trading_account order by seq_no desc) as rn
from
    teams_prd.mm_mart.mrt__mm__positions
where
    1=1
and
    seq_date>'2026-04-23'
and
    trading_account in (200); -- Trading book 200 = 9800001601;



SELECT
    MAX(report_date)
FROM TEAMS_PRD.RISK_FUNCTION_TRANSFORM.trf__risk_function_mrm_book_9800001601_daily_pnl_trades