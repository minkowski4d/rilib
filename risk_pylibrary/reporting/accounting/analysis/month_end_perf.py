#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pandas as pd
from tools.snowflake_db import db_connection as db
from risk_models import pnl_support as pnl_sup


# ----------------------------------------------------------------------
# Global Values
# ----------------------------------------------------------------------

_CACHE = {'pos': None, 'pnl': None, 'risk': None, 'vol': None}

PARAMS_PNL = {
    9800001301: 'share_booking',   # FT 1.0
    9800003301: 'share_booking',   # FT SSP
    9800001601: 'inquisitor',      # Tiberius
    9800003601: 'inquisitor',      # FT 2.0
}




# ----------------------------------------------------------------------
# Sub-functions
# ----------------------------------------------------------------------

def trading_book_pos(sec_acc_no, sdate, edate, fetch_cache=True, verbose=True):
    """
    Positions-based analytics over a period from the trading book valuation table.

    Returns:
        dict with keys:
            'asset_class_breakdown' : DataFrame grouped by [sec_acc_no, instrument_type] at edate
            'instrument_count'      : Series of daily unique instrument count
            'book_size'             : dict with 'daily' DataFrame, 'avg_gross', 'avg_net'
    """

    sec_acc_no = [int(x) for x in sec_acc_no]

    if _CACHE['pos'] is not None and fetch_cache is False:
        if verbose:
            print(f'\n *** [pos] Using cached data ({len(_CACHE["pos"]):,} rows)')
        df = _CACHE['pos'].copy()
    else:
        if verbose:
            print(f'\n *** [pos] Fetching positions {sdate} → {edate}')

        qry = f'''
            SELECT
                report_date::date                      AS report_date,
                sec_acc_no,
                instrument_id,
                instrument_type,
                name_short,
                quantity,
                mkt_mid_eur                            AS mkt_eur_net,
                ABS(mkt_mid_eur)                       AS mkt_eur_gross,
                IFF(mkt_mid_eur > 0, mkt_mid_eur, 0)  AS mkt_eur_long,
                IFF(mkt_mid_eur < 0, mkt_mid_eur, 0)  AS mkt_eur_short
            FROM
                TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation
            WHERE
                report_date::date BETWEEN {db.sqldate(sdate)} AND {db.sqldate(edate)}
            AND
                quantity != 0
            AND
                sec_acc_no IN ({', '.join(str(x) for x in sec_acc_no)})
            ORDER BY 1, 2
        '''

        df = db.run_query(query=qry)
        _CACHE['pos'] = df.copy()

    df['report_date'] = pd.to_datetime(df['report_date'])
    out = {}

    # Asset class breakdown at edate
    df_end = df[df['report_date'] == pd.to_datetime(edate)]
    out['asset_class_breakdown'] = df_end.groupby(['sec_acc_no', 'instrument_type']).agg(
        n_instruments=('instrument_id', 'count'),
        mkt_eur_net=  ('mkt_eur_net',   'sum'),
        mkt_eur_gross=('mkt_eur_gross', 'sum'),
        mkt_eur_long= ('mkt_eur_long',  'sum'),
        mkt_eur_short=('mkt_eur_short', 'sum'),
    )

    # Daily instrument count
    out['instrument_count'] = (
        df.groupby('report_date')['instrument_id']
        .nunique()
        .rename('n_instruments')
    )

    # Gross / net book size
    daily_book = df.groupby('report_date').agg(
        net_book=  ('mkt_eur_net',   'sum'),
        gross_book=('mkt_eur_gross', 'sum'),
    )
    out['book_size'] = {
        'daily':     daily_book,
        'avg_gross': daily_book['gross_book'].mean(),
        'avg_net':   daily_book['net_book'].mean(),
    }

    if verbose:
        print(f'\n   Avg gross book: {out["book_size"]["avg_gross"]:>18,.0f} EUR')
        print(f'\n   Avg net book  : {out["book_size"]["avg_net"]:>18,.0f} EUR')

    return out


