#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime

# Python Charting
from matplotlib.pyplot import *
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib import ticker
from matplotlib import transforms
import seaborn as sns
from matplotlib import cm

# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db
from risk_pylibrary.projects.caracalla import caracalla_universe as c_univ
from risk_pylibrary.instruments import data_prices as dtp
from risk_pylibrary.risk_analytics import risk_engines as rie


def get_caracalla_portfolio(live_trading=True, force_rf=True, calc_rf_port=False, calc_pnl_report=False,
                            calc_risk=False, rf_mapping_new=False, verbose=True, **kwargs):
    """
    Maps Caracalla Initial Inventory to Risk Factors
    """
    # Create output dictionary:
    out_dict = dict()

    if 'value_date' in kwargs.keys():
        value_date = kwargs['value_date']
    else:
        value_date = db.run_query(query="SELECT MAX(CALENDAR_DATE) as sdate "
                                        "FROM teams_prd.investing_publish.pbl__curr__ft_regulatory_reporting").iloc[
            0][0]

        # Reverting back to weekday:
        if value_date.weekday() in [5,6]:
            value_date = value_date - timedelta(1) if value_date.weekday() == 5 else value_date - timedelta(2)
            if verbose:
                print("Max Value Date is on Weekday %s. Reverted back to %s" % (value_date.weekday(),value_date))

    # Fetch Positions Data: ###########################################################################################
    if live_trading:

        if 'enable_wm_data' in kwargs.keys():
            qry_live = '''
                SELECT
                    pos.CALENDAR_DATE, 
                    pos.INSTRUMENT_ID,
                    pos.NAME_OFFICIAL,
                    pos.INSTRUMENT_TYPE,
                    pos.ISSUER,
                    wm_data.gd161::text AS COUNTRY_ISO3166,
                    IFF(pos.CURRENCY_CODE IS NULL,wm_data.gd171::text,pos.CURRENCY_CODE) AS CURRENCY,
                    pos.POSITION_EOD,
                    wm_data.gd090::text AS ISSUE_DATE,
                    wm_data.gd290a::text AS FIRST_COUPON,
                    wm_data.gd300::text AS LAST_COUPON,
                    wm_data.gd312::text AS COUPON_FREQ,
                    wm_data.gd455a::text AS MIN_INCREMENT,
                    wm_data.gd801a::text AS COUPON,
                    wm_data.gd810::text AS DAY_COUNT,
                    wm_data.gd910::text AS MATURITY,
                    IFF(pos.INSTRUMENT_TYPE='BOND',DIV0(pos.EOD_PRICE,100),pos.EOD_PRICE) as EOD_PRICE,
                    SUM(IFF(pos.INSTRUMENT_TYPE='BOND',DIV0(pos.RISK_EXPOSURE_IN_EUR,100),pos.RISK_EXPOSURE_IN_EUR)) as RISK_EXPOSURE_IN_EUR,
                    SUM(pos.BUY_VOLUME) AS BUY_VOLUME,
                    SUM(pos.SELL_VOLUME) AS SELL_VOLUME,
                    SUM(pos.REALIZED_PNL_SUM) AS SUM_PNL_REALIZED,
                    SUM(pos.UNREALIZED_PNL_SUM) AS SUM_PNL_UNREALIZED,
                    SUM(pos.SUM_COSTS) as SUM_COSTS
                FROM
                    teams_prd.investing_publish.pbl__curr__ft_regulatory_reporting as pos
                    INNER JOIN 
                        teams_prd.source_instrument_partners.src__instrument_partners__wmdaten_instruments_view AS wm_data 
                    ON 
                        wm_data."isin" = pos.instrument_id
                WHERE
                    CALENDAR_DATE = (SELECT 
                                        MAX(CALENDAR_DATE) 
                                     FROM 
                                         teams_prd.investing_publish.pbl__curr__ft_regulatory_reporting
                                    WHERE
                                         DAYOFWEEK(CALENDAR_DATE) NOT IN (0,6)) -- Exclude Saturdays (6) and Sundays (0)
                GROUP BY 
                    CALENDAR_DATE,
                    INSTRUMENT_ID,
                    NAME_OFFICIAL,
                    INSTRUMENT_TYPE,
                    ISSUER,
                    COUNTRY_ISO3166,
                    CURRENCY,
                    POSITION_EOD,
                    EOD_PRICE,
                    ISSUE_DATE,
                    FIRST_COUPON,
                    LAST_COUPON,
                    COUPON_FREQ,
                    MIN_INCREMENT,
                    COUPON,
                    DAY_COUNT,
                    MATURITY
                ORDER BY
                    1 DESC;
                    '''


        else:
            if 'startdate' in kwargs.keys():
                startdate = kwargs['startdate']
                enddate = kwargs['enddate']

                qry_live = '''
                            SELECT
                                pos.CALENDAR_DATE, 
                                pos.INSTRUMENT_ID,
                                pos.NAME_OFFICIAL,
                                pos.INSTRUMENT_TYPE,
                                pos.ISSUER, 
                                pos.POSITION_EOD,
                                IFF(pos.INSTRUMENT_TYPE='BOND',DIV0(pos.EOD_PRICE,100),pos.EOD_PRICE) as EOD_PRICE,
                                SUM(IFF(pos.INSTRUMENT_TYPE='BOND',DIV0(pos.RISK_EXPOSURE_IN_EUR,100),pos.RISK_EXPOSURE_IN_EUR)) as RISK_EXPOSURE_IN_EUR,
                                SUM(pos.BUY_VOLUME) AS BUY_VOLUME,
                                SUM(pos.SELL_VOLUME) AS SELL_VOLUME,
                                SUM(pos.REALIZED_PNL_SUM) AS SUM_PNL_REALIZED,
                                SUM(pos.UNREALIZED_PNL_SUM) AS SUM_PNL_UNREALIZED,
                                SUM(pos.SUM_COSTS) as SUM_COSTS
                            FROM
                                teams_prd.investing_publish.pbl__curr__ft_regulatory_reporting as pos
                            WHERE
                                CALENDAR_DATE BETWEEN %s AND %s
                            GROUP BY 
                                CALENDAR_DATE,INSTRUMENT_ID,NAME_OFFICIAL,INSTRUMENT_TYPE,ISSUER,POSITION_EOD,EOD_PRICE
                            ORDER BY
                                1 DESC
                           '''

                qry_live = qry_live % (db.sqldate(startdate), db.sqldate(enddate))

            else:
                qry_live = '''
                            SELECT
                                pos.CALENDAR_DATE, 
                                pos.INSTRUMENT_ID,
                                pos.NAME_OFFICIAL,
                                pos.INSTRUMENT_TYPE,
                                pos.ISSUER, 
                                pos.POSITION_EOD,
                                IFF(pos.INSTRUMENT_TYPE='BOND',DIV0(pos.EOD_PRICE,100),pos.EOD_PRICE) as EOD_PRICE,
                                SUM(IFF(pos.INSTRUMENT_TYPE='BOND',DIV0(pos.RISK_EXPOSURE_IN_EUR,100),pos.RISK_EXPOSURE_IN_EUR)) as RISK_EXPOSURE_IN_EUR,
                                SUM(pos.BUY_VOLUME) AS BUY_VOLUME,
                                SUM(pos.SELL_VOLUME) AS SELL_VOLUME,
                                SUM(pos.REALIZED_PNL_SUM) AS SUM_PNL_REALIZED,
                                SUM(pos.UNREALIZED_PNL_SUM) AS SUM_PNL_UNREALIZED,
                                SUM(pos.SUM_COSTS) as SUM_COSTS
                            FROM
                                teams_prd.investing_publish.pbl__curr__ft_regulatory_reporting as pos
                            GROUP BY 
                                CALENDAR_DATE,INSTRUMENT_ID,NAME_OFFICIAL,INSTRUMENT_TYPE,ISSUER,POSITION_EOD,EOD_PRICE
                            ORDER BY
                                1 DESC
                           '''


        df_inv = db.run_query(query=qry_live)
        # Filter Out Weekends:
        df_inv = df_inv[~pd.to_datetime(df_inv.calendar_date).dt.weekday.isin([5, 6])]
        # Create Weight column:
        df_inv['risk_exposure_in_eur_total'] = df_inv.groupby('calendar_date').sum(numeric_only=True)[['risk_exposure_in_eur']].reindex(
            df_inv.calendar_date).values
        df_inv['weight'] = df_inv.risk_exposure_in_eur / df_inv.risk_exposure_in_eur_total
        df_inv = df_inv.set_index('instrument_id')
        df_inv = df_inv.rename(columns={'calendar_date': 'ddate'})

    elif 'new_pf_engine' in kwargs.keys():

        from risk_pylibrary.projects.trading_book import portfolio as pf

        if verbose:
            print('\t Fetching Positions with New Portfolio Engine for %s' %value_date)

        acct = kwargs['account']
        # if acct == 'caligula':
        #     df_inv = pf.build_book(acct, startdate=value_date, enddate=value_date, query_eis=True)
        # else:
        df_inv = pf.build_book(acct, startdate=value_date, enddate=value_date)
    else:
        # Get Caracalla Inventory
        df_inv = c_univ.get_caracalla_universe()
        df_inv = df_inv.set_index('instrument_id')


    if rf_mapping_new:
        from risk_pylibrary.projects.risk_factor_mapping import rf_wrapper as rw
        if 'startdate' in kwargs.keys():
            df_map = rw.rf_mapping_engine(enddate, enddate)
        elif 'value_date' in kwargs.keys():
            df_map = rw.rf_mapping_engine(value_date, value_date)

        df_map = df_map.set_index('instrument_id')
        df_port = df_inv.join(df_map[[k for k in df_map.columns if k not in df_inv.columns]])
        #df_port = df_map.join(df_inv[[k for k in df_inv.columns if k not in df_map.columns]])

    else:
        # Get Security Mappings:
        df_secs = db.run_query('SELECT * FROM TEAMS_PRD.RISK_DATA.SECURITY_DESCRIPTION')
        df_secs = df_secs.set_index('instrument_id')
        df_secs = df_secs[~df_secs.index.duplicated(keep='first')]

        # Join DataFrames:
        df_port = df_inv.join(df_secs[['country', 'currency', 'sector', 'industry', 'risk_factor']])


    # String Formatting:
    df_port = df_port.sort_values(by='ddate')
    df_port = df_port.dropna(subset=['weight'])
    df_port = df_port.reset_index().set_index(['ddate', 'instrument_id'])
    df_port['instrument_type'][df_port.instrument_type.isnull()] = 'STOCK'
    df_port['instrument_type'] = df_port.instrument_type.apply(lambda x: x[:1] + x[1:].lower())


    if force_rf:
        # Force Bonds to global_agg_bond
        df_port.loc[df_port.instrument_type == 'Bond', 'risk_factor'] = 'global_agg_bond'
        # Force Unmapped Risk Factor to Msci World
        df_port.loc[df_port.risk_factor.isnull(), 'risk_factor'] = 'msci_world'
        df_port.loc[df_port.currency.isnull(), 'currency'] = 'EUR'

    out_dict['inventory'] = df_port

    if calc_pnl_report:
        out_dict_pnl = get_pnl_report(df_port, value_date, 0)
        out_dict = {**out_dict, **out_dict_pnl}


    if calc_rf_port:
        # Fetch Risk Factor Exposures
        rf_dict = get_caracalla_rf_portfolio(df_port.loc[[value_date]], value_date)
        out_dict = {**out_dict, **rf_dict}

        if calc_risk:
            df_risk = pd.DataFrame()
            for k in kwargs['risk_engines']:
                fmt_engine_tmp = kwargs['risk_engines'][k]
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

    return out_dict


