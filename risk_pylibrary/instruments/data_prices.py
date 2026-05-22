#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys

# Import Python Modules
import numpy as np
from datetime import datetime as _datetime, date, timedelta
import time
import traceback

# Custom Modules Added
from tools import pandas_patched as pd
from tools.snowflake_db import db_connection as db
from instruments import data_macro as dtm


def _get_stockperks_prices(filename=None):
    """
    FB 20220429: Obsolete
    First price for stock perks.
    """


    # Read the Data
    df = pd.read_csv(filename)
    # Format Output
    # Column Names
    df = df.rename(columns=lambda x: x.lower())
    # Date Object and Index
    df['ddate'] = df['date'].apply(lambda x: _datetime.strptime(x, '%Y-%m-%d'))
    df = df.drop('date', axis=1)
    df = df[['ddate', 'instrument_id', 'name_short', 'instrument_type', 'price']]
    df = df.set_index('ddate')

    # Create Output
    out = dict()
    # Price DataFrame
    out['prices'] = df.reset_index().pivot_table(values='price', index='ddate', columns='instrument_id')
    # Asset Information (isin, name, asset_class):
    asset_info = df.reset_index()[['instrument_id', 'name_short', 'instrument_type']].drop_duplicates(subset=['instrument_id'])
    out['asset_info'] = asset_info.reset_index().drop('index', axis=1)

    return out



def get_yahoo_prices(symbols=['LTC-USD'], field='Close', startdate=date(2020, 1, 1), enddate=None, freq='1d', is_isin=False, verbose=True):
    """
    Quick code to retrieve cypto price data from yahoo via pandas data_reader

    Feature can be found here: https://ranaroussi.github.io/yfinance/index.html

    Available fields are:
        'Adj Close'
        'Close'
        'High'
        'Low'
        'Open'
        'Volume'

    @param symbols: list,
                    e.g. ['BTC-EUR']
                    for currencies check availability on https://finance.yahoo.com/currencies
                    e.g.  ['EURGBP=X']
    @param field: ohlc, volume or adj_close
    @param startdate: date object
    @param enddate: date object
    """

    import yfinance as yf
    from instruments import data_info as dti
    from curl_cffi import requests

    session = requests.Session(impersonate="chrome")

    # Set Enddate as of Today:
    if enddate is None: enddate = _datetime.now().date()

    if is_isin:

        if verbose: print('Converting ISINs to Yahoo Symbols')

        symbols_old = symbols
        symbols_new = []
        for sym_ISIN in symbols:
            symbols_new.append(dti.yf_enrich_data_scrap(sym_ISIN).symbol.iloc[0])

        symbols = symbols_new


    if verbose: print('Retrieving price data for: %s'%symbols)

    try:
        tmp = yf.download(symbols, start=startdate.strftime('%Y-%m-%d'), end=enddate.strftime('%Y-%m-%d'), interval=freq, session=session)
        tmp = tmp.iloc[:,tmp.columns.get_level_values(0)==field]
        # Drop multiIndex column values
        tmp.columns=tmp.columns.droplevel(0)
        # Drop name of column index
        tmp.columns.name = None
    except:
        tmp = []
        if verbose:
            print('Error: Could not retrieve data for %s'%symbols)

    # Set output
    out = tmp.copy()

    if is_isin:
        out = out.rename(columns=dict(zip(symbols, symbols_old)))

    return out




def get_future_returns():
    """
    Reads major market index returns. Used solely for backtesting
    """
    rets = pd.read_pickle('/Users/fabioballoni/Work/Risk/Projects/FractionalTrading/VaR/Securities/rets_securities.pkl')

    return rets


