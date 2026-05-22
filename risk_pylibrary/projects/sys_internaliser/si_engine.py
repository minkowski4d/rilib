#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime

import pandas as pd





def read_esma_xml(pth, asset_class='equity', sdate=None, edate=None, db_format=False, verbose=True):
    """
    Code to extract SI Data from https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_fitrs_files
    @param pth: string - filename in .xml format
    @param startdate: date object - period startdate
    @param enddate: date object - period enddate
    @return: dataframe
    """
    # Importing Modules
    import xmltodict
    import os
    import numpy as np
    import pandas as pd
    from datetime import datetime as _datetime

    if verbose:
        print("****** Unpacking File %s"%pth)

    out = pd.DataFrame()
    out_orig = pd.DataFrame()

    for fname in [k for k in os.listdir(pth) if k.endswith('xml')]:

        print("\t \t Opening: %s"%fname)
        with open(os.path.join(pth, fname)) as xml_file:
            data_dict = xmltodict.parse(xml_file.read())

        if asset_class == 'equity':

            df_orig = pd.DataFrame(data_dict['BizData']['Pyld']['Document']['FinInstrmRptgEqtyTradgActvtyRslt']['EqtyTrnsprncyData'])
            out_orig = pd.concat([out_orig, df_orig], axis=0)

            df = df_orig[df_orig.Mthdlgy == 'SINT']
            df = df.reset_index(drop=True)
            # Unpack nested values
            #df = pd.DataFrame(index=range(0, len(df)), columns=['FrDt', 'ToDt', 'TtlNbOfTxsExctd', 'TtlVolOfTxsExctd', 'Lqdty'])
            df['FrDt'] = ''
            df['ToDt'] = ''
            df['TtlNbOfTxsExctd'] = ''
            df['TtlVolOfTxsExctd'] = ''

            if verbose:
                print('\t\t Total file Length: %s'%len(df))
            for row in range(0, len(df)):
                if verbose and row % 1000 == 0:
                    print('\t\t Processing Row: %s' %row)
                try:
                    df.loc[row, 'FrDt'] = _datetime.strptime(df.loc[row]['RptgPrd']['FrDtToDt']['FrDt'], '%Y-%m-%d').date()
                    df.loc[row, 'ToDt'] = _datetime.strptime(df.loc[row]['RptgPrd']['FrDtToDt']['ToDt'], '%Y-%m-%d').date()
                except:
                    df.loc[row, 'FrDt'] = np.nan
                    df.loc[row, 'ToDt'] = np.nan

                try:
                    df.loc[row, 'TtlNbOfTxsExctd'] = int(df.loc[row]['Sttstcs']['TtlNbOfTxsExctd'])
                    df.loc[row, 'TtlVolOfTxsExctd'] = float((df.loc[row]['Sttstcs']['TtlVolOfTxsExctd']))
                except:
                    df.loc[row, 'TtlNbOfTxsExctd'] = np.nan
                    df.loc[row, 'TtlVolOfTxsExctd'] = np.nan

                try:
                    df.loc[row, 'Liquidity'] = out_orig[out_orig['Id'] == df.loc[row]['Id']][out_orig['Mthdlgy'] == 'YEAR'].Lqdty.iloc[0] #df.loc[row]['Lqdty']
                except:
                     df.loc[row, 'Liquidity'] = ''


            # Format
            df_tmp = df[['TechRcrdId', 'Id', 'FinInstrmClssfctn', 'Mthdlgy', 'FrDt', 'ToDt', 'TtlNbOfTxsExctd', 'TtlVolOfTxsExctd', 'Liquidity']]
            df_tmp = df_tmp.rename(columns={'Id': 'instrument_id'})
            df_tmp = df_tmp.rename(columns=lambda x: x.lower())

            #
            # import pdb
            # pdb.set_trace()
            # Appending Data
            out = pd.concat([out, df_tmp], axis=0)



        elif asset_class == 'non-equity':

            # Get Data
            df = pd.DataFrame(data_dict['BizData']['Pyld']['Document']['FinInstrmRptgNonEqtyTradgActvtyRslt']['NonEqtyTrnsprncyData'])

            # Set Output
            out = pd.DataFrame(columns=['ISIN', 'DerivSubClss', 'FrDt', 'ToDt', 'TtlNbOfTxsExctd', 'TtlVolOfTxsExctd', 'Liquidity'])

            for row in range(0, len(df)):
                if df.loc[row]['Id']['ISINAndSubClss']['DerivSubClss']['Desc'] in ['Corporate bond', 'Other bonds', 'Sovereign bond', 'Public bond']:
                    try:
                        out.loc[row, 'ISIN'] = df.loc[row]['Id']['ISINAndSubClss']['ISIN']
                    except:
                        out.loc[row, 'ISIN'] = np.nan

                    try:
                        out.loc[row, 'DerivSubClss'] = df.loc[row]['Id']['ISINAndSubClss']['DerivSubClss']['Desc']
                    except:
                        out.loc[row, 'DerivSubClss'] = np.nan

                    try:
                        out.loc[row, 'FrDt'] = _datetime.strptime(df.loc[row]['RptgPrd']['FrDtToDt']['FrDt'], '%Y-%m-%d').date()
                        out.loc[row, 'ToDt'] = _datetime.strptime(df.loc[row]['RptgPrd']['FrDtToDt']['ToDt'], '%Y-%m-%d').date()
                    except:
                        out.loc[row, 'FrDt'] = np.nan
                        out.loc[row, 'ToDt'] = np.nan
                    try:
                        out.loc[row, 'TtlNbOfTxsExctd'] = int(df.loc[row]['Sttstcs']['TtlNbOfTxsExctd'])
                        out.loc[row, 'TtlVolOfTxsExctd'] = float((df.loc[row]['Sttstcs']['TtlVolOfTxsExctd']))
                    except:
                        out.loc[row, 'TtlNbOfTxsExctd'] = np.nan
                        out.loc[row, 'TtlVolOfTxsExctd'] = np.nan

                    try:
                        out.loc[row, 'Liquidity'] = df.loc[row]['Lqdty']
                    except:
                        out.loc[row, 'Liquidity'] = np.nan


            # Format
            out = out[['ISIN', 'DerivSubClss', 'FrDt', 'ToDt', 'TtlNbOfTxsExctd', 'TtlVolOfTxsExctd', 'Liquidity']]
            out = out.rename(columns={'Id': 'instrument_id'})
            out = out.rename(columns=lambda x: x.lower())



        if sdate and verbose and out[(out['frdt'] == sdate)].empty is False:
            print("\t\t Startdate %s available"%sdate)
        if edate and verbose and out[(out['todt'] == edate)].empty is False:
            print("\t\t Enddate %s available"%edate)


    if db_format:
        if asset_class == 'equity':
            out = out[['instrument_id', 'derivsubclss','frdt', 'todt', 'ttlnboftxsexctd', 'ttlvoloftxsexctd', 'liquidity']]
            out.columns = ['INSTRUMENT_ID', 'ASSET_CLASS','START_DATE', 'END_DATE', 'EU_TRADES', 'EU_VOLUME', 'LIQUID']
            out = out[['INSTRUMENT_ID', 'EU_TRADES', 'EU_VOLUME', 'START_DATE', 'END_DATE', 'ASSET_CLASS', 'LIQUID']]

        elif asset_class == 'non-equity':
            out = out[['instrument_id', 'frdt', 'todt', 'ttlnboftxsexctd', 'ttlvoloftxsexctd', 'liquidity']]
            out.columns = ['INSTRUMENT_ID', 'START_DATE', 'END_DATE', 'EU_TRADES', 'EU_VOLUME', 'LIQUID']
            out['ASSET_CLASS'] = 'EQUITY'
            out = out[['INSTRUMENT_ID', 'EU_TRADES', 'EU_VOLUME', 'START_DATE', 'END_DATE', 'ASSET_CLASS', 'LIQUID']]


    return out, out_orig





