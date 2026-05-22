#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys

# Import Python Modules
import numpy as np
from datetime import datetime as _datetime, date, timedelta
import polars as pl

# risk_pylibrary Modules
import risk_pylibrary.tools.pandas_patched as pd
from tools.snowflake_db import db_connection as db



def pos_stick_analysis(startdate, enddate, window_size):

    # Get Rolling Volume KPIs:
    out_qtls = get_qtl_volume(startdate, enddate, window_size)

    # Get ESMA SI Data:
    out_si = get_esma_si_data(symbols=out_qtls.columns)
    out_si = out_si.set_index('instrument_id')

    # Revaluate KPIs:
    si_window = (enddate-startdate).days/window_size
    out['eu_volume_window'] = out['eu_volume']/si_window

    # Generate Output
    out = out_si.join(out_qtls.T)

    return out




def get_inventory_info(use_polars=False):

    qry = '''
        with trades as (
        SELECT 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
            "isin" as instrument_id,
        FROM 
            BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_INVENTORY_TRADE
        WHERE
            "prim_id" NOT LIKE '%%C%%'
        AND 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= '2024-06-15'
        AND 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= CURRENT_DATE()
        UNION ALL
        SELECT 
            TO_TIMESTAMP_NTZ("value_date") AS trade_ts,
            TO_TIMESTAMP_NTZ("value_date")::date as report_date,
             "instrument_id" as instrument_id
        FROM 
            BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING sb 
        WHERE 
            "sec_acc_no"=9800001301
        AND 
            "value_date" >= '2022-10-31'
        AND 
            "value_date" <= '2024-06-07'
        AND
            FLOOR("net_size") = "net_size"

        ORDER BY 1)

        SELECT
            tr.report_date,
            tr.instrument_id,
            COUNT(tr.instrument_id) AS NUM_TRADES
        FROM 
            trades AS tr
        GROUP BY 1,2
        ORDER BY 1
    '''

    qry_out = qry

    df = db.run_query(query=qry_out)


    # Pivot the Data and Add Criteria, if positions have occurences of being more than n days in the portfolio
    df_pivot = pd.pivot_table(df,index='instrument_id', columns='report_date', values='num_trades', aggfunc=np.sum).T
    df_pivot = df_pivot.rename_axis(None, axis=1)
    
    # Setting Output
    out_describe = pd.DataFrame()
    out_roll_mean = pd.DataFrame(index=df_pivot.index)

    # Iterating over 30 days holding period
    count=0
    for col in df_pivot.columns:
        # print counter:
        if count%500 == 0:
            print('\t\t Calculating %sth ISIN'%count)

        # Setting nan values to 0, all other values to 1
        tmp = df_pivot[[col]]

        # Cutting at portfolio entry point
        tmp = tmp[tmp.cumsum().dropna().index[0]:]
        tmp = tmp.notnull().astype('int')

        # Running 30day KPI:
        tmp_roll_mean = tmp.rolling(30).mean().dropna()

        # Add calcs to output
        out_roll_mean = pd.concat([out_roll_mean, tmp_roll_mean], axis = 1)
        out_describe = pd.concat([out_describe, tmp_roll_mean.dropna().describe()], axis = 1)

        count += 1
    
    if use_polars:
        columns = ["col1", "col2", "col3"]

        df_pivot_pl = pl.from_pandas(df_pivot)
        # Rolling window size
        window_size = 30

        # Apply rolling mean to multiple columns
        rolling_df = df_pivot_pl.with_columns([df_pivot_pl[col].rolling_mean(window_size).alias(f"{col}_rolling_mean") for col in df_pivot.columns])



    return df


