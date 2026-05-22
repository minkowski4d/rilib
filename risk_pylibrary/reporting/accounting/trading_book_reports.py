#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os

# Import Python Modules
import numpy as np
from datetime import datetime as _datetime, date, timedelta

# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db
from portfolio_analytics import positions as pos


def build_accounting_report(account=None,sdate=date(2022,9,1), edate=None, to_pkl=True, verbose=True):
    """
    Accounting Report for Book value and PnL Figures
    @param accts: list, e.g. ['caracalla', 'tiberius']
    @param sdate: date object
    @param edate: date object
    @param to_pkl: stores df_trades dataframe in  Download folder

    @return: dictionary
    """



    if account == 'caracalla':
        account_qry = 9800001301
        data_src_primary = 'share_booking'
    elif account == 'caligula':
        account_qry = 9800003301
        data_src_primary = 'share_booking'
    elif account == 'tiberius':
        account_qry = 9800001601
        tib_acct=200
        data_src_primary = 'inquisitor'
    elif account == 'trajan':
        account_qry = 9800003601
        tib_acct=600
        data_src_primary = 'inquisitor'
    elif account == 'fx_mm0':
        account_qry = 9800005001
    elif account == 'fx_mm1':
        account_qry = 9800005201
    elif account == 'fx_mm2': 
        account_qry = 9800005401
    elif account == 'alg':
        account_qry = 9800000201
    elif account is None:
        raise Exception('ERROR: You need to Specify an Account')
    else:
        account_qry = account



    # Setting Output Dictionary
    out_dict = dict()


    # Retrieving Risk Metrics Data
    if verbose:
        print('\n ************ Getting Risk Metrics')

    qry_rm = '''
            SELECT 
                * 
            FROM 
                TEAMS_PRD.RISK_FUNCTION_SOURCE.src_curr__risk_function__mrm_trading_book_risk_metrics
            WHERE
                report_date = %s
            AND
                sec_acc_no = '%s'
            AND
                CODE in ('var999_1d_ewma','var999_1d_hs','risk_exposure_in_eur_total','var999_1d_mc','var999_1d_gjr')
            '''

    df_rm = db.run_query(query=qry_rm%(db.sqldate(edate), account_qry))
    df_rm = df_rm.sort_values(by=['sec_acc_no', 'code'])
    out_dict['df_rm'] = df_rm

    # Retrieving PnL Data
    if verbose:
        print('\n ************ Getting PnL')

    if account in ['caracalla','caligula','tiberius','trajan']:
        qry_pnl = '''
                SELECT
                    REPORT_DATE::date AS DDATE,
                    SEC_ACC_NO AS ACCOUNT,
                    INSTRUMENT_ID,
                    RPNL AS RPNL,
                    UPNL AS UPNL
                FROM
                    TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__MRM_TRADING_BOOK_PNL 
                WHERE
                    REPORT_DATE::date >= %s AND REPORT_DATE::date <= %s
                AND
                    SEC_ACC_NO = '%s'
                AND
                    data_src_primary = '%s'
                '''

        df_pnl = db.run_query(query=qry_pnl % (db.sqldate(sdate), db.sqldate(edate + timedelta(1)), account_qry, data_src_primary))
    



    # Building Position Report
    for acct in [account]:
        # Get Trades
        if verbose:
            print('\n ************ Getting Positions for %s' % (acct))

        out_dict = pos.get_port(account_qry,edate,force_rf=True)
        tmp_pf = out_dict['inventory']
        tmp_pf = tmp_pf[tmp_pf.quantity != 0]
        tmp_pf = tmp_pf[['instrument_id','sec_acc_no', 'report_date', 'instrument_type', 'name_short', 'close_bid_price_clean', 'close_mid_price_clean', 'close_ask_price_clean', 'quantity']]
        tmp_pf = tmp_pf.set_index('instrument_id')
        tmp_pf.columns = ['account', 'report_date', 'instrument_type', 'name_short', 'bid_price', 'mid_price', 'ask_price', 'quantity']
        
        # Adjusting FX
        cols = tmp_pf.columns[4:7]     # the 3 columns you want to invert
        mask = tmp_pf["instrument_type"] == "FX"
        tmp_pf.loc[mask, cols] = 1 / tmp_pf.loc[mask, cols]

        # building Prudent Val
        tmp_pf['mkt_eur_prudent'] = tmp_pf[['bid_price', 'ask_price', 'quantity']].apply(lambda row:
                                                                                row['bid_price'] * row['quantity']
                                                                                if row['quantity'] > 0
                                                                                else row['ask_price'] * row['quantity'], axis=1)
        tmp_pf['mkt_eur_prudent_short'] = tmp_pf[['ask_price', 'quantity']].apply(lambda row:
                                                                                row['ask_price'] * row['quantity']
                                                                                if row['quantity'] < 0
                                                                                else 0, axis=1)
        tmp_pf['mkt_eur_prudent_long'] = tmp_pf[['bid_price', 'quantity']].apply(lambda row:
                                                                                row['bid_price'] * row['quantity']
                                                                                if row['quantity'] > 0
                                                                                else 0, axis=1)
        tmp_pf['mkt_eur'] = tmp_pf.mid_price * tmp_pf.quantity
        tmp_pf['mkt_eur_short'] = tmp_pf[['mid_price', 'quantity']].apply(lambda row: row['mid_price'] * row['quantity'] if row['quantity'] < 0 else 0, axis=1)
        tmp_pf['mkt_eur_long'] = tmp_pf[['mid_price', 'quantity']].apply(lambda row: row['mid_price'] * row['quantity'] if row['quantity'] > 0 else 0, axis=1)

        if verbose:
            print('\n ************ Building Report for %s on %s'%(acct, edate))

        out_rep = pd.DataFrame(index=['mkt_eur_prudent', 'mkt_eur_prudent_short', 'mkt_eur_prudent_long', 'mkt_eur', 'mkt_eur_short', 'mkt_eur_long',
                                      'var999_1d_hs', 'pnl_realised', 'pnl_unrealised'])


        # Build Positions
        tmp_rep = tmp_pf[['mkt_eur_prudent', 'mkt_eur_prudent_short', 'mkt_eur_prudent_long', 'mkt_eur', 'mkt_eur_short', 'mkt_eur_long']].sum().to_frame(name=edate)
        try:
            tmp_rep.loc['var999_1d_hs'] = df_rm[df_rm.report_date == edate][df_rm.code == 'var999_1d_hs'][df_rm.sec_acc_no == str(account_qry)].rm_value.iloc[0]
        except:
            tmp_rep.loc['var999_1d_hs'] = np.nan
            print('\n\t\t Warning: could not find risk metrics data for %s on %s'%(acct, edate))
        
        if account in ['caracalla','caligula','tiberius','trajan']:
            # Treat PnL Data
            tmp_pnl = df_pnl.copy()
            tmp_pnl['ddate'] = pd.to_datetime(tmp_pnl.ddate)
            tmp_pnl = tmp_pnl[(tmp_pnl.ddate.dt.month == edate.month) & (tmp_pnl.ddate.dt.year == edate.year)]
            tmp_pnl = tmp_pnl.sort_values(by='ddate')

            if tmp_pnl.empty:
                tmp_rep.loc['pnl_realised'] = np.nan
                tmp_rep.loc['pnl_unrealised'] = np.nan
                print('\n\t\t Warning: could not find pnl data for %s on %s' % (acct,edate))
            else:
                if verbose:
                    print('\n\t\t Slicing PnL Report from %s to %s'%(tmp_pnl.ddate.iloc[0].date(), tmp_pnl.ddate.iloc[-1].date()))


                tmp_pnl_grp = tmp_pnl[['ddate','rpnl','upnl']].groupby('ddate').sum()

                # Add ISIN based levels
                tmp_pf = tmp_pf.join(tmp_pnl[['instrument_id', 'rpnl']].groupby('instrument_id').sum())
                tmp_pf = tmp_pf.join(tmp_pnl[tmp_pnl.ddate == tmp_pnl.ddate.max()][['instrument_id', 'upnl']].set_index('instrument_id'))

                # Adding aggregated PnL figures to report
                tmp_rep.loc['pnl_realised'] = tmp_pnl_grp.rpnl.sum()
                tmp_rep.loc['pnl_unrealised'] = tmp_pnl_grp.upnl.iloc[-1]

                if tmp_pnl_grp.rpnl.sum() != tmp_pf.rpnl.sum():
                    if verbose:
                        print('\n\t\t Delta rPnL from for %s on %s: %s'%(acct, edate, tmp_pnl_grp.rpnl.sum() - tmp_pf.rpnl.sum()))
                    tmp_pf['rpnl'] += tmp_pf.rpnl / tmp_pf.rpnl.sum() * (tmp_pnl_grp.rpnl.sum() - tmp_pf.rpnl.sum())

                if tmp_pnl_grp.upnl.iloc[-1] != tmp_pf.upnl.sum():
                    if verbose:
                        print('\n\t\t Delta uPnL from for %s on %s: %s'%(acct, edate, tmp_pnl_grp.upnl.iloc[-1] - tmp_pf.upnl.sum()))
                    tmp_pf['upnl'] += tmp_pf.upnl / tmp_pf.upnl.sum() * (tmp_pnl_grp.upnl.iloc[-1] - tmp_pf.upnl.sum())

        # Adding tmp report to output
        out_rep = pd.concat([out_rep, tmp_rep], axis=1)

    # Adding ISIN based report to output
    out_dict['%s_pos_%s' % (acct, edate.strftime('%Y%m%d'))] = tmp_pf

    out_dict['%s_report_month'%acct] = out_rep


    # Build Excel Report
    dict_sec_acc_no = {'tiberius':'9800001601', 
                       'caligula':'9800003301', 
                       'caracalla':'9800001301', 
                       'trajan':'9800003601',
                       'fx_mm0':'9800005001', 
                       'fx_mm1':'9800005201', 
                       'fx_mm2':'9800005401'
                       }
    out_pos = pd.DataFrame()
    for acct in [account]:
        for k in out_dict.keys():
            if k.endswith('month'):
                if k.startswith(acct):
                    tmp_pos = out_dict[k].reset_index()
                    tmp_pos['sec_acc_no'] = dict_sec_acc_no[acct]
                    out_pos = pd.concat([out_pos, tmp_pos.groupby(['sec_acc_no', 'index']).sum()], axis=0)
            if k.startswith('%s_pos'%acct):
                out_dict[k].to_csv('/Users/fabioballoni/Downloads/%s_%s_positions.csv'%(edate.strftime('%Y%m%d'), dict_sec_acc_no[acct]))


    return out_dict




