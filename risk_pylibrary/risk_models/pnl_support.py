#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Python Modules
import numpy as np
import os
import pandas as pd
from datetime import datetime as _datetime
from datetime import timedelta, date

# Custom Modules
from tools.snowflake_db import db_connection as db
from tools import config as CF

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings('ignore')

def build_trade_cache_eod_close(enddate=None):
    """
    Supportive function for building a trade block, which is based on the EOD position of the Caracalla portfolio,
    for PnL execution
    @param enddate: date object - Example: date(2023,6,14)
    @return: DataFrame
    """

    # Get Trades
    df_trades = get_trades_pnl(startdate=date(2022, 9, 1), enddate=enddate)
    df_trades['quantity_trades'] = df_trades[['quantity', 'side']].apply(lambda row: -1 * row['quantity'] if row['side'] == 'S' else row['quantity'], axis=1)
    cols = ['symbol', 'side', 'instrument_type', 'booking_category', 'booking_type', 'price', 'multiplier', 'quantity_trades']
    out = df_trades[['symbol', 'quantity_trades']].groupby('symbol').sum()

    # Get Prices
    prx = get_prices_eod(syms=out.index, startdate=enddate, enddate=enddate)
    prx = prx.loc[[enddate]]
    prx = prx.T
    prx.columns = ['price']

    # Join Prices
    out = out.join(prx)
    out['price'] = out['price'].fillna(0)

    # Join Info
    df_trades_info = df_trades[['symbol', 'instrument_type']].drop_duplicates(subset=['symbol', 'instrument_type'], keep='last')
    df_trades_info = df_trades_info.set_index('symbol')
    out = out.join(df_trades_info)

    # Build Final
    out['side'] = out[['quantity_trades']].apply(lambda row: 'S' if row['quantity_trades'] < 0 else 'B', axis=1)
    out['multiplier'] = 1
    out['booking_category'] = 'TRADING'
    out['booking_type'] = out[['quantity_trades']].apply(lambda row: 'SELL' if row['quantity_trades'] < 0 else 'BUY', axis=1)
    out = out.reset_index()

    # Set EOD Time
    out['time'] = _datetime(enddate.year,enddate.month,enddate.day, 23, 59, 59)

    # Format
    out = out[['time', 'symbol', 'side', 'instrument_type', 'booking_category', 'booking_type', 'price', 'multiplier', 'quantity_trades']]
    out.columns = ['time', 'symbol', 'side', 'instrument_type', 'booking_category', 'booking_type', 'price', 'multiplier', 'quantity']

    return out


def get_prices_eod(syms=[], startdate=None, enddate=None, read_price_cache=False, read_full_dwh=False, fill_na=True):
    """
    Function to retrieve EOD Prices out of TEAMS_PRD.TRANSFORM_AUM.TRF__AUM__EOD_PRICE_FEED
    Output is limited via last portfolio composition and exchange='LSX'

    @param startdate: date object
    @param enddate: date object
    @return: DataFrame
    """

    if read_price_cache:
        print('\t Reading Price Cache')
        df_prices = CF.cache_pnl_prices.copy()

    else:
        # Get Prices from EOD DWH
        # Check for Bonds and delete price by 100 as bonds are executed with decimal prices (e.g. 0.99)

        if read_full_dwh:

            print('\t Retrieving Full DWH Prices')

            qry = '''
                    SELECT
                        pr.REPORT_DATE as ddate, 
                        pr.instrument_id as symbol, 
                        CLOSE_MID_PRICE_CLEAN  AS price
                    FROM 
                        TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_msl_prices as pr
                    WHERE
                        pr.REPORT_DATE BETWEEN %s AND %s
                    AND
                        DAYOFWEEK(pr.REPORT_DATE) not in (0,6)
                    ORDER BY 1,2
                    '''

            qry_prices = qry % (db.sqldate(startdate-timedelta(3)), db.sqldate(enddate))

        elif syms is not None:

            qry = '''
                    SELECT
                        pr.REPORT_DATE as ddate, 
                        pr.instrument_id as symbol, 
                        CLOSE_MID_PRICE_CLEAN  AS price
                    FROM 
                        TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_msl_prices as pr
                    WHERE
                        pr.REPORT_DATE BETWEEN %s AND %s
                    AND
                        pr.instrument_id in (%s)
                    AND
                        DAYOFWEEK(pr.REPORT_DATE) not in (0,6)
                    ORDER BY 1,2
                    '''

            qry_prices = qry % (db.sqldate(startdate-timedelta(3)), db.sqldate(enddate), db.joinpad(syms))


        # Run Price Query
        df_prices = db.run_query(query=qry_prices)

        # Format in Columns:
        df_prices = pd.pivot_table(df_prices, index='ddate', columns='symbol', values='price')
        # Remove column index name
        df_prices = df_prices.rename_axis(None, axis=1)
        if fill_na:
            # FrontFill Prices then Backfill
            df_prices = df_prices.fillna(method='ffill').fillna(method='bfill')

    df_prices = df_prices.sort_index()

    return df_prices


