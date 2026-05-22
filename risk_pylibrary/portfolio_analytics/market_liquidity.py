#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys

# Import Python Modules
import numpy as np
from datetime import datetime as _datetime, date, timedelta

# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db




def calculate_mr_liq_buffer(startdate, enddate):
    """
    Function Calculates Market Liquidity Value At Risk impact based on "An Introduction to
    Market Risk Measurement" Dowd, 2002
    @param startdate: date object
    @param enddate: date object
    @return: dataframe
    """


    enddate_pnl = _datetime(enddate.year, enddate.month, enddate.day, 23, 30, 0)

    sql_qry = '''
                SELECT 
                    price_dt as ddate, 
                    instrument_id, 
                    close_mid_price, 
                    DIV0(close_ask_price - close_bid_price, close_mid_price) as bid_ask_spread
                FROM 
                    TEAMS_PRD.TRANSFORM_AUM.TRF__AUM__EOD_PRICE_FEED
                WHERE 
                    instrument_id in (SELECT 
                                        INSTRUMENT_ID 
                                      FROM 
                                        TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL
                                      WHERE
                                        report_date = %s) 
                AND 
                    exchange='LSX'
                AND 
                    price_dt >= %s 
                AND 
                    price_dt < %s'''%(db.sqldate(enddate_pnl), db.sqldate(startdate), db.sqldate(enddate))

    prx = db.run_query(sql_qry)

    # Adjust Output
    prx = prx.pivot_table(index=['ddate'],
                          columns=['instrument_id'],
                          values=['close_mid_price', 'bid_ask_spread'], fill_value=np.nan)


    # Calculate Liquidity Spread Metric
    mr_liq = ((prx[['bid_ask_spread']].mean() + 4*prx[['bid_ask_spread']].std()) / 2)
    mr_liq = mr_liq.reset_index().set_index('instrument_id').drop('level_0', axis=1)
    mr_liq.columns = ['mr_lvaR']

    # Get Weights
    sql_pnl_qry = '''
                    SELECT 
                        * 
                    FROM 
                        TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL 
                    WHERE 
                        report_date = %s
                  '''

    pos = db.run_query(sql_pnl_qry%db.sqldate(enddate_pnl))
    pos = pos.set_index('instrument_id')
    pos = pd.concat([pos, mr_liq], axis=1)
    pos['weight'] = (pos.quantity * pos.price) / (pos.quantity * pos.price).sum()
    pos['mr_lvaR_weighted'] = pos['mr_lvaR'] * pos['weight']

    return pos



def calculate_mr_liq_buffer_hist(startdate, enddate):
    """
    Function Calculates the Historical Simulation Market Liquidity Value At Risk impact based on "An Introduction to
    Market Risk Measurement" Dowd, 2002
    @param startdate: date object
    @param enddate: date object
    @return: dataframe
    """

    enddate_pnl = _datetime(enddate.year,enddate.month,enddate.day,23,30,0)

    sql_qry = '''
                SELECT 
                    price_dt as ddate, 
                    instrument_id, 
                    close_mid_price, 
                    DIV0(close_ask_price - close_bid_price, close_mid_price) as bid_ask_spread
                FROM 
                    TEAMS_PRD.TRANSFORM_AUM.TRF__AUM__EOD_PRICE_FEED
                WHERE 
                    instrument_id in (SELECT 
                                        INSTRUMENT_ID 
                                      FROM 
                                        TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL
                                      WHERE
                                        report_date = %s) 
                AND 
                    exchange='LSX'
                AND 
                    price_dt > %s 
                AND 
                    price_dt < %s''' % (db.sqldate(enddate_pnl),db.sqldate(startdate),db.sqldate(enddate))

    prx = db.run_query(sql_qry)

    # Adjust Output
    prx = prx.pivot_table(index=['ddate'],
                          columns=['instrument_id'],
                          values=['close_mid_price', 'bid_ask_spread'], fill_value=np.nan)

    # Get Weights
    sql_pnl_qry = '''
                    SELECT 
                        * 
                    FROM 
                        TEAMS_PRD.RISK_DATA.MR_PORT_POS_PNL 
                    WHERE 
                        report_date = %s
                  '''

    pos = db.run_query(sql_pnl_qry%db.sqldate(enddate_pnl))
    pos = pos.set_index('instrument_id')
    pos['mr_lvaR_weighted'] = pos['mr_lvaR'] * pos['weight']

    out = pd.DataFrame(columns=['mr_lvaR_weighted_mean', 'mr_lvaR_weighted_median'])

    for i in np.arange(250, len(prx)+1, 1):

        mr_liq_tmp = ((prx[:i][-250:][['bid_ask_spread']].mean() + 4 * prx[:i][-250:][['bid_ask_spread']].std()) / 2)
        mr_liq_tmp = mr_liq_tmp.reset_index().set_index('instrument_id').drop('level_0', axis=1)
        mr_liq_tmp.columns = ['mr_lvaR']

        pos_tmp = pd.concat([pos, mr_liq_tmp.dropna()], axis=1)
        pos_tmp = pos_tmp.dropna()
        pos_tmp['mr_lvaR_weighted'] = pos_tmp['mr_lvaR'] * pos_tmp['weight']

        out.loc[prx.index[:i][-1], 'mr_lvaR_weighted_mean'] = pos_tmp['mr_lvaR_weighted'].mean()
        out.loc[prx.index[:i][-1], 'mr_lvaR_weighted_median'] = pos_tmp['mr_lvaR_weighted'].median()


    return out