def si_simulation():


    from tools.snowflake_db import db_connection as db


    # Import TRPT Trades
    qry_trpt = '''
        SELECT
            --anm_trade."executed_at" as executed_at,
            --anm_trade."executed_at"::date as ddate,
            IFF(anm_trade."group_id" IS NULL, 'id_null', anm_trade."group_id") as group_id,
            anm_trade."instrument_id" as instrument_id,
            anm_trade."exchange_id" as exchange_id,
            anm_trade."execution_price" as execution_price,
            anm_trade."execution_size" as quantity,
            anm_trade."execution_price" * anm_trade."execution_size" AS volume
        FROM
            BACKEND_PRD.PORTFOLIO.ANONYMIZED_TRADE as anm_trade
        WHERE
            anm_trade."executed_at"::DATE BETWEEN '2022-10-01' AND '2023-03-31'
        AND
            anm_trade."instrument_id"= 'KY30744W1070'
        AND
            anm_trade."exchange_id" in ('LSX', 'TRPT')
        AND
            anm_trade."sec_acc_no" <> '9800001301'
        ORDER BY 1
    '''

    df_trpt = db.run_query(query=qry_trpt)

    # Subset by grouping LSX + TRPT trades, which have a shared group_id. These are the fractional trades OTC trades
    df_ft = df_trpt[df_trpt.group_id != 'id_null'].iloc[:, [0, 1, -1]].groupby(['group_id', 'instrument_id']).sum()
    df_ft = df_ft.reset_index()

    # Subset of integer LSX trades
    df_int = df_trpt[df_trpt.group_id == 'id_null'][['group_id','instrument_id', 'volume']]

    # Combine
    df_tot = pd.concat([df_ft, df_int], axis=0)

    # Calculate SI Thresholds
    # OTC
    df_tot['otc_trades_L6M'] = 0
    df_tot['otc_trades_L6M'].loc[df_tot.group_id != 'id_null'] = 1
    df_tot['otc_trade_turnover_L6M'] = 0
    df_tot['otc_trade_turnover_L6M'].loc[df_tot.group_id != 'id_null'] = df_tot['volume'].loc[df_tot.group_id != 'id_null']
    # Total
    df_tot['total_trades_L6M'] = 1
    df_tot['total_trade_turnover_L6M'] = df_tot['volume']


    return df_tot