def get_trades_pnl(account=None, syms=None, instrument_type=None, startdate=None, enddate=None, query_eis=False, exclude_btype=False, add_filter=None):
    """
    Trades Query for PnL Purpose that Picks up accounts and adds sec infos

    @param account: str, e.g. 'caligula'
    @param syms: list of ISINs
    @param instrument_type: str, 'FUND', 'STOCK' etc
    @param startdate: date object
    @param enddate: date object
    @param query_eis: boolean, if True queries EIS trades for Caligula only
    @param exclude_btype:
    @param add_filter:
    @return:
    """


    if startdate is None:
        raise Exception('\t ERROR: You need to Specify a Startdate')
    if enddate is None:
        raise Exception('\t ERROR: You need to Specify an Enddate')


    if instrument_type is None:
        instrument_type = ['STOCK', 'FUND', 'DERIVATIVE', 'BOND']


    if account==9800003601:
        ibkr_acct=600
    elif account==9800001601:
        ibkr_acct=200

    # Get Trades    ********************************************
    if syms:
        if query_eis:
            # EIS Trades query works only on Caligula Trades
            # Needs to direction wise unadjusted net sizes
            print('\t Querying EIS Trades for %s' % account)
            qry = '''
            with trades as (
            SELECT 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
                "isin" as instrument_id,
                IFF("order_type"='SELL','B','S') as side,
                IFF("order_type"='SELL','BUY','SELL') as booking_direction, -- booking direction inverted for customer orders
                'CUSTOMER' as order_type,
                "execution_price" as price,
                "execution_currency" as execution_currency,
                "size" as quantity,
                IFF("order_type"='SELL', 1, -1) * "size" as quantity_signed
            FROM 
                BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_CUSTOMER_ORDER
            WHERE
                "status" = 'EXECUTED'
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= %s
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
            AND
                "isin" in (%s)

            UNION ALL

            SELECT 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
                "isin" as instrument_id,
                IFF("trade_direction"='SELL','S','B') as side,
                "trade_direction" as booking_direction,
                'EIS' as order_type,
                "execution_price" as price,
                "execution_currency" as execution_currency,
                "execution_size" as quantity,
                IFF("trade_direction"='SELL', -1, 1) * "execution_size" as quantity_signed 
            FROM 
                BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_INVENTORY_TRADE
            WHERE
                "prim_id" NOT LIKE '%%C%%'
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= %s
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
            AND
                "isin" in (%s)

            UNION ALL

            SELECT
                convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as trade_ts,
                mart_sb_trade.booking_date as report_date,
                mart_sb_trade.instrument_id AS instrument_id,
                IFF(mart_sb_trade.booking_direction = 'DEBIT','S','B') AS SIDE,
                mart_sb_trade.booking_direction,
                mart_sb_trade.booking_type,
                COALESCE(mart_sb_trade.execution_price, mart_sb_trade.price_at_booking) as PRICE,
                mart_sb_trade.cc__currency_code as execution_currency,
                mart_sb_trade.net_size AS QUANTITY,
                IFF(mart_sb_trade.booking_direction = 'DEBIT', -1, 1) * mart_sb_trade.net_size as quantity_signed 
            FROM
                TEAMS_PRD.ASSET_HUB.PBL_CURR__SHARE_BOOKING as mart_sb_trade
            WHERE
                convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::date  BETWEEN %s AND %s
            AND
                mart_sb_trade.securities_account_number = %s
            AND
                mart_sb_trade.booking_category in ('CORPORATE_ACTION','DELIVERY')
            AND
                mart_sb_trade.instrument_id in (%s)
            ORDER BY 1),


            sec_info AS (
            SELECT 
                "isin" AS INSTRUMENT_ID,
                "instrument_type" AS INSTRUMENT_TYPE,
            FROM 
                BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
            WHERE
                "instrument_type" in (%s)
            AND
                "isin" in (%s)
            ),

            fx_rates AS (
            SELECT 
                reference_dt,
                currency as fx_currency,
                rate as fx_rate 
            FROM 
                TEAMS_PRD.RISK_FUNCTION_SOURCE.src_curr__risk_function_fx_rates 
            WHERE 
                currency='PLN'
            AND
                reference_dt  BETWEEN %s AND %s
            )


            SELECT
                tr.trade_ts as time,
                tr.report_date as booking_date,
                tr.INSTRUMENT_ID as symbol,
                tr.side as side,
                sc.INSTRUMENT_TYPE as instrument_type,
                tr.booking_direction as booking_category,
                tr.order_type as booking_type,
                IFF(sc.INSTRUMENT_TYPE='BOND' AND tr.order_type='CUSTOMER', tr.PRICE/100, tr.PRICE) as price,
                fx.fx_rate,
                tr.execution_currency,
                tr.QUANTITY AS quantity,
                tr.quantity_signed AS quantity_signed
            FROM
                trades AS tr
            INNER JOIN 
                sec_info AS sc
                ON sc.INSTRUMENT_ID = tr.INSTRUMENT_ID
            LEFT JOIN
                fx_rates AS fx
                ON fx.fx_currency=tr.execution_currency AND fx.reference_dt=tr.report_date
            '''

            qry = qry % (db.sqldate(startdate),db.sqldate(enddate),db.joinpad(syms),db.sqldate(startdate),
                         db.sqldate(enddate),db.joinpad(syms),db.sqldate(startdate),db.sqldate(enddate),account,db.joinpad(syms),
                         db.joinpad(instrument_type),db.joinpad(syms),db.sqldate(startdate),db.sqldate(enddate))
            
        elif account in [9800003601, 9800001601]:
            qry ='''--sql
                WITH trades AS (
                SELECT
                    convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as TIME,
                    mart_sb_trade.booking_date as BOOKING_DATE,
                    mart_sb_trade.instrument_id AS SYMBOL,
                    IFF(mart_sb_trade.booking_direction = 'DEBIT','S','B') AS SIDE,
                    mart_sb_trade.booking_category,
                    mart_sb_trade.booking_type,
                    COALESCE(mart_sb_trade.execution_price, mart_sb_trade.price_at_booking) as PRICE,
                    mart_sb_trade.net_size AS QUANTITY
                FROM
                    TEAMS_PRD.ASSET_HUB.PBL_CURR__SHARE_BOOKING as mart_sb_trade
                WHERE
                    convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::date  BETWEEN %s AND %s
                AND
                    mart_sb_trade.securities_account_number = %s
                AND
                    mart_sb_trade.instrument_id in (%s)

                UNION ALL

                SELECT 
                    convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::timestamp_ntz as time,
                    convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::date as booking_date,
                    ibkr.isin as symbol,
                    IFF(ibkr.notional<0,'S','B') as side,
                    'TRADING_IBKR' AS BOOKING_CATEGORY,
                    IFF(ibkr.notional<0,'SELL','BUY') as BOOKING_CATEGORY,
                    ibkr.price as price,
                    ABS(ibkr.notional)
                FROM 
                    TIBERIUS_PRD.TRADING_PLATFORM_EXTERNAL_SOURCES.MM_INQUISITOR_ENRICHED_TRADES as ibkr
                WHERE
                    1=1
                AND 
                    ibkr.venue='XETR'
                AND
                    convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::date BETWEEN %s AND %s
                AND
                    ibkr.tradingaccount=%s
                AND
                    ibkr.isin in (%s)

                UNION ALL

                SELECT
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::TIMESTAMP_NTZ as TIME,
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::DATE as BOOKING_DATE,
                    jpm_trade."instrument_id" AS SYMBOL,
                    IFF(jpm_trade."trade_direction" = 'SELL','S','B') AS SIDE,
                    CASE
                        WHEN jpm_trade."instrument_id" IS NOT NULL THEN 'TRADING'
                    END AS booking_category,
                    jpm_trade."trade_direction" as booking_type,
                    jpm_trade."execution_price" as PRICE,
                    jpm_trade."execution_size" as QUANTITY,
                FROM
                    BACKEND_PRD.POST_TRADING_TIBERIUS.PUBLIC_TRADE as jpm_trade
                WHERE
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::date  BETWEEN %s AND %s
                AND
                    jpm_trade."sec_acc_no" = %s
                AND
                    jpm_trade."instrument_id" in (%s)
                    
                -- Remove Duplicates
                QUALIFY ROW_NUMBER() OVER(PARTITION BY "id" ORDER BY "updated_at" ASC) = 1
                ORDER BY 2, 1)
                
                
                SELECT
                    tr.TIME,
                    tr.BOOKING_DATE,
                    tr.SYMBOL,
                    tr.SIDE,
                    sec_info."instrument_type" as INSTRUMENT_TYPE,
                    tr.BOOKING_CATEGORY,
                    tr.BOOKING_TYPE,
                    tr.PRICE,
                    tr.QUANTITY
                FROM
                    trades as tr
                INNER JOIN (SELECT 
                                "isin",
                                "instrument_type" 
                            FROM 
                                BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                            WHERE
                                "instrument_type" in (%s)) as sec_info 
                ON tr.SYMBOL = sec_info."isin"
                ORDER BY 2, 1;
            '''

            qry = qry % (db.sqldate(startdate), db.sqldate(enddate), account, db.joinpad(syms),
                        db.sqldate(startdate), db.sqldate(enddate), ibkr_acct, db.joinpad(syms),
                        db.sqldate(startdate), db.sqldate(enddate), account,db.joinpad(syms), 
                        db.joinpad(instrument_type))
        else:
            qry = '''
                    SELECT
                        convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as TIME,
                        mart_sb_trade.booking_date as BOOKING_DATE,
                        mart_sb_trade.instrument_id AS SYMBOL,
                        IFF(mart_sb_trade.booking_direction = 'DEBIT','S','B') AS SIDE,
                        mart_sb_trade.booking_category,
                        mart_sb_trade.booking_type,
                        COALESCE(mart_sb_trade.execution_price, mart_sb_trade.price_at_booking) as PRICE,
                        mart_sb_trade.net_size AS QUANTITY
                    FROM
                        TEAMS_PRD.ASSET_HUB.PBL_CURR__SHARE_BOOKING as mart_sb_trade
                        INNER JOIN (SELECT 
                                        "isin",
                                        "instrument_type" 
                                    FROM 
                                        BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                                    WHERE
                                        "instrument_type" in (%s)) as sec_info
                                ON mart_sb_trade.instrument_id = sec_info."isin"
                    WHERE
                        convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::date BETWEEN %s AND %s
                    AND
                        mart_sb_trade.securities_account_number = %s
                    AND
                        mart_sb_trade.instrument_id in (%s)
                    AND
                        sec_info."instrument_type" in (%s)
                    AND
                        (mart_sb_trade.clearing_id not in ('-5391788484433812345','-3130051740970324751') OR mart_sb_trade.clearing_id IS NULL)
                    ORDER BY 2, 1
                    '''

            # Create String Query
            qry = qry % (db.joinpad(instrument_type), db.sqldate(startdate), db.sqldate(enddate),
                         account, db.joinpad(syms), db.joinpad(instrument_type))

    else:
        if query_eis:
            # EIS Trades query works only on Caligula Trades
            # Needs to direction wise unadjusted net sizes
            print('\t Querying EIS Trades for %s'%account)
            qry = '''
            with trades as (
            SELECT 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
                "isin" as instrument_id,
                IFF("order_type"='SELL','B','S') as side,
                IFF("order_type"='SELL','BUY','SELL') as booking_direction, -- booking direction inverted for customer orders
                'CUSTOMER' as order_type,
                "execution_price" as price,
                "execution_currency" as execution_currency,
                "size" as quantity
                --IFF("order_type"='SELL', 1, -1) * "size" as quantity
            FROM 
                BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_CUSTOMER_ORDER
            WHERE
                "status" = 'EXECUTED'
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= %s
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
            UNION ALL
            SELECT 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
                "isin" as instrument_id,
                IFF("trade_direction"='SELL','S','B') as side,
                "trade_direction" as booking_direction,
                'EIS' as order_type,
                "execution_price" as price,
                "execution_currency" as execution_currency,
                "execution_size" as quantity
                --IFF("trade_direction"='SELL', -1, 1) * "execution_size" as quantity 
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
                convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as trade_ts,
                mart_sb_trade.booking_date as report_date,
                mart_sb_trade.instrument_id AS instrument_id,
                IFF(mart_sb_trade.booking_direction = 'DEBIT','S','B') AS SIDE,
                mart_sb_trade.booking_direction,
                mart_sb_trade.booking_type,
                COALESCE(mart_sb_trade.execution_price, mart_sb_trade.price_at_booking) as PRICE,
                mart_sb_trade.cc__currency_code as execution_currency,
                mart_sb_trade.net_size AS QUANTITY
            FROM
                TEAMS_PRD.ASSET_HUB.PBL_CURR__SHARE_BOOKING as mart_sb_trade
            WHERE
                convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::date  BETWEEN %s AND %s
            AND
                mart_sb_trade.securities_account_number = %s
            AND
               mart_sb_trade.booking_category in ('CORPORATE_ACTION','DELIVERY')
            ORDER BY 1),
        
            
            sec_info AS (
            SELECT 
                "isin" AS INSTRUMENT_ID,
                "instrument_type" AS INSTRUMENT_TYPE,
            FROM 
                BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
            WHERE
                "instrument_type" in (%s)
            ),

            fx_rates AS (
            SELECT 
                reference_dt,
                currency as fx_currency,
                rate as fx_rate 
            FROM 
                TEAMS_PRD.RISK_FUNCTION_SOURCE.src_curr__risk_function_fx_rates 
            WHERE 
                currency='PLN'
            AND
                reference_dt  BETWEEN %s AND %s
            )
            
        
            SELECT
                tr.trade_ts as time,
                tr.report_date as booking_date,
                tr.INSTRUMENT_ID as symbol,
                tr.side as side,
                sc.INSTRUMENT_TYPE as instrument_type,
                tr.booking_direction as booking_category,
                tr.order_type as booking_type,
                IFF(sc.INSTRUMENT_TYPE='BOND' AND tr.order_type='CUSTOMER', tr.PRICE/100, tr.PRICE) as price,
                fx.fx_rate,
                tr.execution_currency,
                tr.QUANTITY AS quantity,
            FROM
                trades AS tr
            INNER JOIN 
                sec_info AS sc
                ON sc.INSTRUMENT_ID = tr.INSTRUMENT_ID
            LEFT JOIN
                fx_rates AS fx
                ON fx.fx_currency=tr.execution_currency AND fx.reference_dt=tr.report_date
            '''


            qry = qry % (db.sqldate(startdate), db.sqldate(enddate), db.sqldate(startdate),
                         db.sqldate(enddate), db.sqldate(startdate), db.sqldate(enddate), account, db.joinpad(instrument_type),
                         db.sqldate(startdate), db.sqldate(enddate))


        elif account in [9800001601, 9800003601]:

            qry ='''--sql
                    WITH trades AS (
                    SELECT
                        convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as TIME,
                        mart_sb_trade.booking_date as BOOKING_DATE,
                        mart_sb_trade.instrument_id AS SYMBOL,
                        IFF(mart_sb_trade.booking_direction = 'DEBIT','S','B') AS SIDE,
                        mart_sb_trade.booking_category,
                        mart_sb_trade.booking_type,
                        COALESCE(mart_sb_trade.execution_price, mart_sb_trade.price_at_booking) as PRICE,
                        mart_sb_trade.net_size AS QUANTITY
                    FROM
                        TEAMS_PRD.ASSET_HUB.PBL_CURR__SHARE_BOOKING as mart_sb_trade
                    WHERE
                        convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::date  BETWEEN %s AND %s
                    AND
                        mart_sb_trade.securities_account_number = %s

                    UNION ALL

                    SELECT 
                        convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::timestamp_ntz as time,
                        convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::date as booking_date,
                        ibkr.isin as symbol,
                        IFF(ibkr.notional<0,'S','B') as side,
                        'TRADING_IBKR' AS BOOKING_CATEGORY,
                        IFF(ibkr.notional<0,'SELL','BUY') as BOOKING_TYPE,
                        ibkr.price as price,
                        ABS(ibkr.notional)
                    FROM 
                        TIBERIUS_PRD.TRADING_PLATFORM_EXTERNAL_SOURCES.MM_INQUISITOR_ENRICHED_TRADES as ibkr
                    WHERE
                        1=1
                    AND 
                        ibkr.venue='XETR'
                    AND
                        convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::date BETWEEN %s AND %s
                    AND
                        ibkr.tradingaccount=%s

                    UNION ALL

                    SELECT
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::TIMESTAMP_NTZ as TIME,
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::DATE as BOOKING_DATE,
                        jpm_trade."instrument_id" AS SYMBOL,
                        IFF(jpm_trade."trade_direction" = 'SELL','S','B') AS SIDE,
                        CASE
                            WHEN jpm_trade."instrument_id" IS NOT NULL THEN 'TRADING'
                        END AS booking_category,
                        jpm_trade."trade_direction" as booking_type,
                        jpm_trade."execution_price" as PRICE,
                        jpm_trade."execution_size" as QUANTITY,
                    FROM
                        BACKEND_PRD.POST_TRADING_TIBERIUS.PUBLIC_TRADE as jpm_trade
                    WHERE
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::date  BETWEEN %s AND %s
                    AND
                        jpm_trade."sec_acc_no" = %s
                        
                    -- Remove Duplicates
                    QUALIFY ROW_NUMBER() OVER(PARTITION BY "id" ORDER BY "updated_at" ASC) = 1
                    ORDER BY 2, 1)
                    
                    
                    SELECT
                        tr.TIME,
                        tr.BOOKING_DATE,
                        tr.SYMBOL,
                        tr.SIDE,
                        sec_info."instrument_type" as INSTRUMENT_TYPE,
                        tr.BOOKING_CATEGORY,
                        tr.BOOKING_TYPE,
                        tr.PRICE,
                        tr.QUANTITY
                    FROM
                        trades as tr
                    INNER JOIN (SELECT 
                                    "isin",
                                    "instrument_type" 
                                FROM 
                                    BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                                WHERE
                                    "instrument_type" in (%s)) as sec_info 
                    ON tr.SYMBOL = sec_info."isin"
                    ORDER BY 2, 1;
            '''

            qry = qry % (db.sqldate(startdate), db.sqldate(enddate), account, 
                         db.sqldate(startdate), db.sqldate(enddate), ibkr_acct,
                         db.sqldate(startdate), db.sqldate(enddate), account, db.joinpad(instrument_type))


        else:
            qry = '''
                    SELECT
                        convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as TIME,
                        mart_sb_trade.booking_date as BOOKING_DATE,
                        mart_sb_trade.instrument_id AS SYMBOL,
                        IFF(mart_sb_trade.booking_direction = 'DEBIT','S','B') AS SIDE,
                        sec_info."instrument_type" as INSTRUMENT_TYPE,
                        mart_sb_trade.booking_category,
                        mart_sb_trade.booking_type,
                        COALESCE(mart_sb_trade.execution_price, mart_sb_trade.price_at_booking) as PRICE,
                        mart_sb_trade.net_size AS QUANTITY
                    FROM
                        TEAMS_PRD.ASSET_HUB.PBL_CURR__SHARE_BOOKING as mart_sb_trade
                    INNER JOIN (SELECT 
                                    "isin",
                                    "instrument_type" 
                                FROM 
                                    BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT) as sec_info
                    ON mart_sb_trade.instrument_id = sec_info."isin"
                    WHERE
                        convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::date  BETWEEN %s AND %s
                    AND
                        mart_sb_trade.securities_account_number = %s
                    ORDER BY 2, 1
                    '''

            # Create String Query
            qry = qry % (db.sqldate(startdate), db.sqldate(enddate), account)


    # Execute Query
    df_trades = db.run_query(query=qry)

    if account == 'tiberius':

        # Querying Additional Trading data from JPM Venue

        qry_tib = '''
                SELECT
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::TIMESTAMP_NTZ as TIME,
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::DATE as BOOKING_DATE,
                    jpm_trade."instrument_id" AS SYMBOL,
                    IFF(jpm_trade."trade_direction" = 'SELL','S','B') AS SIDE,
                    sec_info."instrument_type" as INSTRUMENT_TYPE,
                    CASE
                        WHEN jpm_trade."instrument_id" IS NOT NULL THEN 'TRADING'
                    END AS booking_category,
                    jpm_trade."trade_direction" as booking_type,
                    jpm_trade."execution_price" as PRICE,
                    jpm_trade."execution_size" as QUANTITY,
                    --IFF(jpm_trade."trade_direction" = 'BUY', 1, -1)*jpm_trade."execution_size" AS QUANTITY
                FROM
                    BACKEND_PRD.POST_TRADING_TIBERIUS.PUBLIC_TRADE as jpm_trade
                    INNER JOIN (SELECT 
                                    "isin",
                                    "instrument_type" 
                                FROM 
                                    BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                                WHERE
                                    "instrument_type" in (%s)) as sec_info 
                                    ON jpm_trade."instrument_id" = sec_info."isin"
                WHERE
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::date  BETWEEN %s AND %s
                AND
                    jpm_trade."sec_acc_no" = %s
                AND
                    sec_info."instrument_type" in (%s)
                    
                -- Remove Duplicates
                QUALIFY ROW_NUMBER() OVER(PARTITION BY "id" ORDER BY "updated_at" ASC) = 1
                ORDER BY 2, 1
                '''

        qry_tib = qry_tib % (db.joinpad(instrument_type),db.sqldate(startdate),db.sqldate(enddate),account,db.joinpad(instrument_type))
        df_trades_jpm = db.run_query(query=qry_tib)
        df_trades = pd.concat([df_trades, df_trades_jpm], axis=0)



    elif account == 9800003301:
        # a redemption on XS2326497802 wasn't registered in anonymized_sharebookings. Therefore, we integrate that redemption at the correct price of 101.5
        if 'FULL_CALL' in df_trades[df_trades.symbol == 'XS2326497802'].booking_type:
            raise Exception("WARNING: Redemption detected for XS2326497802 in caligula account")
        else:
            df_douglas = df_trades[df_trades.symbol == 'XS2326497802']
            if df_douglas.empty is False:
                df_redem = get_trades_pnl(account='caracalla', syms=['XS2326497802'], startdate=date(2024, 4, 17), enddate=date(2024, 4, 17))
                df_redem = df_redem.sort_values(by='time')
                df_redem['quantity'] = df_douglas.iloc[:, -1].iloc[0]-df_douglas.iloc[:, -1].iloc[1]
                df_trades = pd.concat([df_trades, df_redem], axis=0)
        
        # Adjusting FX Rate
        df_trades.loc[df_trades.fx_rate.isnull(),'fx_rate']=1.0
        df_trades['price'] = df_trades['price']/df_trades['fx_rate']

    df_trades['multiplier'] = 1

    # Add directional Quantity
    df_trades['quantity_signed'] = np.where(df_trades['side'] == 'S',-1 * df_trades['quantity'],df_trades['quantity'])

    # Add account sec number
    df_trades['account']=account

    if exclude_btype:
        syms_excl = df_trades[df_trades.booking_type.isin(exclude_btype)].symbol.unique()
        df_trades = df_trades[~df_trades.symbol.isin(syms_excl)]

    if add_filter == 'ca':
        syms_incl = df_trades[df_trades.booking_category == 'CORPORATE_ACTION'].symbol.unique()
        df_trades = df_trades[df_trades.symbol.isin(syms_incl)]

    df_trades = df_trades.sort_values(by='time')

    return df_trades


