#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import warnings
import numpy as np
import pandas as pd
from datetime import datetime as _datetime, time
import traceback
import polars as pl

# Import Custom Modules
from tools import config as CF
from tools.snowflake_db import db_connection as db
from risk_models import pnl_support as pnl_sup


warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings('ignore')


def initiate_pnl_engine(acct,tr_sd,tr_ed,ca_sd,refetch_cache,save_data,save_daily,data_src,trade_qry,pth,verbose):
    """
    Initiates the PnL Engine for FIFO PnL Calculation.

    @param acct: Account Number, e.g. 9800003301
    @param tr_sd: Start Date for Trades, e.g.  date(2023, 1, 1)
    @param tr_ed: End Date for Trades
    @param ca_sd: Start Date for Cache
    @param refetch_cache: If 1, the cache is refetched from the database
    @param save_data: If True, saves the output to the specified path
    @param save_daily: If True, saves daily PnL and Cache data to Parquet files (for historical rerun purpose only!)
    @param data_src: Data Source, e.g. 'share_bookings' or 'inquisitor
    @param trade_qry: Query for fetching trades, 'old' or 'new'
    @param pth: Path to save the output
    @param verbose: If True, prints information on the console
    @return: Dictionary with DataFrames for Trades, Prices, Positions, Cache and Trade PnL
    """
    # Set Output
    out_dict=dict()

    # Get Cache
    cache_dict=build_pnl_cache(acct,tr_sd,tr_ed,ca_sd,refetch_cache,data_src,trade_qry,verbose)
    df_trades=cache_dict['df_trades']
    df_trades=df_trades.drop('quantity_signed',axis=1)
    prx=cache_dict['prx']
    out_dict['cache_dict']=cache_dict

    # Calc PnL
    # Get Weekdays for trading start and end
    ll_dd=[k.date() for k in list(pd.date_range(tr_sd,tr_ed,freq='D')) if k.weekday()<5]
    ll_dd = [_datetime.combine(d, time(23, 59, 59)) for d in ll_dd]

    out_pos=pd.DataFrame()
    out_cache=pd.DataFrame()
    out_trade_pnl=pd.DataFrame()
    tmp_cache=pd.DataFrame()

    for i in range(0,len(ll_dd)):
        if ll_dd[i].date() not in prx.index:
            pass
        else:
            # Set Prices:
            prx_tmp=prx[:ll_dd[i].date()]

            if i==0:
                tmp_trades=df_trades[df_trades['time']<=ll_dd[i]]
            elif i>0:
                tmp_trades=df_trades[(df_trades['time']>ll_dd[i-1])&(df_trades['time']<=ll_dd[i])]

                if tmp_cache.empty is False:
                    # Append last cache:
                    #tmp_trades=pd.concat([tmp_cache.drop('split_ratio', axis=1),tmp_trades],axis=0)
                    tmp_trades=pd.concat([tmp_cache, tmp_trades],axis=0)
            
            if tmp_trades.empty is False:
                tmp_pos, tmp_cache, tmp_trade_pnl=pnl_fifo_engine(tmp_trades, 
                                                                prx=prx_tmp, 
                                                                enddate=ll_dd[i].date(), adj_ca=1, 
                                                                verbose=verbose)
            
                # Recombine Data:
                out_pos=pd.concat([out_pos,tmp_pos],axis=0)
                out_cache=tmp_cache.copy()
                out_trade_pnl=pd.concat([out_trade_pnl,tmp_trade_pnl],axis=0)

                # Save Daily Data if requested
                if save_daily==1 and save_data==1:
                    print(f'\t Saving Daily PnL Data for {ll_dd[i].date()} to Parquet')
                    df_pos_daily = tmp_pos.copy()
                    df_pos_daily['data_src_primary'] = data_src
                    fname_pnl_daily = pnl_sup.pnl2parquet(acct=acct, report_date=ll_dd[i].date(),
                                                          df_orig=df_pos_daily, pth=pth, pnl=True)

                    print(f'\t Saving Daily Cache Data for {ll_dd[i].date()} to Parquet')
                    df_cache_daily = tmp_cache.copy()
                    df_cache_daily['data_src_primary'] = data_src
                    fname_cache_daily = pnl_sup.pnl2parquet(acct=acct, report_date=ll_dd[i].date(),
                                                            df_orig=df_cache_daily, pth=pth, cache=True)
                    

            else:
                tmp_cache=pd.DataFrame()


    #Clean Up
    out_pos['upnl']=out_pos['upnl'].replace(-np.inf,0,regex=True)
    out_pos['upnl']=out_pos['upnl'].replace(np.inf,0,regex=True)

    #Add Outputs to dictionaries
    out_dict['out_pos']=out_pos
    out_dict['out_cache']=out_cache
    out_dict['out_trade_pnl']=out_trade_pnl
    

    if save_daily==0 and save_data==1:
        # Saving Files to Folder:
        print('\t Saving PnL Data to Parquet')
        df_pos=out_dict['out_pos'].copy()
        df_pos['data_src_primary']=data_src
        fname_pnl=pnl_sup.pnl2parquet(acct=acct,report_date=tr_ed,df_orig=df_pos,pth=pth,pnl=True)
        out_dict['fname_pnl']=fname_pnl

        print('\t Saving Cache Data to Parquet')
        df_cache=out_dict['out_cache'].copy()
        df_cache['data_src_primary']=data_src
        fname_cache=pnl_sup.pnl2parquet(acct=acct,report_date=tr_ed,df_orig=df_cache,pth=pth,cache=True)
        out_dict['fname_cache']=fname_cache


    return out_dict
    

