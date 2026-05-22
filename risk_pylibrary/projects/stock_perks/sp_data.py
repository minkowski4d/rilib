#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Import Python Modules
import numpy as np
from datetime import datetime as _datetime

# Custom Modules
import pandas as pd


def sp_bundle(df=None, startdate=None, enddate=None, cut_total='q1|2023', re_rate_horizon='q1', verbose=True):
    """
    Fetches Bundle composed of stockperks data, econometrics and prices within given date range
    @param startdate: date object, e.g. date(2022,4,1)
    @param enddate: date object, e.g. date(2022,6,30)
    @param cut_total: second filter for quarter, e.g. 'q2|2022'
    """

    out_dict = dict()

    # Fetching Raw Data
    out_dict['data'] = get_sp_redemptions(df=df, startdate=startdate, enddate=enddate, verbose=verbose)

    # Run Analytics
    out_dict['econometrics'] = build_sp_analytics(out_dict['data'], cut_total=cut_total, re_rate_horizon=re_rate_horizon)

    # Get Returns
    out_dict['price_data'] = get_sp_returns(symbols=out_dict['data']['isin'].unique(), enddate=enddate)


    return out_dict

def get_stockperks_query(key_word):

    if key_word == 'redemption_rates':

        qry = "SELECT " \
                  "auth_account_id,perk_position_created_ts AS perk_position_created_ts," \
                  "perk_position_created_ts::date AS perk_position_created_date,expected_cost," \
                  "trade_ts AS redemption_ts,trade_ts::date AS redemption_date,actual_perk_cost,country,instrument_id AS isin " \
                  "FROM " \
                  "TEAMS_PRD.MARTS_INCENTIVES.MRT__TPERK_ONBOARDING_AND_REFERRAL " \
                  "WHERE " \
                  "perk_position_created_date > %s and perk_position_created_date <= %s"


    return qry

def get_sp_redemptions(df=None, startdate=None, enddate=None, cut_symbols=False, verbose=True):
    """
    Reads the stock perk redemptions and performs data cleaning.
    Current state: data is read via a .csv e.g.: /Users/fabioballoni/Downloads/sp_redemptions_all.csv

    """
    # Fetch Data from
    if verbose:
        print("\n ***************** Building up the data *****************\n")
        print("Step 0: Reading Data from snowflake table: TEAMS_PRD.MARTS_INCENTIVES.MRT__TPERK_ONBOARDING_AND_REFERRAL")

    if df is None:
        # Import Modules
        from tools.snowflake_db import db_connection as db

        # build qry
        qry = get_stockperks_query('redemption_rates')
        qry = qry%(db.sqldate(startdate), db.sqldate(enddate))
        # Get Data
        df = db.run_query(qry)

    if cut_symbols:
        ll_stocks = ['US0378331005', 'US0231351067', 'US88160R1014', 'US64110L1061', 'US5949181045',
                     'US6541061031', 'DE0007100000', 'DE0007664039', 'US2546871060']
        df = df[df.ISIN.isin(ll_stocks)]

    # Format data:
    # Rename columns to lower
    df = df.rename(columns = lambda x: x.lower())

    # Format 'PERK_POSITION_CREATED_TS' and 'REDEMPTION_TS', which are in str(yyyy-mm-dd H:M:S) format
    if verbose: print("Step 1: Formatting Timestamp Objects")
    for k in ['perk_position_created_ts', 'redemption_ts']:
        # Replacing string artifacts
        df[k] = df[k].replace(np.nan, '', regex=True)
        df[k] = df[k].replace('T', ' ', regex=True)
        df[k] = df[k].replace('Z', '', regex=True)
        # Setting datetime dummy for consistent handling the format of the column
        dtime_dummy = _datetime(2500, 12, 31, 0, 0, 0)


    # Format data:
    # Format 'PERK_POSITION_CREATED_DATE' and 'REDEMPTION_DATE' which are already in str(yyyy-mm-dd) format
    if verbose: print("Step 2: Formatting Date Objects")
    for k in ['perk_position_created_date', 'redemption_date']:
         # Insert date dummy for consistent handling the format of the column
         df[k] = df[k].replace(np.nan, '2500-12-31', regex=True)
         #df[k] = df[k].apply(lambda x: _datetime.strptime(x, '%Y-%m-%d').date())


    # Clean the data:
    if verbose:
        print("\n ***************** Performing Data Quality Check *****************\n")
    # 1. Remove Data, if expected_cost AND actual_perk_cost == NaN
    tmp_costs_nan = df[(df.expected_cost.isnull()) & (df.actual_perk_cost.isnull())]
    tmp_costs_nan['counter'] = 1
    tmp_costs_nan_grp = tmp_costs_nan[['country', 'counter']].groupby('country').sum()
    if verbose:
        print('\t 1. Missing expected and actual perk costs (Amount allocated and executed):\n')
        print('\t\t Total Percentage Missing: %s %%'%(np.round(tmp_costs_nan_grp.counter.sum() / len(df)*100, 5)))
        print('\t\t Solution: dropping these entries!\n')

    # Eliminating entries
    df = df.reindex(list(set(df.index)-set(tmp_costs_nan.index)))

    # 2. Check for expected_cost == NaN, but actual_perk_cost != NaN
    tmp_exp_cost = df[(df.expected_cost.isnull())&(~df.actual_perk_cost.isnull())]
    tmp_exp_cost['counter'] = 1
    tmp_exp_cost_grp = tmp_exp_cost[['country', 'actual_perk_cost', 'counter']].groupby(['country']).sum()
    if verbose:
        print("\t 2. Missing expected perk costs (amount allocated):\n")
        print('\t\t Total Percentage Missing: %s %%'%np.round(tmp_exp_cost_grp.counter.sum() / len(df)*100, 5))
        print('\t\t Allocated Amount Missing: %s EUR'%np.round(tmp_exp_cost_grp.actual_perk_cost.sum(), 2))
        print('\t\t Percentage Amount as of Total Amount: %s %%'%np.round(tmp_exp_cost_grp.actual_perk_cost.sum() / df.actual_perk_cost.sum()*100, 5))
        print('\t\t Solution: dropping these entries!\n')

    # Eliminating entries
    df = df.reindex(list(set(df.index) - set(tmp_exp_cost.index)))



    return df