def get_trades_pnl_new(account=None,startdate=None,enddate=None,data_src=None):
    """
    Trades Query for PnL Purpose that Picks up accounts and adds sec infos

    @param account: str, e.g. 'caligula'
    @param startdate: date object
    @param enddate: date object
    @param data_src: str, 'dwh' or 'eis'
    @return:
    """

    if startdate is None:
        raise Exception('\t ERROR: You need to Specify a Startdate')
    if enddate is None:
        raise Exception('\t ERROR: You need to Specify an Enddate')
    
    tr_query = '''
        SELECT
            *
        FROM
            TEAMS_PRD.RISK_FUNCTION_TRANSFORM.trf__risk_function_mrm_book_%s_daily_pnl_trades
        WHERE
            report_date >=%s 
        AND 
            report_date <=%s 
        AND
            data_src_primary='%s'
        ORDER BY trade_ts
        '''

    tr_query = tr_query % (str(account), db.sqldate(startdate), db.sqldate(enddate),data_src)

    # Fetch Trades:
    df_trades = db.run_query(query=tr_query)


    # format columns:
    df_trades['multiplier'] = 1
    df_trades['booking_category'] = 'TRADING'
    df_trades['booking_type']= 'TRADING'
    df_trades = df_trades[['trade_ts', 'report_date', 'instrument_id', 'side', 'booking_category','booking_type',
                           'price', 'quantity', 'quantity_signed','multiplier','data_src_primary']]
    df_trades.columns = ['time', 'booking_date', 'symbol', 'side', 'booking_category','booking_type',
                         'price', 'quantity', 'quantity_signed','multiplier','data_src_primary']


    return df_trades






