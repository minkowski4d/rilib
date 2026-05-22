#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import logging
import warnings
import numpy as np
import pandas as pd
from datetime import datetime as _datetime, time
import traceback
import polars as pl
import logging

# Import Custom Modules
from tools import config as CF
from tools.snowflake_db import db_connection as db
from risk_models import pnl_support_daily_reset as pnl_sup


warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings('ignore')

def collapse_to_synthetic_open_netpos(residual_lots: pd.DataFrame,
                                      prx_syms: pd.DataFrame,
                                      enddate) -> pd.DataFrame:
    """
    Take residual FIFO lots at EOD and produce NEXT-DAY synthetic open trades:
    - one row per symbol (net position)
    - price = EOD price (enddate)
    - time = next day 00:00:01
    """

    if residual_lots.empty:
        return pd.DataFrame(
            columns=["time","symbol","side","booking_category",
                     "booking_type","price","quantity","multiplier"]
        )

    lots = residual_lots.copy()

    # CORRECT SIGNED NETTING
    lots["signed_qty"] = np.where(
        lots["side"] == "S",
        -1.0 * lots["quantity"].astype(float),
        lots["quantity"].astype(float)
    )

    net = (
        lots.groupby(["symbol","multiplier"], as_index=False)
            .agg(qty_signed=("signed_qty", "sum"))
    )

    net = net[np.abs(net["qty_signed"]) > 1e-12]

    if net.empty:
        return pd.DataFrame(
            columns=["time","symbol","side","booking_category",
                     "booking_type","price","quantity","multiplier"]
        )

    net["side"] = np.where(net["qty_signed"] < 0, "S", "B")
    net["quantity"] = net["qty_signed"].abs()

    # correct EOD price
    eod_map = prx_syms["price"].to_dict()
    net["price"] = net["symbol"].map(eod_map)

    net = net.dropna(subset=["price"])
    if net.empty:
        return pd.DataFrame(
            columns=["time","symbol","side","booking_category",
                     "booking_type","price","quantity","multiplier"]
        )

    next_day = pd.Timestamp(enddate) + pd.Timedelta(days=1)
    net["time"] = pd.Timestamp(
        next_day.year, next_day.month, next_day.day, 0, 0, 1
    )

    net["booking_category"] = "TRADING"
    net["booking_type"] = "SYNTHETIC_OPEN"

    return net[[
        "time","symbol","side","booking_category",
        "booking_type","price","quantity","multiplier"
    ]]






