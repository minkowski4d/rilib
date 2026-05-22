#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Python Modules
from matplotlib.pyplot import *
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib import ticker
from matplotlib import transforms
import seaborn as sns

sns.set()
from matplotlib import cm

# TR Modules
import pandas as pd
from risk_pylibrary.tools import config as cf

# Colorset for Backtest Factsheets
color_set_fs_bt = ['#2CD5C4',  # turqoise #2E55A5', #darkblue
                   '#7C878E',  # grey
                   '#98cee0',  # cyan
                   '#4a564e',  # darkgreen
                   '#e2ae1d',  # mintgreen
                   '#9E007E',  # purple
                   '#7cd2ef',  # clearcyan
                   '#8d63b2',  # lilac
                   '#8be58d',  # lightgreen
                   '#e2ae1d',  # orange
                   '#B22222',  # firebrick
                   '#FF69B4']  # hotpink

# Colorset for Backtest Summary Factsheet
color_set_fs_bt_summary = ['#2E55A5',  # darkblue
                           '#0051f7',  # midblue
                           '#0c8dec',  # lighterblue
                           '#7b7c7c',  # grey
                           '#98cee0',  # cyan
                           '#4a564e',  # darkgreen
                           '#18dbc7',  # mintgreen
                           '#6d0654',  # purple
                           '#7cd2ef',  # clearcyan
                           '#8d63b2',  # lilac
                           '#8be58d',  # lightgreen
                           '#e2ae1d']  # orange

color_set_vsop_gross_net = [
    '#2CD5C4',  # turqoise for gross performance
    '#CC9966',  # gold for net performance
]


def twinaxis_line_plot(df,nth=1,y1_label='',y2_label='',tlt=None,**kwargs):
    """
    Plot Dataframe Columns on Two Axis with additional formatting. Columnnames are used as labels'
    :param df:
    :param nth:
    :param y1_label:
    :param y2_label:
    :param kwargs:
    :return:
    """
    fig = figure(figsize=(8,5),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=1,bottom=0.01,left=0.08,right=0.95,top=0.75)
    ax0 = subplot(gs[0])
    df.iloc[:,:nth].plot(ax=ax0,label=df.columns[0],color=color_set_fs_bt)
    # ax0.grid(b=True, which='major', color='grey', linestyle='-', alpha=0.6)
    # cl = [cm.jet(i) for i in np.linspace(0, 0.9, len(ax0.lines))]
    # for l, co in zip(ax0.lines, cl):
    #     l.set_color(co)
    ax0.set_ylabel(y1_label)
    ax1 = ax0.twinx()
    df.iloc[:,nth:].plot(ax=ax1,color=color_set_fs_bt_summary[-4:],label=df.columns[1])
    ax1.set_ylabel(y2_label)
    ax0.margins(0);
    ax1.margins(0)
    setp(ax0.xaxis.get_majorticklabels(),rotation=45)
    leg = ax0.legend(loc='upper left',fancybox=True,frameon=True,bbox_to_anchor=(0,1.25),ncol=2)
    leg1 = ax1.legend(loc='upper right',fancybox=True,frameon=True,bbox_to_anchor=(1,1.25),ncol=3)
    leg.get_frame().set_alpha(1)
    leg1.get_frame().set_alpha(1)
    if tlt:
        title(tlt)

    return fig


def twinaxis_plot_bar(df,nth=1,y1_label='',y2_label='',tlt=None,alpha=0.6,width=0.5,**kwargs):
    """
    Plot Dataframe Columns on Two Axis with additional formatting. Columnnames are used as labels'
    :param df:
    :param nth: Give Secondary data column position
    :param y1_label: str
    :param y2_label: str
    :param tlt: Title as str
    :param kwargs:
    :return:
    """
    fig = figure(figsize=(14.5,7),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=1,bottom=0.30,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[0])
    # First Plot - Bar Chart
    # df.iloc[:, nth:].plot(ax=ax0, kind='bar', color='#33AFFF', width=0.5,align='center',alpha=alpha,label=df.columns[nth:].tolist())
    ax0.bar(np.array(df.index),df.iloc[:,nth].values,color='#ced1cd',alpha=alpha,width=width,
            label=df.columns[nth:].tolist())
    # Get axis sizes and set y limit:
    leg_y = 40  # Roughly with font size 10, sized on Returns
    y = max(df.iloc[:,1].values) + leg_y
    ylim([-max(df.iloc[:,1].values) * 1.5,max(df.iloc[:,1].values) * 1.5])
    ylabel(y1_label,fontsize=14,fontweight='bold')
    # ax0.get_legend().remove()
    xticks(fontsize=12,fontweight='bold')
    # xlabel(fontweight='bold')
    yticks(fontsize=12,fontweight='bold')

    # Annotations
    y_ref_0 = max(df.iloc[:,1].values) * 1.2
    for j,k in enumerate(list(df.iloc[:,1] / 100)):
        ax0.text(j,y_ref_0,"{0:.2%}".format(k) if k != 0 else '-',ha='center',
                 **dict(size=12,color='#000000',fontweight='bold'))

    # Second Plot - Scatter
    ax1 = ax0.twinx()
    df_pos = df.iloc[:,0:nth][df > 0].rename(columns={df.columns[0]: 'Positive Performance'})
    df_neg = df.iloc[:,0:nth][df < 0].rename(columns={df.columns[0]: 'Negative Performance'})
    df_pos.plot(ax=ax1,linestyle=' ',marker='D',markersize=7,label='Positive Performance',
                color='#2CD5C4')  # df.columns[0:nth].tolist()
    df_neg.plot(ax=ax1,linestyle=' ',marker='D',markersize=7,label='Negative Performance',color='#8C1C25')
    ylim([min(df.iloc[:,0].values) * 1.1,-min(df.iloc[:,0].values) * 1.1])
    ylabel(y2_label,fontsize=14,fontweight='bold')

    # Annotations
    # Todo: Show '-' for k if k==0
    y_ref_1 = min(df.iloc[:,0].values) * 0.8
    for j,k in enumerate(list(df.iloc[:,0])):
        if k > 0:
            style = dict(size=12,color='#2CD5C4',fontweight='bold')
        elif k < 0:
            style = dict(size=12,color='#8C1C25',fontweight='bold')
        elif k == 0:
            style = dict(size=12,color='#000000',fontweight='bold')
        ax1.text(j,y_ref_1,"{0:,}".format(k) if k != 0 else '-',ha='center',**style)

    ax0.margins(0);
    ax1.margins(0)

    setp(ax0.xaxis.get_majorticklabels(),rotation=35)
    lines0,labels0 = ax0.get_legend_handles_labels()
    lines1,labels1 = ax1.get_legend_handles_labels()
    leg = ax1.legend(lines0 + lines1,eval(labels0[0]) + labels1,loc=(0.2,1.03),prop={'size': 12,'weight': 'bold'},
                     ncol=3)
    # leg = ax1.legend(loc='upper right', fancybox=True, frameon=True)
    leg.get_frame().set_alpha(1)
    # Adjust Axis
    # ax0.grid(b=True, which='major', color='grey', alpha=0.2)
    ax0.axhline(y=0,color='#000000',linewidth=1.05,alpha=0.9)
    for p in [ax0,ax1]:
        vals = p.get_yticks()
        if p == ax0:
            p.set_yticklabels(['{:,.1%}'.format(x) for x in vals / 100])
        # Adjust Plot Canvas
        p.spines['top'].set_visible(False)
        p.spines['bottom'].set_visible(False)

    ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))

    fig.subplots_adjust(bottom=0.8)
    twinaxis_align_yorigin(ax0,0,ax1,0)

    xlim([min(range(len(df))) - 0.5,max(range(len(df))) + 0.5])
    xticks(fontsize=12,fontweight='bold')
    yticks(fontsize=12,fontweight='bold')

    if tlt:
        title(tlt)

    return fig


def twinaxis_align_yorigin(ax0,v0,ax1,v1):
    """adjust ax2 ylimit so that v2 in ax2 is aligned to v1 in ax1"""
    _,y0 = ax0.transData.transform((0,v0))
    _,y1 = ax1.transData.transform((0,v1))
    inv = ax1.transData.inverted()
    _,dy = inv.transform((0,0)) - inv.transform((0,y0 - y1))
    miny,maxy = ax1.get_ylim()
    ax1.set_ylim(miny + dy,maxy + dy)


def multilayer_alert_plot(df,fig_title=None,resize_grids=True,kind='line',save=None):
    """
    Relates to risk.report.trigger_crypto_transaction
    """

    df = df.copy()
    df.index.name = None
    fig = figure(figsize=(8,5))
    sns.set_style("white")

    # Set up Plot Metrics
    grid_x = len(df.columns)
    if resize_grids:
        grid_x = grid_x + 2

    gs = gridspec.GridSpec(grid_x,1,wspace=0,hspace=1,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[:grid_x - 3,0])
    if fig_title:
        title(fig_title[0])
    ax1 = subplot(gs[grid_x - 3:grid_x - 2,0],sharex=ax0)
    if fig_title:
        title(fig_title[1],fontdict={'fontsize': 8.5})
    ax2 = subplot(gs[grid_x - 2:grid_x - 1,0],sharex=ax1)
    if fig_title:
        title(fig_title[2],fontdict={'fontsize': 8.5})
    ax3 = subplot(gs[grid_x - 1:grid_x,0],sharex=ax1)
    if fig_title:
        title(fig_title[6],fontdict={'fontsize': 8.5})
    # Plot 1
    df.iloc[:,[0]].plot(ax=ax0,lw=1,kind=kind)
    df.iloc[:,-7].plot(ax=ax0,linestyle='--',color='#FF00FF',legend=True,alpha=0.5,linewidth=0.75)
    df.iloc[:,-6].plot(ax=ax0,color='#000000',legend=True,alpha=0.5,linewidth=0.75)
    df.iloc[:,-5].plot(ax=ax0,linestyle='--',color='#00FF7F',legend=True,alpha=0.5,linewidth=0.75)
    # Annotate here the first 4 Plots:
    annotate_series_at_date(ax=ax0,format='returns',labels=False)
    nudge_overlapping_annotations(ax=ax0)
    fix_annotations(ax0,overlap_adj=3.0)

    # Plot the markers
    # df.iloc[:,-2][np.isfinite(df.iloc[:,-2])].plot(ax=ax0,linestyle=' ',marker='o',markersize=7, color='red',legend=True,alpha=0.5)
    # df.iloc[:,-1][np.isfinite(df.iloc[:,-1])].plot(ax=ax0,linestyle=' ',marker='^',markersize=7, color='blue',legend=True,alpha=0.5)
    df.iloc[:,[0]][df.iloc[:,-1] == 1].rename(columns={df.columns[0]: df.columns[-1]}).plot(ax=ax0,linestyle=' ',
                                                                                            marker='^',markersize=7,
                                                                                            color='blue',legend=True,
                                                                                            alpha=0.5)
    ax0.margins(0)
    ax0.legend(loc='best',prop={'size': 8})
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)

    # Plot 2
    df.iloc[:,[1]].plot(ax=ax1)
    ax1.legend(loc=3)
    ax1.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    annotate_series_at_date(ax=ax1,format='%0.2f',labels=False)
    ax1.margins(0)

    # Plot 3
    df.iloc[:,[2]].plot(ax=ax2,lw=1)
    ax2.legend(loc=3)
    ax2.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    ax2.margins(0)

    # Plot 4 - Trade Performance
    df.iloc[:,[6]].plot(ax=ax3,lw=1)
    ax3.legend(loc=3)
    ax3.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    annotate_series_at_date(ax=ax3,format='returns',labels=False)
    setp(ax3.xaxis.get_majorticklabels(),rotation=30)
    ax3.margins(0)

    # Remove Legends for Side Plots
    for plt in [ax1,ax2,ax3]:
        plt.get_legend().remove()

    # Plot ever 2 Hour Horizons:
    # for idx_hzn in df[df.index.minute==0].index[::2]:
    #     ax0.axvline(idx_hzn,color='blue',linewidth=1,alpha=0.5)
    #     ax1.axvline(idx_hzn,color='blue',linewidth=1,alpha=0.5)
    #     ax2.axvline(idx_hzn,color='blue',linewidth=1,alpha=0.5)

    # Plot Strategies:
    for idx_strat in df[df.Strategy != ''].index:
        cl = 'green' if df[df.Strategy != ''].loc[idx_strat].Strategy == 'buy' else 'red'
        ax0.axvline(idx_strat,color=cl,linewidth=1,alpha=0.5)
        ax1.axvline(idx_strat,color=cl,linewidth=1,alpha=0.5)
        ax2.axvline(idx_strat,color=cl,linewidth=1,alpha=0.5)
        ax3.axvline(idx_strat,color=cl,linewidth=1,alpha=0.5)

    # if save: fig.savefig(os.path.join(save,'pic_1.jpeg'), dpi=300)

    return fig


