#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Import Python Modules
import numpy as np
from datetime import datetime as _datetime, date

# Custom Modules
from tools import pandas_patched as pd
from tools.snowflake_db import db_connection as db



def get_universe(filename=None, project='caracalla'):

    if filename is None and project == 'caracalla':
        filename = '/Volumes/GoogleDrive/My\ Drive/Risk/Data/DataRaw/caracalla_universe.csv'
        filename = filename.replace("\/", "").replace("\\", "")
        print("\n ***************** Reading data *****************\n")
        print("Project %s - Opening file: %s"%(project, filename.split('/')[-1]))

        df = pd.read_csv(filename)
        df = df.set_index('INSTRUMENT_ID')

    return df


def enrich_data(symbols=[], verbose=True):
    """
    Enriches data with investpy and yahoo finance
    """
    # Importing Modules
    import investpy

    n = 0
    out = pd.DataFrame(index = symbols, columns=['symbol_investing',
                                                 'symbol_yahoo',
                                                 'name',
                                                 'full_name',
                                                 'currency',
                                                 'country',
                                                 'asset_class',
                                                 'sector',
                                                 'industry',
                                                 'exchange',
                                                 'exchange_code',
                                                 'err_investing',
                                                 'err_yahoo'])
    for sym in symbols:
        if len(symbols[:symbols.index(sym)]) % 250 == 0:
            n += 250
            print("\t\t\tPassed %sth iteration. Remaining %s"%(n, len(symbols)-n))
        # Screening Investing.com
        try:
            tmp_inv = investpy.stocks.search_stocks(by = 'isin', value = sym)
            tmp_inv = tmp_inv[['symbol', 'name', 'full_name', 'currency', 'country']]
            tmp_inv = tmp_inv.rename(columns={'symbol':'symbol_investing'})
            out.loc[sym, tmp_inv.columns] = tmp_inv.values
        except:
            out.loc[sym, 'err_investing'] = 1
            pass

        # Screening yahoofinance
        try:
            tmp_yf = _yf_enrich_data(sym, fmt=['exchange', 'symbol', 'typeDisp', 'exchDisp', 'sector', 'industry'])
            tmp_yf = tmp_yf.rename(columns = {'exchange' : 'exchange_code',
                                              'symbol' : 'symbol_yahoo',
                                              'typeDisp' : 'asset_class',
                                              'exchDisp' : 'exchange',
                                              })
            out.loc[sym, tmp_yf.columns] = tmp_yf.values
        except:
            out.loc[sym, 'err_yahoo'] = 1
            pass

    return out


def sid(sym_str, verbose=True):
    """
    Gains Security Inforamtion such as Name or Currency.
    @param sym_str: string, e.g. ISIN or Name ('Apple')
    """
    from tools import config as cf

    out_dict = dict()
    for info_dict in cf.cache_info.keys():
        tmp = cf.cache_info[info_dict]
        if sym_str in tmp.index:
            out_dict[info_dict] = tmp.loc[[sym_str]]
        for col in [k for k in tmp.columns if 'name' in k.lower()] or [k for k in tmp.columns if 'description' in k.lower()]:
            if tmp[tmp[col].str.contains(sym_str)].empty is False:
                out_dict[info_dict] = tmp[tmp[col].str.contains(sym_str)]


    if len(out_dict.keys()) == 0:
        print('Could not find "%s"'%sym_str)
    else:
        return out_dict


