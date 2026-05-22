#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime
import os
import sys
import getpass as _getpass

# Custom Python Modules
from risk_pylibrary.risk_analytics import risk_engines as re

# Set Username
user_name=_getpass.getuser()




def run_all_scenario_svar(value_date, accounts=None, fmt_engine_base=None,verbose=1):
    """
    Runs rolling stressed_vaR for each scenario and engine type.
    Supports any engine implemented in the original stressed_vaR().
    """
    out = {}
    if verbose:
        print('*********** Running Rolling Stressed VaR **********')

    if accounts is None:
        accounts=['tiberius', 'caligula', 'caracalla', 'trajan']

    # Get Trading Book Portfolios
    if verbose:
        print('\t\t Building Trading Books')

    out_wgts, out_pf_rets, out_rets = build_trading_book_info(accounts,value_date)

    # Get Scnearios
    if verbose:
        print('\t\t Retrieving Stress Scenarios')
    scenario_df=pd.read_excel(r'/Users/%s/Downloads/20250411_UpdateStressScenarioTable.xlsx'%user_name)

    scenario_type_map = {'Historical': 'hs'}
    
    if fmt_engine_base is None:
        fmt_engine_base={'qtls': [0.01,0.001], 'holding_period': 1, 'window': 250}

    # Build Output
    out=pd.DataFrame(index=scenario_df.code, columns=out_wgts.columns)

    for acct in accounts:
        
        # Set PF returns:
        acct_rets=out_pf_rets[[acct]]

        for _, row in scenario_df.iterrows():

            # Set Parameters
            code = row['code']
            start_date = row['shock_startdate'].date()
            length = int(row['shock_length'])
            scenario_type = row['scenario_type']
            engine = scenario_type_map.get(scenario_type, 'hs')
            window = fmt_engine_base.get('window', 250)
            rets_window = acct_rets.iloc[acct_rets.index.get_loc(start_date)-250:acct_rets.index.get_loc(start_date)+length]

            print(len(rets_window))

            if len(rets_window) < length + window:
                print(f"[!] Skipping {code}: not enough data for {window + length} days from {start_date}")
                continue

            print(f"Running rolling stressed_vaR for {code} ({scenario_type}) using engine: {engine}")

            try:
                result = re.stressed_vaR(rets_orig=rets_window,wgts=np.array([[1]]),engine=engine,fmt_engine=fmt_engine_base,verbose=verbose)
            except Exception as e:
                print(f"[!] Error calculating VaR on {code} with engine {engine}: {e}")

            out.loc[code][acct] = result.var999_1d.max()

    return out


def build_trading_book_info(accounts, value_date):
    
    from risk_pylibrary.projects.caracalla import caracalla_portfolio as c_port
    from datetime import date

    accounts=['tiberius','caligula','caracalla','trajan']
    risk_engines = {'hs': {'qtls': [0.001],'window': 250,'verbose': 1}}

    # Set Outputs
    out_wgts=pd.DataFrame()
    out_pf_rets=pd.DataFrame()

    for account in accounts:
        out_dict_tmp = c_port.get_caracalla_portfolio(calc_rf_port=True,value_date=value_date,risk_engines=risk_engines,rf_mapping_new=True,force_rf=True, new_pf_engine=True,live_trading=False,account=account)
        
        tmp_rf=out_dict_tmp['rf_portfolio']
        tmp_rf=tmp_rf.reset_index()[['risk_factor','weight']].groupby('risk_factor').sum()
        tmp_rf.columns=[account]
        out_wgts=pd.concat([out_wgts,tmp_rf],axis=1)

        # portfolio return
        tmp_pf_ret=out_dict_tmp['rf_portfolio_returns']
        tmp_pf_ret.columns=[account]
        out_pf_rets=pd.concat([out_pf_rets,tmp_pf_ret],axis=1)

        # Risk Factor Returns
        rets=out_dict_tmp['returns']
        out_rets = rets.loc[:,~rets.columns.duplicated()].copy()

    
    return out_wgts, out_pf_rets, out_rets