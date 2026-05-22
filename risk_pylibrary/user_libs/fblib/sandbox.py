#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime

import pandas as pd




def pnl_performance(df, verbose=True):
    """
    Calculates PNL Data based on FiFo method.
    @param df:
        DataFrame needs to be passed as:
        time       - can be either integer index, date, datetime or timestamp object
        symbol     - consistent symbol. Must be a string
        side       - Either "B" for Buy or "S" for Sell
        price      - symbol price as float
        quantity   - traded quantity as absolut value as column "side" indicates direction
        multiplier - contract size
    @param verbose: prints Trade, Warning and Error Messages

    return: Multiple dictionary outputs
    """
    import pdb
    trade_dict = dict()
    for k in df.symbol.unique():
        trade_dict[k] = pd.DataFrame(columns = df.columns)

    pnl_dict = dict()
    for k in df.symbol.unique():
        pnl_dict[k] = pd.DataFrame(columns = list(df.columns[1:2]) + ['pnl'])


    # Series Outputs
    pos_series = pd.DataFrame(columns = list(df.columns[1:2]) + ['quantity'])
    pnl_series = pd.DataFrame(columns = ['symbol', 'pnl'])

    for i in list(df.index):
        tmp_trade = df.loc[[i]]
        time, symbol, side, price, quantity, multiplier = df.loc[i][0], df.loc[i][1], df.loc[i][2], df.loc[i][3], \
                                                          df.loc[i][4], df.loc[i][5]

        # Write Positions:
        pos_series.loc[time, 'symbol'] = symbol[:2]
        side_mult = -1 if side == 'S' else 1
        pos_series.loc[time, 'quantity'] = side_mult*tmp_trade.quantity.iloc[0]

        if trade_dict[symbol].empty or trade_dict[symbol].iloc[0]['side'] == side:
            # Fill Trade DF with first Symbol Trade or append trades in same direction
            trade_dict[symbol] = trade_dict[symbol].append(tmp_trade)

        elif trade_dict[symbol].iloc[0]['side'] != side:
            qty_residual = trade_dict[symbol].iloc[0].quantity - quantity

            if qty_residual > 0:
                if verbose: print('Qty_Residual > 0')
                pnl_tmp = 0
                # Sum PnL
                is_short_sell = -1 if trade_dict[symbol].iloc[0].side == 'S' else 1

                if verbose: print("Price %s, Price[0]: %s, Quantity: %s"%(price, trade_dict[symbol].iloc[0].price, quantity))
                pnl_tmp = (price - trade_dict[symbol].iloc[0].price)*quantity*multiplier*is_short_sell

                if verbose: print("PnL: %s"%pnl_tmp)
                trade_dict[symbol]['quantity'].iloc[0] = qty_residual
                pnl_dict[symbol].loc[time, 'symbol'] = symbol

                if np.isnan(pnl_dict[symbol].loc[time, 'pnl']):
                    pnl_dict[symbol].loc[time, 'pnl'] = 0
                pnl_dict[symbol].loc[time, 'pnl'] += pnl_tmp
                quantity = 0

            elif qty_residual == 0:
                if verbose: print('Qty_Residual == 0')
                pnl_tmp = 0
                # Sum PnL
                is_short_sell = -1 if trade_dict[symbol].iloc[0].side == 'S' else 1

                if verbose: print("Price %s, Price[0]: %s, Quantity: %s"%(price, trade_dict[symbol].iloc[0].price,quantity))
                pnl_tmp += (price - trade_dict[symbol].iloc[0].price)*quantity*multiplier*is_short_sell

                if verbose: print("PnL: %s"%pnl_tmp)
                if verbose: print("%s - Position on %s closed: PnL = %s"%(time, symbol, pnl_tmp))

                trade_dict[symbol]['quantity'].iloc[0] = qty_residual
                pnl_dict[symbol].loc[time, 'symbol'] = symbol

                if np.isnan(pnl_dict[symbol].loc[time, 'pnl']):
                    pnl_dict[symbol].loc[time, 'pnl'] = 0
                pnl_dict[symbol].loc[time, 'pnl'] += pnl_tmp

                if len(trade_dict[symbol]) == 1:
                    trade_dict[symbol] = pd.DataFrame(columns=df.columns)
                else:
                    trade_dict[symbol] = trade_dict[symbol][1:]

            elif qty_residual < 0:
                if verbose: print('Qty_Residual < 0')
                pnl_tmp = 0
                skip_j = 0
                for j in list(trade_dict[symbol].index):
                    if skip_j == 1: pass
                    qty_tmp = trade_dict[symbol].loc[j].quantity - quantity
                    if qty_tmp == 0:
                        is_short_sell = -1 if trade_dict[symbol].iloc[0].side == 'S' else 1
                        pnl_tmp += (price - trade_dict[symbol].iloc[0].price)*quantity*multiplier*is_short_sell
                        quantity -= trade_dict[symbol].loc[j].quantity
                        trade_dict[symbol] = trade_dict[symbol][1:]
                        skip_j = 1
                        if verbose: print("%s - Position on %s closed: PnL = %s"%(time, symbol, pnl_tmp))
                    elif qty_tmp < 0:
                        is_short_sell = -1 if trade_dict[symbol].loc[j].side == 'S' else 1
                        pnl_tmp += (price - trade_dict[symbol].loc[j].price)*trade_dict[symbol].loc[j].quantity*multiplier*is_short_sell
                        quantity -= trade_dict[symbol].loc[j].quantity
                        trade_dict[symbol] = trade_dict[symbol][1:]
                        if trade_dict[symbol].empty and quantity > 0:
                            trade_dict[symbol] = trade_dict[symbol].append(tmp_trade)
                            trade_dict[symbol]['quantity'].iloc[0] = quantity
                            print(trade_dict[symbol])
                    elif qty_tmp > 0:
                        trade_dict[symbol]['quantity'].loc[j] = qty_tmp
                        is_short_sell = -1 if trade_dict[symbol].loc[j].side == 'S' else 1
                        pnl_tmp += (price - trade_dict[symbol].loc[j].price)*quantity*multiplier*is_short_sell
                        quantity = 0
                        skip_j = 1
                pnl_dict[symbol].loc[time, 'symbol'] = symbol
                if np.isnan(pnl_dict[symbol].loc[time, 'pnl']): pnl_dict[symbol].loc[time, 'pnl'] = 0
                pnl_dict[symbol].loc[time, 'pnl'] += pnl_tmp

    # Create and Format pnl Series:
    for k in pnl_dict.keys():
        pnl_series = pnl_series.append(pnl_dict[k], sort = True)

    pnl_series['pnl_cumulative'] = pnl_series.pnl.cumsum()

    return trade_dict, pnl_dict, pos_series, pnl_series




