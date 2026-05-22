#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import warnings
import pandas as pd
from datetime import timedelta, date, datetime as _datetime
# Import Custom Modules
from tools.snowflake_db import db_connection as db
from risk_pylibrary.risk_models import pnl_support as pnl_sup


warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings('ignore')

def build_book(account, startdate=None, enddate=None, query_eis=False, query_reg_rep=False, **kwargs):


    if startdate is None and enddate is None:
        # Using Day in the future for query construction purposes only
        enddate_timestamp = _datetime(2500, 12, 31, 23, 59, 59)
    else:
        startdate_timestamp = _datetime(startdate.year, startdate.month, startdate.day, 23, 59, 59)
        enddate_timestamp = _datetime(enddate.year, enddate.month, enddate.day, 23, 59, 59)


    if account == 'caracalla':
        acct_query = 9800001301
    elif account == 'caligula':
        acct_query = 9800003301
    elif account == 'tiberius':
        acct_query = 9800001601
    elif account == 'trajan':
        acct_query = 9800003601
    elif account == 'alg':
        acct_query = 9800000201
    elif account == 'fx_mm0':
        acct_query = 9800005001
    elif account == 'fx_mm1':
        acct_query = 9800005401
    elif account == 'fx_mm2': 
        acct_query = 9800005201
    elif account is None:
        raise Exception('ERROR: You need to Specify an Account')
    else:
        acct_query = account

    # Query Definition for Positions and PnL

    if query_eis:
        qry_pos = '''
        with trades as (
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
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ >= '2024-01-01'
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
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
            WHERE
                "prim_id" NOT LIKE '%%C%%'
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ >= '2024-01-01'
            AND 
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= %s
            UNION ALL
            SELECT
                TO_TIMESTAMP_NTZ("value_date") AS trade_ts,
                TO_TIMESTAMP_NTZ("value_date")::date as report_date,
                "instrument_id" as instrument_id,
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
                "value_date" >= '2024-01-01'
            AND 
                "value_date" <= %s
            ORDER BY 1),
        
        trades_pos as (
            SELECT
                %s AS ddate,
                tr.instrument_id as instrument_id,
                SUM(tr.quantity) as quantity
            FROM
                trades as tr
            GROUP BY 1,2),
            
        sec_info AS (
            SELECT 
                "isin" AS INSTRUMENT_ID,
                "instrument_type" AS INSTRUMENT_TYPE,
                "name_short" AS name_short,
                "issuer" AS ISSUER
            FROM 
                BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT),
            
        price_eod AS (
            SELECT
                pr.CALENDAR_DATE AS DDATE, 
                pr.instrument_id AS INSTRUMENT_ID,
                pr.CLOSE_MID_PRICE AS PRICE 
                --IFF(secs_info.instrument_type = 'BOND',DIV0(pr.close_mid_price, 100), pr.close_mid_price)  AS PRICE
            FROM 
                TEAMS_PRD.CORE_MART.MRT_SNAPSHOT__INSTRUMENT_PRICES__EOD_PRICE as pr
            WHERE
                pr.CALENDAR_DATE = %s
            AND
                pr.EXCHANGE = 'LSX'
            ORDER BY 1,2)
        
        SELECT
            TO_DATE(pos.DDATE,'yyyy-MM-dd') AS DDATE,
            'caligula' AS ACCOUNT,
            pos.INSTRUMENT_ID,
            sc.INSTRUMENT_TYPE,
            sc.name_short AS NAME_OFFICIAL,
            sc.ISSUER AS ISSUER,
            IFF(sc.INSTRUMENT_TYPE='BOND',DIV0(pr.PRICE,100),pr.PRICE) AS EOD_PRICE,
            pos.QUANTITY AS POSITION_EOD,
            IFF(sc.INSTRUMENT_TYPE='BOND',DIV0(pr.PRICE,100),pr.PRICE) * pos.QUANTITY AS RISK_EXPOSURE_IN_EUR
        FROM
            trades_pos AS pos
        INNER JOIN 
            sec_info AS sc
            ON sc.INSTRUMENT_ID = pos.INSTRUMENT_ID
        INNER JOIN 
            price_eod AS pr
            ON pr.INSTRUMENT_ID = pos.INSTRUMENT_ID
        '''

        # Constructing the Query
        qry_pos_out = qry_pos % (db.sqldate(enddate), db.sqldate(enddate), db.sqldate(enddate), db.sqldate(enddate), db.sqldate(enddate))

    elif query_reg_rep:

        qry_pos = '''
        with trades_pos as (
        SELECT
            %s AS ddate,
            tr.instrument_id as instrument_id,
            tr.quantity as quantity
        FROM
            TEAMS_PRD.RISK_DATA.MR_PORT_POS_REG_REP as tr),

        sec_info AS (
            SELECT 
                "isin" AS INSTRUMENT_ID,
                "instrument_type" AS INSTRUMENT_TYPE,
                "name_short" AS name_short,
                "issuer" AS ISSUER
            FROM 
                BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT),

        price_eod AS (
            SELECT
                pr.CALENDAR_DATE AS DDATE, 
                pr.instrument_id AS INSTRUMENT_ID,
                pr.CLOSE_MID_PRICE AS PRICE 
                --IFF(secs_info.instrument_type = 'BOND',DIV0(pr.close_mid_price, 100), pr.close_mid_price)  AS PRICE
            FROM 
                TEAMS_PRD.CORE_MART.MRT_SNAPSHOT__INSTRUMENT_PRICES__EOD_PRICE as pr
            WHERE
                pr.CALENDAR_DATE = %s
            AND
                pr.EXCHANGE = 'LSX'
            ORDER BY 1,2)

        SELECT
            pos.DDATE,
            'caligula' AS ACCOUNT,
            pos.INSTRUMENT_ID,
            sc.INSTRUMENT_TYPE,
            sc.name_short AS NAME_OFFICIAL,
            sc.ISSUER AS ISSUER,
            IFF(sc.INSTRUMENT_TYPE='BOND',DIV0(pr.PRICE,100),pr.PRICE) AS EOD_PRICE,
            pos.QUANTITY AS POSITION_EOD,
            IFF(sc.INSTRUMENT_TYPE='BOND',DIV0(pr.PRICE,100),pr.PRICE) * pos.QUANTITY AS RISK_EXPOSURE_IN_EUR
        FROM
            trades_pos AS pos
        INNER JOIN 
            sec_info AS sc
            ON sc.INSTRUMENT_ID = pos.INSTRUMENT_ID
        INNER JOIN 
            price_eod AS pr
            ON pr.INSTRUMENT_ID = pos.INSTRUMENT_ID
        '''

        # Constructing the Query
        qry_pos_out = qry_pos % (db.sqldate(enddate), db.sqldate(enddate))

    else:
        qry_pos = '''
            SELECT
                POS.REPORT_DATE::date AS DDATE,
                POS.SEC_ACC_NO AS ACCOUNT,
                POS.INSTRUMENT_ID,
                POS.INSTRUMENT_TYPE,
                POS.NAME_OFFICIAL,
                POS.ISSUER_NAME AS ISSUER,
                POS.CLOSE_MID_PRICE_CLEAN AS EOD_PRICE,
                POS.QUANTITY AS POSITION_EOD,
                POS.CLOSE_MID_PRICE_CLEAN * POS.QUANTITY AS RISK_EXPOSURE_IN_EUR
            FROM
                TEAMS_PRD.RISK_FUNCTION_PUBLISH.PBL__RISK_FUNCTION_MRM_BOOK_TRADING_VALUATION AS POS
                INNER JOIN 
                    (SELECT 
                        "isin", 
                        "instrument_type" AS INSTRUMENT_TYPE,
                        "name_official" AS NAME_OFFICIAL,
                        "issuer" AS ISSUER
                    FROM 
                        BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT) as SEC_INFO
                ON POS.INSTRUMENT_ID = SEC_INFO."isin"
            WHERE
                POS.REPORT_DATE = %s
            AND
                POS.SEC_ACC_NO = %s
        '''

        qry_pos_out = qry_pos % (db.sqldate(enddate_timestamp),acct_query)
        # Constructing the Query


    # Executing the Query
    df_pos = db.run_query(query=qry_pos_out)

    #Format Out and Columns
    df_risk_exp_tot = df_pos[['ddate', 'risk_exposure_in_eur']].groupby('ddate').sum().reset_index()
    df_risk_exp_tot.columns = ['ddate', 'risk_exposure_in_eur_total']
    df_pos = pd.merge(df_pos.sort_values(by='ddate'), df_risk_exp_tot, on='ddate')

    df_pos['weight'] = df_pos['risk_exposure_in_eur'] / df_pos['risk_exposure_in_eur_total'].abs()

    df_pos = df_pos[['instrument_id', 'ddate', 'name_official', 'instrument_type', 'position_eod',
                     'eod_price', 'risk_exposure_in_eur', 'risk_exposure_in_eur_total', 'weight']]

    # Remove Residuals
    # out = pd.concat([df_pos[df_pos.position_eod > 1e-5],df_pos[df_pos.position_eod < -1e-5]], axis=0)

    # Further Formatting
    out = df_pos.set_index('instrument_id')

    out['account'] = account
    out = out[['ddate', 'account','name_official', 'instrument_type','position_eod',
              'eod_price', 'risk_exposure_in_eur', 'risk_exposure_in_eur_total', 'weight']]

    # Enhance with Data Packages
    if 'enhance_data' in kwargs.keys():

        out = book_enhance_data(out)

    return out