def multilayer_trade_plot(df,fig_title=None,resize_grids=True,kind='line',save=None):
    """
    Relates to risk.report.trigger_crypto_transaction
    """

    df = df.copy()
    df.index.name = None
    fig = figure(figsize=(8,5))
    sns.set_style("white")

    # Set up Plot Metrics
    grid_x = len(df.columns)
    if resize_grids:
        grid_x = grid_x + 2

    gs = gridspec.GridSpec(grid_x,1,wspace=0,hspace=1,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[:grid_x - 3,0])
    if fig_title:
        title(fig_title[0])
    ax1 = subplot(gs[grid_x - 3:grid_x - 2,0],sharex=ax0)
    if fig_title:
        title(fig_title[1],fontdict={'fontsize': 8.5})
    ax2 = subplot(gs[grid_x - 2:grid_x - 1,0],sharex=ax1)
    if fig_title:
        title(fig_title[2],fontdict={'fontsize': 8.5})
    ax3 = subplot(gs[grid_x - 1:grid_x,0],sharex=ax1)
    if fig_title:
        title(fig_title[6],fontdict={'fontsize': 8.5})
    # Plot 1
    df.iloc[:,[0]].plot(ax=ax0,lw=1,kind=kind)
    df.iloc[:,-7].plot(ax=ax0,linestyle='--',color='#FF00FF',legend=True,alpha=0.5,linewidth=0.75)
    df.iloc[:,-6].plot(ax=ax0,color='#000000',legend=True,alpha=0.5,linewidth=0.75)
    df.iloc[:,-5].plot(ax=ax0,linestyle='--',color='#00FF7F',legend=True,alpha=0.5,linewidth=0.75)
    # Annotate here the first 4 Plots:
    annotate_series_at_date(ax=ax0,format='%0.2f',labels=False,fixchart=False)
    nudge_overlapping_annotations(ax=ax0)
    fix_annotations(ax0,overlap_adj=3.0)

    # Plot the markers
    # df.iloc[:,-2][np.isfinite(df.iloc[:,-2])].plot(ax=ax0,linestyle=' ',marker='o',markersize=7, color='red',legend=True,alpha=0.5)
    # df.iloc[:,-1][np.isfinite(df.iloc[:,-1])].plot(ax=ax0,linestyle=' ',marker='^',markersize=7, color='blue',legend=True,alpha=0.5)
    df.iloc[:,[0]][df.iloc[:,-1] == 1].rename(columns={df.columns[0]: df.columns[-1]}).plot(ax=ax0,linestyle=' ',
                                                                                            marker='^',markersize=7,
                                                                                            color='blue',legend=True,
                                                                                            alpha=0.5)
    ax0.margins(0)
    ax0.legend(loc='best',prop={'size': 8})
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)

    # Plot 2
    df.iloc[:,[1]].plot(ax=ax1)
    ax1.legend(loc=3)
    ax1.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    annotate_series_at_date(ax=ax1,format='%0.2f',labels=False,fixchart=False)
    ax1.margins(0)

    # Plot 3
    df.iloc[:,[2]].plot(ax=ax2,lw=1)
    ax2.legend(loc=3)
    ax2.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    ax2.margins(0)

    # Plot 4 - Trade Performance
    df.iloc[:,[6]].plot(ax=ax3,lw=1)
    ax3.legend(loc=3)
    ax3.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    annotate_series_at_date(ax=ax3,format='%0.2f',labels=False,fixchart=False)
    setp(ax3.xaxis.get_majorticklabels(),rotation=30)
    ax3.margins(0)

    # Remove Legends for Side Plots
    for plt in [ax1,ax2,ax3]:
        plt.get_legend().remove()

    # Plot ever 2 Hour Horizons:
    # for idx_hzn in df[df.index.minute==0].index[::2]:
    #     ax0.axvline(idx_hzn,color='blue',linewidth=1,alpha=0.5)
    #     ax1.axvline(idx_hzn,color='blue',linewidth=1,alpha=0.5)
    #     ax2.axvline(idx_hzn,color='blue',linewidth=1,alpha=0.5)

    # Plot Strategies:
    for idx_strat in df[df.Strategy != ''].index:
        cl = 'green' if df[df.Strategy != ''].loc[idx_strat].Strategy == 'buy' else 'red'
        ax0.axvline(idx_strat,color=cl,linewidth=1,alpha=0.5)
        ax1.axvline(idx_strat,color=cl,linewidth=1,alpha=0.5)
        ax2.axvline(idx_strat,color=cl,linewidth=1,alpha=0.5)
        ax3.axvline(idx_strat,color=cl,linewidth=1,alpha=0.5)

    # if save: fig.savefig(os.path.join(save,'pic_1.jpeg'), dpi=300)

    return fig


def perf_plot(df,fdate=None,freq='D',delta=None,int_loc=20,logy=False,nint=5,ratio=False,cmap=None,
              tlt=None,y_lbl=None,legend=None,annotate=True,**kwargs):
    """
    Function for TimeSeries Plot with Delta Subplot. Delta works only with two series!
    """
    df = df.copy()
    df.index.name = None
    fig = figure(figsize=(16,10))
    sns.set_style("white")
    import matplotlib.dates as mdates
    days = mdates.DayLocator(interval=int_loc)
    hours = mdates.HourLocator(interval=int_loc)
    #h_fmt = mdates.DateFormatter('%D-%M %H:%M:%S')

    if delta:
        gs = gridspec.GridSpec(2,1,height_ratios=[3,1],wspace=0,hspace=0.025,bottom=0.12,left=0.08,
                               right=0.90,top=0.89)
        ax0 = subplot(gs[0])
        ax1 = subplot(gs[1],sharex=ax0)
    else:
        gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
        ax0 = subplot(gs[0])
    df.plot(ax=ax0,lw=2,color=color_set_fs_bt,legend=legend)
    format_plot(ax0,nint=nint,logy=logy,colormap=cmap,legend=True)
    if annotate == True:
        try:
            annotate_series_at_date(ax=ax0,format='%0.2f',labels=False)
            nudge_overlapping_annotations(ax0)
            fix_annotations(ax0,overlap_adj=4.0)
        except:
            print("Something went wrong")
            pass
    if len(df.columns) == 1:
        n_col = 1
    elif len(df.columns) > 1 and len(df.columns) < 4:
        n_col = 2
    else:
        n_col = 1
    ax0.legend(ncol=n_col,loc='best')
    ax0.margins(0)
    ax0.grid(which='major',color='grey',linestyle='-',alpha=0.6)
    if tlt:
        ax0.set_title(tlt)
    if y_lbl:
        ylabel(y_lbl, fontsize=16)

    if legend is None:
        leg = ax0.get_legend()
        if len(df.columns) >= 4:
            leg.set_bbox_to_anchor([1.08,1])
        else:
            leg.set_bbox_to_anchor([0.25,1.1])
        leg.get_frame().set_alpha(1)
    if delta:
        if ratio:
            ls = df.iloc[:,1] / df.iloc[:,0] * 100
        else:
            ls = (df.iloc[:,delta[1]] - df.iloc[:,delta[0]]).to_frame(name='ExcessReturn')
            ls.columns = ['ExcessReturn']
        ls.plot(ax=ax1,color='#9E007E')
        ax1.fill_between(ls.index,0,ls['ExcessReturn'],facecolor='#9E007E',alpha=0.3)
        format_plot(ax1,nint=nint,logy=logy,legend=False,colormap=None)
        format_ticklabels(ax=ax1,format='%0.1f%' if not ratio else '%0.1f')
        if annotate == True:
            try:
                annotate_series_at_date(ax=ax1,format=None,labels=False,fixchart=False)
                nudge_overlapping_annotations(ax1)
            except:
                pass
        setp(ax1.xaxis.get_majorticklabels(),rotation=30)
        ax1.margins(0)
        ax1.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    else:
        setp(ax0.xaxis.get_majorticklabels(),rotation=30)

    if 'vlines' in kwargs.keys():
        v_lines_loc = df.asfreq(freq).index
        for ye in v_lines_loc:
            ax0.axvline(ye,color='grey',linewidth=1,alpha=0.6)
            if delta:
                ax1.axvline(ye,color='grey',linewidth=1,alpha=0.6)
    if fdate:
        # dont plot fdate when it's before start of tseries.
        try:
            min_date = min(df.index)
            if min_date <= fdate:
                ax0.axvline(fdate,color='red',linewidth=2)
                if delta:
                    ax1.axvline(fdate,color='red',linewidth=2)
        except:
            pass
    ax0.xaxis.set_major_locator(days)
    #ax0.xaxis.set_major_formatter(h_fmt)

    return fig


def heatmap_plot(df,fig_title=None):
    """
    Function for Data Plot with 2 Data Subplots.
    """
    df = df.copy()
    df.index.name = None
    fig = figure(figsize=(8,8))
    sns.set_style("white")
    ax0 = sns.heatmap(df)
    if fig_title:
        title(fig_title)

    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    ax0.margins(0)
    return fig


def kde_plot(df,fig_title=None):
    """
    Function for HDe plot with seaborn.
    """
    fig = figure(figsize=(6,6))
    sns.set_style("white")
    for k in df.columns:
        ax0 = sns.kdeplot(df[k].dropna().values,legend=True)
    if fig_title:
        title(fig_title)

    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    ax0.legend(loc='best')
    ax0.margins(0)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)

    return fig


def join_plot(df,cols=None,fig_title=None):
    if cols is None:
        cols = df.columns
    fig = figure(figsize=(6,6))
    sns.set_style("white")
    ax0 = sns.jointplot(cols[0],cols[1],data=df,kind="reg",dropna=True)
    if fig_title:
        title(fig_title)

    return fig


def perf_cond_plot(ts,pf_name,bm_name):
    import matplotlib.patches as mpatches

    fig = figure(figsize=(12,8))
    sns.set_style("white")
    # Create SubPlot:
    gs = gridspec.GridSpec(2,1,height_ratios=[3,1],wspace=0,hspace=0.3,bottom=0.12,left=0.08,right=0.90,
                           top=0.89)
    ax0 = subplot(gs[0])
    ax1 = subplot(gs[1])

    # Indexed Performance Plot:
    ts.plot(ax=ax0,lw=2,color=color_set_fs_bt,legend=None)
    format_plot(ax0,nint=5,logy=False,colormap=None,legend=True)
    try:
        annotate_series_at_date(ax=ax0,format='%0.2f',labels=False)
        nudge_overlapping_annotations(ax0)
        fix_annotations(ax0,overlap_adj=4.0)
    except:
        print("Something went wrong")
        pass
    if len(ts.columns) == 1:
        n_col = 1
    elif len(ts.columns) > 1 and len(ts.columns) < 4:
        n_col = 2
    else:
        n_col = 1
    ax0.legend(ncol=n_col)
    ax0.margins(0)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    ax0.title.set_text('Index Performance for %s and %s' % (pf_name,bm_name))

    # Monthly Returns Plot
    df = ts.mrets(cutnames=True)
    df = df.sort_index(ascending=False)
    df = df.drop('YTD',axis=1)
    df.columns = ["%.2d" % i for i in range(1,13)]
    df_res = pd.DataFrame()
    for item in df.index.levels[0].tolist():
        temp = df.loc[item]
        temp.columns = [a + ' ' + str(item) for a in df.loc[item].columns.tolist()]
        df_res = pd.concat([df_res,temp.T.dropna()],axis=0)
    df_res['ER'] = (df_res.loc[:,pf_name] - df_res.loc[:,bm_name]) * 100
    df_out = df_res.iloc[:,1:]
    df_out.columns = ['MarketReference','ER']
    df_out['positive'] = df_out['MarketReference'] > 0
    df_out = df_out[~(df_out.MarketReference.isnull()) & ~(df_out.ER.isnull())]
    df_out = df_out.rename(index=lambda x: x.split(" ")[1] + "-" + x.split(" ")[0])

    # Conditional Alpha Plot
    # Producing and Formatting Plot:
    # 1. Set Plot and Condition. Market Positives(Ups) in red, Negatives(Downs) in blue:
    # Standard Plot
    bar(np.arange(len(df_out)),df_out['ER'],color=df_out['positive'].map({True: '#3F9A54',False: '#DE32AC'}).tolist(),
        align='center')
    # 2. Format Labels and Legend
    ax1.set_ylabel('Excess Return')
    max_xticks = 8
    setp(ax1.xaxis.get_majorticklabels(),rotation=30)
    red_patch = mpatches.Patch(color='#3F9A54',label='%s Up' % bm_name)
    blue_patch = mpatches.Patch(color='#DE32AC',label='%s Down' % bm_name)
    leg = ax1.legend(handles=[red_patch,blue_patch],loc="best",fancybox=True,frameon=True,shadow=True)
    leg.get_frame().set_alpha(1)
    ax1.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    xticks(np.arange(len(df_out)),tuple(df_out.index))
    for label in ax1.get_xticklabels()[::2]:
        label.set_visible(False)
    ax1.title.set_text('Excess Return as of Market Reference Ups and Downs')

    return fig


