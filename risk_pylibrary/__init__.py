#!/usr/local/bin/python3.11
# -*- coding: UTF-8 -*-

from __future__ import division
import sys as _sys
import platform as _platform
import getpass as _getpass
from multiprocessing import current_process
import pandas as pd
import numpy as np
from datetime import datetime as _datetime
from datetime import date, timedelta
from pdb import pm as postm
from pdb import runcall as dbg
from pdb import runeval as dbge
from importlib import reload


platform = _platform.system()
user_node = _platform.node()
user_name = _getpass.getuser()

if current_process().name == 'MainProcess':
    print("")
    print("     ------------------------------------------------------------")
    print("               Risk @ Trade Republic Bank GmbH")
    print("     ------------------------------------------------------------")
    print('      Node: %s\tUser: %s'%(user_node, user_name))
    print('      Python version '+_sys.version.replace('\n', '\n\t'))
    print('      pandas: %s\tnumpy: %s'%(pd.__version__, np.__version__))


if user_name.startswith('fabioballoni'):

    # Import Python Modules
    import numpy as np
    import matplotlib
    import seaborn as sns
    from datetime import date,timedelta, datetime as _datetime
    import polars as pl
    from ipdb import pm as ipostm

    # Custom Modules
    # Tools
    from tools.snowflake_db import db_connection as db

    # Instruments
    from instruments import data_prices as dtp
    from risk_pylibrary.instruments import data_info as dtf
    from risk_pylibrary.instruments import data_quality as dtq
    from risk_pylibrary.instruments.data_info import sid

    # Risk Analytics
    from risk_pylibrary.risk_analytics import risk_engines as rie

    # Mixed
    from risk_pylibrary.tools import config as CF
    from risk_pylibrary.risk_models import econometrics as ec
    from risk_pylibrary.tools import charting as CH

    # Matplotlib Parameters
    matplotlib.rcParams['figure.facecolor'] = '1'
    matplotlib.rcParams["axes.facecolor"] = '1'
    matplotlib.rcParams["axes.edgecolor"] = '0.75'
    matplotlib.rcParams['grid.color'] = '0.75'
    matplotlib.rcParams['grid.linestyle'] = ':'
    matplotlib.rcParams['grid.linewidth'] = 0.5
    matplotlib.rcParams['axes.xmargin'] = 0
    matplotlib.rcParams['legend.shadow'] = True
    matplotlib.rcParams['legend.framealpha'] = 1
    matplotlib.rcParams['legend.loc'] = "upper left"
    pd.set_option('display.float_format',lambda x: '%0.6f'%x)
    pd.set_option('display.max_columns', 30)
    pd.set_option('display.max_colwidth', 40)
    pd.set_option('display.max_rows', 40)
    pd.set_option('display.width', None)
    pd.options.mode.chained_assignment = None


elif user_name.startswith('fgv'):

    print("Hello Francesco. you may add startup packages in /risk_pylibrary/_init__.py")


if current_process().name == 'MainProcess':
    print('      Kernel started '+_datetime.now().strftime('%Y-%m-%d %H:%M'))
    print("     ------------------------------------------------------------")