def build_book_trades(account=None, enddate=None, cache_trades=None, verbose=True):

    # Set Parameters
    query_eis = False

    if account == 'caracalla':
        acct_query = 9800001301
    elif account == 'caligula':
        acct_query = 9800003301
        query_eis = True
    elif account == 'tiberius':
        acct_query = 9800001601
    elif account == 'alg':
        acct_query = 9800000201
    else:
        acct_query = account


    if verbose:
        print('\n\t ************ Building Report based on Trades')

    # Set OutPut
    out_dict = dict()

    if cache_trades is None:
        # Getting trades
        print('\n\t\t Querying Trades')
        df_trades = pnl_sup.get_trades_pnl(account=account,
                                           startdate=date(2019, 1, 1),
                                           enddate=enddate,
                                           query_eis=query_eis)
    else:
        df_trades = cache_trades


    if verbose:
        print('\n\t\t Querying Prices')

    # Getting Prices --------------------------------------------------------------------------
    qry_pr = '''
    SELECT
        pr.CALENDAR_DATE AS DDATE, 
        pr.instrument_id AS INSTRUMENT_ID,
        pr.CLOSE_BID_PRICE AS BID_PRICE, 
        pr.CLOSE_MID_PRICE AS MID_PRICE,
        pr.CLOSE_ASK_PRICE AS ASK_PRICE 
    FROM 
        TEAMS_PRD.CORE_MART.MRT_SNAPSHOT__INSTRUMENT_PRICES__EOD_PRICE as pr
    WHERE
        pr.CALENDAR_DATE >= %s AND pr.CALENDAR_DATE <= %s
    AND
        pr.EXCHANGE = 'LSX'
    AND
        pr.instrument_id IN (%s)
    ORDER BY 1,2
    '''

    df_prices = db.run_query(query=qry_pr%(db.sqldate(enddate -timedelta(3)), db.sqldate(enddate), db.joinpad(list(df_trades.symbol.unique()))))


    # Getting Sec Info --------------------------------------------------------------------------
    if verbose:
        print('\n\t\t Querying Secs Info')

    qry_sec_info='''
    SELECT 
        inv."isin" AS INSTRUMENT_ID,
        inv."instrument_type" AS INSTRUMENT_TYPE,
        inv."name_short" AS name_short
    FROM 
        BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT AS inv
    WHERE
        inv."isin" in (%s)
    '''

    df_sec_info = db.run_query(query=qry_sec_info%db.joinpad(list(df_trades.symbol.unique())))

    # Formatting the Output
    # Trades
    df_trades = df_trades.rename(columns={'symbol': 'instrument_id'})
    df_trades['quantity'] = df_trades.apply(lambda row: -1 * row['quantity'] if row['side'] == 'S' else row['quantity'], axis=1)
    df_trades = df_trades[['instrument_id', 'quantity']]

    # Prices
    df_prices = df_prices.fillna(method='ffill') # Front filling Missing Prices
    df_prices = df_prices[df_prices.ddate == enddate]
    df_prices = df_prices[['instrument_id', 'bid_price', 'mid_price', 'ask_price']]
    df_prices = df_prices.set_index('instrument_id')

    # Sec Info
    df_sec_info = df_sec_info.set_index('instrument_id')

    # Building  Enddate Report
    out = df_trades.groupby(['instrument_id']).sum()
    out = pd.concat([out, df_sec_info, df_prices], axis=1)
    out['account'] = acct_query
    out['report_date'] = enddate
    out = out[['account', 'report_date', 'instrument_type', 'name_short', 'bid_price', 'mid_price', 'ask_price', 'quantity']]

    # Calculate Market Value
    # Adjust Bond Prices
    for prx in ['bid_price', 'mid_price', 'ask_price']:
        out[prx] = out[['instrument_type', prx]].apply(lambda row: row[prx]/100 if row['instrument_type'] == 'BOND' else row[prx], axis=1)
    out['mkt_eur_prudent'] = out[['bid_price', 'ask_price', 'quantity']].apply(lambda row:
                                                                               row['bid_price'] * row['quantity']
                                                                               if row['quantity'] > 0
                                                                               else row['ask_price'] * row['quantity'], axis=1)
    out['mkt_eur_prudent_short'] = out[['ask_price', 'quantity']].apply(lambda row:
                                                                               row['ask_price'] * row['quantity']
                                                                               if row['quantity'] < 0
                                                                               else 0, axis=1)
    out['mkt_eur_prudent_long'] = out[['bid_price', 'quantity']].apply(lambda row:
                                                                               row['bid_price'] * row['quantity']
                                                                               if row['quantity'] > 0
                                                                               else 0, axis=1)
    out['mkt_eur'] = out.mid_price * out.quantity
    out['mkt_eur_short'] = out[['mid_price', 'quantity']].apply(lambda row: row['mid_price'] * row['quantity'] if row['quantity'] < 0 else 0, axis=1)
    out['mkt_eur_long'] = out[['mid_price', 'quantity']].apply(lambda row: row['mid_price'] * row['quantity'] if row['quantity'] > 0 else 0, axis=1)

    out_dict['report_snapshot'] = out


    return out_dict