def donut_chart(sizes,names,colors,title_str,fig_x,fig_y):
    """
    Donut Charts as used for Factsheets
    :param sizes: List of Numbers, e.g. Weights
    :param names: List of Names that appear as Labels.
    :param colors: List of e.g. Hex Colors
    :param title_str: Title of the Charts

    Hint:
    Sizes can be added to name strings through string manipulation like:
    names=[i+' '+str(np.round(k,2))+'%' for i,k in zip(names,sizes)]
    """
    if len(sizes) != len(names):
        raise Exception("Please parse equal lengths for sizes and names")

    fig = figure(figsize=(fig_x,fig_y),facecolor="white")
    # Create a circle for the center of the plot
    my_circle = Circle((0,0),0.7,color='white')
    pie(sizes,labels=names,colors=colors,startangle=-125)
    p = gcf()
    p.gca().add_artist(my_circle)
    title(title_str,fontweight='bold')

    return fig


# ********************************************************************************************************************
# Formating Tools


def annotate_series_at_date(ax=None,pos=-1,format=None,labels=False,fontsize=10,fontweight='normal',
                            values=True):
    """
    draws annotations with series values for all series on given axis at a certain date
    if format is None, uses same number format as y axis
    if labels==True, adds the name of the series in front of the value
    :param ax:
    :param pos:
    :param format:
    :param labels:
    :param fixchart:
    :param fontsize:
    :param values:
    :return:
    """

    if ax is None:
        ax = gca()
    for c in ax.get_children():
        if isinstance(c,matplotlib.text.Annotation):
            c.remove()
    ax.get_figure().canvas.draw()
    lines = ax.get_lines()
    x = ax.get_xlim()[-1]
    for l in lines:
        # x=l.get_xdata()[pos]
        y = l.get_ydata()[pos]
        yt = y
        if format == 'returns':
            yt = (y / l.get_ydata()[0] - 1) * 100
            fmt = '%0.2f%%'
        elif format is None:
            try:
                fmt = ax.yaxis.get_major_formatter().fmt
            except:
                try:
                    fmt = ax.yaxis.get_major_formatter().format
                except:
                    fmt = '%0.2f'
        else:
            fmt = format
        txt = '%s%s%s' % (
            (l.get_label() if labels else ''),(': ' if labels and values else ''),(fmt % yt if values else ''))
        fontcolor = matplotlib.colors.to_rgb(l.get_color())
        ann = ax.text(x,y,txt,fontsize=fontsize,color=fontcolor,fontweight=fontweight,
                      bbox=dict(boxstyle='square,pad=0',fc='white',ec='none',alpha=0.5))
    ax.get_figure().canvas.draw()
    # if fixchart:
    #     make_room_4_annotations(ax)
    #     nudge_overlapping_annotations(ax)
    ax.get_figure().canvas.draw()
    return ax


def fix_annotations(ax,overlap_adj=3.0):
    """
    Fixes the overlapping annotation on the right hand side edge.
    :param ax:
    :param overlap_adj:
    :return:
    """
    txt = []
    for tt in ax.texts:
        txt.append((tt.get_position()[0],tt.get_position()[1],tt.get_text(),tt))
    overlap_adj = overlap_adj / 100
    xl = max([x for x,y,t,tt in txt])
    txt = [(y,t,tt) for x,y,t,tt in txt if x == xl]
    txt = sorted(txt,key=lambda x: x[0],reverse=True)
    yhight = (ax.get_ylim()[1] - ax.get_ylim()[0])
    for idx,(y,t,tt) in enumerate(txt):
        if idx > 0:
            diff = abs(y - txt[idx - 1][0]) / yhight
            if diff < overlap_adj:
                tt.set_y(y - (overlap_adj - diff) * yhight)


def nudge_overlapping_annotations(ax=None):
    '''
    tries to shift annotations up and down in order to reduce overlap
    does not work with overly crowded annotations
    '''

    try:
        temp = ax.texts[0].get_window_extent()
    except:
        return
    incr = (ax.get_ylim()[1] - ax.get_ylim()[0]) / 200.0

    for i in range(len(ax.texts)):
        oth = list(range(len(ax.texts)))
        oth.remove(i)
        for j in oth:
            while True:
                bb = ax.texts[i].get_window_extent()
                bbo = ax.texts[j].get_window_extent()
                if bb.overlaps(bbo):
                    ix,iy = ax.texts[i].get_position()
                    jx,jy = ax.texts[j].get_position()
                    incr = -abs(incr) if iy < jy else abs(incr)
                    ax.texts[i].set_position((ix,iy + incr))
                    ax.texts[j].set_position((jx,jy - incr))
                    ax.get_figure().canvas.draw()
                else:
                    break


def format_plot(ax=None,logy=True,legend='labels',colormap=cm.nipy_spectral,nint=None):
    """
    some common formattings for financial time series plots
    legend may be:
     - True: ordinary draggable legend
     - right: place legend box on the right outside the chart
     - labels: draw labels on the right at the endpoint of each series
     - None: no legend
     logy, colormap, nint are used to specify whether y axis should be log-scale, the
      colormap, and to force a number of ticklabels on the y axis
    """
    if ax is None:
        ax = gca()
    nl = len(ax.lines)
    if colormap is not None:
        cl = [colormap(i) for i in np.linspace(0,0.9,nl)]
        for l,co in zip(ax.lines,cl):
            l.set_color(co)
            l.set_linewidth(1)
    if logy:
        ax.set_yscale('log')
    else:
        ax.set_yscale('linear')
    mm = minmax(ax)
    intv = mm[1] - mm[0]
    if nint is None:
        if intv > 2500:
            intv = 500
        elif intv > 1000:
            intv = 250
        elif intv > 500:
            intv = 100
        elif intv > 50:
            intv = 25
        elif intv > 20:
            intv = 20
        elif intv > 10:
            intv = 10
        elif intv > 1:
            intv = 1
        elif intv > 0.1:
            intv = 0.1
        else:
            intv = 0.01
    else:
        intv = max(intv / nint,0.01)
    lb = mm[0] - intv
    ub = mm[1] + intv
    ticks = np.arange(lb,ub,intv)
    if ticks[0] <= 100 and ticks[-1] >= 100 and 100 not in ticks:
        ticks = np.unique(np.hstack([lb,np.arange(100,lb,-intv),np.arange(100 + intv,ub,intv),ub]))
        ticks.sort()
    elif ticks[0] <= 0 and ticks[-1] >= 0 and 0 not in ticks:
        ticks = np.unique(np.hstack([lb,np.arange(0,lb,-intv),np.arange(0 + intv,ub,intv),ub]))
        ticks.sort()
    ax.yaxis.set_ticks(ticks)
    ax.set_ylim([mm[0] - intv * 0.1,mm[1] + intv * (0.27 if logy else 0.1)])
    ticks[0] = np.nan
    ticks[-1] = np.nan
    ax.yaxis.set_ticklabels([np.round(x,2) for x in ticks])
    if legend == True:
        leg = ax.legend()
        format_legends(fig=ax.figure)
    elif legend == 'right':
        leg = ax.legend(loc='center left',bbox_to_anchor=(1.01,0.5))
        try:
            setp(leg.get_texts(),fontsize=8)
        except:
            pass
        ax.get_figure().canvas.draw()
        make_room_4_legend(ax=ax)
    elif legend == 'top':
        leg = ax.legend(loc=(0.01,1.01),ncol=3,fontsize=8)  # loc='upper left') #, bbox_to_anchor=(0.01, 1.12))
        ax.get_figure().canvas.draw()
    elif legend == 'inside':
        leg = ax.legend(shadow=True,fancybox=True)
        format_legends(fig=ax.figure)
    elif legend == 'labels':
        try:
            ax.get_legend().set_visible(False)
        except:
            pass
        annotate_series_at_date(ax=ax,pos=-1,format=None,labels=True,fixchart=True)
    else:
        try:
            ax.get_legend().set_visible(False)
        except:
            pass
    try:
        ax.spines['top'].set_alpha(0.2)
        ax.spines['right'].set_alpha(0.2)
    except:
        pass
    ax.get_figure().canvas.draw()


def format_legends(fig=None,fontsize=8):
    '''
    makes all legends on current figure draggable
    '''
    if fig is None:
        fig = gcf()
    axes = fig.get_axes()
    for ax in axes:
        l = ax.get_legend()
        if l is not None:
            l.set_frame_on(False)
            # l.set_draggable(True)
            setp(l.get_texts(),fontsize=fontsize)
    ax.get_figure().canvas.draw()


def make_room_4_legend(ax=None):
    '''
    makes room on the right side of a chart for annotations
    untested with subplots
    '''
    if ax is None:
        ax = gca()
    fig = ax.get_figure()
    try:
        rend = _find_renderer(fig)
        fig.draw(rend)
        w = fig.get_window_extent(rend).extents[2]
    except:
        return
    p = 1.0
    bbr = ax.get_legend().get_window_extent(rend).extents[2]
    while bbr > w and p > 0.5:
        p -= 0.01
        fig.subplots_adjust(right=p)
        fig.canvas.draw()
        bbr = ax.get_legend().get_window_extent(rend).extents[2]
    fig.canvas.draw()


def _find_renderer(fig):
    if hasattr(fig.canvas,"get_renderer"):
        # Some backends, such as TkAgg, have the get_renderer method, which
        # makes this easy.
        renderer = fig.canvas.get_renderer()
    else:
        # Other backends do not have the get_renderer method, so we have a work
        # around to find the renderer.  Print the figure to a temporary file
        # object, and then grab the renderer that was used.
        # (I stole this trick from the matplotlib backend_bases.py
        # print_figure() method.)
        import io
        fig.canvas.print_pdf(io.BytesIO())
        renderer = fig._cachedRenderer
    return (renderer)


def minmax(ax=None):
    '''
    returns lowest and highest value of all lines on the given axis in a chart
    '''
    if ax is None:
        ax = gca()
    d = [l.get_ydata() for l in ax.lines]
    d = np.ma.masked_invalid(np.hstack(d))
    maxv = d.max()
    minv = d.min()
    return minv,maxv


def format_ticklabels(format=None,ax=None,which_axis='y',color=None,fontsize=10,rotation=0):
    '''
    change formatting of ticklabels
    '''
    if ax is None:
        ax = gca()
    if format is not None:
        from matplotlib.ticker import FormatStrFormatter
        major_formatter = FormatStrFormatter(format)
    if which_axis == 'x':
        if format is not None:
            ax.xaxis.set_major_formatter(major_formatter)
        if color is not None:
            [i.set_color(color) for i in ax.get_xticklabels()]
        labels = ax.get_xticklabels()
        setp(labels,fontsize=fontsize,rotation=rotation)
    elif which_axis == 'y':
        if format is not None:
            ax.yaxis.set_major_formatter(major_formatter)
        if color is not None:
            [i.set_color(color) for i in ax.get_yticklabels()]
        labels = ax.get_yticklabels()
        setp(labels,fontsize=fontsize,rotation=rotation)
    else:
        raise Exception('Unknown axis')
    ax.get_figure().canvas.draw()


