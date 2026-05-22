#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime

# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db
from risk_pylibrary.portfolio_analytics import positions as pos


def T_morning_tasks(ddate=None, starting_point = 0):
    """
    Released 1st September 2023
    Author: F.Balloni (fabio.balloni@traderepublic.com)
    Morning Tasks Schedule
    Covered Tasks:
        - Update Prices
        - Update Yields
        - Update CDS Spreads

    @return: dictionary
    """

    # Importing Modules
    from risk_pylibrary.instruments import data_prices as dtp


    # ***********************************************************************************************************
    print("********************   Initiating Morning Task Schedule ********************  ")

    if starting_point <= 10:

        print("********** Running Preliminary Positions Report **********")
        # Import Modules:
        from risk_pylibrary.projects.pnl import pnl_support as pnl_sup
        from risk_pylibrary.projects.pnl import pnl_fifo as pnl

        # Setting Start and Enddate
        date_tdy = _datetime.now().date()
        if date_tdy.weekday() == 1:
            startdate = date_tdy - timedelta(3)
            enddate = date_tdy - timedelta(1)
            cachedate = date_tdy - timedelta(4)
        elif date_tdy.weekday() == 0:
            startdate = enddate = date_tdy - timedelta(3)
            cachedate = date_tdy - timedelta(4)
        else:
            startdate = enddate = date_tdy - timedelta(1)
            cachedate = date_tdy - timedelta(2)


        # Importing Caracalla Trading Book
        print("\t 1. Caracalla Trading Book: Positions and PnL")
        df_trades = pnl_sup.get_trades_pnl(account='caracalla', syms=None, startdate=startdate, enddate=enddate)
        #df_cache =


        #out = c_port.fetch_rt_portfolio(ddate=ddate, eod_ddate=eod_date)

        # ***********************************************************************************************************

        print("********** Running Positions and PnL Reports **********")

        # Importing Caracalla Trading Book
        #print("\t 1. Caracalla Trading Book: Positions on %s"%out.timestamp_cest.iloc[0])




    # ***********************************************************************************************************

    if starting_point <= 20:
        print("********** Retrieving Returns from Web **********")

        max_entry_db_rets = db.run_query(query='SELECT MAX(ddate) '
                                               'FROM teams_prd.risk_data.returns_daily_clean').iloc[0][0]

        date_tdy = _datetime.now().date()
        if (date_tdy - timedelta(1)).weekday() == 6:
            actual_ret_date = [date_tdy - timedelta(3)]
        else:
            actual_ret_date = [date_tdy - timedelta(1)]

        if max_entry_db_rets == actual_ret_date:
            print("\n ***** New Return Data Is Available as of %s ******" %actual_ret_date)
        else:
            print("\n ***** Updating Risk Factor Return Data *****")
            dtp.update_rf_returns()

            print("\n ***** Updating Counterparty Price Data *****")
            dtp.update_prx_returns(prx_cat='ctp_banks')

            print("\n ***** Updating CDS Spreads Data *****")
            try:
                dtp.update_inv_cds_spreads(verbose=True)
            except:
                print("\t ERROR while downloading CDS Spreads")

            print("\n ***** Updating Gov Yield Data *****")
            dtp.update_inv_gov_yields(startdate=date_tdy - timedelta(5), enddate=date_tdy, verbose=True)