def initiate_pnl_engine(
        acct, tr_sd, tr_ed, ca_sd,
        refetch_cache, save_data, save_daily,
        data_src, trade_qry, pth,
        verbose, syms=None):

    out_dict = dict()

    # ---------------------------------------------------------
    # Ensure cache anchor date is previous business day
    # ---------------------------------------------------------
    if ca_sd is None:
        ca_sd = tr_sd

    if ca_sd >= tr_sd:
        prev = pd.Timestamp(tr_sd) - pd.Timedelta(days=1)
        while prev.weekday() >= 5:
            prev -= pd.Timedelta(days=1)
        ca_sd = prev.date()

    cache_dict = build_pnl_cache(acct, tr_sd, tr_ed, ca_sd,refetch_cache, data_src, trade_qry,verbose, syms)

    df_trades = cache_dict["df_trades"].copy()
    prx = cache_dict["prx"]

    # remove signed column (not needed in engine)
    if "quantity_signed" in df_trades.columns:
        df_trades = df_trades.drop("quantity_signed", axis=1)

    out_dict["cache_dict"] = cache_dict

    # ---------------------------------------------------------
    # Trading days
    # ---------------------------------------------------------
    trading_days = [
        d.date()
        for d in pd.date_range(tr_sd, tr_ed, freq="D")
        if d.weekday() < 5
    ]

    # Forward-fill prices for any weekdays missing from the price table
    # (e.g. public holidays where the upstream table has no data).
    # Log each filled date so it is visible in production logs.
    if not prx.empty:
        all_weekdays = pd.bdate_range(tr_sd, tr_ed)
        missing = [d.date() for d in all_weekdays if d.date() not in prx.index]
        if missing:
            # Extend index using the same type as existing entries to avoid DatetimeIndex vs date mismatch
            prx = prx.reindex(sorted(set(list(prx.index) + missing))).ffill()
            for d in missing:
                prior = [x for x in prx.index if x < d]
                last_available = prior[-1] if prior else None
                logging.warning(
                    f"initiate_pnl_engine [{acct}]: no prices found for {d} in price table — "
                    f"forward-filling from {last_available}."
                )

    out_pos = pd.DataFrame(columns=["ddate", "symbol", "price", "eod_quantity", "rpnl", "upnl"])
    out_trade_pnl = pd.DataFrame()
    out_df_trades_enriched = pd.DataFrame(columns=["time", "symbol", "side", "booking_category", "booking_type", "price", "quantity", "multiplier"])

    tmp_cache = pd.DataFrame()
    last_processed_day = None

    # ---------------------------------------------------------
    # DAILY LOOP
    # ---------------------------------------------------------
    for i, current_day in enumerate(trading_days):

        if current_day not in prx.index:

            # Only hit when prx is entirely empty (no prices at all for the window)
            logging.warning(
                f"initiate_pnl_engine [{acct}]: {current_day} missing from price table after forward-fill "
                f"(prx entirely empty for this window) — day skipped, cache will not be updated."
            )
            continue

        day_end_ts = _datetime.combine(current_day, time(23, 59, 59))

        prx_tmp = prx[:current_day]

        # -------------------------------------------------
        # 1️⃣ SELECT REAL TRADES OF THIS DAY
        # -------------------------------------------------
        if last_processed_day is None:
            day_trades = df_trades[df_trades["time"] <= day_end_ts]
        else:
            prev_day_end = _datetime.combine(last_processed_day, time(23,59,59))
            day_trades = df_trades[
                (df_trades["time"] > prev_day_end) &
                (df_trades["time"] <= day_end_ts)
            ]

        # -------------------------------------------------
        # 2️⃣ BUILD SYNTHETIC OPEN FROM PREVIOUS RESIDUAL
        # -------------------------------------------------
        if tmp_cache.empty:
            tmp_trades = day_trades.copy()
        else:
            prev_day = last_processed_day

            prx_prev = prx.loc[[prev_day]].T
            prx_prev.columns = ["price"]
            prx_prev.index.name = "symbol"
            prx_prev = prx_prev.reset_index().groupby("symbol").mean()

            synthetic_open = collapse_to_synthetic_open_netpos(
                tmp_cache,
                prx_prev,
                prev_day
            )

            tmp_trades = pd.concat(
                [synthetic_open, day_trades],
                axis=0
            ).sort_values("time")

        if tmp_trades.empty:
            tmp_cache = pd.DataFrame()
            continue

        # -------------------------------------------------
        # 3️⃣ RUN FIFO ENGINE
        # -------------------------------------------------
        tmp_pos, tmp_cache, tmp_trade_pnl, tmp_df_trades = pnl_fifo_engine(
            tmp_trades,
            prx=prx_tmp,
            enddate=current_day,
            adj_ca=1,
            verbose=verbose
        )

        # -------------------------------------------------
        # 4️⃣ COLLECT OUTPUTS
        # -------------------------------------------------
        out_pos = pd.concat([out_pos, tmp_pos], axis=0)
        out_trade_pnl = pd.concat([out_trade_pnl, tmp_trade_pnl], axis=0)
        out_df_trades_enriched = pd.concat(
            [out_df_trades_enriched, tmp_df_trades],
            axis=0
        )

        last_processed_day = current_day

    # ---------------------------------------------------------
    # FINAL CLEANUP
    # ---------------------------------------------------------
    if "upnl" in out_pos.columns:
        out_pos["upnl"] = out_pos["upnl"].replace([-np.inf, np.inf], 0)

    out_pos = (
        out_pos
        .sort_values(["ddate", "symbol"])
        .reset_index(drop=True)
    )

    out_trade_pnl = out_trade_pnl.sort_index()

    out_df_trades_enriched = (
        out_df_trades_enriched
        .sort_values("time")
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # ---------------------------------------------------------
    # STORE RESULTS
    # ---------------------------------------------------------
    out_dict["out_pos"] = out_pos
    out_dict["out_cache"] = tmp_cache
    out_dict["out_trade_pnl"] = out_trade_pnl
    out_dict["out_df_trades_enriched"] = out_df_trades_enriched

    #import pdb; pdb.set_trace()
    if save_daily==0 and save_data==1:
        # Saving Files to Folder:
        print('\t Saving PnL Data to Parquet')
        df_pos=out_dict['out_pos'].copy()
        df_pos['sec_acc_no']=acct
        df_pos['data_src_primary']='inquisitor_daily_reset'
        df_pos= df_pos[['ddate', 'sec_acc_no', 'symbol', 'price', 'eod_quantity', 'rpnl', 'upnl','data_src_primary']]
        df_pos.columns = ['report_date', 'sec_acc_no', 'instrument_id', 'price', 'quantity', 'rpnl', 'upnl','data_src_primary']
        fname_pnl=pnl_sup.pnl2parquet(acct=acct,report_date=tr_ed,df_orig=df_pos,pth=pth,pnl=True)
        out_dict['fname_pnl']=fname_pnl

        print('\t Saving Cache Data to Parquet')
        df_cache=out_dict['out_cache'].copy()
        df_cache['data_src_primary']='inquisitor_daily_reset'
        fname_cache=pnl_sup.pnl2parquet(acct=acct,report_date=tr_ed,df_orig=df_cache,pth=pth,cache=True)
        out_dict['fname_cache']=fname_cache

    return out_dict



    

def build_pnl_cache(
        acct, tr_sd, tr_ed, ca_sd,
        refetch_cache, data_src,
        trade_qry, verbose, syms=None):

    """
    Historical reconstruction engine.

    1) Pull full history from anchor date (ca_sd)
    2) Compute opening inventory at tr_sd
    3) Create ONE synthetic open at tr_sd 00:00:01
    4) Append only real trades >= tr_sd
    """

    out_dict = {}

    if verbose:
        print(f"Building PnL cache (historical reconstruction) for {acct}")

    if refetch_cache == 1:

        # cache table only has 'inquisitor_daily_reset', not 'inquisitor'
        cache_data_src = "inquisitor_daily_reset" if data_src == "inquisitor" else data_src

        # --------------------------------------------------
        # 1️⃣ Try Snowflake PnL cache at ca_sd (when tr_sd != ca_sd)
        # --------------------------------------------------

        df_cache = pd.DataFrame()
        if tr_sd != ca_sd:
            print('\t\t\t Fetching Trade Cache from Snowflake')
            qry_cache = '''
                SELECT
                    TO_DATE(ca.report_date) as report_date,
                    TO_TIMESTAMP(ca.time_stamp) as time,
                    ca.sec_acc_no as account,
                    ca.instrument_id as symbol,
                    ca.side,
                    ca.booking_category,
                    ca.booking_type,
                    ca.price,
                    ca.quantity,
                    ca.multiplier,
                    ca.data_src_primary
                FROM
                    TEAMS_PRD.RISK_FUNCTION_SOURCE.SRC_CURR__RISK_FUNCTION_MRM_TRADING_BOOK_PNL_CACHE as ca
                WHERE
                    SEC_ACC_NO=%s
                AND
                    TO_DATE(ca.report_date) = %s
                AND
                    ca.data_src_primary = '%s'
                '''
            df_cache = db.run_query(query=qry_cache % (acct, db.sqldate(ca_sd), cache_data_src))
            print(f'\t\t\t\t Length of Fetched Cache: {len(df_cache)}')

            if not df_cache.empty:
                if syms is not None:
                    df_cache = df_cache[df_cache['symbol'].isin(syms)]
                df_cache['quantity_signed'] = np.where(
                    df_cache['side'] == 'S', -1 * df_cache['quantity'], df_cache['quantity']
                )
                df_cache = df_cache[['time', 'account', 'symbol', 'side',
                                     'booking_category', 'booking_type', 'price',
                                     'quantity', 'quantity_signed', 'multiplier']]
                df_cache['booking_type'] = 'SYNTHETIC_OPEN'
                df_cache['time'] = pd.Timestamp(tr_sd.year, tr_sd.month, tr_sd.day, 0, 0, 1)
                df_cache = df_cache.sort_values(by='time')

        # --------------------------------------------------
        # 2️⃣ Pull trades
        #    - from tr_sd if Snowflake cache was found (no reconstruction needed)
        #    - from ca_sd otherwise (full history needed for reconstruction)
        # --------------------------------------------------

        anchor_sd = tr_sd if not df_cache.empty else ca_sd

        if trade_qry == "daily_reset":
            db_trades_all = pnl_sup.get_trades_pnl_daily_reset(account=acct, 
                                                               startdate=anchor_sd, 
                                                               enddate=tr_ed, 
                                                               syms=syms)
            
            print(f'\t\t\t\t Length of Fetched Trades: {len(db_trades_all)}')
        else:
            raise ValueError(
                "This PnL logic only supports trade_qry='daily_reset'. "
                "For other trade query logic, refer to pnl_fifo.py."
            )

        if db_trades_all.empty and df_cache.empty:
            out_dict["df_trades"] = pd.DataFrame()
            out_dict["prx"] = pd.DataFrame()
            return out_dict

        if not db_trades_all.empty:
            db_trades_all = db_trades_all.sort_values("time").copy()

            if "quantity_signed" not in db_trades_all.columns:
                db_trades_all["quantity_signed"] = np.where(
                    db_trades_all["side"] == "S",
                    -1 * db_trades_all["quantity"],
                    db_trades_all["quantity"]
                )
            db_trades_all["account"] = acct
            db_trades_all["booking_category"] = "TRADING"
            db_trades_all["booking_type"] = db_trades_all.get("booking_type", "TRADING")
            db_trades_all["multiplier"] = 1.0

        # --------------------------------------------------
        # 3️⃣ Build df_trades
        #    Path A (Snowflake cache found): cache lots + real trades from tr_sd
        #    Path B (no cache): historical reconstruction → synthetic open at tr_sd
        # --------------------------------------------------

        if not df_cache.empty:
            # Path A: prepend Snowflake FIFO lots to real trades
            if not db_trades_all.empty:
                db_trades_all = db_trades_all[[
                    "time", "account", "symbol", "side",
                    "booking_category", "booking_type",
                    "price", "quantity", "quantity_signed", "multiplier"
                ]]
                df_trades = pd.concat([df_cache, db_trades_all], ignore_index=True)
            else:
                df_trades = df_cache.copy()

        else:
            # Path B: reconstruct opening inventory from full trade history
            tr_sd_ts = pd.Timestamp(tr_sd)
            df_hist = db_trades_all[db_trades_all["time"] < tr_sd_ts]

            if df_hist.empty:
                df_open = pd.DataFrame()
            else:
                df_open = (
                    df_hist.groupby(["account", "symbol"], as_index=False)
                           .agg(quantity_signed=("quantity_signed", "sum"))
                )
                df_open = df_open[np.abs(df_open["quantity_signed"]) > 1e-12]

            if not df_open.empty:
                prev_bd = tr_sd_ts - pd.Timedelta(days=1)
                while prev_bd.weekday() >= 5:
                    prev_bd -= pd.Timedelta(days=1)

                prx_prev = pnl_sup.get_prices_eod(
                    syms=df_open["symbol"].unique(),
                    startdate=prev_bd.date(), enddate=prev_bd.date(), fill_na=False
                )

                if prev_bd.date() in prx_prev.index:
                    eod_map = prx_prev.loc[prev_bd.date()].to_dict()
                    df_open["price"] = df_open["symbol"].map(eod_map)
                else:
                    df_open["price"] = np.nan

                df_open = df_open.dropna(subset=["price"])

                if not df_open.empty:
                    df_open["side"] = np.where(df_open["quantity_signed"] < 0, "S", "B")
                    df_open["quantity"] = df_open["quantity_signed"].abs()
                    df_open["time"] = pd.Timestamp(tr_sd.year, tr_sd.month, tr_sd.day, 0, 0, 1)
                    df_open["booking_category"] = "TRADING"
                    df_open["booking_type"] = "SYNTHETIC_OPEN"
                    df_open["multiplier"] = 1.0
                    df_open = df_open[[
                        "time", "account", "symbol", "side",
                        "booking_category", "booking_type",
                        "price", "quantity", "quantity_signed", "multiplier"
                    ]]

            df_intraday = db_trades_all[db_trades_all["time"] >= tr_sd_ts].copy()
            df_intraday = df_intraday[[
                "time", "account", "symbol", "side",
                "booking_category", "booking_type",
                "price", "quantity", "quantity_signed", "multiplier"
            ]]

            if not df_open.empty:
                df_trades = pd.concat([df_open, df_intraday], ignore_index=True)
            else:
                df_trades = df_intraday.copy()

        df_trades = df_trades.sort_values("time").reset_index(drop=True)

        # --------------------------------------------------
        # 4️⃣ Fetch prices for run window
        # --------------------------------------------------

        syms_to_price = df_trades["symbol"].unique().tolist()

        if syms_to_price:
            print(f'\t\t\t Fetching Prices between {tr_sd} and {tr_ed}')
            prx = pnl_sup.get_prices_eod(syms=syms_to_price, 
                                         startdate=tr_sd, 
                                         enddate=tr_ed, 
                                         fill_na=False)
            
            print(f'\t\t\t\t Length of Fetched Price: {len(prx)}')
        else:
            prx = pd.DataFrame()

        # Store in cache
        CF.cache_pnl_trade = df_trades.copy()
        CF.cache_pnl_prices = prx.copy()

    else:
        if not isinstance(CF.cache_pnl_trade, pd.DataFrame):
            raise ValueError(
                "CF.cache_pnl_trade is not populated. Run with refetch_cache=1 first."
            )
        if verbose:
            print(f"\t\t\t Taking Trades from Cache for {acct}")
        df_trades = CF.cache_pnl_trade
        prx = CF.cache_pnl_prices

    out_dict["df_trades"] = df_trades
    out_dict["prx"] = prx

    return out_dict




def pnl_realised_ca(df_orig, adj_ca, verbose):
    """
    Calculates PNL Data based on FiFo method.
    @param df_orig:
        DataFrame needs to be passed as:
        time       - can be either integer index, date, datetime or timestamp object
        symbol     - consistent symbol. Must be a string
        side       - Either "B" for Buy or "S" for Sell
        price      - symbol price as float
        quantity   - traded quantity as absolut value as column "side" indicates direction
        multiplier - contract size

    @param df_pos:
        DataFrame needs to be passed as:
        time       - can be either integer index, date, datetime or timestamp object
        symbol     - consistent symbol. Must be a string
        side       - Either "B" for Buy or "S" for Sell
        price      - symbol price as float
        quantity   - traded quantity as absolut value as column "side" indicates direction

    @param adj_ca: Adjusting for Corporate Actions
    @param verbose: prints Trade, Warning and Error Messages

    return: Multiple dictionary outputs
    """
    # Copy Data
    df = df_orig.copy()
    df = df.sort_values(by='time')
    df['split_ratio'] = np.nan

    # Define Macro Output
    out_dict = dict()

    trade_dict = dict()
    split_dict = dict()
    for k in df.symbol.unique():
        trade_dict[k] = pd.DataFrame(columns=df.columns)
        # Create Split Dictionary for later use in fifo_engine
        split_dict[k] = pd.DataFrame(columns=df.columns)

    pnl_dict = dict()
    for k in df.symbol.unique():
        pnl_dict[k] = pd.DataFrame(columns=['symbol'] + ['rpnl'])



    # Series Outputs
    #pos_series = pd.DataFrame(columns=['symbol', 'instrument_type', 'booking_type'] + ['quantity'])
    pos_series = pd.DataFrame(columns=['symbol', 'booking_type'] + ['quantity'])
    pnl_series = pd.DataFrame(columns=['symbol', 'rpnl'])


    for i in list(df.index):
        try:
            # Assign Macro Value
            tmp_trade = df.loc[[i]]
            # Assign Values
            time = df.loc[i]['time']
            symbol = df.loc[i]['symbol']
            side = df.loc[i]['side']
            #instrument_type = df.loc[i]['instrument_type']
            price = df.loc[i]['price']
            # Adding Information for Corporate Actions
            if adj_ca:
                booking_category = df.loc[i]['booking_category']
                booking_type = df.loc[i]['booking_type']

                # Collecting last position for Split Ratio Calculation
                last_pos = 0
            else:
                booking_category = ''
                booking_type = ''
                last_pos = 0


            quantity = df.loc[i]['quantity']
            multiplier = df.loc[i]['multiplier']

            # Write Positions:
            pos_series.loc[time, 'symbol'] = symbol
            side_mult = -1 if side == 'S' else 1
            pos_series.loc[time, 'quantity'] = side_mult * tmp_trade.quantity.iloc[0]
            #pos_series.loc[time, 'instrument_type'] = instrument_type
            pos_series.loc[time, 'booking_type'] = booking_type


            # Check for  Corporate Actions without a Price
            pass_pnl_price = 0
            if booking_category == 'CORPORATE_ACTION' and adj_ca and np.isnan(df.loc[i]['price']):
                if trade_dict[symbol].empty is False:
                    tmp_trade['price'] = price = trade_dict[symbol].iloc[-1]['price']
                else:
                    if df[(df.symbol == symbol)].loc[i:].dropna(subset='price').empty is False:
                        tmp_trade['price'] = price = df[(df.symbol == symbol)].loc[i:].iloc[1]['price']
                    else:
                        # Trade Data does not contain any trades with prices that can be used
                        pass_pnl_price = 1
                        pass

            # Calc for later use
            # Split Ratio as posted in DWH = Split Trade Quantity/Position + 1
            total_qty_trades = df[(df.symbol == symbol)
                                  & (df['time'] < time)].apply(lambda row: -1*row['quantity'] if row['side'] == 'S' else row['quantity'], axis=1).sum()

            # Check Pos Series
            tmp_trades_res = trade_dict[symbol].copy()
            trades_res_qty = tmp_trades_res.apply(lambda row: -1*row['quantity'] if row['side'] == 'S' else row['quantity'], axis=1).sum()
            if verbose:
                if np.round(trades_res_qty, 3) != np.round(total_qty_trades, 3):
                    print("\t\tCheck DDate %s: total_qty_trades = %s,  trades_res_qty = %s"%(time, np.round(total_qty_trades, 3), np.round(trades_res_qty, 3)))


            false_reverse_split = 0
            if booking_type in ['SPLIT', 'REVERSE_SPLIT', 'STOCK_SPLIT', 'STOCK_REVERSE_SPLIT'] and np.abs(tmp_trade['quantity'].iloc[0]-total_qty_trades) < 1e-10:
                # REVERSE Splits with quantity = total position qty are used for so-called "consolidations" mainly present in WisdomTree ETFs
                # see IE00B7XD2195 or IE00B76BRD76
                # A trade is inserted that nets with a Sell the present position. Then a second trade with the actual split.
                # In this code the first reverse split trade blanks trade_dict. Therefore, the second reverse split trade is skipped because of
                # if trade_dict[symbol].empty is False:
                print("\t\t %s: Found False Split"%(symbol))
                if pass_pnl_price == 0:
                    try:
                        tmp_trade['price'] = trade_dict[symbol].iloc[-1]['price']
                    except:
                        pass
                false_reverse_split = 1


            if booking_type in ['SPLIT', 'REVERSE_SPLIT', 'STOCK_SPLIT', 'STOCK_REVERSE_SPLIT'] and adj_ca and false_reverse_split == 0:

                if trade_dict[symbol].empty is False and trade_dict[symbol].empty is False:
                    split_ratio = 0
                    if booking_type in ['SPLIT', 'STOCK_SPLIT']:
                        split_ratio = np.round(np.abs(quantity / (last_pos + total_qty_trades)), 0) + 1

                    elif booking_type in ['REVERSE_SPLIT', 'STOCK_REVERSE_SPLIT']:
                        split_ratio = np.round(np.abs((last_pos + total_qty_trades)/quantity), 0) + 1

                    # Check if Split Ratio is a False Positive as we use SPLIT and REVERSE_SPLIT booking_types also for other operations, which do not affect
                    # shares and the price:
                    last_price_pool = trade_dict[symbol].price.iloc[-1]
                    if df[(df.symbol == symbol)].loc[i:].dropna(subset='price').empty:
                        next_price_trade = trade_dict[symbol].iloc[-1]['price'] / split_ratio
                    else:
                        next_price_trade = df[(df.symbol == symbol)].loc[i:].dropna(subset='price').iloc[0].price

                    if np.abs(1-last_price_pool / next_price_trade) > 0.3:
                        # Adjust price
                        if booking_type in ['SPLIT', 'STOCK_SPLIT']:
                            trade_dict[symbol].price /= split_ratio
                        elif booking_type in ['REVERSE_SPLIT', 'STOCK_REVERSE_SPLIT']:
                            trade_dict[symbol].price *= split_ratio

                        print("\t\t %s: Found %s with a Split Ratio of %s" % (symbol, booking_type, split_ratio))
                        # Assign Split Ratio to Output
                        tmp_trade['split_ratio'] = split_ratio
                        split_dict[symbol] = pd.concat([split_dict[symbol], tmp_trade], axis=0)

                    # As splits and reverse splits are booked as trades without prices, but correction trades come in with a price the "split trade" needs to
                    # be added to the pool of trades with a minimal impact. Therefore, using the last trade price prior to the split in order to not
                    # produce high pnl figures:
                    tmp_trade['price'] = trade_dict[symbol].iloc[-1]['price']

                elif df[(df.symbol == symbol)].loc[i:].dropna(subset='price').empty is True:
                    try:
                        tmp_trade['price'] = df[(df.symbol == symbol)].loc[:i].iloc[-1]['price']
                    except:
                        pass
                else:
                    tmp_trade['price'] = df[(df.symbol == symbol)].loc[i:].iloc[1]['price']

                # Rename booking category in order to avoid double counting the split
                tmp_trade['booking_type'] = 'TRADING_' + tmp_trade['booking_type']



            if trade_dict[symbol].empty or trade_dict[symbol].iloc[0]['side'] == side:
                # Fill Trade DF with first Symbol Trade or append trades in same direction
                trade_dict[symbol] = pd.concat([trade_dict[symbol], tmp_trade], axis=0)

            elif trade_dict[symbol].iloc[0]['side'] != side:
                qty_residual = trade_dict[symbol].iloc[0].quantity - quantity

                # Round Quantity Residual
                qty_residual = np.round(qty_residual, 10)

                if verbose:
                    print('\n **** Qty_Residual: %s'%qty_residual)

                if qty_residual > 0:
                    if verbose:
                        print('\n ****Qty_Residual > 0')

                    # pnl_tmp = 0
                    # Sum PnL
                    is_short_sell = -1 if trade_dict[symbol].iloc[0].side == 'S' else 1

                    if verbose:
                        print("\n \t\t Price %s, Price[0]: %s, Quantity: %s" % (price, trade_dict[symbol].iloc[0].price, quantity))
                    pnl_tmp = (price - trade_dict[symbol].iloc[0].price) * quantity * multiplier * is_short_sell

                    if verbose:
                        print("\t\t PnL: %s" % pnl_tmp)


                    trade_dict[symbol].loc[trade_dict[symbol].index[0], 'quantity'] = qty_residual
                    pnl_dict[symbol].loc[time, 'symbol'] = symbol

                    if np.isnan(pnl_dict[symbol].loc[time,'rpnl']):
                        pnl_dict[symbol].loc[time, 'rpnl'] = 0
                    pnl_dict[symbol].loc[time, 'rpnl'] += pnl_tmp

                elif qty_residual == 0:
                    if verbose:
                        print('\n **** Qty_Residual == 0')
                    pnl_tmp = 0
                    # Sum PnL
                    is_short_sell = -1 if trade_dict[symbol].iloc[0].side == 'S' else 1

                    if verbose:
                        print("\n \t\t Price %s, Price[0]: %s, Quantity: %s" % (price, trade_dict[symbol].iloc[0].price, quantity))
                    pnl_tmp += (price - trade_dict[symbol].iloc[0].price) * quantity * multiplier * is_short_sell

                    if verbose:
                        print("\t\t PnL: %s" % pnl_tmp)
                    if verbose:
                        print("\t\t %s - Position on %s closed: PnL = %s" % (time,symbol,pnl_tmp))


                    trade_dict[symbol].loc[trade_dict[symbol].index[0], 'quantity'] = qty_residual
                    pnl_dict[symbol].loc[time, 'symbol'] = symbol

                    if np.isnan(pnl_dict[symbol].loc[time, 'rpnl']):
                        pnl_dict[symbol].loc[time, 'rpnl'] = 0
                    pnl_dict[symbol].loc[time, 'rpnl'] += pnl_tmp

                    if len(trade_dict[symbol]) == 1:
                        trade_dict[symbol] = pd.DataFrame(columns=df.columns)
                    else:
                        trade_dict[symbol] = trade_dict[symbol][1:]

                elif qty_residual < 0:
                    # looping through trades until qty_residual ==0 OR len(trades) == 0
                    if verbose:
                        print('\n \t\t Qty_Residual < 0')

                    # Initialize with setting values to zero
                    pnl_tmp = 0
                    skip_j = 0

                    for j in list(trade_dict[symbol].index):

                        if skip_j == 1:
                            pass

                        if quantity != 0:
                            qty_tmp = trade_dict[symbol].loc[j].quantity - quantity
                            if qty_tmp == 0:
                                is_short_sell = -1 if trade_dict[symbol].iloc[0].side == 'S' else 1
                                pnl_tmp += (price - trade_dict[symbol].iloc[
                                    0].price) * quantity * multiplier * is_short_sell
                                quantity -= trade_dict[symbol].loc[j].quantity
                                trade_dict[symbol] = trade_dict[symbol][1:]
                                skip_j = 1
                                if verbose:
                                    print("\t\t %s - Position on %s closed: PnL = %s" %(time, symbol, pnl_tmp))

                            elif qty_tmp < 0:
                                is_short_sell = -1 if trade_dict[symbol].loc[j].side == 'S' else 1
                                pnl_tmp += (price - trade_dict[symbol].loc[j].price) * trade_dict[symbol].loc[
                                    j].quantity * multiplier * is_short_sell
                                quantity -= trade_dict[symbol].loc[j].quantity
                                trade_dict[symbol] = trade_dict[symbol][1:]
                                if trade_dict[symbol].empty and quantity > 0:
                                    trade_dict[symbol] = pd.concat([trade_dict[symbol], tmp_trade], axis=0)
                                    trade_dict[symbol].loc[trade_dict[symbol].index[0], 'quantity'] = quantity

                                    if verbose:
                                        print(trade_dict[symbol])

                            elif qty_tmp > 0:
                                trade_dict[symbol]['quantity'].loc[j] = qty_tmp
                                is_short_sell = -1 if trade_dict[symbol].loc[j].side == 'S' else 1
                                pnl_tmp += (price - trade_dict[symbol].loc[j].price) * quantity * multiplier * is_short_sell
                                quantity = 0
                                skip_j = 1

                    pnl_dict[symbol].loc[time, 'symbol'] = symbol
                    if np.isnan(pnl_dict[symbol].loc[time, 'rpnl']):
                        pnl_dict[symbol].loc[time, 'rpnl'] = 0

                    pnl_dict[symbol].loc[time, 'rpnl'] += pnl_tmp
        except:
            print(traceback.format_exc())
            #raise Exception("\t\t ERROR on symbol: %s"%symbol)

    # Create and Format pnl Series:
    for k in pnl_dict.keys():
        pnl_series = pd.concat([pnl_series, pnl_dict[k]], axis=0, sort=True)

    pnl_series['pnl_cumulative'] = pnl_series['rpnl'].cumsum()

    # Assign single Object to Macro Output
    out_dict['trade_dict'] = trade_dict
    out_dict['pnl_dict'] = pnl_dict
    out_dict['split_dict'] = split_dict
    out_dict['pos_series'] = pos_series
    out_dict['pnl_series'] = pnl_series

    return out_dict


def pnl_realised_polars(df_trades):
    """
    Calculate FIFO PnL using polars, ensuring that each residual short trade 
    retains its specific price instead of averaging.

    Parameters:
        df_trades (pd.DataFrame): Input data with columns:
            - 'symbol': Asset identifier.
            - 'time': Trade date.
            - 'price': Trade execution price.
            - 'quantity': Positive for buys, negative for sells.

    Returns:
        tuple: Three DataFrames containing:
            - PnL results per trade
            - Remaining FIFO queue
            - Position tracking
    """
    
    # Convert to Polars DataFrame and sort by symbol and date
    df = pl.from_pandas(df_trades).sort(by=["symbol", "time"])
    
    # Mapping positive and negative signs for trade direction
    df = df.with_columns(pl.when(pl.col("side")=="B").then(pl.col("quantity")).otherwise(-1 * pl.col("quantity")).alias("quantity"))

    # Group by symbol and process each group
    results = []
    cache = []
    pos = []

    for group in df.group_by("symbol"):
        trades_orig = group[1].sort("time")
        trades = trades_orig.filter(pl.col("price").is_not_null())

        # Prepare FIFO queue for buy trades
        fifo_queue = []
        fifo_pnl = []
        fifo_pos = []
        short_queue = []  # Stores individual short trades separately

        for row in trades.iter_rows(named=True):
            trade_quantity = row["quantity"]
            trade_price = row["price"]
            realized_pnl = 0.0
            match_quantity = 0.0

            # Buy trade: Process FIFO queue and reduce short position
            if trade_quantity > 0:
                # If there are short positions, they should be covered first
                while trade_quantity > 0 and short_queue:
                    short_trade = short_queue[0]
                    match_quantity = min(trade_quantity, short_trade["quantity"])
                    realized_pnl += match_quantity * (short_trade["price"] - trade_price)

                    # Adjust quantities
                    short_trade["quantity"] -= match_quantity
                    trade_quantity -= match_quantity

                    # Remove the short trade if fully offset
                    if short_trade["quantity"] == 0:
                        short_queue.pop(0)

                fifo_pos.append(
                    {   "time": row["time"],
                        "symbol": row["symbol"],
                        "trade_price": trade_price,
                        "trade_quantity": trade_quantity,
                        "short_position": sum(t["quantity"] for t in short_queue),
                        "match_quantity": match_quantity,
                    }
                )

                # If any buy quantity remains after covering shorts, store in FIFO queue
                if trade_quantity > 0:
                    fifo_queue.append(
                        {
                        "time": row["time"],
                        "symbol": row["symbol"],
                        "quantity": trade_quantity,
                        "price": trade_price
                        })

            # Sell trade: Process FIFO queue or add to short queue
            elif trade_quantity < 0:
                sell_quantity = -trade_quantity

                # Match against FIFO queue first
                while sell_quantity > 0 and fifo_queue:
                    buy_trade = fifo_queue[0]
                    match_quantity = min(sell_quantity, buy_trade["quantity"])
                    realized_pnl += match_quantity * (trade_price - buy_trade["price"])

                    # Adjust quantities
                    buy_trade["quantity"] -= match_quantity
                    sell_quantity -= match_quantity

                    # Remove the buy trade if fully used
                    if buy_trade["quantity"] == 0:
                        fifo_queue.pop(0)

                # If there is remaining unmatched sell quantity, store it **separately** in short queue
                if sell_quantity > 0:
                    short_queue.append(
                        {
                        "time": row["time"], 
                        "symbol": row["symbol"],
                        "quantity": sell_quantity,
                        "price": trade_price
                        })

                fifo_pos.append(
                    {"time": row["time"],
                     "symbol": row["symbol"],
                     "trade_price": trade_price,
                     "trade_quantity": trade_quantity,
                     "short_position": sum(t["quantity"] for t in short_queue),
                     "match_quantity": match_quantity,
                    }
                )

            # Store the realized PnL for this trade
            fifo_pnl.append(
                {"time": row["time"],
                 "symbol": row["symbol"],
                 "pnl": realized_pnl,
                 "matchedqty": match_quantity,
                }
            )

        # At the end, add any remaining short trades to the FIFO queue
        # Multiply Short Queue Quantities by -1:
        if len(short_queue)>0:
            short_queue = [{**pos, 'quantity': -1 * pos['quantity']} for pos in short_queue]
        
        cache.extend(short_queue)
        results.extend(fifo_pnl)
        cache.extend(fifo_queue)
        pos.extend(fifo_pos)

        # Convert results back to a Pandas DataFrame
    out_pnl = pd.DataFrame(results)
    if out_pnl.empty:
        out_pnl = pd.DataFrame(columns=["time","symbol","pnl","matchedqty"])

    out_cache = pd.DataFrame(cache)
    out_pos = pd.DataFrame(pos)

    # Format Cache Output (safe for empty cache)
    if out_cache.empty:
        out_cache = pd.DataFrame(
            columns=["time","symbol","side","booking_category","booking_type","price","quantity","multiplier"]
        )
    else:
        out_cache["side"] = np.where(out_cache["quantity"] < 0, "S", "B")
        out_cache["booking_type"] = "SYNTHETIC_CLOSE"
        out_cache["quantity"] = out_cache["quantity"].abs()
        out_cache["booking_category"] = "SYNTHETIC_CLOSE"
        out_cache["multiplier"] = 1
        out_cache = out_cache[["time","symbol","side","booking_category","booking_type","price","quantity","multiplier"]]

    return out_pnl, out_cache, out_pos



def pnl_unrealised_liq(df_trades, prx, **kwargs):
    """
    Unrealised PnL via synthetic EOD liquidation.
    df_trades : residual open FIFO inventory (from realised step)
    prx       : DataFrame with index=symbol, column 'price' (EOD price)
    """

    # nothing open → no unrealised pnl
    if df_trades.empty:
        return pd.DataFrame(columns=["ddate", "symbol", "upnl"])

    # -------------------------------------------------------
    # 1) build synthetic EOD CLOSE trades
    # -------------------------------------------------------
    df_close = df_trades.copy()

    eod_time = _datetime(
        df_trades["time"].iloc[-1].year,
        df_trades["time"].iloc[-1].month,
        df_trades["time"].iloc[-1].day,
        23, 59, 59
    )

    df_close["time"] = eod_time
    df_close["side"] = df_close["side"].map({"B": "S", "S": "B"})
    df_close["price"] = df_close["symbol"].map(prx["price"].to_dict())

    # drop symbols without EOD price
    df_close = df_close.dropna(subset=["price"])
    if df_close.empty:
        return pd.DataFrame(columns=["ddate", "symbol", "upnl"])

    # -------------------------------------------------------
    # 2) FIFO liquidation = realised PnL = unrealised PnL
    # -------------------------------------------------------
    fifo_input = (
        pd.concat([df_trades, df_close], axis=0)
          .sort_values("time")
          .reset_index(drop=True)
    )

    pnl_polars, _, _ = pnl_realised_polars(
        fifo_input[["symbol", "time", "price", "quantity", "side"]]
    )

    # Ensure pandas datetime dtype for reliable comparison
    pnl_polars["time"] = pd.to_datetime(pnl_polars["time"])
    eod_time = pd.to_datetime(eod_time)

    upnl = (
        pnl_polars.loc[pnl_polars["time"] == eod_time, ["time", "symbol", "pnl"]]
        .rename(columns={"time": "ddate", "pnl": "upnl"})
        .groupby(["ddate", "symbol"], as_index=False)["upnl"].sum()
    )

    return upnl





def pnl_fifo_engine(df_trades, prx=None, enddate=None, adj_ca=1, verbose=False, **kwargs):
    """
    PnL FiFo Engine for Trades in the Fractional Trading Book. The function calculates realised and unrealised PnL.
    Returns:
        out_pos, out_cache(residual lots), out_trade_pnl(per-trade rpnl), df_trades_enriched(with synthetic CLOSE rows)
    """
    global tmp_trades_residual

    start_time = _datetime.now()

    if adj_ca == 1 and verbose:
        print('\n Adjusting for Corporate Actions ***************************************')

    # --- Normalize input ---
    df_trades = df_trades[['time','symbol','side','booking_category','booking_type','price','quantity','multiplier']].copy()
    df_trades = df_trades.reset_index(drop=True)

    if verbose:
        print('\n Initialising PnL Calculation ***************************************')

    out_pos = pd.DataFrame()
    out_trade_pnl = pd.DataFrame()

    # --- Split CA vs non-CA ---
    syms_ca = df_trades[df_trades.booking_category == 'CORPORATE_ACTION'].symbol.unique()
    df_trades_ca = df_trades[df_trades.symbol.isin(syms_ca)]
    df_trades_polars = df_trades[~df_trades.symbol.isin(syms_ca)].copy()

    df_trades_polars["source"] = np.where(
        df_trades_polars["booking_type"].isin(["SYNTHETIC_OPEN", "SYNTHETIC_CLOSE"]),
        df_trades_polars["booking_type"],
        "REAL"
    )
    df_trades_polars = df_trades_polars[["symbol","time","price","quantity","side","source"]]

    # --- Realised PnL (polars + CA) ---
    pnl_series_tmp = pd.DataFrame()
    tmp_trades_residual = pd.DataFrame()
    split_series_tmp = dict()

    if not df_trades_polars.empty:
        if verbose:
            print('\n\t\t Calculating Polars PnL ***************************************')

        tmp_pnl_polars, tmp_cache_polars, _ = pnl_realised_polars(df_trades_polars)

        tmp_pnl_polars = tmp_pnl_polars.set_index("time")

        tmp_pnl_polars = tmp_pnl_polars[["symbol","pnl","matchedqty"]]
        tmp_pnl_polars.columns = ["symbol","rpnl","matchedqty"]


        pnl_series_tmp = pd.concat([pnl_series_tmp, tmp_pnl_polars], axis=0)
        tmp_trades_residual = pd.concat([tmp_trades_residual, tmp_cache_polars], axis=0)

    if not df_trades_ca.empty:
        if verbose:
            print('\n\t\t Calculating Corporate Action PnL ***************************************')

        rpnl_out = pnl_realised_ca(df_trades_ca, adj_ca, verbose)

        pnl_series_ca = rpnl_out['pnl_series'][['symbol','rpnl']]
        split_series_tmp = rpnl_out['split_dict']

        pnl_series_tmp = pd.concat([pnl_series_tmp, pnl_series_ca], axis=0)

        tmp_trades_residual_ca = pd.concat(rpnl_out['trade_dict'].values(), ignore_index=True)
        tmp_trades_residual = pd.concat([tmp_trades_residual, tmp_trades_residual_ca], axis=0)

    # --- Prices at EOD(enddate) for symbols in residual ---
    if prx is None or enddate is None:
        raise ValueError("pnl_fifo_engine requires prx and enddate")

    if tmp_trades_residual.empty:
        prx_syms = pd.DataFrame(columns=["price"])
    else:
        syms_tmp = tmp_trades_residual.symbol.unique()
        prx_tmp = prx[[k for k in syms_tmp if k in prx.columns]]

        prx_tmp_missing = pd.DataFrame(index=prx_tmp.index, columns=[k for k in syms_tmp if k not in prx.columns])
        prx_tmp = pd.concat([prx_tmp, prx_tmp_missing], axis=1).T.sort_index().T

        # Adjust prices for splits (if any)
        if len(split_series_tmp) > 0:
            for sym in split_series_tmp.keys():
                if split_series_tmp[sym].empty:
                    continue
                if prx_tmp.index[-1] == split_series_tmp[sym].iloc[-1]['time'].date():
                    prx_tmp.iloc[-1][sym] = prx_tmp.iloc[-1][sym] / split_series_tmp[sym].iloc[-1]['split_ratio']

        prx_syms = prx_tmp.loc[[enddate]].T
        prx_syms.columns = ['price']
        prx_syms.index.name = 'symbol'
        prx_syms = prx_syms.reset_index().groupby('symbol').mean()

    # =============================================================================
    # Unrealised PnL via liquidation
    # =============================================================================
    if not tmp_trades_residual.empty:
        tmp_upnl = pnl_unrealised_liq(tmp_trades_residual, prx_syms)
    else:
        tmp_upnl = pd.DataFrame(columns=["ddate","symbol","upnl"])

    # =============================================================================
    # VISIBILITY: add SYNTHETIC_CLOSE lines as NEGATIVE of the net position
    # (OPEN is handled upstream by carry-forward injection)
    # =============================================================================
    df_trades_enriched = df_trades.copy()

    if not tmp_trades_residual.empty:
        # signed net position from residual LOTS (residual are in absolute qty + side)
        signed_qty = np.where(
            tmp_trades_residual["side"].values == "S",
            -1.0 * tmp_trades_residual["quantity"].astype(float).values,
            tmp_trades_residual["quantity"].astype(float).values
        )

        df_net = tmp_trades_residual[["symbol","multiplier"]].copy()
        df_net["signed_qty"] = signed_qty
        df_net = df_net.groupby(["symbol","multiplier"], as_index=False)["signed_qty"].sum()
        df_net = df_net[df_net["signed_qty"].abs() > 1e-12].copy()

        if not df_net.empty:
            eod_price_map = prx_syms["price"].to_dict()
            df_net["price"] = df_net["symbol"].map(eod_price_map)
            df_net = df_net.dropna(subset=["price"])

            if not df_net.empty:
                # CLOSE = -OPEN  (negative of signed net)
                df_close = df_net.copy()
                df_close["signed_close"] = -df_close["signed_qty"]

                df_close["time"] = _datetime(enddate.year, enddate.month, enddate.day, 23, 59, 59)
                df_close["booking_category"] = "TRADING"
                df_close["booking_type"] = "SYNTHETIC_CLOSE"
                df_close["side"] = np.where(df_close["signed_close"] < 0, "S", "B")
                df_close["quantity"] = df_close["signed_close"].abs()

                df_close = df_close[[
                    "time","symbol","side","booking_category",
                    "booking_type","price","quantity","multiplier"
                ]]

                df_trades_enriched = pd.concat([df_trades_enriched, df_close], axis=0, ignore_index=True)

    df_trades_enriched = df_trades_enriched.sort_values("time").reset_index(drop=True)

    # =============================================================================
    # Build rPnL summary + per-trade pnl
    # =============================================================================
    if pnl_series_tmp.empty:
        tmp_rpnl = tmp_upnl.drop(columns=['upnl'], errors='ignore').copy()
        tmp_rpnl['rpnl'] = 0.0
    else:
        tmp_rpnl = pnl_series_tmp[['symbol','rpnl']].groupby('symbol').sum().reset_index()
        out_trade_pnl = pd.concat([out_trade_pnl, pnl_series_tmp], axis=0)

    # Merge uPnL + rPnL
    if tmp_upnl.empty:
        # ensure ddate exists for merge
        tmp_upnl = pd.DataFrame({"symbol": tmp_rpnl["symbol"].values, "ddate": _datetime(enddate.year, enddate.month, enddate.day, 23, 59, 59), "upnl": 0.0})

    tmp_pnl = pd.concat([tmp_upnl.set_index('symbol'), tmp_rpnl.set_index('symbol')], axis=1)
    tmp_pnl['ddate'] = tmp_pnl.ddate.ffill().bfill()
    tmp_pnl['upnl'] = tmp_pnl.upnl.fillna(0.0)
    tmp_pnl['rpnl'] = tmp_pnl.rpnl.fillna(0.0)

    # =============================================================================
    # Position report (EOD quantity = signed net residual)
    # =============================================================================
    if tmp_trades_residual.empty:
        tmp_pos = pd.DataFrame(columns=["quantity"])
        out_pos = pd.DataFrame(columns=["ddate","symbol","price","eod_quantity","rpnl","upnl"])
        out_cache = tmp_trades_residual.copy()
    else:
        tmp_trades_residual_signed = tmp_trades_residual.copy()
        tmp_trades_residual_signed["signed_qty"] = np.where(
            tmp_trades_residual_signed["side"] == "S",
            -1.0 * tmp_trades_residual_signed["quantity"].astype(float),
            tmp_trades_residual_signed["quantity"].astype(float)
        )

        tmp_pos = (
            tmp_trades_residual_signed[["symbol","signed_qty"]]
            .groupby("symbol", as_index=True)
            .sum()
            .rename(columns={"signed_qty": "quantity"})
        )

        tmp_pos = pd.concat([tmp_pos, tmp_pnl], axis=1)
        tmp_pos["quantity"] = tmp_pos["quantity"].fillna(0.0)

        out_pos = pd.concat([tmp_pos, prx_syms], axis=1)

        out_pos = out_pos[out_pos.quantity != 0].copy()
        out_pos = out_pos.reset_index()
        out_pos = out_pos[['ddate','symbol','price','quantity','rpnl','upnl']].rename(columns={"quantity":"eod_quantity"})

        for col in ['price','eod_quantity','rpnl','upnl']:
            out_pos[col] = out_pos[col].fillna(0.0)

        # cache = one aggregated row per ISIN at EOD price, mirroring out_pos
        out_cache = out_pos[['symbol', 'price', 'eod_quantity']].copy()
        out_cache['side'] = np.where(out_cache['eod_quantity'] < 0, 'S', 'B')
        out_cache['quantity'] = out_cache['eod_quantity'].abs()
        out_cache['booking_category'] = 'SYNTHETIC_CLOSE'
        out_cache['booking_type'] = 'SYNTHETIC_CLOSE'
        out_cache['time'] = _datetime(enddate.year, enddate.month, enddate.day, 23, 59, 59)
        out_cache['multiplier'] = 1.0
        out_cache = out_cache[['time', 'symbol', 'side', 'booking_category', 'booking_type', 'price', 'quantity', 'multiplier']]

    if verbose:
        print('TIME: %s' % (_datetime.now() - start_time))

    return out_pos, out_cache, out_trade_pnl, df_trades_enriched