#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Import Python Modules
from datetime import date
import numpy as np
import pandas as pd

# Custom Modules
from tools.snowflake_db import db_connection as db
from instruments import data_rf_wrapper as rw
from instruments import data_prices as dtp
from risk_analytics import risk_engines as rie



def get_port(sec_acc_no,report_date,**kwargs):
    """
    Portfolio Position and Risk Factor Exposures Fetcher

    Args:
        sec_acc_no (int): Security Account Number
        report_date (date): Report Date for Position Fetching
        **kwargs: Additional keyword arguments  for customization:
            - force_rf (bool): If True, forces bonds to 'global_agg_bond' and unmapped risk factors to 'msci_world'.
            - calc_risk (bool): If True, calculates risk metrics for the portfolio.
            - risk_engines (dict): A dictionary specifying risk engines and their parameters.
            - account (str): Optional account identifier for database output.
            - rm2db (bool): If True, uploads risk metrics to the database.
    Returns:
        out_dict (dict): A dictionary containing:
            - 'inventory': DataFrame with portfolio positions and risk factor mappings.
            - 'rf_portfolio': DataFrame with risk factor portfolio weights.
            - 'returns': DataFrame with returns of the risk factors.
            - 'rf_portfolio_returns': Series with portfolio returns based on risk factors.
            - 'risk_metrics': DataFrame with calculated risk metrics (if calc_risk is True).
            - 'risk_metrics_sorted': DataFrame with sorted risk metrics for visualization (if calc_risk is True).
            - 'out_db_rm': DataFrame formatted for database upload (if calc_risk is True).  
    """

    # Setting Print Variables
    verbose = kwargs.get('verbose', False)

    # Setting Output
    out_dict = dict()

    # Get Positions
    qry ='''
    SELECT
        *
    FROM
        TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation
    WHERE
        1=1
    AND
        report_date = %s 
    AND
        sec_acc_no = %s
    ORDER BY 1;
    '''

    df = db.run_query(query=qry%(db.sqldate(report_date),sec_acc_no))
    
    # Adding columns
    df['weight'] = df['mkt_mid_eur'].abs()/df['mkt_mid_eur'].abs().sum()

    # Get Risk Factor Mapping
    df_map = rw.rf_mapping_engine(df,verbose)
    df_port = pd.merge(df, df_map[['instrument_id','risk_factor','oas_series']], on='instrument_id')
    df_port = df_port.dropna(subset=['weight'])

    if 'force_rf' in kwargs.keys():
        # Force Bonds to global_agg_bond
        df_port.loc[df_port.instrument_type == 'BOND', 'risk_factor'] = 'global_agg_bond'
        # Force Unmapped Risk Factor to Msci World
        df_port.loc[df_port.risk_factor.isnull(), 'risk_factor'] = 'msci_world'
        df_port.loc[df_port.currency.isnull(), 'currency'] = 'EUR'

    # Remove all quantity zero positions
    df_port = df_port[df_port.quantity != 0]

    out_dict['inventory'] = df_port

    # Build Risk Factor Portfolio
    rf_dict = build_rf_portfolio(df_port, report_date)
    out_dict = {**out_dict, **rf_dict}


    if 'calc_risk' in kwargs.keys():

        df_risk = pd.DataFrame()
        if'risk_engines' in kwargs.keys():
            risk_engines = kwargs['risk_engines']
        else:
            # Set Quantile List
            qtls = [0.05, 0.01, 0.001]
            # Set Window:
            window = 250
            # Activates in code prints:
            print_verbose = False
            risk_engines = {
            'gjr': {'qtls': qtls,'window': window,'distr': 't','fhs': True,'decay': 0.94,'verbose': print_verbose},
            'ewma': {'qtls': qtls,'window': window,'distr': 't','decay': 0.94,'verbose': print_verbose},
            'mc': {'qtls': qtls,'window': window,'distr': 't','ewma_cov': True,'decay': 0.94,'n_sim': 1000,
                   'verbose': print_verbose},
            'hs': {'qtls': qtls,'window': window,'verbose': print_verbose}}

        for k in risk_engines:
            fmt_engine_tmp = risk_engines[k]

            # Distinguish between MonteCarlo (Risk Factors TimeSeries) and GARCH/EWMA Inputs (Portfolio TimeSeries)
            rets_vaR = out_dict['returns'] if k == 'mc' else out_dict['rf_portfolio_returns']
            wgts_vaR = out_dict['rf_portfolio'].weight.values if k == 'mc' else np.array([1])
            tmp_var = rie.portfolio_vaR(rets_vaR,
                                        wgts_vaR,
                                        engine=k,
                                        fmt_engine=fmt_engine_tmp)
            tmp_var.columns = [tmp_var.columns[i] + '_%s' % k for i in range(0, len(tmp_var.columns))]
            df_risk = pd.concat([df_risk, tmp_var], axis=1)

        out_dict['risk_metrics'] = df_risk

        # Build Comprehensive DataFrame for Visualisations
        idx = list(set([k.split("_")[0] for k in df_risk.columns]))
        cols = list(set([k.split("_")[-1] for k in df_risk.columns]))
        out_risk = pd.DataFrame(columns=cols, index=idx).sort_index(ascending=True)

        for k in out_risk.columns:
            out_risk[k] = df_risk[[i for i in df_risk.columns if i.endswith(k)]].T.sort_index().values

        out_dict['risk_metrics_sorted'] = out_risk

        # Creating RiskMetrics Output for Database
        # Set Output
        out_db_rm = pd.DataFrame()

        # Fill Data
        out_rm = out_dict['risk_metrics']
        out_rm.index.name = 'ddate'
        out_db_rm = pd.concat([out_db_rm, out_rm.rets2db()],axis=0)

        # Filing Data with sec_acc_no or account
        if 'account' in kwargs.keys():
            out_db_rm['account'] = kwargs['account']
        else:
            out_db_rm['account'] = sec_acc_no
        out_db_rm = out_db_rm[['ddate', 'account', 'code', 'value']]
        
        # Append to Output
        out_dict['out_db_rm'] = out_db_rm.dropna()

        if 'rm2db' in kwargs.keys():
            db.pandas2db(out_dict['out_db_rm'],'TEAMS_PRD.RISK_DATA.RISK_METRICS_DAILY',merge=True)


    return out_dict