def get_db_prices(symbols=None, startdate=None, enddate=None):
    """
    Fetching data from snowflake EOD table
    """

    # Import modules:
    from tools.snowflake_db import db_connection as db

    sql_qry = "SELECT " \
              "price_dt, instrument_id, close_mid_price as price from TEAMS_PRD.TRANSFORM_AUM.TRF__AUM__EOD_PRICE_FEED " \
              "WHERE instrument_id in (%s) " \
              "AND exchange='LSX'" \
              "AND price_dt > %s " \
              "AND price_dt < %s "%(db.joinpad(symbols), db.sqldate(startdate), db.sqldate(enddate))

    # Fetch Data
    prx = db.run_query(sql_qry)

    # Adjust Output
    prx = prx.pivot_table(index = ['price_dt'], columns = ['instrument_id'], values = 'price', fill_value = np.nan)
    prx = prx.rename_axis(None, axis = 1)


    return prx


def get_rf_returns(rf_port=pd.DataFrame(), rf_list=[], yield2tr=True):
    """
    Downloads Prices and Returns
    """

    # Get Risk Factor Returns
    if rf_port.empty is False:
        rf_list_yields = list(rf_port[rf_port.index.get_level_values(0).str.startswith('YIELD_')].index.get_level_values(0).unique())
        # Add Underlying Government Yields for Credit
        rf_list_oas_rf = list(rf_port[rf_port.index.get_level_values(1).str.startswith('OAS_')].index)
        credit_yields = [k[0].replace('CREDIT', 'YIELD') for k in rf_list_oas_rf]
        credit_yields = [j.replace('HY_', '') for j in credit_yields]
        credit_yields = [l.replace('IG_', '') for l in credit_yields]

        rf_list_yields = list(set(rf_list_yields + credit_yields))
        rf_list_oas = list(rf_port[rf_port.index.get_level_values(1).str.startswith('OAS_')].index.get_level_values(1).unique())
        rf_list_rets = list(rf_port[~rf_port.index.get_level_values(0).str.startswith('YIELD_')].index.get_level_values(0))
        rf_list_eco = list(rf_port[rf_port.index.get_level_values(0).str.startswith('RATE')].index.get_level_values(0))

    elif len(rf_list) > 0 and rf_port.empty:
        rf_list_yields = [k for k in rf_list if k.startswith('YIELD_')]
        rf_list_oas = [k for k in rf_list if k.startswith('OAS_')]
        rf_list_rets = [k for k in rf_list if not k.startswith('YIELD_')]
        rf_list_eco = [k for k in rf_list if k.startswith('RATE')]

    rets = pd.DataFrame()
    # Get Yields
    if len(rf_list_yields) > 0:
        df_yields_db = db.run_query('SELECT * '
                                    'FROM TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY '
                                    'WHERE code IN (%s)' % db.joinpad(rf_list_yields), fmt_engine='RISK')
        df_yields = df_yields_db.pivot_table(values='value', index='ddate', columns='code', dropna=False)
        df_yields = df_yields.ffill()

        # Drop Weekend Days
        df_yields['is_we'] = df_yields.index
        df_yields['is_we'] = df_yields['is_we'].apply(lambda x: x.weekday())
        df_yields = df_yields[~df_yields['is_we'].isin([5, 6])]
        df_yields = df_yields.drop('is_we', axis=1)

        if len(rf_list_oas) > 0:
            df_oas = db.run_query('SELECT * '
                                  'FROM TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY '
                                  'WHERE code IN (%s)' % db.joinpad(rf_list_oas), fmt_engine='RISK')
            df_oas = df_oas.pivot_table(values='value', index='ddate', columns='code', dropna=False)
            df_oas = df_oas.ffill()
            df_oas = df_oas/100

            # Drop Weekend Days
            df_oas['is_we'] = df_oas.index
            df_oas['is_we'] = df_oas['is_we'].apply(lambda x: x.weekday())
            df_oas = df_oas[~df_oas['is_we'].isin([5, 6])]
            df_oas = df_oas.drop('is_we', axis=1)


        # Run for Government Bonds
        rf_port_govies = rf_port[rf_port.index.get_level_values(0).str.startswith('YIELD_')]
        df_returns_govies = pd.DataFrame(index=df_yields.index,
                                         columns=[k for k in df_yields.columns
                                                  if k in rf_port_govies.index.get_level_values(0)])

        for col in df_returns_govies.columns:
            if yield2tr:
                df_returns_govies[col] = (-rf_port_govies.loc[(col, '')].duration_mod * df_yields[col].diff() + 0.5 *
                                          rf_port_govies.loc[(col, '')].convexity * df_yields[col].diff()**2)
            else:
                df_returns_govies[col] = df_yields[col]

        df_returns_bonds = df_returns_govies.rename_axis(None, axis=1)

        # Run for Corporate Bonds
        if len(rf_list_oas) > 0:
            rf_port_credit = rf_port[rf_port.index.get_level_values(0).str.startswith('HY_CREDIT_')
                                     | rf_port.index.get_level_values(0).str.startswith('IG_CREDIT_')]
            rf_port_credit = rf_port_credit.reset_index()
            rf_port_credit = rf_port_credit.drop_duplicates(subset='risk_factor')
            rf_port_credit['yield_series'] = rf_port_credit['risk_factor'].apply(lambda x:
                                                                                 x.replace('IG_CREDIT', 'YIELD')
                                                                                 if x.startswith('IG_CREDIT')
                                                                                 else x)
            rf_port_credit['yield_series'] = rf_port_credit['yield_series'].apply(lambda x:
                                                                                 x.replace('HY_CREDIT', 'YIELD')
                                                                                 if x.startswith('HY_CREDIT')
                                                                                 else x)
            df_returns_credit = pd.DataFrame(index=df_yields.index, columns=rf_port_credit.risk_factor)
            for col in rf_port_credit.risk_factor:
                try:
                    tmp_credit = rf_port_credit[rf_port_credit.risk_factor == col]
                    df_oas_tmp = df_oas[tmp_credit.oas_series.iloc[0]].reindex(df_yields[tmp_credit.yield_series.iloc[0]].index).fillna(0)
                    if yield2tr:
                        df_returns_credit[col] = (-tmp_credit.duration_mod.iloc[0] *
                                                  (df_yields[tmp_credit.yield_series.iloc[0]].diff() +
                                                   df_oas_tmp.diff()) +
                                                  0.5 * tmp_credit.convexity.iloc[0] *
                                                  (df_yields[tmp_credit.yield_series.iloc[0]].diff() +
                                                   df_oas_tmp.diff())**2)
                    else:
                        df_returns_credit[col] = df_yields[tmp_credit.yield_series.iloc[0]] + df_oas_tmp
                except:
                    print('\t\t ERROR: could not calculate returns for: %s'%col)
                    pass

            # Append Results
            df_returns_bonds = pd.concat([df_returns_bonds, df_returns_credit], axis=1)


        # Concat Results:
        rets = pd.concat([rets, df_returns_bonds], axis=1).sort_index()


    # Get Total Returns
    if len(rf_list_rets) > 0:
        df_rets_db = db.run_query('SELECT report_date as ddate, code, return_pct as value '
                                  'FROM TEAMS_PRD.RISK_FUNCTION_SOURCE.src_curr__risk_function__mrm_trading_book_rf_returns '
                                  'WHERE code IN (%s)'%db.joinpad(rf_list_rets), fmt_engine='RISK')
        df_tr_rets = df_rets_db.pivot_table(values='value', index='ddate', columns='code', dropna=False)

        # Concat Results:
        rets = pd.concat([rets, df_tr_rets], axis=1).sort_index()

    # Get Economic Rates
    if len(rf_list_eco) > 0:
        df_eco_db = db.run_query('SELECT * '
                                 'FROM TEAMS_PRD.RISK_DATA.ECONOMIC_DATA '
                                 'WHERE code IN (%s)'%db.joinpad(rf_list_eco), fmt_engine='RISK')
        df_eco_rets = df_eco_db.pivot_table(values='value', index='ddate', columns='code', dropna=False)

        # Concat Results:
        rets = pd.concat([rets, df_eco_rets], axis=1).sort_index()


    return rets


