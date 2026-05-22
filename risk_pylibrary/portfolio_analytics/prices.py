#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Import Python Modules
from datetime import date
import numpy as np

# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db
from risk_pylibrary.instruments import data_rf_wrapper as rw
from risk_pylibrary.instruments import data_prices as dtp
from risk_pylibrary.risk_analytics import risk_engines as rie





def get_prices_eod():

    """
    Fetches price data for all instruments.

    Returns:
        df (DataFrame): DataFrame containing price data.

    """
    
    qry='''
    SELECT
        *
    FROM
        TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_instrument_prices
    '''

    df=db.run_query(query=qry)

    return df


def get_prices_intraday(syms,startdate,enddate):

    """
    Fetches intraday price data for specified instruments within a date range.
    Args:
        syms (list): List of instrument symbols.
        startdate (date): Start date for price data.
        enddate (date): End date for price data.        

    Returns:
        df (DataFrame): DataFrame containing intraday price data.
    """
    
    qry='''
    SELECT
        *
    FROM
        TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_msl_prices_intraday
    WHERE
        cest_minute::date BETWEEN %s AND %s
    AND
        instrument_id IN (%s)  
    order by 1
    '''

    df=db.run_query(query=qry%(db.sqldate(startdate),
                               db.sqldate(enddate),
                               db.joinpad(syms)))

    return df

