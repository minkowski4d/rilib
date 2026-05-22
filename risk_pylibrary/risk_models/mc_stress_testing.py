#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm, t
import traceback

# Import Custom Modules
from tools.snowflake_db import db_connection as db
from instruments import data_prices as dtp
from risk_pylibrary.tools import config as CF
from portfolio_analytics import positions as pos
from risk_models import mc_models


def stress_test_engine(report_date=None, acct=9800003301, stress_scenarios=None, horizon=250, apply_dq=True, plot=False, verbose=True):
 
    out_dict_pf =pos.get_port(acct, report_date, force_rf=True)

    # Risk Factor Portfolio:
    port_rf = out_dict_pf['rf_portfolio'].reset_index().set_index('risk_factor')
    port_rf = port_rf[~port_rf.index.duplicated(keep='first')]

    # Risk Factor Series:
    rets_rf = out_dict_pf['returns']
    rets_rf = rets_rf.loc[:, ~rets_rf.columns.duplicated()].copy()

    # Get Risk Factor Table:
    if len(CF.cache_rf_map) == 0:
        rf_map = db.run_query('SELECT * FROM TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__GSHEET_MRM_RFM_EQUITY')
        CF.cache_rf_map = rf_map
    else:
        rf_map = CF.cache_rf_map

    # Run Stress Test:
    if len(CF.cache_stress_desc) == 0:
        df_stress_desc = db.run_query('SELECT * FROM TEAMS_PRD.RISK_DATA_SENSITIVE.RISK_STRESS_SCENARIO_DEFINITIONS')
        CF.cache_stress_desc = df_stress_desc
    else:
        df_stress_desc = CF.cache_stress_desc


    if stress_scenarios is not None:
        df_stress_desc = df_stress_desc[df_stress_desc.code.isin(stress_scenarios)]
    else:
        stress_scenarios = list(df_stress_desc.code)

    # Build Cash
    # Extract Stress Series:
    df_stress_mtx = pd.DataFrame()
    for stress_code in df_stress_desc['code']:
        str_series = df_stress_desc[df_stress_desc['code'] == stress_code].stress_scenario_parameter.iloc[0]
        (list_series) = [k.split(' ')[0] for k in str_series.split('|')]
        value_series = [k.split(' ')[1] for k in str_series.split('|')]

        #Assign Values
        tmp = pd.DataFrame()
        tmp['code'] = len(list_series)*[stress_code]
        tmp['stress_factor'] = list_series
        tmp['value'] = [float(k.replace('bps',''))/10000
                         if k[-3:]=='bps' else float(k.replace('%',''))/100 for k in value_series]
        tmp['stress_factor_unit'] = tmp.stress_factor.map(dict(zip(rf_map.code, rf_map.asset_class)))
        tmp['shock_length'] = df_stress_desc[df_stress_desc['code'] == stress_code].shock_length.iloc[0]

        # Append Result
        df_stress_mtx = pd.concat([df_stress_mtx, tmp], axis=0)

    df_stress_mtx['stress_mean'] = df_stress_mtx['value'] / df_stress_mtx['shock_length']


    # Create RF port for getting the return series
    sf_stress_dict = db.run_query(query="SELECT * "
                                        "FROM TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING_STRESS_TEST "
                                        "WHERE CODE IN (%s)"%db.joinpad(df_stress_mtx.stress_factor.unique()))

    sf_stress_dict = sf_stress_dict[['code', 'code_2']]
    sf_stress_dict.columns = ['risk_factor', 'oas_series']
    sf_stress_dict = sf_stress_dict.set_index(['risk_factor', 'oas_series'])
    sf_stress_dict['weight'] = 1
    sf_stress_dict['duration_mod'] = np.nan
    sf_stress_dict['convexity'] = np.nan

    # Map Durations and Convexities
    dur_mod_map = {'YIELD_IT_10Y':10, 'YIELD_IT_3Y':3,
                   'YIELD_US_10Y':10, 'YIELD_US_3Y':3,
                   'YIELD_DE_10Y':10, 'YIELD_DE_3Y':3,
                   'IG_CREDIT_US_5Y':5, 'HY_CREDIT_US_5Y':5}

    sf_stress_dict['duration_mod'] = sf_stress_dict.index.get_level_values(0)
    sf_stress_dict['duration_mod'] = sf_stress_dict['duration_mod'].map(dur_mod_map)

    convex_map = {'YIELD_IT_10Y':250, 'YIELD_IT_3Y':150,
                   'YIELD_US_10Y':250, 'YIELD_US_3Y':150,
                   'YIELD_DE_10Y':250, 'YIELD_DE_3Y':150,
                   'IG_CREDIT_US_5Y':150, 'HY_CREDIT_US_5Y':250}

    sf_stress_dict['convexity'] = sf_stress_dict.index.get_level_values(0)
    sf_stress_dict['convexity'] = sf_stress_dict['convexity'].map(convex_map)

    # Use Yield RFs only!
    sf_port_stress_fixed_income = sf_stress_dict.dropna()
    sf_list_fixed_income = list(sf_port_stress_fixed_income.index.get_level_values(0)) + list(sf_port_stress_fixed_income.index.get_level_values(1))
    sf_list_fixed_income = [k for k in sf_list_fixed_income if len(k)>0]

    # Get Stress Factor Returns:
    if len(CF.cache_rets_stress_factors) > 0:
        rets_stress_factors = CF.cache_rets_stress_factors
    else:
        rets_stress_factors = pd.DataFrame()

    # Yields Data Used for Stressed Means
    if len(sf_list_fixed_income) > 0:
        if len(CF.cache_df_sf_yields) == 0:
            df_sf_yields = dtp.get_rf_returns(rf_port=sf_port_stress_fixed_income, rf_list=sf_list_fixed_income, yield2tr=False)

            if apply_dq:
                # Replace Zero:
                for col in df_sf_yields.columns:
                    df_sf_yields[col] = df_sf_yields[col].replace(0, pd.NA).ffill()

            CF.cache_df_yields = df_sf_yields
        else:
            df_sf_yields = CF.cache_df_sf_yields


    # Return Data Used for Regression
    if len(sf_list_fixed_income) > 0:
        if len(CF.cache_df_sf_yields_rets) == 0:
            # Return Data Used for Regression
            df_sf_yields_rets = dtp.get_rf_returns(rf_port=sf_port_stress_fixed_income, rf_list=sf_list_fixed_income, yield2tr=True)

            if apply_dq:
                from risk_pylibrary.projects.data_quality import iqr_logic as iqr
                df_sf_yields_rets, cleaning_report = iqr.iqr_data_cleansing(df_sf_yields_rets, 10)

                if verbose:
                    print(cleaning_report)

            CF.cache_df_yields_rets = df_sf_yields_rets
        else:
            df_sf_yields_rets = CF.cache_df_sf_yields_rets

        rets_stress_factors = df_sf_yields_rets

    else:
        df_sf_yields_rets = pd.DataFrame()

    # Percentage Returns
    sf_list_pct = sf_stress_dict[sf_stress_dict['duration_mod'].isnull()].index.get_level_values(0)
    if len(sf_list_pct) > 0:
        if len(CF.cache_df_sf_rets) == 0:
            df_sf_rets = dtp.get_rf_returns(rf_list=sf_list_pct, yield2tr=False)
            CF.cache_df_sf_rets = df_sf_rets
        else:
            df_sf_rets = CF.cache_df_sf_rets

        # Concatenate Pct Returns:
        rets_stress_factors = pd.concat([df_sf_rets, df_sf_yields_rets], axis=1).sort_index()
        CF.cache_rets_stress_factors = rets_stress_factors


    # Perform Regression Analysis *************************************************
    # Get Stress Series
    if rets_stress_factors.empty:
        raise Exception('ERROR: Stress Factor Returns could not be retrieved')

    # Run Linear Regression for Missing Stress Factors on all Risk Factors
    out_reg = pd.DataFrame(index=df_stress_mtx.stress_factor.unique(), columns=rets_rf.columns)
    for stress_factor in out_reg.index:
        for risk_factor in rets_rf.columns:
            if verbose:
                print("\t Running Regression of Stress Factor %s against %s" % (stress_factor,risk_factor))
            if stress_factor == risk_factor:
                out_reg.loc[stress_factor, risk_factor] = 1
            else:
                tmp = pd.concat([rets_stress_factors[[stress_factor]], rets_rf[[risk_factor]]], axis=1).dropna()
                tmp = tmp[-horizon:]
                X = sm.add_constant(tmp[risk_factor])
                model_tmp = sm.OLS(tmp, X)
                res = model_tmp.fit()
                out_reg.loc[stress_factor, risk_factor] = res.params.loc[risk_factor].iloc[0]


    if len(CF.cache_stress_regressions) == 0:
        CF.cache_stress_regressions = out_reg
    else:
        out_reg = CF.cache_stress_regressions

    # Build Weight Out of each not specifically stressed portfolio risk factor
    out_dict = dict()
    for scen in stress_scenarios:
        if verbose:
            print("Simulating the Scenario %s"%scen)
        try:
            tmp_dict = dict()
            # Set Already Known Variables:
            forward_horizon = df_stress_mtx[df_stress_mtx.code == scen].shock_length.iloc[0]

            # Get Scenario Stress Factors
            str_series_stress = df_stress_desc[df_stress_desc['code'] == scen].stress_scenario_parameter.iloc[0]
            list_stress = [k.split(' ')[0] for k in str_series_stress.split('|')]

            # Calc Total Beta:
            out_reg_tmp = out_reg.loc[list_stress]
            # Multiply Betas by Risk Factor Weights
            out_reg_tmp_weighted = out_reg_tmp.mul(port_rf.loc[rets_rf.columns].weight)

            # Get New Stress Factor Portfolio
            tmp_rets = rets_stress_factors[list_stress].dropna().mul(out_reg_tmp_weighted.sum(axis=1))

            # Evaluate Stressed Means:
            out_stressed_means = pd.DataFrame(index=list_stress, columns=['stressed_mean'])
            for stress_fac in list_stress:
                tmp = df_stress_mtx[(df_stress_mtx['stress_factor'] == stress_fac) & (df_stress_mtx['code'] == scen)]
                out_stressed_means.loc[stress_fac, 'stressed_mean'] = tmp.stress_mean.iloc[0]


            out_rep, out_mean_distr, port_plot, port_plot_total = stress_test_primer(tmp_rets.dropna(),
                                                                                     out_reg_tmp_weighted.sum(axis=1).values,
                                                                                     n_sim=1000,
                                                                                     stressed_means=np.array(out_stressed_means.stressed_mean.tolist()),
                                                                                     forward_horizon=forward_horizon,
                                                                                     scenario=scen, plot=plot)

            tmp_dict['out_rets'] = tmp_rets
            tmp_dict['port_rf'] = out_reg_tmp_weighted.sum(axis=1)
            tmp_dict['out_rep'] = out_rep
            tmp_dict['out_mean_distr'] = out_mean_distr
            tmp_dict['port_plot'] = port_plot
            tmp_dict['port_plot_total'] = port_plot_total

            out_dict[scen] = tmp_dict
        except:
            print(traceback.format_exc())
            pass

    return out_dict