def get_trades_pnl_test(account=None,syms=None,instrument_type=None,startdate=None,enddate=None,query_eis=False,exclude_btype=False,add_filter=None):
    """
    Testing Trades Query for PnL Purpose that Picks up accounts and adds sec infos

    FB 20240904:
    Current adjustments:
        - Excluding Cancelations
        - Reordering for rebookings

    @param account: str, e.g. 'caligula'
    @param syms: list of ISINs
    @param instrument_type: str, 'FUND', 'STOCK' etc
    @param startdate: date object
    @param enddate: date object
    @param query_eis: boolean, if True queries EIS trades for Caligula only
    @param exclude_btype:
    @param add_filter:
    @return:
    """

    if startdate is None:
        raise Exception('\t ERROR: You need to Specify a Startdate')
    if enddate is None:
        raise Exception('\t ERROR: You need to Specify an Enddate')

    if instrument_type is None:
        instrument_type = ['STOCK','FUND','DERIVATIVE','BOND']

    if account == 'caracalla':
        account_qry = 9800001301
    elif account == 'caligula':
        account_qry = 9800003301
    elif account == 'tiberius':
        account_qry = 9800001601
    elif account == 'alg':
        account_qry = 9800000201
    elif account is None:
        raise Exception('ERROR: You need to Specify an Account')
    else:
        account_qry = account

    # Get Trades    ********************************************
    if syms:

        qry = '''
                SELECT
                    convert_timezone('Europe/Berlin',sb_trade."booked_at")::TIMESTAMP_NTZ as TIME,
                    sb_trade."booking_date" as BOOKING_DATE,
                    sb_trade."instrument_id" as SYMBOL,
                    IFF(sb_trade."booking_direction" = 'DEBIT','S','B') as SIDE,
                    sec_info."instrument_type" as INSTRUMENT_TYPE,
                    "booking_category" as booking_category,
                    "booking_type" as booking_type,
                    sb_trade."execution_price" as PRICE,
                    --IFF(sb_trade."booking_direction" = 'DEBIT', -1*sb_trade."net_size", sb_trade."net_size") AS QUANTITY
                    sb_trade."net_size" as QUANTITY
                FROM
                    BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING as sb_trade
                    INNER JOIN (SELECT 
                                    "isin",
                                    "instrument_type" 
                                FROM 
                                    BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                                WHERE
                                    "instrument_type" in (%s)) as sec_info
                            ON sb_trade."instrument_id" = sec_info."isin"
                WHERE
                    convert_timezone('Europe/Berlin',sb_trade."booked_at")::date BETWEEN %s AND %s
                AND
                    sb_trade."sec_acc_no" = %s
                AND
                    sb_trade."instrument_id" in (%s)
                AND
                    sec_info."instrument_type" in (%s)
                AND
                    (sb_trade."clearing_id" not in ('-5391788484433812345','-3130051740970324751') OR sb_trade."clearing_id" IS NULL)
                ORDER BY sb_trade."booking_date",sb_trade."booked_at" --testing purposes ordering for rebookings
                '''

        # Create String Query
        qry = qry % (db.joinpad(instrument_type),db.sqldate(startdate),db.sqldate(enddate),
                     account_qry,db.joinpad(syms),db.joinpad(instrument_type))

    else:
        if query_eis:
            # EIS Trades query works only on Caligula Trades
            print('\t Querying EIS Trades for %s' % account)
            qry = '''
            with trades as (
            SELECT 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
                "isin" as instrument_id,
                IFF("order_type"='SELL','B','S') as side,
                IFF("order_type"='SELL','BUY','SELL') as booking_direction, -- booking direction inverted for customer orders
                'CUSTOMER' as order_type,
                "execution_price" as price,
                "size" as quantity
                --IFF("order_type"='SELL', 1, -1) * "size" as quantity
            FROM 
                BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_CUSTOMER_ORDER
            WHERE
                "status" = 'EXECUTED'
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= %s
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
            UNION ALL
            SELECT 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
                "isin" as instrument_id,
                IFF("trade_direction"='SELL','S','B') as side,
                "trade_direction" as booking_direction,
                'EIS' as order_type,
                "execution_price" as price,
                "execution_size" as quantity
                --IFF("trade_direction"='SELL', -1, 1) * "execution_size" as quantity
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
                IFF("booking_direction"='DEBIT','S','B') as side,
                "booking_direction" as booking_direction,
                "booking_type" as order_type,
                "execution_price" AS price,
                "net_size" AS quantity
                --IFF("booking_direction"='CREDIT', "net_size", -"net_size") AS quantity
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
            ORDER BY 1),


            sec_info AS (
            SELECT 
                "isin" AS INSTRUMENT_ID,
                "instrument_type" AS INSTRUMENT_TYPE,
            FROM 
                BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
            WHERE
                "instrument_type" in (%s)
            )


            SELECT
                tr.trade_ts as time,
                tr.report_date as booking_date,
                tr.INSTRUMENT_ID as symbol,
                tr.side as side,
                sc.INSTRUMENT_TYPE as instrument_type,
                tr.booking_direction as booking_category,
                tr.order_type as booking_type,
                IFF(sc.INSTRUMENT_TYPE='BOND' AND tr.order_type='CUSTOMER', tr.PRICE/100, tr.PRICE) as price,
                tr.QUANTITY AS quantity,
            FROM
                trades AS tr
            INNER JOIN 
                sec_info AS sc
                ON sc.INSTRUMENT_ID = tr.INSTRUMENT_ID
            '''

            qry = qry % (db.sqldate(startdate),db.sqldate(enddate),db.sqldate(startdate),
                         db.sqldate(enddate),db.sqldate(startdate),db.sqldate(enddate),db.joinpad(instrument_type))

        else:
            qry = '''
                    SELECT
                        convert_timezone('Europe/Berlin',sb_trade."booked_at")::TIMESTAMP_NTZ as TIME,
                        sb_trade."booking_date" as BOOKING_DATE,
                        sb_trade."instrument_id" AS SYMBOL,
                        IFF(sb_trade."booking_direction" = 'DEBIT','S','B') AS SIDE,
                        sec_info."instrument_type" as INSTRUMENT_TYPE,
                        "booking_category" as booking_category,
                        "booking_type" as booking_type,
                        sb_trade."execution_price" as PRICE,
                        --IFF(sb_trade."booking_direction" = 'DEBIT', -1*sb_trade."net_size", sb_trade."net_size") AS QUANTITY
                        sb_trade."net_size" AS QUANTITY
                    FROM
                        BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING as sb_trade
                        INNER JOIN (SELECT 
                                        "isin",
                                        "instrument_type" 
                                    FROM 
                                        BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                                    WHERE
                                        "instrument_type" in (%s)) as sec_info 
                                        ON sb_trade."instrument_id" = sec_info."isin"
                    WHERE
                        convert_timezone('Europe/Berlin',sb_trade."booked_at")::date  BETWEEN %s AND %s
                    AND
                        sb_trade."sec_acc_no" = %s
                    AND
                        sb_trade."unhashed_clearing_id" NOT LIKE '%%C%%'
                    AND
                        sec_info."instrument_type" in (%s)
                    AND
                        (sb_trade."clearing_id" not in ('-5391788484433812345','-3130051740970324751') OR sb_trade."clearing_id" IS NULL)
                    ORDER BY sb_trade."booking_date",sb_trade."booked_at" --testing purposes ordering for rebookings
                    '''

            # Create String Query
            qry = qry % (db.joinpad(instrument_type),db.sqldate(startdate),db.sqldate(enddate),account_qry,db.joinpad(instrument_type))

    # Execute Query
    df_trades = db.run_query(query=qry)

    if account == 'tiberius':

        # Querying Additional Trading data from JPM Venue

        qry_tib = '''
                SELECT
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::TIMESTAMP_NTZ as TIME,
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::DATE as BOOKING_DATE,
                    jpm_trade."instrument_id" AS SYMBOL,
                    IFF(jpm_trade."trade_direction" = 'SELL','S','B') AS SIDE,
                    sec_info."instrument_type" as INSTRUMENT_TYPE,
                    CASE
                        WHEN jpm_trade."instrument_id" IS NOT NULL THEN 'TRADING'
                    END AS booking_category,
                    jpm_trade."trade_direction" as booking_type,
                    jpm_trade."execution_price" as PRICE,
                    jpm_trade."execution_size" as QUANTITY,
                    --IFF(jpm_trade."trade_direction" = 'BUY', 1, -1)*jpm_trade."execution_size" AS QUANTITY
                FROM
                    BACKEND_PRD.POST_TRADING_TIBERIUS.PUBLIC_TRADE as jpm_trade
                    INNER JOIN (SELECT 
                                    "isin",
                                    "instrument_type" 
                                FROM 
                                    BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                                WHERE
                                    "instrument_type" in (%s)) as sec_info 
                                    ON jpm_trade."instrument_id" = sec_info."isin"
                WHERE
                    convert_timezone('Europe/Berlin',jpm_trade."executed_at")::date  BETWEEN %s AND %s
                AND
                    jpm_trade."sec_acc_no" = %s
                AND
                    sec_info."instrument_type" in (%s)

                -- Remove Duplicates
                QUALIFY ROW_NUMBER() OVER(PARTITION BY "id" ORDER BY "updated_at" ASC) = 1
                ORDER BY 2, 1
                '''

        qry_tib = qry_tib % (db.joinpad(instrument_type),db.sqldate(startdate),db.sqldate(enddate),account_qry,db.joinpad(instrument_type))
        df_trades_jpm = db.run_query(query=qry_tib)
        df_trades = pd.concat([df_trades,df_trades_jpm],axis=0)



    elif account == 'caligula':
        # a redemption on XS2326497802 wasn't registered in anonymized_sharebookings. Therefore, we integrate that redemption at the correct price of 101.5
        if 'REDEMPTION' in df_trades[df_trades.symbol == 'XS2326497802'].booking_type:
            raise Exception("WARNING: Redemption detected for XS2326497802 in caligula account")
        else:
            df_douglas = df_trades[df_trades.symbol == 'XS2326497802']
            if df_douglas.empty is False:
                df_redem = get_trades_pnl(account='caracalla',syms=['XS2326497802'],startdate=date(2024,4,17),enddate=date(2024,4,17))
                df_redem = df_redem.sort_values(by='time')
                df_redem['quantity'] = df_douglas.iloc[:,-1].iloc[0] - df_douglas.iloc[:,-1].iloc[1]
                df_trades = pd.concat([df_trades,df_redem],axis=0)

    df_trades['multiplier'] = 1

    if exclude_btype:
        syms_excl = df_trades[df_trades.booking_type.isin(exclude_btype)].symbol.unique()
        df_trades = df_trades[~df_trades.symbol.isin(syms_excl)]

    if add_filter == 'ca':
        syms_incl = df_trades[df_trades.booking_category == 'CORPORATE_ACTION'].symbol.unique()
        df_trades = df_trades[df_trades.symbol.isin(syms_incl)]

    df_trades = df_trades.sort_values(by='time')

    return df_trades


