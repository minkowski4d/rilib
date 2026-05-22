#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Python Modules
import numpy as np
import os
from numpy.linalg import inv
from scipy import stats as si
from scipy.optimize import minimize

import pandas as pd
from tools import utils as ut
from tools import charting as CH


def WB(Y, p = 0.015, ff = 1, hori = 252):
    """
    Program for the Block Bootstrap on the series Y via defined block size
    input: Y Series of dimension (T*N)sim2
           p size of the block; values from 0, 1; block size is equal to 1/p
           ff serves to have a fixed minimum size in the sampled data, i.e.
           resample weeks or months. if ff is one, then it starts by days (default)
           hori is the size of the resampled data S.
    """
    T, N = Y.shape

    LL = []  #LL variable will contain the length of each block
    S = np.zeros((hori, N))  #S contains the sample
    k = 0
    while k < hori:
        I = np.int(np.ceil(T*np.random.rand(1)))
        L = np.int(np.random.geometric(p))
        if k + L > hori: L = hori - k
        LL.append(L)
        #if I want to fix a frequency
        L = L - np.mod(L, ff)
        if I + L <= T:
            S[k:k + L, :] = Y[I:I + L, :]
        else:
            hj = I + L - T
            S[k:k + L - hj, :] = Y[I:T, :]
            S[k + L - hj + 1:k + L, :] = Y[1:hj, :]
        k = k + L
    return S, LL


def sim2rets(sim, retfreq = 1):
    m = sim.index.min()[1]
    return sim.pct_change(periods = retfreq).query("time_id>=%i"%(retfreq + m)).loc(axis = 0)[:, ::retfreq]


def sim2VaR(sim, p, h, calc_rets=False):
    if calc_rets:
        rets = sim2rets(sim, h)
        scale_t = 1
    else:
        rets = sim
        scale_t = np.sqrt(h)

    return rets.groupby("sim_id").quantile(1-p) * scale_t


def sim2cagr(sim, yd = 1440):
    rets = 1. + sim2TR(sim)
    rets = rets.applymap(lambda x: x ** (float(yd)/float(len(sim.index.levels[1]))) - 1.)
    return rets.astype(float)


def sim2TR(sim):
    min_t = sim.index.min()[1]
    max_t = sim.index.max()[1]
    rets = sim.loc(axis = 0)[:, (min_t, max_t)].pct_change().loc(axis = 0)[:, max_t]
    rets.index = rets.index.droplevel(1)
    return rets


def sim2vol(sim, retfreq = 5, calc_rets = True):
    factor = 260./retfreq
    if calc_rets:
        vols = sim2rets(sim, retfreq).groupby("sim_id").std()*np.sqrt(factor)
    else:
        vols = sim.groupby("sim_id").std()*np.sqrt(factor)
    return vols


def sim2MDD(sim):
    mdd_out = pd.DataFrame()

    print('Calculation in progress...')
    pb = ut.ProgressBar(len(sim.index.get_level_values(0).unique()))
    for i in range(0, max(sim.index.get_level_values(0))):
        temp = sim.loc[i]
        mdd_out.loc[i, sim.columns[0]] = -1*max((1 - temp/temp.cummax()).values)[0]
        # mdd = 0
        # for j in range(1, temp.shape[0]):
        #     peak = temp.iloc[:j].max().iloc[0]
        #     ip = temp.iloc[:j].idxmax().iloc[0]
        #     through = temp.loc[ip:].min().iloc[0]
        #     if through / peak - 1 < mdd:
        #         mdd = through / peak - 1

        # mdd_out.loc[i,sim.columns[0]]=mdd
        pb.animate(i)

    return mdd_out


def sim2sharpe(sim):
    #if len(sim)>252: raise Exception("Adjust code. Sharpe2Sim works on 252 observations max")
    shr_out = pd.DataFrame()
    for i in range(0, max(sim.index.get_level_values(0))):
        temp = sim.loc[i].pct_change().dropna()
        shr = (temp.mean()*len(temp))/(temp.std()*np.sqrt(len(temp)))
        shr_out.loc[i, 'Sharpe Ratio'] = shr.iloc[0]

    return shr_out