def stress_test_primer(rets_orig, wgts, n_sim=1000, stressed_means=None,
                       forward_horizon=90, plot=True, scenario=None):
    """
    Primer for Stress Testing
    @return:
    """

    # Run MonteCarlo Simulation with stressed means and with series means
    # Slice Original Returns
    rets = rets_orig.copy()

    # Run Simulations
    # Simulating without Stress:
    sim_ret, sim_ts = mc_models.mc_simulate(rets,
                                            n=n_sim,
                                            ewma_cov=True,
                                            distr='t',
                                            sim_len=forward_horizon)

    # Simulating with covariance estimator:
    sim_rets_ml, sim_ts_ml = mc_models.mc_simulate(rets,
                                                   n=n_sim,
                                                   ewma_cov=True,
                                                   mlest_cov=True,
                                                   stress_means=stressed_means,
                                                   distr='t',
                                                   sim_len=forward_horizon)



    # Calculate Portfolio:
    port_stress_sim = sim_rets_ml.dot(wgts.T).to_frame().unstack().T
    port_base_sim = sim_ret.dot(wgts.T).to_frame().unstack().T

    # Fill Portfolio ChartOutPut:
    port_plot = pd.DataFrame(columns=['mean',
                                      'baseline',
                                      'qtl_750', 'qtl_950', 'qtl_990', 'qtl_999'],
                             index=np.arange(len(rets), len(rets)+ forward_horizon, 1))

    distr_stress_values = (1+sim_rets_ml.dot(wgts.T).to_frame().unstack().T).cumprod().iloc[-1].values
    distr_base_values = (1 + sim_ret.dot(wgts.T).to_frame().unstack().T).cumprod().iloc[-1].values

    for kpi in port_plot.columns:

        if kpi == 'baseline':
            col = np.argmin(np.abs(distr_base_values - np.mean(distr_base_values)))
            port_plot[kpi] = port_base_sim[col].values
        else:
            if kpi == 'mean':
                col = np.argmin(np.abs(distr_stress_values - np.mean(distr_stress_values)))
            else:
                kpi_calc = 1 - int(kpi.split('_')[1])/1000
                col = np.argmin(np.abs(distr_stress_values - np.quantile(distr_stress_values, kpi_calc)))
            port_plot[kpi] = port_stress_sim[col].values

    # Append Values to Historical Simulation of the Portfolio
    port_plot_total = pd.concat([pd.DataFrame(np.array(6 * [rets.dot(wgts.T).values.T]).T, columns=port_plot.columns), port_plot], axis=0)

    # Create SubOutPuts:
    out_rep = pd.DataFrame(index=['Mean', 'Median'],
                           columns=['Baseline', 'Covariance_Stressed'])

    out_mean_distr = pd.DataFrame(index=np.arange(0, n_sim, 1), columns=['Baseline', 'Covariance_Stressed'])

    for sim_grp, sim_ts_df in dict(zip(out_rep.columns, [sim_ts, sim_ts_ml])).items():
        # Fill OutRep:
        out_rep.loc['Mean', sim_grp] = sim_ts_df.iloc[:, [0]].unstack().T.iloc[-1].mean()/100-1
        out_rep.loc['Median', sim_grp] = sim_ts_df.iloc[:, [0]].unstack().T.iloc[-1].median() / 100 - 1
        # Fill Mean Distributions:
        out_mean_distr[sim_grp] = sim_ts_df.iloc[:, [0]].unstack().T.iloc[-1]/100-1


    if plot:
        from risk_pylibrary.tools import charting as CH
        CH.density_plot(out_mean_distr, tlt=scenario)
        CH.perf_plot(((1 + port_plot).cumprod() * 100), delta=None, tlt=scenario)

    return out_rep, out_mean_distr, port_plot, port_plot_total




