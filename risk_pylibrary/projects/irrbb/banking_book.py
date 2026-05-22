#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
from datetime import datetime as _datetime
from datetime import date, timedelta
import numpy as np

# Python Charting


# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db
from risk_pylibrary.projects.econometrics import bond_analytics as bda





def banking_book_eval_engine(ddate_ftd=None, ddate_bonds=None):


    # Setting up parameters and output dictionary **********************************************************
    out_dict = dict()

    # Get Banking Book Positions **********************************************************
    #
    # Get Bonds
    #df_bonds = get_bond_book(report_date=ddate_bonds)
    # Grab later used values and drop column
    #rtg_book_avg = df_bonds['rating_fitch_book_avg'].iloc[0]
    #rtg_book_min = df_bonds['rating_fitch_min'].iloc[0]
    #df_bonds = df_bonds.drop(columns=['rating_fitch_book_avg', 'rating_fitch_min'], axis=1)

    # Get Bonds Purchase Value
    #mkt_bonds = np.sum(df_bonds.purchase_clean_price * df_bonds.notional_eur)/100

    # Get Own Cash Accounts
    df_cash = get_cash_deposits(report_date=ddate_ftd, bond_mkt=0)

    # Concat Output
    # out = pd.concat([df_bonds, df_cash], axis=0)
    out = df_cash.copy()

    # Calculate IRRBB Metrics
    out = bda.irrbb_shock_scenarios(out)

    # Format
    out['window_12m'] = out['window_12m'].fillna(method='ffill')
    out.loc[out.last_coupon_date.isnull(), 'last_coupon_date'] = date(2500, 12, 31)
    out.loc[out.next_coupon_date.isnull(), 'next_coupon_date'] = date(2500, 12, 31)

    # Set Max Report Date For All
    out['report_date'] = out['report_date'].max()

    # Store Information which is later dropped


    # Fill Numeric Value, which are None, with np.nan
    df_tbl = db.run_query(query='SELECT * FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_ANALYTICS LIMIT 1')
    out = out.reset_index()
    for col in df_tbl.columns:
        if col not in out.columns:
            out[col] = np.nan

    out = out[df_tbl.columns]
    out = out[[k for k in out.columns if k not in out.select_dtypes(include=[float]).columns]].join(out.select_dtypes(include=[float]).fillna(0))
    out = out[[k for k in out.columns if k not in out.select_dtypes(include=[object]).columns]].join(out.select_dtypes(include=[object]).fillna(''))

    out_dict['rep_pos'] = out

    # Build Delta EVE and NII Minimum Report **********************************************************
    #
    # FB20230108: doing this in Python as it's far simpler then on Looker
    df_rep_cons = out[['delta_eve', 'delta_nii']]
    df_rep_cons.columns = ['delta_eve_min', 'delta_nii_min']

    # Add Report Date
    df_rep_cons['report_date'] = out['report_date'].iloc[0]
    df_rep_cons = df_rep_cons.reset_index()[['report_date', 'delta_eve_min', 'delta_nii_min']]

    # Add Additional Information
    df_rep_cons['rating_minimum'] = np.nan #rtg_book_min
    df_rep_cons['rating_average'] = np.nan #rtg_book_avg
    df_rep_cons['book_value_bonds'] = out.loc[out.instrument_type == 'Bond', 'current_eur_market_value_dirty'].sum()
    df_rep_cons['ytm_max'] = out['years_to_maturity'].max()

    # Format
    df_rep_cons = df_rep_cons[:1]

    out_dict['rep_eve_nii_minimum'] = df_rep_cons

    # Building SAKI Report **********************************************************
    out_dict['saki'] = build_saki_report(out_dict['rep_pos'])

    return out_dict


