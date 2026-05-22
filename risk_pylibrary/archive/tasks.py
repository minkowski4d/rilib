#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime

# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db


def T_morning_tasks(ddate=None, starting_point = 0):
    """
    Released 1st September 2023
    Author: F.Balloni (fabio.balloni@traderepublic.com)
    Morning Tasks Schedule
    Covered Tasks:
        - Update Prices
        - Update Yields
        - Update CDS Spreads

    @return: dictionary
    """

    # Importing Modules
    from risk_pylibrary.instruments import data_prices as dtp


    # ***********************************************************************************************************
    print("********************   Initiating Morning Task Schedule ********************  ")

    if starting_point <= 10:

        print("********** Running Preliminary Positions Report **********")
        # Import Modules:
        from risk_pylibrary.projects.pnl import pnl_support as pnl_sup
        from risk_pylibrary.projects.pnl import pnl_fifo as pnl

        # Setting Start and Enddate
        date_tdy = _datetime.now().date()
        if date_tdy.weekday() == 1:
            startdate = date_tdy - timedelta(3)
            enddate = date_tdy - timedelta(1)
            cachedate = date_tdy - timedelta(4)
        elif date_tdy.weekday() == 0:
            startdate = enddate = date_tdy - timedelta(3)
            cachedate = date_tdy - timedelta(4)
        else:
            startdate = enddate = date_tdy - timedelta(1)
            cachedate = date_tdy - timedelta(2)


        # Importing Caracalla Trading Book
        print("\t 1. Caracalla Trading Book: Positions and PnL")
        df_trades = pnl_sup.get_trades_pnl(account='caracalla', syms=None, startdate=startdate, enddate=enddate)
        #df_cache =


        #out = c_port.fetch_rt_portfolio(ddate=ddate, eod_ddate=eod_date)

        # ***********************************************************************************************************

        print("********** Running Positions and PnL Reports **********")

        # Importing Caracalla Trading Book
        #print("\t 1. Caracalla Trading Book: Positions on %s"%out.timestamp_cest.iloc[0])




    # ***********************************************************************************************************

    if starting_point <= 20:
        print("********** Retrieving Returns from Web **********")

        max_entry_db_rets = db.run_query(query='SELECT MAX(ddate) '
                                               'FROM teams_prd.risk_data.returns_daily_clean').iloc[0][0]

        date_tdy = _datetime.now().date()
        if (date_tdy - timedelta(1)).weekday() == 6:
            actual_ret_date = [date_tdy - timedelta(3)]
        else:
            actual_ret_date = [date_tdy - timedelta(1)]

        if max_entry_db_rets == actual_ret_date:
            print("\n ***** New Return Data Is Available as of %s ******" %actual_ret_date)
        else:
            print("\n ***** Updating Risk Factor Return Data *****")
            dtp.update_rf_returns()

            print("\n ***** Updating Counterparty Price Data *****")
            dtp.update_prx_returns(prx_cat='ctp_banks')

            print("\n ***** Updating CDS Spreads Data *****")
            try:
                dtp.update_inv_cds_spreads(verbose=True)
            except:
                print("\t ERROR while downloading CDS Spreads")

            print("\n ***** Updating Gov Yield Data *****")
            dtp.update_inv_gov_yields(startdate=date_tdy - timedelta(5), enddate=date_tdy, verbose=True)


