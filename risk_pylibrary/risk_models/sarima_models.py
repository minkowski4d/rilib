#!/usr/bin/env python
# -*- coding: UTF-8 -*-



import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import math
import smtplib

from datetime import datetime
from email.message import EmailMessage
from sklearn.metrics import mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.graphics.tsaplots import plot_pacf


def decomp_analysis(df, plot=True):
    """
    Seasonal Decomposition with Statsmodels
    @param df: timeseries
    @param plot: boolean
    @return: statsmodels object
    """

    # Seasonal Decomposition
    out_decomp = seasonal_decompose(df, period=12)


    if plot:
        out_decomp.plot()
        plt.show()

        fig,(ax1,ax2) = plt.subplots(nrows=2,ncols=1,figsize=(14,6),sharex=False,sharey=False)
        ax1 = plot_acf(df, lags=12, ax=ax1)
        ax2 = plot_pacf(df, lags=12, ax=ax2)
        plt.show()

    return out_decomp


def dickey_fuller_test(df, col):

    result = adfuller(df[col])
    print('ADF Statistic: %f' % result[0])
    print('p-value: %f' % result[1])
    print('Critical Test Statistics Values:')
    for key,value in result[4].items():
        print('\t%s: %.3f' % (key,value))



    df_diff = df.diff().diff(52)
    df.dropna(inplace=True)

    # Plot differenced data
    fig,ax = plt.subplots(figsize=(12,9))
    fig.suptitle('Line Plot of the Stationary Seasonal Time Series Data')
    df_diff.plot(ax=ax)
    plt.show()


def arima_engine(df):

    df_diff = df.diff()
    print('test')
