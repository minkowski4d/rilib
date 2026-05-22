#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import pandas
from pandas import *
import os
from pandas.tseries.frequencies import to_offset
__version__ = pandas.__version__


from datetime import datetime as _datetime
from datetime import date, timedelta
import numpy as np


# Custom Modules
from tools import utils as ut


def rebase(self, ip=None, rv=100, cut=True, fill=True):
    """
    rebases dataframe values by columns to a given value at a common point in time

    ip: point at which to rebase; if None, this is set to the first row without nan values
        may also be a date, in which case rebases at that date
        can also be a string: ytd, to rebase at beginning of current year
                              mtd, to rebase at beginning of current year
    rv: value at which to rebase; if this is a string, then the value of the corresponding
        column is used as rebase value
    cut: if true, removes the part before the rebasing point
    fill: if false, keep nan values
    """
    df = self.copy()
    index = df.index
    # if isinstance(index,core.indexes.datetimes.DatetimeIndex): index=index.date
    if ip is None:
        if isinstance(df, Series):
            ip = np.isnan(df.astype(np.float).values).argmin()
        else:
            #import pdb
            #pdb.set_trace()
            ip = np.any(np.isnan(df.astype(np.float).values), 1).argmin()
    elif isinstance(ip, (date, _datetime, Timestamp)):
        if isinstance(ip, (_datetime, Timestamp)) and isinstance(df.index[0], date):
            ip = ip.date()
        elif isinstance(ip, date) and isinstance(df.index[0], (Timestamp, _datetime)):
            ip = _datetime(ip.year, ip.month, ip.day).date()
        ip = (index >= ip).argmax()
    elif isinstance(ip, str):
        if ip.lower() == 'ytd':
            ip = (_datetime(index[-1].year, 1, 1) - offsets.BDay()).date()
        elif ip.lower() == 'mtd':
            ip = (_datetime(index[-1].year, df.index[-1].month, 1) - offsets.BDay()).date()
        else:
            ip = (index[-1] + to_offset(ip)).date()
        ip = (index >= ip).argmax()
    nans = df.isnull()
    if cut:
        df = df.iloc[ip:].fillna(method='ffill').fillna(method='bfill')
        ip = 0
    if not fill:
        df = df.mask(nans.reindex(df.index))
    if isinstance(rv, str):
        rv = df[rv].iloc[ip]
    df = df / df.iloc[ip] * rv
    return df


