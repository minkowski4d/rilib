#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import pandas as pd
from datetime import datetime as _datetime



def prx2parquet(df_orig=None,upload_date=None,pth=None,verbose=True):
    """
    Function to write Risk Factor Price Data to Parquet files

    @param df_orig: DataFrame with prices data, columns: ['report_date', 'code', 'return_pct', 'data_src_primary']
    @param upload_date: date object, e.g. _datetime(2025,5,30)
    @param pth: str, path to save the parquet files
    @param verbose: boolean, if True prints status messages
    @return: string, path to the saved parquet file
    
    """

    df = df_orig.copy()

    if pth is None:
        raise Exception('\t\t\t\t\t ERROR: You need to Specify a Path for Saving the output')

    # Formatting report_date to string YYYYMMDD
    df['report_date'] = df['report_date'].dt.strftime('%Y%m%d')
    df['upload_date'] = upload_date.strftime('%Y%m%d')
    df=df[['report_date', 'code', 'return_pct', 'data_src_primary', 'upload_date']]

    if verbose:
        print('\n\t\t\t\t Writing Risk Factor Price Data to Parquet')
    
    filename = os.path.join(pth,'%s_mrm_rf_update.parquet'%(upload_date.strftime("%Y%m%d")))

    df.to_parquet(filename, engine='pyarrow', index=False)

    return filename




def rm2parquet(df_orig=None,upload_date=None,pth=None,verbose=True):
    """
    Function to write RiskMetrics Data to Parquet files

    @param df_orig: DataFrame with prices data, columns: ['ddate', 'sec_acc_no','code', 'value']
    @param upload_date: date object, e.g. date(2025,5,30)
    @param pth: str, path to save the parquet files
    @param verbose: boolean, if True prints status messages
    @return: string, path to the saved parquet file
    
    """

    df = df_orig.copy()

    if pth is None:
        raise Exception('\t\t\t\t\t ERROR: You need to Specify a Path for Saving the output')

    # Formatting report_date to string YYYYMMDD
    df.rename(columns={'ddate':'report_date','account':'sec_acc_no'}, inplace=True)
    df['report_date'] = pd.to_datetime(df['report_date'])
    df['report_date'] = df['report_date'].dt.strftime('%Y%m%d')
    df['upload_date'] = upload_date.strftime('%Y%m%d')
    df=df[['report_date', 'sec_acc_no','code', 'value', 'upload_date']]
    df.columns=['report_date', 'sec_acc_no','code', 'rm_value', 'upload_date']

    if verbose:
        print('\n\t\t\t\t Writing Risk Metrics Data to Parquet')
    
    filename = os.path.join(pth,'%s_mrm_trading_book_riskmetrics.parquet'%(upload_date.strftime("%Y%m%d")))

    df.to_parquet(filename, engine='pyarrow', index=False)

    return filename


def rfmapping2parquet(df_orig=None,upload_date=None,pth=None,verbose=True):
    """
    Function to write Risk Factor Mapping Level 1 Data to Parquet files

    @param df_orig: DataFrame with prices data, columns: ['report_date', 'instrument_id', 'risk_factor', 'upload_date']
    @param upload_date: date object, e.g. date(2025,5,30)
    @param pth: str, path to save the parquet files
    @param verbose: boolean, if True prints status messages
    @return: string, path to the saved parquet file
    
    """

    df = df_orig.copy()

    if pth is None:
        raise Exception('\t\t\t\t\t ERROR: You need to Specify a Path for Saving the output')

    # Formatting report_date to string YYYYMMDD
    df['report_date'] = pd.to_datetime(df['report_date'])
    df['report_date'] = df['report_date'].dt.strftime('%Y%m%d')
    df['upload_date'] = upload_date.strftime('%Y%m%d')
    df=df[['report_date', 'instrument_id', 'risk_factor', 'upload_date']]

    if verbose:
        print('\n\t\t\t\t Writing Risk Factor Mapping Level 1 Data to Parquet')
    
    filename = os.path.join(pth,'%s_mrm_rf_mapping.parquet'%(upload_date.strftime("%Y%m%d")))

    df.to_parquet(filename, engine='pyarrow', index=False)

    return filename