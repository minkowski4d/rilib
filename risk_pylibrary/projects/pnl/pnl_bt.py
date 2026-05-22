#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import numpy as np
import pandas as pd
from datetime import datetime as _datetime
from datetime import timedelta



# Custom Modules
from tools.snowflake_db import db_connection as db
from risk_pylibrary.projects.caracalla import caracalla_portfolio as c_port
from risk_pylibrary.projects.pnl import pnl_fifo as pnl
from risk_pylibrary.projects.pnl import pnl_support as pnl_sup



def pnl_sym_bt(out_pos=None, df_port=None):



    # Format PnL Output
    out_pnl = out_pos.copy()
    syms = list(out_pnl.symbol.unique())
    out_pnl['ddate'] = out_pnl['time'].apply(lambda x: x.date())
    out_pnl['upnl'] = out_pnl['upnl'].astype(float)
    out_pnl = out_pnl.iloc[:, [-1, 1, 2, 3, 4, 5]].groupby(['ddate', 'symbol']).sum()
    out_pnl = out_pnl.rename(columns=lambda x: 'risk_%s'%x)

    # Format Data Team Portfolio Output
    cols = ['eod_price', 'position_eod', 'sum_pnl_realized', 'sum_pnl_unrealized']
    df = df_port[df_port.index.get_level_values(1).isin(syms)].copy()[cols]
    df = df[df.index.get_level_values(0).isin(out_pnl.index.get_level_values(0).unique())]
    df.columns = [k.replace('risk', 'data') for k in out_pnl.columns]

    # Create output dictionary:
    out_dict = dict()


    out_dict['out_recon'] = pd.concat([out_pnl, df], axis=1)

    # Delta Cumulative Realised PnL
    out_dict['delta_rpnl'] = pd.pivot_table(out_dict['out_recon'].reset_index(),
                                            index='ddate',
                                            columns='level_1',
                                            values='risk_rpnl') - \
                             pd.pivot_table(out_dict['out_recon'].reset_index(),
                                            index='ddate',
                                            columns='level_1',
                                            values='data_rpnl')

    out_dict['delta_upnl'] = pd.pivot_table(out_dict['out_recon'].reset_index(),
                                            index='ddate',
                                            columns='level_1',
                                            values='risk_upnl') - \
                             pd.pivot_table(out_dict['out_recon'].reset_index(),
                                            index='ddate',
                                            columns='level_1',
                                            values='data_upnl').cumsum()

    out_dict['delta_position'] = pd.pivot_table(out_dict['out_recon'].reset_index(),
                                            index='ddate',
                                            columns='level_1',
                                            values='risk_quantity') - \
                             pd.pivot_table(out_dict['out_recon'].reset_index(),
                                            index='ddate',
                                            columns='level_1',
                                            values='data_quantity')


    out_dict['position_risk'] = pd.pivot_table(out_dict['out_recon'].reset_index(),
                                            index='ddate',
                                            columns='level_1',
                                            values='risk_quantity')
    out_dict['position_data'] = pd.pivot_table(out_dict['out_recon'].reset_index(),
                                            index='ddate',
                                            columns='level_1',
                                            values='data_quantity')


    return out_dict