def update_rf_returns(rf_list=None, fill_days=15, sdate=None, edate=None, to_db=False, verbose=True):
    """
    
    Updates Yahoo Finance Risk Factor Returns
    
    :param rf_list: list, can be used to 
    :param fill_days: Description
    :param sdate: Description
    :param edate: Description
    :param to_db: Description
    :param verbose: Description
    """

    import getpass as _getpass

    # Get Risk Factor Tickers:
    if verbose: 
        print("\n\t\t\t ************* Fetching Risk Factors Mapping from DWH *************\n")
    
    rf_map = db.run_query('SELECT * from TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__GSHEET_MRM_RFM_EQUITY')
    
    if rf_list is not None: 
        rf_map = rf_map[rf_map.code.isin(rf_list)]

    # Get Prices:
    if sdate is None:
        sdate = (_datetime.today() - timedelta(fill_days)).date()

    if edate is None:
        edate = _datetime.today().date()

    if verbose:
        print("\n\t\t\t ************* Fetching Prices from Yahoo Finance *************\n")

    prx = get_yahoo_prices(symbols=list(rf_map[rf_map.symbol_yahoo.notna()&(rf_map.symbol_yahoo!='')].symbol_yahoo),
                           startdate=sdate, 
                           enddate=edate)


    # Format Data:
    rets = prx.pct_change().dropna(axis=0, how='all')
    rets = rets.loc[(rets != 0).any(axis=1)]
    rets = rets.rename(columns=dict(zip(rf_map.symbol_yahoo, rf_map.code)))
    rets.index.name = 'ddate'

    # Format for DB Parse:
    rets_db = rets.rets2db().dropna()
    rets_db = rets_db[rets_db['value'] != 0]


    if to_db is False:

        return rets_db
    
    else:
        # Parse Data into DWH. Here the Daily Dummy Table RETURNS_DAILY:
        if verbose: 
            print("\n\t\t\t ************* Parsing Data into DWH TEAMS_PRD.RISK_DATA.RETURNS_DAILY *************\n")
        
        if _getpass.getuser() == 'root':
            try:
                db.pandas2db(rets_db, 'TEAMS_PRD.RISK_DATA.RETURNS_DAILY', replace=True)
            except Exception:
                print(rets_db.head())
                print('Length of DataFrame: %s'%len(rets_db))
                print("\t\t\tWARNING: Potential Issue with parsing Data. Check: TEAMS_PRD.RISK_DATA.RETURNS_DAILY")
                pass
        else:
            db.pandas2db(rets_db,'TEAMS_PRD.RISK_DATA.RETURNS_DAILY', replace=True)

        if verbose: 
            print("\n\t\t\t ************* Merging Data in DWH with TEAMS_PRD.RISK_DATA.RETURNS_DAILY_CLEAN *************\n")
        
        # Merge data with RETURNS_DAILY_CLEAN
        qry = 'merge into TEAMS_PRD.RISK_DATA.RETURNS_DAILY_CLEAN as tgt_table ' \
            'using TEAMS_PRD.RISK_DATA.RETURNS_DAILY as src_table ' \
            'on(tgt_table.ddate = src_table.ddate AND tgt_table.code = src_table.code) ' \
            'when not matched then ' \
            'insert(ddate,code,value) values(src_table.ddate,src_table.code,src_table.value)'

        if _getpass.getuser() == 'root':
            try:
                db.run_query(query=qry, fmt_engine='RISK')
            except Exception:
                print("\t\t\tWARNING: Potential Issue with Merging Data in RETURNS_DAILY_CLEAN")
                pass
        else:
            db.run_query(query=qry, fmt_engine='RISK')