def build_pnl_cache(acct,tr_sd,tr_ed,ca_sd,refetch_cache,data_src,trade_qry,verbose):
    """
    Builds the PnL Cache for Trades and Prices.
    @param acct: Account Number
    @param tr_sd: Start Date for Trades
    @param tr_ed: End Date for Trades
    @param ca_sd: Start Date for Cache
    @param refetch_cache: If 1, the cache is refetched from the database
    @param verbose: If True, prints information on the console
    @return: Dictionary with DataFrames for Trades and Prices
    """
    # Setting Output
    out_dict=dict()

    if verbose:
        print('Building Cache for PnL on account %s ***************'%acct)
        print('\t\t Fetching Trades')


    if refetch_cache==1:
        
        if trade_qry == 'old':
            print("\t\t\t Refetching Trades for %s"%acct)
            query_eis=True if acct==9800003301 else False
            db_trades=pnl_sup.get_trades_pnl(account=acct,startdate=tr_sd,enddate=tr_ed,query_eis=query_eis)
            db_trades=db_trades[['time','account','symbol', 'side',
                                'booking_category','booking_type','price',
                                'quantity','quantity_signed','multiplier']]
        elif trade_qry == 'new':
            print("\t\t\t Refetching Trades for %s with new query logic on src: %s"%(acct,data_src))
            db_trades=pnl_sup.get_trades_pnl_new(account=acct,startdate=tr_sd,enddate=tr_ed,data_src=data_src)
            
        if tr_sd != ca_sd:
            print('\t\t\t Fetching Trade Cache')
            qry_cache='''
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

            
            df_cache=db.run_query(query=qry_cache%(acct,db.sqldate(ca_sd),data_src))
            # Check Length of Cache
            print('\t\t\t\t Length of Fetched Cache: %s'%len(df_cache))

            df_cache['quantity_signed']=np.where(df_cache['side']=='S',-1 * df_cache['quantity'],df_cache['quantity'])
            df_cache=df_cache[['time','account', 'symbol', 'side',
                            'booking_category','booking_type','price',
                            'quantity','quantity_signed','multiplier']]
            df_cache=df_cache.sort_values(by='time')
            df_cache=df_cache[df_cache.symbol!='US33817P3064']

            # Concatenating Cache and Trades
            df_trades=pd.concat([df_cache,db_trades],axis=0)
        else:
            df_trades=db_trades

        # Exclude problematic ISINs
        df_trades=df_trades[~df_trades.symbol.isin(['US33817P3064','NL0012047823','US03815U6073'])]

        # Store Cache
        CF.cache_pnl_trade=df_trades.copy()

    else:
        print("\t\t\t Taking Trades from Cache for %s"%acct)
        df_trades=CF.cache_pnl_trade
    
    out_dict['df_trades']=df_trades.sort_values(by='time')

    # Getting EOD Prices
    print("\t\t\t Fetching Prices for %s"%acct)
    prx=pnl_sup.get_prices_eod(syms=df_trades.symbol.unique(),startdate=tr_sd, enddate=tr_ed,fill_na=False)

    # Store Cache
    CF.cache_pnl_prices=prx.copy()


    if len(df_trades[df_trades.price.isnull()])>0:
        print("\t \t\t Warning: Trades contain NaN Prices. Filling with last price.")

        # Setting up trades with no prices
        df_no_prx=df_trades[df_trades.price.isnull()]
        df_no_prx['ddate']=df_no_prx['time'].apply(lambda x: x.date())

        # Fitlering Prices to those symbols
        prx_syms_no=prx[[k for k in df_no_prx.symbol.unique() if k in prx.columns]]
        prx_melt=pd.melt(prx_syms_no.reset_index(),id_vars=['ddate'],value_vars=prx_syms_no.columns)
        prx_melt.columns=['ddate','symbol','price_new']
        df_no_prx=df_no_prx.set_index(['ddate','symbol']).join(prx_melt.set_index(['ddate','symbol'])).reset_index()
        # Assigning price
        df_no_prx['price']=df_no_prx['price_new']
        # Assigning residuals
        df_no_prx.loc[df_no_prx.price.isnull(),'price']=1
        # Reformating and Reappending trades
        df_trades_new=pd.concat([df_trades[~df_trades.price.isnull()], df_no_prx[df_trades.columns]], axis=0)
        df_trades_new=df_trades_new.sort_values(by='time')

        # Resetting the Cache:
        CF.cache_pnl_trade=df_trades_new
        out_dict['df_trades']=df_trades_new


    out_dict['prx']=prx

    print('\t\t\t Analytices on Trades Data:\n')
    print('\t\t\t\t Number of Trades: %s'%len(df_trades))
    print('\t\t\t\t Number of Symbols: %s'%len(df_trades.symbol.unique()))
    print('\t\t\t\t Number of Symbols with CAs: %s'%len(df_trades[df_trades.booking_category=='CORPORATE_ACTION'].symbol.unique()))
    print('\t\t\t\t Number of Trades with CAs: %s'%len(df_trades[df_trades.booking_category=='CORPORATE_ACTION']))


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
        trades_orig = group[1]
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
                 "matched_quantity": match_quantity,
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
    out_cache = pd.DataFrame(cache)
    out_pos = pd.DataFrame(pos)

    # Format Cache Output
    out_cache['side']=np.where(out_cache['quantity'] < 0, 'S', 'B')
    out_cache['booking_type']=np.where(out_cache['quantity'] < 0, 'SELL', 'BUY')
    out_cache['quantity']=out_cache['quantity'].abs()
    out_cache['booking_category']='TRADING'
    out_cache['multiplier']=1
    out_cache=out_cache[['time','symbol','side','booking_category','booking_type','price','quantity','multiplier']]

    return out_pnl, out_cache, out_pos


def pnl_unrealised(tmp_trades_residual, enddate, prx_syms, **kwargs):
    """
    Calculates PNL Data based on FiFo method.
    @param df_trades: residual trades of pnl_realised(): trade_dict as DataFrame
    @param prx: Dataframe with columns: ISINs, index.shape (1,0)
    @param verbose: True or False
    @return: dataframe
    """

    # Create Closing Trades for Unrealised PnL
    df_close = tmp_trades_residual.copy()
    # Add Time
    if 'eod' == kwargs['cut_off']:
        # Setting closing Time here to 23:30, simply to avoid that a last trade came in at 23:00 and gets
        # mixed in with the closing
        df_close['ddate'] = _datetime(enddate.year,enddate.month,enddate.day,23, 59, 59, 0)

    # Add Closing Prices
    prx_eod_dict = dict(zip(prx_syms.index, prx_syms.price))
    # Assign Prices
    df_close['price_eod'] = df_close.symbol.map(prx_eod_dict)
    df_close = df_close.dropna(subset='price')
    # Assign direction to quantity
    # df_close['quantity_eod'] = df_close.apply(lambda row: -1 * row['quantity'] if row['side'] == 'S' else row['quantity'],axis=1)
    df_close['quantity_eod'] = df_close['quantity']
    df_close['upnl'] = (df_close['price_eod'] - df_close['price']) * df_close['quantity_eod']
    df_close['upnl'] = df_close['upnl'].astype(float)
    # Concat Trades
    out_upnl = df_close[['ddate', 'symbol', 'upnl']]


    return out_upnl



def pnl_unrealised_liq(df_trades, prx, verbose=True, **kwargs):
    """
    Calculates PNL Data based on FiFo method.
    @param df_trades: residual trades of pnl_realised(): trade_dict as DataFrame
    @param prx: Dataframe with columns: ISINs, index.shape (1,0)
    @param verbose: True or False
    @return: dataframe
    """


    # Create Closing Trades for Unrealised PnL
    df_close = df_trades.copy()
    # Add Time
    if 'eod' == kwargs['cut_off']:
        # Setting closing Time here to 23:30, simply to avoid that a last trade came in at 23:00 and gets
        # mixed in with the closing
        df_close['time'] = _datetime(df_trades['time'].iloc[-1].year,
                                     df_trades['time'].iloc[-1].month,
                                     df_trades['time'].iloc[-1].day,
                                     23, 30, 0, 0)

    df_close['side'] = df_close.side.map({'B': 'S', 'S': 'B'})
    # Add Closing Prices
    prx_syms = prx[prx.symbol.isin(df_trades.symbol.unique())]
    df_close['price'] = df_close.symbol.map(dict(zip(prx_syms.symbol, prx_syms.price)))
    # Concat Trades
    tmp_trades = pd.concat([df_trades, df_close], axis=0).reset_index().drop('index', axis=1)
    # Launch Realised PnL Calculation
    upnl_out = pnl_realised_polars(tmp_trades, verbose)
    upnl_series = upnl_out['pnl_series']
    # Rename column:
    upnl_series = upnl_series.reset_index().rename(columns={'index':'ddate', 'rpnl':'upnl'})
    out_upnl = upnl_series[['ddate', 'symbol', 'upnl']]


    return out_upnl



def pnl_fifo_engine(df_trades, prx=None, enddate=None, adj_ca=1, verbose=False, **kwargs):
    """
    PnL FiFo Engine for Trades in the Fractional Trading Book. The function calculates realised and unrealised PnL.
    Additionally,  the Position at a given cutoff, e.g. EndOfDay. The function contains various kwargs arguments, but
    can be launched plain vanilla as:

        pnl_fifo_engine(startdate=date(2023,2,1), enddate=date(2023,2,5)

    That way all trades are pulled within the startdate - enddate horizon. In order to discount properly against already
    given trades, a cache of trades need to be past as df_cache.

    Kwargs:
    read_cache_trades: read cached trades
    eod_pos: read EOD position of Fractional trading book and transforms the positions as initial trade cache
    syms: limit the calculation on specific ISINs e.g. ['US88160R1014']
    read_price_cache: reads EOD price cache
    multi_proc: activates multiprocessing
    n_cores: number of cores that need to be used (default is 6)

    @param account: select either 'caracalla' or 'caligula'
    @param startdate: date object
    @param enddate: date object
    @param df_cache: DataFrame
    @param adj_ca: if 1, corporate actions are considered
    @param skip_ddate_list: the code does not iterate over the date range of the trades, but executes all trades
    @param verbose: boolean, on True it prints out single PnL results
    @param kwargs:
    @return: two DataFrames for positions and a cache of trades that need to be passed for enddate + 1
    """

    # Define Globals
    global tmp_trades_residual


    # Define StartTime:
    start_time = _datetime.now()

    if adj_ca == 1 and verbose:
        print('\n Adjusting for Corporate Actions ***************************************')


    # Reset the index in order to have a proper sequence of integers
    df_trades = df_trades[['time','symbol','side','booking_category','booking_type','price','quantity','multiplier']]
    df_trades = df_trades.reset_index().drop('index', axis=1)

    if verbose:
        print('\n Initialising PnL Calculation ***************************************')
    # Create Outputs
    out_pos = pd.DataFrame()
    out_trade_pnl = pd.DataFrame()

    if verbose:
        print('\n\t Initialising Single Processor Calculation ***************************************')

    if verbose:
        print('\n\t\t Splitting Trades ***************************************')

    # Filter for Corporate Action Symbols
    syms_ca = df_trades[df_trades.booking_category=='CORPORATE_ACTION'].symbol.unique()
    # Set Corporate Action dataframe
    df_trades_ca=df_trades[df_trades.symbol.isin(syms_ca)]

    # Set Polars dataframe
    df_trades_polars=df_trades[~df_trades.symbol.isin(syms_ca)]
    df_trades_polars=df_trades_polars[['symbol','time','price','quantity','side']]

    # Running Polars
    pnl_series_tmp = pd.DataFrame()
    tmp_trades_residual = pd.DataFrame()
    split_series_tmp=dict()

    if df_trades_polars.empty is False:
        if verbose:
            print('\n\t\t Calculating Polars PnL ***************************************')
        tmp_pnl_polars, tmp_cache_polars, tmp_pos_polars=pnl_realised_polars(df_trades_polars)

        # Formatting Polars Output
        tmp_pnl_polars = tmp_pnl_polars.set_index('time')[['symbol','pnl']]
        tmp_pnl_polars.columns = ['symbol','rpnl']

        # Append Data
        pnl_series_tmp = pd.concat([pnl_series_tmp, tmp_pnl_polars], axis=0)
        tmp_trades_residual = pd.concat([tmp_trades_residual, tmp_cache_polars],axis=0)
    
    if df_trades_ca.empty is False:
        if verbose:
            print('\n\t\t Calculating Corporate Action PnL ***************************************')
        # Running Standard
        rpnl_out = pnl_realised_ca(df_trades_ca, adj_ca, verbose)

        # Extract 'trade_dict', 'pnl_series', 'pos_series' as only those results are further used
        # Other Info
        pnl_series_ca = rpnl_out['pnl_series']
        pnl_series_ca = pnl_series_ca[['symbol','rpnl']]
        pos_series_tmp = rpnl_out['pos_series']
        split_series_tmp = rpnl_out['split_dict']

        # Append Data
        pnl_series_tmp = pd.concat([pnl_series_tmp, pnl_series_ca], axis=0)
        tmp_trades_residual_ca = pd.concat(rpnl_out['trade_dict'].values(),ignore_index=True)
        tmp_trades_residual = pd.concat([tmp_trades_residual,tmp_trades_residual_ca],axis=0)


    # Initialize Unrealised PnL (uPnL)   ********************************************
    # Slice Prices
    syms_tmp = tmp_trades_residual.symbol.unique()
    prx_tmp = prx[[k for k in syms_tmp if k in prx.columns]]
    # Append nan prices for missing symbols in prx
    prx_tmp_missing = pd.DataFrame(index=prx_tmp.index, columns=[k for k in syms_tmp if k not in prx.columns])
    prx_tmp = pd.concat([prx_tmp, prx_tmp_missing], axis=1).T.sort_index().T

    # Filter for enddate
    prx_syms = prx_tmp.loc[[enddate]].T
    prx_syms.columns = ['price']
    prx_syms.index.name = 'symbol'
    prx_syms = prx_syms.reset_index().groupby('symbol').mean()
    

    # Adjust Prices for Splits
    if len(split_series_tmp)>0: 
        for sym in split_series_tmp.keys():
            if split_series_tmp[sym].empty:
                pass
            elif prx_tmp.index[-1] == split_series_tmp[sym].iloc[-1]['time'].date():
                prx_tmp.iloc[-1][sym] = prx_tmp.iloc[-1][sym] / split_series_tmp[sym].iloc[-1]['split_ratio']


    # Run Unrealised PnL Code
    if tmp_trades_residual.empty is False:
        tmp_upnl = pnl_unrealised(tmp_trades_residual, enddate, prx_syms, cut_off='eod', verbose=verbose)
        tmp_upnl = tmp_upnl.groupby(['ddate', 'symbol']).sum().reset_index()
    else:
        tmp_upnl = pnl_series_tmp[['symbol']]
        tmp_upnl['upnl'] = 0.0
        tmp_upnl['ddate'] = _datetime(enddate.year, enddate.month, enddate.day, 23, 59, 59, 0)

    # Create Temporary Result Report
    if pnl_series_tmp.empty:
        tmp_rpnl = tmp_upnl.drop('upnl', axis=1).copy()
        tmp_rpnl['rpnl'] = 0.0
    else:
        tmp_rpnl = pnl_series_tmp[['symbol', 'rpnl']].groupby('symbol').sum().reset_index()
        out_trade_pnl = pd.concat([out_trade_pnl, pnl_series_tmp], axis=0)

    # Concat uPnL and rPnL results
    tmp_pnl = pd.concat([tmp_upnl.set_index('symbol'), tmp_rpnl.set_index('symbol')], axis=1)
    tmp_pnl['ddate']=tmp_pnl.ddate.fillna(method='ffill').fillna(method='bfill')
    tmp_pnl['upnl']=tmp_pnl.upnl.fillna(0)

    # Create Positions Report
    tmp_trades_residual['quantity']=np.where(tmp_trades_residual['side'] == 'S',-1 * tmp_trades_residual['quantity'],tmp_trades_residual['quantity'])
    tmp_pos = tmp_trades_residual[['symbol','quantity']].groupby(['symbol']).sum()
    tmp_pos = pd.concat([tmp_pos, tmp_pnl], axis=1)
    tmp_pos['quantity']=tmp_pos['quantity'].fillna(0)

    # ***********************************************************************************************
    # Create final outputs 
    # Concat Position and Price
    out_pos = pd.concat([tmp_pos, prx_syms], axis=1)

    # Remove all entries in which quantity is 0:
    out_pos = out_pos[out_pos.quantity!=0]

    # Format
    out_pos = out_pos.reset_index()
    out_pos = out_pos[['ddate', 'symbol', 'price', 'quantity', 'rpnl', 'upnl']]

    # Assign Residual Trades
    out_cache = tmp_trades_residual.copy()
    out_cache['quantity'] = out_cache['quantity'].abs()

    # Format Values
    for col in ['price', 'quantity', 'rpnl', 'upnl']:
        out_pos[col] = out_pos[col].fillna(0)

    if verbose:
            print('TIME: %s'%(_datetime.now() - start_time))

    return out_pos, out_cache, out_trade_pnl