def sim2ts(ts_sim, wgts, verbose = False):
    sim_rets = sim2rets(ts_sim)
    out = pd.DataFrame(index = [0] + sim_rets.index.get_level_values(1).unique().tolist(),
                       columns = sim_rets.index.get_level_values(1).unique())
    for idx in sim_rets.index.get_level_values(0).unique():
        if idx%500 == 0 and verbose: print(idx)
        out[idx] = np.append([100], (1 + np.dot(sim_rets.loc[idx], wgts)).cumprod()*100)

    return out


def lpm(rets, threshold, order):
    threshold_array = np.empty(len(rets))
    threshold_array.fill(threshold)
    diff = threshold_array - rets.values
    diff = diff.clip(min = 0)
    return np.sum(diff ** order)/len(rets)


def hpm(rets, threshold, order):
    threshold_array = np.empty(len(rets))
    threshold_array.fill(threshold)
    diff = rets.values - threshold_array
    diff = diff.clip(min = 0)

    return np.sum(diff ** order)/len(rets)


def rolling_drawdown(df):

    out_dict = dict()
    run_mdd = pd.DataFrame(index = df.index)
    for col in df.columns:
        run_mdd['%s_run_mdd'%col] = df[col]/df[col].cummax() - 1

    out_dict['run_mdd'] = run_mdd

    # Calculate Max DrawDown
    out_dict['mdd'] = run_mdd.min().iloc[0]

    # Calculate Drawdown Length
    mdd_max_day = run_mdd.index[np.argmin(run_mdd.values)]
    peak_prior_max_mdd = run_mdd[run_mdd.values == 0][:mdd_max_day].index[-1]
    mdd_end = run_mdd.loc[mdd_max_day:].ne(0).idxmin()[0]
    out_dict['ddl'] = (mdd_max_day - peak_prior_max_mdd).days
    # Calculate Time To Recover:
    out_dict['t2r'] = (mdd_end - mdd_max_day).days

    return out_dict


def running_sharpe(df):
    ad = df.index_freq()  # average day length of returns
    ann = 365/ad  # for annualizing returns
    sqann = (365/ad) ** 0.5
    df.index.name = 'index'
    df = df.pct_change().reset_index().dropna()
    out = pd.DataFrame(index = list(range(1, len(df))), columns = ['ddate', 'run_shr'])
    for idx, row in df.iterrows():
        temp = df.loc[df['index'] <= row['index']]
        out.loc[idx, 'ddate'] = temp.loc[idx, 'index']
        if len(temp) >= 252:
            out.loc[idx, 'run_shr'] = ((temp.mean()*ann)/(temp.std()*sqann))[0]
        else:
            out.loc[idx, 'run_shr'] = np.nan

    return out.set_index('ddate')


def lsq(y, x, add_constant = True, stats = False):
    """
    quick and simple least squares implementation without relying on external packages
    """
    if add_constant:
        x = np.c_[np.ones(x.shape[0]), x]
    inv_xx = inv(np.dot(x.T, x))
    xy = np.dot(x.T, y)
    b = np.dot(inv_xx, xy)
    out = np.empty((3, x.shape[1]))

    out[0, :] = b
    if stats:
        df_e = y.shape[0] - x.shape[1]
        e = y - np.dot(x, b)
        sse = np.dot(e, e)/df_e
        out[2, :] = np.diagonal(sse*inv_xx)
        se = np.sqrt(out[2, :])
        with np.errstate(divide = 'ignore', invalid = 'ignore'):
            out[1, :] = b/se
        return out
    else:
        return out[0, :]


def option_delta(S, K, T, sigma, direction, rf, verbose = False):
    """
    Greeks Ouput
    :param S: Spot Price
    :param K: Strike Price
    :param T: Maturity in Days
    :param sigma: Volatility Underlying
    :param direction: call or put
    :param rf: RiskFree rate.
    :param verbose: print msgs
    :return:
    """

    import numpy as np
    import scipy.stats as si

    d1 = (np.log(S/K) + (rf + 0.5*sigma ** 2)*T/365)/(sigma*np.sqrt(T/365))
    if verbose: print(d1, S, K, T, sigma, direction)
    if direction == 'call':
        delta = si.norm.cdf(d1, 0, 1)
    if direction == 'put':
        delta = -si.norm.cdf(-d1, 0, 1)

    return delta