def get_inv_cds_spreads(symbols=None, df_info=None, update_db=False, verbose=True):
    """
    CDS Spreads Scrapper
    @param symbol: list, e.g. ['SPREAD_CDS_JPM_5Y']
    @return: Dictionary of Single CDS Spreads and DataFrame for DWH Import
    """

    # Check Inputs
    if symbols is None and df_info is None and update_db is False:
        sys.exit('ERROR: You need to pass a list of symbols and an info DataFrame for the Mappings')

   

    # Set Outputs
    out_dict = dict()
    out_ts = pd.DataFrame()
    out_db = pd.DataFrame()

    if update_db:
        qry = '''
                SELECT
                    * 
                FROM 
                    TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING_CDS_SPREADS_CORP 
                WHERE 
                    ACTIVE = 1
                AND
                    mapping_rf IS NULL
               '''
        df_info = db.run_query(query=qry)

        if symbols is None:
            symbols = list(df_info.instrument_id)
        else:
            df_info = df_info[df_info.instrument_id.isin(symbols)]

    df_info = df_info.rename(columns=lambda x: x.lower())
    df_info = df_info.set_index('instrument_id')
    for sym in symbols:
        try:
            if verbose:
                print('Running Request for: %s' % sym)
            tmp_url = df_info.loc[sym].dummy_link
            tmp_url = tmp_url.split("&")[1][4:]


            # Request the Data
            time.sleep(45)

            #html_tmp = requests.get(tmp_url)
            #tmp = pd.read_html(html_tmp.text)[0]
            tmp = dtm.fetch_cds_investing_table(tmp_url)

            # Format Temporary Output
            tmp = tmp[['Date', 'Price']]
            tmp['Date'] = tmp['Date'].apply(lambda x: x.date())
            tmp['Price'] = tmp['Price'].astype(float)
            tmp.columns = ['ddate', sym]
            tmp = tmp.set_index('ddate')
            tmp = tmp.sort_index()

            # Append to Outputs
            out_dict[sym] = tmp
            out_ts = pd.concat([out_ts, tmp], axis=1)
            
        except Exception:
            out_dict[sym] = pd.DataFrame()
            print(traceback.format_exc())

    #Fill Missing Values
    out_db = pd.melt(out_ts.fillna(method='ffill').reset_index(), id_vars='ddate', var_name='code')

    if update_db:
        return out_dict, out_db, df_info
    else:
        return out_dict, out_db