def build_rf_portfolio(df_port, report_date, calc_rets=True):
    """
    Fetches based on DWH portfolio the Risk Factor Exposures
    """

    out_dict = dict()

    df = df_port.copy()
    # Fetch Return Data: ##############################################################################################
    rf_map = db.run_query('SELECT * from TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__GSHEET_MRM_RFM_EQUITY')
    rf_map = rf_map.set_index('code')

    # Build Risk Factor Portfolio
    rf_columns = ['risk_factor', 'weight']
    # Set Support Risk Factor Columns to '' in order to not lose info while grouping
    rf_support_cols = ['oas_series']
    for col in rf_support_cols:
        try:
            df[col] = df[col].fillna('')
        except:  # noqa: E722
            pass

    # Build Bond Risk Factors
    # Concat Risk Factor and Oas Series for later Return Calculation
    rf_bond_wgts = df[df.instrument_type == 'BOND'][rf_columns + 
                                                    rf_support_cols].groupby(rf_columns[:1] + 
                                                                             rf_support_cols).sum(numeric_only=True)
    rf_bond_analytics = df[df.instrument_type == 'BOND'][rf_columns[:1] + 
                                                         rf_support_cols + 
                                                         ['duration_mod', 'convexity']].groupby(rf_columns[:1] + 
                                                                                                rf_support_cols).mean(numeric_only=True)
    rf_bond = pd.concat([rf_bond_wgts, rf_bond_analytics], axis=1)

    rf_port = df[df.instrument_type != 'BOND'][rf_columns + 
                                               rf_support_cols].groupby(rf_columns[:1] + 
                                                                        rf_support_cols).sum(numeric_only=True)[['weight']]
    rf_port = pd.concat([rf_bond, rf_port], axis=0)
    rf_port['currency'] = rf_port.index.get_level_values(0)
    rf_port['currency'] = rf_port.currency.map(dict(zip(rf_map.index, rf_map.currency)))
    rf_port['currency'] = rf_port['currency'].fillna('EUR')
    rf_port['currency_rf'] = rf_port['currency'].apply(lambda x: 'fx_eur%s' % x.lower())

    # Group and Filter
    rf_port_fx = rf_port.reset_index()[['currency_rf', 'weight']].groupby(['currency_rf']).sum(numeric_only=True)
    rf_port_fx = rf_port_fx[rf_port_fx.index.get_level_values(0) != 'fx_eureur'].reset_index()
    # Build Index with Risk Factor Support columns
    for col in rf_support_cols:
        rf_port_fx[col] = ''

    rf_port_fx = rf_port_fx.rename(columns={'currency_rf': 'risk_factor'})
    rf_port_fx = rf_port_fx.groupby(rf_columns[:1] + rf_support_cols).sum(numeric_only=True)
    rf_port = pd.concat([rf_port, rf_port_fx], axis=0).drop(['currency', 'currency_rf'], axis=1).sort_index()

    out_dict['rf_portfolio'] = rf_port

    # Get Returns. Loc with Value Date
    if calc_rets:
        rets = dtp.get_rf_returns(rf_port=rf_port, yield2tr=False)
        rets = rets[date(2008, 1, 1):report_date].fillna(0)
        rets = rets.loc[(rets != 0).any(axis=1)]
        rets = rets[[k for k in list(rf_port.index.get_level_values(0)) if k in rets]]

        # Crosscheck Retunrs and Weights
        rf_port_wgts = rf_port[rf_port.index.get_level_values(0).isin(rets.columns)]
        rets_wgts = rets[list(set(rf_port_wgts.index.get_level_values(0)))]

        out_dict['rf_portfolio'] = rf_port_wgts
        out_dict['returns'] = rets

        # Build Portfolio Timeseries
        out_dict['rf_portfolio_returns'] = rets_wgts.portfolio_rets(rf_port_wgts.weight.values)

    return out_dict


def get_public_pos(sec_acc_no):


    # sec_acc_no='9800005601' -- Private Markets

    qry='''
    SELECT
        "id" AS position_id,
        "sec_acc_no",
        "instrument_id",
        "gross_long",
        "gross_short",
        ("gross_long"-"gross_short") as net_position,
        "extraction_timestamp"
    FROM
        backend_prd.portfolio.anonymized_position --public_position 
    WHERE
        "sec_acc_no"=%s
    '''

    df=db.run_query(query=qry%(sec_acc_no))

    return df


def pos_hist_run(accts,list_ddate):
    """
    Run Historical Position Fetcher for List of Accounts and Dates
    """

    out_db = pd.DataFrame()
    err_list=dict()

    for acct in accts:
        for dd in list_ddate:
            print(f'Fetching Position for Account {acct} on Date {dd}')
            try:
                out_dict=get_port(acct,dd,force_rf=True,calc_risk=True)
                out_db=pd.concat([out_db,out_dict['out_db_rm']],axis=0)
            except:
                err_list[f'{acct}_{dd}']=f'Error Fetching Position for Account {acct} on Date {dd}'
                pass

    

    return out_db, err_list