def get_caracalla_rf_portfolio(df_port, value_date, calc_rets=True):
    """
    Fetches based on DWH portfolio the Risk Factor Exposures
    """

    out_dict = dict()

    df = df_port.copy()
    # Fetch Return Data: ##############################################################################################
    rf_map = db.run_query('SELECT * from TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING')
    rf_map = rf_map.set_index('code')

    # Build Risk Factor Portfolio
    rf_columns = ['risk_factor', 'weight']
    # Set Support Risk Factor Columns to '' in order to not lose info while grouping
    rf_support_cols = ['oas_series']
    for col in rf_support_cols:
        try:
            df.loc[(df[col].isnull()), col] = ''
        except:
            pass

    # Build Bond Risk Factors
    # Concat Risk Factor and Oas Series for later Return Calculation
    rf_bond_wgts = df[df.instrument_type == 'Bond'][rf_columns + rf_support_cols].groupby(rf_columns[:1] + rf_support_cols).sum()
    rf_bond_analytics = df[df.instrument_type == 'Bond'][rf_columns[:1] + rf_support_cols + ['dur_mod', 'convexity']].groupby(rf_columns[:1] + rf_support_cols).mean()
    rf_bond = pd.concat([rf_bond_wgts, rf_bond_analytics], axis=1)

    rf_port = df[df.instrument_type != 'Bond'][rf_columns + rf_support_cols].groupby(rf_columns[:1] + rf_support_cols).sum()[['weight']]
    rf_port = pd.concat([rf_bond, rf_port], axis=0)
    rf_port['currency'] = rf_port.index.get_level_values(0)
    rf_port['currency'] = rf_port.currency.map(dict(zip(rf_map.index, rf_map.currency)))
    rf_port['currency'] = rf_port['currency'].fillna('EUR')
    rf_port['currency_rf'] = rf_port['currency'].apply(lambda x: 'fx_eur%s' % x.lower())

    # Group and Filter
    rf_port_fx = rf_port.reset_index()[['currency_rf', 'weight']].groupby(['currency_rf']).sum()
    rf_port_fx = rf_port_fx[rf_port_fx.index.get_level_values(0) != 'fx_eureur'].reset_index()
    #Build Index with Risk Factor Support columns
    for col in rf_support_cols:
        rf_port_fx[col] = ''

    rf_port_fx = rf_port_fx.rename(columns={'currency_rf': 'risk_factor'})
    rf_port_fx = rf_port_fx.groupby(rf_columns[:1] + rf_support_cols).sum()
    rf_port = pd.concat([rf_port, rf_port_fx], axis=0).drop(['currency', 'currency_rf'], axis=1).sort_index()

    out_dict['rf_portfolio'] = rf_port

    # Get Returns. Loc with Value Date
    if calc_rets:
        rets = dtp.get_rf_returns(rf_port=rf_port, yield2tr=True)
        rets = rets[date(2008, 1, 1):value_date].fillna(0)
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


