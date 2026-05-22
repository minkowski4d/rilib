#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Python Modules
import numpy as np
import pandas as pd
from scipy.optimize import minimize







def _allocation_risk(weights, covariances):

    # We calculate the risk of the weights distribution
    portfolio_risk = np.sqrt((weights * covariances * weights.T))[0, 0]

    # It returns the risk of the weights distribution
    return portfolio_risk


def _assets_risk_contribution_to_allocation_risk(weights, covariances):

    # We calculate the risk of the weights distribution
    portfolio_risk = _allocation_risk(weights, covariances)

    # We calculate the contribution of each asset to the risk of the weights
    # distribution
    assets_risk_contribution = np.multiply(weights.T, covariances * weights.T)  / portfolio_risk

    # It returns the contribution of each asset to the risk of the weights
    # distribution
    return assets_risk_contribution


def _risk_budget_objective_error(init_wgts, args):

    # The covariance matrix occupies the first position in the variable
    covariances = args[0]; risk_budget = args[1]

    # We convert the weights to a matrix
    weights = np.matrix(init_wgts)

    # Volatility ex-Ante
    vol_exante = np.sqrt((weights * covariances * weights.T))[0, 0]

    # Volatility Contribution:
    vol_ctr = np.multiply(weights.T, covariances * weights.T)/vol_exante

    # Target Distribution
    vol_target = np.asmatrix(np.multiply(vol_exante, risk_budget))

    # Error between the desired contribution and the calculated contribution of
    error_val = sum(np.square(vol_ctr - vol_target.T))[0, 0]

    return error_val


def _portfolio_risk(init_wgts,covariances):

    weights = np.matrix(init_wgts)
    vol_exante = np.sqrt(np.dot(weights,np.dot(covariances,weights.T)))


    return vol_exante.tolist()[0][0]


def _portfolio_risk_ctr(init_wgts,covariances):

    vol_exante = _portfolio_risk(init_wgts,covariances)
    risk_ctr= init_wgts * np.dot(covariances, init_wgts.T)/vol_exante

    return risk_ctr


def _portfolio_return(init_wgts,rets):

    weights = np.matrix(init_wgts)
    portfolio_return = np.dot(weights, rets.mean()*250)
    return portfolio_return.tolist()[0][0]


def _neg_portfolio_return(init_wgts,rets):

    weights = np.matrix(init_wgts)
    neg_portfolio_return = -1*np.dot(weights, rets.mean()*250)
    return neg_portfolio_return.tolist()[0][0]


def _neg_sharpe_ratio(wgts,rets, covariances):

    p_ret=_portfolio_return(wgts,rets)
    p_vol=_portfolio_risk(wgts,covariances)
    neg_shr=-1* p_ret/p_vol

    return neg_shr


def _get_risk_parity_weights(covariances, risk_budget, init_wgts,leverage):
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html
    # Restrictions to consider in the optimisation: only long positions whose
    # sum equals 100%
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - leverage},
                   {'type': 'ineq', 'fun': lambda x: x})

    # Optimisation process
    optimize_result = minimize(fun=_risk_budget_objective_error, #Function to Optimize
                               x0=init_wgts, # Initial Guess
                               args=[covariances, risk_budget], #Parameters for fun
                               method='SLSQP',
                               constraints=constraints,
                               tol=1e-10,
                               options={'disp': True})

    # Recover the weights from the optimised object
    weights = optimize_result.x

    # It returns the optimised weights
    return weights


def _get_target_ret_weights(rets,covariances,init_wgts,leverage,target_return):
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html
    # Restrictions to consider in the optimisation: only long positions whose
    # sum equals 100%
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x)-leverage},
                   {'type': 'eq', 'args': (rets,),'fun':lambda x,rets: target_return-_portfolio_return(x,rets)})

    # Optimisation process
    optimize_result = minimize(fun=_portfolio_risk, #Function to Optimize
                               x0=init_wgts, # Initial Guess
                               args=(covariances,), #Parameters for fun
                               method='SLSQP',
                               constraints=constraints,
                               tol=1e-10,
                               bounds=((0.0, leverage),)*len(rets.columns),
                               options={'disp': 0})

    # Recover the weights from the optimised object
    weights = optimize_result.x

    # It returns the optimised weights
    return weights