def build_book_trades_grouped(account=None, enddate=None, cache_trades=None, verbose=True):

    # Set Parameters
    query_eis = False

    if account == 'caracalla':
        acct_query = 9800001301
    elif account == 'caligula':
        acct_query = 9800003301
        query_eis = True
    elif account == 'tiberius':
        acct_query = 9800001601
    elif account == 'trajan':
        acct_query = 9800003601
    elif account == 'alg':
        acct_query = 9800000201
    else:
        acct_query = account


    if verbose:
        print('\n\t ************ Building Report based on Trades')

    # Set OutPut
    out_dict = dict()

    if cache_trades is None:
        # Getting trades
        print('\n\t\t Querying Trades')
        df_trades = pnl_sup.get_trades_pnl(account=account,
                                           startdate=date(2019, 1, 1),
                                           enddate=enddate,
                                           query_eis=query_eis)
    else:
        df_trades = cache_trades


    if verbose:
        print('\n\t\t Querying Prices')

    # Getting Prices   --------------------------------------------------------------------------
    qry_pr = '''
    SELECT
        pr.REPORT_DATE AS DDATE, 
        pr.instrument_id AS INSTRUMENT_ID,
        pr.CLOSE_BID_PRICE_CLEAN AS BID_PRICE, 
        pr.CLOSE_MID_PRICE_CLEAN AS MID_PRICE,
        pr.CLOSE_ASK_PRICE_CLEAN AS ASK_PRICE 
    FROM 
        TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_msl_prices as pr
    WHERE
        pr.REPORT_DATE >= %s AND pr.REPORT_DATE <= %s
    AND
        pr.instrument_id IN (%s)
    ORDER BY 1,2
    '''

    df_prices = db.run_query(query=qry_pr%(db.sqldate(enddate -timedelta(3)), db.sqldate(enddate), db.joinpad(list(df_trades.symbol.unique()))))


    # Getting Sec Info --------------------------------------------------------------------------
    if verbose:
        print('\n\t\t Querying Secs Info')

    qry_sec_info='''
    SELECT 
        inv."isin" AS INSTRUMENT_ID,
        inv."instrument_type" AS INSTRUMENT_TYPE,
        inv."name_short" AS NAME_SHORT
    FROM 
        BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT AS inv
    WHERE
        inv."isin" in (%s)
    '''

    df_sec_info = db.run_query(query=qry_sec_info%db.joinpad(list(df_trades.symbol.unique())))

    # Formatting the Output
    # Trades
    df_trades = df_trades.rename(columns={'symbol': 'instrument_id'})
    df_trades = df_trades[['instrument_id', 'quantity']]

    # Prices
    df_prices = df_prices.fillna(method='ffill') # Front filling Missing Prices
    df_prices = df_prices[df_prices.ddate == enddate]
    df_prices = df_prices[['instrument_id', 'bid_price', 'mid_price', 'ask_price']]
    df_prices = df_prices.set_index('instrument_id')

    # Sec Info
    df_sec_info = df_sec_info.set_index('instrument_id')

    # Building  Enddate Report
    out = df_trades.groupby(['instrument_id']).sum()
    out = pd.concat([out, df_sec_info, df_prices], axis=1)
    out['account'] = acct_query
    out['report_date'] = enddate
    out = out[['account', 'report_date', 'instrument_type', 'name_short', 'bid_price', 'mid_price', 'ask_price', 'quantity']]

    # Calculate Market Value
    # Adjust Bond Prices
    for prx in ['bid_price', 'mid_price', 'ask_price']:
        out[prx] = out[['instrument_type', prx]].apply(lambda row: row[prx]/100 if row['instrument_type'] == 'BOND' else row[prx], axis=1)
    out['mkt_eur_prudent'] = out[['bid_price', 'ask_price', 'quantity']].apply(lambda row:
                                                                               row['bid_price'] * row['quantity']
                                                                               if row['quantity'] > 0
                                                                               else row['ask_price'] * row['quantity'], axis=1)
    out['mkt_eur_prudent_short'] = out[['ask_price', 'quantity']].apply(lambda row:
                                                                               row['ask_price'] * row['quantity']
                                                                               if row['quantity'] < 0
                                                                               else 0, axis=1)
    out['mkt_eur_prudent_long'] = out[['bid_price', 'quantity']].apply(lambda row:
                                                                               row['bid_price'] * row['quantity']
                                                                               if row['quantity'] > 0
                                                                               else 0, axis=1)
    out['mkt_eur'] = out.mid_price * out.quantity
    out['mkt_eur_short'] = out[['mid_price', 'quantity']].apply(lambda row: row['mid_price'] * row['quantity'] if row['quantity'] < 0 else 0, axis=1)
    out['mkt_eur_long'] = out[['mid_price', 'quantity']].apply(lambda row: row['mid_price'] * row['quantity'] if row['quantity'] > 0 else 0, axis=1)

    out_dict['report_snapshot'] = out


    return out_dict