def update_inv_cds_spreads(verbose=True):
    """
    Updates CDS Spread Series
    """

    import getpass as _getpass


    out_dict, out_db, df_info = get_inv_cds_spreads(update_db=True)

    #Adding Custom Syms for DWH Upload
    custom_syms = list(df_info[~df_info.mapping_rf.isnull()].mapping_rf)
    dict_custom_syms = dict(zip(custom_syms, df_info[~df_info.mapping_rf.isnull()].index))
    out_custom = out_db[out_db['code'].isin(custom_syms)]
    out_custom['code'] = out_custom['code'].map(dict_custom_syms)

    # Concat to DB output:
    out_db = pd.concat([out_db, out_custom], axis=0)
    out_db = out_db[~out_db['value'].isnull()]

    if _getpass.getuser() == 'root':

        try:
            db.run_query(query='CREATE TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY_DUMMY '
                               'CLONE TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY')
        except:
            if verbose:
                print("WARNING: Potential Issue with creating Risk Metrics Dummy Table.")
            pass

        try:
            db.pandas2db(out_db,'TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY_DUMMY',replace=True)
        except:
            if verbose:
                print(out_db.head())
                print('Length of DataFrame: %s' % len(out_db))
                print("WARNING: Potential Issue with parsing Data. Check: TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY_DUMMY")
            pass
    else:
        db.run_query(query='CREATE TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY_DUMMY '
                           'CLONE TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY')
        db.pandas2db(out_db, 'TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY_DUMMY',replace=True)

    qry_rm = 'merge into TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY as tgt_table ' \
             'using TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY_DUMMY as src_table ' \
             'on(tgt_table.ddate = src_table.ddate AND tgt_table.code = src_table.code) ' \
             'when not matched then ' \
             'insert(ddate,code,value) values(src_table.ddate,src_table.code,src_table.value)'

    try:
        db.run_query(query=qry_rm,fmt_engine='RISK')
    except:
        if verbose:
            print("WARNING: Potential Issue with mergin Risk Metrics CDS Spreads Dummy Table.")
        pass

    try:
        db.run_query(query='DROP TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_CDS_SPREADS_DAILY_DUMMY')
    except:
        if verbose:
            print("WARNING: Potential Issue with dropping Risk Metrics CDS Spreads Dummy Table.")
        pass