def option_price(S, K, T, sigma, direction, rf, verbose = False):
    from math import exp, log, sqrt

    d1 = (np.log(S/K) + (rf + 0.5*sigma ** 2)*T/365)/(sigma*np.sqrt(T/365))
    d2 = (np.log(S/K) + (rf - 0.5*sigma ** 2)*T/365)/(sigma*np.sqrt(T/365))

    if verbose: print(S, K, T, sigma, rf, direction)
    if direction == 'call':
        price = (S*si.norm.cdf(d1, 0.0, 1.0) - K*np.exp(-rf*T/365)*si.norm.cdf(d2, 0.0, 1.0))
    elif direction == 'put':
        price = (K*np.exp(-rf*T/365)*si.norm.cdf(-d2, 0.0, 1.0) - S*si.norm.cdf(-d1, 0.0, 1.0))

    return price


def rolling_corr(rets, window, x):
    df = rets.copy().loc[:, [x] + [l for l in rets.columns if l != x]]
    roll_corr = pd.DataFrame(index = df.index[window:], columns = df.columns)
    for k in range(window, len(df)):
        roll_corr.loc[df.index[k]] = df[k - window:k].corr().iloc[0]

    return roll_corr



def rolling_sharpe(rets, window):
    df = rets.copy()
    roll_sharpe = pd.DataFrame(index = df.index[window:], columns = df.columns)
    for k in range(window, len(df)):
        roll_sharpe.loc[df.index[k]] = df[k - window:k].shr()

    return roll_sharpe


def rolling_ret(ts, window):
    df = ts.copy()
    roll_ret = pd.DataFrame(index = df.index[window:], columns = df.columns)
    for k in range(window, len(df)):
        roll_ret.loc[df.index[k]] = df[k - window:k].ret().iloc[0]

    return roll_ret


def sim2cov(rets_sim):
    covs = rets_sim.groupby("sim_id").cov()
    covs = covs*250

    return covs




# def sim2beta(rets_sim, qtl, verbose = True):
#     out_beta = pd.DataFrame(columns = ['beta'])
#     for i in rets_sim.index.get_level_values(0).unique():
#         if i%250 == 0 and verbose: print(i)
#         tmp_res = ri.quantile_reg_sim(rets_sim.loc[i], qtl = qtl)
#         out_beta.loc[i, 'beta'] = tmp_res.params.iloc[1]
#
#     return out_beta


def qq_plot_dataset(rets, startdate=None, enddate=None):

    rets_qq = rets.copy()
    if startdate: rets_qq = rets_qq[startdate:]
    if enddate: rets_qq = rets_qq[:enddate]

    rets_qq = rets_qq.fillna(0)
    out_qq = pd.DataFrame(columns = ['norm_qtl']+[k for k in rets.columns])
    out_qq['norm_qtl'] = si.probplot(rets_qq.iloc[:, 0].values, dist = "norm", fit = False, plot = None)[0]
    out_qq = out_qq.set_index('norm_qtl')
    for col in rets.columns:
        tmp = si.probplot(rets_qq[col].values, dist = "norm", fit = False, plot = None)
        out_qq[col] = tmp[1]

    return out_qq