def sb_simulate(self, len_sim=None, data_in_levels=True, out_freq=0, n_sim=10000, ff=1, p=1. / 60., fpath=None,
                fname=None, to_lvl=True, verbose=1, seed=None):
    """

    :param self: dataframe, containing the series to be simulated
    :param len_sim: int, time horizon (length) of each simulation
    :param n_sim: int, number of simulations to be performed
    :param seed: int (between 0 and 2^32 - 1). set the seed of the random number generator. default = None. The seed is reset at the end of simulation
                back to the default value.
    :param data_in_levels: bools, set it to True if series passed are in levels and must be different
    :param out_freq: int, if 0 series simulated are returned in levels else they are returned as returns with freq=out_freq
    :param to_lvl: produce an indexed 100 timeseries out of simulate returns
    :param ff: int, min block size length
    :param p: float, probability of success for geometric distribution of blocks' length
    :param fpath: if not None it is a string stating where the simulation panel will be saved as pickle file
    :param fname: None or int, if int detrend simulating series (returns/yield changes) picking the cycle component of an HP filter
    :param verbose: bool, if not False print the % of sim processed

    :return: DataFrame, index: simulation_id/time_id --> columns: series simulated
    """
    from risk_pylibrary.risk_models.econometrics import WB
    # Prepare data for the stationary bootstrap analysis
    df = self.copy()
    df = df[df.index >= df.dropna().index[0]]
    df = df.fillna(method='ffill')
    if type(p) is not float: p = float(p)

    # If the dataframe passed contains series that are in levels then considered pct_changes at the highest frequency posible
    if data_in_levels is True:
        df = df.pct_change(periods=1).dropna()
    else:
        pass

    # If the length of the simulation is not specified then set it to the original series length
    if len_sim is None: len_sim = df.shape[0]

    # Initialize the output
    if out_freq < 1:
        len_sim = len_sim - 1
        l_out_sim = len_sim + 1 if to_lvl else len_sim
    else:
        l_out_sim = len(range(out_freq, len_sim + 1, out_freq))

    # Get values to be boostrapped
    values = df.values
    ids_list = list()
    results = list()
    i = 0
    if verbose > 0: print('Simulation in progress...')
    if verbose > 0: pb = ut.ProgressBar(n_sim)

    # Set the seed, default is None.
    np.random.seed(seed)
    for s in range(0, n_sim, 1):
        # ids for simulation items
        ids = list(zip([s] * l_out_sim, range(0, l_out_sim, 1)))

        # Generate a SB simulation
        sim, LL = WB(values, p=p, ff=ff, hori=len_sim)

        # Trasform the series of returns to series in levels
        if to_lvl:
            sim = 100. * np.vstack((np.ones(sim.shape[1]), np.cumprod(1. + sim, axis=0)))

            # If out_freq is 0 then keep the series in level, else produce returns at out_freq frequency
            if out_freq == 0:
                pass
            else:
                sim = (sim[out_freq::out_freq, :] / sim[0:-out_freq:out_freq, :]) - 1.

        results.append(sim)
        ids_list += ids

        i += 1
        if verbose > 0: pb.animate(i)

    # Resets the seed back to None.
    np.random.seed(None)
    sim_df = DataFrame(data=np.vstack(tuple(results)), index=MultiIndex.from_tuples(ids_list), columns=df.columns)
    # Ensure output elements are float type
    sim_df = sim_df.astype(float)
    # Set index names
    sim_df.index.names = ['sim_id', 'time_id']

    if (fpath is not None) and (fname is not None):
        sim_df.to_excel(os.path.join(fpath, fname + '.xls'))

    if verbose > 0: print('Simulation completed.')

    return sim_df, ids_list



def rets2lvl(self, compound = True, verbose = False):
    """
    returns a series of levels based upon given returns
    """

    nms = self.columns.tolist() if isinstance(self, DataFrame) else self.name
    if compound:
        if verbose: print("Warning: the Returns will be compounded for: %s"%nms)
        out = (1+self).cumprod()*100
        fi = self.index.searchsorted(self.first_valid_index())
        if fi == 0:  # need to add a date for base value
            if isinstance(self.index[0], int):
                out = out.reindex(list(out.index)+[out.index[-1]+1]).shift(1)
            else:
                d = np.ceil(np.mean([x.days for x in np.diff(out.index.tolist())]))
                out.loc[out.index[fi]-timedelta(d)] = np.nan
            out = out.sort_index()
        else:
            fi-= 1
        out.iloc[fi] = 100
    else:
        if verbose: print("Warning: the Returns will NOT be compounded for: %s"%nms)
        out = (self.cumsum()+1)*100

    return out