def stress2db(out_dict, account,ddate):

    from datetime import timedelta
    out_db = pd.DataFrame()
    for idx in out_dict.keys():
        tmp = out_dict[idx]['port_plot']
        tmp = tmp.reset_index().drop('index', axis=1)
        tmp['ddate_fwd'] = pd.date_range(start=ddate, end=ddate + timedelta(len(tmp)-1))
        tmp = pd.melt(tmp, id_vars='ddate_fwd', var_name='code')
        tmp['account'] = account
        tmp['code'] = tmp['code'].apply(lambda x: idx+'_'+x)
        tmp['ddate'] = ddate
        tmp = tmp[['ddate', 'ddate_fwd', 'account', 'code', 'value']]

        # Capital Requirement Calculation
        cap_req_series = ((1+out_dict[idx]['port_plot']).cumprod()-1).iloc[-1]
        tmp_cap_req = pd.DataFrame(index=cap_req_series.index,columns=tmp.columns)
        tmp_cap_req['ddate'] = tmp.ddate.max()
        tmp_cap_req['ddate_fwd'] = tmp.ddate_fwd.max()
        tmp_cap_req['account'] = account
        tmp_cap_req['value'] = cap_req_series
        tmp_cap_req = tmp_cap_req.reset_index().drop(['code'], axis=1)
        tmp_cap_req = tmp_cap_req.rename(columns={'index':'code'})
        tmp_cap_req = tmp_cap_req[tmp.columns]
        tmp_cap_req['code'] = tmp_cap_req['code'].apply(lambda x: idx + '_' + 'capreq_' + x)
        
        # Max VaR
        tmp_var = pd.DataFrame(index=[0],columns=tmp.columns)
        tmp_var['ddate'] = tmp.ddate.max()
        tmp_var['ddate_fwd'] = tmp.ddate_fwd.max()
        tmp_var['account'] = account
        tmp_var['code'] = idx + '_' + 'maxvar'
        tmp_var['value'] = (out_dict[idx]['port_plot_total']['qtl_999'].rolling(250).std()[-len(tmp):]*norm.ppf(0.999)).max()
        # FB: potential new anchor behaviour
        #tmp_var['value'] = (out_dict[idx]['port_plot_total']['qtl_999'].rolling(250).std()[-len(tmp):]*t.ppf(0.999, df=4)).max()

        # Build output
        out_db = pd.concat([out_db, tmp, tmp_cap_req, tmp_var], axis=0)

    return out_db



