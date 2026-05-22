#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Import Python Modules
import numpy as np
import pandas as pd

# Custom Modules


def ewma_volatility(rets, window=250, decay=0.94, verbose=False):
    """
    Calculates EWMA Volatility on a given return series:
    https://www.une.edu.au/__data/assets/pdf_file/0009/76464/unebsop14-1.pdf
    """
    out = pd.DataFrame(index = rets[window - 1:].index, columns = rets.columns)

    # Calculate EWM weights
    # SUM [lambda^(t-1) * (1 - lambda)]
    ewm_values = np.power(decay, np.arange(window - 1, -1, -1))*(1 - decay)

    for idx in rets[window - 1:].index:
        # Slice to look back window
        tmp = rets[:idx][-window:]
        # Assign Standard Deviation Forecast
        # SUM [lambda^(t-1) * (1 - lambda)] * R_t^2
        out.loc[idx] = np.sqrt(np.sum(pd.DataFrame(ewm_values).values*tmp ** 2))

    return out

def ewma_fhs_volatility(rets, window=250, decay=0.94, verbose=False):

    # Calculate EWMA Volatility as support dataframe:
    ewma_vol = ewma_volatility(rets, window=window, decay=decay, verbose=verbose)
    ewma_vol.columns = ['ewma_vol']
    # Create New FHS column
    ewma_vol['ewma_fhs_vol_1250'] = np.nan
    # Run EWMA Volatility with a sliding window in order to apply scaling
    for k in ewma_vol.index:
        revol_devol_ratio = ewma_vol[k:][:window+1].iloc[-1][0] / ewma_vol[k:][:window]
        vol_new = np.std(rets.reindex(revol_devol_ratio.index).values * revol_devol_ratio.iloc[:, [0]].values)
        ewma_vol.loc[ewma_vol[k:][:window+1].index[-1], 'ewma_fhs_vol_1250'] = vol_new

    return ewma_vol



def ewma_covariance(rets, decay=0.94, window=250):
    """
    Calculates EWMA Covariance Matrix on a given return series
    """
    rets_window = rets[-window:]

    ewm_values = np.power(decay, np.arange(window - 1, -1, -1))*(1 - decay)
    # Calculate Normalized Returns
    normalized = (rets_window - rets_window.mean()).fillna(0).to_numpy()

    out = ((ewm_values*normalized.T)@normalized/ewm_values.sum())

    return out





def cornish_fisher_approx(zorig, rets):
    """
    Cornish Fisher Approximation
    @param zorig: z-score quantile, e.g. norm.ppf(0.01)
    @param rets: returns dataframe
    """
    from scipy.stats import kurtosis
    from scipy.stats import skew

    skew_sample = skew(rets)
    kurtosis_sample = kurtosis(rets)
    # Cornish Fisher Expansion on five cumulants
    z_new =(zorig + (zorig ** 2 - 1)*skew_sample/6 +
             (zorig ** 3 - 3*zorig)*(kurtosis_sample - 3)/24 -
             (2*zorig ** 3 - 5*zorig)*(skew_sample ** 2)/36)

    return z_new


def portfolio_risk_ctr(init_wgts, covariances):

    weights = np.asarray(init_wgts)
    vol_exante = np.sqrt(np.dot(weights, np.dot(covariances, weights.T)))
    risk_ctr = weights * np.dot(covariances, weights.T)/vol_exante

    return risk_ctr