def trading_book_pnl(sec_acc_no, sdate, edate, fetch_cache=True, verbose=True):
    """
    Daily realised and unrealised P&L over a period.

    Returns:
        dict with keys:
            'pnl_daily'   : DataFrame of daily [rpnl, upnl] aggregated across instruments
            'pnl_by_isin' : DataFrame of [rpnl, upnl] per instrument_id over the period
    """

    sec_acc_no = [int(x) for x in sec_acc_no]

    if _CACHE['pnl'] is not None and fetch_cache is False:
        if verbose:
            print(f'\n *** [pnl] Using cached data ({len(_CACHE["pnl"]):,} rows)')
        df = _CACHE['pnl'].copy()
    else:
        if verbose:
            print(f'\n *** [pnl] Fetching P&L {sdate} → {edate}  (accounts {sec_acc_no})')

        case_stmt = 'CASE SEC_ACC_NO\n' + ''.join(
            f"            WHEN {acct} THEN '{src}'\n"
            for acct, src in PARAMS_PNL.items()
            if acct in sec_acc_no
        ) + '        END'

        qry = f'''
            SELECT
                REPORT_DATE::date  AS report_date,
                SEC_ACC_NO         AS sec_acc_no,
                INSTRUMENT_ID      AS instrument_id,
                RPNL               AS rpnl,
                UPNL               AS upnl
            FROM
                TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION__MRM_TRADING_BOOK_PNL
            WHERE
                REPORT_DATE::date BETWEEN {db.sqldate(sdate)} AND {db.sqldate(edate)}
            AND
                SEC_ACC_NO IN ({', '.join(str(x) for x in sec_acc_no)})
            AND
                data_src_primary = {case_stmt}
            ORDER BY 1, 3
        '''

        df = db.run_query(query=qry)
        _CACHE['pnl'] = df.copy()

    df['report_date'] = pd.to_datetime(df['report_date'])

    pnl_daily = df.groupby(['report_date', 'sec_acc_no'])[['rpnl', 'upnl']].sum()

    pnl_by_isin = df.groupby(['sec_acc_no', 'instrument_id']).agg(
        rpnl=('rpnl', 'sum'),
        upnl=('upnl', 'last'),
    )

    if verbose:
        print(f'\n   Total rPnL: {pnl_daily["rpnl"].sum():>18,.0f} EUR')
        print(f'\n   Last uPnL : {pnl_daily["upnl"].iloc[-1]:>18,.0f} EUR')

    return {'pnl_daily': pnl_daily, 'pnl_by_isin': pnl_by_isin}


def trading_book_risk(sec_acc_no, sdate, edate, fetch_cache=True, verbose=True):
    """
    Risk metrics over a period.

    Returns:
        dict with key:
            'risk_metrics' : DataFrame of risk metric codes and values from sdate to edate
    """

    sec_acc_no = [int(x) for x in sec_acc_no]

    if _CACHE['risk'] is not None and fetch_cache is False:
        if verbose:
            print(f'\n *** [risk] Using cached data ({len(_CACHE["risk"]):,} rows)')
        df = _CACHE['risk'].copy()
    else:
        if verbose:
            print(f'\n *** [risk] Fetching risk metrics {sdate} → {edate}  (accounts {sec_acc_no})')

        qry = f'''
            SELECT
                report_date::date  AS report_date,
                sec_acc_no,
                code,
                rm_value
            FROM
                TEAMS_PRD.RISK_FUNCTION_SOURCE.src_curr__risk_function__mrm_trading_book_risk_metrics
            WHERE
                report_date BETWEEN {db.sqldate(sdate)} AND {db.sqldate(edate)}
            AND
                sec_acc_no::varchar IN ({', '.join(f"'{x}'" for x in sec_acc_no)})
            AND
                code IN ('var999_1d_ewma', 'var999_1d_hs', 'var999_1d_mc', 'var999_1d_gjr',
                         'var990_1d_ewma', 'var990_1d_hs', 'var990_1d_mc', 'var990_1d_gjr',
                         'cvar950_1d_ewma', 'cvar950_1d_hs', 'cvar950_1d_mc', 'cvar950_1d_gjr')
            ORDER BY 2, 3
        '''

        df = db.run_query(query=qry)
        _CACHE['risk'] = df.copy()


    return {'risk_metrics': df}