def get_pnl_report(df_port, value_date, historical):
    """
    Builds a PnL Report for Caracalla Portfolio OutPut and adds also percentage returns
    """

    # Set Variables
    acct = df_port.account.iloc[0]
    value_date_dt = _datetime(value_date.year, value_date.month, value_date.day, 23, 59, 59)


    out_dict_pnl = dict()

    if historical:
        # Get PnL
        qry_pnl = '''
        SELECT 
            * 
        FROM
            TEAMS_PRD.RISK_DATA.MR_PORT_PNL
        WHERE
            REPORT_DATE <= %s
        AND
            ACCOUNT = '%s'
        '''

        qry_pnl = qry_pnl % (db.sqldate(value_date_dt), acct)

        # Get Positions
        qry_pos = '''
        SELECT 
            *
        FROM
            TEAMS_PRD.RISK_DATA.MR_PORT_POS AS POS
        WHERE
            REPORT_DATE <= %s
        AND
            ACCOUNT = '%s'
        '''
        qry_pos = qry_pos % (db.sqldate(value_date_dt), acct)


    else:
        # Get PnL
        qry_pnl = '''
        SELECT 
            * 
        FROM
            TEAMS_PRD.RISK_DATA.MR_PORT_PNL
        WHERE
            REPORT_DATE BETWEEN (SELECT MAX(REPORT_DATE) FROM TEAMS_PRD.RISK_DATA.MR_PORT_POS WHERE REPORT_DATE < %s) AND %s
        AND
            ACCOUNT = '%s'
        '''

        qry_pnl = qry_pnl % (db.sqldate(value_date_dt), db.sqldate(value_date_dt), acct)

        # Get Positions
        qry_pos = '''
        SELECT 
            * 
        FROM
            TEAMS_PRD.RISK_DATA.MR_PORT_POS
        WHERE
            REPORT_DATE BETWEEN (SELECT MAX(REPORT_DATE) FROM TEAMS_PRD.RISK_DATA.MR_PORT_POS WHERE REPORT_DATE < %s) AND %s
        AND
            ACCOUNT = '%s'
        '''

        qry_pos = qry_pos % (db.sqldate(value_date_dt), db.sqldate(value_date_dt), acct)

    # PnL: SQL to Py
    df_pnl = db.run_query(query=qry_pnl)
    df_pnl = df_pnl.sort_values(by='report_date')
    df_pnl = df_pnl.drop_duplicates(subset=['report_date', 'account', 'instrument_id'])

    # PoS: SQL to Py

    df_pos = db.run_query(query=qry_pos)
    df_pos = df_pos.sort_values(by='report_date')
    df_pos['risk_exposure_in_eur_total'] = df_pos.price * df_pos.quantity
    df_pos_tot = df_pos[['report_date', 'risk_exposure_in_eur_total']].groupby('report_date').sum()

    # Set Date List for Iteration
    ddate_ll = list(df_pos_tot.index)

    # Create Portfolio Historical Performance
    df_port_pnl = df_pos_tot.reset_index()[['report_date', 'risk_exposure_in_eur_total']].drop_duplicates(subset=['report_date'])
    df_port_pnl.columns = ['ddate', 'risk_exposure_in_eur_total']
    df_port_pnl = df_port_pnl.set_index('ddate')
    # Iterate through PnLs
    for sdate, edate in dict(zip(ddate_ll[:-1], ddate_ll[1:])).items():

        # Set Support DataFrame
        tmp_pnl_edate = df_pnl[df_pnl.report_date == edate].set_index('instrument_id')
        tmp_pnl_edate = tmp_pnl_edate.rename(columns=lambda x: x + '_edate')
        tmp_pnl_sdate = df_pnl[df_pnl.report_date == sdate].set_index('instrument_id')
        tmp_pnl_sdate = tmp_pnl_sdate.rename(columns=lambda x: x + '_sdate')

        # Merge
        tmp_pnl = tmp_pnl_edate.join(tmp_pnl_sdate, how='outer')

        tmp_pnl['pnl_clean'] = tmp_pnl['upnl_edate'] - tmp_pnl['upnl_sdate']
        tmp_pnl['pnl_dirty'] = tmp_pnl['pnl_clean'] + tmp_pnl['rpnl_edate']

        # Add PnL Totals
        df_port_pnl.loc[edate, 'pnl_clean'] = tmp_pnl['pnl_clean'].sum()
        df_port_pnl.loc[edate, 'pnl_dirty'] = tmp_pnl['pnl_dirty'].sum()
        
        # Adding Percentage Returns
        df_port_pnl.loc[edate, 'total_return_clean'] = df_port_pnl.loc[edate, 'pnl_clean'] / df_port_pnl.loc[sdate, 'risk_exposure_in_eur_total']
        df_port_pnl.loc[edate, 'total_return_dirty'] = df_port_pnl.loc[edate, 'pnl_dirty'] / df_port_pnl.loc[sdate, 'risk_exposure_in_eur_total']

    # Format
    df_port_pnl = df_port_pnl.rename(index=lambda x: x.date())

    out_dict_pnl['pnl_tot'] = df_port_pnl if historical else df_port_pnl.loc[[value_date]]

    return out_dict_pnl