def alloc_frontier(rets, len_sim=5000, leverage=[0, 1], randomizer = 'uniform', plot=False, pth='/Users/fabioballoni/Downloads'):
    """
    Efficient Frontier Simulation

    @param rets: DataFrame of Returns
    @param len_sim: number of iterations
    @param leverage: normalisation factor
    @return:
    """

    import random

    covariances = rets.cov() * 250
    risk_all = np.array([])
    return_all = np.array([])
    weights_all = pd.DataFrame(index=range(0,len_sim),columns=range(0,len(rets.columns)))
    for k in range(len_sim):
        if k % 5000 == 0:
            print(k)
        weights = []

        if randomizer == 'uniform':
            for l in range(1, len(rets.columns)+1):
                if l == len(rets.columns)+1:
                    pass
                else:
                    weights.append(random.uniform(leverage[0],leverage[1]))

            # Normalize
            weights_out = weights / np.sum(weights)

        elif randomizer == 'dirichlet':
            weights_out = np.random.dirichlet(np.ones(len(rets.columns)), size=1)[0]

        elif randomizer == 'random':
            weights = np.random.random(len(rets.columns))
            weights_out = weights / np.sum(weights)


        # Calculate Risk
        risk = _portfolio_risk(weights_out, covariances)
        ret = _portfolio_return(weights_out, rets)
        risk_all = np.append(risk_all, risk)
        return_all = np.append(return_all, ret)
        weights_all.loc[k] = weights_out

    # Prepare Output
    out = dict()
    out['risk_all'] = risk_all
    out['return_all'] = return_all
    out['weights_all'] = weights_all

    if plot:
            plot_markowitz = pd.DataFrame()
            plot_markowitz['Volatility exAnte'] = out['risk_all'] * 100
            plot_markowitz['Returns'] = out['return_all'] * 100
            plot_markowitz['Sharpe Ratio'] = out['return_all'] / out['risk_all']

            CH.style.use('seaborn-white')
            fig, ax = CH.subplots()
            plot_markowitz.plot.scatter(ax=ax,x='Volatility exAnte', y='Returns', c='Sharpe Ratio',
                                        cmap='YlGnBu', edgecolors='black', figsize=(10, 8), grid=True)
            #ax.scatter(100*max_shr_vol, 100*max_shr_ret, marker='x', color='r', s=200, label='Maximum Sharpe Ratio')
            CH.xlim(left=0)
            y_low_factor = 1.05 if plot_markowitz['Returns'].min() < 0 else 0.95
            y_high_factor = 1.05 if plot_markowitz['Returns'].max() > 0 else 0.95
            CH.ylim(bottom=y_low_factor * plot_markowitz['Returns'].min(), top=y_high_factor*plot_markowitz['Returns'].max())
            CH.xlabel('Volatility exAnte (Std. Deviation)')
            CH.ylabel('Expected Returns')
            CH.title('Efficient Frontier')
            fig.savefig(os.path.join(pth,'efficient_frontier_%s.jpeg'%len_sim))
            CH.show()



    return risk_all, return_all, weights_all


def _portfolio_risk(init_wgts,covariances):

    weights = np.matrix(init_wgts)
    vol_exante = np.sqrt(np.dot(weights,np.dot(covariances,weights.T)))


    return vol_exante.tolist()[0][0]


def _portfolio_return(init_wgts,rets):

    weights = np.matrix(init_wgts)
    portfolio_return = np.dot(weights, rets.mean()*250)
    return portfolio_return.tolist()[0][0]


def _neg_sharpe_ratio(wgts,rets, covariances):

    p_ret=_portfolio_return(wgts,rets)
    p_vol=_portfolio_risk(wgts,covariances)
    neg_shr=-1* p_ret/p_vol

    return neg_shr

def _max_risk(wgts,rets):

    """
    Parametric Calculation of risk
    """
    p_vol_ann = -1 * _portfolio_risk(wgts, rets.cov()*250)

    return p_vol_ann


def _get_target_vol(rets, target_vol=0.1):
    """

    @param rets:
    @return:
    """

    num_assets = len(rets.columns)
    args = (rets.cov() * 250)
    cons = (
        # Sum of weights must equate to 1
        {'type': 'eq','fun': lambda w: np.sum(w) - 1},

        # Difference between expected return and target must be equal to 0.
        {'type': 'eq','fun': lambda x: _portfolio_risk(x, rets.cov() * 250) - target_vol})

    bounds = tuple((0,1) for i in range(num_assets))
    init_wgts = num_assets * [1 / num_assets]
    optimize_result = minimize(_portfolio_risk, init_wgts, args=args, method='SLSQP', bounds=bounds, constraints=cons)

    # Recover the weights from the optimised object
    weights = optimize_result.x

    pf_rets = _portfolio_return(weights, rets)
    pf_vol = _portfolio_risk(weights, rets.cov()*250)
    pf_shr = pf_rets/pf_vol

    print('Sharpe Ratio: ', pf_shr)
    print('Return: ', pf_rets)
    print('Volatility (ann.): ', pf_vol)

    return weights


