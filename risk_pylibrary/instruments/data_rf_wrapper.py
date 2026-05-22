#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import numpy as np
import traceback
import pandas as pd

# Import Custom Modules
from instruments import data_rf_wrapper_support as rfws
from tools.snowflake_db import db_connection as db




def rf_mapping_engine(df, verbose):


    # Basis Data Set
    count_print_str = 1
    if verbose:
        print("\t ********** Initialising Risk Factor Mapping Engine **********")
        print("\t\t %s. Retrieving GenericSecurity Information"%count_print_str)
        count_print_str += 1

    df_orig = rfws.rf_get_secs_info(df)

    # Country Dict
    if verbose:
        print("\t\t %s. Retrieving Equity Country Mapping"%count_print_str)
        count_print_str += 1

    out_dict = rfws.rf_stocks_country_dict(verbose)

    # Map Equity (Stocks & ETF) Risk Factors
    if verbose:
        print("\t\t %s. Mapping Equity Risk Factors" % count_print_str)
        count_print_str += 1

    df = build_equity_mapping(df_orig, out_dict)

    # Map Bond Risk Factors
    if verbose:
        print("\t\t %s. Mapping Bond Risk Factors" % count_print_str)
        count_print_str += 1

    df = bonds_mapping_risk_factors(df, verbose)

    # Calculate Bond Analytics
    if verbose:
        print("\t\t %s. Calculating Bond Analytics" % count_print_str)
        count_print_str += 1

    # from risk_pylibrary.projects.econometrics import bond_analytics as ba
    # df = ba.bonds_dur_conv(df, 1)

    # Map Funds & ETF Risk Factors
    if verbose:
        print("\t\t %s. Mapping ETF Risk Factors" % count_print_str)
        count_print_str += 1

    df = build_funds_mapping(df, out_dict)


    # Map Residuals:
    if verbose:
        print("\t\t %s. Mapping Residual Risk Factors" % count_print_str)
        count_print_str += 1

    # Mapping FX Spot and Crypto
    out_dict_instr = {'7244472562215223296':'fx_eurpln','XF000BTC0017':'btc_eur','XF000ETH0015':'eth_eur',
                      'XF000XRP0018':'xrp_eur'}

    df = build_residual_over_instr_mapping(df, out_dict_instr)


    # Mapping Currency Residuals
    out_dict_res = {'EUR':'msci_europe','AUD':'msci_australia', 'USD':'sp500', 'HKD':'msci_pacific_ex_jp',
                'GBP':'ftse100', 'BRL':'msci_emerging', 'CAD':'msci_canada', 'RUB':'msci_eastern_europe',
                'ILS':'msci_emerging', 'CNY':'msci_pacific_ex_jp', 'CZK':'msci_emerging', 'CHF':'msci_switzerland',
                'JPY':'nikkei225', 'DKK':'msci_europe', 'SEK':'msci_europe',
                'IDR':'msci_pacific_ex_jp', 'HUF':'msci_emerging', 'SGD':'msci_pacific_ex_jp',
                'MXN':'msci_emerging', 'NOK':'msci_europe', 'PGK':'msci_pacific_ex_jp',
                'PLN':'msci_emerging', 'THB':'msci_pacific_ex_jp', 'NZD':'msci_australia', 'MAD':'msci_emerging',
                'TWD':'msci_pacific_ex_jp', 'TRY':'msci_emerging', 'ARS':'msci_emerging', 'COP':'msci_emerging',
                'KZT':'msci_emerging', 'KRW':'msci_pacific_ex_jp', 'INR':'msci_emerging', 'ZAR':'msci_emerging',
                'PEN':'msci_emerging','PHP':'msci_pacific_ex_jp'}

    df = build_residual_over_ccy_mapping(df, out_dict_res)


    return df