def barchart(df,y_label='',tlt=None,width=0.5,alpha=0.3,fmt='%0.2f%%',show_grid=True,color_set=None,**kwargs):
    """
    Plot Dataframe Columns on Two Axis with additional formatting. Columnnames are used as labels'
    :param df:
    :param y_label:
    :param tlt: Title as str
    :param width:
    :param alpha:
    :param fmt:
    :param show_grid:
    :param color_set:
    :param kwargs:
    :return:
    """
    fig = figure(figsize=(16,7),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=1,bottom=0.30,left=0.15,right=0.90,top=0.89)
    ax0 = subplot(gs[0])

    if color_set is None:
        color_set = cm.jet(np.linspace(0,1,len(df.columns)))

    for k in range(0,len(df.columns)):
        vals = list(df.iloc[:,k])
        if k == 0:
            group_idx = np.arange(len(vals))
        else:
            # Reassign group_idx
            group_idx = [i + width for i in group_idx]
        # Plot the bar
        ax0.bar(group_idx,vals,
                color=color_set[k] if color_set else color_set_fs_bt[k],
                alpha=alpha,width=width,
                label=df.iloc[:,k].name)


    setp(ax0.xaxis.get_majorticklabels(),rotation=55)
    if show_grid:
        ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.2)

    # leg0=ax0.legend(loc='center left',bbox_to_anchor=(1.01,0.5))
    # leg0.get_frame().set_alpha(1)
    format_ticklabels(ax=ax0,format=fmt)
    ylabel(y_label,fontweight='bold')
    xticks([j + 3 * width for j in range(len(df.iloc[:,0]))],list(df.index),fontweight='bold',fontsize=6)
    xlabel('Realised PnL',fontsize=16,fontweight='bold')
    yticks(fontweight='bold')
    legend(loc='best')

    if 'remove_spines' in kwargs.keys():
        ax0.spines['top'].set_visible(False)
        ax0.spines['right'].set_visible(False)
        ax0.spines['bottom'].set_visible(False)

    if tlt:
        title(tlt,fontweight='bold')

    return fig


def barchart_grp(df,y_label='',x_label='',tlt=None,fmt='%0.2f%%',show_grid=True,
                 color_set=None,**kwargs):
    """
    Plot Dataframe Columns on Two Axis with additional formatting. Column names are used as labels'
    :param df:
    :param tlt: Title as str
    :param kwargs:
    :return:
    """
    sns.set_style('white')
    ax0 = df.plot(kind='bar',color=color_set if color_set else color_set_fs_bt,align='center',width=0.3)
    fig = ax0.get_figure()
    # Change the plot dimensions (width, height)
    fig.set_size_inches(20,6)
    setp(ax0.xaxis.get_majorticklabels(),rotation=55)
    if show_grid:
        ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.2)

    format_ticklabels(ax=ax0,format=fmt)
    ylabel(y_label,fontweight='bold')
    xlabel(x_label,fontsize=16,fontweight='bold')
    yticks(fontweight='bold')
    legend(loc='best')
    if show_grid:
        ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.2)

    if 'remove_spines' in kwargs.keys():
        ax0.spines['top'].set_visible(False)
        ax0.spines['right'].set_visible(False)
        ax0.spines['bottom'].set_visible(False)

    if tlt:
        title(tlt,fontweight='bold')

    return fig


def barchart_h(df,y_label='',tlt=None,width=0.7,alpha=0.8,fmt='%0.2f%%',show_grid=True,color_set=None,
               **kwargs):
    """
    Plot Dataframe Columns on Two Axis with additional formatting. Columnnames are used as labels'
    :param df:
    :param tlt: Title as str
    :param kwargs:
    :return:
    """
    fig = figure(figsize=(10,9),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=1,bottom=0.30,left=0.15,right=0.90,top=0.89)
    ax0 = subplot(gs[0])
    # First Plot - Bar Chart
    ax0.barh(np.arange(len(df)),df.iloc[:,0].values,width,color=color_set if color_set else color_set_fs_bt,
             alpha=alpha,align='center')
    setp(ax0.xaxis.get_majorticklabels(),rotation=55)
    if show_grid:
        ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.2)
    # leg0=ax0.legend(loc='center left',bbox_to_anchor=(1.01,0.5))
    # leg0.get_frame().set_alpha(1)
    ax0.set_yticks(np.arange(len(df)))
    # Annotations
    if all(i < 1 for i in df.values):
        x_ref_0 = min(df.values) * -1.4
    else:
        x_ref_0 = max(df.values) * 1.15
    for j,k in enumerate(list(df.values / 100)):
        ax0.text(x_ref_0,j,"{0:.2%}".format(k[0]) if k[0] != 0 else '-',ha='center',
                 **dict(size=12,color='#000000'))  # ,fontweight='bold'))
    ax0.set_yticklabels(df.index)

    format_ticklabels(ax=ax0,format=fmt,which_axis='x')
    # ylabel(y_label,fontweight='bold')
    setp(ax0.get_xticklabels(),visible=False)
    if all(i < 1 for i in df.values):
        xlim([min(df.iloc[:,0].values) * 1.4,0])
    elif min(df.iloc[:,0].values) < 0:
        xlim([min(df.iloc[:,0].values) * 1,max(df.iloc[:,0].values) * 1.2])
    else:
        xlim([0,max(df.iloc[:,0].values) * 1.2])
    xlabel('Strategies',fontsize=16,fontweight='bold')
    yticks(fontweight='bold')

    if 'remove_spines' in kwargs.keys():
        ax0.spines['top'].set_visible(False)
        ax0.spines['right'].set_visible(False)
        ax0.spines['bottom'].set_visible(False)

    if tlt:
        title(tlt,fontweight='bold')

    return fig


def barchart_cmp(df,y_label=None,tlt=None,width=None,fmt='%0.2f%%',color_set=None,legend=None,stacked=False,
                     int_xaxis=2,logy=False,**kwargs):
    """
    Plot Dataframe Columns on Two Axis with additional formatting. Columnnames are used as labels'
    :param df:
    :param tlt: Title as str
    :param kwargs:
    :return:
    """
    if color_set is None:
        color_set = cm.jet(np.linspace(0,1,len(df.columns)))
    fig = figure(figsize=(12,7),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=1,bottom=0.30,left=0.15,right=0.90,top=0.89)
    ax0 = subplot(gs[0])
    # First Plot - Bar Chart
    width = 0.7 if width is None else width
    df.plot(ax=ax0,kind='bar',stacked=stacked,color=color_set,alpha=0.9,width=width,legend=legend)
    setp(ax0.xaxis.get_majorticklabels(),rotation=55)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    if legend is None:
        leg0 = ax0.legend(loc='center left',bbox_to_anchor=(1.01,0.5))
        leg0.get_frame().set_alpha(1)
    format_ticklabels(ax=ax0,format=fmt)
    for label in ax0.get_xticklabels()[::int_xaxis]:
        label.set_visible(False)

    ylabel(y_label)

    if logy:
        ax0.set_yscale('log')

    if tlt:
        title(tlt)

    return fig


def risk_budget_bubble(df=None,wgts=None,ll=[],dict_title=None,name_string='',fpath=None,save_plot=0,
                       show_fig=0):
    '''
    Creates Bubble Chart for Risb Budget Tools
    :param df = Risk Contributions of single Factors
    :param wgts = DataFrame of WeightVector of Risk Factors
    :param ll = list of simulated portfolios (df columns!)
    :param dict_title = dictionary for ChartTitle strings. Values expressed in %. E.g. {'Portfolio':5,'Benchmark':5}
    :param name_string= "VaR 99, 20D"
    :return:
    '''
    import seaborn as sns
    import os
    import matplotlib.patches as mpatches
    fig = figure(figsize=(8,5),facecolor="white")
    sns.set_style("white")
    gs = gridspec.GridSpec(2,1,height_ratios=[3,1],wspace=0,hspace=0.01,bottom=0.12,left=0.15,right=0.90,
                           top=0.89)
    ax0 = subplot(gs[0])
    ax0.margins(x=1,y=1,tight=False)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    # Create a Chart Title based on passed df columns and summed values
    str0 = '%s Contribution for %s (Totals: ' % (name_string,ll[0])
    for item,item_value in dict_title.items():
        str0 = str0 + '%s %s %%, ' % (item,np.round(100 * item_value,2))
    title(str0[:-2] + ')',fontsize=12,fontweight='bold')
    # Plot DataSet. Max passed portfolios are 4
    df = df[(df.T != 0).any()]
    weights = wgts[(wgts.T != 0).any()]
    color_list = color_set_fs_bt_summary
    for p,c in dict(zip(ll,color_list[:len(ll)])).items():
        area = np.pi * (100 * weights.loc[p].values) ** 2
        x = p;
        y = df.loc[p].values
        scatter(p,df.loc[p].values * 100,s=area,alpha=0.8,c=c,label=p)

    # ll_patches = []
    # for id, c in dict(zip(range(0, len(ll)), color_list)).items():
    #     ll_patches.append(mpatches.Patch(color=c, label=ll[id]))

    # Label Format
    ylabel('VaR Contribution',fontsize=12,fontweight='bold')
    yticks(fontsize=10,fontweight='bold')
    xlabel('Risk Factor (Bubble Size = Risk Factor Weight)',fontsize=12,fontweight='bold')
    xticks(fontsize=10,fontweight='bold')
    format_ticklabels(ax=ax0,format='%0.2f%%')
    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    ax0.margins(0)

    if show_fig == 1:
        fig.show()
    if save_plot == 1:
        savefig(os.path.join(fpath,'%s_%s.jpeg' % (ll[0],name_string[:3])))
        close()


def strategy_bubble(df=None,wgts=None,ll=[],dict_title=None,name_string='',fpath=None,save_plot=0,
                    show_fig=0):
    """
    Creates Bubble Chart for Strategy Presentations
    :param df = Risk Contributions of single Factors
    :param wgts = DataFrame of Volatilities
    :param ll = list of simulated portfolios (df columns!)
    :param dict_title = dictionary for ChartTitle strings. Values expressed in %. E.g. {'Portfolio':5,'Benchmark':5}
    :return:
    """
    import seaborn as sns
    import os
    import matplotlib.patches as mpatches
    fig = figure(figsize=(8,5),facecolor="white")
    sns.set_style("white")
    gs = gridspec.GridSpec(2,1,height_ratios=[3,1],wspace=0,hspace=0.01,bottom=0.12,left=0.15,right=0.90,
                           top=0.89)
    ax0 = subplot(gs[0])
    ax0.margins(x=1,y=1,tight=False)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    # Create a Chart Title based on passed df columns and summed values
    # str0 = 'Maximum Drawdown over Volatility Contribution'
    # for item,item_value in dict_title.items():
    #    str0=str0+'%s %s %%, '%(item,np.round(100*item_value,2))
    # title(str0,fontsize=12, fontweight='bold')
    # Plot DataSet. Max passed portfolios are 4
    df = df[(df.T != 0).any()]
    weights = wgts[(wgts.T != 0).any()]
    color_list = color_set_fs_bt
    for p,c in dict(zip(ll,color_list[:len(ll)])).items():
        area = np.pi * (100 * weights.loc[p].values) ** 2
        scatter(p,df.loc[p].values * 100,s=area,alpha=0.8,c=c,label=p)

    # Label Format
    ylabel('Return Contribution',fontsize=12,fontweight='bold')
    yticks(fontsize=10,fontweight='bold')
    xlabel('Strategies (Bubble Size = Average Weight over Horizon)',fontsize=12,fontweight='bold')
    xticks(fontsize=10,fontweight='bold')
    format_ticklabels(ax=ax0,format='%0.2f%%')
    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    ax0.margins(0)
    bottom,top = ylim()
    ylim(bottom * 1.05,top * 0.9)

    return fig