def get_bond_book(report_date=None, rename=True):

    if report_date:
        qry = '''
        SELECT 
            *
        FROM 
            teams_prd.finance_staging.snapshot_stg__finance__treasury_bond_position
        WHERE
            report_date = %s;
        '''

        qry = qry%db.sqldate(report_date)


    else:

        report_date = _datetime.now().date()

        qry = '''
        SELECT 
            *
        FROM 
            teams_prd.finance_staging.snapshot_stg__finance__treasury_bond_position
        WHERE
            report_date = (SELECT MAX(REPORT_DATE) FROM teams_prd.finance_staging.snapshot_stg__finance__treasury_bond_position);
        '''

    df_orig = db.run_query(query=qry)

    if rename:
        rname_dict = {'isin':'instrument_id',
                      'final_maturity':'maturity',
                      'bloomberg_composite':'rating_bbg',
                      'trading_date':'buy_date',
                      'settlement_date':'buy_settlement',
                      'sell_trade_date':'sell_date',
                      'sell_settlement_date':'sell_settlement'
                      }

        df_orig = df_orig.rename(columns=rname_dict)


    # Get Future Cash Flows:
    df = bda.irrbb_bond_cash_flow(df_orig, report_date)

    # Get Bucket Mappings
    df = bda.irrbb_bucket_mapping(df)

    # Format Columns
    # Coupon as decimals
    df['coupon'] /= 100
    # Yields to Percentages
    df['ytm_bid'] /= 100
    df['ytm_ask'] /= 100
    # Calculate Mid Yield
    df['ytm_mid'] = (df['ytm_bid'] + df['ytm_ask'])/2

    # Calculating Mid Price
    df['current_mid_price'] = (df['current_bid_price'] + df['current_ask_price']) / 2

    # Calculating Dirty Market Value EUR
    df['current_eur_market_value_dirty'] = df['current_eur_market_value'] + df['accrued_unpaid_interest']

    # Set Closing
    df['book_closing'] = df['report_date']


    # Build Rating Information
    df = get_bond_ratings(df)

    # String Formatting
    df = df.rename(columns={'instrument_id':'symbol'})


    return df



