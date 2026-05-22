#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from datetime import timedelta, date,  datetime as _datetime
from risk_models import pnl_fifo_daily_reset as pnl_fifo
from tools.snowflake_db import db_connection as db
from tools import python2s3 as ps3
import traceback
import sys



def main_run_pnl_fifo_daily_reset():
    """
    Main function to run PnL FIFO calculation for trading book accounts and store results in S3.
    This function retrieves the latest cache information from a Snowflake database,
    processes PnL data for specified accounts, and uploads the results to an S3 bucket.
    """

    print("\n\n\n\n-----------------------------------------------------------------")
    print("Initialising PnL FIFO module from risk_models")

    # Track if any errors occurred during processing
    error_occurred = False

    # Set output path:
    pth='/tmp'

    # Set enddate:
    enddate=_datetime.now().date()-timedelta(1)

    print("\n\tBuilding Cache Info")
    # Get Cache Info:
    qry_cache_info = '''
                        SELECT
                            sec_acc_no,
                            data_src_primary,
                            MAX(report_date) AS max_report_date
                        FROM TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__MRM_TRADING_BOOK_PNL_CACHE
                        WHERE data_src_primary IN ('inquisitor_daily_reset')
                        GROUP BY
                            sec_acc_no,
                            data_src_primary
                        ORDER BY
                            sec_acc_no,
                            data_src_primary;
                    '''
    
    df_cache_info=db.run_query(query=qry_cache_info)
    df_cache_info=df_cache_info.set_index(['sec_acc_no','data_src_primary'])

    # Initialising Loop over Accounts:
    for acct in [9800003601,9800001601]: 

        print(f"\tRunning PnL FIFO for account: {acct}")

        try:
            # Get the last cache date for the account; fall back to full load if no cache exists
            if (str(acct), 'inquisitor_daily_reset') in df_cache_info.index:
                ca_sd=df_cache_info.loc[(str(acct),'inquisitor_daily_reset')].iloc[0].date()
                print(f"\t\tOn Inquisitor Data - Starting Cache from {ca_sd}")
            else:
                ca_sd=_datetime(2025, 1, 16).date()
                print(f"\t\tNo Snowflake cache found for {acct} - full load from {ca_sd}")

            # Setting start and end date for PnL calculation
            startdate=ca_sd+timedelta(1)

            if startdate >= _datetime.now().date():
                print(f"\t\t\tNo new data to process for account {acct}. Skipping...")
                continue
            else:
                print(f"\t\t\tProcessing data from {startdate} to {enddate}")

                print("\t\tOn Inquisitor Data")
                out_dict = pnl_fifo.initiate_pnl_engine(acct, ca_sd+timedelta(1), enddate, ca_sd, 1, 1, 0,'inquisitor_daily_reset', 'daily_reset', pth,syms=None,verbose= 0)
                
                # Save the output to S3
                print("\t\t\tSaving output for account")
                if out_dict['fname_pnl'] is None:
                    print(f"\t\t\tNo PnL parquet produced for account {acct} (no price data for the period) — skipping S3 upload")
                else:
                    ps3.save_in_s3(local_path=out_dict['fname_pnl'], path_s3="risk_write/mr/trading_book/pos", file_name=out_dict['fname_pnl'].split('/')[-1], file_type="parquet")

                if out_dict['fname_cache'] is None:
                    print(f"\t\t\tNo cache parquet produced for account {acct} (no price data for the period) — skipping S3 upload")
                else:
                    ps3.save_in_s3(local_path=out_dict['fname_cache'], path_s3="risk_write/mr/trading_book/cache", file_name=out_dict['fname_cache'].split('/')[-1], file_type="parquet")
        
        except Exception as e:
            print(f"\t\tError processing account {acct}: {e}")
            print(traceback.format_exc())
            error_occurred = True
            continue

    print("\n-----------------------------------------------------------------")

    # Exit with failure code if any errors occurred during processing
    if error_occurred:
        print("\nERROR: One or more accounts failed to process. Check logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    out = main_run_pnl_fifo_daily_reset()