def simulate_ptf_ef(prx, n_sim=100, y_lim=[None, 0.02]):

    from pypfopt.expected_returns import mean_historical_return
    from pypfopt.risk_models import CovarianceShrinkage
    from pypfopt.efficient_frontier import EfficientFrontier
    from pypfopt import objective_functions
    from pypfopt import plotting
    import matplotlib.pyplot as plt

    mu = mean_historical_return(prx)
    S = CovarianceShrinkage(prx).ledoit_wolf()

    ef = EfficientFrontier(mu, S, weight_bounds=(0,None))
    #ef.efficient_return(target_return=0.,market_neutral=True)
    ef.add_constraint(lambda w: w[0] <= 0.8)

    fig,ax = plt.subplots()
    ef_max_sharpe = ef.deepcopy()
    plotting.plot_efficient_frontier(ef, ax=ax, show_assets=False)

    # Find the tangency portfolio
    ef_max_sharpe.max_sharpe(risk_free_rate=0)
    ret_tangent,std_tangent,_ = ef_max_sharpe.portfolio_performance()
    ax.scatter(std_tangent, ret_tangent,marker="*", s=50, c="r", label="Max Sharpe")

    # Generate random portfolios
    w = np.random.dirichlet(np.ones(ef.n_assets), n_sim)
    ef_plot = pd.DataFrame()
    ef_plot['Returns'] = w.dot(ef.expected_returns)
    ef_plot['Volatility exAnte'] = np.sqrt(np.diag(w @ ef.cov_matrix @ w.T))
    ef_plot['Sharpe Ratio'] = ef_plot['Returns'] / ef_plot['Volatility exAnte']
    ef_plot.plot.scatter(ax=ax,x='Volatility exAnte',y='Returns',c='Sharpe Ratio',
                                cmap='YlGnBu',edgecolors='black',figsize=(10,8),grid=True)


    # Format
    plt.ylim((ef_plot['Returns'].min() * 1.25 if ef_plot['Returns'].min() < 0 else 0) if y_lim[0] is None else y_lim[0],
             (ef_plot['Returns'].max() * 1.25 if ef_plot['Returns'].max() > 0 else 0) if y_lim[1] is None else y_lim[1])

    plt.xlim(ef_plot['Volatility exAnte'].min() * 0.75, ef_plot['Volatility exAnte'].max() * 1.25)
    ax.set_title("Efficient Frontier with Random Portfolios")
    ax.legend(loc='best')
    ax.grid(which='major', color='grey', linestyle='-', alpha=0.6)
    plt.tight_layout()
    plt.savefig('/Users/fabioballoni/Downloads/ef_scatter.jpeg',dpi=200)
    plt.show()




def qq_plot_dataset(rets, startdate=None, enddate=None, plot=False):
    """
    Docstring for qq_plot_dataset

    :param rets: Description
    :param startdate: Description
    :param enddate: Description
    :param plot: Description
    """
    from scipy.stats import norm

    rets_qq = rets.copy()
    if startdate: rets_qq = rets_qq[startdate:]
    if enddate: rets_qq = rets_qq[:enddate]

    rets_qq = rets_qq.fillna(0)
    out_qq = pd.DataFrame(columns = ['norm_qtl']+[k for k in rets.columns])
    out_qq['norm_qtl'] = si.probplot(rets_qq.iloc[:, 0].values, dist = "norm", fit = False, plot = None)[0]

    # Add empirical quantile positions
    n = len(out_qq)
    out_qq['empirical_qtl'] = np.linspace(1/(n+1), n/(n+1), n)

    # Populate return data columns
    for col in rets.columns:
        tmp = si.probplot(rets_qq[col].values, dist = "norm", fit = False, plot = None)
        out_qq[col] = tmp[1]

    # Insert rows at exact key quantile levels
    key_quantiles = [0.001, 0.01, 0.99, 0.999]
    new_rows = []

    for qtl in key_quantiles:
        row_data = {'empirical_qtl': qtl, 'norm_qtl': norm.ppf(qtl)}
        # Calculate actual quantile values for each return column
        for col in rets.columns:
            row_data[col] = rets_qq[col].quantile(qtl)
        new_rows.append(row_data)

    # Append new rows and sort by empirical_qtl
    out_qq = pd.concat([out_qq, pd.DataFrame(new_rows)], ignore_index=True)
    out_qq = out_qq.sort_values('empirical_qtl').reset_index(drop=True)
    out_qq = out_qq.set_index('norm_qtl')

    if plot:
        fig_qq=CH.qq_plot(out_qq)
        return out_qq, fig_qq
    else:
        return out_qq