def barchart_pnl(df,df_strat,df_pnl_cum,y_label='PnL in Euro',pct=False,tlt=None,fmt='%0.2f',**kwargs):
    """
    Plot Dataframe Columns on Two Axis with additional formatting. Columnnames are used as labels'
    :param df:
    :param tlt: Title as str
    :param kwargs:
    :return:
    """
    import matplotlib.ticker as plticker
    fig = figure(figsize=(9,7),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(3,1,height_ratios=[3,3,3],wspace=0,hspace=0.85,bottom=0.12,left=0.15,right=0.95,
                           top=0.89)
    ax0 = subplot(gs[0]);
    ax1 = subplot(gs[1]);
    ax2 = subplot(gs[2])
    # First Plot - Bar Chart
    df.index.name = ''
    df.plot(ax=ax0,color=color_set_fs_bt,kind='bar',stacked=True,alpha=0.9,
            width=0.7 if len(df) <= 10 else 0.95)
    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    leg0 = ax0.legend(ncol=2 if len(df) > 8 else 1,loc='center left',bbox_to_anchor=(1.01,0.5))
    leg0.get_frame().set_alpha(1)
    ax0.set_ylabel(y_label)
    ax0.set_title("Daily PnL for Sub-Strategies" if pct is False else "Daily Contribution per Sub-Strategy")
    format_ticklabels(ax=ax0,format=fmt)
    # if len(df.index)>=10:
    #    ax0.xaxis.set_major_locator(mdates.WeekdayLocator())
    #    ax0.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

    # Second Plot - Bar Chart
    df_strat.index.name = ''
    df_strat.plot(ax=ax1,color=color_set_fs_bt,kind='bar',stacked=True,alpha=0.9,
                  width=0.7 if len(df) <= 10 else 0.95)
    setp(ax1.xaxis.get_majorticklabels(),rotation=30)
    ax1.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    leg0 = ax1.legend(ncol=2 if len(df) > 4 else 1,loc='center left',bbox_to_anchor=(1.01,0.5))
    leg0.get_frame().set_alpha(1)
    ax1.set_ylabel(y_label)
    ax1.set_title("Daily PnL per Strategy" if pct is False else "Daily Contribution per Strategy")
    format_ticklabels(ax=ax1,format=fmt)
    # if len(df.index) >= 10:
    #    ax1.xaxis.set_major_locator(mdates.WeekdayLocator())
    #    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

    # third Plot - Line Chart
    df_pnl_cum.index.name = ''
    df_pnl_cum.columns = ['Total','Strategies','FX','Fees','Broker Interest','AccruedInterests','Commissions']
    df_pnl_cum.plot(ax=ax2,color=['#2E55A5','#CCCC00','#FFA500','#B30000','#FF00FF','#654321','#20B2AA'])
    ax2.set_ylabel(y_label)
    format_ticklabels(ax=ax2,format=fmt)
    setp(ax2.xaxis.get_majorticklabels(),rotation=30)
    ax2.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)
    leg1 = ax2.legend(loc='center left',bbox_to_anchor=(1.01,0.5))
    leg1.get_frame().set_alpha(1)
    ax2.set_xticklabels([])
    ax2.set_title("Cumulative PnL per Component" if pct is False else "Cumulative Return per Component")

    if tlt:
        title(tlt)

    return fig


def heatmap_corr(corr,rng=[-.2,0.8]):
    from string import ascii_letters
    import numpy as np
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt

    sns.set_style('white')
    # Generate a mask for the upper triangle
    mask = np.zeros_like(corr,dtype=np.bool)
    mask[np.triu_indices_from(mask)] = True

    # Set up the matplotlib figure
    f,ax = plt.subplots(figsize=(11,9))

    # Generate a custom diverging colormap
    # cmap = sns.diverging_palette(220, 10, as_cmap=True)
    cmap = 'YlGnBu'
    # Draw the heatmap with the mask and correct aspect ratio
    plot_heat = sns.heatmap(corr,mask=mask,cmap=cmap,vmin=rng[0],vmax=rng[1],center=0,square=True,
                            linewidths=.5,cbar_kws={"shrink": .5},annot=True,annot_kws={"size": 8})
    setp(plot_heat.xaxis.get_majorticklabels(),rotation=30)
    setp(plot_heat.yaxis.get_majorticklabels(),rotation=0)
    xticks(fontsize=12,fontweight='bold')
    yticks(fontsize=12,fontweight='bold')
    fig = plot_heat.get_figure()

    return fig


def histplot(df,leg=None,fit=False,bins=100):
    fig = figure(figsize=(9,7),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax = subplot(gs[0])
    # ax.grid(b=True, which='major', color='grey', linestyle='-', alpha=0.6)
    # the histogram of the data
    mean = df.mean().iloc[0]
    std = df.std().iloc[0]
    n,bin_num,patches = ax.hist(df.values,bins,density=False)

    if fit:
        # add a 'best fit' line
        y_fit = ((1 / (np.sqrt(2 * np.pi) * std)) * np.exp(-0.5 * (1 / std * (bin_num - mean)) ** 2))
        ax.plot(bin_num,y_fit,'--')
    ax.set_xlabel('Returns',fontsize=14,fontweight='bold')
    ax.set_ylabel('Probability Density',fontsize=14,fontweight='bold')
    # ax.set_title('Portfolio Return Distribution ($\sigma=%s$)'%np.round(std*np.sqrt(250),2), fontsize=14, fontweight='bold')
    ax.set_title('Portfolio Return Distribution ($\sigma=10.2$)',fontsize=14,fontweight='bold')
    ax.axvline(x=0,color='#000000',linewidth=1.8,alpha=0.9,linestyle='-')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    xticks(fontsize=14,fontweight='bold')
    yticks(fontsize=14,fontweight='bold')

    return fig


def scatter_plot(df,ll=[],lnd=None,color_list=None,tlt=None):
    import matplotlib.patches as mpatches
    fig = figure(figsize=(9,7),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax = subplot(gs[0])
    ax.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)

    color_list = color_set_fs_bt_summary if color_list is None else color_list
    for p,c in dict(zip(ll,color_list[:len(ll)])).items():
        x = df.loc[p].values[0]
        y = df.loc[p].values[1]
        scatter(x,y,s=250,alpha=0.8,c=c,label=p)

    ll_patches = []
    for idx,c in dict(zip(range(0,len(ll)),color_list)).items():
        ll_patches.append(mpatches.Patch(color=c,label=ll[idx]))
    leg_plot = ax.legend(handles=ll_patches,loc='best',ncol=1,fancybox=True,frameon=True,shadow=True)
    leg_plot.get_frame().set_alpha(1)

    ax.set_xlabel(df.columns[0])
    ax.set_ylabel(df.columns[1])
    vals_y = ax.get_yticks()
    ax.set_yticklabels(['{:,.2%}'.format(x) for x in vals_y])
    vals_x = ax.get_xticks()
    ax.set_xticklabels(['{:,.2%}'.format(x) for x in vals_x])

    if lnd:
        ax.legend(lnd,loc='upper left')

    if tlt:
        title(tlt)

    return fig


def peer_quantile_chart(df,df_marker,freq=3,qtls=[1.00,0.95,0.75,0.5,0.25,0.05,0.00],width=0.8):
    df = df.rename(index=lambda x: x.strftime("%b") + ' ' + str(x.year))
    df_marker = df_marker.rename(index=lambda x: x.strftime("%b") + ' ' + str(x.year))
    df_qtl = df.T.quantile(qtls)

    fig = figure(figsize=(20,6),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[0])
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)

    # Add colorsets
    # ToDo: Add flexible alpha set based on qtls length
    color_list = ['#b1b1b1','#a7a7a7','#949494','#808080','#c5c5c5','#d8d8d8','#ececec']
    df_marker.iloc[:,0].plot(ax=ax0,linestyle=' ',marker='o',markersize=6,legend=False,color='#0051f7')
    df_qtl.T.iloc[:,[3,2,1,0,-3,-2,-1]].plot(ax=ax0,kind='bar',stacked=True,color=color_list,width=0.8)

    # Format Legend
    handles,labels = gca().get_legend_handles_labels()
    handles = handles[1:];
    labels = labels[1:]
    order = [3,2,1,0,-3,-2,-1]
    legend([handles[idx] for idx in order],[labels[idx] for idx in order],loc='center left',
           bbox_to_anchor=(1.01,0.5))

    ax0.set_xlabel("")
    format_ticklabels(format='%0.2f%%',ax=ax0,which_axis='y')
    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    # for label in ax0.xaxis.get_ticklabels()[::2]:
    #    label.set_visible(False)

    # Remove Black Frame
    ax0.spines['top'].set_visible(False)
    ax0.spines['right'].set_visible(False)
    ax0.spines['bottom'].set_visible(False)

    # Set Title
    title("Peer Group Quantiles Positioning")

    return fig


def plot_beta(rets):
    import statsmodels.api as sm
    from statsmodels import regression

    X = rets.iloc[:,0].values
    Y = rets.iloc[:,1].values

    def linreg(x,y):
        x = sm.add_constant(x)
        model = regression.linear_model.OLS(y,x).fit()
        x = x[:,1]
        return model.params[0],model.params[1]

    alpha,beta = linreg(X,Y)
    print("*** Alpha: %s" % alpha)
    print("*** Beta: %s" % beta)

    X2 = np.linspace(X.min(),X.max(),100)
    Y_hat = X2 * beta + alpha

    fig = figure(figsize=(9,7),facecolor="white")
    sns.set_style('white')
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax = subplot(gs[0])
    ax.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)

    scatter(X,Y,s=250,alpha=0.8)

    xlabel(rets.columns[0])
    ylabel(rets.columns[1])

    plot(X2,Y_hat,'r',0.9)

    return fig


# def cagr_budget_cone_chart(pf = None,ddate = None,sim = None,quantiles = None,nstd = 0.5,verbose = False,fpath = None,
#                            **kwargs):
#     """
#     Plots projected Returns as a Cone. Highlights Median
#     :param sim: Pass a sim_engine output
#     :param quantiles: set quantiles for plot cone
#     """
#     import seaborn as sns
#     import warnings
#     warnings.filterwarnings("ignore")
#
#     if fpath is None:
#         fpath = os.path.join(CF.website_path,CF.webserver_gestione,'risk_management','risk_budget')
#     if ddate is None:
#         ddate = TS.pbd(n = 2,calendar = 'LUX')
#     if quantiles is None:
#         quantiles = [0.01,0.05,0.15,0.25,0.35,0.5,0.65,0.75,0.85,0.9,0.95,0.99]
#     if ddate < (ddate + TS.offsets.BYearEnd(+1)).date() - TS.timedelta(days = 180):
#         chart_title = pf + " Projected YTD Returns"
#         dates = get_rolling_1Y_dates(ddate,calendar = 'LUX')
#         ts = TS.get_prices(pf,startdate = ddate - TS.timedelta(days = 360)).rebase()
#     else:
#         chart_title = pf + " Projected Year End Returns"
#         dates = get_current_year_dates(ddate,calendar = 'LUX')
#     ts = TS.get_prices(pf,startdate = TS.official_nav_dates(enddate = ddate,period = 'Y')[-1]).rebase()
#     ts = ts.reindex(dates);
#     ts = ts.fillna(method = 'bfill')
#     out_fut_ret_cond_distr,ddate = cdi_expected_return_analysis(pfs = [pf],ddate = ddate,nstd = nstd,dates = dates,
#                                                                 sim_bb = sim,quantiles = quantiles,verbose = verbose,
#                                                                 **kwargs)
#     try:
#         mdd_limit = TS.db2pd('select limit_mdd from risk_limits_cdi where account_id="%s"'%pf).index[0]
#     except:
#         mdd_limit = 0
#         if verbose:
#             print("MDD Limit set to 0, hence missing in Limits Table")
#
#     fig = figure(figsize = (6,8),facecolor = "white")
#     gs = gridspec.GridSpec(2,1,height_ratios = [3,1],wspace = 0,hspace = 0.01,bottom = 0.12,left = 0.08,right = 0.90,
#                            top = 0.89)
#     ax0 = subplot(gs[0])
#     sns.set_style("white")
#     (ts).plot(ax = ax0,title = chart_title)
#     colors = ['#800000','#767676','#FFA319','#C16622','#8A9045','#725663','#5B8FA8','#FF3399','#0F425C','#47B5FF',
#         '#D6D6CE','#350E20','#CC8214']
#     end_value = out_fut_ret_cond_distr[pf].loc[0.5]  #00FF00
#     CH.plot([ts.dropna().index[-1],dates[-1]],[ts.dropna().iloc[-1][0],ts.dropna().iloc[-1][0] + end_value*100],
#             label = 'Median',color = '#00FF00',marker = 'o')
#     for idx,color in dict(zip(range(0,len(quantiles)),colors)).items():
#         # Plot Median First with Marker and in Red
#         if idx!=5:
#             end_value = out_fut_ret_cond_distr[pf].iloc[idx]
#             label_item = 'Quantile ' + str(np.round(out_fut_ret_cond_distr.iloc[idx].name,2))
#             plot([ts.dropna().index[-1],dates[-1]],[ts.dropna().iloc[-1][0],ts.dropna().iloc[-1][0] + end_value*100],
#                  label = label_item,color = color)
#     if mdd_limit!=0:
#         axhline(y = ts.dropna().iloc[-1][0] + (100*mdd_limit),color = '#800000',linestyle = ':',
#                 label = 'Current Performance')
#         axhline(y = ts.dropna().iloc[-1][0] - (nstd),color = '#800000',linestyle = '-.',label = 'Average TEV -')
#         axhline(y = ts.dropna().iloc[-1][0] + (nstd),color = '#800000',linestyle = '--',label = 'Average TEV +')
#     leg = ax0.legend(loc = 'upper left',ncol = 3,borderaxespad = 0.,fancybox = True,frameon = True,shadow = True,
#                      prop = {'size':7})
#     leg.get_frame().set_alpha(1)
#     ax0.grid(b = True,which = 'major',color = 'grey',linestyle = '-',alpha = 0.6)
#     ax0.margins(0)
#     format_ticklabels('%0.1f',ax = ax0,fontsize = 10)
#     format_xdates(format = '%Y-%m-%d',freq = 'm',fontsize = 8,rotation = 30,ax = ax0)
#     annotate_series_at_date(ax = ax0,format = None,labels = False,fixchart = True)
#     fix_annotations(ax0,overlap_adj = 4.0)
#
#     return fig


