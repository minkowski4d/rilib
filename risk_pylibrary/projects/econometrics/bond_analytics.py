#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys

# Import Python Modules
import numpy as np
from datetime import datetime as _datetime, date, timedelta

# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db




def bonds_dur_conv(df_orig, verbose):
    """
    Calculator for Bond Analytics Duration
    @param df: output of rws.rf_get_secs_info()
    @param verbose: True or False
    @return: Enriched DataFrame
    """

    df = df_orig.copy()

    # Calculate Duration using closed form:
    # See de La Grandville, O.: Bond pricing and portfolio analysis. The MIT Press, Cambridge (2001)
    ytm = df['yield_to_maturity']
    maturity = df['years_to_maturity']
    cpn = df['coupon']
    cpn_freq = df['cpn_freq']

    # Macaulay Duration
    if verbose:
        print("\t Calculating Macaulay Duration")
    df['dur_mac'] = 1 + ytm**(-1) + (maturity*(ytm - cpn) - (1 + ytm)) / (cpn * ((1 + ytm)**maturity - 1) + ytm)

    # Calculate for Zero-Coupon Bonds
    df.loc[df.is_zerocpn == 1, 'dur_mac'] = df.loc[df.is_zerocpn == 1, 'years_to_maturity']

    # Modified Duration
    if verbose:
        print("\t Calculating Modified Duration")
    df['dur_mod'] = df['dur_mac'] * (1+ytm/cpn_freq)**(-1)

    # Convexity
    if verbose:
        print("\t Calculating Convexity")
    cpn_prev = df['cpn_previous_in_years']
    cpn_outst = df['cpn_num2mat']
    gamma = (cpn_prev - cpn_outst) * (cpn_prev - cpn_outst - 1) * (1 + ytm)**(-2)
    prx = df['eod_price_clean']
    # Closed form as per Scholz A Revised Closed-Form Solution for Bond Convexity 2018
    df['convexity'] = cpn / (ytm * prx) * (cpn_prev * (cpn_prev - 1) * (1 + ytm)**(-2) -
                                           gamma +
                                           (- cpn_prev + (cpn_prev - cpn_outst) * (1 + ytm)**(-cpn_outst)) /
                                           (0.5 * ytm * (1 + ytm)) +
                                           (1 - (1 + ytm)**(-cpn_outst)) / (0.5 * ytm**2)) + gamma

    # Calculate for Zero-Coupon Bonds
    df.loc[df.is_zerocpn == 1, 'convexity'] = (((df.loc[df.is_zerocpn == 1, 'years_to_maturity']**2 +
                                               df.loc[df.is_zerocpn == 1, 'years_to_maturity'])) /
                                               (1 + df.loc[df.is_zerocpn == 1, 'yield_to_maturity'])**2)


    return df




def irrbb_bond_cash_flow(df_orig, report_date):
    """
    Expected Cash Flow Simulation
    @param df_orig: dataframe
    @return: enriched dataframe
    """

    df = df_orig.copy()
    df = df.set_index('instrument_id')

    # Add Support Columns
    df['years_to_maturity'] = df['maturity'].apply(lambda x: (x - report_date).days/365)
    df['window_12m'] = df['report_date'].apply(lambda x: (x + timedelta(365)))

    # Calculate the Number Of Coupons in the Next 12 months (IRRBB forward-looking horizon)
    cols_cpn_12m = ['next_coupon_date', 'window_12m', 'coupon_frequency']
    df['num_cpn_in_12m'] = df[cols_cpn_12m].apply(lambda row: int((row['window_12m'] -
                                                                   row['next_coupon_date']).days *
                                                                   row['coupon_frequency']/365) +
                                                                   1 if row['coupon_frequency'] != 0 else 0, axis=1)

    # Calculate the Number Of Coupons until maturity
    cols_cpn_mat = ['maturity', 'next_coupon_date', 'coupon_frequency']
    df['num_cpn_until_maturity'] = df[cols_cpn_mat].apply(lambda row: int((row['maturity'] -
                                                                           row['next_coupon_date']).days *
                                                                           row['coupon_frequency']/365) +
                                                                           1 if row['coupon_frequency'] != 0 else 0, axis=1)



    # Calculate Total Cash Flows until Maturity
    cols_cash_flows = ['notional_eur', 'num_cpn_until_maturity', 'coupon']
    df['cash_flow_total'] = df[cols_cash_flows].apply(lambda row: row['notional_eur'] *
                                                                  (1 + row['num_cpn_until_maturity'] *
                                                                   row['coupon']/100), axis=1)

    # Calculate Cash Flows in the next 12 months
    cols_cash_flows_12m = ['maturity', 'window_12m', 'notional_eur', 'num_cpn_in_12m', 'coupon']
    df['cash_flow_12m'] = df[cols_cash_flows_12m].apply(lambda row: row['notional_eur'] *
                                                                    (1 + row['num_cpn_in_12m'] *
                                                                     row['coupon']/100) if row['maturity'] < row['window_12m']
                                                                     else row['notional_eur'] *
                                                                          row['num_cpn_in_12m'] *
                                                                          row['coupon']/100, axis=1)


    return df.reset_index()