def enrich_sp_data(dforig, df_info, verbose=True):
    """
    Code for Instrument Type Enrichment
    @param dforig: dforig=spd.get_sp_redemptions(url, cut_symbols=False)
    @param df_info: dtp.get_sf_prices()['asset_info']

    returns: dictionary
    """

    # Create mapping dictionary:
    dict_info = dict(zip(df_info.instrument_id, df_info.instrument_type))

    # Map instrument_type:
    dforig['instrument_type'] = dforig['isin'].map(dict_info)

    # Check for unmapped securities:
    ll_missing = list(dforig[dforig['instrument_type'].isnull()]['isin'].unique())
    if verbose:
        print('Missing Mapping Information for these ISINs:')
        print('\t %s'%ll_missing)

    if 'XF000ETH0019' in ll_missing or 'XF000BTC0017' in ll_missing:
        # Assigning "CRYPTO" to BTC and ETH
        dforig['instrument_type'].loc[dforig['isin'].isin(['XF000ETH0019', 'XF000BTC0017'])] = 'CRYPTO'

    # Creating an output for each instrument type:
    out_dict = dict()
    for instr_type in dforig.instrument_type.unique():
        out_dict[instr_type] = dforig[dforig['instrument_type'] == instr_type]

    out_dict['dforig'] = dforig

    return out_dict


