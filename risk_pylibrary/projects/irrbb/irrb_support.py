#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import timedelta, date, datetime as _datetime
from joblib import Parallel, delayed
import multiprocessing

# Import Custom Modules
from risk_pylibrary.tools import config as CF
from tools.snowflake_db import db_connection as db
from risk_pylibrary.projects.pnl import pnl_support as pnl_sup



def annex28_to_db(df_orig, df_nms_orig, report_date, verbose):

    df = df_orig.copy()
    df_names = df_nms_orig.copy()

    df['index'] = ['00' + str(k) if len(str(k)) == 2 else '0' + str(k) for k in df['index']]
    df['ddate'] = report_date

    # Create DB Input
    out = pd.melt(df, id_vars=['ddate', 'index'], value_vars=df.columns[1:])
    out['fmt'] = 'integer'

    # Set Up Renaming Dictionary
    df_names['column'] = ['00' + str(k) if len(str(k)) == 2 else '0' + str(k) for k in df_names['column']]

    # Create Group columns
    out['group_0'] = out['variable']
    out['group_0'] = out['variable'].map(dict(zip(df_names['column'], df_names['description'])))

    # Format Output
    out.columns = ['report_date', 'index', 'group_1', 'value', 'fmt', 'group_0']
    out = out[['report_date', 'index', 'group_0', 'group_1', 'fmt', 'value']]

    if verbose:
        print(list(out.group_0.unique()))
        print(list(out.group_1.unique()))

    return out