def add_subgroups(self, total_label=' All',agg_func=np.sum, drop_single_rows=False):
    '''
    given a dataframe with multilevel index, calcs a total for each level and adds it as a row to the dataframe
    :param total_label: string to be used to identify total rows (a str starting with space place it on top when sorting)
    :param drop_single_rows: remove subtotals for groups where there is only one line
    '''

    df = self.copy()
    nlevels = df.index.nlevels
    out = df.groupby(lambda x: total_label).agg(agg_func)
    out.index = MultiIndex(levels=[[total_label]]*nlevels, codes=[[0]]*nlevels, names=df.index.names)
    for l in range(nlevels - 1):
        temp = df.groupby(level=list(range(l + 1))).agg(agg_func)
        if temp.index.nlevels == 1:
            idx = [temp.index.tolist()]
        else:
            idx = list(zip(*temp.index.tolist()))
        for i in range(l + 1,nlevels):
            idx.append([total_label]*temp.shape[0])
        temp.index = MultiIndex.from_tuples(list(zip(*idx)), names=df.index.names)
        out = out.append(temp)

    if out.index.nlevels == 1:
        out.index = out.index.get_level_values(0)

    # Remove useless groups (because there is only one sublevel)
    if drop_single_rows:
        singles = Series(1, index = out.index)
        for i in range(nlevels - 1):
            temp = df.groupby(df.index.names[:i + 1]).count().iloc[:,0].to_frame('x')
            for k in df.index.names[i + 1:]: temp[k] = total_label
            temp = temp.reset_index().set_index(df.index.names).iloc[:,0]
            temp = temp[temp == 1]
            if temp.shape[0] > 0:
                singles[temp.index] = 0
        out = out.loc[singles[singles == 1].index]


    return df.append(out).sort_index()



def portfolio_rets(self, wgts):
    """
    Calculates Portfolio Return based on return dataframe and weights
    @param wgts: list or array
    """
    out = DataFrame(index=self.index, columns=['pf'])

    if isinstance(wgts, list):
        wgts = DataFrame([wgts]*len(self.index),index=self.index,columns=self.columns)

    out['pf'] = self.mul(wgts).sum(axis=1)

    return out


def rets2py(self, dateformat=None):
    out = self.copy()
    if dateformat is None: dateformat = "%d.%m.%y"
    out['ddate'] = out['ddate'].apply(lambda x: _datetime.strptime(x, dateformat))
    out['ddate'] = out['ddate'].apply(lambda x: x.date())
    out = out.set_index('ddate')

    return out

def rets2db(self):
    """
    Creates a pd.melt dataframe for parsing into DWH
    """
    if self.index.name!='ddate': raise Exception("Error: index name must be ddate")

    return melt(self.reset_index(), id_vars='ddate', var_name='code')


def mrets(tsorig,**kwargs):
    """
    Monthly return Table.
    :param tsorig: DataFrame composed e.g. by PF and BM
    :return: Monthly Return Table
    """
    import calendar
    import pandas as pd
    from pandas import offsets
    from datetime import date
    # Standard Calculation on Month End Dates, e.g. 31/05 - 30/06
    ts=tsorig.asfreq('M',method='ffill').copy()
    if pd.to_datetime(max(ts.index)).date() != max(tsorig.index): ts = concat([ts,tsorig.iloc[[-1]]], axis=0)
    ts=ts.rename(index=lambda x: pd.to_datetime(x))
    if pd.to_datetime(min(ts.index)).date() != min(tsorig.index): ts = concat([ts,tsorig.iloc[[0]]], axis=0)
    ts = ts.rename(index=lambda x: pd.to_datetime(x))
    ts = ts.sort_index()
    ts.index = pd.to_datetime(ts.index)

    ts=ts.sort_index(ascending=True); rets=ts.pct_change().iloc[1:]
    rets['Year']=[a.year for a in rets.index]; rets['Month']=[a.month for a in rets.index]
    rt=rets.pivot_table(columns='Year',index='Month').T
    rt.index=rt.index.swaplevel(0,1)

    # Calculate Year Performances
    # Based on normal Year Ends 31/12 to 31/12
    yrets=ts.asfreq('M',method='ffill').fillna(method='ffill').fillna(method='bfill').asfreq('A',method='ffill')
    yrets.loc[min(ts.index)] = ts.loc[min(ts.index)]
    yrets.loc[max(ts.index)] = ts.loc[max(ts.index)]
    yrets = yrets.sort_index(ascending=True)
    yrets=yrets.pct_change().iloc[1:]
    yrets.index=[a.year for a in yrets.index]
    #Make sure that years without data do not appear as "0" but remain NaN
    for tsi in yrets.columns:
        for y in yrets.index:
            if ts.loc[ts.index.year==y,tsi].isnull().all():
                yrets.loc[y,tsi]=np.nan

    rt['YTD']=yrets.stack()
    rt.index.set_names(['Year', 'Symbol'],inplace=True)
    missing_mnth=list(set(list(range(1, 13))) - set(rt.columns))
    if len(missing_mnth)>0:
        for mnth in missing_mnth:
            rt[mnth]=np.nan
        rt = rt[[k for k in rt.columns if k != 'YTD'] + ['YTD']]

    rt=rt.rename(columns=lambda x:calendar.month_name[x] if x!='YTD' else x)

    if 'cutnames' in kwargs.keys(): rt=rt.rename(columns=lambda x: x[:3])

    return rt.sort_index(ascending=False)