def read_esma_non_eq(pth, startdate, enddate, verbose):
    """
    Unwrapper of ESMA SI Data files for Non-Equity Instruments
    """

    # Import modules
    import xmltodict
    import polars as pl
    from datetime import datetime as _datetime


    if verbose:
        print("\n ****** Unpacking File %s"%pth)

    # Set Output
    out = pd.DataFrame()

    for fname in [k for k in os.listdir(pth) if k.endswith('xml')]:
        # Parse the XML file
        print("\n\t\t Opening: %s"%fname)
        with open(os.path.join(pth, fname)) as xml_file:
            data_dict = xmltodict.parse(xml_file.read())

        try:
            if verbose:
                print("\t\t Creating polas dataframe")
            df = pl.DataFrame(data_dict['BizData']['Pyld']['Document']['FinInstrmRptgNonEqtyTradgActvtyRslt']['NonEqtyTrnsprncyData'])

            if 'Sttstcs' in df.columns:
                # Unnesting the Data
                df = df.unnest('Id').unnest('ISINAndSubClss').unnest('DerivSubClss')
                df = df.unnest('RptgPrd').unnest('FrDtToDt')
                df = df.unnest('Sttstcs')

                out_pl = df.select(['TechRcrdId', 'ISIN', 'Desc', 'FrDt', 'ToDt', 'TtlNbOfTxsExctd', 'TtlVolOfTxsExctd'])

                # Convert to Pandas
                tmp = out_pl.to_pandas()

                # Get Liqudity Info
                tmp['Lqdty'] = pd.DataFrame(data_dict['BizData']['Pyld']['Document']['FinInstrmRptgNonEqtyTradgActvtyRslt']['NonEqtyTrnsprncyData'])['Lqdty']

                # Format
                tmp = tmp.drop('TechRcrdId', axis=1)
                tmp.columns = ['INSTRUMENT_ID', 'ASSET_CLASS', 'START_DATE', 'END_DATE', 'EU_TRADES', 'EU_VOLUME', 'LIQUID']
                tmp = tmp[['INSTRUMENT_ID', 'EU_TRADES', 'EU_VOLUME', 'START_DATE', 'END_DATE','ASSET_CLASS','LIQUID']]

                # Slice Data
                tmp = tmp[(tmp.START_DATE == startdate.strftime('%Y-%m-%d'))&(tmp.END_DATE == enddate.strftime('%Y-%m-%d'))]

                # Format Date Columns
                tmp['START_DATE'] = tmp.START_DATE.apply(lambda x: _datetime.strptime(x,'%Y-%m-%d').date())
                tmp['END_DATE'] = tmp.END_DATE.apply(lambda x: _datetime.strptime(x,'%Y-%m-%d').date())

                # Format flaot columns
                tmp['EU_TRADES'] = tmp.EU_TRADES.astype(float)
                tmp['EU_VOLUME'] = tmp.EU_VOLUME.astype(float)

                # Append Data
                out = pd.concat([out, tmp], axis=0)

            else:
                print("\n\t\t WARNING: missing Sttstcs column. Skipping file: %s"%fname)
        except:
            print("\n\t ERROR: Skipping file: %s"%fname)


    return out