def yf_enrich_data_scrap(sym_isin, fmt=['exchange', 'shortname', 'symbol', 'typeDisp', 'exchDisp', 'sector', 'industry']):
    """
    Converts ISINs to yahoo finance tickers
    @param sym_isin: ISIN code of 12 charcaters, e.g. IE00B4L5Y983
    @param fmt: list of quotes keys

    Yahoo finance 'quotes' output on DK0010244508:
    {'exchange': 'CPH',
     'shortname': 'A.P. Møller - Mærsk B A/S',
     'quoteType': 'EQUITY',
     'symbol': 'MAERSK-B.CO',
     'index': 'quotes',
     'score': 21913.0,
     'typeDisp': 'Equity',
     'longname': 'A.P. Møller - Mærsk A/S',
     'exchDisp': 'Copenhagen',
     'sector': 'Industrials',
     'industry': 'Marine Shipping',
     'isYahooFinance': True}

    """
    # Import modules:
    import requests

    # Yahoo finance search header
    url = 'https://query1.finance.yahoo.com/v1/finance/search'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; '
                             'Intel Mac OS X 10_15_7) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/98.0.4758.109 Safari/537.36' }

    # Define Params
    params = dict(
        q=sym_isin,
        quotesCount=1,
        newsCount=0,
        listsCount=0,
        quotesQueryId='tss_match_phrase_query'
    )

    # Fetch Symbols
    resp = requests.get(url=url, headers=headers, params=params)
    data = resp.json()
    if 'quotes' in data and len(data['quotes']) > 0:
        out_vals = [data['quotes'][0][k] if k in fmt else np.nan for k in data['quotes'][0].keys()]
        out = pd.DataFrame([out_vals], columns = data['quotes'][0].keys())
        out['ISIN'] = sym_isin
        return out
    else:
        return pd.DataFrame([len(fmt)*[np.nan]], columns = fmt)


def multiproc_yf_enrich_data(symbols, n_cores=1, verbose=1):
    """
    Multiproc Tool for Enrich Data
    """
    # Import Modules:
    import multiprocessing
    from joblib import Parallel, delayed

    ctx = multiprocessing.get_context(method = 'forkserver')
    k = len(symbols)//n_cores
    # Adding up the list
    ff = [symbols[j*k:(j + 1)*k] for j in range(0, n_cores-1)]
    # Adding last element
    ff = ff + [symbols[(n_cores-1)*k:]]
    iter_zip = zip(ff, len(ff) * [verbose])
    tmp = Parallel(n_jobs = n_cores, verbose = True, backend = ctx)(delayed(_yf_enrich_data)(syms, verbose) for (syms, verbose) in iter_zip)

    # Reframe Multiproc Output
    out = tmp[0]
    for l in range(1, len(tmp)):
        out = out.append(tmp[l])

    return out

def _yf_enrich_data(symbols,verbose):

    # Import Modules
    import yfinance as yf
    import time

    out = pd.DataFrame(yf.Ticker(symbols[0]).info.items())
    out.columns = ['code', symbols[0]]
    out = out.set_index('code').T

    count = 0
    if len(symbols) > 1:
        for k in symbols[1:]:
            time.sleep(10)
            if verbose:
                if count%10 == 0: print("\t\t\t Screened %s columns"%count)
            tmp = pd.DataFrame(yf.Ticker(k).info.items())
            tmp.columns = ['code', k]
            tmp = tmp.set_index('code').T
            out = pd.concat([out, tmp], axis = 0)
            count += 1

    return out



