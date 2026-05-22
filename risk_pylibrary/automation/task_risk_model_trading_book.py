#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
import traceback
import pandas as pd
import os
import warnings
from portfolio_analytics import positions as pos
from tools.snowflake_db import db_connection as db
from instruments import data_support as data_sup
from tools import python2s3 as ps3

# Suppress FutureWarning about DataFrame.sum
warnings.filterwarnings('ignore', category=FutureWarning, message='.*DataFrame.sum.*')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setting Variables
DEFAULT_TMP_PATH = os.getenv('TEMP_PATH', '/tmp')
DEFAULT_RM_S3_PATH = os.getenv('S3_PATH', 'risk_write/mr/trading_book/risk')
DEFAULT_RF_MAPPING_S3_PATH = os.getenv('S3_PATH', 'risk_write/mr/data/risk_factor_mapping')


def main_run_trading_book_risk_update(tmp_path=DEFAULT_TMP_PATH,
                                      rm_s3_path=DEFAULT_RM_S3_PATH,
                                      rf_mapping_s3_path=DEFAULT_RF_MAPPING_S3_PATH):
    """
    Main function to calculate risk model figures for trading book accounts.

    This function retrieves cache information from Snowflake and calculates
    risk model figures for a predefined list of trading book accounts.

    Returns:
        dict: Status dictionary with:
            - 'success' (bool): Whether the operation was successful
            - 'message' (str): Status message
            - 'accounts_processed' (list): List of successfully processed account numbers
            - 'results' (dict): Dictionary mapping account numbers to their risk results
    """

    # Setting Current Date:
    ddate = pd.to_datetime('today')

    # Track if any errors occurred during processing
    error_occurred = False
    error_messages = []

    logger.info("="*65)
    logger.info("Initialising Trading Book- Risk Model Calculation")

    # Setting Output
    out_dict = dict()
    out_dict['db_rm_all'] = pd.DataFrame()
    out_dict['rf_mapping'] = pd.DataFrame()

    logger.info("****** Building Cache Info")

    # Get last entry value in risk metrics table (last processed date per account)
    qry_rm_info='''
                    SELECT
                        sec_acc_no,
                        MAX(report_date) AS max_report_date
                    FROM TEAMS_PRD.RISK_FUNCTION_SOURCE.src_curr__risk_function_mrm_trading_book_risk
                    WHERE
                        sec_acc_no<>'bmk_caracalla'
                    GROUP BY
                        sec_acc_no
                    ORDER BY
                        sec_acc_no
                '''

    df_rm_info=db.run_query(query=qry_rm_info)
    df_rm_info=df_rm_info.set_index(['sec_acc_no'])

    # Get Cache Info: ALL dates per account from trading book valuation
    qry_cache_info = '''
                        SELECT DISTINCT
                            sec_acc_no,
                            report_date
                        FROM TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation
                        ORDER BY
                            sec_acc_no,
                            report_date
                    '''

    df_cache_info=db.run_query(query=qry_cache_info)

    # Filter to only process NEW dates (dates newer than last processed date per account)
    logger.info("****** Filtering for new dates to process")

    # Convert report_date columns to datetime for comparison
    df_cache_info['report_date'] = pd.to_datetime(df_cache_info['report_date'])
    if not df_rm_info.empty:
        df_rm_info['max_report_date'] = pd.to_datetime(df_rm_info['max_report_date'])

    # Filter logic: keep only dates newer than last processed date
    if not df_rm_info.empty:
        # Merge to get the last processed date for each account
        df_cache_info = df_cache_info.merge(
            df_rm_info[['max_report_date']],
            left_on='sec_acc_no',
            right_index=True,
            how='left'
        )

        # Keep only rows where report_date > max_report_date (exclude NaT/new accounts)
        df_cache_info = df_cache_info[
            (df_cache_info['report_date'] > df_cache_info['max_report_date']) &
            (~df_cache_info['max_report_date'].isna())
        ]

        # Drop the merge column
        df_cache_info = df_cache_info.drop(columns=['max_report_date'])

    logger.info(f"Found {len(df_cache_info)} new account-date combinations to process")

    if df_cache_info.empty:
        logger.info("No new dates to process. All accounts are up to date.")
        return {
            'success': True,
            'message': 'No new dates to process. All accounts are up to date.',
            'accounts_processed': [],
            'results': {}
        }

    # Looping through accounts and dates to calculate risk figures
    logger.info("****** Updating Trading book Risk Model Figures")
    for idx, row in df_cache_info.iterrows():
        acct = row['sec_acc_no']
        report_date = row['report_date'].date()

        try:
            # Create unique key for this account-date combination
            acct_date_key = f"{acct}_{report_date}"

            out_dict[acct_date_key]=pos.get_port(acct,
                                                 report_date,
                                                 calc_risk=True,
                                                 force_rf=True)

            # Append Model Data
            out_dict['db_rm_all']=pd.concat([out_dict['db_rm_all'],
                                             out_dict[acct_date_key]['out_db_rm']],
                                             ignore_index=True)

            # Append Risk Factor Mapping Data
            out_dict['rf_mapping']=pd.concat([out_dict['rf_mapping'],
                                             out_dict[acct_date_key]['inventory'][['report_date','instrument_id','risk_factor']]],
                                             ignore_index=True)

            logger.info(f"Successfully processed account {acct} for date {report_date}")
        except Exception as e:
            error_msg = f"Error occurred during Risk Model Update on {acct} for date {report_date}: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            error_occurred = True
            error_messages.append(error_msg)
            # Continue processing other account-date combinations instead of returning early

    logger.info("****** Trading Book Risk Model Figures Update Completed Successfully")

    # Check if we have any results to save
    accounts_processed = [k for k in out_dict.keys() if k not in ['db_rm_all', 'rf_mapping']]

    if not accounts_processed:
        error_msg = "No accounts were successfully processed"
        logger.error(error_msg)
        return {'success': False, 'message': error_msg}


    # ------------------------------------------------------------------------------------
    # Creating output for risk metrics data to S3 storage
    try:
        logger.info(f"Creating parquet file for risk metrics data in {tmp_path}")

        # Ensure tmp_path exists
        os.makedirs(tmp_path, exist_ok=True)

        fname_rm = data_sup.rm2parquet(
            df_orig=out_dict['db_rm_all'],
            upload_date=ddate,
            pth=tmp_path,
            verbose=True
        )

        if not fname_rm or not os.path.exists(fname_rm):
            error_msg = f"Parquet file creation failed or file not found: {fname_rm}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

        logger.info(f"\t\t Parquet file created successfully: {fname_rm}")

    except Exception as e:
        error_msg = f"Error during parquet creation: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        error_occurred = True
        return {'success': False, 'message': error_msg}

    # Upload to S3
    try:
        logger.info(f"***** Uploading to Risk Metrics S3 bucket: {rm_s3_path}")

        file_name = os.path.basename(fname_rm)
        ps3.save_in_s3(
            local_path=fname_rm,
            path_s3=rm_s3_path,
            file_name=file_name,
            file_type="parquet"
        )

        logger.info(f"File uploaded successfully to S3: {rm_s3_path}/{file_name}")

    except Exception as e:
        error_msg = f"Error during Risk Metrics S3 upload: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        error_occurred = True
        return {'success': False, 'message': error_msg}


    # ------------------------------------------------------------------------------------
    # Creating output for risk factor mapping to S3 storage
    try:
        logger.info(f"Creating parquet file for risk factor mapping data in {tmp_path}")

        # Ensure tmp_path exists
        os.makedirs(tmp_path, exist_ok=True)

        fname_rf_mapping = data_sup.rfmapping2parquet(
            df_orig=out_dict['rf_mapping'],
            upload_date=ddate,
            pth=tmp_path,
            verbose=True
        )

        if not fname_rf_mapping or not os.path.exists(fname_rf_mapping):
            error_msg = f"Parquet file creation failed or file not found: {fname_rf_mapping}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

        logger.info(f"\t\t Parquet file created successfully: {fname_rf_mapping}")

    except Exception as e:
        error_msg = f"Error during parquet creation: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        error_occurred = True
        return {'success': False, 'message': error_msg}

    # Upload to S3
    try:
        logger.info(f"***** Uploading to Risk Factor Mapping S3 bucket: {rf_mapping_s3_path}")

        file_name = os.path.basename(fname_rf_mapping)
        ps3.save_in_s3(
            local_path=fname_rf_mapping,
            path_s3=rf_mapping_s3_path,
            file_name=file_name,
            file_type="parquet"
        )

        logger.info(f"File uploaded successfully to S3: {rf_mapping_s3_path}/{file_name}")

    except Exception as e:
        error_msg = f"Error during Risk Factor Mapping S3 upload: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        error_occurred = True
        return {'success': False, 'message': error_msg}

    # Check if we had any errors during processing
    if error_occurred:
        combined_error_msg = "One or more accounts failed to process:\n" + "\n".join(error_messages)
        logger.error(combined_error_msg)
        print("\nERROR: One or more accounts failed to process. Check logs above for details.")
        return {'success': False, 'message': combined_error_msg}

    logger.info(f"Successfully processed {len(accounts_processed)} accounts")
    logger.info("Trading Book Risk Model Update Completed Successfully")
    logger.info("="*65)

    return {
        'success': True,
        'message': f'Trading book risk model update completed successfully for {len(accounts_processed)} accounts',
        'accounts_processed': accounts_processed,
        'results': out_dict
    }


if __name__ == "__main__":
    result = main_run_trading_book_risk_update()

    if result['success']:
        logger.info(f"Success: {result['message']}")
        if 'accounts_processed' in result:
            logger.info(f"Accounts processed: {result['accounts_processed']}")
    else:
        logger.error(f"Failed: {result['message']}")
        exit(1)