def book_recon_report(account, enddate):


    # Set Output
    out_dict = dict()

    if account == 'tiberius':
        qry ='''
            with mart_trades as (
            SELECT
                convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::TIMESTAMP_NTZ as TRADE_TS,
                mart_sb_trade.instrument_id AS INSTRUMENT_ID,
                IFF(mart_sb_trade.booking_direction = 'DEBIT', -1*mart_sb_trade.net_size, mart_sb_trade.net_size) AS QUANTITY
            FROM
                TEAMS_PRD.CORE_MART.MRT_CURR__SHARE_BOOKING as mart_sb_trade
            WHERE
                convert_timezone('Europe/Berlin',mart_sb_trade.booked_ts)::date  BETWEEN '2023-12-01' AND %s
            AND
                mart_sb_trade.securities_account_number = 9800001601
            UNION ALL
            SELECT
                convert_timezone('Europe/Berlin',jpm_trade."executed_at")::TIMESTAMP_NTZ as TRADE_TS,
                jpm_trade."instrument_id" AS INSTRUMENT_ID,
                IFF(jpm_trade."trade_direction" = 'BUY', 1, -1)*jpm_trade."execution_size" AS QUANTITY
            FROM
                BACKEND_PRD.POST_TRADING_TIBERIUS.PUBLIC_TRADE as jpm_trade
            WHERE
                convert_timezone('Europe/Berlin',jpm_trade."executed_at")::date  BETWEEN '2023-12-01' AND %s
            AND
                jpm_trade."sec_acc_no" = 9800001601
            
            -- Remove Duplicates
            QUALIFY ROW_NUMBER() OVER(PARTITION BY "id" ORDER BY "updated_at" ASC) = 1
            ORDER BY 1, 2
            ),
            
            mart_tr_grouped as (
            SELECT
                mart_tr.INSTRUMENT_ID as instrument_id,
                SUM(mart_tr.QUANTITY) AS quantity
            FROM
                mart_trades AS mart_tr
            GROUP BY 1
            ),
            
            
            risk_pos as (
            SELECT
                ri.report_date::date as ddate,
                ri.INSTRUMENT_ID as instrument_id,
                ri.QUANTITY AS QUANTITY_RISK
            FROM
                TEAMS_PRD.RISK_DATA.MR_PORT_POS AS ri
            WHERE
                ri.report_date::date = %s
            AND
                account='tiberius'
            ORDER BY 1,2
            ),
            
            tib_pos as (
            SELECT 
                DDATE,
                INSTRUMENT_ID,
                POSITION_SIZE AS QUANTITY_TIB 
            FROM 
                TEAMS_PRD.RISK_DATA.TIB_POS_DAILY 
            WHERE 
                DDATE=(SELECT MAX(DDATE) FROM TEAMS_PRD.RISK_DATA.TIB_POS_DAILY))
            
            
            SELECT
                %s as report_date,
                mart_tr_grp.INSTRUMENT_ID as instrument_id,
                mart_tr_grp.quantity as quantity_mart_sb,
                tib.QUANTITY_TIB,
                ri.QUANTITY_RISK
            FROM
                mart_tr_grouped AS mart_tr_grp
            LEFT OUTER JOIN
                (SELECT * FROM tib_pos) AS tib 
            ON tib.INSTRUMENT_ID = mart_tr_grp.INSTRUMENT_ID
            LEFT OUTER JOIN
                (SELECT * FROM risk_pos) AS ri 
            ON ri.INSTRUMENT_ID = mart_tr_grp.INSTRUMENT_ID
            ORDER BY 
                1,2;
            '''

    df = db.run_query(query=qry%(db.sqldate(enddate),
                                 db.sqldate(enddate),
                                 db.sqldate(enddate),
                                 db.sqldate(enddate)))

    out_dict['recon_tot'] = df

    # Slice if sb == trading book 1LoD source
    if account == 'tiberius':
        main_source = 'quantity_tib'

    out_dict['recon_sb'] = df[np.round(df.quantity_mart_sb, 6) == np.round(df[main_source], 6)]

    return df