def read_esma_xml(pth, startdate, enddate):
    """
    Code to extract SI Data from https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_fitrs_files
    @param pth: string - filename in .xml format
    @param startdate: date object - period startdate
    @param enddate: date object - period enddate
    @return: dataframe
    """
    import xmltodict

    with open(pth) as xml_file:
        data_dict = xmltodict.parse(xml_file.read())

    df = pd.DataFrame(data_dict['BizData']['Pyld']['Document']['FinInstrmRptgEqtyTradgActvtyRslt']['EqtyTrnsprncyData'])

    # Unpack nested values
    df['FrDt'] = ''
    df['ToDt'] = ''
    df['TtlNbOfTxsExctd'] = ''
    df['TtlVolOfTxsExctd'] = ''

    for row in range(0, len(df)):
        try:
            df.loc[row, 'FrDt'] = _datetime.strptime(df.loc[row]['RptgPrd']['FrDtToDt']['FrDt'], '%Y-%m-%d').date()
            df.loc[row, 'ToDt'] = _datetime.strptime(df.loc[row]['RptgPrd']['FrDtToDt']['ToDt'], '%Y-%m-%d').date()
        except:
            df.loc[row, 'FrDt'] = np.nan
            df.loc[row, 'ToDt'] = np.nan

        try:
            df.loc[row, 'TtlNbOfTxsExctd'] = int(df.loc[row]['Sttstcs']['TtlNbOfTxsExctd'])
            df.loc[row, 'TtlVolOfTxsExctd'] = float((df.loc[row]['Sttstcs']['TtlVolOfTxsExctd']))
        except:
            df.loc[row, 'TtlNbOfTxsExctd'] = np.nan
            df.loc[row, 'TtlVolOfTxsExctd'] = np.nan

    # Format
    df = df[['TechRcrdId', 'Id', 'FinInstrmClssfctn', 'Mthdlgy', 'FrDt', 'ToDt', 'TtlNbOfTxsExctd', 'TtlVolOfTxsExctd']]
    df = df.rename(columns={'Id':'instrument_id'})
    df = df.rename(columns=lambda x: x.lower())
    df = df[(df['frdt'] == startdate) & (df['todt'] == enddate)]

    return df


def quantile_regression(x, y, quantiles=[0.05, 0.5, 0.95]):

    from risk_pylibrary.tools import charting as CH
    from sklearn.utils.fixes import sp_version, parse_version
    from sklearn.linear_model import QuantileRegressor

    # This is line is to avoid incompatibility if older SciPy version.
    # You should use `solver="highs"` with recent version of SciPy.
    solver = "highs" if sp_version >= parse_version("1.6.0") else "interior-point"

    predictions = {}
    out_bounds_predictions = np.zeros_like(y, dtype=np.bool_)
    for quantile in quantiles:
        qr = QuantileRegressor(quantile=quantile, alpha=0, solver=solver)
        y_prediction = qr.fit(x[:, np.newaxis], y).predict(x[:, np.newaxis])
        predictions[quantile] = y_prediction

        if quantile == min(quantiles):
            out_bounds_predictions = np.logical_or(
                out_bounds_predictions, y_prediction >= y
            )
        elif quantile == max(quantiles):
            out_bounds_predictions = np.logical_or(
                out_bounds_predictions, y_prediction <= y
        )

    # Plot the Data
    fig = CH.figure(figsize=(8,8), facecolor="white")
    for quantile,y_pred in predictions.items():
        CH.plot(x[:, np.newaxis], y_pred, label=f"Quantile: {quantile}")

    CH.scatter(x[out_bounds_predictions], y[out_bounds_predictions],
               color="black", marker="+", alpha=0.5, label="Outside interval",)
    CH.scatter(x[~out_bounds_predictions], y[~out_bounds_predictions],
               color="black", alpha=0.5, label="Inside interval",)

    CH.legend()
    CH.xlabel("x")
    CH.ylabel("y")

    return fig



