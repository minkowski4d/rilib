#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import timedelta, date, datetime as _datetime
from joblib import Parallel, delayed
import multiprocessing
import traceback

# Import Custom Modules
from risk_pylibrary.tools import config as CF
from tools.snowflake_db import db_connection as db
from risk_pylibrary.projects.pnl import pnl_support as pnl_sup
from risk_pylibrary.projects.pnl import pnl_fifo_polars as pnl_p
from risk_pylibrary.projects.pnl import pnl_fifo as pnl



def pnl_prep_data(blank_cache=True):


    start_list=[date(2025,2,8)]
    end_list=[date(2025,2,28)]
    instr_types=['STOCK','BOND','FUND']
    #account_list=['caligula','trajan','caracalla','tiberius']#'
    account_list=['tiberius']
    skip_ddate_list=True
    skip_cache=False
    fixed_startpoint=None#date(2024,1,2)
    fixed_endpoint=None#date(2024,8,27)
    counter_sd=1
    counter_ed=21
    append_out_put=False



    import multiprocessing
    print('Cores Available: %s'%multiprocessing.cpu_count())
    n_cores = multiprocessing.cpu_count();
    enable_multi_proc=False
    if enable_multi_proc is True:
        print('Cores in Usage: %s'%n_cores)
    #
    pd.options.mode.chained_assignment = None
    import warnings
    warnings.filterwarnings('ignore')
    if blank_cache:
        CF.cache_pnl_prices={}
        CF.cache_pnl_trade={}

    for account in account_list:
        
        if account == 'caligula':
            query_eis=True
            print('\n \t Using EIS TRading Data for account: %s'%(account))
        else:
            query_eis=False
            
        print('\n \t Starting Iteration for %s at: %s'%(account, _datetime.now()))
        print('\n \t\t Fetching Trades for dates %s and %s'%(start_list[0] if fixed_startpoint is None else fixed_startpoint, end_list[-1] if fixed_endpoint is None else fixed_endpoint))
        

        df_trades = pnl_sup.get_trades_pnl(account=account,
                                        startdate=start_list[0] if fixed_startpoint is None else fixed_startpoint, 
                                        enddate=end_list[-1] if fixed_endpoint is None else fixed_endpoint,
                                        add_filter=None,
                                        query_eis=query_eis,
                                        instrument_type=instr_types).sort_values(by='time')
        df_trades['price']=df_trades['price'].astype(float)
        df_trades_filtered=df_trades.copy()
        df_trades_filtered=df_trades_filtered.sort_values(by='time')


        # Setting Custom 
        if start_list is None:
            print('\n \t Setting a startlist based on trades max date')
            start_list=df_trades['time'].apply(lambda x: x.date()).unique()

        if end_list is None:
            print('\n \t Setting an endlist by copying the startlist')
            end_list=start_list
            
        
        # Get Prices
        df_prx = pnl_sup.get_prices_eod(startdate=start_list[0], enddate=end_list[-1], read_full_dwh=True)

        
        # Get Cache
        if skip_cache is False:
            start_str_cache = _datetime.strftime((start_list[0] - timedelta(counter_sd)),"%Y%m%d")
            end_str_cache = _datetime.strftime((end_list[0] - timedelta(counter_ed)),"%Y%m%d")
            
            print("\n \t\t Getting Cache on Dates: %s and %s"%(start_list[0] - timedelta(counter_sd),end_list[0] - timedelta(counter_ed)))
            tmp_cache=pd.read_pickle('~/Development/repos/risk/risk_pylibrary/projects/pnl/storage/%s_%s_%s_all_recon_tmp_cache_total.pkl'%(start_str_cache,end_str_cache,account))
            
            print("\t\t\t Slicing following instrument_types: %s"%instr_types)
            tmp_cache=tmp_cache[tmp_cache.instrument_type.isin(instr_types)]
            
            # FB 20241001 Excluding JP3734800000 as it causes an error
            # no position in there but a stock split on the 27th September
            if account == 'caracalla':
                tmp_cache = tmp_cache[~tmp_cache.symbol.isin(['JP3734800000','JP3493800001','JP3709600005'])]
            #elif account == 'caligula':
            #    instr_excl = ['US67066G1040','DE000ENER6Y0','NL0010273215']
            #    tmp_cache = tmp_cache[tmp_cache.symbol.isin(instr_excl)]
            
        else:
            tmp_cache = pd.DataFrame()
        

        if append_out_put:
            out_pos=pd.DataFrame()
        
        for startdate, enddate in dict(zip(start_list,end_list)).items():
            
            # Print Start and Enddate
            print('\n \t\t Slicing Trades for dates %s and %s'%(startdate, enddate))
            # Slice Trades
            tmp_trades = df_trades_filtered[df_trades_filtered['time'] <= _datetime.combine(enddate, _datetime.max.time())]
            tmp_trades = tmp_trades[tmp_trades['time'] >= _datetime.combine(startdate, _datetime.min.time())]

            if tmp_cache.empty is False:
                print('\n \t\t Cache - Number of Row: %s'%len(tmp_cache))
                print('\t\t Cache - Number of Unique Symbols: %s'%len(tmp_cache.symbol.unique()))

                if 'account' in tmp_cache.columns:
                    tmp_cache = tmp_cache.drop(['report_date', 'account'],axis=1)


            # Concat Print New Trades Cache
            total_trade_cache = pd.concat([tmp_cache,tmp_trades],axis=0)
            
            #if account == 'caligula':
            #    instr_excl = ['US67066G1040','DE000ENER6Y0','NL0010273215']
            #    print('\n \t\t Excluding the following instruments: %s'%instr_excl)
            #    total_trade_cache = total_trade_cache[total_trade_cache.symbol.isin(instr_excl)]
                
            CF.cache_pnl_trade = total_trade_cache
            print('\n \t\t Trades tmp Trades - Number of Row: %s'%len(tmp_trades))
            print('\t\t Trades Cache (tmp and cache) - Number of Row: %s'%len(CF.cache_pnl_trade))
            print('\t\t Trades Cache (tmp and cache) - Number of Unique Symbols: %s'%len(CF.cache_pnl_trade.symbol.unique()))
            
                    
            # Slicing Price Cache
            print('\n \t\t Slicing Prices for dates %s and %s'%(startdate, enddate))
            
            #tmp_prx = df_prx[CF.cache_pnl_trade.symbol.unique()]
            tmp_prx=df_prx
            #print('\n \t\t Prices Cache - Number of nans: %s'%(len(tmp_prx.T)-len(tmp_prx.T.dropna())))
            
            CF.cache_pnl_prices = tmp_prx[startdate:enddate]


