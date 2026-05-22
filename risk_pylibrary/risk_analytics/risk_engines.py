#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Import Python Modules
import numpy as np

# Custom Modules
from tools import pandas_patched as pd


def portfolio_vaR(rets_orig, wgts, holding_period=1, engine='mc', fmt_engine={}):
    """
    Author: F.Balloni (fabio.balloni@traderepublic.com)
    Portfolio Value-At-Risk (and CVaR, SVaR) engine. Callable engines are
    - Historical Simulation
    - GJR GARCH
    - Multivariate MonteCarlo

    Engine Parameters are passes via ftm_engine dictionary.

    @param rets_orig: Returns Dataframe
    @param wgts: list of weights, e.g. np.random.dirichlet(np.ones(len(rets.columns)),size=1)
    @param holding_period: integer
    @param engine: risk model selection, e.g. 'mc' or 'hs'
    @param fmt_engine: dictionary with model specifications
    """

    # Import multiple used models:
    # Python
    from scipy.stats import norm, t

    # Custom Modules
    from risk_models import support_models as smo

    # ToDo: Implement quick Data shape print

    # Set Value Date
    value_date = rets_orig.index[-1]

    if engine == 'egarch' or engine == 'gjr':
        # Import Model
        from risk_models import garch_models as gm

        # GARCH Model Inputs
        # window: lookback period, e.g. 250 days
        # horizon: forecast horizon, e.g. 1
        # rescale: rescale for fitting purposes
        # decay: values from 1 to 0.94 for EWMA
        # ftol: tolerance for optimizer convergence, default 1e-06
        # max_iter: maximum iteration for convergence search

        fmt_engine_keys = ['window', 'qtls', 'holding_period', 'rescale', 'decay',
                           'ftol', 'max_iter', 'fhs', 'distr', 'garch_engine', 'verbose']

        # Default Values
        fmt_engine_default = {'window_default': 250,
                              'qtls_default': [0.05, 0.01, 0.001],
                              'holding_period_default': 1,
                              'rescale_default': 1000,
                              'decay_default': 1,
                              'ftol_default': 1e-06,
                              'max_iter_default': 150,
                              'fhs_default': False,
                              'distr_default': 'Normal',
                              'garch_engine_default': engine,
                              'verbose_default': True}

    elif engine == 'mc':

        # Monte Carlo Model Inputs
        # window: lookback period, e.g. 250 days
        # n_sim: number of simulations

        fmt_engine_keys = ['window', 'holding_period', 'n_sim', 'distr', 'decay', 'ewma_cov', 'qtls', 'verbose']
        # Default Values
        fmt_engine_default = {'window_default': 250,
                              'holding_period_default': 1,
                              'qtls_default': [0.05, 0.01, 0.001],
                              'n_sim_default': 1000,
                              'distr_default': 'norm',
                              'decay_default': 0.94,
                              'ewma_cov_default': True,
                              'qtl': 0.01,
                              'verbose_default': True}

    elif engine == 'ewma':
        fmt_engine_keys = ['window', 'qtls', 'holding_period', 'decay', 'distr', 'verbose']

        # Default Values
        fmt_engine_default = {'window_default': 250,
                              'qtls_default': [0.05, 0.01, 0.001],
                              'holding_period_default': 1,
                              'decay_default': 0.94,
                              'distr_default': 'norm',
                              'verbose_default': True}

    elif engine == 'hs':
        fmt_engine_keys = ['window', 'qtls', 'holding_period', 'decay', 'distr', 'verbose']

        # Default Values
        fmt_engine_default = {'window_default': 250,
                              'qtls_default': [0.05, 0.01, 0.001],
                              'holding_period_default': 1,
                              'decay_default': 0.94,
                              'distr_default': 'norm',
                              'verbose_default': True}

    # Build fmt_engine:
    for k in fmt_engine_keys:
        if not k in fmt_engine.keys():
            fmt_engine[k] = fmt_engine_default[k + '_default']

    fmt_engine_string = ''
    for k in fmt_engine:
        fmt_engine_string += '\t\t\t%s: %s\n'%(k, fmt_engine[k])

    # Initialising Risk Model Calculation
    # Slice returns:
    rets = rets_orig.copy()
    rets = rets[-fmt_engine['window']:]

    if fmt_engine['verbose']:
        # Print Model Setup
        print("\n     ------------------------------------------------------------")
        print("               Portfolio VaR Calculation")
        print("     ------------------------------------------------------------")
        print('      Model: \n\t\t\t%s\n'%engine)
        print('      Model Inputs:\n %s'%fmt_engine_string)
        print('      Window Start and End:\n \t\t\tStart %s, End %s'%(rets.index[0], rets.index[-1]))
        print("     ------------------------------------------------------------")

    # Calculate Value at Risk
    # GARCH
    if engine == 'egarch' or engine == 'gjr':
        if fmt_engine['verbose']: print("\nInitializing GARCH Volatility Model for Value at Risk Calculation")
        # Build portfolio
        ret_vaR = rets.portfolio_rets(wgts)
        # Initialise GARCH Calculation
        out = gm.calculate_vaR_garch(ret_vaR[['pf']],
                                     qtls = fmt_engine['qtls'],
                                     holding_period = holding_period,
                                     rescale = fmt_engine['rescale'],
                                     decay = fmt_engine['decay'],
                                     ftol = fmt_engine['ftol'],
                                     max_iter = fmt_engine['max_iter'],
                                     fhs = fmt_engine['fhs'],
                                     distr = fmt_engine['distr'],
                                     garch_engine = fmt_engine['garch_engine'])

        # Scale by holdings period
        out = out * np.sqrt(fmt_engine['holding_period'])

    # Monte Carlo
    elif engine == 'mc':
        # Import Model
        from risk_models import mc_models
        if fmt_engine['verbose']: print("\nInitializing MonteCarlo Simulation for Value at Risk Calculation")
        # Initialise MonteCarlo Calculation
        sim_rets, sim_ts = mc_models.mc_simulate(rets = rets,
                                                n = fmt_engine['n_sim'],
                                                sim_len = fmt_engine['window'],
                                                distr = fmt_engine['distr'],
                                                ewma_cov = fmt_engine['ewma_cov'],
                                                verbose = fmt_engine['verbose'])

        # Build Output
        out = pd.DataFrame(index = [value_date])
        # Calculate Value at Risk for holding period and quantile
        qtls = fmt_engine['qtls']
        h = fmt_engine['holding_period']

        out = pd.DataFrame()
        for qtl in qtls:
            # Calculate Value at Risk for holding period and quantile
            tmp_vaR = -1 * sim_rets.dot(wgts.T).groupby("sim_id").quantile(qtl)
            tmp_vaR.columns = ['var%s_1d'%str(int(1000*(1 - qtl)))]

            # Calculate conditional VaR (expected Shortfall):
            cvar_f = lambda x: np.mean(x[x <= np.percentile(x, qtl*100)], axis = 0)
            # Multiply by -1 as other risk engines produce positive VaR values by convention
            tmp_cvaR = -1 * sim_rets.dot(wgts.T).groupby("sim_id").apply(lambda x: cvar_f(x))

            # Create Output
            out.loc[value_date, 'var%s_%sd'%(str(int(1000*(1 - qtl))), str(h))] = tmp_vaR.median() * np.sqrt(h)
            out.loc[value_date, 'cvar%s_%sd'%(str(int(1000*(1 - qtl))), str(h))] = tmp_cvaR.median() * np.sqrt(h)


    # EWMA Volatility
    elif engine == 'ewma':
        if fmt_engine['verbose']: print("\nInitializing EWMA Volatility Model for Value at Risk Calculation")
        # Build portfolio
        ret_vaR = rets.portfolio_rets(wgts)

        # Apply EWMA volatility
        vol_ewma = smo.ewma_volatility(ret_vaR[-fmt_engine['window']:],
                                       decay = fmt_engine['decay'],
                                       verbose = fmt_engine['verbose'])


        qtls = fmt_engine['qtls']
        h = fmt_engine['holding_period']
        # Build Output
        out = pd.DataFrame(index = [value_date])

        for qtl in qtls:
            if fmt_engine['distr'] == 'norm':
                mu_norm, sig_norm = norm.fit(ret_vaR)
                # Calculate VaR
                value_at_risk = mu_norm - vol_ewma*norm.ppf(qtl)
                # Calculate CVaR
                cond_value_at_risk = -mu_norm + vol_ewma*qtl ** (-1)*norm.pdf(norm.ppf(qtl))

            elif fmt_engine['distr'] == 't':
                nu, mu_t, sig_t = t.fit(ret_vaR)
                if nu < 2: nu = 3  # Force to 3
                # Calculate VaR
                value_at_risk = mu_t - vol_ewma*np.sqrt(((nu - 2)/nu))*t.ppf(qtl, nu)
                # Calculate CVaR
                cond_value_at_risk = -mu_t - vol_ewma*qtl**(-1)*(1 - nu)**(-1) \
                                     * (nu - 2 + t.ppf(qtl, nu)**2) \
                                     * t.pdf(t.ppf(qtl, nu), nu)

            out.loc[value_date, 'var%s_%sd'%(str(int(1000*(1 - qtl))), str(holding_period))] = value_at_risk.iloc[0, 0]*np.sqrt(h)
            out.loc[value_date, 'cvar%s_%sd'%(str(int(1000*(1 - qtl))), str(holding_period))] = cond_value_at_risk.iloc[0, 0]*np.sqrt(h)


    # Historical Simulation
    elif engine == 'hs':
        # Build Output
        out = pd.DataFrame(index = [value_date])

        # Calculate Value at Risk for holding period and quantile
        qtls = fmt_engine['qtls']
        h = fmt_engine['holding_period']

        # Build portfolio
        ret_vaR = rets.portfolio_rets(wgts)

        for qtl in qtls:
            # Calculate Value at Risk for holding period and quantile
            tmp_vaR = -1 * ret_vaR.quantile(qtl)
            tmp_vaR.columns = ['var%s_1d'%str(int(1000*(1 - qtl)))]

            # Calculate conditional VaR (expected Shortfall):
            tmp_cvaR = -1*ret_vaR[ret_vaR <= np.percentile(ret_vaR, qtl*100)].mean()

            # Create Output
            out.loc[value_date, 'var%s_%sd'%(str(int(1000*(1 - qtl))), str(h))] = tmp_vaR.iloc[0] * np.sqrt(h)
            out.loc[value_date, 'cvar%s_%sd'%(str(int(1000*(1 - qtl))), str(h))] = tmp_cvaR.iloc[0] * np.sqrt(h)


    return out