def get_yields(ticker='germany-3-month'):

    import re
    def get_soup(url, user_agent):
        from mechanize import Browser
        import random
        from bs4 import BeautifulSoup as BS
        br = Browser()
        br.set_handle_robots(False)
        br.set_handle_referer(False)
        br.set_handle_refresh(False)
        u_a = random.choice(user_agent)
        br.addheaders = [('User-agent', u_a)]
        br.open(url)
        soup = BS(br.response().read())
        return soup


    user_agent = ['Google Chrome', 'Firefox']
    url = 'https://www.investing.com/rates-bonds/%s-bond-yield-historical-data'%ticker
    soup = get_soup(url, user_agent)

    hp_str = soup.decode("utf-8")

    # Find Result Box:
    res_box = hp_str.find('results_box')
    # Find First Data Real Value
    first_dr = hp_str[res_box:].find('data-real-value')
    end_dr = hp_str[first_dr:].find('class="genTbl closedTbl historicalTblFooter"')
    start_str = hp_str[res_box+first_dr:end_dr]

    tr_list = [k.start() for k in re.finditer("<tr>", hp_str[res_box+first_dr:end_dr])]
    n = 0
    out = pd.DataFrame(columns=['yield'])
    for k in range(0, len(tr_list)):#len(hp_str[res_box+first_dr:end_dr])):
        if k < len(tr_list)-1:
            tmp_str = start_str[tr_list[k]:tr_list[k + 1] - 1]
            tmp_str = tmp_str[tmp_str.find('data-real-value'):]
            # Get TimeStamp

            time_stamp = int(tmp_str[tmp_str.find('"'):][1:11])
            dr_list = [l.start() for l in re.finditer('data-real-value', tmp_str)][1:]
            yield_close_start = dr_list[0] + tmp_str[dr_list[0]:].find('"') + 1
            yield_close_end = yield_close_start + tmp_str[yield_close_start:].find('"')
            out.loc[time_stamp, 'yield'] = float(tmp_str[yield_close_start:yield_close_end])
            n += tmp_str.find("<tr>")

    out = out.rename(index=lambda x: _datetime.fromtimestamp(x).date())
    out.columns = [ticker.replace('-', '_').replace('_month', 'M').replace('_year', 'Y')]

    return out


def stress_test_engine(ddate=None, port='caracalla', stress_scenarios=None, horizon=250):


    # Importing Modules
    from tools.snowflake_db import db_connection as db
    from risk_pylibrary.instruments import data_prices as dtp
    import statsmodels.api as sm
    from risk_pylibrary.tools import config as CF

    if port == 'caracalla':
        # Fractional Trading Book:
        from risk_pylibrary.projects.caracalla import caracalla_portfolio as c_port
        if len(CF.cache_caracalla_port) == 0:
            if ddate:
                out_dict = c_port.get_caracalla_portfolio(value_date=ddate,
                                                          force_rf=True,
                                                          calc_rf_port=True,
                                                          calc_pnl_report=False)
            else:
                out_dict = c_port.get_caracalla_portfolio(force_rf=True,
                                                          calc_rf_port=True,
                                                          calc_pnl_report=False)
            CF.cache_caracalla_port = out_dict
        else:
            out_dict = CF.cache_caracalla_port
        # Risk Factor Portfolio:
        port_rf = out_dict['rf_portfolio'].reset_index().drop('ddate', axis=1).set_index('risk_factor')
        # Risk Factor Series:
        rets_rf = out_dict['returns']

    # Get Risk Factor Table:
    if len(CF.cache_rf_map) == 0:
        rf_map = db.run_query('SELECT * FROM TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING', fmt_engine='RISK')
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

    # Get Yields:
    yield_series = df_stress_mtx[df_stress_mtx.stress_factor_unit == 'Yield'].drop_duplicates(subset=['stress_factor']).stress_factor
    if len(CF.cache_df_yields) == 0:
        df_yields = dtp.get_rf_returns(rf_list=list(yield_series), yield2tr=False)
        CF.cache_df_yields = df_yields
    else:
        df_yields = CF.cache_df_yields


    # Get Missing Series
    list_series = list(set(df_stress_mtx.stress_factor))
    list_series_missing = [j for j in list_series if j not in rets_rf.columns]
    if len(CF.cache_rets_missing) == 0:
        rets_missing = dtp.get_rf_returns(rf_list=list_series_missing)
        CF.cache_rets_missing = rets_missing
    else:
        rets_missing = CF.cache_rets_missing

    # Concatenate Returns:
    rets_stress_factors = pd.concat([rets_rf, rets_missing], axis=1).sort_index()

    # Build Weight Out of each not specifically stressed portfolio risk factor
    out_dict = dict()
    for scen in stress_scenarios:

        try:
            tmp_dict = dict()
            # Set Already Known Variables:
            forward_horizon = df_stress_mtx[df_stress_mtx.code == scen].shock_length.iloc[0]

            out_rets = pd.DataFrame()
            str_series_stress = df_stress_desc[df_stress_desc['code'] == scen].stress_scenario_parameter.iloc[0]
            list_stress = [k.split(' ')[0] for k in str_series_stress.split('|')]
            list_stress_missing = [j for j in rets_rf.columns if j not in list_stress]

            # Get Scenario Stress Factors which are already in Portfolio
            if list_stress != list_stress_missing:
                out_rets = rets_stress_factors[[j for j in list_stress if j in rets_stress_factors.columns]]
                out_rets = out_rets[[l for l in out_rets.columns if l in rets_rf.columns]]
                rets_ref_res = rets_rf[[k for k in rets_rf.columns if k not in out_rets.columns]]
            else:
                rets_ref_res = rets_stress_factors.copy()

            # Run Linear Regression for Missing Stress Factors on all Risk Factors
            out_reg = pd.DataFrame(index=list_stress, columns=rets_ref_res.columns)
            for stress_factor in list_stress:
                for risk_factor in rets_ref_res.columns:
                    tmp = rets_stress_factors[[stress_factor, risk_factor]].dropna()
                    X = sm.add_constant(tmp[stress_factor])
                    model_tmp = sm.OLS(tmp, X)
                    res = model_tmp.fit()
                    out_reg.loc[stress_factor, risk_factor] = res.params.loc[stress_factor].iloc[1]

            # Calc Total Beta:
            out_reg.loc['beta'] = out_reg.sum().T

            # Apply Beta's to Returns:
            out_rets = pd.concat([out_rets, rets_ref_res * out_reg.loc['beta'].values], axis=1).astype(float)

            # Evaluate Stressed Means:
            out_stressed_means = pd.DataFrame(index=list_stress, columns=['stressed_mean'])
            for stress_fac in list_stress:
                tmp = df_stress_mtx[(df_stress_mtx['stress_factor'] == stress_fac) & (df_stress_mtx['code'] == scen)]
                if tmp.stress_factor_unit.iloc[0] == 'Yield':
                    dict_dur_yields = {'ger_tsy_10y': 10, 'ger_tsy_3y': 3,
                                       'ita_tsy_10y': 10, 'ita_tsy_3y': 3,
                                       'us_tsy_10y': 10, 'us_tsy_3y': 3,
                                       'us_corp_hy': 4, 'us_corp_ig': 7}

                    tmp_yield = df_yields[stress_fac].dropna()
                    mean_yield_new = (np.mean(tmp_yield[-horizon:].diff()) + tmp.stress_mean.iloc[0])
                    out_stressed_means.loc[stress_fac, 'stressed_mean'] = -dict_dur_yields[stress_fac] * mean_yield_new
                else:
                    out_stressed_means.loc[stress_fac, 'stressed_mean'] = tmp.stress_mean.iloc[0]

            # Calc Total Stressed Means
            out_reg.loc['stressed_mean'] = (out_reg[:-1] * out_stressed_means.loc[list_stress].values).sum()
            out_reg = pd.concat([out_reg, out_stressed_means.loc[[k for k in out_stressed_means.index if k in rets_rf.columns]].T], axis=1)
            out_reg = out_reg[rets_rf.columns]
            tmp_dict['out_reg'] = out_reg

            out_rep, out_mean_distr, port_plot, port_plot_total = stress_test_primer(out_rets.dropna(),
                                                                                     port_rf.weight.values,
                                                                                     n_sim=1000,
                                                                                     stressed_means=np.array(out_reg.T.stressed_mean.tolist()),
                                                                                     forward_horizon=forward_horizon,
                                                                                     horizon=horizon,
                                                                                     scenario=scen)

            tmp_dict['out_rep'] = out_rep
            tmp_dict['out_mean_distr'] = out_mean_distr
            tmp_dict['port_plot'] = port_plot
            tmp_dict['port_plot_total'] = port_plot_total

            out_dict[scen] = tmp_dict
        except:
            pass

    return out_dict