def irrbb_bucket_mapping(df_orig, indexer='instrument_id'):


    df = df_orig.copy()
    if indexer == 'instrument_id':
        df = df.set_index('instrument_id')
    elif indexer == 'symbol':
        df = df.set_index('symbol')
    elif indexer == '':
        pass

    # Get Mapping Table
    df_map = db.run_query(query='''SELECT * FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_BUCKETS''')

    # Define Bucket Start and End Points
    df_map['bucket_start'] = df_map.bucket.apply(lambda x: x.split('<')[0])
    df_map['bucket_end'] = df_map.bucket.apply(lambda x: x.split('<=')[1] if len(x.split('<=')) > 1 else x.split('<=')[0])


    # Recalculate Start and End Points as years
    for col in ['bucket_start', 'bucket_end']:
        if col == 'bucket_start':
            df_map[col+'_num'] = df_map[col].apply(lambda x: float(x.replace('M', '')) / 12 if x[-1] == 'M'
                                                                                            else
                                                                                                (float(x.replace('Y', ''))
                                                                                                if x[-1] == 'Y' and x[0] != 't'
                                                                                                else
                                                                                                    (0
                                                                                                     if x == 'Overnight'
                                                                                                     else
                                                                                                        (0
                                                                                                         if x == str(0)
                                                                                                         else 20)))) # Brute Mapping 20Y Bucket
        elif col == 'bucket_end':
            df_map[col+'_num'] = df_map[col].apply(lambda x: float(x.replace('M', '')) / 12 if x[-1] == 'M'
                                                                                            else
                                                                                                (float(x.replace('Y', ''))
                                                                                                if x[-1] == 'Y' and x[0] != 't'
                                                                                                else
                                                                                                    (0
                                                                                                     if x == 'Overnight'
                                                                                                     else 100))) # Assuming 100Y as max maturity (e.g. AUT Govies)

    # Map Instruments
    df_map_float = df_map[~df_map.bucket_start_num.isin(['Overnight', 't>20Y'])]
    df_map_float['bucket_start_num'] = df_map_float['bucket_start_num'].astype(float)
    df_map_float['bucket_end_num'] = df_map_float['bucket_end_num'].astype(float)

    # Initiate Mapping Process
    out_map = pd.DataFrame()
    for sym in df.index:
        if 'Overnight Deposit' in df.loc[sym].instrument_type:
            df_map_tmp = df_map_float[(df_map_float['bucket_start_num'] <= df.loc[sym].years_to_maturity.mean())
                                      & (df_map_float['bucket_start'] == 'Overnight')]
        else:
            df_map_tmp = df_map_float[(df_map_float['bucket_start_num'] <= df.loc[sym].years_to_maturity.mean())
                                      & (df_map_float['bucket_start'] != 'Overnight')]

        df_map_tmp = df_map_tmp.iloc[[-1]]
        df_map_tmp['instrument_id'] = sym
        out_map = pd.concat([out_map, df_map_tmp.set_index('instrument_id')], axis=0)


    # Formatting
    out_map = out_map.rename(columns={'midpoint':'bucket_midpoint'})

    # Merge Outputs
    df = pd.concat([df, out_map], axis=1)

    if indexer == '':
        return df
    else:
        return df.reset_index()