def stats(self,model=None,bmk=None,calc_rfree=False,comp=False,freq='W',verbose=True,**kwargs):

    if verbose: print("Warning: Always Use Returns for this Function!!!")
    # Make Series Stationary
    rets=self.copy()
    #rets = rets.ffill().asfreq(freq, method='ffill')
    if calc_rfree:
        ts_rfree,rfree=ut.get_backtest_series(['euribor_1M_360_pct'])
        rfree=rfree.reindex(rets.index).fillna(method='ffill').iloc[:,0]
    else:
        rfree=None

    if isinstance(bmk,int):
        bmk=rets.iloc[:,bmk]
    else:
        bmk=None

    # calc statistics for each column in ts
    if 'rollyear' in kwargs.keys():  # break into years and repeat analysis for each year, then produce a Panel with results
        years = list(dict.fromkeys([x.year for x in df.index]))
        statdict = {}
        for y in years:
            idx = rets.index.year == y
            if idx.sum() > 1:
                stats = DataFrame()
                for name, srs in rets.join([] if bmk is None else [] if bmk.name in rets.columns else bmk).iteritems():
                    if srs[idx].dropna().shape[0] > 0:
                        temp = srs[idx]._rets_stats(ref=None if bmk is None else bmk[idx],model=model[idx], rfree=rfree,comp=comp,ret_fmts=False,verbose=verbose)
                        stats = stats.join(temp, how='outer')
                statdict[y] = stats
            stats = concat(statdict.values(), keys=statdict.keys())
    else:
        # repeat for each column of rets
        stats = DataFrame()
        for name, srs in rets.join([] if bmk is None else [] if bmk.name in rets.columns else bmk).iteritems():
            temp, fmt = srs._rets_stats(ref=bmk, rfree=rfree,comp=comp, model=model, ret_fmts=True)
            stats = stats.join(temp, how='outer')

    if 'rename' in kwargs.keys():
        nms={'ExpSF5':'cVaR_5_5D','P01':'VaR_99_5D','P05':'VaR_95_5D','P50':'Return_Median',
             'P50A':'Return_Median_Ann','P95':'Return_Quantile_95pct','P99':'Return_Quantile_99pct',
             'Avg':'Avg_Return','AvgA':'Avg_Return_Ann','StD':'Standard_Dev','StDA':'Volatility','ShR':'Sharpe',
             'MDD':'MaxDrawDown','AnnTR':'CAGR'}
        stats=stats.rename(index=nms)

    return stats

# -----------------------------------------------------------------------------------------------------------------------


DataFrame.rebase =            rebase
Series.rebase =               rebase
DataFrame.sb_simulate =       sb_simulate
DataFrame.rets2lvl =          rets2lvl
Series.rets2lvl =             rets2lvl
DataFrame.rets2py =           rets2py
DataFrame.add_subgroups =     add_subgroups
DataFrame.portfolio_rets=     portfolio_rets
DataFrame.rets2db =           rets2db
DataFrame.mrets =           mrets
DataFrame.stats =            stats
Series.stats =               stats