def get_trades_caligula_eis():

    qry = '''
    SELECT 
        convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
        convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
        "isin" as instrument_id,
        "order_type" as booking_direction,
        'customer' as order_type,
        "execution_price" as price,
        IFF("order_type"='SELL', 1, -1) * "size" as quantity
    FROM 
        BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_CUSTOMER_ORDER
    WHERE
        "status" = 'EXECUTED'
    UNION ALL
    SELECT 
        convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
        convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
        "isin" as instrument_id,
        "trade_direction" as booking_direction,
        'eis' as order_type,
        "execution_price" as price,
        IFF("trade_direction"='SELL', -1, 1) * "execution_size" as quantity
    FROM 
        BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_INVENTORY_TRADE
    '''

    df_trades = db.run_query(query=qry).sort_values(by='trade_ts')

    return df_trades


def get_trades_ptf_src():
    #ToDo: @Vicky here adjust for Ana's query
    print('Hello vicky')


def pos_to_csv(rep_name='pos', account='caracalla', pth=None, verbose=True):

    if not isinstance(pth, str):
        raise ValueError('ERROR: Path is missing. Pass pth variable!')

    import os

    for fname in [k for k in os.listdir(pth) if k.endswith('all_tmp_%s.pkl'%rep_name)]:
        df_db = pd.read_pickle(os.path.join(pth, fname))

        if rep_name == 'pos':
            df_db['account'] = account
            df_db = df_db[['time', 'account', 'symbol', 'price', 'quantity', 'rpnl', 'upnl']]
            for col in ['price', 'quantity', 'rpnl', 'upnl']:
                df_db[col] = df_db[col].fillna(0)

            df_db.columns = ['REPORT_DATE', 'ACCOUNT', 'INSTRUMENT_ID', 'PRICE', 'QUANTITY', 'R_PNL', 'U_PNL']

        elif rep_name == 'cache':
            df_db['account'] = account
            rep_date = _datetime.strptime(fname.split('_')[0][-10:-3]+fname.split('_')[1][-2:], '%Y%m%d')
            df_db['report_date'] = rep_date.replace(hour=23, minute=30)
            df_db = df_db[['report_date', 'time', 'account', 'symbol', 'side', 'price', 'quantity', 'multiplier']]
            # Rename Columns
            df_db.columns = ['REPORT_DATE','TRADE_DATE','ACCOUNT','INSTRUMENT_ID','SIDE','PRICE','QUANTITY','MULTIPLIER']

        elif rep_name == 'trades':
            df_db = df_db.reset_index()
            df_db['account'] = account
            df_db = df_db[['index', 'account', 'symbol', 'quantity', 'rpnl']]
            for col in ['quantity', 'rpnl']:
                df_db[col] = df_db[col].fillna(0)

            df_db.columns = ['TRADE_DATE', 'ACCOUNT', 'INSTRUMENT_ID', 'QUANTITY', 'R_PNL']




        if verbose:
            print('\t Parsing Data to CSV')
            print('\t ************************************** \n')
            print(df_db.tail())
            print('\t ************************************** \n')
            print(len(df_db))

        df_db.to_csv(os.path.join(pth, fname[:-3]) + 'csv', index=False)



def get_trades_cache(report_date=None, verbose=True):

    if verbose:
        print('\n Retrieving PnL Cached Trades')

    qry = '''
          SELECT * FROM TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL WHERE REPORT_DATE = %s
          '''

    df_cache = db.run_query(query = qry%db.sqldate(report_date))

    # Adjust Output
    df_cache = df_cache[['trade_date', 'instrument_id', 'side', 'price', 'quantity', 'multiplier']]
    df_cache.columns = ['time', 'symbol', 'side', 'price', 'quantity', 'multiplier']

    return df_cache


def build_initial_cache(syms=None, startdate=None, enddate=None, verbose=True):


    if verbose:
        print('\n Retrieving Cache ***************************************')

    # Build in Cache Trades ********************************************
    if verbose:
        print('\t Building Trade Cache')

    df_trades = get_trades_pnl(syms=syms, startdate=startdate + timedelta(1),enddate=enddate)
    CF.cache_pnl_trade = df_trades.copy()

    # Build in Cache Prices ********************************************
    if verbose:
        print('\t Building Price Cache')
    prx = get_prices_eod(startdate=startdate, enddate=enddate, read_full_dwh=True)
    CF.cache_pnl_prices = prx.copy()

    # Build in Cache Port ********************************************
    if verbose:
        print('\t Building Position Cache')
        df_cache = get_trades_cache(report_date=startdate, verbose=verbose)
        CF.cache_pnl_cache = df_cache.copy()

    # if verbose:
    #     print('\t Building Price Cache')
    # df_port = c_port.get_caracalla_portfolio()['inventory']
    # CF.cache_pnl_port = df_port.copy()



def parse_pos_old(tmp_pos_orig, verbose=True):
    """
    Quick Program to Parse Cache DAta for PnL
    @param tmp_cache:
    @param verbose:
    @return:
    """

    tmp_pos = tmp_pos_orig.copy()

    if verbose:
        print('\n Adjusting Cache Data')

    tmp_pos['account'] = 'caracalla'
    tmp_pos = tmp_pos.dropna()
    tmp_pos = tmp_pos[['time', 'account', 'symbol', 'price', 'quantity', 'rpnl', 'upnl']]
    tmp_pos.columns = ['report_date', 'account', 'instrument_id', 'price', 'quantity', 'r_pnl', 'u_pnl']

    if verbose:
        print('\n Creating Dummy Table for Positions')

    db.run_query(query='''CREATE TABLE 
                            TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL_DUMMY 
                          LIKE 
                            TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL''')

    if verbose:
        print('\n Parsing Pos')
    len_tmp_pos = len(tmp_pos)
    db.pandas2db(tmp_pos[:7500], 'TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL_DUMMY')
    if len(tmp_pos) >= 15000:
        db.pandas2db(tmp_pos[7500:15000], 'TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL_DUMMY')
    if len(tmp_pos) >= 15000:
        db.pandas2db(tmp_pos[15000:22500], 'TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL_DUMMY')
    if len(tmp_pos) >= 22500:
        db.pandas2db(tmp_pos[22500:], 'TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL_DUMMY')


    if verbose:
        print('\n Merging Positions with Target Table')

    qry_pnl_pos = '''
    merge into TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL as tgt_table 
    using TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL_DUMMY as src_table 
    on(tgt_table.report_date = src_table.report_date AND tgt_table.account = src_table.account 
    AND tgt_table.instrument_id = src_table.instrument_id) when not matched then 
    insert(report_date,account,instrument_id,price,quantity,r_pnl,u_pnl) 
    values(src_table.report_date,src_table.account,src_table.instrument_id,
    src_table.price,src_table.quantity,src_table.r_pnl,src_table.u_pnl)
    '''

    db.run_query(query=qry_pnl_pos)

    if verbose:
        print('\n Deleting Pos Table')
    db.run_query(query='''DROP TABLE TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL_DUMMY''')



def parse_cache(tmp_cache_orig, enddate, verbose=True):
    """
    Quick Program to Parse Cache Data for PnL
    @param tmp_cache:
    @param verbose:
    @return:
    """

    tmp_cache = tmp_cache_orig.copy()

    if verbose:
        print('\n Adjusting Cache Data')

    tmp_cache['report_date'] = _datetime(enddate.year, enddate.month, enddate.day, 0, 0, 0)
    tmp_cache['account'] = 'caracalla'
    tmp_cache = tmp_cache.dropna()
    tmp_cache = tmp_cache[['report_date', 'time', 'account', 'symbol', 'side', 'price', 'quantity', 'multiplier']]
    tmp_cache.columns = ['report_date', 'trade_date', 'account', 'instrument_id', 'side', 'price', 'quantity', 'multiplier']


    if verbose:
        print('\n Creating Dummy Table for Cache Trades')
    db.run_query(query='''CREATE TABLE 
                            TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY 
                          LIKE 
                            TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL''')

    if verbose:
        print('\n Parsing Cache Trades')
    db.pandas2db(tmp_cache[:10000], 'TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY')
    db.pandas2db(tmp_cache[10000:20000], 'TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY')
    db.pandas2db(tmp_cache[20000:30000], 'TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY')
    db.pandas2db(tmp_cache[30000:40000], 'TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY')
    if len(tmp_cache) >= 40000:
        db.pandas2db(tmp_cache[40000:50000], 'TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY')
    if len(tmp_cache) >= 50000:
        db.pandas2db(tmp_cache[50001:60000], 'TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY')
    if len(tmp_cache) >= 60000:
        db.pandas2db(tmp_cache[60001:70000], 'TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY')
    if len(tmp_cache) >= 70000:
        db.pandas2db(tmp_cache[70001:80000], 'TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY')


    if verbose:
        print('\n Merging Cache Trades with Target Table')

    qry_pnl_cache = '''
    merge into TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL as tgt_table 
    using TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY as src_table 
    on(tgt_table.report_date = src_table.report_date AND tgt_table.trade_Date = src_table.trade_date 
    AND tgt_table.account = src_table.account 
    AND tgt_table.instrument_id = src_table.instrument_id) when not matched 
    then insert(report_date,trade_date,account,instrument_id,side,price,quantity,multiplier) 
    values(src_table.report_date,src_table.trade_date,src_table.account,src_table.instrument_id,src_table.side,src_table.price,
    src_table.quantity,src_table.multiplier)
    '''

    db.run_query(query=qry_pnl_cache)

    if verbose:
        print('\n Deleting Dummy Table')
    db.run_query(query='''DROP TABLE TEAMS_PRD.RISK_DATA.MR_PORT_CACHE_PNL_DUMMY''')



