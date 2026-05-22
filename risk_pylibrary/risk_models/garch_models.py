#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import numpy as np
from arch import arch_model
from scipy.stats import t, norm
from datetime import datetime as _datetime


# Custom Modules
import pandas as pd



def garch_exp(rets_rescaled, dist='t'):
    """
    Calculation of  EGarch Volatility and Residual Returns
    :param rets_rescaled: returns series multiplied by rescaling factor, e.g. 100
    :param dist: distribution that is used for maximum likelihood estimation
    """

    # Specify EGARCH model assumptions
    egarch_gm = arch_model(rets_rescaled, p=1, q=1, o=1, vol='EGARCH', dist=dist)
    # Fit the model
    egarch_result = egarch_gm.fit(disp='off')
    # Get Conditional Volatility
    egarch_vol = egarch_result.conditional_volatility

    # Get Residuals
    egarch_resid = egarch_result.resid
    # Calculate Standardized Residuals:
    egarch_std_resid = egarch_resid / egarch_vol
    # Test
    return egarch_gm, egarch_result, egarch_vol, egarch_resid, egarch_std_resid


def garch_gjr(rets_rescaled, dist='t'):
    """
    Calculation of  GJR Volatility and Residual Returns
    :param rets_rescaled: returns series multiplied by rescaling factor, e.g. 100
    :param dist: distribution, default 't'. Options: 'norm', 'skewt'
    """
    gjr_gm = arch_model(rets_rescaled, p=1, q=1, o=1, vol='GARCH', dist=dist)
    # Fit the model
    gjrgm_result = gjr_gm.fit(disp='off')
    # Get Conditional Volatility
    gjrgm_vol = gjrgm_result.conditional_volatility
    # Get Residuals
    gjrgm_resid = gjrgm_result.resid
    # Calculate Standardized Residuals:
    gjrgm_std_resid = gjrgm_resid / gjrgm_vol

    return gjr_gm, gjrgm_result, gjrgm_vol, gjrgm_resid, gjrgm_std_resid



def calculate_vaR_garch(rets, qtls=[0.01], holding_period=1, rescale=100, decay=1, ftol=1e-06, distr='t',max_iter=150, fhs=False, garch_engine='gjr'):
    """
    Calculate Parametric Value at Risk Quantiles 99&95 throughout GARCH Volatiltiy Model
    :param rets: Single Column percentage change dataframe
    :param qtls: quantiles list, e.g. [0.01] (1 - confidence interval)
    :param holding_period: forecast horizon, e.g. 1
    :param rescale: e.g. 100
    :param decay: applied via an exponentially weighted moving average, e.g. 0.94 or 1 for no decay
    :param ftol: Precision goal for the value of f in the stopping criterion in slsqp optimizer, e.g. 1e-03
    :param max_iter: iteration limit for the optimizer to reach convergence
    :return: dataframe with VaR Values for 95,99 and 1D,20D
    """

    # Adjust Index format
    if rets.index.dtype == 'O':
        rets = rets.rename(index=lambda x: _datetime(x.year, x.month, x.day))

    # Apply Sample Size
    rets_garch = rets.copy()
    # Use decay
    if decay != 1:
        rets_garch = rets_garch.sort_index(ascending=False).ewm(alpha=decay, adjust=True).mean()

    # Run Garch Model
    rets_garch = rets_garch.sort_index() * rescale

    if garch_engine == 'egarch':
        am = garch_exp(rets_garch, dist = distr)[0]
    elif garch_engine == 'gjr':
        am = garch_gjr(rets_garch, dist = distr)[0]

    res = am.fit(disp='off', last_obs=str(rets_garch.index[-1])[:10], options={'maxiter': max_iter, 'ftol': ftol})
    forecasts = res.forecast(horizon=holding_period, start=str(rets_garch.index[-1])[:10], simulations=1000, reindex = False)
    cond_mean = forecasts.mean[-holding_period:]
    cond_var = forecasts.variance[-holding_period:]

    if fhs:
        # Apply Filtered Historical Simulation
        std_rets = (rets_garch.iloc[:, 0] - res.params["mu"]).div(res.conditional_volatility)
        std_rets = std_rets.dropna()
        q_vals = np.array(std_rets.quantile([1-k for k in qtls]))
    else:
        # q_vals = am.distribution.ppf([qtl], res.params[-2 if garch_engine == 'egarch' else -1:]) FB20220511 only to use if distr for egarch is 'skewt'
        q_vals = am.distribution.ppf([1-k for k in qtls], res.params.loc['nu'] if distr == 't' else None)

    # Calculate Value At Risk:
    value_at_risk = - cond_mean.values + np.sqrt(cond_var).values * q_vals[None, :]
    # Assign Values to Output:
    value_at_risk_df = pd.DataFrame(value_at_risk,
                                    columns=['var%s_1d'%str(int(1000 * (1-k))) for k in qtls],
                                    index=[rets_garch.index[-1].date()])

    # Calculate cVaR (expected Shortfall):
    if distr == 'Normal':
        cond_value_at_risk = list()
        for qtl in qtls:
            cond_value_at_risk.append(- cond_mean.values + np.sqrt(cond_var).values * qtl**(-1) * norm.pdf(norm.ppf(qtl)))

    elif distr == 't':
        mu_t = cond_mean.values ; nu = res.params.loc['nu']
        cond_value_at_risk = list()
        for qtl in qtls:
            cond_value_at_risk.append(- mu_t - np.sqrt(cond_var).values * qtl**(-1) \
                                 * (1-nu)**(-1)*(nu-2 + t.ppf(qtl, nu)**2) * t.pdf(t.ppf(qtl, nu), nu))

    # Assign Values to Output:
    cond_value_at_risk_df = pd.DataFrame(np.array([[k[0][0]] for k in cond_value_at_risk]).T,
                                         columns = ['cvar%s_1d'%str(int(1000 * (1-k))) for k in qtls],
                                         index = [rets_garch.index[-1].date()])

    out_garch_var = pd.concat([value_at_risk_df, cond_value_at_risk_df], axis=1) / rescale
    out_garch_var.index.name = ''

    return out_garch_var