def get_cash_deposits(report_date=None, bond_mkt=None, verbose=True):


    # Get Fixed Term Deposits **********************************************************
    if report_date:
        qry_ftd = '''
        SELECT 
             ftd.EXTRACTION_DATE AS REPORT_DATE,
             ftd.BORROWER AS SYMBOL,
             ftd.TERM,
             ftd.START_DATE,
             ftd.END_DATE AS MATURITY,
             ftd.INTEREST_RATE_IN_PERCENT/100 AS YTM_MID,
             ftd.AMOUNT AS CURRENT_EUR_MARKET_VALUE
        FROM 
            teams_prd.finance_staging.snapshot_stg__finance__treasury_bond_regulatory_reporting_info as ftd
        WHERE 
            EXTRACTION_DATE = %s
        AND
            EOM_INTEREST NOT IN ('Not Started', 'Matured')
        AND
            ftd.EXTRACTION_DATE < ftd.END_DATE;
        '''

        qry_ftd = qry_ftd%db.sqldate(report_date)

    else:
        qry_ftd = '''
        SELECT 
             ftd.EXTRACTION_DATE AS REPORT_DATE,
             ftd.BORROWER AS SYMBOL,
             ftd.TERM,
             ftd.START_DATE,
             ftd.END_DATE AS MATURITY,
             ftd.INTEREST_RATE_IN_PERCENT/100 AS YTM_MID,
             ftd.AMOUNT AS CURRENT_EUR_MARKET_VALUE
        FROM 
            teams_prd.finance_staging.snapshot_stg__finance__treasury_bond_regulatory_reporting_info as ftd
        WHERE 
            EXTRACTION_DATE = (SELECT MAX(EXTRACTION_DATE) FROM teams_prd.finance_staging.snapshot_stg__finance__treasury_bond_regulatory_reporting_info)
        AND
            EOM_INTEREST NOT IN ('Not Started', 'Matured')
        AND
            ftd.EXTRACTION_DATE < ftd.END_DATE;
        '''

    df_ftd = db.run_query(query=qry_ftd)

    if df_ftd.empty is False:
        # Formatting
        df_ftd['security_name'] = df_ftd.apply(lambda row: row['symbol']
                                                           + ', '
                                                           + row['term']
                                                           + ', ' + '{0:.2%}'.format(row['ytm_mid']), axis=1)

        df_ftd['symbol'] = df_ftd.apply(lambda row: row['symbol'].split(' ')[0].lower()
                                                    + '_'
                                                    + row['term'].replace(' ', '').replace('+', '_') + '_' + '{0:.2f}'.format(row['ytm_mid']*10000)
                                                    + 'bps', axis=1)

        df_ftd['years_to_maturity'] = df_ftd['maturity'].apply(lambda x: (x - df_ftd['report_date'].iloc[0]).days / 365)
        df_ftd['instrument_type'] = 'Cash Account - Fixed Term Deposit'
        df_ftd['book_closing'] = df_ftd['report_date']
        df_ftd['currency'] = 'EUR'

        # Drop Columns
        df_ftd = df_ftd.drop(columns=['start_date', 'term'], axis=1)


    # Get Cash Deposits **********************************************************

    if report_date:
        # Falling Back to latest MonthEnd Date
        if (report_date + timedelta(1)).month == report_date.month:
            prev_month_end = report_date.replace(day=1) - timedelta(days=1)
        else:
            prev_month_end = report_date

        if verbose:
            print("\t\t Extracting Cash Deposits on %s"%prev_month_end)

        qry_depo = '''
            SELECT 
                ca.balance_dt AS BOOK_CLOSING,
                ca.snapshot_dt AS SNAPSHOT_DT,
                ca.G_L_ACCOUNT_2 AS SECURITY_NAME,
                CASE
                    WHEN ca.G_L_ACCOUNT_2 = 'Other Receivables - Fixed Deposits' THEN 'Cash Account - Fixed Term Deposit'
                    ELSE 'Cash Account - Overnight Deposit %s'
                    END AS INSTRUMENT_TYPE,
                ca.PERIOD_BALANCE_CURRENCY AS CURRENCY,
                ca.PERIOD_BALANCE AS CURRENT_EUR_MARKET_VALUE
            FROM teams_prd.regulatory_reporting_staging.stg_snapshot__regulatory_reporting__balance_sheet_income_statement as ca
            WHERE report_granularity = 'month'
                AND 
                    balance_dt = %s
                AND 
                    snapshot_dt = (SELECT MAX(snapshot_dt) FROM teams_prd.regulatory_reporting_staging.stg_snapshot__regulatory_reporting__balance_sheet_income_statement WHERE balance_dt = %s)
                AND 
                    financial_statement_leaf_item_1 ='RKVO/00ASSETS'
                --and financial_statement_leaf_item_2 ='10300000 Receivables Banks'
                AND 
                    g_l_account_2 in ('JPM TRB Test', 'HSBC TRB Business Account UK','HSBC TRB Money Pool', 'HSBC TRB Money Pool - Transit', 
                    'JPM TRB Billing Bank Account', 'Pleo TRB Wallet Balance','Citi TRB Business Bank Account','Deutsche Bank TRB Business Account', 
                    'HSBC TRB Business Account','HSBC TRB Business Account Transit', 'HSBC BBA Trad Tax','HSBC TRB Stammkapital', 'HSBC TRB Spain Account', 
                    'HSBC TRB PUK','HSBC TRB Business Account USD', 'HSBC TRB Fractionals','HSBC TRB Fractionals Transit', 'HSBC TRB Tiberius',
                    'HSBC TRB Tiberius Transit', 'HSBC TRB Lease Deposit','HSBC TRB Lease Deposit Transit', 'DB TRB Testing','Citi TRB Billing', 
                    'HSBC TRB EBICS Test','Bundesbank TRB Account')
            order by g_l_account_2 asc;
        '''

        qry_depo = qry_depo%('4%', db.sqldate(prev_month_end), db.sqldate(prev_month_end))

    else:
        qry_depo = '''
            SELECT 
                ca.balance_dt AS BOOK_CLOSING,
                ca.snapshot_dt AS SNAPSHOT_DT,
                ca.G_L_ACCOUNT_2 AS SECURITY_NAME,
                CASE
                    WHEN ca.G_L_ACCOUNT_2 = 'Other Receivables - Fixed Deposits' THEN 'Cash Account - Fixed Term Deposit'
                    ELSE 'Cash Account - Overnight Deposit 4%'
                    END AS INSTRUMENT_TYPE,
                ca.PERIOD_BALANCE_CURRENCY AS CURRENCY,
                ca.PERIOD_BALANCE AS CURRENT_EUR_MARKET_VALUE
            FROM teams_prd.regulatory_reporting_staging.stg_snapshot__regulatory_reporting__balance_sheet_income_statement as ca
            WHERE report_granularity = 'month'
                AND balance_dt = (SELECT MAX(balance_dt) FROM teams_prd.regulatory_reporting_staging.stg_snapshot__regulatory_reporting__balance_sheet_income_statement)
                AND snapshot_dt = (SELECT MAX(snapshot_dt) FROM teams_prd.regulatory_reporting_staging.stg_snapshot__regulatory_reporting__balance_sheet_income_statement)
                AND financial_statement_leaf_item_1 ='RKV0/00ASSETS'
                --and financial_statement_leaf_item_2 ='10300000 Receivables Banks'
                AND g_l_account_2 in (-- 'Other Receivables - Fixed Deposits',
                                      'Bundesbank TRB Account', 
                                      'Citi Commission', 'Citi Transit Payout', 'Citi TRB Billing', 'Citi TRB Business Bank Account',
                                      'DB TRB Billing', 'Deutsche Bank TRB Business Account',
                                      'HSBC BBA Trad Tax', 'HSBC TRB Business Account', 'HSBC TRB Business Account Transit', 
                                      'HSBC TRB Business Account UK', 'HSBC TRB Business Account USD','HSBC TRB EBICS Test',
                                      'HSBC TRB Fractionals','HSBC TRB Fractionals Transit','HSBC TRB Money Pool','HSBC TRB Money Pool - Transit',
                                      'HSBC TRB PUK','HSBC TRB Spain Account','HSBC TRB Stammkapital','HSBC TRB Tiberius','HSBC TRB Tiberius Transit','JPM TRB Billing Bank Account')
            order by g_l_account_2 asc;
        '''

    df_reg_rep_orig = db.run_query(query=qry_depo)
    df_reg_rep = df_reg_rep_orig.copy().drop(columns=['security_name'], axis=1)
    df_reg_rep = df_reg_rep.groupby([k for k in df_reg_rep.columns if k not in ['current_eur_market_value']]).sum().reset_index()

    # Adding FTD Counter Position
    # FB20240105: FTD Positions are retrievable daily, while the qry_depo retrieves only monthly numbers. This correction position takes
    # into account further FTD investments
    #
    # Get Non Cash Balance at T-1
    qry_non_cash_bonds = '''
        SELECT
            *
        FROM
            TEAMS_PRD.RISK_DATA.MR_IRRBB_ANALYTICS
        WHERE
            REPORT_DATE > %s AND REPORT_DATE <%s
        AND
            SECURITY_NAME <> 'Cash Account - Overnight Deposit 4%s'
        '''

    df_recon = db.run_query(query=qry_non_cash_bonds%(db.sqldate(report_date - timedelta(7)), db.sqldate(report_date), '%'))
    df_recon = df_recon[df_recon.report_date == df_recon.report_date.max()]
    dict_recon = dict()
    if df_recon.empty is False:
        for instr_type in df_recon.instrument_type.unique():
            tmp_recon = df_recon[df_recon.instrument_type == instr_type]
            if instr_type == 'Cash Account - Overnight Deposit 4%':
                tmp_recon_ftd = tmp_recon[tmp_recon.security_name == 'Cash Account - Overnight Deposit 4% Adj. FTD']
                dict_recon[instr_type + ' Adj. FTD'] = tmp_recon_ftd.current_eur_market_value.sum()
                tmp_recon_bond = tmp_recon[tmp_recon.security_name == 'Cash Account - Overnight Deposit 4% Adj. Bond']
                dict_recon[instr_type + ' Adj. Bond'] = tmp_recon_bond.current_eur_market_value.sum()
            else:
                dict_recon[instr_type] = tmp_recon.current_eur_market_value.sum()

    #import pdb
    #pdb.set_trace()

    # Creating Cash Adjustment Positions
    #
    # Handling Bonds


    mkt_bonds_delta = 0
    if 'Bond' in dict_recon.keys():
        if bond_mkt < dict_recon['Bond']:
            mkt_bonds_delta = ((bond_mkt if bond_mkt else 0)
                               - dict_recon['Bond']
                               + dict_recon['Cash Account - Overnight Deposit 4% Adj. Bond'] if 'Cash Account - Overnight Deposit 4% Adj. Bond' in dict_recon.keys() else 0)

        elif bond_mkt > dict_recon['Bond']:
            mkt_bonds_delta = (dict_recon['Bond']
                               - (bond_mkt if bond_mkt else 0)
                               + dict_recon['Cash Account - Overnight Deposit 4% Adj. Bond'] if 'Cash Account - Overnight Deposit 4% Adj. Bond' in dict_recon.keys() else 0)

        elif bond_mkt == dict_recon['Bond']:
            mkt_bonds_delta = + dict_recon['Cash Account - Overnight Deposit 4% Adj. Bond'] if 'Cash Account - Overnight Deposit 4% Adj. Bond' in dict_recon.keys() else 0

        else:
            mkt_bonds_delta = bond_mkt


    # Handling FTDs
    mkt_ftd_delta = 0
    if df_ftd.empty is False:
        if 'Cash Account - Fixed Term Deposit' in dict_recon.keys():
            if df_ftd.current_eur_market_value.sum() < dict_recon['Cash Account - Fixed Term Deposit']:
                # Sell FTD
                mkt_ftd_delta = (dict_recon['Cash Account - Fixed Term Deposit']
                                 - df_ftd.current_eur_market_value.sum()
                                 + dict_recon['Cash Account - Overnight Deposit 4% Adj. FTD'] if 'Cash Account - Overnight Deposit 4% Adj. FTD' in dict_recon.keys() else 0)
            elif df_ftd.current_eur_market_value.sum() > dict_recon['Cash Account - Fixed Term Deposit']:
                # Buy FTD
                mkt_ftd_delta = (dict_recon['Cash Account - Fixed Term Deposit']
                                 - df_ftd.current_eur_market_value.sum()
                                 + dict_recon['Cash Account - Overnight Deposit 4% Adj. FTD'] if 'Cash Account - Overnight Deposit 4% Adj. FTD' in dict_recon.keys() else 0)
            elif df_ftd.current_eur_market_value.sum() == dict_recon['Cash Account - Fixed Term Deposit']:
                # No Trade
                mkt_ftd_delta = + dict_recon['Cash Account - Overnight Deposit 4%'] if 'Cash Account - Overnight Deposit 4%' in dict_recon.keys() else 0
        else:
            mkt_ftd_delta = -1 * df_ftd.current_eur_market_value.sum()



    # Add FTD Values
    #
    df_reg_adj = df_reg_rep[df_reg_rep.instrument_type == 'Cash Account - Overnight Deposit 4%']
    df_reg_adj['current_eur_market_value'] = mkt_ftd_delta
    df_reg_adj['instrument_type'] = 'Cash Account - Overnight Deposit 4%'
    df_reg_adj['security_name'] = 'Cash Account - Overnight Deposit 4% Adj. FTD'

    # Appending and slicing away FTD Position
    df_reg_rep = df_reg_rep[df_reg_rep.instrument_type == 'Cash Account - Overnight Deposit 4%']
    df_reg_rep['security_name'] = 'Cash Account - Overnight Deposit 4%'
    df_reg_rep = pd.concat([df_reg_rep, df_reg_adj], axis=0)

    # Add Bond Values
    #
    # Bonds Market Value Need also Be discounted in case report_date != prev_month_end
    if (report_date + timedelta(1)).month == report_date.month:
        # Add Values
        df_reg_adj_bond = df_reg_rep[df_reg_rep.security_name == 'Cash Account - Overnight Deposit 4% Adj. FTD']
        df_reg_adj_bond['current_eur_market_value'] = mkt_bonds_delta
        df_reg_adj_bond['instrument_type'] = 'Cash Account - Overnight Deposit 4%'
        df_reg_adj_bond['security_name'] = 'Cash Account - Overnight Deposit 4% Adj. Bond'
        df_reg_rep = pd.concat([df_reg_rep, df_reg_adj_bond], axis=0)

    # Formatting
    df_reg_rep['symbol'] = 'overnight_various_400bps'
    df_reg_rep['report_date'] = report_date if report_date else df_ftd['report_date'].iloc[0]

    # Mapping YTM to IRRBB ON mid point
    df_reg_rep['years_to_maturity'] = 0.0028
    df_reg_rep['maturity'] = date(2500, 12, 31)
    df_reg_rep['ytm_mid'] = 0.04



    # Merge Datasets **********************************************************
    if df_ftd.empty is False:
        df = pd.concat([df_ftd, df_reg_rep], axis=0)
    else:
        df = df_reg_rep
    df = df.reset_index()  # resetting the index to obtain sequential numeration
    df = df.drop(columns=['snapshot_dt', 'index'])

    # Add Columns
    df['current_mid_price'] = 1
    df['nominal'] = df['notional_eur'] = df['current_eur_market_value_dirty'] = df['current_eur_market_value']
    df['industry_sector'] = df['industry_group'] = df['instrument_type']

    # Map IRRBB Bucket:
    df = bda.irrbb_bucket_mapping(df, indexer='')

    # Adding further columns
    df['cash_flow_12m'] = 0
    df['window_12m'] = df['report_date'].apply(lambda x: (x + timedelta(365)))
    df['portfolio'] = 'BankingBook'
    df['buy_date'] = df['buy_settlement'] = df['issue_date'] = df['last_coupon_date'] = df['next_coupon_date'] = date(2500, 12, 31)
    df['callable'] = 'N'

    return df



