#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Generic Modules
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas_datareader as pdr
import seaborn as sns
from datetime import datetime as _datetime, timedelta

# Statsmodels
from statsmodels.tsa.forecasting.theta import ThetaModel


def theta_engine(df_orig, metric='diff', len_forecast=1, model_params={'theta_mod0':'theta1'}, confidence=0.05, verbose=False):

    # Set Output
    out_dict = dict()

    # Copy Input Data
    df = df_orig.copy()
    col = df.columns[0]

    # Adjust Data per Metric:
    if metric == 'diff':
        df = df_orig.diff().dropna()

    # Format Input Data
    # Check if index is datetime object
    if isinstance(df.index[0], _datetime) is False:
        df = df.rename(index=lambda x: pd.to_datetime(x))

    mod = ThetaModel(df)
    res = mod.fit()

    if verbose:
        print(res.summary())

    # Build Output
    out_forecast = pd.DataFrame(index=df_orig.index, columns=list(model_params.values()))

    # Join Data
    for k in list(model_params.values()):
        out_forecast[k] = df_orig[[col]].values

    # Get Model Results
    ll_model_params = [int(k[-1]) if k[-1]!='g' else np.inf for k in list(model_params.values())]

    forecasts = pd.DataFrame()
    confidence_int = pd.DataFrame(index=pd.MultiIndex.from_product([list(model_params.values())]+[['lower','upper']],names=['model','bounds']),
                                  columns=np.arange(0,len_forecast)).T


    for fcast_name, fcast_param in dict(zip(list(model_params.values()), ll_model_params)).items():
        # Add Forecasts
        forecasts[fcast_name] = res.forecast(len_forecast, theta=fcast_param)
        # Add Confidence Interval with step 1
        confidence_int[(fcast_name, 'lower')] = res.prediction_intervals(len_forecast, fcast_param, confidence).lower.values
        confidence_int[(fcast_name, 'upper')] = res.prediction_intervals(len_forecast, fcast_param, confidence).upper.values


    # Build Index
    forecasts['ddate'] = pd.bdate_range(start=df_orig.index[-1]+timedelta(1),
                                        end=df_orig.index[-1]+timedelta(len_forecast+10))[:len_forecast]

    forecasts = forecasts.reset_index().drop('index', axis=1).set_index('ddate')
    forecasts_cumsum = pd.concat([out_forecast.iloc[[-1]], forecasts], axis=0).cumsum()[1:].rename(index=lambda x: pd.to_datetime(x))

    confidence_int['ddate'] = pd.bdate_range(start=df_orig.index[-1]+timedelta(1),
                                        end=df_orig.index[-1]+timedelta(len_forecast+10))[:len_forecast]

    confidence_int = confidence_int.reset_index().drop('index', axis=1).set_index('ddate')


    # Append to Output
    out_forecast = pd.concat([out_forecast, forecasts_cumsum.rename(index=lambda x: x.date())], axis=0)
    out_dict['forecast'] = out_forecast
    out_dict['confidence'] = confidence_int


    return out_dict




def theta_model_backtest(df_orig, initial_window_size, rolling_window, metric='diff', len_forecast=1, model_params={'theta_mod0': 'theta1'}, verbose=1):


    if verbose:
        print('\n****************** Initiating Theta Model Backtest\n')
    out_dict = dict()

    # Copy Input Data
    df = df_orig.copy()

    # Qualitative Check: Code Break if data requirements are not met
    if len(df) <= initial_window_size:
        raise Exception("ERROR: Original Data is too short (length = %s, but required length = %s)"%(len(df), initial_window_size))

    #Set Outputs
    out_fixed = out_expanding = pd.DataFrame()
    out_fixed_conf = out_expanding_conf = pd.DataFrame()

    # Iterate
    for idx_num in range(1, len(df[initial_window_size:])):

        if idx_num % 50 == 0 and verbose:
            print('\t\t\t Iteration on Step: %s'%idx_num)

        # Predict 1 day ahead for a fixed window
        tmp_fixed_dict = theta_engine(df[idx_num:idx_num+rolling_window], len_forecast=len_forecast, metric=metric, model_params=model_params)
        out_fixed = pd.concat([out_fixed, tmp_fixed_dict['forecast'].iloc[[-1]]], axis=0)

        # Add Fixed confidence Intervals
        out_fixed_conf = pd.concat([out_fixed_conf, tmp_fixed_dict['confidence']], axis=0)

        # Predict 1 day ahead for an expanding window
        tmp_expanding_dict = theta_engine(df[:initial_window_size + idx_num], len_forecast=len_forecast, metric=metric, model_params=model_params)
        out_expanding = pd.concat([out_expanding, tmp_expanding_dict['forecast'].iloc[[-1]]], axis=0)

    # Create Output
    out = df_orig.copy()
    out = pd.concat([out, out_fixed.rename(columns={'theta1':'theta1_expanding'}), out_expanding.rename(columns={'theta1':'theta1_fixed'})], axis=1)


    return out