def stress_test_primer(rets_orig, wgts, n_sim=1000, stressed_means=None,
                       forward_horizon=90, horizon=250, plot=True, scenario=None):
    """
    Primer for Stress Testing
    @return:
    """

    # Define OutPut
    out_dict = dict()

    # Run MonteCarlo Simulation with stressed means and with series means
    from risk_pylibrary.risk_models import mc_models

    # Slice Original Returns
    #rets = rets_orig[-horizon:].copy()
    rets = rets_orig.copy()

    # Run Simulations
    # Simulating without Stress:
    sim_ret, sim_ts = mc_models.mc_simulate(rets,
                                            n=n_sim,
                                            ewma_cov=False,
                                            distr='norm',
                                            sim_len=forward_horizon)
    # Simulating without stressed means:
    # stressed_means = rets.mean().values - 0.2 / forward_horizon
    # sim_ret_hist, sim_ts_hist = mc_models.mc_simulate(rets,
    #                                                   n=n_sim,
    #                                                   ewma_cov=False,
    #                                                   stress_means=stressed_means,
    #                                                   distr='norm',
    #                                                   sim_len=forward_horizon)

    # Simulating without covariance estimator:
    sim_rets_ml, sim_ts_ml = mc_models.mc_simulate(rets,
                                                   n=n_sim,
                                                   ewma_cov=False,
                                                   mlest_cov=True,
                                                   stress_means=stressed_means,
                                                   distr='norm',
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
    port_plot_total = pd.concat([pd.DataFrame(np.array(6 * [rets.dot(wgts.T).values.T]).T, columns=port_plot.columns),
                           port_plot], axis=0)

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
        CH.density_plot(out_mean_distr)

        #CH.perf_plot(((1+port_plot_total[-int(horizon/5):]).cumprod()*100), delta=None, tlt=scenario)
        CH.perf_plot(((1 + port_plot).cumprod() * 100), delta=None, tlt=scenario)

    return out_rep, out_mean_distr, port_plot, port_plot_total




def stress2db(out_dict, ddate):

    from datetime import timedelta
    out_db = pd.DataFrame()
    for idx in out_dict.keys():
        tmp = out_dict[idx]['port_plot']
        tmp = tmp.reset_index().drop('index', axis=1)
        tmp['ddate_fwd'] = pd.date_range(start=ddate, end=ddate + timedelta(len(tmp)-1))
        tmp = pd.melt(tmp, id_vars='ddate_fwd', var_name=['code'])
        tmp['account'] = 'caracalla'
        tmp['code'] = tmp['code'].apply(lambda x: idx+'_'+x)
        tmp['ddate'] = ddate
        tmp = tmp[['ddate', 'ddate_fwd', 'account', 'code', 'value']]

        # Capital Requirement Calculation
        tmp_cap_req = pd.DataFrame(index=(out_dict[idx]['port_plot_total'][-250:].std()*3.09*np.sqrt(30)*1.3).index,
                                   columns=tmp.columns)
        tmp_cap_req['ddate'] = tmp.ddate.max()
        tmp_cap_req['ddate_fwd'] = tmp.ddate_fwd.max()
        tmp_cap_req['account'] = 'caracalla'
        tmp_cap_req['value'] = out_dict[idx]['port_plot_total'][-250:].std()*3.09*np.sqrt(30)*1.3
        tmp_cap_req = tmp_cap_req.reset_index().drop(['code'], axis=1)
        tmp_cap_req = tmp_cap_req.rename(columns={'index':'code'})
        tmp_cap_req = tmp_cap_req[tmp.columns]
        tmp_cap_req['code'] = tmp_cap_req['code'].apply(lambda x: idx + '_' + 'capreq_' + x)
        out_db = pd.concat([out_db, tmp, tmp_cap_req], axis=0)

    return out_db


def credit_sample_data_import(pth):

    df = pd.read_csv(pth)
    for col in df.columns[5:6]:
        max_value = 0
        for item in df[col]:
            if not isinstance(item, float) and not isinstance(item, int):
                if len(item) > max_value:
                    max_value = len(item)
                    print(max_value)

        out.loc[col, 'col_len'] = max_value


def multiply_cols(df):

    df_new = df.copy()
    df_new['C'] = df_new['A'] + df_new['B']

    return df_new



def si_simulation():


    from tools.snowflake_db import db_connection as db


    # Import TRPT Trades
    qry_trpt = '''
        SELECT
            --anm_trade."executed_at" as executed_at,
            --anm_trade."executed_at"::date as ddate,
            IFF(anm_trade."group_id" IS NULL, 'id_null', anm_trade."group_id") as group_id,
            anm_trade."instrument_id" as instrument_id,
            anm_trade."exchange_id" as exchange_id,
            anm_trade."execution_price" as execution_price,
            anm_trade."execution_size" as quantity,
            anm_trade."execution_price" * anm_trade."execution_size" AS volume
        FROM
            BACKEND_PRD.PORTFOLIO.ANONYMIZED_TRADE as anm_trade
        WHERE
            anm_trade."executed_at"::DATE BETWEEN '2022-10-01' AND '2023-03-31'
        AND
            anm_trade."instrument_id"= 'KY30744W1070'
        AND
            anm_trade."exchange_id" in ('LSX', 'TRPT')
        AND
            anm_trade."sec_acc_no" <> '9800001301'
        ORDER BY 1
    '''

    df_trpt = db.run_query(query=qry_trpt)

    # Subset by grouping LSX + TRPT trades, which have a shared group_id. These are the fractional trades OTC trades
    df_ft = df_trpt[df_trpt.group_id != 'id_null'].iloc[:, [0, 1, -1]].groupby(['group_id', 'instrument_id']).sum()
    df_ft = df_ft.reset_index()

    # Subset of integer LSX trades
    df_int = df_trpt[df_trpt.group_id == 'id_null'][['group_id','instrument_id', 'volume']]

    # Combine
    df_tot = pd.concat([df_ft, df_int], axis=0)

    # Calculate SI Thresholds
    # OTC
    df_tot['otc_trades_L6M'] = 0
    df_tot['otc_trades_L6M'].loc[df_tot.group_id != 'id_null'] = 1
    df_tot['otc_trade_turnover_L6M'] = 0
    df_tot['otc_trade_turnover_L6M'].loc[df_tot.group_id != 'id_null'] = df_tot['volume'].loc[df_tot.group_id != 'id_null']
    # Total
    df_tot['total_trades_L6M'] = 1
    df_tot['total_trade_turnover_L6M'] = df_tot['volume']


    return df_tot


def pnl_trades(syms=['US6544453037'],startdate=None,enddate=None):

    from tools.snowflake_db import db_connection as db

    if startdate is None:
        startdate = date(2022,1,9)
    if enddate is None:
        enddate = _datetime.now().date()

    qry='''   
    -- Inventory Position
    SELECT
        CASE
            WHEN 
                SB.booking_category = 'CORPORATE_ACTION' --AND SB.BOOKING_TYPE = 'SPLIT' 
            THEN 
                SB.booking_date
            WHEN 
                SB.BOOKING_FUNCTION IN ('CANCEL','NEW') 
            THEN 
                COALESCE(ext_trade.execution_received, trade.execution_received, SB.booked_at_ts)
            ELSE 
                COALESCE(ext_trade.executed_at, trade.executed_at, SB.booked_at_ts)
        END AS calendar_date,
        SB.INSTRUMENT_ID AS instrument_id,
        SB.BOOKING_CATEGORY,
        SB.BOOKING_TYPE,
        SB.BOOKING_FUNCTION,
        SB.BOOKING_DIRECTION,
        IFF(SB.BOOKING_DIRECTION = 'CREDIT', 1, -1) * SB.NET_SIZE AS NET_SIZE
    FROM 
        TEAMS_PRD.TRANSFORM_SHARE_BOOKING.TRF__SHARE_BOOKING AS SB
    LEFT JOIN TEAMS_PRD.source_portfolio.src__portfolio__external_trade AS ext_trade 
                ON SB.external_trade_id = ext_trade.id -- for TR<>user trades
    LEFT JOIN 
        TEAMS_PRD.source_portfolio.src__portfolio__trade AS trade
            ON SB.trade_id = trade.id --for TR<>LSX trades
    WHERE
        1=1
    AND
        SB.SEC_ACC_NO = 9800001301
    AND
        SB.instrument_id in (%s)
    AND
        calendar_date BETWEEN %s AND %s
    ORDER BY 1;
    '''

    qry = qry%(db.joinpad(syms), db.sqldate(startdate), db.sqldate(enddate))
    df = db.run_query(query=qry)


    return df





def scroll(distance, duration):

    import pyautogui
    import math
    import time
    import keyboard
    import random

    center_x, center_y = pyautogui.position()  # Initial mouse position will be the center
    end_time = time.time() + duration

    while time.time() < end_time:
        if keyboard.is_pressed('esc'):  # Stop if the Escape key is pressed
            print("Execution halted.")
            break

        current_x, current_y = pyautogui.position()

        # Check if the mouse has moved significantly
        if abs(current_x - center_x) > 300 or abs(current_y - center_y) > 300:
            print("Mouse moved manually, restarting circle.")
            center_x, center_y = current_x, current_y
            angle = 0  # Reset angle

        random_value = random.random()
        pyautogui.scroll(random_value * distance)
        time.sleep(random_value * 45)
        pyautogui.scroll(-1 * random_value * distance)
        time.sleep(random_value * 98)

    # Example usage
    #move_in_circle(radius=100, duration=36000)



def distribute_per_column():

    import pandas as pd

    # Example DataFrame
    data = {'values': [10,15,20,25,30,35,40,45,50]}
    df_sort = pd.DataFrame(data)

    # Step 2: Calculate total occurrences
    sorted_values = sorted(df_sort['num_trades'], reverse=True)

    n_cores = 6
    # Initialize lists to hold values for each column
    col_list = [[] for _ in range(n_cores)]

    # Distribute values among columns

    out = pd.DataFrame(columns=['batch_%s'%str(k) for k in np.arange(0, n_cores)])
    for idx in df_sort.index:
        value_tmp = df_sort.loc[idx].iloc[0]
        sums = [sum(col) for col in col_list]
        min_sum_index = sums.index(min(sums))
        # Add Value to Columns List
        col_list[min_sum_index].append(value_tmp)
        # Add symbol to DataFrame Output
        out.loc[len(col_list[min_sum_index]), 'batch_%s'%str(min_sum_index)] = idx



    # Create a new DataFrame with the distributed values
    df_distributed = pd.DataFrame()
    count = 0
    for col in col_list:
        df_distributed = pd.concat([df_distributed, pd.DataFrame({'batch_%s'%str(count):col})], axis=1)
        count += 1

    return new_df



def get_esma_hyperlink():

    import requests

    url ='''https://registers.esma.europa.eu/solr/esma_registers_mifid_shsexs/select?q=({!parent%20which=%27type_s:parent%27})
    &fq=((((shs_modificationDate:[*%20TO%202024-02-29T23:59:59.000Z])%20AND%20(shs_modificationBDate:[2024-02-29T00:00:00.000Z%20TO%20*])
    %20AND%20!shs_status:Unchanged)%20OR%20((shs_modificationDate:[*%20TO%202024-02-29T23:59:59.000Z])%20AND%20
    (shs_modificationBDate:[2024-02-29T00:00:00.000Z%20TO%20*])%20AND%20(shs_modificationDate:[*%20TO%202024-02-29T23:59:59.000Z])
    %20AND%20(shs_modificationBDate:[2024-02-29T00:00:00.000Z%20TO%20*])%20AND%20shs_status:Unchanged))
    )%20AND%20(shs_countryCode:FR)&wt=xml&indent=true&rows=100000'''

    res=requests.get(url)



def read_rr_excels_0(a, verbose):


    import shutil
    import traceback

    try:
        fname_new = a.split('.')[0]+'_new.xlsx'
        shutil.copyfile(a, fname_new)
        if verbose:
            print('\n\tFile %s has been copied to %s'%(a, fname_new))
    except:
        print(traceback.format_exc())
        pass

    fname_new = fname_new.split('.')[0] + '_new.xlsx'

    return fname_new


def read_rr_excels_1(b, verbose):


    import shutil
    import traceback

    try:
        fname_new = b.split('.')[0]+'_new.xlsx'
        shutil.copyfile(b, fname_new)
        if verbose:
            print('\n\tFile %s has been copied to %s'%(b, fname_new))
    except:
        if verbose:
            print(traceback.format_exc())
        pass


def script_rr_copy(a, verbose=True):
    import pdb
    pdb.set_trace()
    if verbose:
        print('\n\n********* Ininitialising File Copy 1 *******')

    b = read_rr_excels_0(a, verbose)

    if verbose:
        print('\n\n********* Ininitialising File Copy 2 *******')

    read_rr_excels_1(b, verbose)



def data_ohlc_cleansing(df_orig, col, buffer, verbose=1):
    """
    Quantile range based cleaning Function with iqr (quantile 0.75 - quantile 0.25 range)

    @param df_orig: Unfiltered OHLC data
    @param col: column to filter, e.g. 'open'
    @param buffer: set multiplying factor for iqr.
    @param verbose: 1 or 0 for print messages
    @return: cleaned price OHLC, cleansing report
    """
    # Create Outputs
    out_prices = pd.DataFrame()
    out_report = pd.DataFrame(columns=[col], index=df_orig.ticker.unique())

    # Set Progress Counter
    len_tot = len(df_orig.ticker.unique())
    count = 1
    starttime = _datetime.now()


    for ticker in df_orig.ticker.unique():
        if verbose:
            if count % 500 == 0:
                print('Processed %s of %s tickers'%(count, len_tot))

        # Slice DataFrame
        df = df_orig[df_orig.ticker == ticker]
        # Set Boundaries
        q1 = np.quantile(df[col], 0.25)
        q3 = np.quantile(df[col], 0.75)
        iqr = q3-q1

        # Filter DataFrame
        # Lower Bound
        df_clean = df[~(df[col] < (q1-buffer*iqr))]
        # Upper Bound
        df_clean = df_clean[~(df_clean[col] > (q3+buffer*iqr))]

        # Append Results to Outputs
        out_prices = pd.concat([out_prices, df_clean], axis=0)
        out_report.loc[ticker, col] = len(df) - len(df_clean)

        # Adjust counter
        count += 1

    if verbose:
        print('Time elapsed: %s'%(_datetime.now() - starttime))


    return out_prices, out_report


def data_ohlc_cleansing_test(df_orig, columns_list, verbose=1):
    """
    Cleaning Function
    @param df_orig:
    @param verbose:
    @return:
    """
    # Create Outputs
    out_prices = pd.DataFrame()
    out_report = pd.DataFrame(columns=['open'], index=df_orig.ticker.unique())

    # Set Progress Counter
    starttime = _datetime.now()

    df=pd.pivot_table(df_orig[['window_start','ticker','open']],
                      index='window_start',
                      columns='ticker',
                      values='open',
                      aggfunc=np.mean)

    q1 = df.quantile(0.25)
    q3 = df.quantile(0.75)
    iqr = q3 - q1


    if verbose:
        print('Time elapsed: %s'%(starttime - _datetime.now()))


    return out_prices, out_report



def data_iqr_cleansing(df_orig, buffer, verbose=1):
    """
    Quantile range based cleaning Function with iqr (quantile 0.75 - quantile 0.25 range)

    @param df_orig: Unfiltered OHLC data
    @param buffer: set multiplying factor for iqr.
    @param verbose: 1 or 0 for print messages
    @return: cleaned price OHLC, cleansing report
    """
    # Create Outputs
    out_prices = pd.DataFrame(index=df_orig.index)
    out_report = pd.DataFrame(columns=['cleaned_records'], index=df_orig.columns)

    # Set Progress Counter
    len_tot = len(df_orig.columns)
    count = 1
    starttime = _datetime.now()


    for ticker in df_orig.columns:
        if verbose:
            if count % 500 == 0:
                print('Processed %s of %s tickers'%(count, len_tot))

        # Slice DataFrame
        df = df_orig[[ticker]]
        # Set Boundaries
        q1 = np.quantile(df[ticker], 0.25)
        q3 = np.quantile(df[ticker], 0.75)
        iqr = q3-q1

        # Filter DataFrame
        # Lower Bound
        df_clean = df[~(df[ticker] < (q1-buffer*iqr))]
        # Upper Bound
        df_clean = df_clean[~(df_clean[ticker] > (q3+buffer*iqr))]

        # Append Results to Outputs
        out_prices = pd.concat([out_prices, df_clean], axis=1)
        out_report.loc[ticker, 'cleaned_records'] = len(df) - len(df_clean)

        # Adjust counter
        count += 1

    # Fill Na with predecessor
    out_prices = out_prices.fillna(method='ffill')

    if verbose:
        print('Time elapsed: %s'%(_datetime.now() - starttime))


    return out_prices, out_report


def plot_black_model_interest_sensitvity(f_start, f_end, tau_start, tau_end, K, rf, direction, sigma, P, Dur, Conv, IRvola, y, verbose):


    # Define parameters for plotting
    F_range = np.linspace(f_start, f_end, 100)
    T_range = np.linspace(tau_start, tau_end, 100)

    # Calculate Black Model Call Duration over the ranges
    F_mesh,T_mesh = np.meshgrid(F_range, T_range)
    opt_ir_sens_values = np.zeros_like(F_mesh)

    for i in range(F_mesh.shape[0]):
        for j in range(F_mesh.shape[1]):
            F = F_mesh[i,j]
            tau = T_mesh[i,j]
            opt_ir_sens_values[i,j] = black_model_interest_sensitivity(F, K, P, rf, sigma, tau, direction, Dur, Conv, y, IRvola, verbose)

    # Plot the results
    fig_opt_ir_sens = plt.figure(figsize=(10,7))
    ax = fig_opt_ir_sens.add_subplot(111, projection='3d')
    ax.plot_surface(F_mesh, T_mesh, opt_ir_sens_values, cmap='viridis', edgecolor='none')
    ax.set_xlabel("Future Price")
    ax.set_ylabel("Maturity Time (years)")
    ax.set_zlabel("Option Interest Rate Sensitivity (Duration)")
    plt.title("Black Model %s Interest Rate Sensitivty"%direction)

    return fig_opt_ir_sens


def option_hedging():
    from numpy import array,arange,busday_count,cov,datetime64,exp,log,r_,sqrt,squeeze,zeros
    from scipy.stats import norm as normal
    from pandas import read_csv,to_datetime,Series
    from seaborn import histplot,kdeplot,lineplot,scatterplot

    db_call_data = read_csv('~/Databases/temporary-databases/db_call_data.csv',index_col=0,low_memory=False)
    m_bar = int(array(db_call_data['m_'].iloc[0]))  # upper limit of monitoring horizon
    t_m = array(to_datetime(db_call_data['t_m'].dropna().values.reshape(-1)),dtype='datetime64[D]')  # monitoring times
    t_end = datetime64(to_datetime(db_call_data['t_end'].iloc[0]),'D')  # call option expiry date
    k_strike = int(array(db_call_data['k_strike'].iloc[0]))  # call option strike
    y = array(db_call_data['y_rf'].iloc[0])  # risk-free yield for selected horizons
    sigma_t_now = db_call_data['log_sigma_atm'].iloc[0]  # interpolated log-implied volatility at money
    j_bar = int(array(db_call_data['j_'].iloc[0]))  # number of Monte Carlo simulations
    # simulated realizations of call option value over monitoring times
    v_call_m = array(db_call_data['v_call_thor'].iloc[:j_bar * (m_bar + 1)]).reshape((j_bar,(m_bar + 1)))
    # value of underlying for monitoring times
    v_stock_m = exp(array(db_call_data['log_s'].iloc[:j_bar * (m_bar + 1)]).reshape((j_bar,(m_bar + 1))))


    # 1. Compute Black-Scholes-Merton delta and Black-Scholes-Merton beta

    delta_t = busday_count(t_m[0],t_end) / 252  # time to expiry (years)
    sigma = exp(sigma_t_now)  # implied volatility
    delta_bsm = normal.cdf((log(v_stock_m[0,0] / k_strike) + \
                            (y + (sigma ** 2) / 2)) / (sigma * sqrt(delta_t)))  # Black-Scholes-Merton delta
    beta_bsm = delta_bsm * v_stock_m[0,0] / v_call_m[0,0]  # Black-Scholes-Merton beta


    # 2. Compute call option and stock linear returns and factors on demand beta for selected horizon, then compute factors on demand delta
    ########## input (you can change it) ##########
    m = 90  # hedging horizon (days)
    ###############################################

    r_call = (v_call_m[:,[m]] / v_call_m[:,[0]]) - 1  # call option linear return
    r_stock = (v_stock_m[:,[m]] / v_stock_m[:,[0]]) - 1  # stock linear return
    r = r_['-1',r_call,r_stock]  # combined linear returns
    cv = cov(r.T)  # covariance of linear return
    beta_fod = cv[0,1] / cv[1,1]  # factors on demand beta
    delta_fod = beta_fod * v_call_m[0,0] / v_stock_m[0,0]  # factors on demand delta


    # 3. Compute return of Black-Scholes-Merton hedged portfolio and factors on demand hedged portfolio

    r_bsm = r_call - beta_bsm * r_stock  # return of Black-Scholes-Merton hedged portfolio
    r_fod = r_call - beta_fod * r_stock  # return of factors on demand hedged portfolio

    ############################# plot #############################
    # repriced call option return
    histplot(r_call.flatten(),bins=100,kde=False,stat='density')
    kdeplot(Series(r_bsm.flatten()),c='r',label='BSM hedged pdf')
    kdeplot(Series(r_fod.flatten()),c='b',label='FOD hedged pdf');

    # 4. Compute Black-Scholes-Merton call option value and payoff as functions of underlying and compute current value of call option

    ############## input (you can change it) ##############
    s = arange(600,1801)  # range of values for underlying
    #######################################################

    # compute Black-Scholes-Merton call option value and payoff
    c_bs_curve = zeros(len(s))
    c_bs_payoff = zeros(len(s))
    for l in range(len(s)):
        # range of call option values
        d_1 = (log(s[l] / k_strike) + (y + (sigma ** 2) / 2) * delta_t) / (sigma * sqrt(delta_t))
        d_2 = d_1 - sigma * sqrt(delta_t)
        c_bs_curve[l] = s[l] * normal.cdf(d_1) - k_strike * exp(-y * delta_t) * normal.cdf(d_2)
        # range of payoff values
        c_bs_payoff[l] = (s[l] - k_strike) * int(k_strike <= s[l]) + 0 * int(k_strike >= s[l])

        # current value of call option
    d_1 = (log(v_stock_m[0,0] / k_strike) + (y + (sigma ** 2) / 2) * delta_t) / (sigma * sqrt(delta_t))
    d_2 = d_1 - sigma * sqrt(delta_t)
    c_bs_curve_current = v_stock_m[0,0] * normal.cdf(d_1) - k_strike * exp(-y * delta_t) * normal.cdf(d_2)

    ######################################################## plot ########################################################
    # Black-Scholes-Merton vs factors on demand
    scatterplot(x=v_stock_m[:,m],y=v_call_m[:,m],label='Call option values')
    lineplot(x=s,y=c_bs_curve.flatten(),label='BSM call option value')
    lineplot(x=[v_stock_m[0,0]],y=c_bs_curve_current,marker='.',markersize=15,label='BSM call option current value')
    lineplot(x=s,y=squeeze(c_bs_curve_current + delta_bsm * (s - v_stock_m[0,0])),label='BSM hedge')
    lineplot(x=s,y=squeeze(c_bs_curve_current + delta_fod * (s - v_stock_m[0,0])),label='FoD hedge')
    lineplot(x=s,y=c_bs_payoff.flatten());