def perf_plot_simulation(df,hist_rets=[],logy=False,nint=None,cmap=cm.cool,**kwargs):
    """
    Function for TimeSeries Simualtion Plot with Delta Subplot. Delta works only with two series!
    """
    df_orig = df.copy()
    df.index.name = None
    fig = figure(figsize=(12,8))
    sns.set_style("white")

    if len(hist_rets) > 0:
        gs = gridspec.GridSpec(4,4,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
        ax0 = fig.add_subplot(gs[1:4,0:3])
    else:
        gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
        ax0 = subplot(gs[0])

    df[['Realized Portfolio']].dropna().plot(ax=ax0,lw=2,color='#000000')

    # Plot Residuals with cmap
    df_res = df[[k for k in df.columns if k not in ['Realized Portfolio','Median']]]
    cmap_colors = cmap(np.linspace(0,1,len(df_res.columns)))
    res_idx = max(df[['Realized Portfolio']].dropna().index)
    df_res[res_idx:].plot(ax=ax0,lw=2,color=cmap_colors)
    format_plot(ax0,nint=nint,logy=logy,colormap=None,legend=True)

    # Plot Median
    df[['Median']][res_idx:].plot(ax=ax0,lw=2,color='#000000',linestyle='-.')

    try:
        annotate_series_at_date(ax=ax0,format='%0.2f',labels=False)
        nudge_overlapping_annotations(ax0)
        fix_annotations(ax0,overlap_adj=4.0)
    except:
        print("Something went wrong")
        pass

    ax0.legend(ncol=1 if len(df.columns) == 1 else 2)
    ax0.margins(0)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.6)

    leg = ax0.get_legend()
    if len(df.columns) >= 4:
        leg.set_bbox_to_anchor([1.08,1])
    else:
        leg.set_bbox_to_anchor([0.25,1.1])
    leg.get_frame().set_alpha(1)
    setp(ax0.xaxis.get_majorticklabels(),rotation=30)

    # if len(hist_rets)>0:
    #     ax1 = fig.add_subplot(gs[1:4,3])
    #     mean=hist_rets.mean().iloc[0]
    #     std=hist_rets.std().iloc[0]
    #     hist_vals=hist_rets[hist_rets.columns[0]].dropna().values
    #     n, bin_num, patches = ax1.hist(mean+std*hist_vals,150, density=1,orientation="horizontal")
    #
    #     cmp_hist = cm.get_cmap("cool")
    #     bin_centers = 0.5 * (bin_num[:-1] + bin_num[1:])
    #     maxi = np.abs(bin_centers).max()
    #     norm = Normalize(-maxi,maxi)
    #
    #     for c, p in zip(bin_centers, patches):
    #         setp(p, "facecolor", cmp_hist(norm(c)))
    #     setp(ax1.get_yticklabels(), visible=True)
    #     #ax1.set_ylim([min(hist_vals), max(hist_vals)])
    #     ax1.set_xlabel('Expected Return Distribution')

    return fig


def perf_trade_plot(df,df_tr,tlt="Volatility Arbitrage - Trading Session 4th January 2021"):
    """
    Function for TimeSeries Plot with Trades Bar Subplot.
    df: TimeSeries DataFrame
    tr: Trades DataFrame

    Indices must be identical
    """

    df = df.copy()
    df.index.name = None
    # Remove timezone
    df = df.rename(index=lambda x: x.replace(tzinfo=None))
    df_tr = df_tr.rename(index=lambda x: x.replace(tzinfo=None))

    fig = figure(figsize=(12,8))
    sns.set_style("white")

    # Create Plot Canvas
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[0])
    df.plot(ax=ax0,lw=2,color='#808080')

    # Plotting Trading Dots
    df_tr = df_tr.dropna()
    df_tr['plot_size'] = abs(df_tr.notional) / abs(df_tr.iloc[-1]).sum()
    color_list = ['#f56d40','#289c4b']  # red,green
    for p in df_tr.index:
        y = df.loc[p].values[0]
        col = color_list[0] if df_tr.loc[p].values[0] < 0 else color_list[1]
        lbl = "Sell " if df_tr.loc[p].values[0] < 0 else "Buy "
        ax0.scatter(p,y,s=250 * df_tr.loc[p].values[-1],marker="o",alpha=0.8,c=col,label=lbl + str(p)[-8:-3])

    ax0.legend(ncol=2,loc='best')
    ax0.margins(0)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.9)
    ax0.set_ylabel('Price')
    # ax0.xaxis.set_major_locator(mdates.HourLocator(interval = 1))
    # ax0.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

    leg = ax0.get_legend()
    for k in range(0,len(df_tr.index) + 1):
        if k != 0:
            leg.legendHandles[k]._sizes = [30]
    # leg.set_bbox_to_anchor([0.25,1.1])
    leg.get_frame().set_alpha(1)
    if tlt:
        title(tlt,fontdict={'fontsize': 12})

    return fig


def factsheet_mrets_chart(ts,window=None,fmt='%0.2f%%',peer_name=None):
    # Plot Monthly Market Conditional Plot:
    m_rets_tmp = ts.mrets(cutnames=True)
    m_rets_tmp = m_rets_tmp.sort_index(ascending=False)
    m_rets_tmp = m_rets_tmp.drop('YTD',axis=1)

    m_rets_plot = pd.DataFrame()
    for item in m_rets_tmp.index.levels[0].tolist():
        temp = m_rets_tmp.loc[item]
        temp.columns = [a + ' ' + str(item) for a in m_rets_tmp.loc[item].columns.tolist()]
        m_rets_plot = pd.concat([m_rets_plot,temp.T.dropna()],axis=0)

    m_rets_plot = m_rets_plot.iloc[:,[1,0]]
    m_rets_plot.columns = ['PF','BM']
    m_rets_plot['Alpha'] = (m_rets_plot.PF - m_rets_plot.BM) * 100
    m_rets_plot = m_rets_plot[~(m_rets_plot.BM.isnull()) & ~(m_rets_plot.PF.isnull())]
    m_rets_plot = m_rets_plot.iloc[:,1:]
    m_rets_plot.columns = ['MarketReturns','ExcessReturn']
    m_rets_plot['positive'] = m_rets_plot['MarketReturns'] > 0
    m_rets_plot = m_rets_plot[~(m_rets_plot.MarketReturns.isnull()) & ~(m_rets_plot.ExcessReturn.isnull())]
    if window:
        m_rets_plot = m_rets_plot[-window:]  # Pick last 12 Months

    sns.set_style("white")
    fig = figure(figsize=(18,6),facecolor="white")
    ax0 = subplot(111)
    bar(np.arange(len(m_rets_plot)),m_rets_plot['ExcessReturn'],
        color=m_rets_plot['positive'].map({True: '#2E55A5',False: '#6d0654'}).tolist(),align='center')
    # 2. Format Labels and Legend
    ax0.set_ylabel('Excess Return')
    # ax0.text(3, 8, 'boxed italics text in data coords', style='italic',
    #         bbox={'facecolor': 'red', 'alpha': 0.5, 'pad': 10})
    max_xticks = 8
    xloc = MaxNLocator(max_xticks)
    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    red_patch = mpatches.Patch(color='#2E55A5',label='%s Up Month' % peer_name if peer_name else "Peer")
    blue_patch = mpatches.Patch(color='#6d0654',label='%s Down Month' % peer_name if peer_name else "Peer")
    leg = ax0.legend(handles=[red_patch,blue_patch],loc="best",fancybox=True,frameon=True,shadow=True)
    leg.get_frame().set_alpha(1)
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.3)
    xticks(np.arange(len(m_rets_plot)),tuple(m_rets_plot.index))
    for label in ax0.get_xticklabels()[::2]:
        label.set_visible(False)

    format_ticklabels(ax=ax0,format=fmt)

    return fig


def stepchart(df,tlt=None,y_lbl=None, annotate=True, format_an='%0.2f'):
    """
    Function for TimeSeries Plot with Trades Bar Subplot.
    df: TimeSeries DataFrame
    Indices must be identical
    """

    df = df.copy()
    df.index.name = None

    fig = figure(figsize=(12,8))
    sns.set_style("white")

    # Create Plot Canvas
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[0])
    max_tmp = 0; min_tmp = 0
    for k in range(0, len(df.columns)):
        max_tmp = df.iloc[:, [k]].values.max() if df.iloc[:, [k]].values.max() > max_tmp else max_tmp
        min_tmp = df.iloc[:, [k]].values.min() if df.iloc[:, [k]].values.min() < min_tmp else min_tmp
        ax0.step(df.index, df.iloc[:, [k]].values, label=df.columns[k])
    # ax0.set_label(df.columns)

    ax0.legend(loc='best')
    leg = ax0.get_legend()
    leg.get_frame().set_alpha(1)
    ax0.margins(0)

    if annotate:
        annotate_series_at_date(ax=ax0, format=format_an, labels=False)

    ylim(min_tmp*1.25, max_tmp*1.25)
    ax0.set_xlabel(df.index.name)
    setp(ax0.xaxis.get_majorticklabels(),rotation=30)
    ax0.set_xlabel('Date',fontsize=14,fontweight='bold')
    ax0.set_ylabel(y_lbl,fontsize=14,fontweight='bold')
    ax0.grid(b=True,which='major',color='grey',linestyle='-',alpha=0.3)

    if tlt:
        title(tlt,fontdict={'fontsize': 12})

    return fig


def fs_qq_plot(df_qq,color_list=['#9E007E','#2CD5C4','#7C878E'],lang_de=False):
    fig_qq_plot = figure(figsize=(10,8))
    sns.set_style("white")

    # Create Plot Canvas
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[0])

    # Setting Colors
    if color_list is None:
        color_list = color_set_fs_bt
    # Building Plot
    for k in range(0,len(df_qq.columns)):
        col = color_list[k]
        for p in df_qq.index:
            y = df_qq.loc[p].values[k]
            ax0.scatter(p,y,s=150,marker="D",alpha=0.8,facecolors=col,edgecolors=col)

    # Legend Formatting
    ll_patches = []
    for idx,c in dict(zip(range(0,len(df_qq.columns)),color_list)).items():
        ll_patches.append(mpatches.Patch(color=c,label=df_qq.columns[idx]))
    ncol_len = 3 if len(df_qq.columns) <= 3 else 2
    legend_plot = ax0.legend(handles=ll_patches,fontsize=14,prop={'weight': 'bold'},loc='upper center',
                             ncol=ncol_len,fancybox=True,frameon=True,shadow=True)
    legend_plot.get_frame().set_alpha(1)

    # Axis Formatting
    # x Axis
    if lang_de:
        x_text = 'Quantile der Normalverteilung'
        y_text = 'Quantile der realisierten Renditeverteilung'
    else:
        x_text = 'Normal Distribution Quantiles'
        y_text = 'Realized Distribution Quantiles'
    ax0.set_xlabel(x_text,fontname='Verdana',fontsize=12,fontweight='bold')
    xlim([min(df_qq.index) - 0.25,max(df_qq.index) + 0.25])
    xticks(fontname='Verdana',fontsize=14,fontweight='bold')
    # y Axis
    ax0.set_ylabel(y_text,fontname='Verdana',fontsize=12,fontweight='bold')
    vals_y = ax0.get_yticks()
    ax0.set_yticklabels(['{:,.2%}'.format(x) for x in vals_y])
    yticks(fontname='Verdana',fontsize=14,fontweight='bold')

    # Frame Formatting
    ax0.spines['top'].set_visible(False)
    ax0.spines['right'].set_visible(False)
    ax0.spines['bottom'].set_visible(False)
    ax0.axhline(y=0,color='#000000',linewidth=1.05,alpha=0.9,linestyle='--')

    return fig_qq_plot