def qq_plot_3d(rets, window_lengths=None, index=None, column=None, plot_type='surface', wireframe=False, startdate=None, enddate=None):
    """
    Creates a 3D surface or contour plot of QQ data with sample length as third dimension.

    :param rets: DataFrame of returns
    :param window_lengths: List of window lengths to analyze. If None, uses [50, 100, 250, 500, 1000] or max available
    :param index: Y-axis variable: 'norm_qtl' (default) for theoretical normal quantiles, 'empirical_qtl' for empirical quantiles
    :param column: Column name to analyze. If None, uses first column
    :param plot_type: 'surface' for 3D surface plot, 'contour' for 2D contour plot
    :param wireframe: If True, shows mesh grid lines on surface plot (default: False)
    :param startdate: Optional start date filter
    :param enddate: Optional end date filter
    :return: matplotlib figure object
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from scipy.stats import norm

    # Set default index type
    if index is None:
        index = 'norm_qtl'

    # Prepare data
    rets_work = rets.copy()
    if startdate: rets_work = rets_work[startdate:]
    if enddate: rets_work = rets_work[:enddate]

    # Select column
    if column is None:
        column = rets_work.columns[0]

    # Set default window lengths
    max_len = len(rets_work)
    if window_lengths is None:
        window_lengths = [w for w in [50, 100, 250, 500, 1000, 2000] if w <= max_len]
        if not window_lengths:
            window_lengths = [max_len]

    # Collect QQ data for each window length
    qq_data_collection = []

    for window in window_lengths:
        rets_window = rets_work[[column]].iloc[-window:]
        rets_clean = rets_window.fillna(0)

        # Calculate QQ plot points
        qq_result = si.probplot(rets_clean[column].values, dist="norm", fit=False)
        n = len(qq_result[0])

        # Calculate empirical quantiles
        empirical_qtls = np.linspace(1/(n+1), n/(n+1), n)

        for norm_qtl, empirical_val, emp_qtl in zip(qq_result[0], qq_result[1], empirical_qtls):
            qq_data_collection.append({
                'window_length': window,
                'norm_qtl': norm_qtl,
                'empirical_qtl': emp_qtl,
                'empirical_value': empirical_val
            })

    # Convert to DataFrame
    df_3d = pd.DataFrame(qq_data_collection)

    # Create a common grid for interpolation that respects actual data ranges
    if index == 'empirical_qtl':
        # Use the range that covers all windows properly
        min_qtl = df_3d['empirical_qtl'].min()
        max_qtl = df_3d['empirical_qtl'].max()
        common_index = np.linspace(min_qtl, max_qtl, 100)
    else:
        common_index = np.linspace(df_3d['norm_qtl'].min(), df_3d['norm_qtl'].max(), 100)

    # Interpolate data onto common grid for each window length
    interpolated_data = []
    for window in window_lengths:
        df_window = df_3d[df_3d['window_length'] == window].sort_values(index)

        # Interpolate empirical values onto common grid with bounds_error=False to preserve extremes
        # Use fill_value to extend with actual min/max values
        interpolated_values = np.interp(common_index,
                                         df_window[index].values,
                                         df_window['empirical_value'].values,
                                         left=df_window['empirical_value'].values[0],
                                         right=df_window['empirical_value'].values[-1])

        for idx_val, emp_val in zip(common_index, interpolated_values):
            interpolated_data.append({
                'window_length': window,
                index: idx_val,
                'empirical_value': emp_val
            })

    # Create DataFrame from interpolated data
    df_interpolated = pd.DataFrame(interpolated_data)

    # Pivot for plotting
    pivot_data = df_interpolated.pivot_table(values='empirical_value',
                                               index=index,
                                               columns='window_length')

    # Fill any remaining NaNs (should be rare with interpolation)
    pivot_data = pivot_data.ffill(axis=0).bfill(axis=0)
    pivot_data = pivot_data.ffill(axis=1).bfill(axis=1)

    # Create meshgrid
    X = pivot_data.columns.values  # window lengths
    Y = pivot_data.index.values     # selected index (norm_qtl or empirical_qtl)
    X_mesh, Y_mesh = np.meshgrid(X, Y)
    Z = pivot_data.values

    # Ensure no NaNs remain in Z for clean plotting
    if np.any(np.isnan(Z)):
        Z = np.nan_to_num(Z, nan=np.nanmean(Z))

    # Set labels based on index choice
    if index == 'empirical_qtl':
        y_label = 'Empirical Quantile'
        title_suffix = '(Empirical Quantile Scale)'
    else:
        y_label = 'Theoretical Normal Quantile'
        title_suffix = '(Normal Quantile Scale)'

    # Create plot
    if plot_type == 'surface':
        from matplotlib.ticker import PercentFormatter

        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Adjust subplot position to prevent label clipping
        fig.subplots_adjust(left=0.05, right=0.95, bottom=0.1, top=0.95)

        # Configure wireframe display
        if wireframe:
            surf = ax.plot_surface(X_mesh, Y_mesh, Z*100, cmap='viridis', alpha=0.8,
                                    edgecolor='black', linewidth=0.3, antialiased=True)
        else:
            surf = ax.plot_surface(X_mesh, Y_mesh, Z*100, cmap='viridis', alpha=0.8,
                                    edgecolor='none', linewidth=0, antialiased=True)

        ax.set_xlabel('Sample Length', fontsize=10, labelpad=10)
        ax.set_ylabel(y_label, fontsize=10, labelpad=10)
        ax.set_zlabel('Empirical Value (%)', fontsize=10, labelpad=10)
        ax.set_title(f'QQ Plot 3D Surface: {column} {title_suffix}', fontsize=12, pad=20)

        # Format Z-axis as percentage
        ax.zaxis.set_major_formatter(PercentFormatter())

        cbar = fig.colorbar(surf, shrink=0.5, aspect=5, pad=0.1)
        cbar.ax.yaxis.set_major_formatter(PercentFormatter())

    elif plot_type == 'contour':
        from matplotlib.ticker import PercentFormatter

        fig, ax = plt.subplots(figsize=(12, 8))

        contour = ax.contourf(X_mesh, Y_mesh, Z*100, levels=20, cmap='viridis')
        ax.contour(X_mesh, Y_mesh, Z*100, levels=20, colors='black', alpha=0.3, linewidths=0.5)

        ax.set_xlabel('Sample Length', fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        ax.set_title(f'QQ Plot Contour: {column} {title_suffix}', fontsize=14)

        cbar = fig.colorbar(contour, label='Empirical Value (%)')
        cbar.ax.yaxis.set_major_formatter(PercentFormatter())
        ax.grid(True, alpha=0.3)

    plt.tight_layout(pad=2.0)

    return fig


def var_stability_analysis(rets, column=None, window=250, qtl=0.01, plot_type='combined', startdate=None, enddate=None):
    """
    Analyzes and visualizes the impact of extreme returns on Historical Simulation VaR stability.

    :param rets: DataFrame of returns
    :param column: Column name to analyze. If None, uses first column
    :param window: Rolling window length for VaR calculation
    :param qtl: VaR quantile (e.g., 0.01 for 99% VaR)
    :param plot_type: 'combined' for multi-panel view, 'heatmap' for window composition, 'sensitivity' for VaR vs worst return
    :param startdate: Optional start date filter
    :param enddate: Optional end date filter
    :return: matplotlib figure object
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle

    # Prepare data
    rets_work = rets.copy()
    if startdate: rets_work = rets_work[startdate:]
    if enddate: rets_work = rets_work[:enddate]

    if column is None:
        column = rets_work.columns[0]

    rets_series = rets_work[column].fillna(0)

    # Calculate rolling VaR and track worst return in each window
    rolling_var = []
    rolling_worst = []
    rolling_dates = []

    for i in range(window, len(rets_series)):
        window_data = rets_series.iloc[i-window:i]
        var_value = window_data.quantile(qtl)
        worst_value = window_data.min()

        rolling_var.append(-var_value)  # Convention: positive VaR
        rolling_worst.append(-worst_value)
        rolling_dates.append(rets_series.index[i])

    # Create DataFrame for easier manipulation
    df_results = pd.DataFrame({
        'date': rolling_dates,
        'var': rolling_var,
        'worst_in_window': rolling_worst,
        'return': rets_series.iloc[window:].values
    })

    # Identify extreme events (returns worse than 2x the mean VaR)
    extreme_threshold = 2 * df_results['var'].mean()
    extreme_returns = rets_series[rets_series.abs() > extreme_threshold]

    if plot_type == 'combined':
        fig = plt.figure(figsize=(16, 12))

        # Panel 1: VaR over time with returns
        ax1 = plt.subplot(3, 1, 1)
        ax1_twin = ax1.twinx()

        # Plot returns as bars
        colors = ['red' if x < 0 else 'green' for x in df_results['return']]
        ax1_twin.bar(df_results['date'], df_results['return'], alpha=0.3, color=colors, width=1)
        ax1_twin.set_ylabel('Daily Returns', fontsize=10, color='gray')
        ax1_twin.tick_params(axis='y', labelcolor='gray')

        # Plot VaR
        ax1.plot(df_results['date'], df_results['var'], color='darkred', linewidth=2, label=f'{int((1-qtl)*100)}% VaR')
        ax1.set_ylabel(f'{int((1-qtl)*100)}% VaR', fontsize=10, color='darkred')
        ax1.set_title(f'Historical Simulation VaR Stability: {column}', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')

        # Mark extreme events
        for date in extreme_returns.index:
            if date in df_results['date'].values:
                ax1.axvline(date, color='orange', alpha=0.5, linestyle='--', linewidth=1)

        # Panel 2: VaR vs Worst Return in Window
        ax2 = plt.subplot(3, 1, 2)
        scatter = ax2.scatter(df_results['worst_in_window'], df_results['var'],
                               c=df_results.index, cmap='viridis', alpha=0.6, s=20)
        ax2.plot([df_results['worst_in_window'].min(), df_results['worst_in_window'].max()],
                  [df_results['worst_in_window'].min(), df_results['worst_in_window'].max()],
                  'r--', alpha=0.5, label='1:1 line')
        ax2.set_xlabel('Worst Return in Window (absolute)', fontsize=10)
        ax2.set_ylabel(f'{(1-qtl)*100}% VaR', fontsize=10)
        ax2.set_title('VaR Sensitivity to Extreme Returns', fontsize=11)
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        plt.colorbar(scatter, ax=ax2, label='Time')

        # Panel 3: VaR Changes (first differences)
        ax3 = plt.subplot(3, 1, 3)
        var_changes = df_results['var'].diff()
        ax3.bar(df_results['date'][1:], var_changes[1:], color='steelblue', alpha=0.7, width=1)
        ax3.axhline(0, color='black', linewidth=0.8)
        ax3.set_xlabel('Date', fontsize=10)
        ax3.set_ylabel('VaR Change (Daily)', fontsize=10)
        ax3.set_title('VaR Instability: Daily Changes', fontsize=11)
        ax3.grid(True, alpha=0.3)

        # Mark extreme events
        for date in extreme_returns.index:
            if date in df_results['date'].values:
                ax3.axvline(date, color='orange', alpha=0.5, linestyle='--', linewidth=1)

    elif plot_type == 'heatmap':
        # Create rolling window composition heatmap
        fig, ax = plt.subplots(figsize=(16, 10))

        # Prepare data for heatmap (subsample for visibility)
        step = max(1, len(rets_series) // 100)
        heatmap_data = []

        for i in range(window, len(rets_series), step):
            window_data = rets_series.iloc[i-window:i].values
            heatmap_data.append(window_data)

        heatmap_data = np.array(heatmap_data).T

        im = ax.imshow(heatmap_data, aspect='auto', cmap='RdYlGn', interpolation='nearest')
        ax.set_xlabel('Time Window', fontsize=12)
        ax.set_ylabel('Position in Window (days ago)', fontsize=12)
        ax.set_title(f'Rolling Window Composition: {column} (window={window})', fontsize=14, fontweight='bold')

        # Invert y-axis so most recent is at bottom
        ax.invert_yaxis()

        plt.colorbar(im, ax=ax, label='Return Value')

    elif plot_type == 'sensitivity':
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # Left: VaR vs Worst Return
        scatter1 = ax1.scatter(df_results['worst_in_window'], df_results['var'],
                                c=df_results.index, cmap='viridis', alpha=0.6, s=30)
        ax1.plot([df_results['worst_in_window'].min(), df_results['worst_in_window'].max()],
                  [df_results['worst_in_window'].min(), df_results['worst_in_window'].max()],
                  'r--', alpha=0.5, linewidth=2, label='1:1 line')
        ax1.set_xlabel('Worst Return in Window (absolute)', fontsize=12)
        ax1.set_ylabel(f'{(1-qtl)*100}% VaR', fontsize=12)
        ax1.set_title('VaR vs. Worst Return in Window', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        plt.colorbar(scatter1, ax=ax1, label='Time Progression')

        # Right: Distribution of VaR changes
        var_changes = df_results['var'].diff().dropna()
        ax2.hist(var_changes, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
        ax2.axvline(var_changes.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {var_changes.mean():.4f}')
        ax2.axvline(var_changes.median(), color='orange', linestyle='--', linewidth=2, label=f'Median: {var_changes.median():.4f}')
        ax2.set_xlabel('Daily VaR Change', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.set_title('Distribution of VaR Changes', fontsize=13, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    return fig