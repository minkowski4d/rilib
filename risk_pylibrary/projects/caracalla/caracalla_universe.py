#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from tools.snowflake_db import db_connection as db

# Custom Modules



def get_caracalla_query(key_word):

    if key_word == 'carcalla_universe_old':
        qry = "with nothing as (select null) "\
                ", spar as (select sp.instrument_id, sp.instrument_name, count(*) as n_sp, "\
                "COUNT_IF(sp.DELETED_TS IS NOT NULL AND sp.COUNT_EXECUTIONS = 1) as n_canceled_after_single_execution "\
                "from TEMP_DB.PUBLISH_SAVINGS_PLAN.PBL__SAVINGS_PLAN__SAVINGS_PLAN_DETAILS as sp "\
                "join TEAMS_PRD.TRANSFORM_AUM.TRF__AUM__EOD_PRICE_FEED as pf on pf.instrument_id=sp.instrument_id "\
                "and pf.PRICE_DT=date(sp.creation_ts) "\
                "where date(creation_ts)>=date('2021-01-01')"\
                "group by sp.instrument_id,sp.instrument_name "\
                "order by n_canceled_after_single_execution desc), "\
                "instruments_preq as ("\
                "select t.instrument_id, i.name_short, i.instrument_type, count(t.trade_id) as n_trades, "\
                "count(distinct t.AUTH_ACCOUNT_ID) as n_customers, round(sum(t.volume),0) as vol_eur_trades, "\
                "round(avg(t.price),2) as avg_price, "\
                "sum(coalesce(sp.n_canceled_after_single_execution,0)) as n_canceled_after_single_execution, sum(coalesce(sp.n_sp, 0)) as n_sp "\
                "from TEMP_DB.MARTS_TRADE.MRT__TRADE_CUSTOMER t "\
                "join TEMP_DB.MARTS_INSTRUMENTS.MRT__INSTRUMENTS i using (instrument_id) "\
                "full join TEMP_DB.DATA_LAKE.FTT_SCOPE as fs "\
                "using (instrument_id) left join spar as sp using (instrument_id) "\
                "where 1=1 and to_date(t.trade_ts)>'2021-01-01' and i.instrument_type in ('STOCK','FUND') "\
                "and t.TRADE_TYPE='REGULAR' and t.DIRECTION='BUY' and i.IS_SAVABLE_IN_AT_LEAST_ONE_JURISDICTION=TRUE "\
                "and fs.instrument_id IS NULL group by t.instrument_id, name_short, i.instrument_type order by n_trades desc), "\
                "stocks_with_calc_vals as (select * "\
                ", ((POWER(n_trades,2) - min(POWER(n_trades,2)) OVER(PARTITION BY instrument_type) ) / (max(POWER(n_trades,2)) OVER(PARTITION BY instrument_type) - min(POWER(n_trades,2)) OVER(PARTITION BY instrument_type)) * (1 - 0) + 0)  as n_trades_scaled"\
                ", ((POWER(AVG_PRICE,2) - min(POWER(AVG_PRICE,2)) OVER(PARTITION BY instrument_type)) / (max(POWER(AVG_PRICE,2)) OVER(PARTITION BY instrument_type) - min(POWER(AVG_PRICE,2)) OVER(PARTITION BY instrument_type)) * (1 - 0) + 0)  as price_scaled"\
                ", ((POWER(vol_eur_trades,2) - min(POWER(vol_eur_trades,2)) OVER(PARTITION BY instrument_type)) / (max(POWER(vol_eur_trades,2)) OVER(PARTITION BY instrument_type) - min(POWER(vol_eur_trades,2)) OVER(PARTITION BY instrument_type)) * (1 - 0) + 0)  as volume_scaled"\
                ", ((POWER(n_canceled_after_single_execution,2) - min(POWER(n_canceled_after_single_execution,2)) OVER(PARTITION BY instrument_type) ) / (max(POWER(n_canceled_after_single_execution,2)) OVER(PARTITION BY instrument_type) - min(POWER(n_canceled_after_single_execution,2)) OVER(PARTITION BY instrument_type)) * (1 - 0) + 0)  as n_canceled_after_single_execution_scaled"\
                ", ((POWER(n_sp,2) - min(POWER(n_sp,2)) OVER(PARTITION BY instrument_type) ) / (max(POWER(n_sp,2)) OVER(PARTITION BY instrument_type) - min(POWER(n_sp,2)) OVER(PARTITION BY instrument_type)) * (1 - 0) + 0)  as n_sp_scaled"\
                ", n_trades / sum(n_trades) OVER(PARTITION BY instrument_type) as perc_of_trades, vol_eur_trades / sum(vol_eur_trades) OVER(PARTITION BY instrument_type) as perc_of_vol "\
                "from instruments_preq order by instrument_type,n_trades_scaled) "\
                ",rankings as (select *"\
                ", rank() over (partition by instrument_type order by N_TRADES_SCALED*1+PRICE_SCALED*0 desc) as rank_nt100"\
                ", rank() over (partition by instrument_type order by N_TRADES_SCALED*0.8+PRICE_SCALED*0.2 desc) as rank_nt80pr20"\
                ", rank() over (partition by instrument_type order by N_TRADES_SCALED*0+PRICE_SCALED*1 desc) as rank_pr100"\
                ", rank() over (partition by instrument_type order by N_TRADES_SCALED*0+PRICE_SCALED*0+n_canceled_after_single_execution_scaled*1 desc) as rank_ar100"\
                ", rank() over (partition by instrument_type order by N_TRADES_SCALED*0.8+PRICE_SCALED*0.1+n_canceled_after_single_execution_scaled*0.1 desc) as rank_nt80pr10ar10"\
                ", rank() over (partition by instrument_type order by n_sp_scaled*1 desc) as rank_sp100 "\
                "from stocks_with_calc_vals) "\
                "select * from rankings order by instrument_type,N_TRADES_SCALED desc"

    elif key_word == 'fpa_universe_4k':
        qry = "WITH "\
                "TRADES AS ("\
                "SELECT INSTRUMENT_ID, count(trade_id) as d_trades, "\
                "SUM(IFF(DIRECTION = 'BUY',1,0)) AS d_buy_trades, "\
                "SUM(IFF(DIRECTION = 'SELL',1,0))  AS d_sell_trades, "\
                "SUM(SIZE) as d_shares, "\
                "SUM(IFF(DIRECTION = 'BUY',SIZE,0)) AS d_buy_shares, "\
                "SUM(IFF(DIRECTION = 'SELL',SIZE,0))  AS d_sell_shares, "\
                "SUM(volume) AS d_trade_volume, "\
                "SUM(IFF(DIRECTION = 'BUY',volume,0)) AS d_buy_volume, "\
                "SUM(IFF(DIRECTION = 'SELL',volume,0)) AS d_sell_volume "\
                "FROM TEAMS_PRD.MART_TRADE.MRT__TRADE_CUSTOMER "\
                "WHERE  (LATEST_STATUS = 'ORIGINAL' OR LATEST_STATUS = 'NEW') "\
                "AND TRADE_TYPE IN ( 'REGULAR','FRACTIONAL_SELL' ) "\
                "AND INSTRUMENT_TYPE IN ( 'STOCK', 'FUND' ) "\
                "AND TRADE_TS::DATE >= CURRENT_DATE()-%s "\
                "GROUP BY 1), "\
                "PRICE_DATE AS ("\
                "SELECT DISTINCT INSTRUMENT_ID, MAX(PRICE_DT::DATE) AS PRICE_DT "\
                "FROM TEAMS_PRD.TRANSFORM_AUM.trf__aum__eod_price_feed group by 1), "\
                "PRICE AS ("\
                "SELECT DISTINCT INSTRUMENT_ID, MAX(CLOSE_MID_PRICE) AS PRICE FROM TRANSFORM_AUM.trf__aum__eod_price_feed "\
                "inner join PRICE_DATE using (INSTRUMENT_ID,PRICE_DT) group by 1) "\
                "SELECT INSTRUMENT_ID,INSTRUMENT_TYPE, INTL_SYMBOL, NAME_SHORT, PRICE, d_trades, d_buy_trades, d_sell_trades, d_shares, "\
                "d_buy_shares, d_sell_shares, d_trade_volume, d_buy_volume, d_sell_volume "\
                "FROM  TEAMS_PRD.CORE_MART.MRT_CURR__INSTRUMENTS "\
                "LEFT JOIN TRADES USING (INSTRUMENT_ID) "\
                "LEFT JOIN PRICE USING (INSTRUMENT_ID) "\
                "WHERE IS_SAVABLE_IN_AT_LEAST_ONE_JURISDICTION = 'TRUE' "\
                "AND IS_SAVABLE_IN_AT_LEAST_ONE_JURISDICTION = 'TRUE' "\
                "AND INSTRUMENT_TYPE IN ( 'STOCK', 'FUND' ) "\
                "AND FINANCIAL_TRANSACTION_TAX is NULL order by d_trades desc"


    elif key_word == 'fpa_universe_full':
        qry = '''
        WITH TRADES AS (	
        SELECT	
        INSTRUMENT_ID,	
        -- DATE_TRUNC('day', TRADE_TS :: DATE) AS trade_date,	
        count(trade_id) as d_trades,	
        SUM(IFF(DIRECTION = 'BUY',1,0)) AS d_buy_trades,	
        SUM(IFF(DIRECTION = 'SELL',1,0)) AS d_sell_trades,	
        SUM(SIZE) as d_shares,	
        SUM(IFF(DIRECTION = 'BUY',SIZE,0)) AS d_buy_shares,	
        SUM(IFF(DIRECTION = 'SELL',SIZE,0)) AS d_sell_shares,	
        SUM(volume) AS d_trade_volume,	
        SUM(IFF(DIRECTION = 'BUY',volume,0)) AS d_buy_volume,	
        SUM(IFF(DIRECTION = 'SELL',volume,0)) AS d_sell_volume	
            
        FROM MART_TRADE.MRT__TRADE_CUSTOMER	
        WHERE ( LATEST_STATUS = 'ORIGINAL'	
        OR LATEST_STATUS = 'NEW' )	
        AND TRADE_TYPE IN ( 'REGULAR','FRACTIONAL_SELL' )	
        AND INSTRUMENT_TYPE IN ( 'STOCK', 'FUND' )	
        AND TRADE_TS::DATE >= CURRENT_DATE()-%s -- 7 day was initial outline, push from product to move to 21	
        GROUP BY 1	
        order by d_trades desc	
        ),	
            
        PRICE_DATE AS (	
        SELECT	
        DISTINCT INSTRUMENT_ID,	
        MAX(PRICE_DT::DATE) AS PRICE_DT	
        FROM TRANSFORM_AUM.trf__aum__eod_price_feed	
        group by 1	
        ),	
            
        PRICE AS (	
        SELECT	
        DISTINCT INSTRUMENT_ID,	
        MAX(CLOSE_MID_PRICE) AS PRICE	
        FROM TRANSFORM_AUM.trf__aum__eod_price_feed	
        inner join PRICE_DATE using (INSTRUMENT_ID,PRICE_DT)	
        -- where PRICE_DT = PRICE_DT	
        group by 1	
        )	
            
        SELECT	
        INSTRUMENT_ID,	
        INTL_SYMBOL,	
        NAME_SHORT,	
        PRICE,	
        -- trade_date,	
        d_trades,	
        d_buy_trades,	
        d_sell_trades,	
        d_shares,	
        d_buy_shares,	
        d_sell_shares,	
        d_trade_volume,	
        d_buy_volume,	
        d_sell_volume	
        FROM DISCOVERY_MART.MRT__CURR__INSTRUMENTS	
            
        LEFT JOIN TRADES USING (INSTRUMENT_ID)	
        LEFT JOIN PRICE USING (INSTRUMENT_ID)	
        WHERE	
        INSTRUMENT_TYPE IN ( 'STOCK', 'FUND' )	
        AND IS_ACTIVE_IN_AT_LEAST_ONE_JURISDICTION = 'TRUE'	
        -- AND FINANCIAL_TRANSACTION_TAX is NULL	
        -- AND IS_SAVABLE_IN_AT_LEAST_ONE_JURISDICTION = 'TRUE'	
        -- and INSTRUMENT_ID ='US0231351067'	
        order by d_trades desc	
        '''

    return qry