def qq_plot(df_qq,color_list=['#9E007E','#2CD5C4','#7C878E'],tlt=None):
    """
    Docstring for qq_plot
    
    :param df_qq: Description
    :param color_list: Description
    :param tlt: Description
    """
    fig_qq_plot = figure(figsize=(10,8))
    sns.set_style("white")

    # Create Plot Canvas
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[0])

    # Setting Colors
    if color_list is None:
        color_list = color_set_fs_bt
    # Building Plot
    for k in range(0,len(df_qq.columns)):
        col = color_list[k]
        ax0.scatter(df_qq.index.values,df_qq.iloc[:,k].values,color=col)

    # Legend Formatting
    ll_patches = []
    for idx,c in dict(zip(range(0,len(df_qq.columns)),color_list)).items():
        ll_patches.append(mpatches.Patch(color=c,label=df_qq.columns[idx]))
    ncol_len = 3 if len(df_qq.columns) <= 3 else 2
    legend_plot = ax0.legend(handles=ll_patches,fontsize=14,prop={'weight': 'bold'},loc='upper center',
                             ncol=ncol_len,fancybox=True,frameon=True,shadow=True)
    legend_plot.get_frame().set_alpha(1)

    # Axis Formatting
    # x Axis
    x_text = 'Normal Distribution Quantiles'
    y_text = 'Realized Distribution Quantiles'
    ax0.set_xlabel(x_text,fontname='Verdana',fontsize=12,fontweight='bold')
    xlim([min(df_qq.index) - 0.25,max(df_qq.index) + 0.25])
    xticks(fontname='Verdana',fontsize=14,fontweight='bold')
    # y Axis
    ax0.set_ylabel(y_text,fontname='Verdana',fontsize=12,fontweight='bold')
    vals_y = ax0.get_yticks()
    ax0.set_yticklabels(['{:,.2%}'.format(x) for x in vals_y])
    yticks(fontname='Verdana',fontsize=14,fontweight='bold')

    # Frame Formatting
    ax0.spines['top'].set_visible(False)
    ax0.spines['right'].set_visible(False)
    ax0.spines['bottom'].set_visible(False)
    ax0.axhline(y=0,color='#000000',linewidth=1.05,alpha=0.9,linestyle='--')
    if tlt:
        ax0.set_title(tlt)

    return fig_qq_plot


def fs_perf_chart(df,fdate=None,freq='D',delta=[1,0],logy=False,color_list=None,ratio=False,
                  **kwargs):
    """
    Function for TimeSeries Plot with Delta Subplot. Delta works only with two series!
    E.g for jinja Factsheet: rep.perf_chart(ts.iloc[:,[0]],delta=None,logy=False)
    """
    import seaborn as sns;
    sns.set()
    from matplotlib import cm
    from matplotlib.pyplot import setp

    df = df.copy()
    df.index.name = None
    fig = figure(figsize=(11.5,8))
    sns.set_style("white")

    if fdate:
        df = df.rebase(ip=fdate,cut=False)

    if delta:
        gs = gridspec.GridSpec(2,1,height_ratios=[3,1],wspace=0,hspace=0.025,bottom=0.12,left=0.08,
                               right=0.90,top=0.89)
        ax0 = subplot(gs[0])
        ax1 = subplot(gs[1],sharex=ax0)
    else:
        gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
        ax0 = subplot(gs[0])

    if color_list is None:
        color_list = color_set_fs_bt
    df.plot(ax=ax0,lw=2.5,color=color_list)
    format_plot(ax0,nint=None,logy=logy,colormap=None,legend=True)
    try:
        annotate_series_at_date(ax=ax0,labels=False,fontsize=15,fontweight='bold')
        nudge_overlapping_annotations(ax0)
        fix_annotations(ax0,overlap_adj=2.0)
    except:
        pass
    ax0.legend(ncol=1 if len(df.columns) < 2 else 3,fontsize=12,prop={'weight': 'bold'})
    ax0.margins(0)
    # ax0.grid(b=True, which='major', color='grey', linestyle='-', alpha=0.6)
    ax0.axhline(y=100,color='#000000',linewidth=1.05,alpha=0.9,linestyle='--')
    ax0.spines['top'].set_visible(False)
    ax0.spines['right'].set_visible(False)
    ax0.spines['bottom'].set_visible(False)
    ax0.set_ylim(df.min().min() * 0.9,df.max().max() * 1.1)

    leg = ax0.get_legend()
    # leg.set_bbox_to_anchor([0.25,1.1])
    leg.get_frame().set_alpha(1)
    if delta:
        if ratio:
            ls = df.iloc[:,1] / df.iloc[:,0] * 100
        else:
            ls = (df.iloc[:,delta[1]] - df.iloc[:,delta[0]]).to_frame(name='ExcessReturn')
            ls.columns = ['ExcessReturn']
        ls.plot(ax=ax1,color=color_set_fs_bt[1])
        ax1.fill_between(ls.index,0,ls['ExcessReturn'],facecolor=color_set_fs_bt[1],alpha=0.5)
        format_plot(ax1,nint=None,logy=False,legend=False,colormap=None)
        format_ticklabels(ax=ax1,format='%0.1f%%' if not ratio else '%0.1f')
        try:
            annotate_series_at_date(ax=ax1,labels=False,fontsize=14,fontweight='bold')
            nudge_overlapping_annotations(ax1)
        except:
            pass
        # CH.setp(ax1.xaxis.get_majorticklabels(), rotation=30)
        ax1.margins(0)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['bottom'].set_visible(
            False)  # ax1.grid(b=True, which='major', color='grey', linestyle='-', alpha=0.6)
    else:
        # CH.setp(ax0.xaxis.get_majorticklabels(), rotation=30)
        xticks(fontname='Verdana',fontsize=12,fontweight='bold')
        yticks(fontname='Verdana',fontsize=12,fontweight='bold')

    if 'vlines' in kwargs.keys():
        v_lines_loc = df.asfreq(freq).index
        for ye in v_lines_loc:
            ax0.axvline(ye,color='grey',linewidth=1,alpha=0.6)
            if delta:
                ax1.axvline(ye,color='grey',linewidth=1,alpha=0.6)
    if fdate:
        # dont plot fdate when it's before start of tseries.
        try:
            min_date = min(df.index)
            if min_date <= fdate:
                ax0.axvline(fdate,color='black',linewidth=2)
                if delta:
                    ax1.axvline(fdate,color='black',linewidth=2)
        except:
            pass

    return fig


def risk_correlogram(rets,stats_dict,lags=None,title=None):
    from statsmodels.tsa.stattools import acf,q_stat,adfuller
    from statsmodels.graphics.tsaplots import plot_acf,plot_pacf
    from scipy.stats import probplot,moment

    sns.set_style("white")
    lags = min(10,int(len(x) / 5)) if lags is None else lags
    fig = figure(figsize=(12,8))
    gs = gridspec.GridSpec(2,2,wspace=0.15,hspace=0.35,bottom=0.12,left=0.08,right=0.90,top=0.89)

    # Daily Returns
    ax0 = fig.add_subplot(gs[0,0])
    rets.plot(ax=ax0,title='Daily Returns')

    q_p = np.max(q_stat(acf(rets,nlags=lags,fft=False),len(rets))[1])
    stats = f'Q-Stat: {np.max(q_p):>8.2f}\nADF: {adfuller(rets)[1]:>11.2f} \nHurst: {round(stats_dict["hurst"],2)}'
    ax0.text(x=.02,y=.8,s=stats,transform=ax0.transAxes)
    format_plot(ax0,nint=None,logy=False,legend=False,colormap=None)
    format_ticklabels(ax=ax0,format='%0.1f%%')
    ax0.spines['top'].set_alpha(1)
    ax0.spines['right'].set_alpha(1)
    ax0.axes.get_xaxis().get_label().set_visible(False)
    n = 4  # Keeps every 3th label
    [l.set_visible(False) for (i,l) in enumerate(ax0.xaxis.get_ticklabels()) if i % n != 0]
    ax0.set_xlabel('Date')

    # Probability Q-Q Plot
    ax1 = fig.add_subplot(gs[0,1])
    probplot(rets.values.squeeze(),plot=ax1)
    mean,var,skew,kurtosis = moment(rets,moment=[1,2,3,4])
    # s = f'Mean: {mean:>12.2f}\nSD: {np.sqrt(var):>16.2f}\nSkew: {skew:12.2f}\nKurtosis:{kurtosis:9.2f}'
    s = f'Mean: {mean[0]:>12.2f}\nSD: {np.sqrt(var[0]):>16.2f}\nSkew: {skew[0]:12.2f}\nKurtosis:{kurtosis[0]:9.2f}'
    ax1.text(x=.02,y=.73,s=s,transform=ax1.transAxes)
    ax1.set_title('Q-Q Plot')

    # Autocorrelation Plot
    ax2 = fig.add_subplot(gs[1,0])
    plot_acf(x=rets,lags=lags,zero=False,ax=ax2)
    ax2.set_xlabel('Lag')

    # Partial Autocorrelation Plot
    ax3 = fig.add_subplot(gs[1,1])
    plot_pacf(rets,lags=lags,zero=False,ax=ax3)
    ax3.set_xlabel('Lag')

    # Additional Chart options
    fig.suptitle(title,fontsize=20)
    fig.subplots_adjust(top=.9)

    return fig


def math_func(math_func={'Asymmetric': 'x**2 + 2*x + 2'},x_min=-10,x_max=10,ticks=1000):
    sns.set_style("white")
    df = pd.DataFrame(index=np.linspace(x_min,x_max,ticks))

    for k,i in math_func.items():
        x = df.index.values
        df[k] = eval(i)
    # calculate the y value for each element of the x vector
    fig,ax0 = subplots()
    df.plot(ax=ax0,color=color_set_fs_bt,legend=True)
    ax0.axvline(0,color='grey',linewidth=1,alpha=0.6)

    # Legend Formatting
    ax0.legend(ncol=1,fontsize=12,prop={'weight': 'bold'})

    ylim([0,5])

    return fig


def risk_hurst_exponent(H,c,data):
    """
    Plots R/S rescaled Ratio of the Hurst Exponent
    E(R/S) = c * T^H
    :param H: Hurst Exponent
    :param c: constant
    :param data:
    :return:
    """
    sns.set_style("white")
    fig = figure(figsize=(11.5,8))
    gs = gridspec.GridSpec(1,1,wspace=0,hspace=0.025,bottom=0.12,left=0.08,right=0.90,top=0.89)
    ax0 = subplot(gs[0])
    ax0.plot(data[0],c * data[0] ** H,color=color_set_fs_bt[3])
    ax0.scatter(data[0],data[1],color=color_set_fs_bt[0])
    ax0.set_xscale('log')
    ax0.set_yscale('log')
    ax0.set_xlabel('Time interval')
    ax0.set_ylabel('R/S ratio')
    ax0.grid(True)

    return fig