def ls_report_acct(pth,rpnl_base,upnl_base,dd_base,dd_end):

    # Create tmp output
    df = pd.DataFrame()
    pth = os.path.expanduser(pth)

    # Ingest Data
    for nms in os.listdir(pth):
        try:
            df = pd.concat([df, pd.read_csv(os.path.join(pth, nms))], axis=0)
        except Exception:
            print(nms)

    # Format df
    df = df.sort_values(by='report_date')
    df = df[['report_date','instrument_id','quantity','mkt_eur','rpnl','upnl']]

    # Set Overall OutPut
    out = pd.DataFrame(index=df.instrument_id.unique())

    # Setting M2M Value at Endddate and LongShort Direction
    out_mkt = df[df.report_date == dd_end][['instrument_id', 'quantity', 'mkt_eur']].groupby('instrument_id').sum()
    out = out.join(out_mkt, how='outer')
    out['direction'] = out['mkt_eur'].apply(lambda x: 'Long' if x >= 0 else 'Short')

    # Get realised PnL
    out_rpnl = df[df.report_date != dd_base][['instrument_id', 'rpnl']].groupby('instrument_id').sum()
    out = out.join(out_rpnl, how='outer')
    _rpnl_raw = out['rpnl'].copy()
    _rpnl_scale = rpnl_base / _rpnl_raw.sum()
    out['rpnl'] = _rpnl_raw * _rpnl_scale
    _rpnl_delta = out['rpnl'] - _rpnl_raw
    print(
        f"\n [RPNL Rebase | {len(out)} instruments]"
        f"\n   Raw total    : {_rpnl_raw.sum():>14,.2f}"
        f"\n   Target       : {rpnl_base:>14,.2f}"
        f"\n   Gap          : {rpnl_base - _rpnl_raw.sum():>14,.2f}"
        f"\n   Scale factor : {_rpnl_scale:>14.6f}"
        f"\n   Delta max    : {_rpnl_delta.max():>14,.2f}  ({_rpnl_delta.idxmax()})"
        f"\n   Delta min    : {_rpnl_delta.min():>14,.2f}  ({_rpnl_delta.idxmin()})"
        f"\n   Delta mean   : {_rpnl_delta.mean():>14,.2f}"
    )

    # Get unrealised PnL
    out_upnl=pd.pivot_table(df[['instrument_id','report_date','upnl']],
                            index='instrument_id',
                            columns='report_date',
                            values='upnl',
                            aggfunc=np.sum)

    out_upnl_diff = out_upnl.diff(axis=1)
    out_upnl_diff['upnl'] = out_upnl_diff.sum(axis=1)
    _upnl_raw = out_upnl_diff['upnl'].copy()
    _upnl_scale = upnl_base / _upnl_raw.sum()
    out_upnl_diff['upnl'] = _upnl_raw * _upnl_scale
    _upnl_delta = out_upnl_diff['upnl'] - _upnl_raw
    print(
        f"\n [UPNL Rebase | {len(out_upnl_diff)} instruments]"
        f"\n   Raw total    : {_upnl_raw.sum():>14,.2f}"
        f"\n   Target       : {upnl_base:>14,.2f}"
        f"\n   Gap          : {upnl_base - _upnl_raw.sum():>14,.2f}"
        f"\n   Scale factor : {_upnl_scale:>14.6f}"
        f"\n   Delta max    : {_upnl_delta.max():>14,.2f}  ({_upnl_delta.idxmax()})"
        f"\n   Delta min    : {_upnl_delta.min():>14,.2f}  ({_upnl_delta.idxmin()})"
        f"\n   Delta mean   : {_upnl_delta.mean():>14,.2f}"
    )

    # Join to final output
    out = out.join(out_upnl_diff[['upnl']], how='outer')

    return out
    