def get_qtl_volume(startdate, enddate, window_size):

    qry = '''
        with trades as (
        SELECT 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
            "isin" as instrument_id,
            "execution_price" as price,
            "execution_size" as quantity
        FROM 
            BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_INVENTORY_TRADE
        WHERE
            "prim_id" NOT LIKE '%%C%%'
        AND 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= %s
        AND 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
        UNION ALL
        SELECT 
            TO_TIMESTAMP_NTZ("value_date") AS trade_ts,
            TO_TIMESTAMP_NTZ("value_date")::date as report_date,
             "instrument_id" as instrument_id,
            "execution_price" as price,
            "net_size" as quantity
        FROM 
            BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING sb 
        WHERE 
            "sec_acc_no"=9800001301
        AND 
            "value_date" >= %s
        AND 
            "value_date" <= %s
        AND
            FLOOR("net_size") = "net_size"

        ORDER BY 1)

        SELECT
            tr.report_date,
            tr.instrument_id,
            COUNT(tr.instrument_id) AS NUM_TRADES,
            AVG(tr.price * tr.quantity) AS AVG_VOL_EUR
        FROM 
            trades AS tr
        GROUP BY 1,2
        ORDER BY 1
    '''
    
    # Move startdate back by 30 days in order to start rolling KPIs at effective startdate

    startdate_shift = startdate - timedelta(30)
    qry_out =qry%(db.sqldate(startdate_shift), db.sqldate(enddate), db.sqldate(startdate_shift), db.sqldate(enddate))
    df_vol = db.run_query(query=qry_out)
   

    # Run Analytics:
    # Pivot the Data and Add Criteria, if positions have occurences of being more than n days in the portfolio
    df_pivot_vol = pd.pivot_table(df_vol,index='instrument_id', columns='report_date', values='avg_vol_eur', aggfunc=np.sum).T
    df_pivot_vol = df_pivot_vol.rename_axis(None, axis=1)
    df_pivot_vol = df_pivot_vol[date(2024,4,1):]
    
    # Initialising Polars
    df_pivot_pl = pl.from_pandas(df_pivot_vol)
    
    # Apply rolling quantile to multiple columns
    out_rolling_qtls = pd.DataFrame()

    for qtl in [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]:

        tmp = df_pivot_pl.with_columns(
            [df_pivot_pl[col].fill_null(
                strategy="zero").rolling_quantile(
                    quantile=qtl, window_size=window_size).alias(f"{col}_rolling_qtl") for col in df_pivot_pl.columns])
        
        out_rolling_qtls
    
    out_rolling_qtls = tmp.to_pandas()
    out_rolling_qtls = out_rolling_qtls[[k for k in out_rolling_qtls.columns if k.endswith('qtl')]]
    out_rolling_qtls = out_rolling_qtls.rename(columns=lambda x: x.split('_')[0])


    rolling_df = df_pivot_pl.with_columns([df_pivot_pl[col].fill_null(strategy="zero").rolling_mean(window_size).alias(f"{col}_rolling_mean") 
                                        for col in df_pivot_pl.columns])
    
    # Start setting output
    tmp_qtls = rolling_df.to_pandas()
    tmp_qtls = tmp_qtls[[k for k in tmp_qtls.columns if k.endswith('mean')]]
    tmp_qtls = tmp_qtls.rename(columns = lambda x: x.split('_')[0])

    # Generate output
    out_qtls = tmp_qtls.quantile([0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95])


    return out_qtls


def get_esma_si_data(symbols=[]):

    qry = '''
        SELECT * FROM TEAMS_PRD.RISK_DATA.SI_DATA WHERE END_DATE='2024-09-30'
        '''
    
    df_si_orig = db.run_query(query=qry)

    df_si = df_si_orig[df_si_orig.instrument_id.isin(symbols)]

    return df_si


def get_inventory_trades(startdate, enddate):

    qry = '''
        SELECT 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
            "isin" as instrument_id,
            IFF("trade_direction"='SELL','S','B') as side,
            "trade_direction" as booking_direction,
            'EIS' as order_type,
            "execution_price" as price,
            IFF("trade_direction"='SELL', -1, 1) * "execution_size" as quantity 
        FROM 
            BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_INVENTORY_TRADE
        WHERE
            "prim_id" NOT LIKE '%%C%%'
        AND 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= %s
        AND 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
        AND
            "isin" = 'US88160R1014'
        UNION ALL
        SELECT
            TO_TIMESTAMP_NTZ("value_date") AS trade_ts,
            TO_TIMESTAMP_NTZ("value_date")::date as report_date,
            "instrument_id" as instrument_id,
            IFF("booking_direction"='DEBIT','S','B') as side,
            "booking_direction" as booking_direction,
            "booking_type" as order_type,
            "execution_price" AS price,
            IFF("booking_direction"='CREDIT', "net_size", -"net_size") AS quantity
        FROM
            BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING sb
        WHERE
            "sec_acc_no" = 9800003301
        AND 
            "booking_category" = 'CORPORATE_ACTION'
        AND 
            "value_date" >= %s
        AND 
            "value_date" <= %s
        AND
            "instrument_id" = 'US88160R1014'
        ORDER BY 1
        '''


    qry_out = qry % (db.sqldate(startdate),db.sqldate(enddate),db.sqldate(startdate),db.sqldate(enddate))

    df_trades = db.run_query(query=qry_out)

    return df_trades