def stressed_vaR(rets_orig, wgts, engine='gjr', fmt_engine={}, verbose=True):
    """
    This is a test
    """

    # Import multiple used models:
    # Python
    from scipy.stats import norm, t

    # Custom Modules
    from risk_models import support_models as smo

    if engine == 'egarch' or engine == 'gjr':
        # Import Model
        from risk_models import garch_models as gm

        # GARCH Model Inputs
        # window: lookback period, e.g. 250 days
        # horizon: forecast horizon, e.g. 1
        # rescale: rescale for fitting purposes
        # decay: values from 1 to 0.94 for EWMA
        # ftol: tolerance for optimizer convergence, default 1e-06
        # max_iter: maximum iteration for convergence search

        fmt_engine_keys = ['window', 'qtls', 'holding_period', 'rescale', 'decay',
                           'ftol', 'max_iter', 'fhs', 'distr', 'garch_engine', 'verbose']

        # Default Values
        fmt_engine_default = {'window_default': 250,
                              'qtls_default': [0.05, 0.01, 0.001],
                              'holding_period_default': 1,
                              'rescale_default': 1000,
                              'decay_default': 1,
                              'ftol_default': 1e-06,
                              'max_iter_default': 150,
                              'fhs_default': False,
                              'distr_default': 'Normal',
                              'garch_engine_default': engine,
                              'verbose_default': True}


    elif engine == 'hs':
        fmt_engine_keys = ['window', 'qtls', 'holding_period', 'decay', 'distr', 'verbose']

        # Default Values
        fmt_engine_default = {'window_default': 250,
                              'qtls_default': [0.05, 0.01, 0.001],
                              'holding_period_default': 1,
                              'decay_default': 0.94,
                              'distr_default': 'norm',
                              'verbose_default': True}

    # Build fmt_engine:
    for k in fmt_engine_keys:
        if not k in fmt_engine.keys():
            fmt_engine[k] = fmt_engine_default[k + '_default']

    fmt_engine_string = ''
    for k in fmt_engine:
        fmt_engine_string += '\t\t\t%s: %s\n'%(k, fmt_engine[k])

    if fmt_engine['verbose']:
        # Print Model Setup
        print("\n     ------------------------------------------------------------")
        print("               Portfolio Stressed VaR Calculation")
        print("     ------------------------------------------------------------")
        print('      Model: \n\t\t\t%s\n'%engine)
        print('      Model Inputs:\n %s'%fmt_engine_string)
        print('      Series Start and End:\n \t\t\tStart %s, End %s'%(rets_orig.index[0], rets_orig.index[-1]))
        print("     ------------------------------------------------------------")

    # Calculate Value at Risk
    rets = rets_orig.copy()

    # Output DataFrame:
    out = pd.DataFrame()

    # GARCH
    if engine == 'egarch' or engine == 'gjr':
        if verbose:
            print("\nInitializing GARCH Simulation for Value at Risk Calculation with %s days"%len(rets.index[fmt_engine['window']:]))
        idx = 1
        for k in rets.index[fmt_engine['window']:]:
            # Print Counter:
            if idx%fmt_engine['window'] == 0: print("\t\t\t Calculated %s windows"%idx)
            rets_tmp = rets[idx:].loc[:k]
            # Build portfolio
            ret_vaR = rets_tmp.portfolio_rets(wgts)
            # Initialise GARCH Calculation
            tmp_vaR = gm.calculate_vaR_garch(ret_vaR[['pf']],
                                             qtls = fmt_engine['qtls'],
                                             holding_period = fmt_engine['holding_period'],
                                             rescale = fmt_engine['rescale'],
                                             decay = fmt_engine['decay'],
                                             ftol = fmt_engine['ftol'],
                                             max_iter = fmt_engine['max_iter'],
                                             fhs = fmt_engine['fhs'],
                                             garch_engine = fmt_engine['garch_engine'])
            # Format
            out = pd.concat([out, tmp_vaR], axis = 0)

            # Set Counter up +1
            idx += 1

    # Historical Simulation
    elif engine == 'hs':
        if verbose:
            print("\nInitializing Historical Simulation Model for Value at Risk Calculation with %s windows"%len(rets.index[fmt_engine['verbose']:]))
        # Calculate VaR
        qtls = fmt_engine['qtls']
        idx = 1
        for k in rets.index[fmt_engine['window']:]:
            # Print Counter:
            if idx%fmt_engine['window'] == 0: print("\t\t\t Calculated %s windows"%idx)
            rets_tmp = rets[idx:].loc[:k]
            # Build portfolio
            ret_vaR = rets_tmp.portfolio_rets(wgts)
            out_tmp = pd.DataFrame(index = [k])
            for qtl in qtls:
                # Calculate Value at Risk for holding period and quantile
                tmp_vaR = -1*ret_vaR.quantile(qtl).to_frame(name = 'var%s_1d'%str(int(1000*(1 - qtl))))
                tmp_vaR = tmp_vaR.rename(index = {'pf':k})

                # Calculate conditional VaR (expected Shortfall):
                tmp_cvaR = -1*ret_vaR[ret_vaR <= np.percentile(ret_vaR, qtl*100)].mean().to_frame(name = 'cvar%s_1d'%str(int(1000*(1 - qtl))))
                tmp_cvaR = tmp_cvaR.rename(index = {'pf': k})

                out_tmp = out_tmp.join(tmp_vaR).join(tmp_cvaR)


            # Format
            out = pd.concat([out, out_tmp], axis = 0)

            # Set Counter up +1
            idx += 1

    return out