def get_bond_ratings(df_orig):

    df = df_orig.copy()

    # Rating:
    df.loc[df.instrument_id == 'DE000A1RQC36', "rating_fitch"] = 'AA+'
    df.loc[df.instrument_id == 'EU000A3JZSC2', "rating_fitch"] = 'AAA'
    df.loc[df.instrument_id == 'EU000A3K4EB0', "rating_fitch"] = 'AA+'
    df.loc[df.instrument_id == 'XS1550154626', "rating_fitch"] = 'AAA'
    df.loc[df.instrument_id == 'AT0000A37AW1', "rating_fitch"] = 'AA+'
    df.loc[df.instrument_id == 'FR0127921304', "rating_fitch"] = 'AA-'
    df.loc[df.instrument_id == 'FI4000561279', "rating_fitch"] = 'AA+'

    # Retrieve Rating Numerical
    df_rtg_map = db.run_query(query='SELECT * FROM TEAMS_PRD.RISK_DATA_SENSITIVE.RISK_CREDIT_RATING_SCALES')

    # Map Rating Scores
    df['rating_fitch_num'] = df['rating_fitch'].map(dict(zip(df_rtg_map.fitch, df_rtg_map.num_value)))
    # Comment FB 20240424:
    # Hardcode fixing the Rating average as the current Short Term bonds are all HQLA and mature within a month,
    # but have no rating
    # df['rating_fitch_book_avg'] = df_rtg_map.loc[df_rtg_map.num_value == np.floor(df['rating_fitch_num'].mean()), 'fitch'].iloc[0]
    # df['rating_fitch_min'] = df_rtg_map.loc[df_rtg_map.num_value == np.floor(df['rating_fitch_num'].max()), 'fitch'].iloc[0]
    df['rating_fitch_book_avg'] = df_rtg_map.loc[df_rtg_map.num_value == np.floor(4), 'fitch'].iloc[0]
    df['rating_fitch_min'] = df_rtg_map.loc[df_rtg_map.num_value == np.floor(5), 'fitch'].iloc[0]


    # DropNum ValueColumn
    df = df.drop('rating_fitch_num', axis=1)


    return df