# ----------------------------------------------------------------------
# Top / Bottom performers
# ----------------------------------------------------------------------

def trading_book_top_bottom(n=10, verbose=True):
    """
    Top and bottom n instruments by total PnL (rPnL + uPnL).

    Requires _CACHE['pos'] and _CACHE['pnl'] to be populated first
    (call trading_book_summary or the individual sub-functions).

    Returns:
        dict with keys:
            'top'        : DataFrame — top n by total_pnl
            'bottom'     : DataFrame — bottom n by total_pnl
            'top_bottom' : DataFrame — both combined, sorted by total_pnl desc

        Columns: sec_acc_no, instrument_id, name_short, instrument_type,
                 rpnl, upnl, total_pnl, avg_gross_pos, avg_net_pos
    """

    if _CACHE['pos'] is None or _CACHE['pnl'] is None:
        raise RuntimeError('Cache empty — run trading_book_summary (or pos + pnl sub-functions) first.')

    df_pos = _CACHE['pos'].copy()
    df_pnl = _CACHE['pnl'].copy()

    # Metadata: name and instrument_type taken from the last available date
    edate = df_pos['report_date'].max()
    df_meta = (
        df_pos[df_pos['report_date'] == edate][['sec_acc_no', 'instrument_id', 'name_short', 'instrument_type']]
        .drop_duplicates(subset=['sec_acc_no', 'instrument_id'])
        .set_index(['sec_acc_no', 'instrument_id'])
    )

    # Average daily gross / net position over the period (trading volume proxy)
    avg_pos = df_pos.groupby(['sec_acc_no', 'instrument_id']).agg(
        avg_gross_pos=('mkt_eur_gross', 'mean'),
        avg_net_pos=  ('mkt_eur_net',   'mean'),
    )

    # PnL per instrument
    pnl = df_pnl.groupby(['sec_acc_no', 'instrument_id']).agg(
        rpnl=('rpnl', 'sum'),
        upnl=('upnl', 'last'),
    )
    pnl['total_pnl'] = pnl['rpnl'] + pnl['upnl']

    # Join
    result = pnl.join(avg_pos, how='left').join(df_meta, how='left')
    result = result[['name_short', 'instrument_type', 'rpnl', 'upnl', 'total_pnl', 'avg_gross_pos', 'avg_net_pos']]

    top    = result.nlargest(n, 'total_pnl')
    bottom = result.nsmallest(n, 'total_pnl')
    top_bottom = pd.concat([top, bottom]).sort_values('total_pnl', ascending=False)

    if verbose:
        print(f'\n *** Top {n} performers (total PnL):')
        print(top[['instrument_type', 'name_short', 'total_pnl']].to_string())
        print(f'\n *** Bottom {n} performers (total PnL):')
        print(bottom[['instrument_type', 'name_short', 'total_pnl']].to_string())

    return {'top': top, 'bottom': bottom, 'top_bottom': top_bottom}


# ----------------------------------------------------------------------
# Trading Volume for Top / Bottom instruments
# ----------------------------------------------------------------------