def build_ptf_src(account, enddate):


    if account == 'caracalla':
        acct_query = 9800001301
    elif account == 'caligula':
        acct_query = 9800003301
    elif account == 'tiberius':
        acct_query = 9800001601
    elif account == 'alg':
        acct_query = 9800000201
    else:
        acct_query = account

    qry = '''
    WITH daily_trades AS (
        SELECT
             executed_at::date as ddate, 
             trade_type, 
             instrument_id,
             CASE 
                WHEN trade_type = 'BUY' then execution_size
                ELSE -1 * execution_size 
             END as quantity
        FROM
            TEAMS_PRD.SOURCE_PORTFOLIO.SRC__PORTFOLIO__TRADE as ptf_trade
        WHERE
            1=1
        AND
            ptf_trade.sec_acc_no = %s
        AND
            executed_at::date <= %s
        
        UNION  ALL 
        
        SELECT 
            "executed_at"::date as ddate, 
            "trade_direction" as trade_type, 
            "instrument_id" as instrument_id,
            CASE 
                WHEN "trade_direction" = 'BUY' then  "execution_size"
                ELSE -1 *  "execution_size"
             END as quantity
        FROM 
            BACKEND_PRD.POST_TRADING_TIBERIUS.PUBLIC_TRADE
        WHERE 
            1=1 
        AND 
            "sec_acc_no" = %s
        AND
            "executed_at"::date <= %s
            
        QUALIFY ROW_NUMBER() OVER(PARTITION BY "id" ORDER BY "updated_at" ASC) = 1),
        
        positions AS (
        SELECT
            instrument_id,
            SUM(quantity) as quantity
        FROM
            daily_trades
        GROUP BY 1),
        
        
        sec_info AS (
        SELECT 
            instrument_id, 
            symbol, 
            intl_symbol,
            instrument_type, 
            name_official as asset_name
        FROM 
            TEAMS_PRD.CORE_MART.MRT_CURR__INSTRUMENTS
        WHERE
            instrument_id in (SELECT instrument_id FROM positions)
        ),
        
        price_eod AS (
        SELECT
            pr.CALENDAR_DATE AS DDATE, 
            pr.instrument_id AS INSTRUMENT_ID,
            pr.CLOSE_MID_PRICE AS PRICE 
            --IFF(secs_info.instrument_type = 'BOND',DIV0(pr.close_mid_price, 100), pr.close_mid_price)  AS PRICE
        FROM 
            TEAMS_PRD.CORE_MART.MRT_SNAPSHOT__INSTRUMENT_PRICES__EOD_PRICE as pr
        WHERE
            pr.CALENDAR_DATE = %s
        AND
            pr.EXCHANGE = 'LSX'
        ORDER BY 1,2
        )
        
        SELECT 
            %s AS REPORT_DATE, 
            '%s' AS ACCT,
            %s AS ACCT_NUM,
            pos.INSTRUMENT_ID,
            sc.INSTRUMENT_TYPE,
            sc.asset_name,
            pos.quantity as quantity,
            IFF(sc.INSTRUMENT_TYPE = 'BOND',DIV0(pr.PRICE, 100), pr.PRICE)  AS PRICE_EUR,
            (quantity * IFF(sc.INSTRUMENT_TYPE = 'BOND',DIV0(pr.PRICE, 100), pr.PRICE)) AS MARKET_VALUE_EUR
        FROM 
            positions AS pos
        INNER JOIN 
            sec_info AS sc
            ON sc.instrument_id = pos.instrument_id
        INNER JOIN 
            price_eod AS pr
            ON pr.instrument_id = pos.instrument_id
        ORDEr BY REPORT_DATE DESC;
    '''

    sql_edate = db.sqldate(enddate)
    qry_adj = qry % (acct_query, sql_edate, acct_query, sql_edate, sql_edate, sql_edate, account, acct_query)

    df = db.run_query(query=qry_adj)

    # Format
    df = df.set_index('instrument_id')

    return df


