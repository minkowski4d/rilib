#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Import Python Modules
from datetime import date
from typing import Optional, List, Any
import numpy as np

# Custom Modules
import pandas as pd
from tools.snowflake_db import db_connection as db
from risk_pylibrary.instruments import data_rf_wrapper as rw
from risk_pylibrary.instruments import data_prices as dtp
from risk_pylibrary.risk_analytics import risk_engines as rie



def get_public_trade(sec_acc_no: int) -> pd.DataFrame:
    """
    Fetches public trade data for a given security account number.

    Args:
        sec_acc_no: Security Account Number

    Returns:
        DataFrame containing trade data.

    Raises:
        ValueError: If sec_acc_no is not a valid integer.
    """
    if not isinstance(sec_acc_no, int) or sec_acc_no <= 0:
        raise ValueError(f"sec_acc_no must be a positive integer, got: {sec_acc_no}")

    qry = '''
    SELECT
        *
    FROM
        backend_prd.portfolio.public_trade
    WHERE
        "sec_acc_no"=%s
    '''

    df = db.run_query(query=qry % (sec_acc_no))

    return df


def get_trades_pnl(
    sec_acc_no: int,
    startdate: Optional[date],
    enddate: Optional[date],
    src: str,
    **kwargs: Any
) -> pd.DataFrame:
    """
    Calculates the profit and loss (PnL) for trades within a specified date range.

    Args:
        sec_acc_no: Security Account Number
        startdate: Start date for PnL calculation.
        enddate: End date for PnL calculation.
        src: Source of the trade data.
        **kwargs: Additional optional parameters.
            syms (List[str]): List of instrument symbols to filter trades.

    Returns:
        DataFrame containing PnL data for each trade.

    Raises:
        ValueError: If startdate or enddate is None, or if sec_acc_no is invalid.
    """
    if startdate is None:
        raise ValueError('startdate must be specified')
    if enddate is None:
        raise ValueError('enddate must be specified')
    if not isinstance(sec_acc_no, int) or sec_acc_no <= 0:
        raise ValueError(f"sec_acc_no must be a positive integer, got: {sec_acc_no}")
    if startdate > enddate:
        raise ValueError(f"startdate ({startdate}) must be before or equal to enddate ({enddate})")
    
    syms: List[str] = kwargs.get('syms', [])

    tr_query = '''
        SELECT
            *
        FROM
            TEAMS_PRD.RISK_FUNCTION_TRANSFORM.trf__risk_function_mrm_book_%s_daily_pnl_trades
        WHERE
            report_date >=%s
        AND
            report_date <=%s
        AND
            data_src_primary='%s'
        '''

    if syms:
        tr_query += '''
        AND
            instrument_id in (%s)
        '''

    tr_query += '''
        ORDER BY trade_ts
        '''

    if syms:
        tr_query = tr_query % (
            str(sec_acc_no),
            db.sqldate(startdate),
            db.sqldate(enddate),
            src,
            db.joinpad(syms)
        )
    else:
        tr_query = tr_query % (
            str(sec_acc_no),
            db.sqldate(startdate),
            db.sqldate(enddate),
            src
        )

    # Fetch Trades
    df_trades = db.run_query(query=tr_query)

    # Format columns
    df_trades['multiplier'] = 1
    df_trades['booking_category'] = 'TRADING'
    df_trades['booking_type'] = 'TRADING'

    df_trades = df_trades[[
        'trade_ts', 'report_date', 'instrument_id',
        'side', 'booking_category', 'booking_type',
        'price', 'quantity', 'quantity_signed',
        'multiplier', 'data_src_primary'
    ]]

    df_trades.columns = [
        'time', 'booking_date', 'symbol',
        'side', 'booking_category', 'booking_type',
        'price', 'quantity', 'quantity_signed',
        'multiplier', 'data_src_primary'
    ]

    return df_trades