def pnl_trades_eq(ddate, sym):
    """
    New PnL Trade function for Equity trades
    @param ddate: date object
    @param sym: ISIN, e.g. DE0007664039 (Volkswagen)
    @return:
    """

    qry = '''
            WITH trade_base AS (
            SELECT
                CONVERT_TIMEZONE('UTC','Europe/Berlin',trade_ts)::DATE AS calendar_date,
                CONVERT_TIMEZONE('UTC','Europe/Berlin',trade_ts) AS trade_ts,
                instrument_id,
                portfolio_id,
                trade_type,
                trade_id,
                exchange_id,
                CASE
                    WHEN direction = 'SELL' AND exchange_id = 'TIB' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TIB' THEN 'SELL'
                    WHEN direction = 'SELL' AND exchange_id = 'TRPT' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TRPT' THEN 'SELL'
                    ELSE direction
                    END AS trade_direction_adj,
                original_price AS price,
                IFF(trade_direction_adj = 'BUY' ,original_size, original_size * (-1)) AS signed_qty_column,
                signed_qty_column * original_price AS signed_vol
            FROM TEAMS_PRD.CORE_MART.MRT_CURR__TRADE_BACKEND t
            WHERE
                (securities_account_number = '9800001301' OR exchange_id = 'TIB' OR exchange_id = 'TRPT')
                AND NOT (securities_account_number = '9800001301' AND exchange_id = 'TIB')
                AND instrument_type NOT IN ('CRYPTO','BOND','DERIVATIVE')
                AND (calendar_date != CONVERT_TIMEZONE('UTC','Europe/Berlin',first_cancellation_received_ts)::DATE
                OR first_cancellation_received_ts IS NULL)
                AND latest_status IN ('ORIGINAL','CANCEL')
                AND calendar_date >= %s
                AND instrument_id = '%s'
        
            UNION ALL
        
            SELECT
                CONVERT_TIMEZONE('UTC','Europe/Berlin',first_cancellation_received_ts)::DATE AS calendar_date,
                CONVERT_TIMEZONE('UTC','Europe/Berlin',first_cancellation_received_ts) AS trade_ts,
                instrument_id,
                portfolio_id,
                trade_type,
                trade_id,
                exchange_id,
                CASE
                    WHEN direction = 'SELL' AND exchange_id = 'TIB' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TIB' THEN 'SELL'
                    WHEN direction = 'SELL' AND exchange_id = 'TRPT' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TRPT' THEN 'SELL'
                    ELSE direction
                    END AS trade_direction_adj,
                price,
                IFF(trade_direction_adj = 'BUY' ,size, size * (-1)) AS signed_qty_column,
                signed_qty_column * price AS signed_vol
            FROM TEAMS_PRD.CORE_MART.MRT_CURR__TRADE_BACKEND t
            WHERE
                (securities_account_number = '9800001301' OR exchange_id = 'TIB' OR exchange_id = 'TRPT')
                AND NOT (securities_account_number = '9800001301' AND exchange_id = 'TIB')
                AND instrument_type NOT IN ('CRYPTO','BOND','DERIVATIVE')
                AND (TRADE_TS::DATE != CONVERT_TIMEZONE('UTC','Europe/Berlin',first_cancellation_received_ts)::DATE
                OR first_cancellation_received_ts IS NULL)
                AND latest_status IN ('NEW')
                AND calendar_date >= %s
                AND instrument_id = '%s'
        )
        
        SELECT
            calendar_date,
            trade_ts,
            instrument_id,
            portfolio_id,
            trade_id,
            price,
            signed_qty_column
        FROM
            trade_base
        ORDER BY 2;
      '''


    df = db.run_query(query=qry%(db.sqldate(ddate), sym, db.sqldate(ddate), sym))


    return df



def trades_recon(startdate, enddate, symbol):


    qry = '''            
            WITH eq_inv_tr AS (
            -- Fetching Trades from a Backend Tables that gives the inventory trades
            SELECT 
                bck_trade."booked_at"::DATE as DDATE,
                SUM(IFF(bck_trade."booking_direction" = 'DEBIT', -1*bck_trade."net_size", bck_trade."net_size")) AS QTY_EQ_INV
            FROM 
                BACKEND_PRD.EQUITIES_INVENTORY.ANONYMIZED_SHARE_BOOKING as bck_trade
            where 
                1=1
            AND 
                bck_trade."isin" = '%s'
            AND
                DDATE BETWEEN %s AND %s
            GROUP BY DDATE
            ORDER BY DDATE
            ),
            
            sb_tr AS (
            -- Anonymized ShareBookings
            SELECT
                sb_trade."booking_date" as DDATE,
                SUM(IFF(sb_trade."booking_direction" = 'DEBIT', -1*sb_trade."net_size", sb_trade."net_size")) AS QTY_SB
            FROM
                BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING as sb_trade
            WHERE
                sb_trade."instrument_id" = '%s'
            AND
                sb_trade."booking_date" BETWEEN %s AND %s
            AND
                sb_trade."sec_acc_no" = 9800001301
            GROUP BY DDATE
            ORDER BY DDATE
            ),
            
            mart_trades_raw as (
            -- Anonymized MART Trades Raw
            SELECT
                CONVERT_TIMEZONE('UTC','Europe/Berlin',trade_ts)::DATE AS calendar_date,
                CONVERT_TIMEZONE('UTC','Europe/Berlin',trade_ts) AS trade_ts,
                instrument_id,
                portfolio_id,
                trade_type,
                trade_id,
                exchange_id,
                CASE
                    WHEN direction = 'SELL' AND exchange_id = 'TIB' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TIB' THEN 'SELL'
                    WHEN direction = 'SELL' AND exchange_id = 'TRPT' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TRPT' THEN 'SELL'
                    ELSE direction
                    END AS trade_direction_adj,
                original_price AS price,
                IFF(trade_direction_adj = 'BUY' ,original_size, original_size * (-1)) AS signed_qty_column,
                signed_qty_column * original_price AS signed_vol
            FROM TEAMS_PRD.CORE_MART.MRT_CURR__TRADE_BACKEND t
            WHERE
                (securities_account_number = '9800001301' OR exchange_id = 'TIB' OR exchange_id = 'TRPT')
                AND NOT (securities_account_number = '9800001301' AND exchange_id = 'TIB')
                AND instrument_type NOT IN ('CRYPTO','BOND','DERIVATIVE')
                AND (calendar_date != CONVERT_TIMEZONE('UTC','Europe/Berlin',first_cancellation_received_ts)::DATE
                OR first_cancellation_received_ts IS NULL)
                AND latest_status IN ('ORIGINAL','CANCEL')
                AND calendar_date BETWEEN %s AND %s
                AND instrument_id = '%s'
            
            UNION ALL
            
            SELECT
                CONVERT_TIMEZONE('UTC','Europe/Berlin',first_cancellation_received_ts)::DATE AS calendar_date,
                CONVERT_TIMEZONE('UTC','Europe/Berlin',first_cancellation_received_ts) AS trade_ts,
                instrument_id,
                portfolio_id,
                trade_type,
                trade_id,
                exchange_id,
                CASE
                    WHEN direction = 'SELL' AND exchange_id = 'TIB' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TIB' THEN 'SELL'
                    WHEN direction = 'SELL' AND exchange_id = 'TRPT' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TRPT' THEN 'SELL'
                    ELSE direction
                    END AS trade_direction_adj,
                price,
                IFF(trade_direction_adj = 'BUY' ,size, size * (-1)) AS signed_qty_column,
                signed_qty_column * price AS signed_vol
            FROM TEAMS_PRD.CORE_MART.MRT_CURR__TRADE_BACKEND t
            WHERE
                (securities_account_number = '9800001301' OR exchange_id = 'TIB' OR exchange_id = 'TRPT')
                AND NOT (securities_account_number = '9800001301' AND exchange_id = 'TIB')
                AND instrument_type NOT IN ('CRYPTO','BOND','DERIVATIVE')
                AND (TRADE_TS::DATE != CONVERT_TIMEZONE('UTC','Europe/Berlin',first_cancellation_received_ts)::DATE
                OR first_cancellation_received_ts IS NULL)
                AND latest_status IN ('NEW')
                AND calendar_date BETWEEN %s AND %s
                AND instrument_id = '%s'
            ),
            
            mart_trades AS (
            SELECT
                calendar_date AS DDATE,
                SUM(signed_qty_column) AS QTY_MART
            FROM
                mart_trades_raw
            GROUP BY
                DDATE
            ),
            
            reg_pos as (
            SELECT
                pos.CALENDAR_DATE AS DDATE, 
                pos.POSITION_EOD AS QTY_REG
            FROM
                teams_prd.investing_publish.pbl__curr__ft_regulatory_reporting as pos
            WHERE
                CALENDAR_DATE BETWEEN %s AND %s
            AND
                pos.INSTRUMENT_ID = '%s'
            ORDER BY
                1 DESC
            ),
            
            risk_pos as (
            SELECT
                rp.REPORT_DATE::date AS DDATE, 
                rp.QUANTITY AS QTY_RISK
            FROM
                TEAMS_PRD.RISK_DATA.MR_PORT_POS AS rp
            WHERE
                rp.REPORT_DATE BETWEEN %s AND %s
            AND
                rp.INSTRUMENT_ID = '%s'
            ORDER BY
                1 DESC
            ),
            
            
            
            ddate_initiate AS (
            SELECT
                eq.DDATE
            FROM
                 eq_inv_tr AS eq
            
            UNION ALL
            
                SELECT
                    sb.DDATE
                FROM
                    sb_tr AS sb
            
            UNION ALL
            
                SELECT
                    reg.DDATE
                FROM
                    reg_pos AS reg
                    
            UNION ALL
            
                SELECT
                    ma.DDATE
                FROM
                    mart_trades AS ma
            
            UNION ALL
            
                SELECT
                    rp.DDATE
                FROM
                    risk_pos AS rp          
            ),
            
            unique_ddate AS (
                SELECT
                    DISTINCT dd_init.DDATE
                FROM
                    ddate_initiate AS dd_init
            )
            
            
            SELECT
                ddate_uni.DDATE,
                eq.QTY_EQ_INV,
                sb.QTY_SB,
                ma.QTY_MART,
                reg_p.QTY_REG,
                rp.QTY_RISK
            FROM
                unique_ddate as ddate_uni
                LEFT JOIN  eq_inv_tr AS eq ON ddate_uni.DDATE = eq.DDATE
                LEFT JOIN  sb_tr AS sb ON ddate_uni.DDATE = sb.DDATE
                LEFT JOIN  mart_trades AS ma ON ddate_uni.DDATE = ma.ddate
                LEFT JOIN  reg_pos AS reg_p ON ddate_uni.DDATE = reg_p.ddate
                LEFT JOIN  risk_pos AS rp ON ddate_uni.DDATE = rp.ddate
            ORDER BY
                DDATE
    '''

    sql_sdate = db.sqldate(startdate)
    sql_edate = db.sqldate(enddate)
    qry_adj = qry%(symbol, sql_sdate, sql_edate,
                   symbol, sql_sdate, sql_edate,
                   sql_sdate, sql_edate, symbol,
                   sql_sdate, sql_edate, symbol,
                   sql_sdate, sql_edate, symbol,
                   sql_sdate, sql_edate, symbol)

    df = db.run_query(query=qry_adj)

    return df


