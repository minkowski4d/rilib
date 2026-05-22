with tib_trades as (
SELECT 
trade_id as trade__id,
        instrument_id as trade__instrument_id,
        order_id as trade__order_id,
        bundle_id as trade__bundle_id,
        trade_ts as trade__ts,
        direction as trade__direction,
        trade_type as trade__type,
        tvtic as trade__tvtic,
        group_id as trade__group_id,
        exchange_id as trade__exchange_id,
        original_price as trade__original_price,
        original_size as trade__original_size,
        prim_id as trades__prim_id
FROM TEAMS_PRD.MART_TRADE.MRT_CURR__TRADE_BACKEND
WHERE 
    exchange_id = 'TIB' 
  AND trade_order_usecase != 'PROPRIETARY' 
  AND latest_status <> 'CANCEL'
  and trade_type = 'REGULAR'
        and cancellations = 0
  AND trade_ts::date = CURRENT_DATE() - 1 
  AND (
      time(convert_timezone('UTC', 'Europe/Berlin', trade_ts)) BETWEEN time('07:30:01') AND time('08:59:59') 
      OR time(convert_timezone('UTC', 'Europe/Berlin', trade_ts)) BETWEEN time('17:30:01') AND time('22:59:59')
  )
),
  instruments as (
    select
        instrument_id as instrument__id,
        instrument_type as instrument__type,
        name_official as instrument__name_official,
        symbol as instrument__symbol_ticker_t
    from TEAMS_PRD.ASSET_HUB.PBL_CURR__INSTRUMENTS
    where
         instrument_type not in ('CRYPTO', 'BOND', 'DERIVATIVE')
),

  trf__exe_q__tib_trades as 
  (
  select tib_trades.*,
  instruments.*
  from tib_trades
  inner join instruments
  on instruments.instrument__id = tib_trades.trade__instrument_id
  ),

quotes_lsx as (
  select
  timestamp,
  timestamp::DATE as quote_date,
  'LSX' as reference_exchange,
  ask_size,
  ask_price,
  bid_size,
  bid_price,
  isin
  from EVENTS_PRD.RAPPBODE_QUOTES_PUBLISH.QUOTES_FCT_QUOTES_LSX_V1
  where ingestion_date = CURRENT_DATE() - 1
  and ask_price > 0 and bid_price > 0
),

trf__exe_q__lsx_quotes as 
(
select *
from quotes_lsx
),

  
  ordered_timeline as 
  (
  
  select
        trade__ts as timestamp,
        'trade' as source,
        trade__id as trade_id,
        trade__instrument_id as isin,
        trade__exchange_id as exchange_id,
        trade__direction as direction,
        trade__type as trade_type,
        trade__tvtic as tvtic,
        trade__group_id as group_id,
        instrument__type as instrument_type,
        instrument__name_official as instrument_name,
        trade__original_price as trade_price,
        trade__original_size as trade_size,
        null as exchange,
        null as bid,
        null as ask,
        null as bidsize,
        null as asksize,
    from trf__exe_q__tib_trades
    union all
    select
        timestamp,
        'feed' as source,
        null as trade_id,
        isin,
        null as exchange_id,
        null as direction,
        null as trade_type,
        null as tvtic,
        null as group_id,
        null as instrument_type,
        null as instrument_name,
        null as trade_price,
        null as trade_size,
        reference_exchange as exchange,
        bid_price as bid,
        ask_price as ask,
        bid_size as bidsize,
        ask_size as asksize,
    from trf__exe_q__lsx_quotes as quotes
    order by 1
),

adding_next_trade_id_for_a_given_feed_entry as (
    select
        *,
        lead(trade_id) ignore nulls over (partition by isin order by timestamp) as next_trade_id,
    from ordered_timeline
),

trf__exe_q__xetra_q_and_trades as
(
select * from adding_next_trade_id_for_a_given_feed_entry
),

mapping_quotes_and_relevant_trades as (
    select * from (
        select
            base.timestamp,
            base.source,
            base.isin,
            base.exchange_id,
            iff(next_trade.trade__direction = 'BUY', base.ask, null) as ask,
            iff(next_trade.trade__direction = 'BUY', base.asksize, null) as asksize,
            iff(next_trade.trade__direction = 'SELL', base.bid, null) as bid,
            iff(next_trade.trade__direction = 'SELL', base.bidsize, null) as bidsize,
            (base.ask - base.bid) as spread,
            next_trade.trade__ts as next_trade_timestamp,
            next_trade.trade__id as next_trade_id,
            next_trade.trade__instrument_id as next_trade_isin,
            next_trade.trade__direction as next_trade_direction,
            next_trade.trade__type as next_trade_type,
            next_trade.trade__tvtic as next_trade_tvtic,
            next_trade.trade__group_id as next_trade_group_id,
            next_trade.trade__exchange_id as next_trade_exchange_id,
            next_trade.instrument__type as next_trade_instrument_type,
            next_trade.instrument__name_official as next_trade_execution_instrument_name,
            next_trade.trade__original_price as next_trade_trade_price,
            next_trade.trade__original_size::int as next_trade_trade_size,
        from trf__exe_q__xetra_q_and_trades as base
        left join trf__exe_q__tib_trades as next_trade
            on base.next_trade_id = next_trade.trade__id
        where
            source = 'feed'
    )
),