def pnl_calc(account):

    import multiprocessing
    print('Cores Available: %s'%multiprocessing.cpu_count())
    n_cores = multiprocessing.cpu_count()-2;
    enable_multi_proc=True
    if enable_multi_proc is True:
        print('Cores in Usage: %s'%n_cores)

    start_list=[date(2025,2,8)]
    end_list=[date(2025,2,28)]
    instr_types=['STOCK','BOND','FUND']
    #account_list=['caligula','trajan','caracalla','tiberius']#'
    account_list=['caligula']
    skip_ddate_list=True
    skip_cache=False
    fixed_startpoint=None#date(2024,1,2)
    fixed_endpoint=None#date(2024,8,27)
    counter_sd=1
    counter_ed=21
    append_out_put=False

    # Count unique instrumente and ventually scale down n_cores
    len_instr = len(CF.cache_pnl_trade.symbol.unique())
    if n_cores > len_instr:
                print("\n Scaling down n_cores to: %s"%len_instr)
                n_cores_res = len_instr
    else:
        n_cores_res = n_cores
    
    if enable_multi_proc:
        if account == 'caligula':
            tmp_pos,tmp_cache, tmp_trades = pnl.pnl_fifo_engine(startdate=start_list[0], enddate=end_list[0],multi_proc=True,
                                                                    n_cores = n_cores,read_cache_trades=True,read_price_cache=True,
                                                                    skip_ddate_list=skip_ddate_list,verbose=False)
        else:
            tmp_pos,tmp_cache, tmp_trades = pnl.pnl_fifo_engine_old(startdate=start_list[0], enddate=end_list[0],multi_proc=True,
                                                                    n_cores = n_cores,read_cache_trades=True,read_price_cache=True,
                                                                    skip_ddate_list=skip_ddate_list,verbose=False)
    else:
        if account == 'caligula':
            tmp_pos,tmp_cache, tmp_trades = pnl.pnl_fifo_engine(startdate=start_list[0], enddate=end_list[0],read_cache_trades=True,read_price_cache=True,
                                                        skip_ddate_list=skip_ddate_list,verbose=False)
        else:
            tmp_pos,tmp_cache, tmp_trades = pnl.pnl_fifo_engine_old(startdate=start_list[0], enddate=end_list[0],read_cache_trades=True,read_price_cache=True,
                                                        skip_ddate_list=skip_ddate_list,verbose=False)
        

    return tmp_pos, tmp_cache


