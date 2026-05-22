#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import logging
import traceback
from datetime import datetime as _datetime
from instruments import data_prices as dtp, data_support as data_sup
from tools import python2s3 as ps3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_FILL_DAYS = 45  # Number of days to fill missing data
DEFAULT_TMP_PATH = os.getenv('TEMP_PATH', '/tmp')
DEFAULT_S3_PATH = os.getenv('S3_PATH', 'risk_write/mr/data/risk_factor_returns')


def main_run_ext_data_update(fill_days=DEFAULT_FILL_DAYS,
                              tmp_path=DEFAULT_TMP_PATH,
                              s3_path=DEFAULT_S3_PATH):
    """
    Main function to update external data sources and store results in S3.

    This function updates Risk Factor Returns and uploads
    the results to an S3 bucket.

    Args:
        fill_days (int): Number of days to fill for missing data (default: 15)
        tmp_path (str): Temporary path for file storage (default: /tmp or TEMP_PATH env var)
        s3_path (str): S3 path for upload (default: risk_write/mr/trading_book/pos or S3_PATH env var)

    Returns:
        dict: Status dictionary with 'success' (bool) and 'message' (str) keys
    """

    logger.info("="*65)
    logger.info("Initialising External Data Update Module from instruments.data_prices")

    # Update Yahoo Finance Risk Factor Returns
    try:
        logger.info("Updating Yahoo Finance Risk Factor Returns")
        out = dtp.update_rf_returns(
            rf_list=None,
            fill_days=fill_days,
            sdate=None,
            edate=None,
            to_db=False,
            verbose=True
        )
        logger.info("Yahoo Finance Risk Factor Returns Update Completed Successfully")

    except Exception as e:
        error_msg = f"Error occurred during Yahoo Finance Risk Factor Returns Update: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {'success': False, 'message': error_msg}

    # Validate output data
    if out is None or out.empty:
        error_msg = "No data returned from Yahoo Finance update"
        logger.error(error_msg)
        return {'success': False, 'message': error_msg}

    # Format output data
    try:
        logger.info("Formatting output data")
        out = out.copy()  # Avoid modifying original data
        out['data_src_primary'] = 'yf'

        # Explicit column mapping instead of positional assignment
        expected_columns = ['report_date', 'code', 'return_pct']
        if len(out.columns) < len(expected_columns):
            error_msg = f"Expected at least {len(expected_columns)} columns, got {len(out.columns)}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

        # Rename columns explicitly
        out = out.iloc[:, :3]  # Take first 3 columns
        out.columns = expected_columns
        out['data_src_primary'] = 'yf'
        out = out[['report_date', 'code', 'return_pct', 'data_src_primary']]

    except Exception as e:
        error_msg = f"Error during data formatting: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {'success': False, 'message': error_msg}

    # Create parquet file
    try:
        logger.info(f"Creating parquet file in {tmp_path}")

        # Ensure tmp_path exists
        os.makedirs(tmp_path, exist_ok=True)

        fname_rf_prx = data_sup.prx2parquet(
            df_orig=out,
            upload_date=_datetime.now().date(),
            pth=tmp_path,
            verbose=True
        )

        if not fname_rf_prx or not os.path.exists(fname_rf_prx):
            error_msg = f"Parquet file creation failed or file not found: {fname_rf_prx}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

        logger.info(f"Parquet file created successfully: {fname_rf_prx}")

    except Exception as e:
        error_msg = f"Error during parquet creation: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {'success': False, 'message': error_msg}

    # Upload to S3
    try:
        logger.info(f"Uploading to S3 bucket: {s3_path}")

        file_name = os.path.basename(fname_rf_prx)
        ps3.save_in_s3(
            local_path=fname_rf_prx,
            path_s3=s3_path,
            file_name=file_name,
            file_type="parquet"
        )

        logger.info(f"File uploaded successfully to S3: {s3_path}/{file_name}")

    except Exception as e:
        error_msg = f"Error during S3 upload: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {'success': False, 'message': error_msg}

    logger.info("External Data Update Module Completed Successfully")
    logger.info("="*65)

    return {
        'success': True,
        'message': 'External data update completed successfully',
        'file_name': file_name,
        'records_processed': len(out)
    }


if __name__ == "__main__":
    result = main_run_ext_data_update()

    if result['success']:
        logger.info(f"Success: {result['message']}")
        if 'records_processed' in result:
            logger.info(f"Records processed: {result['records_processed']}")
    else:
        logger.error(f"Failed: {result['message']}")
        exit(1)