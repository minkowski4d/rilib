#!/usr/bin/env python
# -*- coding: UTF-8 -*-



import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import math
import smtplib




def volume_intraday(df_orig):

    df = df_orig.copy()
    out = pd.DataFrame(index=df.timestamp_cest.unique())

    for k in df.exchange_id.unique():
        tmp = df[df.exchange_id == k]
        tmp['volume_eur'] = tmp[['direction',
                                 'execution_price',
                                 'net_size']].apply(lambda row: row['execution_price'] * row['net_size']
                                                                if row['direction']=='BUY' else
                                                                    (-1)*row['execution_price']*row['net_size'],axis=1)
        out['Volume EUR - %s'%k] = tmp[['timestamp_cest', 'volume_eur']].groupby('timestamp_cest').sum().cumsum()


    return out