def dump_files(tmp_pos,tmp_cache,startdate,enddate,account):

    start_str=str(startdate.year)+('0'+str(startdate.month) if + startdate.month<10 else str(startdate.month)) +('0'+str(startdate.day) if startdate.day<10 else str(startdate.day));
    end_str=str(startdate.year)+('0'+str(enddate.month) if + enddate.month<10 else str(enddate.month)) +('0'+str(enddate.day) if enddate.day<10 else str(enddate.day));
    # Pos Format
    tmp_pos['account']=account;
    tmp_pos=tmp_pos.dropna();
    tmp_pos=tmp_pos[tmp_pos.upnl.abs()!=np.inf];
    #
    # Cache Format
    tmp_cache['report_date']=_datetime(enddate.year,enddate.month,enddate.day,23,59,59);
    tmp_cache['account']=account;
    instr_type_str = 'total'
    
    tmp_pos.to_pickle('~/Development/repos/risk/risk_pylibrary/projects/pnl/storage/%s_%s_%s_all_recon_tmp_pos_%s.pkl'%(start_str,end_str,account,instr_type_str));    
    tmp_cache.to_pickle('~/Development/repos/risk/risk_pylibrary/projects/pnl/storage/%s_%s_%s_all_recon_tmp_cache_%s.pkl'%(start_str,end_str,account,instr_type_str));