def recon_eis_inventory(enddate):

    df_trades = pnl_sup.get_trades_caligula_eis()

def book_enhance_data(df_orig):


    from risk_pylibrary.projects.risk_factor_mapping import rf_wrapper as rw

    df = df_orig.copy()

    df_map = rw.rf_mapping_engine(df.ddate.unique()[0], df.ddate.unique()[0])
    df_map = df_map.set_index('instrument_id')
    df_port = df.set_index('instrument_id').join(df_map[[k for k in df_map.columns if k not in df.columns]])

    return df_port



def build_rt_positions(account, syms, run_pnl=False):

    if account == 'caracalla':
        acct_query = 9800001301
    elif account == 'caligula':
        acct_query = 9800003301
    elif account == 'tiberius':
        acct_query = 9800001601

    qry = '''
    with last_trades as (
            SELECT
                date_trunc('SECOND',convert_timezone('Europe/Berlin', timestamp)::TIMESTAMP_NTZ) AS timestamp_cest,
                CAST(data['output']['instrumentId'] as string) as instrument_id,
                -- CAST(data['output']['secAccNo'] as string) as acc_num,
                CAST(data['output']['exchangeId'] as string) as exchange_id,
                CAST(data['output']['executionSize'] as float) as quantity,
                CAST(CAST(data['output']['executionPrice'] AS string) AS float) as execution_price,
                
                -- Customer Sell LSX
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['exchangeId'] = 'LSX', CAST(CAST(data['output']['executionSize'] AS string) AS float),0) AS customer_trading_sell_quantity_lsx,
    
                -- Customer Buy LSX
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['exchangeId'] = 'LSX', CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS customer_trading_buy_quantity_lsx,
                
                -- Customer Sell nostro 
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['exchangeId'] = 'TRPT', CAST(CAST(data['output']['executionSize'] AS string) AS float),0) AS customer_trading_sell_quantity_nostro,
                
                -- Customer Buy nostro
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['exchangeId'] = 'TRPT', CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS customer_trading_buy_quantity_nostro,
                    
                -- Customer Sell Tradegate
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['exchangeId'] = 'TDG', CAST(CAST(data['output']['executionSize'] AS string) AS float),0) AS customer_trading_sell_quantity_tdg,
                
                -- Customer Buy Tradegate
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['exchangeId'] = 'TDG', CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS customer_trading_buy_quantity_tdg,
                    
                -- Customer Sell Tiberius
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['exchangeId'] = 'TIB', CAST(CAST(data['output']['executionSize'] AS string) AS float),0) AS customer_trading_sell_quantity_tib,
                
                -- Customer Buy Tiberius
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['exchangeId'] = 'TIB', CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS customer_trading_buy_quantity_tib,
                
                -- EIS Sell
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['secAccNo'] = '9800001301', CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS eis_trading_sell_quantity,
                    
                -- EIS Buy
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['secAccNo'] = '9800001301', CAST(CAST(data['output']['executionSize'] AS string) AS float),0) AS eis_trading_buy_quantity,
                    
                -- Customer Sell Volume  LSX  
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['exchangeId'] = 'LSX', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                    AS float)*CAST(CAST(data['output']['executionSize'] as string) as float),0) as customer_trading_sell_volume_lsx,
                                                                    
                -- Customer Buy Volume  LSX                                                  
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['exchangeId'] = 'LSX', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                    AS float)*CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS customer_trading_buy_volume_lsx,
                                                                    
                -- Customer Sell Volume  Nostro  
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['exchangeId'] = 'TRPT', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                    AS float)*CAST(CAST(data['output']['executionSize'] as string) as float),0) as customer_trading_sell_volume_nostro,
                                                                    
                -- Customer Buy Volume  Nostro                                                  
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['exchangeId'] = 'TRPT', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                    AS float)*CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS customer_trading_buy_volume_nostro,
                                                                    
               
                -- Customer Sell Volume Tradegate
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['exchangeId'] = 'TDG', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                    AS float)*CAST(CAST(data['output']['executionSize'] as string) as float),0) as customer_trading_sell_volume_tdg,
                                                                    
                -- Customer Buy Volume Tradegate                                                   
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['exchangeId'] = 'TDG', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                    AS float)*CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS customer_trading_buy_volume_tdg,
                                                                    
                -- Customer Sell Volume Tiberius
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['exchangeId'] = 'TIB', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                    AS float)*CAST(CAST(data['output']['executionSize'] as string) as float),0) as customer_trading_sell_volume_tib,
                                                                    
                -- Customer Buy Volume Tiberius                                                   
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['exchangeId'] = 'TIB', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                    AS float)*CAST(CAST(data['output']['executionSize'] AS string) AS float)*(-1),0) AS customer_trading_buy_volume_tib,
                                                                    
                -- EIS Sell Volume                                                     
                iff(data['output']['orderType'] = 'SELL' 
                    AND data['output']['secAccNo'] = '9800001301', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                        AS float)*CAST(CAST(data['output']['executionSize'] AS string) 
                                                                                       AS float)*(-1),0) AS eis_depo_trading_sell_volume,
                -- EIS Buy Volume
                iff(data['output']['orderType'] = 'BUY' 
                    AND data['output']['secAccNo'] = '9800001301', CAST(CAST(data['output']['executionPrice'] AS string) 
                                                                        AS float)*CAST(CAST(data['output']['executionSize'] AS string) 
                                                                                       AS float),0) AS eis_depo_trading_buy_volume
            FROM 
                events_prd.portfolio_manager.PORTFOLIO_MANAGER_TRACKING_EVENTS_VIEW a
            WHERE 1=1
                AND timestamp::date > current_date - 2
                AND execution_price IS NOT NULL
                AND (data['output']['secAccNo'] = '%s' OR data['output']['exchangeId'] = 'TRPT' OR data['output']['exchangeId'] = 'TDG' OR data['output']['exchangeId'] = 'TIB')
                AND CAST(CAST(data['output']['executionSize'] AS string) AS float) <> 0 
                --AND CAST(data['output']['instrumentId'] AS string) in ('US36467W1099')
            order by 1 ASC)
            
        SELECT
            timestamp_cest,
            instrument_id,
            --acc_num,
            exchange_id,
            execution_price,
            quantity,
            iff(exchange_id='LSX', COUNT(1), 0) AS sum_trades_lsx,
            iff(exchange_id='TDG', COUNT(1), 0) AS sum_trades_tdg,
            iff(exchange_id='TIB', COUNT(1), 0) AS sum_trades_tiberius,
            iff(exchange_id='TRPT', COUNT(1), 0) AS sum_trades_nostro,
            SUM(customer_trading_sell_quantity_lsx) AS customer_trading_sell_quantity_lsx,
            SUM(customer_trading_buy_quantity_lsx) AS customer_trading_buy_quantity_lsx,
            SUM(customer_trading_sell_quantity_nostro) AS customer_trading_sell_quantity_nostro,
            SUM(customer_trading_buy_quantity_nostro) AS customer_trading_buy_quantity_nostro,
            SUM(customer_trading_sell_quantity_tdg) AS customer_trading_sell_quantity_tdg,
            SUM(customer_trading_buy_quantity_tdg) AS customer_trading_buy_quantity_tdg,
            SUM(customer_trading_sell_quantity_tib) AS customer_trading_sell_quantity_tib,
            SUM(customer_trading_buy_quantity_tib) AS customer_trading_buy_quantity_tib,
            SUM(eis_trading_sell_quantity) AS nostro_trading_sell_quantity,
            SUM(eis_trading_buy_quantity) AS nostro_trading_buy_quantity,
            SUM(customer_trading_sell_volume_lsx) AS customer_trading_sell_volume_lsx,
            SUM(customer_trading_buy_volume_lsx) AS customer_trading_buy_volume_lsx,
            SUM(customer_trading_sell_volume_nostro) AS customer_trading_sell_volume_nostro,
            SUM(customer_trading_buy_volume_nostro) AS customer_trading_buy_volume_nostro,
            SUM(customer_trading_sell_volume_tdg) AS customer_trading_sell_volume_tdg,
            SUM(customer_trading_buy_volume_tdg) AS customer_trading_buy_volume_tdg,
            SUM(customer_trading_sell_volume_tib) AS customer_trading_sell_volume_tib,
            SUM(customer_trading_buy_volume_tib) AS customer_trading_buy_volume_tib,
            SUM(eis_depo_trading_sell_volume) AS nostro_depo_trading_sell_volume,
            SUM(eis_depo_trading_buy_volume) AS nostro_depo_trading_buy_volume
        FROM 
            last_trades

        group by 
            timestamp_cest,
            instrument_id,
            --acc_num,
            exchange_id,
            execution_price,
            quantity
        order by timestamp_cest ASC
    '''

    # Create Output
    out_trades = dict()

    df = db.run_query(query=qry%acct_query)
    out_trades['orig'] = df


    # Run Analytics:
    df_total = df.set_index('timestamp_cest').iloc[:, 5:]
    df_total = df_total.rename(columns=lambda x: 'total_' + x)
    out_trades['total'] = df_total

    # Filter Original dataframe for symbols:
    df_syms = df[df.instrument_id.isin(syms)]
    out_trades['syms'] = df_syms

    # out_trades_kpi = dict()
    # for col in ['sum_trades', 'customer_trading_buy_quantity', 'customer_trading_sell_quantity', 'customer_trading_buy_volume', 'customer_trading_sell_volume']:
    #     tmp = df_total[[k for k in df_total.columns if col in k]]
    #     tmp = tmp.join(df_syms[['timestamp_cest']+[k for k in df_syms.columns if col in k]].groupby('timestamp_cest').sum().cumsum())
    #     tmp = tmp.fillna(method='ffill')
    #     out_trades_kpi[col] = tmp


    # Treat Nostro Positions:
    out_dict_syms = dict()
    out_syms_tmp = df_syms[['timestamp_cest','instrument_id',
                   'customer_trading_sell_quantity_nostro',
                   'customer_trading_buy_quantity_nostro',
                   'nostro_trading_buy_quantity',
                   'nostro_trading_sell_quantity']].groupby(['timestamp_cest','instrument_id']).sum()

    out_syms_tmp['nostro_trading_net_quantity'] = out_syms_tmp.sum(axis=1)

    out_syms = pd.DataFrame()
    for instr in out_syms_tmp.index.get_level_values(1).unique():
        tmp = out_syms_tmp[out_syms_tmp.index.get_level_values(1) == instr]
        #tmp['nostro_trading_net_quantity'] = tmp.sum(axis=1)
        tmp = tmp[['nostro_trading_net_quantity']]
        tmp.columns = [instr]
        tmp = tmp.reset_index().drop('instrument_id', axis=1).set_index('timestamp_cest')
        out_syms = pd.concat([out_syms, tmp], axis=1)

    out_dict_syms['out_syms'] = out_syms

    if run_pnl is True:
        print('hello')



    return out_trades, out_dict_syms