def irrbb_shock_scenarios(df_orig):

    df = df_orig.copy()

    # Calculate Discount Factor
    df['discount'] = 1 / (1 + df['ytm_mid'])**df['years_to_maturity']

    # Calculate Projected, Discounted Cash Flows
    df['dcf'] = df['cash_flow_12m'] * df['discount']
    df['dcf_1'] = df['dcf'] * df['years_to_maturity']
    df['dcf_2'] = df['dcf'] * df['years_to_maturity'] * (df['years_to_maturity'] + 1)

    # Define Yield Shocks EUR
    # Current Bonds are EUR only. Risk observes the currency Exposure as a Specific Limit
    #
    # EUR Shock Values are defined on p. 44 in https://www.bis.org/bcbs/publ/d368.pdf
    shock_parallel_eur = 0.02
    shock_parallel_eur_stress = 0.045
    shock_short_eur = 0.025
    shock_long_eur = 0.015

    # Calculating Yield Shock Scenarios
    #
    # Calculate EVE Parallel Yield shocks
    df['eve_parallel_down'] = df['ytm_mid'] - shock_parallel_eur
    df['eve_parallel_up'] = df['ytm_mid'] + shock_parallel_eur
    df['eve_parallel_stress_down'] = df['ytm_mid'] - shock_parallel_eur_stress
    df['eve_parallel_stress_up'] = df['ytm_mid'] + shock_parallel_eur_stress

    # Exponential Shocks
    # Short Rate Shocks
    df['eve_shortrate_down'] = -1 * shock_short_eur * np.exp(-df['years_to_maturity'] / 4) + df['ytm_mid']
    df['eve_shortrate_up'] = shock_short_eur * np.exp(-df['years_to_maturity'] / 4) + df['ytm_mid']

    # Steepener Shocks
    df['eve_steepener'] = -0.65 * np.abs(df['eve_shortrate_up']) + 0.9 * np.abs(shock_long_eur * (1 - np.exp(-df['years_to_maturity'] / 4)))
    df['eve_flattener'] = 0.8 * np.abs(df['eve_shortrate_up']) - 0.6 * np.abs(shock_long_eur * (1 - np.exp(-df['years_to_maturity'] / 4)))


    # Calculating Delta EVE and Delta NII
    #
    # General Formula: dEVE = ShockDCF - DCF = 1/(1+ShockYield)**BucketMidPoint*CashFlows - DCF
    #
    # Set Scenario Columns
    ll_scenarios = ['eve_parallel_down', 'eve_parallel_up', 'eve_parallel_stress_down', 'eve_parallel_stress_up',
                    'eve_shortrate_down', 'eve_shortrate_up', 'eve_steepener', 'eve_flattener']
    # Iterate
    for scen in ll_scenarios:
        df['delta_%s'%scen] = 1 / (1 + df[scen])**df['bucket_midpoint'] * df['cash_flow_12m'] - df['dcf']

    # Get Minimum for Delta EVE per Row (exclude 450 bps EUR stress)
    delta_eve_cols = ['bucket']+['delta_'+k for k in ll_scenarios if k not in ['eve_parallel_stress_down', 'eve_parallel_stress_up']]
    df['delta_eve'] = df[delta_eve_cols].groupby('bucket').sum().T.min().min()

    # Calculate Delta NII
    #
    df['delta_nii_parallel_down'] = (df['eve_parallel_down'] - df['ytm_mid']) * df['current_eur_market_value_dirty']
    df['delta_nii_parallel_up'] = (df['eve_parallel_up'] - df['ytm_mid']) * df['current_eur_market_value_dirty']

    # Get Minimum for Delta NII per Row
    delta_nii_cols = ['bucket', 'delta_nii_parallel_down', 'delta_nii_parallel_up']
    df['delta_nii'] = df[delta_nii_cols].groupby('bucket').sum().T.min().min()


    return df
