def get_inv_gov_yields(symbols=None, df_info=None, startdate=date(2000, 1, 1), enddate=date(2023, 8, 29), update_db=False, verbose=True):
    """
    Government Yields Scrapper
    @param symbol: list, e.g. ['YIELD_AU_30Y']
    @return:
    """

    import requests, traceback, time

    if symbols is None and df_info is None and update_db is False:
        sys.exit('ERROR: You need to pass a list of symbols and an info DataFrame for the Mappings')
    if update_db:
        qry = '''
                SELECT
                    * 
                FROM 
                    TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING_GOV_BONDS
                WHERE 
                    ACTIVE = 1
               '''
        df_info = db.run_query(query=qry)
        symbols = list(df_info.instrument_id)

    if df_info is None:
        qry = '''
                SELECT
                    * 
                FROM 
                    TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING_GOV_BONDS
                WHERE 
                    ACTIVE = 1
               '''
        df_info = db.run_query(query=qry)


    # Set Outputs
    out_dict = dict()
    out_db = pd.DataFrame()

    df_info = df_info.rename(columns=lambda x: x.lower())
    df_info = df_info.set_index('instrument_id')
    for sym in symbols:
        time.sleep(25)
        try:
            if verbose:
                print('Running Request for: %s'%sym)
            # Format Parameter Strings
            start_fmt = _datetime.strftime(startdate, df_info.loc[sym].start_date_fmt)
            end_fmt = _datetime.strftime(enddate, df_info.loc[sym].end_date_fmt)
            name_fmt = df_info.loc[sym].name_str_inv.split(' ')[0]
            mat_fmt = '%20' if len(df_info.loc[sym].maturity) == 3 else '%'+df_info.loc[sym].maturity
            # Build URL string
            url_tmp = df_info.loc[sym].dummy_link%(start_fmt, end_fmt, df_info.loc[sym].country_str_inv, name_fmt, mat_fmt)

            # Request the Data
            html_tmp = requests.get(url_tmp)
            tmp = pd.read_html(html_tmp.text)[0]

            # Format Temporary Output
            tmp['Date'] = tmp['Date'].apply(lambda x: _datetime.strptime(x,'%b %d, %Y').date())
            tmp = tmp[['Date', 'Price']]
            tmp.columns = ['ddate', sym]
            tmp = tmp.set_index('ddate')
            tmp = tmp.sort_index()
            tmp[sym] /= 100

            # Append to Outputs
            out_dict[sym] = tmp
            out_db = pd.concat([out_db, pd.melt(tmp.reset_index(),id_vars='ddate',var_name='code')], axis=0)

        except:
            out_dict[sym] = pd.DataFrame()
            print(traceback.format_exc())


    if update_db:
        return out_dict, out_db, df_info
    else:
        return out_dict, out_db


def update_inv_gov_yields(startdate=None, enddate=None, verbose=True):
    """
    Updates Government Bond Yield Series
    """

    # Check Inputs
    if startdate is None or enddate is None :
        sys.exit('ERROR: You need to pass a startdate and an enddate')

    import getpass as _getpass

    out_dict, out_db, df_info = get_inv_gov_yields(startdate=startdate, enddate=enddate, update_db=True)


    if _getpass.getuser() == 'root':

        try:
            db.run_query(query='CREATE TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY_DUMMY '
                               'CLONE TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY')
        except:
            print("WARNING: Potential Issue with creating Risk Metrics Dummy Table.")
            pass

        try:
            db.pandas2db(out_db,'TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY_DUMMY',replace=True)
        except:
            print(out_db.head())
            print('Length of DataFrame: %s' % len(out_db))
            print("WARNING: Potential Issue with parsing Data. Check: TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY_DUMMY")
            pass
    else:
        db.pandas2db(out_db,'TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY_DUMMY', replace=True)

    qry_rm = 'merge into TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY as tgt_table ' \
             'using TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY_DUMMY as src_table ' \
             'on(tgt_table.ddate = src_table.ddate AND tgt_table.code = src_table.code) ' \
             'when not matched then ' \
             'insert(ddate,code,value) values(src_table.ddate,src_table.code,src_table.value)'

    try:
        db.run_query(query=qry_rm,fmt_engine='RISK')
    except:
        print("WARNING: Potential Issue with mergin Risk Metrics Gov Yield Table.")
        pass

    try:
        db.run_query(query='DROP TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_GOV_YIELDS_DAILY_DUMMY')
    except:
        print("WARNING: Potential Issue with dropping Risk Metrics Gov Yield Dummy Table.")
        pass


