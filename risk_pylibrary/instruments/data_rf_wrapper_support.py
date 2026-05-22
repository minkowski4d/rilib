#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import numpy as np
import datetime
from datetime import date
from datetime import datetime as _datetime

# Import Custom Modules
from tools.snowflake_db import db_connection as db


def rf_get_secs_info(df_orig):
    """
    Retrieves Necessary Information from Snowflake

    @param ddate: date that determines dynamic variables (prices, etc.)
    @param verbose: True/False
    @return: dataframe
    """

    df = df_orig.copy()

    # Calculate support KPIs for Bonds
    df['cpn_num2mat'] = (df.last_coupon_date.apply(lambda x: x.year if isinstance(x, date) else x)
                         - df.next_coupon_date.apply(lambda x: x.year if isinstance(x, date) else x) + 1)
    df['cpn_freq'] = df['interest_period'].apply(lambda x: 4 if x == 'QUARTERLY' else 2 if x == 'SEMI_ANNUALLY' else 1 if x == 'ANNUALLY' else np.nan)
    df['cpn_freq_days'] = df['interest_period'].apply(lambda x: 90 if x == 'QUARTERLY' else 180 if x == 'SEMI_ANNUALLY' else 365 if x == 'ANNUALLY' else np.nan)
    df['cpn_num2mat'] = df['cpn_num2mat'] * df['cpn_freq']

    # Calculate time differences to previous and next coupon
    df['cpn_next_in_days'] = df['next_coupon_date'].apply(lambda x: (x - _datetime.today().date()).days if isinstance(x, datetime.date) else x)
    df['cpn_next_in_years'] = df['cpn_next_in_days']/365
    df['cpn_previous_in_days'] = df['cpn_freq_days'] - df['cpn_next_in_days']

    # Set all occurrences with x<0 (no coupon payments so far) to 0
    df['cpn_previous_in_days'] = df['cpn_previous_in_days'].apply(lambda x: 0 if x < 0 else x)
    df['cpn_previous_in_years'] = df['cpn_previous_in_days']/365

    return df



def rf_stocks_country_dict(verbose=True):
    """
    Maps Country ISO 3166-2 Codes to Risk Factor Indices for Stocks
    @return: dictionary
    """

    if verbose:
        print("\t\t Mapping Equity Risk Factors")
        print("\t\t\t Querying TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING")
    qry = '''
            SELECT 
                * 
            FROM 
                TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING 
            WHERE 
                COUNTRY_ISO3166 IS NOT NULL
            '''

    df_rf = db.run_query(query=qry)

    # Unwrap country_iso3166 column to dictionary
    if verbose:
        print("\t\t\t Creating Mapping Dictionary")
    out_dict = dict()
    for idx in df_rf.index:
        if len(df_rf.loc[idx].country_iso3166) > 2:
            for country in df_rf.loc[idx].country_iso3166.split('|'):
                out_dict[country] = df_rf.loc[idx].code
        else:
            out_dict[df_rf.loc[idx].country_iso3166] = df_rf.loc[idx].code


    return out_dict




