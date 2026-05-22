#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Standard Models
import numpy as np

# Model Specific Modules
import statsmodels.api as sm


# Custom Modules
from tools.snowflake_db import db_connection as db



def get_revenue_data(startdate, enddate, adj_weekends, verbose):
    '''
    Aggregated Trading Revenue Data in EUR. Combining all revenue branches in on stream

    @param startdate: date object
    @param enddate: date object
    @param adj_weekends: Bool
    @param verbose: Bool
    @return: DataFrame with revenue data for trading
    '''

    if verbose:
        print('\t Retrieving Data for Revenue Prediction')


    qry = '''
    SELECT
        TRADE_TS::date AS DDATE,
        SUM(REVENUE_BUSINESS_TOTAL) AS REVENUE_TOTAL
    FROM
        TEAMS_PRD.TRANSFORM_TRADE.TRF__TRADE_REVENUE_REVENUE
    WHERE
        TRADE_TS::date >= %s
    AND
        TRADE_TS::date <= %s
    GROUP BY 1
    ORDER BY 1;
    '''

    df_orig = db.run_query(qry%(db.sqldate(startdate), db.sqldate(enddate)))
    df_orig = df_orig.set_index('ddate')

    if adj_weekends:
        df = comp_kpi_weekend_adj(df_orig, verbose)
    else:
        df = df_orig.copy()


    return df


def get_customer_cash_balance(enddate):

    qry = '''
    SELECT
        aum.AUTH_ACCOUNT_ID,
        int_bal.ANNUAL_RATE,
        int_bal.BALANCE_CAP,
        aum.VOLUME AS CASH_TOTAL,
        IFF(aum.VOLUME>int_bal.BALANCE_CAP,int_bal.BALANCE_CAP,aum.VOLUME) AS CASH_PARTNER,
        IFF(aum.VOLUME>int_bal.BALANCE_CAP,aum.VOLUME - int_bal.BALANCE_CAP,0) AS CASH_MMF
    FROM 
        TEAMS_PRD.CORE_MART.MRT_CURR__AUC AS aum
        LEFT JOIN (
            SELECT 
                MRT_USR.AUTH_ACCOUNT_ID,
                MRT_INT.ANNUAL_RATE,
                MRT_INT.BALANCE_CAP
            FROM 
                TEAMS_PRD.INTEREST_MARTS.MRT__INTEREST__INTEREST AS MRT_INT
                LEFT OUTER JOIN (
                    SELECT ACCOUNT_ID,AUTH_ACCOUNT_ID FROM TEAMS_PRD.INTEREST_MARTS.MRT__CURR__INTEREST__USERS
                ) AS MRT_USR
                ON MRT_USR.ACCOUNT_ID = MRT_INT.ACCOUNT_ID
            WHERE
                MRT_INT.VALID_TO_EXCLUSIVE IS NULL
            AND
                MRT_INT.BALANCE_CAP IS NOT NULL
            AND
                MRT_USR.AUTH_ACCOUNT_ID IS NOT NULL
        ) AS int_bal
        ON int_bal.AUTH_ACCOUNT_ID = aum.AUTH_ACCOUNT_ID
    WHERE
        AUM.CALENDAR_DATE = %s
    AND
        AUM.INSTRUMENT_TYPE = 'CASH'
    AND
        AUM.VOLUME <>0
    AND
        AUM.AUTH_ACCOUNT_ID IS NOT NULL;
    '''

    df_orig = db.run_query(qry%(db.sqldate(enddate)))
    df_orig = df_orig.set_index('ddate')



def get_customer_cash_alloc(startdate, enddate, remove_weekends, verbose):

    qry = '''
    SELECT
        AUM.CALENDAR_DATE AS DDATE,
        SUM(AUM.VOLUME) AS VOLUME_EUR
    FROM
        TEAMS_PRD.CORE_MART.MRT_CURR__AUC AS AUM
    WHERE
        CALENDAR_DATE >= %s
    AND
        CALENDAR_DATE <= %s
    AND
        AUM.INSTRUMENT_TYPE in ('STOCK','FUND','BOND','DERIVATIVE','CASH')
    AND
        AUM.VOLUME <>0
    GROUP BY DDATE
    ORDER BY DDATE;
    '''

    df_orig = db.run_query(qry % (db.sqldate(startdate), db.sqldate(enddate)))
    df_orig = df_orig.set_index('ddate')

    if remove_weekends:
        if verbose:
                print('\t Warning: removing weekends for cash allocation data')
        # Remove Weekends:
        df = df_orig.reindex([k for k in df_orig.index if k.weekday() not in [5, 6]])
    else:
        df = df_orig.copy()

    return df




def get_customer_mmf_alloc(startdate, enddate):

    qry = '''
    SELECT
        "created_at"::date AS DDATE,
        SUM(IFF("direction"='SELL', -1*"amount", "amount")) AS VOLUME_EUR
    FROM
        BACKEND_PRD.INTEREST_PLUS.ANONYMIZED_ORDER
    WHERE
        "created_at"::date >= %s
    AND
        "created_at"::date <= %s
    GROUP BY 1
    ORDER BY 1
    '''

    df_orig = db.run_query(qry % (db.sqldate(startdate),db.sqldate(enddate)))
    df_orig = df_orig.set_index('ddate')



    return df_orig


def get_customer_growth(startdate, enddate):

    qry ='''
    WITH cust_data AS (
    -- customer growth per taxed customers
    SELECT 
      "tax_confirmed_at"::DATE AS DDATE,
      COUNT(1) AS CUSTOMERS_PER_DAY
    FROM 
      BACKEND_PRD.CUSTOMER.ANONYMIZED_PERSON
    WHERE
       "tax_confirmed_at"::DATE >= %s
    AND
       "tax_confirmed_at"::DATE <= %s    
    GROUP BY DDATE
    ORDER BY DDATE ASC)
    
    SELECT 
        DDATE, 
        SUM(CUSTOMERS_PER_DAY) OVER (ORDER BY DDATE ASC ROWS BETWEEN unbounded preceding AND CURRENT ROW) AS CUSTOMERS_CUMULATIVE
    FROM
        cust_data;
    '''

    df_orig = db.run_query(qry % (db.sqldate(startdate),db.sqldate(enddate)))
    df_orig = df_orig.set_index('ddate')


    return df_orig



def comp_kpi_weekend_adj(df_orig, verbose):

    if verbose:
        print('\t\t Adjusting Weekend Data (Crypto Trading)')

    df = df_orig.copy()
    df = df.join(df.iloc[:,[0]].reindex([k for k in df.index if k.weekday() == 5]).rename(columns={df.columns[0]: df.columns[0]+'_sat'}))
    df = df.join(df.iloc[:,[0]].reindex([k for k in df.index if k.weekday() == 6]).rename(columns={df.columns[0]: df.columns[0]+'_sun'}))

    # Shifting Observations
    df[df.columns[0]+'_sat'] = df[df.columns[0]+'_sat'].shift(2)
    df[df.columns[0]+'_sun'] = df[df.columns[0]+'_sun'].shift(1)
    df[df.columns[0]+'_total'] = df.sum(axis=1)
    df = df[[df.columns[0]+'_total']]

    # Reindex and slice out weekends
    df = df.reindex([k for k in df.index if k.weekday() != 5])
    df = df.reindex([k for k in df.index if k.weekday() != 6])

    return df