def update_prx_returns(symbols=None, prx_cat='ctp_banks', fill_days=15, sdate=None, edate=None, verbose=True):
    """
    Updates Risk Factor Series
    """

    import getpass as _getpass

    if symbols is None and prx_cat == 'ctp_banks':
        # Get Coutnerparty Banks Tickers:
        if verbose:
            print("\n ************* Fetching Counterparty Banks Mapping from DWH *************\n")
        cds_map = db.run_query(query='SELECT * FROM TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING_CDS_SPREADS_CORP')
        # Drop Country CDS
        cds_map = cds_map.dropna(subset='symbol_yahoo')
        symbols = list(cds_map.symbol_yahoo)


    # Get Prices:
    if sdate is None:
        sdate = (_datetime.today() - timedelta(fill_days)).date()
    if edate is None:
        edate = _datetime.today().date()
    if verbose:
        print("\n ************* Fetching Prices from Yahoo Finance *************\n")
    prx = get_yahoo_prices(symbols=symbols, startdate=sdate, enddate=edate)


    # Format Data:
    rets = prx.pct_change().dropna(axis=0, how='all')
    rets = rets.loc[(rets != 0).any(axis=1)]
    rets = rets.rename(columns=dict(zip(cds_map.symbol_yahoo, [k.split('_')[-2] for k in cds_map.instrument_id])))
    rets.index.name = 'ddate'

    # Format for DB Parse:
    rets_db = rets.rets2db().dropna()
    rets_db = rets_db[rets_db['value'] != 0]

    # Parse Data into DWH. Here the Daily Dummy Table RETURNS_DAILY:
    if verbose: print("\n ************* Parsing Data into DWH TEAMS_PRD.RISK_DATA.RETURNS_DAILY *************\n")


    if _getpass.getuser() == 'root':
        try:
            db.pandas2db(rets_db, 'TEAMS_PRD.RISK_DATA.RETURNS_DAILY', replace=True)
        except:
            print(rets_db.head())
            print('Length of DataFrame: %s'%len(rets_db))
            print("WARNING: Potential Issue with parsing Data. Check: TEAMS_PRD.RISK_DATA.RETURNS_DAILY")
            pass
    else:
        db.pandas2db(rets_db,'TEAMS_PRD.RISK_DATA.RETURNS_DAILY', replace=True)

    if verbose: print("\n ************* Merging Data in DWH with TEAMS_PRD.RISK_DATA.RETURNS_DAILY_CLEAN *************\n")
    # Merge data with RETURNS_DAILY_CLEAN
    qry = 'merge into TEAMS_PRD.RISK_DATA.RETURNS_DAILY_CLEAN as tgt_table ' \
        'using TEAMS_PRD.RISK_DATA.RETURNS_DAILY as src_table ' \
        'on(tgt_table.ddate = src_table.ddate AND tgt_table.code = src_table.code) ' \
        'when not matched then ' \
        'insert(ddate,code,value) values(src_table.ddate,src_table.code,src_table.value)'

    if _getpass.getuser() == 'root':
        try:
            db.run_query(query=qry, fmt_engine='RISK')
        except:
            print("WARNING: Potential Issue with Merging Data in RETURNS_DAILY_CLEAN")
            pass
    else:
        db.run_query(query=qry, fmt_engine='RISK')








