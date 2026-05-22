#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime

# Custom Modules
from tools.snowflake_db import db_connection as db





def get_bond_trades(startdate=None,  enddate=None):

    qry='''
        WITH share_booking_accrued_interest AS (
            SELECT
              "booking_date" as BOOKING_DATE,
              "instrument_id" as ISIN,
              "accrued_interest_amount" / "net_size" AS ACCRUED_INTEREST
            FROM BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING sb
            INNER JOIN BACKEND_PRD.INSTRUMENT_UNIVERSE.ANONYMIZED_INSTRUMENTS__INSTRUMENT i
                ON sb."instrument_id" = i."isin"
            WHERE i."instrument_type" = 'BOND'
                AND BOOKING_DATE >= %s
                AND ACCRUED_INTEREST > 0
        ),
        agg_share_booking_accrued_interest AS (
          SELECT BOOKING_DATE, ISIN, MODE(ACCRUED_INTEREST) AS SB_ACCRUED_INTEREST
          FROM share_booking_accrued_interest
          GROUP BY BOOKING_DATE, ISIN
        ),
        booking_accrued_interest AS (
            SELECT
                SECURITIES_TRADE_CLOSING_DATE AS BOOKING_DATE,
                SECURITIES_INSTRUMENT_ISIN AS ISIN,
                AMOUNT,
                SECURITIES_QUANTITY AS QTY,
                DIV0(SECURITIES_EXECUTION_PRICE, 100) AS CLEAN_PRICE,
                (AMOUNT - (QTY*CLEAN_PRICE)) / QTY AS ACCRUED_INTEREST
            FROM 
                TEAMS_PRD.LEDGER_PLATFORM_SOURCE.SRC__BOOKING__POSTINGLINE AS POSTINGLINE
            LEFT JOIN TEAMS_PRD.LEDGER_PLATFORM_SOURCE.SRC__BOOKING__POSTING AS POSTING
                ON POSTINGLINE.POSTINGSETID = POSTING.POSTING_SET
            WHERE POSTINGLINE.GLACCOUNTID = 1000112
                AND SECURITIES_INSTRUMENT_GROUP = 'BOND'
                AND BOOKING_DATE >= %s
                AND SECURITIES_STATEMENT_AFTER_CANCELLATION_FLAG = 'N'
                AND ACCRUED_INTEREST > 0
        ),
        agg_booking_accrued_interest AS (
            SELECT BOOKING_DATE, ISIN, MODE(ACCRUED_INTEREST) AS BE_ACCRUED_INTEREST
            FROM booking_accrued_interest
            GROUP BY BOOKING_DATE, ISIN
        ),
        bond_trades AS (
            SELECT
                CONVERT_TIMEZONE('UTC','Europe/Berlin', trade_ts)::DATE AS calendar_date,
                CONVERT_TIMEZONE('UTC','Europe/Berlin', trade_ts) AS trade_ts,
                instrument_id,
                portfolio_id,
                securities_account_number,
                trade_type,
                trade_id,
                exchange_id,
                CASE
                    WHEN direction = 'SELL' AND exchange_id = 'TRPT' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TRPT' THEN 'SELL'
                    ELSE direction
                END AS trade_direction_adj,
                CASE
                    WHEN sb."accrued_interest_amount" IS NOT NULL THEN sb."accrued_interest_amount" / size
                    WHEN SB_ACCRUED_INTEREST IS NOT NULL THEN SB_ACCRUED_INTEREST
                    WHEN BE_ACCRUED_INTEREST IS NOT NULL THEN BE_ACCRUED_INTEREST
                    ELSE 0
                END AS accrued_interest,
                original_price AS clean_price,
                clean_price + accrued_interest as dirty_price,
                iff(trade_direction_adj = 'BUY', original_size, original_size * (-1)) AS signed_qty_column,
                signed_qty_column * dirty_price AS signed_vol
            FROM
              TEAMS_PRD.CORE_MART.MRT_CURR__TRADE_BACKEND t
            LEFT JOIN BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING sb
                ON trade_id = sb."trade_id"
            LEFT JOIN agg_share_booking_accrued_interest as sbai
                ON t.instrument_id = sbai.isin
                AND calendar_date = sbai.BOOKING_DATE
            LEFT JOIN agg_booking_accrued_interest as bai
                ON t.instrument_id = bai.isin
                AND calendar_date = bai.BOOKING_DATE
            WHERE
                (securities_account_number = '9800001301' OR exchange_id = 'TRPT')
                AND NOT (securities_account_number = '9800001301' AND exchange_id = 'TRPT')
                AND instrument_type = 'BOND'
                AND (
                    calendar_date != CONVERT_TIMEZONE('UTC','Europe/Berlin', first_cancellation_received_ts)::DATE
                    OR first_cancellation_received_ts IS NULL
                )
                AND LATEST_STATUS IN ('ORIGINAL', 'CANCEL')
                AND calendar_date >= %s
            UNION ALL
            SELECT
                CONVERT_TIMEZONE('UTC','Europe/Berlin', first_cancellation_received_ts)::DATE AS calendar_date,
                CONVERT_TIMEZONE('UTC','Europe/Berlin', first_cancellation_received_ts) AS trade_ts,
                instrument_id,
                portfolio_id,
                securities_account_number,
                trade_type,
                trade_id,
                exchange_id,
                CASE
                    WHEN direction = 'SELL' AND exchange_id = 'TRPT' THEN 'BUY'
                    WHEN direction = 'BUY' AND exchange_id = 'TRPT' THEN 'SELL'
                    ELSE direction
                END AS trade_direction_adj,
                CASE
                    WHEN sb."accrued_interest_amount" IS NOT NULL THEN sb."accrued_interest_amount" / size
                    WHEN SB_ACCRUED_INTEREST IS NOT NULL THEN SB_ACCRUED_INTEREST
                    WHEN BE_ACCRUED_INTEREST IS NOT NULL THEN BE_ACCRUED_INTEREST
                    ELSE 0
                END AS accrued_interest,
                price AS clean_price,
                clean_price + accrued_interest as dirty_price,
                iff(trade_direction_adj = 'BUY', size, size * (-1)) AS signed_qty_column,
                signed_qty_column * dirty_price AS signed_vol
            FROM
              TEAMS_PRD.CORE_MART.MRT_CURR__TRADE_BACKEND t
            INNER JOIN BACKEND_PRD.PORTFOLIO.ANONYMIZED_TRADE bt
                ON bt."id" = trade_id
            LEFT JOIN BACKEND_PRD.PORTFOLIO.ANONYMIZED_SHARE_BOOKING sb
                ON trade_id = sb."trade_id"
            LEFT JOIN agg_share_booking_accrued_interest as sbai
                ON t.instrument_id = sbai.isin
                AND calendar_date = sbai.BOOKING_DATE
            LEFT JOIN agg_booking_accrued_interest as bai
                ON t.instrument_id = bai.isin
                AND calendar_date = bai.BOOKING_DATE
            WHERE
                (securities_account_number = '9800001301' OR exchange_id = 'TRPT')
                AND NOT (securities_account_number = '9800001301' AND exchange_id = 'TRPT')
                AND instrument_type = 'BOND'
                AND (
                    TRADE_TS::DATE != CONVERT_TIMEZONE('UTC','Europe/Berlin', first_cancellation_received_ts)::DATE
                    OR first_cancellation_received_ts IS NULL
                )
                AND LATEST_STATUS IN ('NEW')
                AND calendar_date >= %s
        )
        SELECT
            calendar_date,
            trade_ts,
            instrument_id,
            portfolio_id,
            securities_account_number,
            trade_id,
            clean_price as clean_price,
            dirty_price as dirty_price,
            signed_qty_column
        FROM
            bond_trades
    '''

    sql_sdate = db.sqldate(startdate)
    qry_adj = qry%(sql_sdate, sql_sdate, sql_sdate, sql_sdate)


    df = db.run_query(query=qry_adj)

    return df