def _old_get_caracalla_universe():
    """
    Retrieves Carcalla universe based on
    """
    # Load modules:
    from tools.snowflake_db import db_connection as db

    # Get query:
    qry = get_caracalla_query('carcalla_universe_old')

    # Execute query
    df_0 = db.run_query(qry, fmt_engine='TEMP_DB')

    return df_0


def get_caracalla_universe(horizon=21, trade_limit=10, max_inv_low=3, max_inv_high=6, univ_selec='fpa_universe_full'):
    """
    Retrieves Caracalla Inventory Construction according to FP&A rules
    """

    # Load Modules:
    from tools.snowflake_db import db_connection as db

    # Get query:
    qry = get_caracalla_query(univ_selec)
    qry = qry%horizon

    # Execute query
    df = db.run_query(qry, fmt_engine='RISK')

    # Replace NaNs with zeros:
    for col in [k for k in df.columns if k[:2] == 'd_']:
        df[col] = df[col].fillna(0)

    # Calculate Metrics:
    df['count'] = 1
    df['tier'] = df['d_trades'].apply(lambda x: 'low' if x <= trade_limit else 'high')
    df['max_exposure'] = df[['price', 'tier']].apply(lambda row:
                                                         row['price']*max_inv_low
                                                         if row['tier'] == 'low'
                                                         else row['price']*max_inv_high, axis=1)
    # Calculate weight
    df['weight'] = df.max_exposure/df.max_exposure.sum()

    # Insert weight buckets
    wgts_array = np.append(np.arange(0, df.weight.max(), df.weight.max()/10), df.weight.max())[1:]
    wgts_buckets = []
    for k in range(0, len(wgts_array)):
        if k == 0:
            key_item = str(0)+' < x < ' + str(np.round(wgts_array[k]*100, 2))
            wgts_buckets.append((key_item, [0, wgts_array[k]]))
        else:
            key_item = str(np.round(wgts_array[k-1]*100, 2))+' < x <'+str(np.round(wgts_array[k]*100, 2))
            wgts_buckets.append((key_item, [wgts_array[k-1], wgts_array[k]]))

    df['weight_bucket'] = np.nan
    for k, v in dict(wgts_buckets).items():
        df.loc[(df.weight > v[0]) & (df.weight <= v[1]), 'weight_bucket'] = k

    return df