def build_sp_analytics(dforig, cut_total='q1|2023', re_rate_horizon='q1', verbose=True):

    # Savecopy df:
    df = dforig.copy()

    out_dict = dict()
    if verbose:
        print("\n ***************** Calculating up the validation tables *****************\n")

    # Create query dictionary for horizons:
    horizons = ['q1', 'q2', 'q3', 'q4']
    horizon_dict = dict()
    for h in [k for k in horizons if not k == 'total']:
        if h == 'q1':
            start_month = 1; end_month = 3
        elif h == 'q2':
            start_month = 4; end_month = 6
        elif h == 'q3':
            start_month = 7; end_month = 9
        elif h == 'q4':
            start_month = 10; end_month = 12
        # Assign values
        horizon_dict[h] = dict(zip(['start_month', 'end_month'], [start_month, end_month]))

    # Insert auxiliary columns string
    df['month_num'] = df.perk_position_created_date.apply(lambda x: x.month)
    df['year_num'] = df.perk_position_created_date.apply(lambda x: x.year)

    # Cut Input data to enddate:
    if cut_total:
        # Ceiling
        df = df[(df.month_num <= horizon_dict[cut_total.split("|")[0]]['end_month']) & (df.year_num <= int(cut_total.split("|")[1]))]
        # Floor
        df = df[(df.month_num >= horizon_dict[cut_total.split("|")[0]]['start_month']) & (df.year_num >= int(cut_total.split("|")[1]))]

    # Create output dataframe
    out_alloc = pd.DataFrame()
    # Build Validation Summary Table for Total and Quarterly Figures
    for y in df.year_num.unique():
        tmp = df[df.year_num == y]
        for horizon in horizons:
            # Call limits:
            start = horizon_dict[horizon]['start_month']
            end = horizon_dict[horizon]['end_month']
            print(start, end)
            tmp_q = tmp[(tmp.month_num >= start) & (tmp.month_num <= end)]
            if tmp_q.empty:
                pass
            else:
                # Calculate KPIs
                tmp_q = tmp_q[['country', 'expected_cost', 'actual_perk_cost']]
                tmp_q['counter'] = 1
                tmp_grp = tmp_q.dropna(how='any').groupby('country').sum()
                tmp_grp.columns = ['amount_allocated', 'amount_executed', 'count_of_transactions']
                tmp_grp = tmp_grp[['count_of_transactions', 'amount_allocated', 'amount_executed']]
                tmp_grp['difference'] = tmp_grp.amount_allocated - tmp_grp.amount_executed
                # Add Totals for every columns except "ratio"
                for k in tmp_grp.columns:
                    tmp_grp.loc['total', k] = tmp_grp[k].sum()

                # Calculate ratio:
                tmp_grp['ratio'] = tmp_grp.amount_executed / tmp_grp.amount_allocated

                # Store in output dataframe
                tmp_grp = tmp_grp.reset_index()
                tmp_grp['year'] = str(y)
                tmp_grp['quarter'] = str(horizon)
                out_alloc = pd.concat([out_alloc, tmp_grp], axis = 0)

    # Assign to output dictionary
    out_dict['quarters'] = out_alloc.sort_values(by=['year', 'quarter'])


    if verbose:
        print("\n ***************** Calculating redemption rates *****************\n")

    # Slicing to the last 90 days of given data:
    df_re_rate = df[(df.month_num <= horizon_dict[re_rate_horizon]['end_month'])
                    & (df.year_num <= int(cut_total.split("|")[1]))]
    # Floor
    df_re_rate = df_re_rate[(df_re_rate.month_num >= horizon_dict[re_rate_horizon]['start_month'])
                            & (df_re_rate.year_num >= int(cut_total.split("|")[1]))]

    out_re_rate = pd.DataFrame(index = df_re_rate.country.unique(), columns = ['avg_redemption_rate'])
    for cty in df_re_rate.country.unique():
        tmp = df_re_rate[df_re_rate['country'] == cty]
        out_re_rate.loc[cty, 'avg_redemption_rate'] = len(tmp[~tmp.actual_perk_cost.isnull()])/len(tmp)

    # Assign to output dictionary
    out_dict['avg_redemption_rate_%s'%re_rate_horizon] = out_re_rate


    if verbose:
        print("\n ***************** Calculating allocation probabilities *****************\n")

    df_stats = pd.DataFrame(index = dforig['isin'].unique())
    for k in dforig.country.unique():
        df_tmp = dforig[dforig.country == k][['isin', 'expected_cost']].groupby(['isin']).sum()
        df_tmp /= df_tmp.expected_cost.sum()
        df_tmp_mean = dforig[dforig.country == k][['isin', 'expected_cost']].groupby(['isin']).mean()
        df_stats = df_stats.join(df_tmp.rename(columns = {'expected_cost':'weight_'+k}))
        df_stats = df_stats.join(df_tmp_mean.rename(columns = {'expected_cost': 'avg_perk_'+k}))

    out_dict['stats'] = df_stats[df_stats.T.sort_index().index].fillna(0)


    if verbose:
        print("\n ***************** Calculating Average Delta Perk Cost *****************\n")

    tmp = dforig[['perk_position_created_date','expected_cost','actual_perk_cost']].groupby('perk_position_created_date').sum()
    tmp = tmp.asfreq(freq='W-FRI').cumsum()
    tmp['delta']=tmp.expected_cost-tmp.actual_perk_cost
    out_dict['average_perk_exposure'] = tmp.delta.mean()/6

    return out_dict


def get_sp_returns(symbols=None, enddate=None):
    """
    Converts ISINs into Yahoo Ticker and Fetches Prices from yahoo finance

    @param: symbols list
    """

    # Import Modules
    from datetime import timedelta
    from risk_pylibrary.risk_models.pnl_support import get_prices_eod


    # Define Output Dictionary:
    out_dict = dict()

    # # Get Symbol Info
    # symbol_info = pd.DataFrame()
    # for k in symbols:
    #     symbol_info = pd.concat([symbol_info, yf_enrich_data_scrap(k)], axis = 0)

    # # Correct Symbols:
    # symbol_info = symbol_info.replace('IE00BG370F43.SG', 'XZEM.L')

    # out_dict['symbol_info'] = symbol_info.dropna(how='all', axis=1)

    # # Get Yahoo Prices:
    # prx = get_yahoo_prices(symbols=symbol_info['symbol'].tolist(), startdate=enddate-timedelta(360), enddate=enddate)
    # prx = prx.rename(columns = dict(zip(symbol_info.symbol, symbol_info.ISIN)))

    prx = get_prices_eod(syms=symbols, startdate=enddate-timedelta(360), enddate=enddate)


    out_dict['prices'] = prx.fillna(method='ffill').fillna(method='bfill').fillna(0)
    out_dict['returns'] = out_dict['prices'].pct_change()[-250:]
    out_dict['cov'] = out_dict['prices'].pct_change()[-250:].cov()

    return out_dict
                