def _get_target_vol_weights(rets,covariances,init_wgts,leverage,target_vol):
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html
    # Restrictions to consider in the optimisation: only long positions whose
    # sum equals 100%
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x)-leverage},
                   {'type': 'eq', 'args': (covariances,),'fun':lambda x,covariances: target_vol-_portfolio_risk(x,covariances)})

    # Optimisation process
    optimize_result = minimize(fun=_neg_portfolio_return, #Function to Optimize
                               x0=init_wgts, # Initial Guess
                               args=(rets,), #Parameters for fun
                               method='SLSQP',
                               constraints=constraints,
                               tol=1e-10,
                               bounds=((0.0, leverage),)*len(rets.columns),
                               options={'disp': 0})

    # Recover the weights from the optimised object
    weights = optimize_result.x

    # It returns the optimised weights
    return weights


def _get_max_sharpe_ratio(rets, covariances, leverage, fix_bounds):

    num_assets = len(rets.columns)
    args = (rets, covariances)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - leverage})
    bound = (0.0,leverage)
    if len([k for k in fix_bounds if k!=0])>0:
        bound_ll=[bound for asset in range(num_assets)]
        for j in [k for k in fix_bounds if k!=0]:
            bound_ll[fix_bounds.index(j)] = (j, j)
            bounds=tuple(bound_ll)
    else:
        bounds = tuple([bound for asset in range(num_assets)])
    optimize_result = minimize(_neg_sharpe_ratio, num_assets*[1./num_assets], args=args,method='SLSQP', bounds=bounds, constraints=constraints)

    # Recover the weights from the optimised object
    weights = optimize_result.x

    return weights



def alloc_frontier(rets, len_sim=5000, leverage=[0,1]):

    import random
    covariances = rets.cov().values * 250
    risk_all = np.array([])
    return_all = np.array([])
    weights_all = pd.DataFrame(index=range(0,len_sim),columns=range(0,len(rets.columns)))
    for k in range(len_sim):
        if k % 5000 == 0:
            print(k)
        weights = []
        for l in range(1, len(rets.columns)+1):
            if l == len(rets.columns)+1:
                pass
            else:
                weights.append(random.uniform(leverage[0],leverage[1]))

        # Calculate Risk
        risk = _portfolio_risk(weights,covariances)
        ret = _portfolio_return(weights,rets)
        risk_all = np.append(risk_all, risk)
        return_all = np.append(return_all, ret)
        weights_all.loc[k] = weights

    return risk_all, return_all, weights_all






def _run_mix_parity_markowitz(out,pct_ranks=[0.75,0.85,0.9,0.95]):

    # out=alloc.optimal_allocation(ts,len_sim=1000,shift=[2,-1],targets=[0.05,0.15],ret_min=0.01,plot=True,to_excel=True)
    ts = out['plot_sample'].iloc[:, :3]
    prices = out['prices_shifted']
    wgts = pd.DataFrame(list(out['avg_markowitz'].iloc[:,:-3].values) * len(prices.index),columns=out['avg_markowitz'].iloc[:, :-3].columns, index=prices.index)

    wgts_parity = pd.DataFrame([out['parity_wgts']] * len(prices.index), columns=out['avg_markowitz'].iloc[:, :-3].columns,index=prices.index)

    vol = ts.pct_change().rolling(window=250).std().dropna() * np.sqrt(250)
    vol_rank = vol.rank(pct=True)

    for rnk in pct_ranks:
        print("****** Running Portfolio for Rank %s"%rnk)
        wgts_tmp=wgts.copy()
        idx = ts.reindex(vol_rank[vol_rank.Average_Markowitz >= rnk].index).index
        wgts_tmp[wgts_tmp.index.isin(idx)] = wgts_parity[wgts_parity.index.isin(idx)]
        ts['Mix_Markowitz_Parity_%s'%rnk]=prices.portfolio(wgts_tmp,name='Mix_Markowitz_Parity_%s'%rnk)

    return ts



