def get_caracalla_prices(ids, len):
    """
    Fetches Prices for given security list
    @param ids: list, e.g. ['IE00B4L5Y983']
    @param len: look back horizon in days, e.g. 250
    """

    # Transform Python list to sql syntax
    ids_sql = db.joinpad(ids)

    # Basic query
    qry = "with nothing as (select null), instruments as (" \
          "select instrument_id, name_short, instrument_type " \
          "from TEAMS_PRD.CORE_MART.MRT_CURR__INSTRUMENTS " \
          "where 1=1 and instrument_id in (%s) and instrument_type in ('STOCK', 'FUND')), " \
          "prices as (" \
          "select p.price_dt, i.instrument_id, i.name_short, i.instrument_type, p.close_mid_price as price, p.exchange as exch " \
          "from instruments as i join TEAMS_PRD.TRANSFORM_AUM.TRF__AUM__EOD_PRICE_FEED as p using (instrument_id)) " \
          "select * from prices where price_dt > dateadd(day, %s, current_date()) order by instrument_id asc, price_dt asc"%(ids_sql, -len)

    # Fetch data
    df = db.run_query(qry, fmt_engine = 'RISK')
    # Remove Duplicates
    df = df.drop_duplicates(subset = ['price_dt', 'instrument_id'])
    # Unstack the data
    df = df.pivot_table(index = ['price_dt'], columns = ['instrument_id'], values = 'price')

    return df