def get_limit_report(out_dict, account=None, value_dates=None, keep_lim_val=False, apply_ret_limits=True, verbose=True):
    """
    Limits Report for Caracalla Trading Book
    """
    # ToDo: Adjust outputs and queries for single point in time

    def_limits = db.run_query(query="SELECT * from TEAMS_PRD.RISK_DATA_SENSITIVE.RISK_METRICS_LIMITS_DEFINITION WHERE account='%s'"%account)
    def_limits = def_limits[def_limits.account == account]

    # Assign df_port and pnl
    df_port = out_dict['inventory']
    df_pnl = out_dict['pnl_tot']

    # Get Exceptions for Specific ISINs
    df_port_ex = build_limit_exceptions(df_port=df_port)
    df_exceptions = df_port_ex[df_port_ex.max_pos == 1]

    # Get VaR Report
    bmk = 'bmk_caracalla'
    df_VaR = db.run_query(query="SELECT * "
                                "FROM TEAMS_PRD.RISK_DATA.RISK_METRICS_DAILY "
                                "WHERE code='var990_1d_hs' AND account='%s'"%account)

    # Get Cap Req Report
    df_cap_req = db.run_query(query="SELECT * "
                                    "FROM TEAMS_PRD.RISK_DATA.RISK_METRICS_DAILY "
                                    "WHERE code='cap_req_var_hs_h30' AND account='%s'"%account)

    df_chk_var = pd.pivot_table(df_VaR[['ddate', 'account', 'value']], columns='account', index='ddate')
    df_chk_var.columns = df_chk_var.columns.droplevel()
    df_chk_var = df_chk_var.fillna(method='ffill')
    df_chk_var = df_chk_var.fillna(method='bfill')

    out = pd.DataFrame()
    # Iterate through value date list
    for value_dd in value_dates:
        # Slice by Max ddate:
        def_limits_tmp = def_limits[def_limits.ddate <= value_dd]
        def_limits_tmp = def_limits_tmp.drop_duplicates(subset='code', keep='last')
        def_limits_tmp['ddate'] = value_dd
        df_port_tmp = df_port[df_port.index.get_level_values(0) == value_dd]
        df_port_ex_tmp = df_port_ex[df_port_ex.index.get_level_values(0) == value_dd]
        df_exceptions_tmp = df_exceptions[df_exceptions.index.get_level_values(0) == value_dd]

        if verbose and df_exceptions_tmp[['position_eod', 'max_pos']].empty is False:
            print("Using the following exceptions: \n%s"%df_exceptions_tmp[['position_eod', 'max_pos']])

        # Optional: Exclude Performance Limits
        if apply_ret_limits is False:
            def_limits_tmp = def_limits_tmp[~(def_limits.code.str.startswith('daily_loss'))
                                    & ~(def_limits_tmp.code.str.startswith('drawdown_loss'))]

        # Creating output
        def_limits_tmp = pd.pivot_table(def_limits_tmp, values=['value'], index=['ddate'], columns=['code'])
        def_limits_tmp.columns = def_limits_tmp.columns.droplevel()
        def_limits_tmp = def_limits_tmp[def_limits_tmp.index <= value_dd][-1:]
        def_limits_tmp = def_limits_tmp.dropna(axis=1)

        # Assign df_pnl
        if 'pnl_tot' in out_dict.keys():
            df_pnl_tmp = df_pnl.loc[[value_dd]]

        out_lim_chk = pd.DataFrame(index=[value_dd])

        for col in [k for k in def_limits_tmp.columns if k[-3:] != 'tol']:

            df_chk_lim = pd.DataFrame()
            try:
                if 'pnl_tot' in out_dict.keys():
                    if col == 'book_size' or col == 'daily_loss' or col == 'rbc_size':
                        value_col = 'risk_exposure_in_eur_total' if col in ['book_size', 'rbc_size'] else 'total_return_dirty'
                        df_chk_lim = df_pnl_tmp[[value_col]]
                        df_chk_lim = df_chk_lim.reset_index()[['ddate', value_col]].drop_duplicates(subset='ddate')
                        df_chk_lim = df_chk_lim.set_index('ddate')

                        if value_col == 'risk_exposure_in_eur_total' and col == 'book_size':
                            # Book Size Limit is given as positive value
                            df_chk_lim['book_size_lim_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x < def_limits_tmp[col].iloc[0] else 0)
                            df_chk_lim['book_size_tol_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x < def_limits_tmp[col + '_tol'].iloc[0] else 0)


                        elif value_col == 'risk_exposure_in_eur_total' and col == 'rbc_size':
                            # Book Size Limit is given as positive value
                            df_chk_lim['rbc_size_lim_chk'] = df_chk_lim[value_col].apply(
                                lambda x: 1 if x < def_limits_tmp[col].iloc[0] else 0)
                            df_chk_lim['rbc_size_tol_chk'] = df_chk_lim[value_col].apply(
                                lambda x: 1 if x < def_limits_tmp[col + '_tol'].iloc[0] else 0)

                        elif value_col == 'total_return_dirty':
                            # Daily Loss Limit is given as negative value
                            df_chk_lim['daily_loss_lim_chk'] = df_chk_lim[value_col].apply(
                                lambda x: 1 if x > def_limits_tmp[col].iloc[0] else 0)
                            df_chk_lim['daily_loss_tol_chk'] = df_chk_lim[value_col].apply(
                                lambda x: 1 if x > def_limits_tmp[col + '_tol'].iloc[0] else 0)

                    elif col == 'drawdown_loss':
                        value_col = 'total_return_dirty'
                        ts_pnl = df_pnl[['total_return_dirty']].rets2lvl()
                        df_chk_lim = ts_pnl / ts_pnl.cummax() - 1
                        df_chk_lim = df_chk_lim.loc[[value_dd]]
                        df_chk_lim['drawdown_loss_lim_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x > def_limits_tmp[col].iloc[0] else 0)
                        df_chk_lim['drawdown_loss_tol_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x > def_limits_tmp[col + '_tol'].iloc[0] else 0)

                if col == 'max_pos':
                    value_col = 'position_eod'
                    # Exclude Exceptions ISINs:
                    df_port_filtered = df_port_ex_tmp.copy()
                    df_port_filtered = df_port_filtered[df_port_filtered.max_pos != 1]
                    df_port_filtered = df_port_filtered[df_port_filtered.issuer != 'SOC_GEN']
                    df_chk_lim = df_port_filtered.reset_index()[['ddate', value_col]].groupby('ddate').max()
                    df_chk_lim['max_pos_lim_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x < def_limits_tmp[col].iloc[0] else 0)
                    df_chk_lim['max_pos_tol_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x < def_limits_tmp[col].iloc[0] else 0)

                elif col == 'rel_var_bmk':
                    df_chk_lim = df_chk_var.loc[[value_dd]]
                    value_col = 'var_pf_bmk_ratio'
                    df_chk_lim[value_col] = df_chk_lim[account] / df_chk_lim[bmk]
                    df_chk_lim = df_chk_lim[[value_col]]
                    df_chk_lim['var_ratio_lim_chk'] = df_chk_lim[value_col].apply(
                        lambda x: 1 if x < def_limits_tmp[col].iloc[0] else 0)
                    df_chk_lim['var_ratio_tol_chk'] = df_chk_lim[value_col].apply(
                        lambda x: 1 if x < def_limits_tmp[col + '_tol'].iloc[0] else 0)

                elif col == 'cap_req':
                    df_chk_lim = pd.pivot_table(df_cap_req[['ddate', 'account', 'value']], columns='account', index='ddate')
                    df_chk_lim.columns = df_chk_lim.columns.droplevel()

                    value_col = 'cap_req_ratio'
                    df_chk_lim[value_col] = df_chk_lim[account] / df_pnl['risk_exposure_in_eur_total']
                    df_chk_lim = df_chk_lim[[value_col]]
                    df_chk_lim['cap_req_lim_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x < def_limits_tmp[col].iloc[0] else 0)
                    df_chk_lim['cap_req_tol_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x < def_limits_tmp[col + '_tol'].iloc[0] else 0)

                elif col == 'tracker_cert':
                    value_col = 'risk_exposure_in_eur'
                    # Filter for Tracker Certificates
                    df_port_filtered = df_port_tmp[df_port_tmp.issuer == 'SOC_GEN']
                    df_chk_lim = df_port_filtered[[value_col]].reset_index()[['ddate','risk_exposure_in_eur']].groupby('ddate').sum()
                    # Book Size Limit is given as positive value
                    df_chk_lim['tracker_cert_lim_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x < def_limits_tmp[col].iloc[0] else 0)
                    df_chk_lim['tracker_cert_tol_chk'] = df_chk_lim[value_col].apply(lambda x: 1 if x < def_limits_tmp[col + '_tol'].iloc[0] else 0)
            except:
                print('WARNING: Could not produce Limit Checks for %s on %s'%(col, value_dd))

            if df_chk_lim.empty is False:
                df_chk_lim['%s_lim' % col] = def_limits_tmp[col].iloc[0]
                df_chk_lim['%s_tol' % col] = def_limits_tmp[col + '_tol'].iloc[0]
                if keep_lim_val:
                    df_chk_lim.columns = [k.replace(value_col, '%s_lim_value' % col) for k in df_chk_lim.columns]
                    out_lim_chk = out_lim_chk.join(df_chk_lim)
                else:
                    out_lim_chk = out_lim_chk.join(df_chk_lim.iloc[:, 1:])

        out = pd.concat([out, out_lim_chk], axis=0)

    return out



def build_limit_exceptions(df_port=None, account='caracalla'):

    if df_port is None:
        df_port = get_caracalla_portfolio()['inventory']


    # Get PortFolio date range:
    df_port_idx_dates = df_port.index.get_level_values(0).unique()

    df_ex = db.run_query(query="SELECT * "
                               "FROM RISK_DATA_SENSITIVE.RISK_METRICS_LIMITS_EXCEPTIONS "
                               "WHERE ACCOUNT='%s'"%account)

    df_ex = df_ex.replace(date(2500, 12, 31), df_port.index.get_level_values(0).max(), regex=True)
    # If single day is checked
    if len(df_port_idx_dates) == 1:
        df_ex = df_ex[df_ex.ddate_end.isin(df_port_idx_dates)]

    # Serialize the Data
    df_ex_series = pd.pivot_table(df_ex,
                                  index=['ddate_start', 'ddate_end', 'isin'],
                                  columns=['limit_code'],
                                  values=['active'])

    out_data = pd.DataFrame()
    for idx, vals in enumerate(df_ex_series.values):
        tmp = df_ex_series.iloc[[idx]]
        tmp_idx = tmp.index
        # Build Series
        tmp_data = pd.DataFrame(index=[tmp_idx[0][0], tmp_idx[0][1]])
        tmp_idx_new = [k for k in df_port_idx_dates if k >= tmp_idx[0][0] and k <= tmp_idx[0][1]]
        if len(tmp_idx_new) == 1:
            if len(df_port_idx_dates) == 1:
                # If single day is checked
                tmp_data = tmp_data[1:]
            else:
                # For single Day Exceptions within the history
                tmp_data = tmp_data[:1]

        else:
            tmp_data = tmp_data.reindex(tmp_idx_new)
        tmp_data = tmp_data.reset_index()
        tmp_data.columns = ['ddate']
        tmp_data['instrument_id'] = tmp_idx[0][2]
        tmp_data[list(tmp.columns.droplevel(0))] = vals

        # Add to Output and reindex to full index:
        out_data = pd.concat([out_data, tmp_data], axis=0)

    # Reunite Data Sets
    df_port = df_port.join(out_data.groupby(['ddate', 'instrument_id']).sum())
    df_port['max_pos'] = df_port['max_pos'].fillna(0)

    # Disabling Max Pos for Bonds
    df_port['max_pos'][df_port.instrument_type == 'Bond'] = 1

    return df_port


def get_risk_model_backtest():
    db_rm = db.run_query(query="select * from TEAMS_PRD.RISk_DATA.RISK_METRICS_DAILY "
                               "where code in ('total_return', 'var990_1d_hs', 'var990_1d_gjr') "
                               "and account = 'caracalla'")
    df_rm = pd.pivot_table(db_rm[['ddate', 'code', 'value']], index='ddate', columns='code')
    df_rm.columns = df_rm.columns.droplevel()


def get_portfolio_rt(ddate, symbols=None):

    if symbols is not None:
        qry = '''
        SELECT
        convert_timezone('Europe/Berlin', timestamp)::TIMESTAMP_NTZ AS timestamp_cest,
        CAST(data['output']['instrumentId'] as string) as instrument_id,
        CAST(CAST(data['output']['executionPrice'] as string) as float) as execution_price,
        iff(data['output']['orderType'] = 'SELL' 
            AND data['output']['exchangeId'] = 'TRPT', 
                CAST(CAST(data['output']['executionSize'] as string) as float),0) as customer_trading_sell_quantity,
        iff(data['output']['orderType'] = 'BUY' 
            AND data['output']['exchangeId'] = 'TRPT', 
                CAST(CAST(data['output']['executionSize'] as string) as float)*(-1),0) as customer_trading_buy_quantity,
        iff(data['output']['orderType'] = 'SELL' 
            AND data['output']['secAccNo'] = '9800001301', 
                CAST(CAST(data['output']['executionSize'] as string) as float)*(-1),0) as nostro_depo_trading_sell_quantity,
        iff(data['output']['orderType'] = 'BUY' 
            AND data['output']['secAccNo'] = '9800001301', 
                CAST(CAST(data['output']['executionSize'] as string) as float),0) as nostro_depo_trading_buy_quantity,
        iff(data['output']['orderType'] = 'SELL' 
            AND data['output']['exchangeId'] = 'TRPT', 
                CAST(CAST(data['output']['executionPrice'] as string) as float)*CAST(CAST(data['output']['executionSize'] as string) as float),0) as customer_trading_sell_volume,
        iff(data['output']['orderType'] = 'BUY' 
            AND data['output']['exchangeId'] = 'TRPT', 
                CAST(CAST(data['output']['executionPrice'] as string) as float)*CAST(CAST(data['output']['executionSize'] as string) as float)*(-1),0) as customer_trading_buy_volume,
        iff(data['output']['orderType'] = 'SELL' 
            AND data['output']['secAccNo'] = '9800001301', 
                CAST(CAST(data['output']['executionPrice'] as string) as float)*CAST(CAST(data['output']['executionSize'] as string) as float)*(-1),0) as nostro_depo_trading_sell_volume,
        iff(data['output']['orderType'] = 'BUY' 
            AND data['output']['secAccNo'] = '9800001301', 
                CAST(CAST(data['output']['executionPrice'] as string) as float)*CAST(CAST(data['output']['executionSize'] as string) as float),0) as nostro_depo_trading_buy_volume,
        customer_trading_sell_quantity + customer_trading_buy_quantity as customer_quantity,
        nostro_depo_trading_sell_quantity + nostro_depo_trading_buy_quantity as nostro_quantity,
        customer_trading_sell_quantity+customer_trading_buy_quantity+nostro_depo_trading_sell_quantity+nostro_depo_trading_buy_quantity as quantity,
        customer_trading_sell_volume+customer_trading_buy_volume+nostro_depo_trading_sell_volume+nostro_depo_trading_buy_volume as risk_exposure_in_eur
        FROM events_prd.portfolio_manager.PORTFOLIO_MANAGER_TRACKING_EVENTS_VIEW a
        WHERE 1=1
        AND eventname = 'orderExecuted'
        AND timestamp::date >= %s
        AND (data['output']['secAccNo'] = '9800001301' OR data['output']['exchangeId'] = 'TRPT')
        AND instrument_id in (%s)
        order by 1 DESC
        '''
    else:
        qry = '''
        SELECT
        convert_timezone('Europe/Berlin', timestamp)::TIMESTAMP_NTZ AS timestamp_cest,
        CAST(data['output']['instrumentId'] as string) as instrument_id,
        CAST(CAST(data['output']['executionPrice'] as string) as float) as execution_price,
        iff(data['output']['orderType'] = 'SELL' AND data['output']['exchangeId'] = 'TRPT', CAST(CAST(data['output']['executionSize'] as string) as float),0) as customer_trading_sell_quantity,
        iff(data['output']['orderType'] = 'BUY' AND data['output']['exchangeId'] = 'TRPT', CAST(CAST(data['output']['executionSize'] as string) as float)*(-1),0) as customer_trading_buy_quantity,
        iff(data['output']['orderType'] = 'SELL' AND data['output']['secAccNo'] = '9800001301', CAST(CAST(data['output']['executionSize'] as string) as float)*(-1),0) as nostro_depo_trading_sell_quantity,
        iff(data['output']['orderType'] = 'BUY' AND data['output']['secAccNo'] = '9800001301', CAST(CAST(data['output']['executionSize'] as string) as float),0) as nostro_depo_trading_buy_quantity,
        iff(data['output']['orderType'] = 'SELL' AND data['output']['exchangeId'] = 'TRPT', CAST(CAST(data['output']['executionPrice'] as string) as float)*CAST(CAST(data['output']['executionSize'] as string) as float),0) as customer_trading_sell_volume,
        iff(data['output']['orderType'] = 'BUY' AND data['output']['exchangeId'] = 'TRPT', CAST(CAST(data['output']['executionPrice'] as string) as float)*CAST(CAST(data['output']['executionSize'] as string) as float)*(-1),0) as customer_trading_buy_volume,
        iff(data['output']['orderType'] = 'SELL' AND data['output']['secAccNo'] = '9800001301', CAST(CAST(data['output']['executionPrice'] as string) as float)*CAST(CAST(data['output']['executionSize'] as string) as float)*(-1),0) as nostro_depo_trading_sell_volume,
        iff(data['output']['orderType'] = 'BUY' AND data['output']['secAccNo'] = '9800001301', CAST(CAST(data['output']['executionPrice'] as string) as float)*CAST(CAST(data['output']['executionSize'] as string) as float),0) as nostro_depo_trading_buy_volume,
        customer_trading_sell_quantity + customer_trading_buy_quantity as customer_quantity,
        nostro_depo_trading_sell_quantity + nostro_depo_trading_buy_quantity as nostro_quantity,
        customer_trading_sell_quantity+customer_trading_buy_quantity+nostro_depo_trading_sell_quantity+nostro_depo_trading_buy_quantity as quantity,
        customer_trading_sell_volume+customer_trading_buy_volume+nostro_depo_trading_sell_volume+nostro_depo_trading_buy_volume as risk_exposure_in_eur
        FROM events_prd.portfolio_manager.PORTFOLIO_MANAGER_TRACKING_EVENTS_VIEW a
        WHERE 1=1
        AND eventname = 'orderExecuted'
        AND timestamp::date >= %s
        AND (data['output']['secAccNo'] = '9800001301' OR data['output']['exchangeId'] = 'TRPT')
        order by 1 DESC
        '''

    # Run Query:
    qry = qry % db.sqldate(ddate) if symbols is None else qry % (db.sqldate(ddate), db.joinpad(symbols))
    port_rt = db.run_query(query=qry)
    port_rt = port_rt.sort_values(by='timestamp_cest')

    # Add additional Info
    df_secs = db.run_query('SELECT * FROM TEAMS_PRD.RISK_DATA.SECURITY_DESCRIPTION')
    df_secs = df_secs.set_index('instrument_id')

    for k in ['name_short', 'country', 'currency', 'sector', 'risk_factor']:
        port_rt[k] = port_rt.instrument_id.map(dict(zip(df_secs.index, df_secs[k])))
        port_rt.loc[port_rt[k].isnull(), k] = '[Unassigned]'

    # Format output
    port_rt = port_rt.reset_index().drop('index', axis=1)
    port_rt['ddate'] = port_rt.timestamp_cest.apply(lambda x: x.date())

    # Remove Weekend Days
    port_rt['week_day'] = port_rt.ddate.apply(lambda x: x.weekday())
    port_rt = port_rt[~port_rt.week_day.isin([5, 6])]

    # Additional Analysis:
    volume_comparison = port_rt.loc[:, ['timestamp_cest', 'risk_exposure_in_eur']].join(
        port_rt.loc[:, 'customer_trading_sell_volume':'nostro_depo_trading_buy_volume'])
    volume_comparison = volume_comparison.set_index('timestamp_cest')

    return port_rt


def bt_carcalla_pnl():
    qry_pnl_eod = '''
    SELECT 
    CALENDAR_DATE, INSTRUMENT_ID,ISSUER, POSITION_EOD, 
    EOD_PRICE, RISK_EXPOSURE_IN_EUR, BUY_VOLUME, SELL_VOLUME, REALIZED_PNL_SUM, UNREALIZED_PNL_SUM, SUM_COSTS 
    FROM teams_prd.investing_publish.pbl__curr__ft_regulatory_reporting
    order by 1
    '''

    df_pnl_eod = db.run_query(query=qry_pnl_eod)

    qry_pnl_r = '''
    SELECT 
    t_real.INCOMING_EXECUTED_AT, 
    t_real.OUTGOING_EXECUTED_AT,
    t_real.OUTGOING_INSTRUMENT_ID AS INSTRUMENT_ID,
    t_real.INCOMING_PRICE, 
    t_real.INCOMING_SIZE, 
    t_real.OUTGOING_PRICE, 
    t_real.OUTGOING_SIZE, 
    t_real.PNL AS REALISED_PNL
    FROM teams_prd.investing_transform.trf__curr__ft_r_pnl_history_incremental AS t_real
    WHERE t_real.OUTGOING_INSTRUMENT_ID='US9168961038'
    '''
    df_pnl_r = db.run_query(query=qry_pnl_r)

    qry_pnl_ur = ''' 
    SELECT 
        t_ureal.INCOMING_EXECUTED_AT, 
        t_ureal.OUTGOING_EXECUTED_AT,
        t_ureal.OUTGOING_INSTRUMENT_ID AS INSTRUMENT_ID,
        t_ureal.INCOMING_PRICE, 
        t_ureal.INCOMING_SIZE, 
        t_ureal.OUTGOING_PRICE, 
        t_ureal.OUTGOING_SIZE, 
        t_ureal.PNL AS UNREALISED_PNL
    FROM teams_prd.investing_transform.trf__curr__ft_ur_pnl_history_incremental AS t_ureal
    WHERE t_ureal.OUTGOING_INSTRUMENT_ID='US9168961038'
    ORDER BY 1
    '''
    df_pnl_ur = db.run_query(query=qry_pnl_ur)

    out_pnl_hist = pd.concat([df_pnl_ur, df_pnl_r], axis=0)


def multiproc_port_rt_cumsum_data(df, n_cores=1, verbose=1):
    """
    Multiproc Tool for Cumulative Sum
    """
    # Import Modules:
    import multiprocessing
    from joblib import Parallel, delayed

    ctx = multiprocessing.get_context(method='forkserver')
    k = len(df.columns) // n_cores
    # Adding up the list
    ff = [df[list(df.columns)[j * k:(j + 1) * k]] for j in range(0, n_cores - 1)]
    if verbose: print('\t Starting MultiProc with Average Block Length: %s' % k)
    # Adding last element
    ff = ff + [df[list(df.columns)[(n_cores - 1) * k:]]]
    iter_zip = zip(ff, len(ff) * [verbose])
    tmp = Parallel(n_jobs=n_cores, verbose=True, backend=ctx)(
        delayed(_port_rt_enrich_data)(df_isins, verbose) for (df_isins, verbose) in iter_zip)

    # Reframe Multiproc Output
    out = tmp[0]
    for l in range(1, len(tmp)):
        out = pd.concat([out, tmp[l]], axis=1)

    return out


def _port_rt_enrich_data(df_isins, verbose):
    count = 0
    out_tmp = pd.DataFrame(index=df_isins.index)
    for k in df_isins.columns:
        if verbose:
            if count % 100 == 0: print("\t\t\t Screened %s columns" % count)
        out_tmp = pd.concat([out_tmp, df_isins[[k]].cumsum()], axis=1)
        count += 1

    return out_tmp


def multiproc_port_rt_pivot_data(df, n_cores=1, verbose=1):
    """
    Multiproc Tool for Enrich Data
    """
    # Import Modules:
    import multiprocessing
    from joblib import Parallel, delayed

    ctx = multiprocessing.get_context(method='forkserver')
    k = len(df) // n_cores
    # Adding up the list
    ff = [df[j * k:(j + 1) * k] for j in range(0, n_cores - 1)]
    if verbose: print('Average length')
    # Adding last element
    ff = ff + [df[(n_cores - 1) * k:]]
    iter_zip = zip(ff, len(ff) * [verbose])
    tmp = Parallel(n_jobs=n_cores, verbose=True, backend=ctx)(
        delayed(_port_rt_pivot_data)(df_tmp, verbose) for (df_tmp, verbose) in iter_zip)

    # Reframe Multiproc Output
    out = tmp[0]
    for l in range(1, len(tmp)):
        out = pd.concat([out, tmp[l]], axis=0)

    return out


def _port_rt_pivot_data(df_tmp, verbose):
    if verbose: print('Hello')
    out_tmp = pd.pivot_table(df_tmp, columns='instrument_id', index='timestamp_cest', values='quantity').fillna(0)

    return out_tmp


def fetch_cumulative_pos(cached_pos, use_multi_proc=False, verbose=True):
    out_tmp = cached_pos.copy()
    # Fetch newest IntraDay Data
    port_rt = get_portfolio_rt(out_tmp.index[-1].date())
    # Filter for New entries in respect to cached_pos
    if verbose: print("Cutting New Entries at %s" % out_tmp.index[-1])
    port_rt = port_rt[port_rt.timestamp_cest > out_tmp.index[-1]]
    if use_multi_proc:
        df_pivot = multiproc_port_rt_pivot_data(port_rt, n_cores=4)
    else:
        df_pivot = pd.pivot_table(port_rt[['timestamp_cest', 'instrument_id', 'quantity']],
                                  columns='instrument_id',
                                  index='timestamp_cest',
                                  values='quantity')

    df_pivot = pd.concat([out_tmp.iloc[[-1]], df_pivot], axis=0)
    # Extract column list for alter sorting
    ll_cols = df_pivot.T.sort_index().index
    # Derive cumulative sum
    df_pivot = df_pivot.fillna(0).cumsum()

    # Combine all DataFrames:
    out = pd.concat([out_tmp[:-1], df_pivot], axis=0)
    out = out.fillna(0)
    out = out[ll_cols]

    return out


def report_rt_cumsum_data(df_orig, df_cache=None, value_column='quantity',
                          multi_proc_fmt={'active': 0, 'n_cores': 6}, verbose=1):
    """
    Multiproc Tool for Cumulative Sum of Trading Book Data. E.g. quantity or risk_exposure
    @param df_orig: DataFrame with columns ['instrument_id', value_column], e.g. value_column = 'quantity'
    @param df_cache: optional. pivot input of df_orig like cached data a previous observation
    @param value_column: string. E.g. 'quantity'
    @param multi_proc_fmt: dictionary. keys: 'active', 'n_cores': active = 1 initiates multiproc

    Example for df_orig: https://app.snowflake.com/eu-central-1/gm68377/w2GTf6zxp9hl#query

    """

    # Create Output
    out = pd.DataFrame()
    if df_cache is None: df_cache = pd.DataFrame()

    df = df_orig.copy()
    df['ddate'] = df.index
    df['ddate'] = df.ddate.apply(lambda x: x.date())
    # Get unique ddate list:
    dd_list = df.ddate.unique()
    for dd in dd_list:
        if verbose: print('Running Data for : %s' % dd)
        # Slicing dd with helper column ddate
        df_tmp = df[df.ddate == dd].drop('ddate', axis=1)
        if verbose: print('\t Length of the Data: %s' % len(df_tmp))
        # Handling Input DataFrame with double rest_index() in order to avoid duplicate index dropping by pandas.pivot_table
        # Create Pivot Table of the Data:
        df_tmp_pivot = pd.pivot_table(df_tmp.reset_index().reset_index(),
                                      columns='instrument_id',
                                      index='index',
                                      values=value_column,
                                      fill_value=0)
        if verbose: print('\t Number of Columns: %s' % len(df_tmp_pivot.columns))
        # Recombine information
        df_tmp_pivot['timestamp_cest'] = df_tmp.index
        df_tmp_pivot.set_index('timestamp_cest', inplace=True)

        if len(df_cache) > 0:
            # Concatenate df_cache last row with new DataFrame
            df_tmp_pivot = pd.concat([df_cache.iloc[[-1]], df_tmp_pivot], axis=0)
            # Fill NaNs otherwise cumulative sum will not work
            df_tmp_pivot = df_tmp_pivot.fillna(0)

        # Run cumulative sum directly, if DataFrame is smaller than 600 rows
        if multi_proc_fmt['active'] == 0:
            if verbose: print('\t Initiating Direct Cumulative Sum')
            df_tmp_cumsum = df_tmp_pivot.cumsum()
        # If not, initiate multiproc over row blocks
        elif multi_proc_fmt['active'] == 1:
            if verbose: print('\t Initiating MultiProc')
            df_tmp_cumsum = multiproc_port_rt_cumsum_data(df_tmp_pivot, n_cores=multi_proc_fmt['n_cores'])

        if len(df_cache) > 0:
            # Exclude first row as it's the cached observation
            df_tmp_cumsum = df_tmp_cumsum[1:]

        # Assign df_cache as a callable
        df_cache = df_tmp_cumsum.iloc[[-1]]
        # Append temporary output
        out = pd.concat([out, df_tmp_cumsum], axis=0)
        out = out.reindex(sorted(df_tmp_cumsum.columns), axis=1)

    return out


def _port_rt_cumsum_data(df_tmp):
    """
    MultiProc Support function for cumulative sums
    """
    out_tmp = df_tmp.fillna(0).cumsum()

    return out_tmp


def fluctuation_analysis(symbol='US88160R1014', port_rt=None, plot=True):
    cols = ['customer_trading_sell_quantity', 'customer_trading_buy_quantity',
            'nostro_depo_trading_sell_quantity', 'nostro_depo_trading_buy_quantity', 'quantity']

    out = pd.DataFrame()
    for k in cols:
        df_tmp = port_rt[port_rt.instrument_id == symbol][['timestamp_cest', 'instrument_id', k]]
        df_tmp = df_tmp.set_index('timestamp_cest')
        out_tmp = multiproc_port_rt_cumsum_data(df_tmp[[k]], n_cores=4, verbose=False)
        out_tmp.columns = [k + '_cumulative']
        out = pd.concat([out, df_tmp, out_tmp], axis=1)

    # Add Support Columns:
    out['index_hour'] = out.rename(index=lambda x: x.hour).index
    out['index_minute'] = out.rename(index=lambda x: x.minute).index

    # Market Close Analysis
    mkt_close_df = out[(out.index_hour >= 19) & (out.index_minute >= 00)][['quantity_cumulative']]
    mkt_close_df.columns = ['Quantity Held within 19:00h - 23:00h CEST']
    # Market Opening Analysis
    mkt_open_df_nostro = out[(out.index_hour <= 8) & (out.index_minute >= 00)][['nostro_depo_trading_buy_quantity']]
    mkt_open_df_nostro.columns = ['Nostro Depot Buys within 07:30h - 08:00h CEST']

    # Combine DataFrames:
    out_close_open = pd.concat([mkt_close_df, mkt_open_df_nostro], axis=0).sort_index()

    if plot:
        ll_close_vlines = list(set([_datetime(k.year, k.month, k.day, 23, 0, 0) for k in mkt_close_df.index]))
        vlines_df_mkt_close = pd.DataFrame(index=ll_close_vlines, columns=['vlines'])
        vlines_df_mkt_close['vlines'] = 1
        out_plot = pd.concat([out_close_open, vlines_df_mkt_close], axis=0).sort_index()
        chart_ft_trading(out_plot.rename(index=lambda x: str(x)[:19]), plot_style='step', vlines=True)

    return out


def chart_ft_trading(df, plot_style='line', vlines=False, tlt=None, y_lbl=None, c_map=cm.Greens):
    """
    Function for TimeSeries Plot with Trades Bar Subplot.
    df: TimeSeries DataFrame
    Indices must be identical
    """
    from risk_pylibrary.tools import charting as CH
    from matplotlib import cm

    if 'vlines' in df.columns:
        df_plot = df.copy().drop('vlines', axis=1)
    else:
        df_plot = df.copy()
    df_plot.index.name = None

    fig = figure(figsize=(12, 8))
    sns.set_style("white")

    # Create Plot Canvas
    gs = gridspec.GridSpec(1, 1, wspace=0, hspace=0.025, bottom=0.12, left=0.08, right=0.90, top=0.89)
    ax0 = subplot(gs[0])
    if plot_style == 'line':
        colors = c_map(np.linspace(0, 1, len(df_plot.columns)))
        df_plot.plot(ax=ax0, lw=2, color=colors, legend=legend)
        # df_plot[[k for k in df_plot.columns if k != 'US91851C2017']].plot(ax = ax0, lw = 2, color = colors, legend = legend)
        # df_plot[[k for k in df_plot.columns if k == 'IE00BDDRF478']].plot(ax = ax0, lw = 2, color = '#AC44BF', legend = legend)
    elif plot_style == 'step':
        # colors = cm.Greens(np.linspace(0, 1, len(df_plot.columns)))
        # for k in range(0, len(df_plot.columns)):
        #     ax0.step(df_plot.index, df_plot.iloc[:, [k]].values, label = df_plot.columns[k], color = colors[k])
        df_plot_nz = df_plot[[k for k in df_plot.columns if k != 'US91851C2017']]
        colors = cm.Greens(np.linspace(0, 1, len(df_plot_nz.columns)))
        for k in range(0, len(df_plot_nz.columns)):
            ax0.step(df_plot_nz.index, df_plot_nz.iloc[:, [k]].values, label=df_plot_nz.columns[k], color=colors[k])
        # df_plot_z=df_plot[[k for k in df_plot.columns if k == 'US91851C2017']]
        # for k in range(0, len(df_plot_z.columns)):
        #     ax0.step(df_plot_z.index, df_plot_z.iloc[:, [k]].values, label = df_plot_z.columns[k], color = 'red')

    ax0.legend(loc=2, ncol=1 if len(df_plot.columns) <= 20 else 2, bbox_to_anchor=[1.05, 1])
    leg = ax0.get_legend()
    leg.get_frame().set_alpha(1)
    ax0.margins(0)

    ax0.set_xlabel(df_plot.index.name)
    setp(ax0.xaxis.get_majorticklabels(), rotation=30)
    ax0.set_xlabel('Timestamp', fontsize=14)
    ax0.set_ylabel(y_lbl, fontsize=14)
    min_y = df_plot.min().min()
    max_y = df_plot.max().max()
    ax0.set_ylim(min_y * 1.1, max_y * 1.1)

    # Draw vertical lines:
    if vlines:
        xticks(list(df[['vlines']].dropna().index))
        for fdate in df[['vlines']].dropna().index:
            ax0.axvline(fdate, color='#8FA6A5', linewidth=1, linestyle='--')

    # Draw horizontal line at zero:
    ax0.axhline(6, color='red', linewidth=1, linestyle='-')
    ax0.axhline(0, color='red', linewidth=1, linestyle='-')

    if tlt:
        title(tlt, fontdict={'fontsize': 12})

    return fig


def fetch_rt_portfolio(ddate=None, eod_ddate=None, verbose=True):
    """
    Fetches New Positioning Data from EVENTS_PRD combining them with stored sharebookings positions
    """

    if ddate is None:
        ddate = db.run_query(query="SELECT "
                                   "MAX(calendar_date) "
                                   "FROM TEAMS_PRD.INVESTING_PUBLISH.pbl__curr__ft_regulatory_reporting").iloc[0][0]

    if verbose: print("**** Current Max Date of Database Positions is: %s" % ddate)


    # Fetch RT Trades
    port_rt = get_portfolio_rt(ddate)
    if eod_ddate:
        port_rt = port_rt[(port_rt['ddate'] > ddate) & (port_rt['ddate'] <= eod_ddate)]
    else:
        port_rt = port_rt[port_rt['ddate'] > ddate]
    port_rt_max_timestamp = port_rt.timestamp_cest.iloc[-1]

    df_cache = get_caracalla_portfolio()['inventory'].loc[[ddate]]
    df_cache = df_cache.reset_index().drop('ddate', axis=1)
    df_cache = df_cache.rename(columns = {'risk_exposure_in_eur':'risk_exposure_in_eur_eod',
                                          'risk_exposure_in_eur_total':'risk_exposure_in_eur_total_eod'})

    out = df_cache.join(port_rt.groupby(['instrument_id']).sum(numeric_only=True), on='instrument_id')
    out['timestamp_cest'] = port_rt_max_timestamp

    # Format Columns
    # Fill NaN with 0 on float columns
    out[port_rt.iloc[:, 2:-7].columns] = out[port_rt.iloc[:, 2:-7].columns].fillna(0)
    # Move timestamp column
    out = pd.concat([out[['timestamp_cest']], out.iloc[:, :-1]], axis=1)

    # Create Useful columns
    out['position_rt'] = out.position_eod + out.quantity
    out['risk_exposure_in_eur_rt'] = out.risk_exposure_in_eur_eod + out.risk_exposure_in_eur

    return out


def evaluate_positions_eod():
    """
    Evaluates Positions of EVENTS_PRD Datatable that have been stroe din Risk Database

    @param: df DataFrame

    Example:
        df=db.run_query(query="SELECT * FROM TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS WHERE ACCOUNT='caracalla' and CODE='quantity'")
    """

    # Get Positions
    qry_pos = '''
    SELECT 
        TIMESTAMP_CEST::date as DDATE,
        INSTRUMENT_ID,
        VALUE as QUANTITY
    FROM 
        TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS 
    WHERE 
        ACCOUNT='caracalla' 
    AND 
        CODE='quantity'
    '''
    df_pos = db.run_query(query=qry_pos).sort_values(by='ddate')

    # Get Prices:
    # Build Query
    qry_prx = '''
    SELECT
        CALENDAR_DATE as ddate,
        INSTRUMENT_ID,
        CLOSE_MID_PRICE as PRICE
    FROM 
        TEAMS_PRD.INVESTING_MART.mrt__instrument_prices__eod_price
    WHERE
        INSTRUMENT_ID in (%s)
    AND
        CALENDAR_DATE >= %s
    ORDER BY 
        1
    '''
    ll_pos = list(df_pos.instrument_id.unique())
    start_date = db.sqldate(df_pos.ddate.iloc[0])
    df_prx = db.run_query(query=qry_prx % (db.joinpad(ll_pos), start_date))
    df_prx = df_prx.sort_values(by='ddate').groupby(['ddate', 'instrument_id']).sum()

    # Create Output:
    out = df_pos[['ddate', 'instrument_id', 'quantity']].groupby(['ddate', 'instrument_id']).sum()
    out = out.join(df_prx)

    # Calculate Risk Exposure in EUR
    out['risk_exposure_eur'] = out.quantity * out.price
    daily_notional = out.reset_index()[['ddate', 'risk_exposure_eur']].groupby('ddate').sum()
    daily_notional.columns = ['portfolio_notional_eur']
    out = out.join(daily_notional)

    # Calculate Weight
    out['weight'] = out.risk_exposure_eur / out.portfolio_notional_eur

    # Map Risk Factors
    df_secs = db.run_query('SELECT * FROM TEAMS_PRD.RISK_DATA.SECURITY_DESCRIPTION')
    df_secs = df_secs.set_index('instrument_id')
    out = out.join(df_secs[['country', 'currency', 'risk_factor']])

    return out


def hist_risk_ctr(out, rets):
    from risk_models import support_models as smo
    from scipy.stats import norm, t

    out_risk_ctr = pd.DataFrame(index=rets.columns)
    out_wgts = pd.DataFrame(index=rets.columns)
    for dd in out.index.get_level_values(0).unique():
        rf_tmp = get_caracalla_rf_portfolio(out.loc[[dd]], dd, calc_rets=False)['rf_portfolio'].loc[dd]
        rets_tmp = rets[rf_tmp.index]
        rets_cov_mtx_tmp = smo.ewma_covariance(rets_tmp[:dd][-250:], decay=0.94)
        risk_tmp = pd.DataFrame(index=rets_tmp.columns)
        risk_tmp[dd] = smo.portfolio_risk_ctr(list(rf_tmp.weight), rets_cov_mtx_tmp) * norm.ppf(0.999)
        out_risk_ctr = pd.concat([out_risk_ctr, risk_tmp], axis=1)
        out_wgts = pd.concat([out_wgts, rf_tmp.rename(columns={'weight': dd})], axis=1)

    return out_risk_ctr, out_wgts


def get_dividends():
    """
    Retrieves Cash Dividend Payment
    @return:
    """
    qry_dividends = '''
                    SELECT
                    calendar_date as ddate,
                    instrument_id,
                    amount as dividend_amount
                    FROM 
                    TEAMS_PRD.INVESTING_TRANSFORM.TRF__CURR__FT_EI_DIVIDENDS
                    '''
    df_divs = db.run_query(query=qry_dividends).set_index(['ddate', 'instrument_id'])
    df_divs = df_divs

    df_port = get_caracalla_portfolio(calc_pnl_report=False)['inventory']

    out = df_port.dropna(subset='dividend_amount')


def perf_calc(df_orig, verbose=True):

    df = df_orig.copy()
    df = df.set_index(['calendar_date','instrument_id'])
    ll_dates = list(df.sort_index().index.get_level_values(0).unique())

    out_pnl = pd.DataFrame()
    # Set Counter
    for sdate, edate in zip(ll_dates[:-1], ll_dates[1:]):
        tmp = df.loc[[sdate, edate]]
        tmp = tmp.reset_index()
        tmp_sdate = tmp[tmp.calendar_date == sdate]
        tmp_edate = tmp[tmp.calendar_date == edate]

        sdate_rnm_dict = {'eod_price': 'eod_price_sdate', 'position_eod': 'position_eod_sdate'}
        tmp_sdate_price = tmp_sdate[['instrument_id', 'position_eod', 'eod_price']].rename(columns=sdate_rnm_dict)
        sdate_rnm_dict = {'eod_price': 'eod_price_edate', 'position_eod': 'position_eod_edate', 'sum_pnl_realized': 'pnl_realised_edate'}
        tmp_edate_price = tmp_edate[['calendar_date', 'instrument_id', 'position_eod', 'eod_price','sum_pnl_realized']].rename(columns=sdate_rnm_dict)
        tmp_edate_clean = pd.merge(tmp_edate_price, tmp_sdate_price, on='instrument_id', how='outer')
        clean_pnl_cols = ['position_eod_sdate', 'eod_price_sdate','eod_price_edate']
        tmp_edate_clean['clean_pnl'] = tmp_edate_clean[clean_pnl_cols].apply(lambda row:
                                                                             row['position_eod_sdate']
                                                                             * (row['eod_price_edate']
                                                                                - row['eod_price_sdate']),axis=1)
        tmp_edate_clean['clean_pnl'] = tmp_edate_clean['clean_pnl'].fillna(0)
        tmp_edate_clean['dirty_pnl'] = tmp_edate_clean['clean_pnl'] + tmp_edate_clean['pnl_realised_edate']

        # NAV Calculation
        tmp_edate_clean['mv_edate'] = tmp_edate_clean['position_eod_edate'] * tmp_edate_clean['eod_price_edate']
        tmp_edate_clean['mv_sdate'] = tmp_edate_clean['position_eod_sdate'] * tmp_edate_clean['eod_price_sdate']

        out_pnl = pd.concat([out_pnl, tmp_edate_clean], axis=0)


    return out_pnl