def pnl_calc_total(blank_cache=False):

    start_list=[date(2025,2,8)]
    end_list=[date(2025,2,28)]
    instr_types=['STOCK','BOND','FUND']
    #account_list=['caligula','trajan','caracalla','tiberius']#'
    account_list=['caligula']
    skip_ddate_list=True
    skip_cache=False
    fixed_startpoint=None#date(2024,1,2)
    fixed_endpoint=None#date(2024,8,27)
    counter_sd=1
    counter_ed=21
    append_out_put=False



    import multiprocessing
    print('Cores Available: %s'%multiprocessing.cpu_count())
    n_cores = multiprocessing.cpu_count();
    enable_multi_proc=False
    if enable_multi_proc is True:
        print('Cores in Usage: %s'%n_cores)
    #
    pd.options.mode.chained_assignment = None
    import warnings
    warnings.filterwarnings('ignore')
    if blank_cache:
        CF.cache_pnl_prices={}
        CF.cache_pnl_trade={}

    for account in account_list:
        
        if account == 'caligula':
            query_eis=True
            print('\n \t Using EIS TRading Data for account: %s'%(account))
        else:
            query_eis=False
            
        print('\n \t Starting Iteration for %s at: %s'%(account, _datetime.now()))
        print('\n \t\t Fetching Trades for dates %s and %s'%(start_list[0] if fixed_startpoint is None else fixed_startpoint, end_list[-1] if fixed_endpoint is None else fixed_endpoint))
        

        df_trades = pnl_sup.get_trades_pnl(account=account,
                                        startdate=start_list[0] if fixed_startpoint is None else fixed_startpoint, 
                                        enddate=end_list[-1] if fixed_endpoint is None else fixed_endpoint,
                                        add_filter=None,
                                        query_eis=query_eis,
                                        instrument_type=instr_types).sort_values(by='time')
        df_trades['price']=df_trades['price'].astype(float)
        df_trades_filtered=df_trades.copy()
        df_trades_filtered=df_trades_filtered.sort_values(by='time')


        # Setting Custom 
        if start_list is None:
            print('\n \t Setting a startlist based on trades max date')
            start_list=df_trades['time'].apply(lambda x: x.date()).unique()

        if end_list is None:
            print('\n \t Setting an endlist by copying the startlist')
            end_list=start_list
            
        
        # Get Prices
        df_prx = pnl_sup.get_prices_eod(startdate=start_list[0], enddate=end_list[-1], read_full_dwh=True)

        
        # Get Cache
        if skip_cache is False:
            start_str_cache = _datetime.strftime((start_list[0] - timedelta(counter_sd)),"%Y%m%d")
            end_str_cache = _datetime.strftime((end_list[0] - timedelta(counter_ed)),"%Y%m%d")
            
            print("\n \t\t Getting Cache on Dates: %s and %s"%(start_list[0] - timedelta(counter_sd),end_list[0] - timedelta(counter_ed)))
            tmp_cache=pd.read_pickle('~/Development/repos/risk/risk_pylibrary/projects/pnl/storage/%s_%s_%s_all_recon_tmp_cache_total.pkl'%(start_str_cache,end_str_cache,account))
            
            print("\t\t\t Slicing following instrument_types: %s"%instr_types)
            tmp_cache=tmp_cache[tmp_cache.instrument_type.isin(instr_types)]
            
            # FB 20241001 Excluding JP3734800000 as it causes an error
            # no position in there but a stock split on the 27th September
            if account == 'caracalla':
                tmp_cache = tmp_cache[~tmp_cache.symbol.isin(['JP3734800000','JP3493800001','JP3709600005'])]
            #elif account == 'caligula':
            #    instr_excl = ['US67066G1040','DE000ENER6Y0','NL0010273215']
            #    tmp_cache = tmp_cache[tmp_cache.symbol.isin(instr_excl)]
            
        else:
            tmp_cache = pd.DataFrame()
        

        if append_out_put:
            out_pos=pd.DataFrame()
        
        for startdate, enddate in dict(zip(start_list,end_list)).items():
            
            # Print Start and Enddate
            print('\n \t\t Slicing Trades for dates %s and %s'%(startdate, enddate))
            # Slice Trades
            tmp_trades = df_trades_filtered[df_trades_filtered['time'] <= _datetime.combine(enddate, _datetime.max.time())]
            tmp_trades = tmp_trades[tmp_trades['time'] >= _datetime.combine(startdate, _datetime.min.time())]

            if tmp_cache.empty is False:
                print('\n \t\t Cache - Number of Row: %s'%len(tmp_cache))
                print('\t\t Cache - Number of Unique Symbols: %s'%len(tmp_cache.symbol.unique()))

                if 'account' in tmp_cache.columns:
                    tmp_cache = tmp_cache.drop(['report_date', 'account'],axis=1)


            # Concat Print New Trades Cache
            total_trade_cache = pd.concat([tmp_cache,tmp_trades],axis=0)
            
            #if account == 'caligula':
            #    instr_excl = ['US67066G1040','DE000ENER6Y0','NL0010273215']
            #    print('\n \t\t Excluding the following instruments: %s'%instr_excl)
            #    total_trade_cache = total_trade_cache[total_trade_cache.symbol.isin(instr_excl)]
                
            CF.cache_pnl_trade = total_trade_cache
            print('\n \t\t Trades tmp Trades - Number of Row: %s'%len(tmp_trades))
            print('\t\t Trades Cache (tmp and cache) - Number of Row: %s'%len(CF.cache_pnl_trade))
            print('\t\t Trades Cache (tmp and cache) - Number of Unique Symbols: %s'%len(CF.cache_pnl_trade.symbol.unique()))
            
                    
            # Slicing Price Cache
            print('\n \t\t Slicing Prices for dates %s and %s'%(startdate, enddate))
            
            #tmp_prx = df_prx[CF.cache_pnl_trade.symbol.unique()]
            tmp_prx=df_prx
            #print('\n \t\t Prices Cache - Number of nans: %s'%(len(tmp_prx.T)-len(tmp_prx.T.dropna())))
            
            CF.cache_pnl_prices = tmp_prx[startdate:enddate]

            
            # Count unique instrumente and ventually scale down n_cores
            len_instr = len(CF.cache_pnl_trade.symbol.unique())
            if n_cores > len_instr:
                        print("\n Scaling down n_cores to: %s"%len_instr)
                        n_cores_res = len_instr
            else:
                n_cores_res = n_cores
            
            if enable_multi_proc:
                tmp_pos,tmp_cache, tmp_trades = pnl.pnl_fifo_engine(startdate=startdate, enddate=enddate,multi_proc=True,
                                                                        n_cores = n_cores_res,read_cache_trades=True,read_price_cache=True,
                                                                        skip_ddate_list=skip_ddate_list,verbose=False)
            else:
                tmp_pos,tmp_cache, tmp_trades = pnl.pnl_fifo_engine(startdate=startdate, enddate=enddate,read_cache_trades=True,read_price_cache=True,
                                                            skip_ddate_list=skip_ddate_list,verbose=False)

            # Dump files
            start_str=str(startdate.year)+('0'+str(startdate.month) if + startdate.month<10 else str(startdate.month)) +('0'+str(startdate.day) if startdate.day<10 else str(startdate.day));
            end_str=str(startdate.year)+('0'+str(enddate.month) if + enddate.month<10 else str(enddate.month)) +('0'+str(enddate.day) if enddate.day<10 else str(enddate.day));
            # Pos Format
            tmp_pos['account']=account;
            tmp_pos=tmp_pos.dropna();
            tmp_pos=tmp_pos[tmp_pos.upnl.abs()!=np.inf];
            #
            # Cache Format
            tmp_cache['report_date']=_datetime(enddate.year,enddate.month,enddate.day,23,59,59);
            tmp_cache['account']=account;
            instr_type_str = 'total' if len(instr_types)>=2 else instr_types[0]
            
            if append_out_put:
                # Append Positions to pos
                out_pos = pd.concat([out_pos, tmp_pos], axis=0)
            else:
                tmp_pos.to_pickle('~/Development/repos/risk/risk_pylibrary/projects/pnl/storage/%s_%s_%s_all_recon_tmp_pos_%s.pkl'%(start_str,end_str,account,instr_type_str));
            
            
            tmp_cache.to_pickle('~/Development/repos/risk/risk_pylibrary/projects/pnl/storage/%s_%s_%s_all_recon_tmp_cache_%s.pkl'%(start_str,end_str,account,instr_type_str));
            #tmp_cache.to_csv('/root/risk_pylibrary/projects/pnl/storage/caligula_eis/%s_%s_%s_all_recon_tmp_cache_%s.csv'%(start_str,end_str,account,instr_type_str),index=False);
            #tmp_pos.to_csv('/root/risk_pylibrary/projects/pnl/storage/caligula_eis/%s_%s_%s_all_recon_tmp_pos_%s.csv'%(start_str,end_str,account,instr_type_str),index=False);
        
        # Saving Positions Output to file in case of summary output
        if append_out_put:
            out_pos.to_pickle('~/Development/repos/risk/risk_pylibrary/projects/pnl/storage/%s_%s_%s_all_recon_tmp_pos_%s.pkl'%(start_str,end_str,account,instr_type_str));
            