def confidence_ellipse(x,y,n_std=3.0,facecolor='none',calc_add_cov=False,**kwargs):
    """
    Create a plot of the covariance confidence ellipse of *x* and *y*.
    https://carstenschelp.github.io/2018/09/14/Plot_Confidence_Ellipse_001.html

    Parameters
    ----------
    x, y : array-like, shape (n, )
        Input data.

    ax : matplotlib.axes.Axes
        The axes object to draw the ellipse into.

    n_std : float
        The number of standard deviations to determine the ellipse's radiuses.

    **kwargs
        Forwarded to `~matplotlib.patches.Ellipse`

    Returns
    -------
    matplotlib.patches.Ellipse
    """
    sns.set_style("white")

    if x.size != y.size:
        raise ValueError("x and y must be the same size")

    cov = np.cov(x,y)
    pearson = cov[0,1] / np.sqrt(cov[0,0] * cov[1,1])
    # Using a special case to obtain the eigenvalues of this
    # two-dimensionl dataset.
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    ellipse = mpatches.Ellipse((0,0),width=ell_radius_x * 2,height=ell_radius_y * 2,edgecolor='red',
                               facecolor=facecolor,**kwargs)

    # Calculating the standard deviation of x from
    # the square root of the variance and multiplying
    # with the given number of standard deviations.
    scale_x = np.sqrt(cov[0,0]) * n_std
    mean_x = np.mean(x)

    # Calculating the stdandard deviation of y ...
    scale_y = np.sqrt(cov[1,1]) * n_std
    mean_y = np.mean(y)
    transf = transforms.Affine2D().rotate_deg(45).scale(scale_x,scale_y).translate(mean_x,mean_y)

    # Draw Scatter Plot with ellipse
    fig,ax = subplots(1,1,figsize=(6,6))
    ellipse.set_transform(transf + ax.transData)
    ax.add_patch(ellipse)

    if calc_add_cov:
        # Add x negative cov ellipse
        cov_x_neg = np.cov(x[x < 0],y[(x < 0)])
        pearson_x_neg = cov_x_neg[0,1] / np.sqrt(cov_x_neg[0,0] * cov_x_neg[1,1])
        ell_radius_x_0 = np.sqrt(1 + pearson_x_neg)
        ell_radius_y_0 = np.sqrt(1 - pearson_x_neg)
        ellipse_0 = mpatches.Ellipse((0,0),width=ell_radius_x_0 * 2,height=ell_radius_y_0 * 2,
                                     edgecolor=color_set_fs_bt[5],facecolor=facecolor)
        ellipse_0.set_transform(transf + ax.transData)
        ax.add_patch(ellipse_0)

        # Add x positive cov ellipse
        cov_x_pos = np.cov(x[x > 0],y[(x > 0)])
        pearson_x_pos = cov_x_pos[0,1] / np.sqrt(cov_x_pos[0,0] * cov_x_pos[1,1])
        ell_radius_x_1 = np.sqrt(1 + pearson_x_pos)
        ell_radius_y_1 = np.sqrt(1 - pearson_x_pos)
        ellipse_1 = mpatches.Ellipse((0,0),width=ell_radius_x_1 * 2,height=ell_radius_y_1 * 2,edgecolor='blue',
                                     facecolor=facecolor)
        ellipse_1.set_transform(transf + ax.transData)
        ax.add_patch(ellipse_1)

    ax.scatter(x,y,s=0.8)
    ax.scatter(x[x < 0],y[(x < 0)],s=0.8,color=color_set_fs_bt[5])
    ax.axvline(c='grey',lw=1)
    ax.axhline(c='grey',lw=1)
    ax.scatter(np.mean(x),np.mean(y),c='red',s=3)
    # ax.set_title('Balanced Portfolio (30%% S&P500, 70%% US Treasuries).\n Pearson correlation: %s'%np.round(pearson,2))
    ax.set_title('Daily Returns: VSOP Backtest versus S&P500 Correlation.\n Pearson correlation total: %s'
                 '\n Pearson correlation S&P500 neg.: %s'
                 '\n Pearson correlation S&P500 pos.: %s' % (
                     np.round(pearson,2),np.round(pearson_x_neg,2),np.round(pearson_x_pos,2)))
    ax.set_xlabel('S&P 500 Returns')
    ax.set_ylabel('VSOP Backtest Returns')

    return fig


def density_plot(df, colorset=['#9E007E', '#2CD5C4', '#7C878E'], tlt='', line_formatter=['-','--',':']):


    from scipy import stats
    sns.set_style("white")
    fig, ax = subplots(1, 1, figsize=(10, 4))

    # Iterate through the five airlines
    for col in df:
        # Set index:
        idx = list(df.columns).index(col)
        # Set Color:
        col_color = colorset[idx]
        # Set Line Formatter:
        col_line_type = line_formatter[idx]
        # Draw the density plot
        tmp = df[col] * 100
        tmp.plot.kde(ax=ax, legend=False, color=col_color, linestyle=col_line_type)
        ax.axvline(tmp.mean(), c=col_color, lw=1, linestyle=col_line_type)
        ax.plot(tmp, [0] * len(df[col]), '|', color=col_color)


    # Plot formatting
    ax.legend(prop={'size': 8}, title='Simulations')
    ax.set_title('Density Plot for Simulations - %s'%tlt if len(tlt) > 0 else 'Density Plot for Simulations')
    ax.set_xlabel('Returns in %')
    ax.set_ylabel('Density')
    #ax.set_ylim(-0.1,10)
    ax.axhline(c='black', lw=1)
    ax.grid(which='major', color='grey',linestyle='-',alpha=0.6)

    return fig


def distribution_comp():
    import matplotlib.pyplot as plt
    from scipy.stats import multivariate_t
    from scipy.stats import multivariate_normal

    fig = figure(figsize=(12,8))
    gs = gridspec.GridSpec(1,2,wspace=0.15,hspace=0.35,bottom=0.12,left=0.08,right=0.90,top=0.89)

    # Duild Grid
    x,y = np.mgrid[-2:4:.01,-3:2:.01]
    pos = np.dstack((x,y))

    # Distributions:
    rv_t = multivariate_t([1.0,-0.5],[[2.1,0.3],[0.3,1.5]],df=2)
    rv_norm = multivariate_normal([1.0,-0.5])

    # Start Plotting
    # Plot 1
    ax0 = fig.add_subplot(gs[0,0])
    contourf(x,y,rv_t.pdf(pos))
    ax0.set_title('Multivariate Student t Distribution')
    ax0.set_aspect('equal')
    # Plot 2
    ax1 = fig.add_subplot(gs[0,1])
    contourf(x,y,rv_norm.pdf(pos))
    ax1.set_title('Multivariate Normal Distribution')
    ax1.set_aspect('equal')

    return fig



def polygon_fill_gaussian(df):
    import matplotlib.pyplot as plt
    import numpy as np

    x = np.linspace(0,10,200)
    y1 = np.random.normal(0.02,1,200).cumsum() + 20
    y2 = np.random.normal(0.05,1,200).cumsum() + 50

    polygon = plt.fill_between(x,y1,y2,lw=0,color='none')
    ylim = plt.ylim()
    verts = np.vstack([p.vertices for p in polygon.get_paths()])
    ymin,ymax = verts[:,1].min(),verts[:,1].max()
    gradient = plt.imshow(np.array([np.interp(np.linspace(ymin,ymax,200),[y1i,y2i],np.arange(2))
                                    for y1i,y2i in zip(y1,y2)]).T, cmap='YlGnBu',aspect='auto',origin='lower',extent=[x.min(),x.max(),ymin,ymax])
    gradient.set_clip_path(polygon.get_paths()[0],transform=plt.gca().transData)
    plt.ylim(ylim)
    plt.show()


def plot_dynamic_strats(t,v_t_strat,v_t_risky,w_t_risky,h_t_risky,num,j_sel):
    """This function generates a dynamic plot comparing the performance of
    a strategy against a risky instrument over time.

    Parameters
    ----------
        t : array, shape (t_bar,)
        v_t_strat : array, shape (j_bar, t_bar)
        v_t_risky : array, shape (j_bar, t_bar)
        w_t_risky : array, shape (j_bar, t_bar)
        h_t_risky: array, shape (j_bar, t_bar)
        num: int
        j_sel: int

    Returns
    -------
        plots
    """
    import numpy as np

    # adjust v_t_risky so that it has same initial value as v_t_strat
    v_t_risky = v_t_risky * v_t_strat[0,0] / v_t_risky[0,0]

    mu_risky = np.mean(v_t_risky,axis=0,keepdims=True).reshape(-1)
    sig_risky = np.std(v_t_risky,axis=0,keepdims=True).reshape(-1)
    mu_strat = np.mean(v_t_strat,axis=0,keepdims=True).reshape(-1)
    sig_strat = np.std(v_t_strat,axis=0,keepdims=True).reshape(-1)

    fig = plt.figure()
    gs = GridSpec(1,2)
    gs1 = GridSpecFromSubplotSpec(3,1,subplot_spec=gs[0])

    num_bins = int(round(100 * np.log(v_t_strat.shape[1])))
    lgrey = [0.8,0.8,0.8]  # light grey
    dgrey = [0.4,0.4,0.4]  # dark grey

    j_bar = v_t_risky.shape[0]

    x_min = t[0]
    x_max = 1.25 * t[-1]
    y_min = v_t_strat[0,0] / 4
    y_max = v_t_strat[0,0] * 2.25

    # scatter plot
    ax4 = plt.subplot(gs[1])
    plt.scatter(v_t_risky[:,-1],v_t_strat[:,-1],marker='.',s=2)
    so = np.sort(v_t_risky[:,-1])
    plt.plot(so,so,label='100% risky instrument',color='r')
    plt.plot([y_min,v_t_risky[j_sel,-1],v_t_risky[j_sel,-1]],
             [v_t_strat[j_sel,-1],v_t_strat[j_sel,-1],y_min],'b--')
    plt.plot(v_t_risky[j_sel,-1],v_t_strat[j_sel,-1],'bo')
    ax4.set_xlim(y_min,y_max)
    ax4.set_ylim(y_min,y_max)
    ax4.xaxis.set_major_formatter(FuncFormatter(tick_label_func))
    ax4.yaxis.set_major_formatter(FuncFormatter(tick_label_func))
    plt.xlabel('Strategy')
    plt.ylabel('Risky instrument')
    plt.legend()

    # weights and holdings
    ax3 = plt.subplot(gs1[2])
    y_min_3 = np.min(h_t_risky[j_sel,:-1])
    y_max_3 = np.max(h_t_risky[j_sel,:-1])
    plt.sca(ax3)
    plt.plot(t,w_t_risky[j_sel,:],color='b')
    plt.axis([x_min,x_max,0,1])
    plt.xticks(np.linspace(t[0],1.2 * t[-1],7))
    plt.yticks(np.linspace(0,1,3),color='b')
    plt.ylabel('Weights',color='b')
    plt.xlabel('Time')

    ax3_2 = ax3.twinx()
    plt.plot(t,h_t_risky[j_sel,:],color='black')
    plt.ylabel('Holdings',color='black')
    plt.axis([x_min,x_max,y_min_3 - 1,y_max_3 + 1])
    plt.yticks(np.linspace(y_min_3,y_max_3,3))
    ax3_2.yaxis.set_major_formatter(FuncFormatter(tick_label_func_1))

    ax1 = plt.subplot(gs1[0],sharex=ax3,sharey=ax4)
    # simulated path, standard deviation of strategy
    for j in range(j_bar - num,j_bar):
        plt.plot(t,v_t_strat[j,:],color=lgrey)
    plt.plot(t,v_t_strat[j_sel,:],color='b')
    plt.plot(t,mu_strat + sig_strat,color='orange')
    plt.plot(t,mu_strat - sig_strat,color='orange')
    plt.xticks(np.linspace(t[0],1.2 * t[-1],7))
    # histogram
    y_hist,x_hist = np.histogram(v_t_strat[:,-1],num_bins)
    scale = 0.25 * t[-1] / np.max(y_hist)
    y_hist = y_hist * scale
    plt.barh(x_hist[:-1],y_hist,height=(max(x_hist) - min(x_hist)) /
                                       (len(x_hist) - 1),left=t[-1],facecolor=dgrey,edgecolor=dgrey)
    plt.setp(ax1.get_xticklabels(),visible=False)
    plt.ylabel('Strategy')
    ax1.set_ylim(y_min,y_max)
    ax1.yaxis.set_major_formatter(FuncFormatter(tick_label_func))

    # risky instrument
    ax2 = plt.subplot(gs1[1],sharex=ax3,sharey=ax4)
    # simulated path, standard deviation of risky instrument
    for j in range(j_bar - num,j_bar):
        plt.plot(t,v_t_risky[j,:],color=lgrey)
    plt.plot(t,v_t_risky[j_sel,:],color='b')
    plt.plot(t,mu_risky + sig_risky,color='orange')
    plt.plot(t,mu_risky - sig_risky,color='orange')
    plt.xticks(np.linspace(t[0],1.2 * t[-1],7))
    # histogram
    y_hist,x_hist = np.histogram(v_t_risky[:,-1],num_bins)
    scale = 0.25 * t[-1] / np.max(y_hist)
    y_hist = y_hist * scale
    plt.barh(x_hist[:-1],y_hist,height=(max(x_hist) - min(x_hist)) /
                                       (len(x_hist) - 1),left=t[-1],facecolor=dgrey,edgecolor=dgrey)
    plt.setp(ax2.get_xticklabels(),visible=False)
    plt.ylabel('Risky instrument')
    ax2.set_ylim(y_min,y_max)
    ax2.yaxis.set_major_formatter(FuncFormatter(tick_label_func))

    plt.grid(True)
    plt.tight_layout()

    return fig,gs