adding_timewindow as (
    select
        *,
        datediff(
                minute,
                timestamp,
                next_trade_timestamp
        ) as mnt_diff_between_next_trade_ts_and_feed_ts,
        mnt_diff_between_next_trade_ts_and_feed_ts <= 5 as within_time_window,
    from mapping_quotes_and_relevant_trades
),

trades_w as (
select
    NEXT_TRADE_TYPE as trade_type,
    next_trade_id as trade_id,
    NEXT_TRADE_TVTIC as tvtic,
    NEXT_TRADE_GROUP_ID as group_id,
    exchange_id as reference_exchange,
    next_trade_timestamp as trade_ts,
    isin as instrument_id,
    next_trade_direction as direction,
    next_trade_trade_price as trade_price,
    next_trade_trade_size as trade_size,
    timestamp as reference_quote_ts,
    ask as ask_price,
    asksize as ask_size,
    bid as bid_price,
    bidsize as bid_size,
    spread
from adding_timewindow
QUALIFY RANK() OVER(PARTITION BY trade_id ORDER BY REFERENCE_QUOTE_TS DESC) = 1
),


trades_agg as (
    select
        trade_type,
        trade_id,
        tvtic,
        group_id,
        reference_exchange,
        trade_ts,
        instrument_id,
        direction,
        trade_price,
        trade_size,
        ask_price,
        ask_size,
        bid_price,
        bid_size,
        spread,
        reference_quote_ts
    from trades_w
    where trade_price != 0 and trade_size != 0
    group by all
),

weighted AS (
    SELECT
        trade_type,
        trade_id,
        tvtic,
        group_id,
        reference_exchange,
        trade_ts,
        instrument_id,
        direction,
        trade_price,
        trade_size,
        reference_quote_ts,
        ask_price AS quote_price,
        ask_size AS quote_size,
        ROUND(ask_price, 4) AS weighted_quote_price,
        spread
    FROM trades_agg
    WHERE direction = 'BUY'
    AND trade_size <= quote_size

    UNION ALL

    SELECT
        trade_type,
        trade_id,
        tvtic,
        group_id,
        reference_exchange,
        trade_ts,
        instrument_id,
        direction,
        trade_price,
        trade_size,
        reference_quote_ts,
        bid_price AS quote_price,
        bid_size AS quote_size,
        ROUND(bid_price, 4) AS weighted_quote_price,
        (ask_price - bid_price) AS spread
    FROM trades_agg
    WHERE direction = 'SELL'
    AND trade_size <= quote_size
),

summary as (
    SELECT
        trade_type,
        trade_id,
        tvtic,
        group_id,
        reference_exchange,
        trade_ts,
        instrument_id,
        direction,
        trade_price,
        trade_size,
        reference_quote_ts,
        quote_price,
        quote_size,
        weighted_quote_price,
        spread,
        CURRENT_TIMESTAMP() AS query_run_ts,
        CASE WHEN direction = 'BUY' THEN weighted_quote_price - trade_price
        WHEN direction = 'SELL' THEN trade_price - weighted_quote_price
        ELSE NULL
        END AS price_difference,
        CASE WHEN direction = 'BUY' THEN weighted_quote_price - trade_price
        WHEN direction = 'SELL' THEN trade_price - weighted_quote_price
        ELSE NULL
        END * trade_size AS pnl,
        ROUND(
            (-(CASE WHEN direction = 'BUY' THEN weighted_quote_price - trade_price
                    WHEN direction = 'SELL' THEN trade_price - weighted_quote_price
                    ELSE NULL END)
            / NULLIF(weighted_quote_price, 0)) * 10000, 2
        ) AS markup_bps,
        ROUND(
            (-(CASE WHEN direction = 'BUY' THEN weighted_quote_price - trade_price
                    WHEN direction = 'SELL' THEN trade_price - weighted_quote_price
                    ELSE NULL END)
            / NULLIF(spread, 0)) * 100, 2
        ) AS markup_pct_of_spread,
        CASE WHEN direction = 'BUY'  THEN weighted_quote_price - spread / 2
             WHEN direction = 'SELL' THEN weighted_quote_price + spread / 2
        END AS mid_price,
        CASE WHEN direction = 'BUY'  THEN trade_price - (weighted_quote_price - spread / 2)
             WHEN direction = 'SELL' THEN (weighted_quote_price + spread / 2) - trade_price
        END AS slippage_eur,
        ROUND(
            CASE WHEN direction = 'BUY'  THEN trade_price - (weighted_quote_price - spread / 2)
                 WHEN direction = 'SELL' THEN (weighted_quote_price + spread / 2) - trade_price
            END / NULLIF(
                CASE WHEN direction = 'BUY'  THEN weighted_quote_price - spread / 2
                     WHEN direction = 'SELL' THEN weighted_quote_price + spread / 2
                END, 0
            ) * 10000, 2
        ) AS slippage_bps
    FROM weighted
    WHERE pnl is not null
)

select * from summary
--where PNL < -30
ORDER BY markup_bps DESC;