def book_recon(account, startdate, enddate, test_sb, verbose):
    """
    Reconciliation function for trading books
    @param account: e.g. 'caligula'
    @param enddate: date object
    @return:
    """

    # Set output
    out_dict = dict()

    if verbose:
        print("************** Building Recon Report")
    # Get Trades
    if account == 'caligula':
        if verbose:
            print("\n\t Querying EIS Trades")
        df_eis = pnl_sup.get_trades_pnl(account=account, startdate=startdate, enddate=enddate, query_eis=True)
        df_eis['quantity_eis'] = df_eis[['side','quantity']].apply(lambda row: -1 * row['quantity'] if row['side'] == 'S' else row['quantity'],axis=1)

    if verbose:
        print("\n\t Querying ShareBooking Trades")

    if test_sb:
        df_sb = pnl_sup.get_trades_pnl_test(account=account,startdate=startdate,enddate=enddate,query_eis=False)
    else:
        df_sb = pnl_sup.get_trades_pnl(account=account, startdate=startdate, enddate=enddate, query_eis=False)
    df_sb['quantity_sb'] = df_sb[['side','quantity']].apply(lambda row: -1 * row['quantity'] if row['side'] == 'S' else row['quantity'],axis=1)
    df_sb['report_date'] = df_sb['time'].apply(lambda x: x.date())
    df_sb_hist = pd.pivot_table(df_sb[['report_date','symbol','quantity_sb']],
                                index='symbol',
                                columns='report_date',
                                values='quantity_sb',
                                aggfunc='sum')

    df_sb_hist = df_sb_hist.fillna(0)
    df_sb_hist = df_sb_hist.cumsum(axis=1)

    if verbose:
        print("\n\t Querying Risk Data Positions")
    df_ri_orig = db.run_query(query=" SELECT * FROM TEAMS_PRD.RISK_DATA.MR_PORT_POS WHERE ACCOUNT='%s' ORDEr BY 1"%account)
    df_ri_hist = pd.pivot_table(df_ri_orig, index='instrument_id', columns='report_date', values='quantity',aggfunc='sum')
    df_ri_hist = df_ri_hist.fillna(0)
    df_ri_hist = df_ri_hist.rename(columns=lambda x: x.date())

    # Slicing Snapshot
    df_ri = df_ri_hist.iloc[:, [-1]]
    df_ri.columns = ['quantity_sb_old']
    df_ri = df_ri[df_ri.quantity_sb_old!=0]

    if verbose:
        print("\n\t Building Report Risk Data Positions")

    # Concatenating for Snapshot Report
    if account == 'caligula':
        out = pd.concat([df_eis[['symbol', 'quantity_eis']].groupby('symbol').sum(),
                         df_sb[['symbol', 'quantity_sb']].groupby('symbol').sum(),
                         df_ri.rename(columns={'position_eod':'quantity_sb_old'})], axis=1)

        # Create Output
        out = out.fillna(0)
        out['delta_eis_sb'] = out.quantity_eis - out.quantity_sb
        out['delta_eis_sb_old'] = out.quantity_eis - out.quantity_sb_old

    else:
        out = pd.concat([df_sb[['symbol', 'quantity_sb']].groupby('symbol').sum(),
                         df_ri.rename(columns={'position_eod':'quantity_sb_old'})], axis=1)

        # Create Output
        out = out.fillna(0)
        out['delta_sb_old'] = out.quantity_sb - out.quantity_sb_old

    out_dict['pos'] = out


    # Building Historical Report
    df_delta_hist = df_sb_hist - df_ri_hist
    df_filter = df_delta_hist.iloc[:,[-1]]
    df_filter = df_filter[df_filter.values!=0]
    df_delta_hist = df_delta_hist.loc[df_filter.index]
    out_dict['delta_hist'] = df_delta_hist

    return out_dict