def trades_sym_recon_sb_risk(startdate, enddate, symbol):


    qry = '''            
            WITH sb_tr AS (
            -- Anonymized ShareBookings
            SELECT
                sb_trade."booked_at"::DATE as DDATE,
                SUM(IFF(sb_trade."booking_direction" = 'DEBIT', -1*sb_trade."net_size", sb_trade."net_size")) AS QTY_SB
            FROM
                BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING as sb_trade
            WHERE
                convert_timezone('Europe/Berlin',sb_trade."booked_at")::DATE  BETWEEN %s AND %s
            AND
                sb_trade."sec_acc_no" = 9800003301
            AND
                sb_trade."instrument_id" = '%s'
            AND
                (sb_trade."clearing_id" not in ('-5391788484433812345','-3130051740970324751') OR sb_trade."clearing_id" IS NULL)
            GROUP BY DDATE
            ORDER BY DDATE),

            risk_pos as (
            SELECT
                rp.REPORT_DATE::date AS DDATE, 
                rp.QUANTITY AS QTY_RISK
            FROM
                TEAMS_PRD.RISK_DATA.MR_PORT_POS AS rp
            WHERE
                rp.REPORT_DATE BETWEEN %s AND %s
            AND
                rp.INSTRUMENT_ID = '%s'
            AND
                rp.ACCOUNT = 'caracalla'
            ORDER BY
                1 DESC
            ),


            ddate_initiate AS (
            SELECT
                sb.DDATE
            FROM
                 sb_tr AS sb

            UNION ALL

                SELECT
                    rp.DDATE
                FROM
                    risk_pos AS rp          
            ),

            unique_ddate AS (
                SELECT
                    DISTINCT dd_init.DDATE
                FROM
                    ddate_initiate AS dd_init
            )


            SELECT
                ddate_uni.DDATE,
                sb.QTY_SB,
                rp.QTY_RISK
            FROM
                unique_ddate as ddate_uni
                LEFT JOIN  sb_tr AS sb ON ddate_uni.DDATE = sb.DDATE
                LEFT JOIN  risk_pos AS rp ON ddate_uni.DDATE = rp.ddate
            ORDER BY
                DDATE
    '''

    sql_sdate = db.sqldate(startdate)
    sql_edate = db.sqldate(enddate)
    qry_adj = qry % (sql_sdate,sql_edate,symbol,
                     sql_sdate,sql_edate,symbol)

    df = db.run_query(query=qry_adj)

    # Format
    df = df.set_index('ddate')
    df = df.dropna(subset=['qty_sb'])
    df['qty_sb'] = df['qty_sb'].cumsum()
    df['delta'] = df['qty_sb'] - df['qty_risk']

    return df



def screen_for_ca(booking_type='SPLIT', startdate=None, enddate=None):

    if startdate is None:
        raise Exception('\t ERROR: You need to Specify a Startdate')
    if enddate is None:
        raise Exception('\t ERROR: You need to Specify an Enddate')

    if booking_type:
        qry = '''
                SELECT
                    "booked_at" as booked_at,
                    "instrument_id" as instrument_id,
                    IFF("booking_direction" = 'DEBIT', -1*"net_size", "net_size") as quantity
                FROM
                    BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING sb
                WHERE
                    "sec_acc_no" = 9800001301
                AND "booking_category" = 'CORPORATE_ACTION'
                AND "booking_type" = '%s'
                AND "booked_at" BETWEEN  %s AND %s
                ORDER BY 1;
                '''

        df = db.run_query(query=qry%(booking_type, db.sqldate(startdate), db.sqldate(enddate)))

    else:
        qry = '''
                SELECT
                    "booked_at" as booked_at,
                    "instrument_id" as instrument_id,
                    IFF("booking_direction" = 'DEBIT', -1*"net_size", "net_size") as quantity
                FROM
                    BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING sb
                WHERE
                    "sec_acc_no" = 9800001301
                AND "booking_category" = 'CORPORATE_ACTION'
                AND "booked_at" BETWEEN  %s AND %s
                ORDER BY 1;
                '''

        df = db.run_query(query=qry % (db.sqldate(startdate),db.sqldate(enddate)))

    # Create Pivot Table
    out = pd.pivot_table(df, index='booked_at', columns='instrument_id', values='quantity')

    return out



def parse_pos(accts, startdate, enddate, pth='/Users/fabioballoni/Downloads/pnl/', merge=True, replace=True):
    """
    Manuel Position and PnL Parser
    @param accts:
    @param startdate:
    @param enddate:
    @return:
    """
    import os

    counter = 1

    for acct in accts:
        start_str=_datetime.strftime(startdate,"%Y%m%d")
        end_str=_datetime.strftime(enddate,"%Y%m%d")
        tmp_pos=pd.read_pickle(os.path.join(pth,'%s_%s_%s_all_recon_tmp_pos_total.pkl'%(start_str,end_str,acct)))
        out_pnl=tmp_pos[['time','account','symbol','rpnl','upnl']]
        out_pnl.columns=['report_date','account','instrument_id','rpnl','upnl']
        out_pos=tmp_pos[['time','account','symbol','price','quantity']]
        out_pos.columns=['report_date','account','instrument_id','price','quantity']

        print("%s. Parsing Data for %s"%(counter,acct))
        db.pandas2db(out_pnl,'TEAMS_PRD.RISK_DATA.MR_PORT_PNL', merge=merge, replace=replace)
        db.pandas2db(out_pos,'TEAMS_PRD.RISK_DATA.MR_PORT_POS', merge=merge, replace=replace)

        counter +=1


