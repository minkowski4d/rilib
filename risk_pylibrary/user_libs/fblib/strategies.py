#!/usr/bin/env python
# -*- coding: UTF-8 -*-



# Python Modules
import os
import numpy as np
import six as _six
from datetime import date, timedelta, datetime as _datetime





def es_recovery(prx=None, prx_eod=None, overrule=False):

    if _datetime.now().date().weekday() == 1 and overrule is False:
        print("Warning: Today is not Weekday Monday")
    else:
        import sys
        from risk_pylibrary.instruments import data_prices as dtp
        if prx is None:
            prx = dtp.get_yahoo_prices(symbols=['^GSPC'], startdate=date(2001, 1, 1), enddate=_datetime.today().date())
        prx = prx.dropna()
        if prx_eod:
            prx.loc[_datetime.now().date(), ] = prx_eod
        else:
            sys.exit("ERROR : Missing Last Price")

        prx['underlying_returns'] = prx.pct_change().dropna()

        last_date = prx.index[-1]
        px_last = prx.iloc[-1, 0]
        maxhigh = max(prx.iloc[-9:, 0])
        minlow = min(prx.iloc[-9:, 0])
        percentile = (px_last-minlow)/(maxhigh-minlow)
        px_crit = 0.2 * (maxhigh -minlow) + minlow
        if percentile < 0.2:
            message = "EQ Recovery should trade today %s. Critical Price to Reach is %s"%(last_date, px_crit)
        else:
            message = "EQ Recovery is not trading today %s. Critical Price to Reach is %s"%(last_date, px_crit)

        return message