def get_book_kpi(accts, enddate, verbose):

    out = pd.DataFrame(index=accts, columns=['first_trade', 'last_trade', 'num_trades',
                                             'booking_cats', 'mkt_gross_last', 'mkt_net_last', 'num_pos', 'num_shorts', 'instrument_types'])

    for acct in accts:
        try:
            if verbose:
                print('Querying %s'%acct)

            cnt=db.run_query(query='SELECT COUNT(*) FROM BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING WHERE "sec_acc_no"=%s'%acct)
            if cnt.iloc[0][0] > 3e07:
                if verbose:
                    print("\n WARNING: %s has more than 3e07 trades"%acct)

            else:
                # Trades KPIs
                tmp_trades = pnl_sup.get_trades_pnl(account=acct, startdate=date(2022, 9, 1), enddate=enddate)
                out.loc[acct, 'first_trade'] = tmp_trades.booking_date.min()
                out.loc[acct, 'last_trade'] = tmp_trades.booking_date.max()
                out.loc[acct, 'num_trades'] = len(tmp_trades)
                out.loc[acct, 'booking_cats'] = ('|').join(list(tmp_trades.booking_category.unique()))

                # Share Bookings
                tmp = build_book_trades(acct, enddate)
                tmp['market_value_gross_eur'] = tmp.market_value_eur.abs()

                out.loc[acct, 'mkt_gross_last'] = tmp.market_value_gross_eur.sum()
                out.loc[acct, 'mkt_net_last'] = tmp.market_value_eur.sum()
                out.loc[acct, 'num_pos'] = len(tmp)
                out.loc[acct, 'num_shorts'] = len(tmp[tmp.quantity_sb <= 0])
                out.loc[acct, 'instrument_types'] = ('|').join(list(tmp.instrument_type.unique()))

        except:
            pass
            print("\t ERROR: Could not build share_bookings for %s"%acct)


    return out















