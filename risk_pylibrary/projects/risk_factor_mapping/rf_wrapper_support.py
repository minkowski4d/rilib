#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import numpy as np
import pandas as pd
import datetime
from datetime import timedelta
from datetime import datetime as _datetime

# Import Custom Modules
from risk_pylibrary.tools import config as CF
from tools.snowflake_db import db_connection as db







def rf_get_secs_info(ddate, ddate_pos, verbose=True):
    """
    Retrieves Necessary Information from Snowflake

    @param ddate: date that determines dynamic variables (prices, etc.)
    @param verbose: True/False
    @return: dataframe
    """


    qry = '''
        with ALL_SYMBOLS as (
        SELECT
            DISTINCT(INSTRUMENT_ID) AS INSTRUMENT_ID
        FROM
            TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation AS POS
        WHERE
            POS.REPORT_DATE = %s
        ORDER BY 1
        ),
        -- Secs Info 1 for Instrument Type and Name
        SECS_INFO_0 as (
        SELECT 
            SECS.INSTRUMENT_ID,
            SECS.INSTRUMENT_TYPE,
            SECS.NAME_SHORT
        FROM 
            TEAMS_PRD.CORE_MART.MRT_CURR__INSTRUMENTS AS SECS
        WHERE
            SECS.INSTRUMENT_ID in (SELECT ALL_SYMBOLS.INSTRUMENT_ID FROM ALL_SYMBOLS)
        ),
        
        SECS_INFO_1 as (
        SELECT 
          BONDS_INFO."isin" AS INSTRUMENT_ID,
          BONDS_ISSUER_INFO."issuer_classification" AS ASSET_TYPE,
          BONDS_ISSUER_INFO."issuer_name" AS ISSUER_NAME,
          BONDS_INFO."interest_period" AS INTEREST_PERIOD,
          BONDS_INFO."last_coupon_date" AS LAST_COUPON_DATE,
          BONDS_INFO."interest_rate" AS COUPON,
          BONDS_INFO."accrued_interest" AS ACCRUED_INTEREST,
          BONDS_INFO."emission_date" AS EMISSION_DATE,
          BONDS_INFO."maturity_date" AS MATURITY_DATE,
          BONDS_INFO."next_coupon_date" AS NEXT_COUPON_DATE,
          -- Trading
          BONDS_INFO."emission_volume" AS EMISSION_VOLUME,
          BONDS_INFO."min_nominal_amount" AS MIN_NOMIAL_AMOUNT,
          BONDS_INFO."step_nominal_amount" AS STEP_NOMINAL_AMOUNT
        FROM 
            BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__BOND AS BONDS_INFO
            INNER JOIN 
                BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__ISSUER AS BONDS_ISSUER_INFO
            ON 
                BONDS_ISSUER_INFO."lei" = BONDS_INFO."issuer_lei"
        WHERE
            BONDS_INFO."isin" in (SELECT ALL_SYMBOLS.INSTRUMENT_ID FROM ALL_SYMBOLS)
        ),
        -- WM DATA
        SECS_INFO_2 as (
        SELECT
            WM."isin" AS INSTRUMENT_ID,
            WM.gd172::text AS CURRENCY,
            WM.gd161::text AS COUNTRY,
            WM.gd162::text AS ISSUER_COUNTRY
        FROM
            teams_prd.source_instrument_partners.src__instrument_partners__wmdaten_instruments_view AS WM
        WHERE
            WM."isin" in (SELECT ALL_SYMBOLS.INSTRUMENT_ID FROM ALL_SYMBOLS)
        ),
        -- RATING DATA
        SECS_INFO_3 as (
        SELECT
            RAT.INSTRUMENT_ID AS INSTRUMENT_ID,
            RAT.RATING_SP AS RATING_SP,
            RAT.RATING_SP AS RATING_MOODYS,
            -- Map High Yield and Investment Grade
            CASE
                WHEN RAT_SCALE.RATING_NUM <= 50 THEN 'HY'
                WHEN RAT_SCALE.RATING_NUM > 50 THEN 'IG'
                ELSE NULL
            END AS RATING_GROUP,
            RAT_SCALE.RATING_NUM AS RATING_NUM,
            RAT_SCALE.RATING_CLASS AS RATING_CLASS
        FROM
            TEAMS_PRD.RISK_DATA.RISK_FACTOR_BOND_RATINGS AS RAT
            LEFT JOIN
                (SELECT RATING_SP,RATING_NUM,RATING_CLASS FROM TEAMS_PRD.RISK_DATA.RISK_FACTOR_RATING_SCALE) AS RAT_SCALE
            ON RAT_SCALE.RATING_SP = RAT.RATING_SP
        ),      
        
        
        -- EOD Prices
        EOD_PRICES as (
        SELECT
            PR.PRICE_DT as DDATE, 
            PR.INSTRUMENT_ID as INSTRUMENT_ID,
            PR.CLOSE_MID_PRICE AS CLOSE_MID_PRICE
        FROM 
            TEAMS_PRD.TRANSFORM_AUM.TRF__AUM__EOD_PRICE_FEED as PR
        WHERE
            pr.price_dt = %s
        AND
            pr.EXCHANGE = 'LSX'
        AND
            PR.INSTRUMENT_ID in (SELECT ALL_SYMBOLS.INSTRUMENT_ID FROM ALL_SYMBOLS)
        ORDER BY 1,2
        )
        
        SELECT
            ALL_SYMBOLS.*,
            SECS_INFO_0.NAME_SHORT,
            SECS_INFO_0.INSTRUMENT_TYPE,
            SECS_INFO_2.CURRENCY,
            SECS_INFO_2.COUNTRY,
            SECS_INFO_2.ISSUER_COUNTRY,
            CASE 
                WHEN SECS_INFO_0.INSTRUMENT_TYPE='STOCK' THEN 'STOCK'
                WHEN SECS_INFO_0.INSTRUMENT_TYPE='FUND' THEN 'FUND'
                WHEN SECS_INFO_0.INSTRUMENT_TYPE NOT IN ('FUND','STOCK','BOND') THEN 'STOCK'
                ELSE SECS_INFO_1.ASSET_TYPE
            END AS ASSET_TYPE,
            SECS_INFO_1.ISSUER_NAME,
            SECS_INFO_3.RATING_SP AS RATING_SP,
            SECS_INFO_3.RATING_SP AS RATING_MOODYS,
            SECS_INFO_3.RATING_NUM AS RATING_NUM,
            SECS_INFO_3.RATING_GROUP AS RATING_GROUP,
            SECS_INFO_3.RATING_CLASS AS RATING_CLASS,
            SECS_INFO_1.INTEREST_PERIOD,
            SECS_INFO_1.COUPON,
            SECS_INFO_1.ACCRUED_INTEREST AS ACCRUED_INTEREST,
            SECS_INFO_1.EMISSION_DATE,
            SECS_INFO_1.MATURITY_DATE,
            DIV0(SECS_INFO_1.MATURITY_DATE - current_date(), 365) as YEARS_TO_MATURITY,
            SECS_INFO_1.NEXT_COUPON_DATE,
            SECS_INFO_1.LAST_COUPON_DATE,
            -- Trading
            SECS_INFO_1.EMISSION_VOLUME,
            SECS_INFO_1.MIN_NOMIAL_AMOUNT,
            SECS_INFO_1.STEP_NOMINAL_AMOUNT,
            -- Aggregates
            IFF(SECS_INFO_0.INSTRUMENT_TYPE = 'BOND',DIV0(EOD_PRICES.CLOSE_MID_PRICE, 100), EOD_PRICES.CLOSE_MID_PRICE)  AS EOD_PRICE_CLEAN,
            CASE
                WHEN SECS_INFO_1.COUPON IS NULL AND SECS_INFO_0.INSTRUMENT_TYPE = 'BOND' THEN EOD_PRICE_CLEAN
                ELSE IFF(SECS_INFO_0.INSTRUMENT_TYPE = 'BOND',DIV0(EOD_PRICES.CLOSE_MID_PRICE+ACCRUED_INTEREST, 100), EOD_PRICES.CLOSE_MID_PRICE+ACCRUED_INTEREST)
            END AS EOD_PRICE_DIRTY,
            CASE
                WHEN SECS_INFO_1.COUPON IS NULL AND SECS_INFO_0.INSTRUMENT_TYPE = 'BOND' THEN (DIV0((1-EOD_PRICE_CLEAN),YEARS_TO_MATURITY))/((1+EOD_PRICE_CLEAN)/2)
                ELSE (SECS_INFO_1.COUPON +DIV0((1-EOD_PRICE_CLEAN),YEARS_TO_MATURITY))/((1+EOD_PRICE_CLEAN)/2)
            END AS YIELD_TO_MATURITY,
            CASE
                WHEN SECS_INFO_1.COUPON IS NULL AND SECS_INFO_0.INSTRUMENT_TYPE = 'BOND' THEN YIELD_TO_MATURITY
                ELSE DIV0(SECS_INFO_1.COUPON,EOD_PRICE_CLEAN)
            END AS CURRENT_YIELD,
            IFF(SECS_INFO_1.COUPON IS NULL AND SECS_INFO_0.INSTRUMENT_TYPE = 'BOND', 1, 0) AS IS_ZEROCPN
        FROM
            ALL_SYMBOLS
            LEFT JOIN
                SECS_INFO_0
            ON
                SECS_INFO_0.INSTRUMENT_ID = ALL_SYMBOLS.INSTRUMENT_ID
            LEFT JOIN
                EOD_PRICES
            ON
                EOD_PRICES.INSTRUMENT_ID = ALL_SYMBOLS.INSTRUMENT_ID
            LEFT JOIN
                SECS_INFO_1
            ON
                SECS_INFO_1.INSTRUMENT_ID = ALL_SYMBOLS.INSTRUMENT_ID
            LEFT JOIN
                SECS_INFO_2
            ON
                SECS_INFO_2.INSTRUMENT_ID = ALL_SYMBOLS.INSTRUMENT_ID
            LEFT JOIN
                SECS_INFO_3
            ON
                SECS_INFO_3.INSTRUMENT_ID = ALL_SYMBOLS.INSTRUMENT_ID;
    '''

    dt_ddate_pos = _datetime(ddate_pos.year, ddate_pos.month, ddate_pos.day, 23, 59, 59)
    df = db.run_query(query=qry%(db.sqldate(dt_ddate_pos),db.sqldate(ddate)))


    # Calculate support KPIs for Bonds
    df['cpn_num2mat'] = (df.last_coupon_date.apply(lambda x: x.year if isinstance(x, datetime.date) else x)
                         - df.next_coupon_date.apply(lambda x: x.year if isinstance(x, datetime.date) else x) + 1)
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