def build_saki_report(df_pos):
    """
    SAKI Report can be viewed here. Report is published on a Looker Dashboard
    @param df_orig: input data
    @return: dataframe
    """

    df = df_pos.copy()

    # Creating Output with SAKI Report Index
    out = pd.DataFrame(index=[379, 380, 390, 400, 410, 435] + list(np.arange(420, 430, 1)) + list(np.arange(431, 434, 1)),
                       columns=['report_date', 'desc', 'value'])
    out = out.sort_index()
    out['report_date'] = df.report_date.iloc[0]
    out['code'] = out.index

    # Calculating Sums and Minima
    cols_rate = ['eve_parallel_down', 'eve_parallel_up', 'eve_parallel_stress_down', 'eve_parallel_stress_up',
                 'eve_shortrate_down', 'eve_shortrate_up', 'eve_steepener', 'eve_flattener']
    cols_eur = ['delta_eve_parallel_down', 'delta_eve_parallel_up', 'delta_eve_shortrate_down', 'delta_eve_shortrate_up', 'delta_eve_steepener',
                'delta_eve_flattener', 'delta_eve', 'delta_nii_parallel_down', 'delta_nii_parallel_up', 'delta_nii']

    df_rep_rate = df[['bucket'] + cols_rate].groupby('bucket').min()
    df_rep_eur = df[['bucket'] + cols_eur].groupby('bucket').sum()
    df_rep_eur['delta_eve_min'] = df_rep_eur['delta_eve'].min()
    df_rep_eur['delta_nii_min'] = df_rep_eur['delta_nii'].min()


    # Filling Values ******************************************************************************
    out.loc[379, 'desc'] = 'Anwendung des § 2a Absatz 1 KWG (= 1)'
    out.loc[379, 'value'] = 0

    # Total Book Value
    out.loc[380, 'desc'] = 'Zinsbuchbarwert (in EUR)'
    out.loc[380, 'value'] = '{:,.0f}'.format(np.round(df['current_eur_market_value_dirty'].sum(), 0))

    # Delta NII Calculations ********************************************
    # Index 390 - Delta NII at +200 bps
    out.loc[390, 'desc'] = 'Barwertänderung bei Zinserhöhung – Standardtest (in EUR)'
    out.loc[390, 'value'] = '{:,.0f}'.format(np.round(df_rep_eur.delta_nii_parallel_up.min(), 0))

    # Index 400 - Delta NII at +200 bps
    out.loc[400, 'desc'] = 'Zinskoeffizient bei Zinserhöhung (in %) – Standardtest'
    # Get bucket for dNII Maximum and pick Interest Rate shock for that bucket
    min_dNII_rate_up = df_rep_rate.loc[df_rep_eur.delta_nii_parallel_up.sort_values(ascending=False).index[-1]].eve_parallel_up
    out.loc[400, 'value'] = '{:.2%}'.format(np.round(min_dNII_rate_up, 4))

    # Index 410 - Delta NII at -200 bps
    out.loc[410, 'desc'] = 'Barwertänderung bei Zinssenkung – Standardtest'
    # Get bucket for dNII Minimum and pick Interest Rate shock for that bucket
    out.loc[410, 'value'] = '{:,.0f}'.format(np.round(df_rep_eur.delta_nii_parallel_down.min(), 0))

    # Index 420 - Delta NII at -200 bps
    out.loc[420, 'desc'] = 'Zinskoeffizient bei Zinssenkung (in %) – Standardtest'
    # Get bucket for dNII Maximum and pick Interest Rate shock for that bucket
    min_dNII_rate_down = df_rep_rate.loc[df_rep_eur.delta_nii_parallel_down.sort_values(ascending=False).index[-1]].eve_parallel_down
    out.loc[420, 'value'] = '{:.2%}'.format(np.round(min_dNII_rate_down, 4))


    # Delta EVE Calculations ********************************************
    # Parallel Shocks *******************
    # Index 421 - Delta EVE at parallel up
    out.loc[421, 'desc'] = 'Barwertänderung bei paralleler Zinserhöhung – Frühwarnindikator (FWI) (in EUR)'
    out.loc[421, 'value'] = '{:,.0f}'.format(np.round(df_rep_eur.delta_eve_parallel_up.min(), 0))

    # Index 422 - Delta EVE at parallel up
    out.loc[422, 'desc'] = 'Zinskoeffizient bei paralleler Zinserhöhung (in %) – FWI'
    min_deve_par_rate_up = df_rep_rate.eve_parallel_up.min()
    out.loc[422, 'value'] = '{:.2%}'.format(np.round(min_deve_par_rate_up, 4))

    # Index 423 - Delta EVE at parallel down
    out.loc[423, 'desc'] = 'Barwertänderung bei paralleler Zinserhöhung – FWI (in EUR)'
    out.loc[423, 'value'] = '{:,.0f}'.format(np.round(df_rep_eur.delta_eve_parallel_down.min(), 0))

    # Index 424 - Delta EVE at parallel down
    out.loc[424, 'desc'] = 'Zinskoeffizient bei paralleler Zinssenkung (in %) – FWI'
    min_deve_par_rate_down = df_rep_rate.eve_parallel_down.min()
    out.loc[424, 'value'] = '{:.2%}'.format(np.round(min_deve_par_rate_down, 4))

    # Steepener and Flattener Shocks *******************
    # Index 425 - Delta EVE at steepener
    out.loc[425, 'desc'] = 'Barwertänderung bei Versteilung der Zinskurve – FWI (in EUR)'
    out.loc[425, 'value'] = '{:,.0f}'.format(np.round(df_rep_eur.delta_eve_steepener.min(), 0))

    # Index 426 - Delta EVE at steepener
    out.loc[426, 'desc'] = 'Zinskoeffizient bei Versteilung der Zinskurve (in %) – FWI'
    min_deve_steep = df_rep_rate.eve_steepener.min()
    out.loc[426, 'value'] = '{:.2%}'.format(np.round(min_deve_steep, 4))

    # Index 427 - Delta EVE at flattener
    out.loc[427, 'desc'] = 'Barwertänderung bei Verflachung der Zinskurve – FWI (in EUR)'
    out.loc[427, 'value'] = '{:,.0f}'.format(np.round(df_rep_eur.delta_eve_flattener.min(), 0))

    # Index 428 - Delta EVE at flattener
    out.loc[428, 'desc'] = 'Zinskoeffizient bei Verflachung der Zinskurve (in %) – FWI'
    min_deve_flat = df_rep_rate.eve_flattener.min()
    out.loc[428, 'value'] = '{:.2%}'.format(np.round(min_deve_flat, 4))

    # Short Rate Up and Down Shocks *******************
    # Index 429 - Delta EVE at short rate up
    out.loc[429, 'desc'] = 'Barwertänderung bei Kurzfristschock aufwärts – FWI (in EUR)'
    out.loc[429, 'value'] = '{:,.0f}'.format(np.round(df_rep_eur.delta_eve_shortrate_up.min(), 0))

    # Index 431 - Delta EVE at short rate down
    out.loc[431, 'desc'] = 'Zinskoeffizient bei Kurzfristschock aufwärts (in %) – FWI'
    min_deve_short_up = df_rep_rate.eve_shortrate_up.min()
    out.loc[431, 'value'] = '{:.2%}'.format(np.round(min_deve_short_up, 4))

    # Index 432 - Delta EVE at short rate up
    out.loc[432, 'desc'] = 'Barwertänderung bei Kurzfristschock abwärts – FWI (in EUR)'
    out.loc[432, 'value'] = '{:,.0f}'.format(np.round(df_rep_eur.delta_eve_shortrate_down.min(), 0))

    # Index 433 - Delta EVE at short rate down
    out.loc[433, 'desc'] = 'Zinskoeffizient bei Kurzfristschock abwärts (in %) – FWI'
    min_deve_short_down = df_rep_rate.eve_shortrate_down.min()
    out.loc[433, 'value'] = '{:.2%}'.format(np.round(min_deve_short_down, 4))


    # Adding Margin Approach ********************************************
    out.loc[435, 'desc'] = 'Berücksichtigung (= 1) oder Nicht-Berücksichtigung (= 2) von Margen in Cashflows'
    out.loc[435, 'value'] = 2



    # Format Output
    out = out[['report_date', 'code', 'desc', 'value']]


    return out



def parse_irrbb(out_dict):
    for kk in out_dict.keys():
        if kk == 'saki':
            db.pandas2db(out_dict[kk],'TEAMS_PRD.RISK_DATA.MR_IRRBB_SAKI', merge=True)
        elif kk == 'rep_pos':
            db.pandas2db(out_dict[kk],'TEAMS_PRD.RISK_DATA.MR_IRRBB_ANALYTICS', merge=True)
        elif kk == 'rep_eve_nii_minimum':
            db.pandas2db(out_dict[kk],'TEAMS_PRD.RISK_DATA.MR_IRRBB_CONSOLIDATED', merge=True)















