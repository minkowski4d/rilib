#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import traceback
# Import Python Modules
import numpy as np
import pandas as pd
from datetime import datetime as _datetime, date, timedelta
from risk_models import pnl_fifo
from tools import python2s3 as ps3
from tools.snowflake_db import db_connection as db




def hist_run_pnl_fifo(accts,startdate,enddate,ca_sd,pth):
    """
    Historical rerun function to run PnL FIFO calculation for trading book accounts and store results in pth.
    This function retrieves the latest cache information from a Snowflake database,
    processes PnL data for specified accounts, and uploads the results to an S3 bucket.
 
    """

    print("\n-----------------------------------------------------------------")
    print("Initialising PnL FIFO module for Historical Rerun")

    # Initialising Loop over Accounts:
    for acct in accts:
        print(f"\tRunning PnL FIFO for account: {acct}")
        try:
            print(f"\t\t\tProcessing data from {startdate} to {enddate}")
            
            if acct in [9800001301, 9800003301]:
                # Initiate the PnL engine
                print("\t\tOn Share Booking Data")
                out_dict = pnl_fifo.initiate_pnl_engine(acct, startdate, enddate, ca_sd, 1, 1, 0, 'share_booking', 'old', pth, 0)

            else:
                # Initiate the PnL engine
                print("\t\tOn Inquisitor Data")
                out_dict = pnl_fifo.initiate_pnl_engine(acct, startdate, enddate, ca_sd, 1, 1, 0, 'inquisitor', 'new', pth, 0)


        except Exception as e:
            print(f"\t\tError processing account {acct}: {e}")
            print(traceback.format_exc())
            continue


        print("\n-----------------------------------------------------------------")

    # Running Some Checks:
    print('\t\t\t Analytices on OutPut Data:\n')

    # Pos
    print('\t\t\t\t Startdate Pos: %s'%out_dict['out_pos'].ddate.iloc[0])
    print('\t\t\t\t Enddate Pos: %s'%out_dict['out_pos'].ddate.iloc[-1])

    # Cache
    print('\t\t\t\t Length of Cache: %s'%len(out_dict['out_cache']))
    print('\t\t\t\t Number of Symbols: %s'%len(out_dict['out_cache'].symbol.unique()))

    # PnL
    print('\t\t\t\t Total Realised PnL: %s'%np.round(out_dict['out_pos'].rpnl.sum(),2))
    # Looping through urnealised PnL:
    for dd in out_dict['out_pos'].ddate.unique():
        rp=np.round(out_dict['out_pos'][out_dict['out_pos'].ddate==dd].rpnl.sum(),2)
        up=np.round(out_dict['out_pos'][out_dict['out_pos'].ddate==dd].upnl.sum(),2)
        print('\t\t\t\t %s - Total Realised: %s, Unrealised PnL: %s'%(dd,rp,up))


    while True:
        answer = input("Do you want to proceed? (yes/no): ").strip().lower()
        if answer in ("yes", "y"):
            print("Proceeding with data upload")
            # Upload Files:
            ps3.save_in_s3_local(local_path=out_dict['fname_pnl'], path_s3="risk_write/mr/trading_book/pos", file_name=out_dict['fname_pnl'].split('/')[-1], file_type="parquet")
            ps3.save_in_s3_local(local_path=out_dict['fname_cache'], path_s3="risk_write/mr/trading_book/cache", file_name=out_dict['fname_cache'].split('/')[-1], file_type="parquet")
            return out_dict

        elif answer in ("no", "n"):
            print("Exiting...")
            return out_dict
        else:
            print("Please answer yes or no.")
    


def cache_chk(acct):
    """
    Check if Cache has been loaded
    """
    qry_cache_info = '''
                    SELECT
                        sec_acc_no,
                        data_src_primary,
                        MAX(report_date) AS max_report_date
                    FROM TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__MRM_TRADING_BOOK_PNL_CACHE
                    WHERE sec_acc_no=%s
                    GROUP BY
                        sec_acc_no,
                        data_src_primary
                    ORDER BY
                        sec_acc_no,
                        data_src_primary;
                '''

    df_cache_info=db.run_query(query=qry_cache_info%acct)
    df_cache_info=df_cache_info.set_index(['sec_acc_no','data_src_primary'])

    print(df_cache_info)

def cache_chk_symbol(acct,symbol,ddate,data_src):
    """
    Docstring for cache_chk_symbol
    
    :param acct: Description
    :param symbol: Description
    :param ddate: Description
    :param data_src: Description
    """
    qry_cache_info = '''
                    SELECT
                        *
                    FROM TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__MRM_TRADING_BOOK_PNL_CACHE
                    WHERE sec_acc_no=%s
                    AND instrument_id='%s'
                    AND report_date::date = %s
                    AND data_src_primary='%s'
                    ORDER BY
                        sec_acc_no,
                        data_src_primary;
                '''

    df_cache_info=db.run_query(query=qry_cache_info%(acct,symbol,db.sqldate(ddate),data_src))
    df_cache_info=df_cache_info.set_index(['sec_acc_no','data_src_primary'])

    return df_cache_info





def run_perf_analytics(acct,syms,sdate,edate,ca_sd):

    out_dict = pnl_fifo.initiate_pnl_engine(acct,
                                            sdate,
                                            edate,
                                            date(2026,2,27),
                                            1, 1, 0,
                                            'share_booking',
                                            'old',
                                            '~/Downloads',
                                            0)

    df_trades = out_dict['cache_dict']['df_trades'].copy()[['time','symbol','quantity_signed','price','booking_category','booking_type']]
    df_trade_pnl = out_dict['out_trade_pnl'].copy()
    df_trade_pnl.index.name = 'time'
    df_trade_pnl = df_trade_pnl.reset_index()[['time','symbol','rpnl']]

    # Filter for syms
    df_trades = df_trades[df_trades.symbol.isin(syms)]
    df_trade_pnl = df_trade_pnl[df_trade_pnl.symbol.isin(syms)]
    
    tmp = df_trades.merge(df_trade_pnl, on=['time','symbol'], how='left')

    # Remove zero rpnl rows and floor time to minute
    out = tmp[tmp['rpnl'] != 0]
    out['time'] = out['time'].dt.floor('min')

    out_pnl = out.groupby(['time','symbol']).agg(quantity_signed=('quantity_signed', 'sum'),
                                                 price=('price', 'mean'),
                                                 booking_category=('booking_category', 'first'),
                                                 booking_type=('booking_type', 'first'),
                                                 rpnl=('rpnl', 'sum')).reset_index()

    out = out_pnl.pivot(index='time', columns='symbol', values='rpnl').fillna(0).cumsum()
    out.columns = pd.MultiIndex.from_product([['rpnl'], out.columns])
    out_trades = out_pnl.pivot(index='time', columns='symbol', values='quantity_signed').fillna(0)
    out_trades.columns = pd.MultiIndex.from_product([['trades'], out_trades.columns])

    out = pd.concat([out,out_trades],axis=1)


    return out

    









