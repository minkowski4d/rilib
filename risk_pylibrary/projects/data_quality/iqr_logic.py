#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime

import pandas as pd




def iqr_data_cleansing(df_orig, buffer, verbose=1):
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
        df = df_orig[[ticker]].dropna()
        # Set Boundaries
        q1 = np.quantile(df[ticker], 0.35)
        q3 = np.quantile(df[ticker], 0.65)
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