def get_trades_pnl_grouped(account=None, instrument_type=None, startdate=None, enddate=None, query_eis=False,exclude_btype=False,add_filter=None):
    """
    Trades Query for PnL Purpose that Picks up accounts and adds sec infos

    @param account: str, e.g. 'caligula'
    @param syms: list of ISINs
    @param instrument_type: str, 'FUND', 'STOCK' etc
    @param startdate: date object
    @param enddate: date object
    @param query_eis: boolean, if True queries EIS trades for Caligula only
    @param exclude_btype:
    @param add_filter:
    @return:
    """

    if startdate is None:
        raise Exception('\t ERROR: You need to Specify a Startdate')
    if enddate is None:
        raise Exception('\t ERROR: You need to Specify an Enddate')

    if instrument_type is None:
        instrument_type = ['STOCK','FUND','DERIVATIVE','BOND']

    if account == 'caracalla':
        account_qry = 9800001301
    elif account == 'caligula':
        account_qry = 9800003301
    elif account == 'tiberius':
        account_qry = 9800001601
        tib_acct=200
    elif account == 'trajan':
        account_qry = 9800003601
        tib_acct=600
    elif account == 'alg':
        account_qry = 9800000201
    elif account is None:
        raise Exception('ERROR: You need to Specify an Account')
    else:
        account_qry = account

    # Get Trades    ********************************************

    if query_eis:
        # EIS Trades query works only on Caligula Trades
        # Needs to direction wise unadjusted net sizes
        print('\t Querying EIS Trades for %s' % account)
        qry = '''
        with trades as (
        SELECT 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_ts,
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date as report_date,
            "isin" as instrument_id,
            IFF("order_type"='SELL','B','S') as side,
            IFF("order_type"='SELL','BUY','SELL') as booking_direction, -- booking direction inverted for customer orders
            'CUSTOMER' as order_type,
            "execution_price" as price,
            CASE
                WHEN "order_type"='SELL' AND "status"='CORRECTED' THEN 1 * "size"
                WHEN "order_type"='BUY' AND "status"='CORRECTED' THEN -1 * "size"
                WHEN "order_type"='SELL' AND "status"='EXECUTED' THEN 1 * "size"
                WHEN "order_type"='BUY' AND "status"='EXECUTED' THEN -1 * "size"
            END as quantity
        FROM 
            BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_CUSTOMER_ORDER
        WHERE
            "status" in ('EXECUTED', 'CORRECTED')
        AND 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= %s
        AND 
            convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
        UNION ALL
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
        UNION ALL
        SELECT
            convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as trade_ts,
            mart_sb_trade.booking_date as report_date,
            mart_sb_trade.instrument_id AS instrument_id,
            IFF(mart_sb_trade.booking_direction = 'DEBIT','S','B') AS SIDE,
            mart_sb_trade.booking_direction,
            mart_sb_trade.booking_type as order_type,
            COALESCE(mart_sb_trade.execution_price, mart_sb_trade.price_at_booking) as PRICE,
            IFF(mart_sb_trade.booking_direction='CREDIT', mart_sb_trade.net_size, -mart_sb_trade.net_size) AS quantity
        FROM
            TEAMS_PRD.ASSET_HUB.PBL_CURR__SHARE_BOOKING as mart_sb_trade
        WHERE
            mart_sb_trade.securities_account_number  = 9800003301
        AND 
            mart_sb_trade.booking_category in ('CORPORATE_ACTION','DELIVERY')
        AND 
            mart_sb_trade.booking_date >= %s
        AND 
            mart_sb_trade.booking_date <= %s
        ORDER BY 1),

        trades_grp as (
        SELECT
            tr.instrument_id,
            SUM(tr.quantity) as quantity
        FROM
            trades as tr
        GROUP BY 1
        ),

        sec_info AS (
        SELECT 
            "isin" AS INSTRUMENT_ID,
            "instrument_type" AS INSTRUMENT_TYPE,
        FROM 
            BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
        WHERE
            "instrument_type" in (%s)
        )


        SELECT
            tr_grp.INSTRUMENT_ID as symbol,
            sc.INSTRUMENT_TYPE as instrument_type,
            tr_grp.QUANTITY AS quantity
        FROM
            trades_grp AS tr_grp
        INNER JOIN 
            sec_info AS sc
            ON sc.INSTRUMENT_ID = tr_grp.INSTRUMENT_ID;
        '''

        qry = qry % (db.sqldate(startdate),db.sqldate(enddate),db.sqldate(startdate),
                     db.sqldate(enddate),db.sqldate(startdate),db.sqldate(enddate),db.joinpad(instrument_type))

    else:
        qry = '''
                with trades as (
                    SELECT
                        convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as TIME,
                        mart_sb_trade.booking_date as BOOKING_DATE,
                        mart_sb_trade.instrument_id AS SYMBOL,
                        IFF(mart_sb_trade.booking_direction = 'DEBIT','S','B') AS SIDE,
                        mart_sb_trade.booking_category,
                        mart_sb_trade.booking_type,
                        mart_sb_trade.execution_price as PRICE,
                        IFF(mart_sb_trade.booking_direction = 'DEBIT', -1*mart_sb_trade.net_size, mart_sb_trade.net_size) AS QUANTITY
                    FROM
                        TEAMS_PRD.ASSET_HUB.PBL_CURR__SHARE_BOOKING as mart_sb_trade
                    WHERE
                        convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::date  BETWEEN %s AND %s
                    AND
                        mart_sb_trade.securities_account_number = %s
                    AND
                        (mart_sb_trade.clearing_id  not in ('-5391788484433812345','-3130051740970324751') OR mart_sb_trade.clearing_id  IS NULL)
                    
                    UNION ALL

                    SELECT 
                        convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::timestamp_ntz as time,
                        convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::date as booking_date,
                        ibkr.isin as symbol,
                        IFF(ibkr.notional<0,'S','B') as side,
                        'TRADING_IBKR' AS BOOKING_CATEGORY,
                        IFF(ibkr.notional<0,'SELL','BUY') as BOOKING_TYPE,
                        ibkr.price as price,
                        ibkr.notional
                    FROM 
                        TIBERIUS_PRD.TRADING_PLATFORM_EXTERNAL_SOURCES.MM_INQUISITOR_ENRICHED_TRADES as ibkr
                    WHERE
                        1=1
                    AND 
                        ibkr.venue='XETR'
                    AND
                        convert_timezone('UTC','Europe/Berlin',TO_TIMESTAMP(ibkr.TIMESTAMP/1e9))::date BETWEEN %s AND %s
                    AND
                        ibkr.tradingaccount=%s

                    UNION ALL

                    SELECT
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::TIMESTAMP_NTZ as TIME,
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::DATE as BOOKING_DATE,
                        jpm_trade."instrument_id" AS SYMBOL,
                        IFF(jpm_trade."trade_direction" = 'SELL','S','B') AS SIDE,
                        CASE
                            WHEN jpm_trade."instrument_id" IS NOT NULL THEN 'TRADING'
                        END AS booking_category,
                        jpm_trade."trade_direction" as booking_type,
                        jpm_trade."execution_price" as PRICE,
                        IFF(jpm_trade."trade_direction"='SELL',-1,1)*jpm_trade."execution_size" as QUANTITY,
                    FROM
                        BACKEND_PRD.POST_TRADING_TIBERIUS.PUBLIC_TRADE as jpm_trade
                    WHERE
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::date  BETWEEN %s AND %s
                    AND
                        jpm_trade."sec_acc_no" = %s
                        
                    -- Remove Duplicates
                    QUALIFY ROW_NUMBER() OVER(PARTITION BY "id" ORDER BY "updated_at" ASC) = 1
                    ORDER BY 2, 1),
                
                sec_info AS (
                    SELECT 
                        "isin" as isin,
                        "instrument_type" as instrument_type
                    FROM 
                        BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                    WHERE
                        "instrument_type" in (%s))
                    
                
                SELECT
                    tr.SYMBOL AS symbol,
                    sec_info.instrument_type AS instrument_type,
                    SUM(tr.QUANTITY) AS quantity
                FROM
                    trades AS tr
                INNER JOIN 
                    sec_info ON tr.SYMBOL = sec_info.isin
                GROUP BY 1, 2
                ORDER BY 1, 2
                '''

        # Create String Query
        qry = qry % (db.sqldate(startdate),db.sqldate(enddate),account_qry,
                     db.sqldate(startdate),db.sqldate(enddate),tib_acct,
                     db.sqldate(startdate),db.sqldate(enddate),account_qry,
                     db.joinpad(instrument_type))

    # Execute Query
    df_trades = db.run_query(query=qry)

    if account == 'tiberius':

        # Querying Additional Trading data from JPM Venue

        qry_tib = '''
                with jpm_trades as (
                    SELECT
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::TIMESTAMP_NTZ as TIME,
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::DATE as BOOKING_DATE,
                        jpm_trade."instrument_id" AS SYMBOL,
                        IFF(jpm_trade."trade_direction" = 'SELL','S','B') AS SIDE,
                        sec_info."instrument_type" as INSTRUMENT_TYPE,
                        CASE
                            WHEN jpm_trade."instrument_id" IS NOT NULL THEN 'TRADING'
                        END AS booking_category,
                        jpm_trade."trade_direction" as booking_type,
                        jpm_trade."execution_price" as PRICE,
                        IFF(jpm_trade."trade_direction" = 'BUY', 1, -1)*jpm_trade."execution_size" AS QUANTITY
                    FROM
                        BACKEND_PRD.POST_TRADING_TIBERIUS.PUBLIC_TRADE as jpm_trade
                        INNER JOIN (SELECT 
                                        "isin",
                                        "instrument_type" 
                                    FROM 
                                        BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT
                                    WHERE
                                        "instrument_type" in (%s)) as sec_info 
                                        ON jpm_trade."instrument_id" = sec_info."isin"
                    WHERE
                        convert_timezone('Europe/Berlin',jpm_trade."executed_at")::date  BETWEEN %s AND %s
                    AND
                        jpm_trade."sec_acc_no" = %s
                    AND
                        sec_info."instrument_type" in (%s)
    
                    -- Remove Duplicates
                    QUALIFY ROW_NUMBER() OVER(PARTITION BY "id" ORDER BY "updated_at" ASC) = 1
                    ORDER BY 2, 1)
                
                SELECT
                    jtr.SYMBOL as symbol,
                    jtr.INSTRUMENT_TYPE as instrument_type,
                    SUM(jtr.QUANTITY) AS quantity
                FROM
                    jpm_trades AS jtr
                GROUP BY 1,2;
                '''

        qry_tib = qry_tib % (db.joinpad(instrument_type),db.sqldate(startdate),db.sqldate(enddate),account_qry,db.joinpad(instrument_type))
        df_trades_jpm = db.run_query(query=qry_tib)
        df_trades = pd.concat([df_trades,df_trades_jpm],axis=0)


    df_trades = df_trades.sort_values(by='symbol')

    return df_trades




def pnl2parquet(acct=None,df_orig=None,report_date=None,pth=None,verbose=True, **kwargs):
    """
    Function to write PnL and Cache Data to Parquet files
    @param acct: str, e.g. 'caligula'
    @param df_orig: DataFrame with PnL or Cache Data
    @param report_date: date object, e.g. _datetime(2025,5,30,23,59,59)
    @param pth: str, path to save the parquet files
    @param verbose: boolean, if True prints status messages
    @param kwargs: additional keyword arguments, e.g. 'cache' or 'pnl'
    @return: None
    This function will write the DataFrame to a Parquet file in the specified path.
    The file will be named with the report date and account number.
    If 'cache' is in kwargs, it will write cache data, otherwise it will write
    PnL data.
    If 'pnl' is in kwargs, it will write PnL data.
    If neither is specified, it will raise an Exception.
    If 'verbose' is True, it will print status messages.
    If 'acct' or 'df_orig' or 'report_date' or 'pth' is None, it will raise an Exception.
    The DataFrame will be renamed and columns will be reordered before writing to Parquet.
    The Parquet file will be written with 'pyarrow' engine and timestamps coerced to microseconds.
    The output files will be named as '<report_date>_<acct>_cache.parquet' or '<report_date>_<acct>_pnl.parquet'.
    The report date will be formatted as 'YYYYMMDD'.
    The account number will be converted to string.
    The DataFrame will be saved without the index.
    The columns will be coerced to timestamps in microseconds.
    If 'verbose' is True, it will print a message indicating that the data is being written to Parquet.
    If 'verbose' is False, it will not print any messages.
    
    """

    df = df_orig.copy()

    if acct is None:
        raise Exception('\t\t\t\t\t ERROR: You need to Specify an Account')
    if df is None:
        raise Exception('\t\t\t\t\t ERROR: You need to Specify a DataFrame')
    if report_date is None:
        raise Exception('\t\t\t\t\t ERROR: You need to Specify a Report Date')
    if pth is None:
        raise Exception('\t\t\t\t\t ERROR: You need to Specify a Path for Saving the output')


    data_src_primary=df_orig['data_src_primary'].unique()[0]

    if 'cache' in kwargs:

        df['report_date']=_datetime(report_date.year,report_date.month,report_date.day,23,59,59)
        df['sec_acc_no']=acct
        # Rename Columns
        df=df.rename(columns={'time': 'time_stamp','symbol': 'instrument_id'})
        df=df[['report_date','time_stamp', 'sec_acc_no', 
               'instrument_id', 'side', 'booking_category', 
               'booking_type', 'price','quantity', 'multiplier','data_src_primary']]
        if verbose:
            print('\n\t\t\t\t Writing Cache Data to Parquet')
        
        filename = os.path.join(pth,'%s_%s_%s_cache.parquet'%(report_date.strftime("%Y%m%d"),str(acct),str(data_src_primary)))
        df.to_parquet(filename,
                      engine='pyarrow',
                      index=False,
                      coerce_timestamps="us")

    elif 'pnl' in kwargs:

        df['sec_acc_no'] = acct
        # Rename Columns
        df = df.rename(columns={'ddate': 'report_date', 'symbol': 'instrument_id'})
        df = df[['report_date', 'sec_acc_no', 'instrument_id', 'price', 'quantity', 'rpnl', 'upnl','data_src_primary']]
        
        if verbose:
            print('\n\t\t\t\t Writing PnL Data to Parquet')

        filename= os.path.join(pth,'%s_%s_%s_pnl.parquet'%(report_date.strftime("%Y%m%d"),str(acct),str(data_src_primary)))
        df.to_parquet(filename,engine='pyarrow',index=False,coerce_timestamps="us")
        

    return filename