def bonds_mapping_risk_factors(df_orig, verbose):
    """
    Wrapper for Yield Curve Notches

    @param df: output of rws.rf_get_secs_info()
    @param verbose:
    @return: Enriched DataFrame (one column: risk_factor)
    """

    # Split Original DataFrame
    df = df_orig[df_orig.instrument_type == 'BOND']

    # Get Yield Curves Library
    if verbose:
        print("\n\n\t ***** Retrieving Stored Yields Data *****")

    df_gov_yields = db.run_query(query="SELECT * FROM TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING_GOV_BONDS")
    cty_yields = list(df_gov_yields.country_iso3166_origin.unique())
    missing_cty = [k for k in df.country.unique() if k not in cty_yields]

    # Get Yield Curves Library
    if verbose:
        print("\t\n ***** Retrieving Stored OAS Data *****")

    df_oas = db.run_query(query="SELECT * FROM TEAMS_PRD.RISK_DATA.RISK_FACTOR_MAPPING_OAS")
    df_oas = df_oas[df_oas.mapping.isin(['US', 'EU'])]
    df_oas_ig = df_oas[~df_oas.maturity.str.endswith('HY')]
    df_oas_ig['mat_mid'] = [int(k.split("-")[0]) + 1 for k in df_oas_ig.maturity]


    df['risk_factor'] = None
    df['oas_series'] = None
    df['risk_factor'] = df['risk_factor'].astype('object')
    df['oas_series'] = df['oas_series'].astype('object')
    unmapped_ids = []
    for j in df.index:
        cty = 'DE' if df.loc[j].country in missing_cty else df.loc[j].country
        mat = df.loc[j].years_to_maturity
        ll_mty = list(df_gov_yields[df_gov_yields.country_iso3166_origin == cty].maturity)
        ll_mty = [0 if k == 'Overnight' else int(k[:-1])/12 if k[-1] == 'M' else int(k[:-1]) for k in ll_mty]
        try:
            closest_mat = min(ll_mty, key=lambda x: abs(mat - x))
            horizon = 'Y' if closest_mat >= 1 else 'M' if closest_mat <= 1 else 'Overnight'
            mat_id = str(int(closest_mat)
                         if horizon == 'Y'
                         else int(closest_mat*12) if horizon == 'M' else '') + horizon
            df.loc[j, 'risk_factor'] = df_gov_yields[(df_gov_yields.country_iso3166_origin == cty)
                                                    & (df_gov_yields.maturity == mat_id)].instrument_id.iloc[0]
        except:
            print(traceback.format_exc())
            if verbose:
                print('\t\t ERROR: Could not map %s to any Risk Factor'%df.loc[j].instrument_id)
            unmapped_ids = unmapped_ids + [df.loc[j].instrument_id]

        # Mapping Investment Grade OAS Series
        if df.loc[j].asset_type == 'CORPORATE':
            if df.loc[j].country == 'US' and df.loc[j].rating_group != 'HY':
                closest_oas = min(list(df_oas_ig[(df_oas_ig.mapping == 'US')].mat_mid), key=lambda x: abs(mat - x))
                df.loc[j, 'oas_series'] = df_oas_ig[(df_oas_ig.mat_mid == closest_oas)
                                                    & (df_oas_ig.mapping == 'US')].code_oas.iloc[0]

            elif df.loc[j].country != 'US' and df.loc[j].rating_group != 'HY':
                closest_oas = min(list(df_oas_ig[(df_oas_ig.mapping != 'US')].mat_mid), key=lambda x: abs(mat - x))
                df.loc[j, 'oas_series'] = df_oas_ig[(df_oas_ig.mat_mid == closest_oas)
                                                    & (df_oas_ig.mapping != 'US')].code_oas.iloc[0]


    # Bulk Mapping High Yield OAS Series
    # US
    df.loc[(df.rating_group == 'HY') & (df.country == 'US'), 'oas_series'] = df_oas[(df_oas.mapping == 'US')
                                                                                    & (df_oas.maturity == 'US_HY')].code_oas.iloc[0]
    # EUR
    df.loc[(df.rating_group == 'HY') & (df.country != 'US'), 'oas_series'] = df_oas[(df_oas.mapping != 'US')
                                                                                    & (df_oas.maturity == 'EUR_HY')].code_oas.iloc[0]
    # Rename Corporate/Credit Risk Factors
    df.loc[(~df.oas_series.isnull()) & (df.rating_group == 'HY'), 'risk_factor'] = df.loc[(~df.oas_series.isnull())
                                                                                          & (df.rating_group == 'HY'), 'risk_factor'].replace('YIELD', 'HY_CREDIT', regex=True)
    df.loc[(~df.oas_series.isnull()) & (df.rating_group != 'HY'), 'risk_factor'] = df.loc[(~df.oas_series.isnull())
                                                                                          & (df.rating_group != 'HY'), 'risk_factor'].replace('YIELD', 'IG_CREDIT', regex=True)

    if verbose:
        print("\t\n ***** WARNING: %s instruments could not be mapped *****"%len(unmapped_ids))


    df = pd.concat([df, df_orig[df_orig.instrument_type != 'BOND']], axis=0)

    return df







def build_equity_mapping(df, out_dict):

    df.loc[df.instrument_type == 'STOCK', 'risk_factor'] = df.loc[df.instrument_type == 'STOCK', 'country'].map(out_dict)

    # Hardcode Berkshire A
    df.loc[df.instrument_id == 'US0846701086', 'risk_factor'] = 'brk_a'

    return df

def build_funds_mapping(df, out_dict):

    df.loc[df.instrument_type == 'FUND', 'risk_factor'] = df.loc[df.instrument_type == 'FUND', 'country'].map(out_dict)

    return df

def build_residual_over_ccy_mapping(df, out_dict):

    df.loc[df.risk_factor.isnull(), 'risk_factor'] = df.loc[df.risk_factor.isnull(), 'currency'].map(out_dict)

    return df

def build_residual_over_instr_mapping(df, out_dict):

    df.loc[df.instrument_id.isin(out_dict.keys()), 'risk_factor'] = df.loc[df.instrument_id.isin(out_dict.keys()), 'instrument_id'].map(out_dict)

    return df