def trading_book_volume(sec_acc_no, sdate, edate, n=20, fetch_cache=True, verbose=True):
    """
    Daily trading volume for the top/bottom n instruments by total PnL.

    Fetches trades via pnl_support.get_trades_pnl_new, using the
    data_src_primary from PARAMS_PNL per account.
    Requires _CACHE['pos'] and _CACHE['pnl'] to be populated first.

    Args:
        sec_acc_no (list) : Account numbers
        sdate (date)      : Period start date
        edate (date)      : Period end date
        n (int)           : Number of top and bottom instruments to include (default 20)
        fetch_cache (bool): If False, reuses _CACHE['vol']
        verbose (bool)    : Print progress messages

    Returns:
        dict with keys:
            'daily_volume' : DataFrame grouped by [booking_date, sec_acc_no, symbol]
                             columns: notional_volume, n_trades, net_quantity
            'trades'       : Raw trades DataFrame filtered to top/bottom instruments
    """

    sec_acc_no = [int(x) for x in sec_acc_no]

    # Resolve top/bottom instrument universe
    tb = trading_book_top_bottom(n=n, verbose=False)
    instruments = tb['top_bottom'].index.get_level_values('instrument_id').unique().tolist()

    if _CACHE['vol'] is not None and fetch_cache is False:
        if verbose:
            print(f'\n *** [vol] Using cached data ({len(_CACHE["vol"]):,} rows)')
        df_trades = _CACHE['vol'].copy()
    else:
        dfs = []
        for acct in sec_acc_no:
            data_src = PARAMS_PNL.get(acct)
            if verbose:
                print(f'\n *** [vol] Fetching trades for {acct} ({data_src})  {sdate} → {edate}')

            try:
                tmp = pnl_sup.get_trades_pnl_new(
                    account=acct,
                    startdate=sdate,
                    enddate=edate,
                    data_src=data_src,
                )
                tmp['sec_acc_no'] = acct
                dfs.append(tmp)
            except Exception as e:
                print(f'\n *** [vol] WARNING: failed to fetch trades for {acct} — {e}')
                tmp = pd.DataFrame(columns=['time', 'booking_date', 'symbol', 'side',
                                            'booking_category', 'booking_type', 'price',
                                            'quantity', 'quantity_signed', 'multiplier',
                                            'data_src_primary', 'sec_acc_no'])
                dfs.append(tmp)

        df_trades = pd.concat(dfs, ignore_index=True)
        _CACHE['vol'] = df_trades.copy()

    # Filter to top/bottom universe
    df_trades = df_trades[df_trades['symbol'].isin(instruments)].copy()
    df_trades['booking_date'] = pd.to_datetime(df_trades['booking_date'])
    df_trades['notional'] = df_trades['quantity_signed'].abs() * df_trades['price']

    daily_vol = df_trades.groupby(['booking_date', 'sec_acc_no', 'symbol']).agg(
        notional_volume=('notional',        'sum'),
        n_trades=       ('quantity',        'count'),
        net_quantity=   ('quantity_signed', 'sum'),
    )

    if verbose:
        print(f'\n   Instruments covered : {df_trades["symbol"].nunique()}')
        print(f'\n   Total notional vol  : {daily_vol["notional_volume"].sum():>18,.0f}')

    return {'daily_volume': daily_vol, 'trades': df_trades}


# ----------------------------------------------------------------------
# Top-level orchestrator
# ----------------------------------------------------------------------

def trading_book_summary(sdate, edate, sec_acc_no_list=[], n_top_bottom=20, fetch_cache=True, verbose=True):
    """
    Full trading book summary: positions, P&L, risk metrics, top/bottom performers, trading volume.

    Args:
        sdate (date)          : Period start date (inclusive)
        edate (date)          : Period end date (inclusive)
        sec_acc_no_list (list): Account numbers (defaults to all in PARAMS_PNL)
        n_top_bottom (int)    : Number of top and bottom instruments for performer and volume sections
        fetch_cache (bool)    : If False, reuses cached data for all sub-functions
        verbose (bool)        : Print progress messages

    Returns:
        Merged dict from all five sub-functions
    """

    sec_acc_no = list(PARAMS_PNL.keys()) if len(sec_acc_no_list) == 0 else list(sec_acc_no_list)

    out = {}
    out.update(trading_book_pos(sec_acc_no, sdate, edate, fetch_cache=fetch_cache, verbose=verbose))
    out.update(trading_book_pnl(sec_acc_no, sdate, edate, fetch_cache=fetch_cache, verbose=verbose))
    out.update(trading_book_risk(sec_acc_no, sdate, edate, fetch_cache=fetch_cache, verbose=verbose))
    out.update(trading_book_top_bottom(n=n_top_bottom, verbose=verbose))
    out.update(trading_book_volume(sec_acc_no, sdate, edate, n=n_top_bottom, fetch_cache=fetch_cache, verbose=verbose))

    return out