def bond_universe_rpf(df):

    from tools.snowflake_db import db_connection as db
    # Select Info from Snowflake
    qry_bond_info = '''
                    SELECT
                        WM."isin" AS INSTRUMENT_ID,
                        WM.gd161::text AS COUNTRY_ISO3166_ORIGIN,
                        WM.gd162::text AS COUNTRY_ISO3166_ISSUER,
                        WM.gd172::text AS CURRENCY,
                        WM.gd090::text AS ISSUE_DATE,
                        WM.gd669::text AS ISSUER_PRICE,
                        WM.gd290a::text AS FIRST_COUPON,
                        WM.gd300::text AS LAST_COUPON,
                        WM.gd312::text AS COUPON_FREQ,
                        WM.gd455a::text AS MIN_INCREMENT,
                        WM.gd801a::text AS COUPON,
                        WM.gd810::text AS DAY_COUNT,
                        WM.gd910::text::date AS MATURITY,
                        WM.GD133A::text AS RATING
                    FROM
                        teams_prd.source_instrument_partners.src__instrument_partners__wmdaten_instruments_view AS WM 
                    WHERE
                        WM."isin" in (%s)
                    '''

    qry_bond_prices = '''
                        SELECT
                            pr.price_dt as ddate, 
                            pr.instrument_id as symbol, 
                            pr.close_mid_price  AS price
                        FROM 
                            TEAMS_PRD.TRANSFORM_AUM.TRF__AUM__EOD_PRICE_FEED as pr
                        INNER JOIN 
                            TEAMS_PRD.CORE_MART.MRT_CURR__INSTRUMENTS as secs_info
                            ON secs_info.instrument_id = pr.instrument_id
                        WHERE
                            pr.EXCHANGE = 'LSX'
                        AND
                            pr.instrument_id in (%s)
                        ORDER BY 1,2
                        '''

    # Build Output
    # Bond WM Info
    tmp_bond_info = db.run_query(query=qry_bond_info%db.joinpad(list(df.index)))
    out = tmp_bond_info.set_index('instrument_id')

    # Bond Prices
    tmp_bond_prices = db.run_query(query=qry_bond_prices%db.joinpad(list(df.index)))
    df_bond_prices = pd.pivot_table(tmp_bond_prices,index='ddate',columns='symbol',values='price')
    # Remove column index name
    df_bond_prices = df_bond_prices.rename_axis(None,axis=1)
    # FrontFill Prices then Backfill
    df_bond_prices = df_bond_prices.fillna(method='ffill').fillna(method='bfill')



def bond_ratings(df_orig, calc_avg_rtg=True):


    df = df_orig.copy()

    # Get Rating Scales
    rat_scales = db.run_query(query="SELECT * FROM TEAMS_PRD.RISK_DATA_SENSITIVE.RISK_CREDIT_RATING_SCALES")

    # Create Dictionaries
    dict_moodys = dict(zip(rat_scales.moodys, rat_scales.num_value))
    dict_sp = dict(zip(rat_scales.sp, rat_scales.num_value))
    dict_fitch = dict(zip(rat_scales.fitch, rat_scales.num_value))


    # Cleaning Up Strings:
    df_info = df.iloc[:, :4]
    df_rat = df.iloc[:, -4:]
    df_rat = df_rat.replace(np.nan, "NR", regex=True)
    df_rat = df_rat.replace("u", "", regex=True)

    # Replace last bits, which can't be replaced by dataframe regex method and map rating num scales
    for col in df_rat.columns:
        # Replace Strings
        df_rat[col] = df_rat[col].apply(lambda x: x.replace("*-", "").replace("*+", "").replace("*", ""))

        # Map Numerical Values
        if col == 'RTG_MOODY':
            df_rat[col + '_NUM'] = df_rat[col].map(dict_moodys)
        elif col == 'RTG_SP':
            df_rat[col + '_NUM'] = df_rat[col].map(dict_sp)
        elif col == 'RTG_FITCH':
            df_rat[col + '_NUM'] = df_rat[col].map(dict_fitch)
        elif col == 'BB_COMPOSITE':
            df_rat[col + '_NUM'] = df_rat[col].map(dict_fitch)

    # Replace empty placeholders
    df_rat = df_rat.replace(" ", "", regex=True)


    # Calculate Average Rating:
    df_rat['RTG_AVG_NUM'] = df_rat.iloc[:, -4:].mean(axis=1)
    # Map to Fitch Rating while rounding down
    df_rat['RTG_AVG'] = np.ceil(df_rat['RTG_AVG_NUM']).map(dict(zip(rat_scales.num_value, rat_scales.fitch)))

    # Merge Data
    out = pd.concat([df_info, df_rat], axis=1)


    return out