def build_eis_recon():

    """
    Builds EIS reconciliation data for given symbol.

    Args:
        sym: Instrument symbol to include in the reconciliation.
        verbose: If True, prints progress messages.
    Returns:
        Dictionary containing EIS reconciliation data.
    """


    # Set Output
    out_dict = {}

    # Fetch Risk EIS Recon Table
    qry_recon='''
        with recon as (
        SELECT
            RISK.REPORT_DATE,
            RISK.INSTRUMENT_ID,
            INFO.INSTRUMENT_TYPE,
            INFO.NAME_SHORT,
            RISK.QUANTITY as eis_risk_pos,
            EIS.quantity_eis as eis_pos,
            (RISK.QUANTITY-EIS.quantity_eis) AS DELTA,
            RISK.MKT_MID_EUR
        FROM
            TEAMS_PRD.RISK_FUNCTION_PUBLISH.PBL__RISK_FUNCTION_MRM_BOOK_TRADING_VALUATION AS RISK
        -- EIS Position
        LEFT JOIN
        (SELECT
            "isin" as instrument_id,
            "nostro_shares" as quantity_eis
            FROM
            BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_INVENTORY_POSITION) AS EIS
        ON EIS.INSTRUMENT_ID=RISK.INSTRUMENT_ID
        -- Instrument Info
        LEFT JOIN
        (SELECT
            instrument_id,
            instrument_type,
            name_short
            FROM
            TEAMS_PRD.RISK_FUNCTION_PUBLISH.PBL__RISK_FUNCTION_MRM_BOOK_MSL_INFO) AS INFO
        ON INFO.INSTRUMENT_ID=RISK.INSTRUMENT_ID
        WHERE
            1=1
        AND
            SEC_ACC_NO=9800003301
        AND
            REPORT_DATE = CURRENT_DATE()-1
        ORDER BY 1)

        SELECT 
            * 
        FROM recon 
        WHERE 
        1=1
        AND
        DELTA<>0
        '''
    
    df_recon=db.run_query(query=qry_recon)
    recon_syms=df_recon['instrument_id'].unique().tolist()

    # Assign to Output
    out_dict['pos'] = df_recon

    # Fetch Trades

    qry_ri='''
        WITH trade_detail AS (
            SELECT
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as trade_date,
                "isin" as instrument_id,
                'customer' as src,
                "status" as booking_info,
                CASE
                    WHEN "order_type"='SELL' THEN 1 * "size"
                    WHEN "order_type"='BUY' THEN -1 * "size"
                END as quantity,
                CASE WHEN "status" in ('EXECUTED', 'CORRECTED') THEN 1 ELSE 0 END as is_filtered
            FROM
                BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_CUSTOMER_ORDER
            WHERE
                1=1
            AND
                "isin" in (%s)
            AND
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= '2024-01-01'
            AND
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= CURRENT_DATE()
            UNION ALL

            SELECT
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ as report_date,
                "isin" as instrument_id,
                'inventory' as src,
                "prim_id" as booking_info,
                IFF("trade_direction"='SELL', -1, 1) * "execution_size" as quantity,
                CASE WHEN "prim_id" NOT LIKE '%%C%%' THEN 1 ELSE 0 END as is_filtered
            FROM
                BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_INVENTORY_TRADE
            WHERE
                1=1
            AND
                "isin" in (%s)
            AND
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date >= '2024-01-01'
            AND
                convert_timezone('Europe/Berlin', "created_at")::TIMESTAMP_NTZ::date <= CURRENT_DATE()
            UNION ALL

            SELECT
                TO_TIMESTAMP_NTZ(value_date) as trade_date,
                instrument_id as instrument_id,
                'corporate_action' as src,
                booking_category as booking_info,
                IFF(booking_direction='CREDIT', net_size, -net_size) AS quantity,
                CASE WHEN booking_category IN ('CORPORATE_ACTION','DELIVERY') THEN 1
                     WHEN booking_category <> 'TRADING' THEN 0
                END as is_filtered
            FROM
                TEAMS_PRD.asset_hub.pbl_curr__share_booking  as sb_trade
            WHERE
                securities_account_number = 9800003301
            AND
                (booking_category IN ('CORPORATE_ACTION','DELIVERY') OR booking_category <> 'TRADING')
            AND
                instrument_id in (%s)
            AND
                value_date >= '2024-01-01'
            AND
                value_date <= CURRENT_DATE()
        ),
        trade_stats AS (
            SELECT
                instrument_id,
                COUNT(*) as number_of_trades,
                SUM(CASE WHEN src = 'customer' THEN 1 ELSE 0 END) as number_of_customer_trades,
                SUM(CASE WHEN src = 'inventory' THEN 1 ELSE 0 END) as number_of_inventory_trades,
                SUM(CASE WHEN booking_info = 'CORPORATE_ACTION' THEN 1 ELSE 0 END) as number_of_corporate_actions,
                SUM(CASE WHEN booking_info = 'EXECUTED' THEN 1 ELSE 0 END) as number_of_executed,
                SUM(CASE WHEN booking_info = 'CORRECTED' THEN 1 ELSE 0 END) as number_of_corrected,
                SUM(CASE WHEN booking_info LIKE 'N%%' THEN 1 ELSE 0 END) as number_of_prim_ids,
                SUM(CASE WHEN booking_info LIKE '%%C' OR booking_info LIKE '%%S' THEN 1 ELSE 0 END) as number_prim_id_ending_c_or_s,
                SUM(CASE WHEN booking_info != 'CORPORATE_ACTION' AND booking_info != 'EXECUTED'
                AND booking_info != 'CORRECTED' AND booking_info NOT LIKE 'N%%'
                AND booking_info NOT LIKE '%%C' AND booking_info NOT LIKE '%%S' THEN 1 ELSE 0 END) as number_of_other_booking_info,
                SUM(quantity) as sum_eis_trades_nofilter,
                SUM(CASE WHEN is_filtered = 1 THEN quantity ELSE 0 END) as sum_eis_trades_risk
            FROM trade_detail
            GROUP BY instrument_id
        )
        SELECT
            tr.instrument_id,
            info.instrument_type,
            info.name_short,
            tr.number_of_trades,
            tr.number_of_customer_trades,
            tr.number_of_inventory_trades,
            tr.number_of_corporate_actions,
            tr.number_of_executed,
            tr.number_of_corrected,
            tr.number_of_prim_ids,
            tr.number_prim_id_ending_c_or_s,
            tr.number_of_other_booking_info,
            tr.sum_eis_trades_risk,
            eis.quantity_eis as sum_eis_pos
        FROM trade_stats as tr
        -- EIS Position
        LEFT JOIN
        (SELECT
            "isin" as instrument_id,
            "nostro_shares" as quantity_eis
            FROM
            BACKEND_PRD.EQUITIES_INVENTORY_CALIGULA.PUBLIC_INVENTORY_POSITION) AS eis
        ON eis.instrument_id = tr.instrument_id
        -- Instrument Info
        LEFT JOIN
        (SELECT
            instrument_id,
            instrument_type,
            name_short
            FROM
            TEAMS_PRD.RISK_FUNCTION_PUBLISH.PBL__RISK_FUNCTION_MRM_BOOK_MSL_INFO) AS info
        ON info.instrument_id = tr.instrument_id
        ORDER BY instrument_id
    '''

    df_trades = db.run_query(query=qry_ri%(db.joinpad(recon_syms),db.joinpad(recon_syms),db.joinpad(recon_syms)))

    # Create MultiIndex DataFrame
    # Set row index
    df_trades = df_trades.set_index(['instrument_id', 'instrument_type', 'name_short'])

    # Create column MultiIndex
    columns_multiindex = pd.MultiIndex.from_tuples([
        ('overview', 'number_of_trades'),
        ('overview', 'number_of_customer_trades'),
        ('overview', 'number_of_inventory_trades'),
        ('detail', 'number_of_corporate_actions'),
        ('detail', 'number_of_executed'),
        ('detail', 'number_of_corrected'),
        ('detail', 'number_of_prim_ids'),
        ('detail', 'number_prim_id_ending_c_or_s'),
        ('detail', 'number_of_other_booking_info'),
        ('Position', 'sum_eis_trades_risk'),
        ('Position', 'sum_eis_pos')
    ])

    df_trades.columns = columns_multiindex

    # Assign to Output
    out_dict['tr_stats'] = df_trades

    return out_dict