def T_afternoon_tasks(value_dates=[], account='caracalla', to_db=True, starting_point=0):
    """
    Released 1st September 2022
    Author: F.Balloni (fabio.balloni@traderepublic.com)
    Afternoon Tasks Schedule
    Covered Tasks:
        - PnL Calculation
        - Trading Book Value At Risk Models
            1. Risk Metrics Calculation
            2. Capital Requirement Calculation
            3. Limit Monitor

    @return: dictionary
    """
    # Importing Modules:
    from risk_pylibrary.tools import config as CF
    from risk_pylibrary.instruments import data_prices as dtp
    from risk_pylibrary.projects.caracalla import caracalla_portfolio as c_port
    from risk_pylibrary.risk_analytics import risk_engines as rie
    from risk_pylibrary.risk_models import pnl_fifo as pnl
    from risk_pylibrary.risk_models import pnl_support as pnl_sup


    # Screen value dates argument
    if len(value_dates) < 1:
        date_tdy = _datetime.now().date()
        if (date_tdy - timedelta(1)).weekday() == 6:
            value_dates = [date_tdy - timedelta(3)]
        else:
            value_dates = [date_tdy - timedelta(1)]



    print("Initiating Afternoon Task Schedule")

    # ***********************************************************************************************************
    if starting_point <= 10:
        print("\t 1. %s Trading Book: PnL Execution"%account)

        # Get Start Date
        start_date = value_dates[0]-timedelta(1) if value_dates[0].weekday() != 0 else value_dates[0]-timedelta(3)

        print("\t\t 1.1. Building Initial Cache between %s and %s"%(start_date, value_dates[0]))

        pnl_sup.build_initial_cache(startdate=start_date, enddate=value_dates[0])

        print("\t\t 1.2. Initiating PnL Calculation on %s"%value_dates[0])
        tmp_pos, tmp_cache, tmp_trades = pnl.initiate_pnl_engine(value_dates[0], value_dates[0])

        print("\t\t 1.3. Parsing Data into Datawarehouse")
        print("\t\t\t 1.3.1. Parsing Positions Data")

        pnl_sup.parse_pos(tmp_pos)

        print("\t\t\t 1.3.1. Parsing Positions Data as report date %s"%value_dates[0])
        pnl_sup.parse_cache(tmp_cache, value_dates[0])


    # ***********************************************************************************************************

    if starting_point <= 20:
        print("\t 2. Trading Book: Setting Up Risk Parameters for account %s"%account)

        # Assign Output Dictionary:
        out_dict = dict()
        # Calculates Risk Factor Portfolio
        calc_rf_port = True
        # Calculates Risk Metrics (e.g. VaR). Dependent on calc_rf_port
        calc_risk = True

        if account == 'caracalla':
            account_qry = 9800001301
        elif account == 'caligula':
            account_qry = 9800003301
        elif account == 'tiberius':
            account_qry = 9800001601
        elif account == 'trajan':
            account_qry = 9800003601
        elif account == 'alg':
            account_qry = 9800000201
        elif account == 'trajan':
            account_qry = 9800003601
        elif account == 'fx_mm0':
            account_qry = 9800005001
        elif account == 'fx_mm1':
            account_qry = 9800005401
        elif account == 'fx_mm2': 
            account_qry = 9800005201
        elif account is None:
            raise Exception('ERROR: You need to Specify an Account')
        else:
            account_qry = account


        print('\t\t Running Analytics for: %s' % value_dates)

        # Set Quantile List
        qtls = [0.05, 0.01, 0.001]
        # Set Window:
        window = 250
        # Activates in code prints:
        print_verbose = False
        # Set risk engines with parameters
        # Modells run with a Student's T distribution assumption. The decay factor is 0.94. GJR GARCH runs with filtered
        # historical simulation (FHS).
        risk_engines = {
            'gjr': {'qtls': qtls,'window': window,'distr': 't','fhs': True,'decay': 0.94,'verbose': print_verbose},
            'ewma': {'qtls': qtls,'window': window,'distr': 't','decay': 0.94,'verbose': print_verbose},
            'mc': {'qtls': qtls,'window': window,'distr': 't','ewma_cov': True,'decay': 0.94,'n_sim': 1000,
                   'verbose': print_verbose},
            'hs': {'qtls': qtls,'window': window,'verbose': print_verbose}}
        #
        # Calculate SVaR
        calc_svar = False
        # Calculate PnL
        calc_pnl_report = True

        # ***********************************************************************************************************

        print("\t 2. %s Trading Book: Checking Positions"%account_qry)
        #Check if Newest Positions Data is already in
        qry ='''
        SELECT
            *
        FROM
            TEAMS_PRD.RISK_FUNCTION_PUBLISH.PBL__RISK_FUNCTION_MRM_BOOK_TRADING_VALUATION
        WHERE
            SEC_ACC_NO = %s
        AND
            REPORT_DATE = %s
        '''
        max_entry_db_pos = db.run_query(query=qry%(account_qry,db.sqldate(value_dates[-1]))).iloc[0][0]

        if max_entry_db_pos == value_dates[-1]:
            pos_rdy = 1
            print("\t\t\n ***** New Positions Data Is Available as of %s ******" % value_dates[-1])
        else:
            import sys
            pos_rdy = 0
            sys.exit("\t\t\n ***** STOP: New Portfolio Data not yet available *****")

        # ***********************************************************************************************************
        print("\t 3. %s Trading Book: Checking Returns"%account)
        # Check if Newest Returns Data is already in
        max_entry_db_rets = db.run_query(query='SELECT MAX(ddate) '
                                               'FROM teams_prd.risk_data.returns_daily_clean').iloc[0][0]

        if max_entry_db_rets == value_dates[-1] or max_entry_db_rets >= value_dates[-1]:
            rets_rdy = 1
            print("\n ***** New Return Data Is Available as of %s ******" % value_dates[-1])
        else:
            rets_rdy = 0
            import sys
            sys.exit("\t\t\n ***** STOP: New Return Data Data not yet available *****")

        # ***********************************************************************************************************
        print("\t 4. %s Trading Book: Running RiskMetrics For Benchmarks"%account)
        # Check if Newest Positions Data is already in
        if rets_rdy:
            out_db_rm_bmk = pd.DataFrame()
            active_bmks = [['msci_world', 'global_agg_bond']]
            rets_vaR_tot = dtp.get_rf_returns(rf_list=active_bmks[0])

            for dd in value_dates:

                rets_vaR = rets_vaR_tot[:dd]
                if dd not in rets_vaR.index:
                    print("\t\t\n ***** WARNING: Filling Missing Day in Benchmark with 0: %s *****" % dd)
                    rets_vaR.loc[dd] = 0

                for bmk in active_bmks:
                    df_risk_bmk = pd.DataFrame()

                    for k in risk_engines:
                        fmt_engine_tmp = risk_engines[k]
                        wgts_vaR = np.array([1, 0])
                        tmp_var = rie.portfolio_vaR(rets_vaR[bmk],
                                                    wgts_vaR,
                                                    engine=k,
                                                    fmt_engine=fmt_engine_tmp)
                        tmp_var.columns = [tmp_var.columns[i] + '_%s' % k for i in range(0, len(tmp_var.columns))]
                        df_risk_bmk = pd.concat([df_risk_bmk, tmp_var], axis=1)

                    df_risk_bmk.index.name = 'ddate'
                    df_risk_bmk = df_risk_bmk.rets2db()
                    df_risk_bmk['account'] = 'bmk_caracalla'
                    df_risk_bmk = df_risk_bmk[['ddate', 'account', 'code', 'value']]
                    df_risk_bmk['ddate'] = dd
                    # Add Return for MSCI World
                    df_risk_bmk = pd.concat([df_risk_bmk,
                                             pd.DataFrame([[dd,
                                                            'bmk_caracalla',
                                                            'total_return_bmk_caracalla',
                                                            rets_vaR.loc[dd][0]]],
                                                          columns=df_risk_bmk.columns)], axis=0)
                    out_db_rm_bmk = pd.concat([out_db_rm_bmk, df_risk_bmk], axis=0)

        # ***********************************************************************************************************

        print("\t 5. %s Trading Book: Running RiskMetrics For Portfolios"%account)

        if rets_rdy and pos_rdy:
            out_db_rm = pd.DataFrame()
            out_db_pos = pd.DataFrame()
            print('Running Analytics:')
            for dd in value_dates:
                out_dict_tmp = c_port.get_caracalla_portfolio(calc_rf_port=calc_rf_port,
                                                              calc_risk=calc_risk,
                                                              calc_pnl_report=False,
                                                              value_date=dd,
                                                              risk_engines=risk_engines,
                                                              rf_mapping_new=True,
                                                              force_rf=True, new_pf_engine=True, live_trading=False, account=account)

                if calc_risk:
                    out_rm = out_dict_tmp['risk_metrics']
                    out_rm.index.name = 'ddate'
                    # Save RiskMetrics Data
                    out_db_rm = pd.concat([out_db_rm, out_rm.rets2db()],axis=0)

                # Save Positions Data
                out_pos = out_dict_tmp['rf_portfolio'].reset_index()
                out_pos['ddate'] = dd
                out_pos = out_pos[['ddate', 'risk_factor', 'weight']]
                out_pos = out_pos.set_index('ddate')
                out_db_pos = pd.concat([out_db_pos, out_pos.rets2db()], axis=0)

                # Save Notional Exposure Total Data
                #out_exp_tot = out_dict_tmp['pnl_tot'].iloc[:, [0,-2,-1]].loc[[dd]]
                #out_db_rm = pd.concat([out_db_rm,out_exp_tot.rets2db()], axis=0)

                if calc_svar:
                    for risk_model in ['gjr','hs']:
                        print('Initializing Model: %s' % risk_model)
                        df_svar = rie.stressed_vaR(out_dict_tmp['rf_portfolio_returns'], np.array([1]), engine=risk_model,
                                                   fmt_engine=risk_engines[risk_model])
                        df_svar_max = df_svar.max().to_frame().T.rename(index={0: dd},
                                                                        columns=lambda x: 's' + x + '_%s' % risk_model)
                        df_svar_max.index.name = 'ddate'
                        out_db_rm = pd.concat([out_db_rm,df_svar_max.rets2db()],axis=0)




        print('***********************************************************************************************************')

        print("\t 6. Caracalla Trading Book: Running Market Liquidity Calculation")

        # from risk_pylibrary.projects.econometrics import market_liquidity as mrlq
        #
        # sdate_mlrq = _datetime(value_dates[0].year-1, value_dates[0].month, value_dates[0].day-1)
        #
        # out_dict['df_mrlq'] = mrlq.calculate_mr_liq_buffer(sdate_mlrq, value_dates[0])



        print('***********************************************************************************************************')

        print("\t 7. Caracalla Trading Book: Parsing RiskMetrics into the Database")

        # Adjusting the Output
        out_db_rm['account'] = account
        out_db_rm = out_db_rm[['ddate', 'account', 'code', 'value']]

        # *******************************************************

        # print("\t\t 6.1. Capital Requirements")
        # ll_codes = ['svar999_1d_gjr', 'svar999_1d_hs', 'var999_1d_gjr', 'var999_1d_hs', 'risk_exposure_in_eur_total']
        # df_cap_req_tmp = out_db_rm[(out_db_rm.account == account) & (out_db_rm.code.isin(ll_codes))]
        # df_cap_req = pd.pivot_table(df_cap_req_tmp[['ddate', 'code', 'value']],index='ddate',columns='code')
        # df_cap_req.columns = df_cap_req.columns.droplevel()

        # if calc_svar:
        #     df_cap_req = df_cap_req[['risk_exposure_in_eur_total','svar999_1d_gjr',
        #                              'svar999_1d_hs','var999_1d_gjr','var999_1d_hs']]
        #     df_cap_req['cap_req_svar_hs_h250'] = df_cap_req.svar999_1d_hs * np.sqrt(250)
        #     df_cap_req['cap_req_svar_gjr_h250'] = df_cap_req.svar999_1d_gjr * np.sqrt(250)
        #     df_cap_req['cap_req_svar_hs_h30'] = df_cap_req.svar999_1d_hs * np.sqrt(30)
        #     df_cap_req['cap_req_svar_gjr_h30'] = df_cap_req.svar999_1d_gjr * np.sqrt(30)
        # else:
        #     df_cap_req = df_cap_req[['risk_exposure_in_eur_total','var999_1d_gjr','var999_1d_hs']]

        # df_cap_req['cap_req_var_gjr_h30'] = df_cap_req.var999_1d_gjr * np.sqrt(30)
        # df_cap_req['cap_req_var_hs_h30'] = df_cap_req.var999_1d_hs * np.sqrt(30)
        # df_cap_req['cap_req_var_gjr_h250'] = df_cap_req.var999_1d_gjr * np.sqrt(250)
        # df_cap_req['cap_req_var_hs_h250'] = df_cap_req.var999_1d_hs * np.sqrt(250)
        # df_db_cap_req = df_cap_req.copy()
        # df_db_cap_req = df_db_cap_req[[k for k in df_db_cap_req.columns if k.startswith('cap')]]

        # # Level Values above 1:
        # df_db_cap_req[df_db_cap_req > 1] = 1

        # # Multiply by Notional Exposure:
        # df_db_cap_req = df_db_cap_req.multiply(df_cap_req.loc[:,'risk_exposure_in_eur_total'], axis='index')

        # # Format Output:
        # df_db_cap_req = df_db_cap_req.rets2db()
        # df_db_cap_req['account'] = account
        # out_db_cap_req = df_db_cap_req.iloc[:,[0,-1,1,2]]
        # out_db_cap_req = out_db_cap_req[out_db_cap_req.code != 'risk_exposure_in_eur_total']

        # # Create single output DataFrame
        # out_db_rm = pd.concat([out_db_rm,out_db_rm_bmk,out_db_cap_req],axis=0)

        # print("\t\t 6.2. Adding Market Liquidity Risk")

        # out_db_mrliq = pd.DataFrame(columns=['ddate', 'account', 'code', 'value'], index=[out_db_rm.index[-1]])
        # out_db_mrliq.loc[0, 'ddate'] = value_dates[0]
        # out_db_mrliq.loc[0, 'account'] = account
        # out_db_mrliq.loc[0, 'code'] = 'mr_lvaR_weighted_mean'
        # out_db_mrliq.loc[0, 'value'] = 0 #out_dict['df_mrlq']['mr_lvaR_weighted'].mean()

        # # Append to out_db_rm
        # out_db_rm = pd.concat([out_db_rm, out_db_mrliq], axis=0)
        # out_db_rm = out_db_rm.dropna()


        out_dict['out_db_rm'] = out_db_rm.dropna()

        # *******************************************************

        if to_db:

            print("\t\t 6.2. Parsing Data")
            print("\t\t 6.2.1. Parsing Risk Metrics to DWH: TEAMS_PRD.RISK_DATA.RISK_METRICS_DAILY")


            try:
                db.run_query(query='CREATE TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_DUMMY '
                                   'CLONE TEAMS_PRD.RISK_DATA.RISK_METRICS_DAILY')
            except:
                print("WARNING: Potential Issue with creating Risk Metrics Dummy Table.")
                pass

            try:
                db.pandas2db(out_db_rm,'TEAMS_PRD.RISK_DATA.RISK_METRICS_DUMMY', replace=True)
            except:
                print(out_db_rm.head())
                print('Length of DataFrame: %s' % len(out_db_rm))
                print("WARNING: Potential Issue with parsing Data. Check: TEAMS_PRD.RISK_DATA.RISK_METRICS_DUMMY")
                pass


            qry_rm = 'merge into TEAMS_PRD.RISK_DATA.RISK_METRICS_DAILY as tgt_table ' \
                     'using TEAMS_PRD.RISK_DATA.RISK_METRICS_DUMMY as src_table ' \
                     'on(tgt_table.ddate = src_table.ddate AND tgt_table.account = src_table.account AND tgt_table.code = src_table.code) ' \
                     'when not matched then ' \
                     'insert(ddate,account,code,value) values(src_table.ddate,src_table.account,src_table.code,src_table.value)'

            try:
                db.run_query(query=qry_rm, fmt_engine='RISK')
            except:
                print("WARNING: Potential Issue with merging Risk Metrics Dummy Table.")
                pass

            try:
                db.run_query(query='DROP TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_DUMMY')
            except:
                print("WARNING: Potential Issue with dropping Risk Metrics Dummy Table.")
                pass

            print("\t\t 6.2.2. Parsing Positions to DWH: TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS")
            # Clone Table
            try:
                db.run_query(query='CREATE TABLE TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS_DUMMY '
                                   'CLONE TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS')
            except:
                print("WARNING: Potential Issue with creating Table.")
                pass

        # Format Data
        df_pos = out_dict_tmp['inventory']
        df_pos = df_pos.loc[value_dates]
        for dd in value_dates:
            df_pos_tmp = df_pos.loc[dd]
            # Check for Maximum Position Limit Excess
            df_pos_lim = df_pos_tmp[df_pos_tmp.position_eod > 8][['name_official', 'position_eod']]

            # Print Pos Limit Check
            if df_pos_lim.empty is False:
                print("\t\t Alert: Maximum Position of 6 breached")
                print(df_pos_lim)

            # Check for Short Positions
            df_pos_short = df_pos_tmp[df_pos_tmp.position_eod < 0][['name_official','position_eod']]
            # Print Pos Short Check
            if df_pos_short.empty is False:
                print("\t\t Alert: Short Positions detected")
                print(df_pos_short)

        df_pos = df_pos[['position_eod']].reset_index()
        df_pos['code'] = 'quantity'
        df_pos['timestamp_cest'] = df_pos.ddate.apply(lambda x: _datetime(x.year,x.month,x.day,23,0,0))
        df_pos['account'] = '%s_sharebooking'%account
        df_pos = df_pos.rename(columns={'position_eod': 'value'})
        df_pos = df_pos[['timestamp_cest', 'account', 'instrument_id', 'code', 'value']]
        out_dict['df_pos'] = df_pos

        if to_db:
            # Parse Data into Dummy Table
            try:
                db.pandas2db(df_pos,'TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS_DUMMY', replace=True)
            except:
                print(df_pos.head())
                print('Length of DataFrame: %s' % len(df_pos))
                print(
                    "WARNING: Potential Issue with parsing Data. Check: TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS_DUMMY")
                pass


            # Create Merge Query
            qry_pos = 'merge into TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS as tgt_table ' \
                      'using TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS_DUMMY as src_table ' \
                      'on(tgt_table.timestamp_cest = src_table.timestamp_cest ' \
                      'AND tgt_table.account = src_table.account ' \
                      'AND tgt_table.code = src_table.code ' \
                      'AND tgt_table.instrument_id = src_table.instrument_id) ' \
                      'when not matched then ' \
                      'insert(timestamp_cest,account,instrument_id,code,value)' \
                      'values(src_table.timestamp_cest,src_table.account,src_table.instrument_id,src_table.code,src_table.value)'

            try:
                db.run_query(query=qry_pos,fmt_engine='RISK')
            except:
                print("WARNING: Potential Issue with merging Positions Dummy Table.")
                pass

            try:
                db.run_query(query='DROP TABLE TEAMS_PRD.RISK_DATA.PORTFOLIO_POSITIONS_DUMMY')
            except:
                print("WARNING: Potential Issue with dropping Positions Dummy Table.")
                pass

        print('***********************************************************************************************************')

        # print("\t 7. Caracalla Trading Book: Parsing LimitMetrics into the Database")

        # # *******************************************************

        # print("\t\t 7.1. Running Limit Report ")
        # df_lim = c_port.get_limit_report(out_dict_tmp, account= account, value_dates=[value_dates[-1]], keep_lim_val=True)
        # df_lim.index.name = 'ddate'
        # df_db_lim = df_lim.loc[[value_dates[-1]]].rets2db()
        # df_db_lim['account'] = account
        # df_db_lim = df_db_lim[['ddate','account','code','value']]
        # out_dict['df_db_lim'] = df_db_lim

        # print(pd.pivot_table(df_db_lim[df_db_lim.code.str.endswith('value')],
        #                      columns='code',
        #                      index='ddate',
        #                      values='value'))

        # *******************************************************
        # if to_db:
        #     print("\t\t 5.2. Parsing Data")

        #     try:
        #         db.run_query(query='CREATE TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_LIMITS_DUMMY '
        #                            'CLONE TEAMS_PRD.RISK_DATA.RISK_METRICS_LIMITS_DAILY')
        #     except:
        #         print("WARNING: Potential Issue with creating Limits Dummy Table.")
        #         pass


        #     try:
        #         db.pandas2db(df_db_lim,'TEAMS_PRD.RISK_DATA.RISK_METRICS_LIMITS_DUMMY',replace=False)
        #     except:
        #         print(df_db_lim.head())
        #         print('Length of DataFrame: %s' % len(df_db_lim))
        #         print(
        #             "WARNING: Potential Issue with parsing Data. Check: TEAMS_PRD.RISK_DATA.RISK_METRICS_LIMITS_DUMMY")
        #         pass


        #     qry_lim = 'merge into TEAMS_PRD.RISK_DATA.RISK_METRICS_LIMITS_DAILY as tgt_table ' \
        #               'using TEAMS_PRD.RISK_DATA.RISK_METRICS_LIMITS_DUMMY as src_table ' \
        #               'on(tgt_table.ddate = src_table.ddate AND tgt_table.account = src_table.account AND tgt_table.code = src_table.code) ' \
        #               'when not matched then ' \
        #               'insert(ddate,account,code,value) values(src_table.ddate,src_table.account,src_table.code,src_table.value)'

        #     try:
        #         db.run_query(query=qry_lim, fmt_engine='RISK')
        #     except:
        #         print("WARNING: Potential Issue with Merging Limits Dummy Table.")
        #         pass

        #     try:
        #         db.run_query(query='DROP TABLE TEAMS_PRD.RISK_DATA.RISK_METRICS_LIMITS_DUMMY')
        #     except:
        #         print("WARNING: Potential Issue with dropping Limits Dummy Table.")
        #         pass

        return out_dict
