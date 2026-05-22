#!/usr/bin/env python
# -*- coding: UTF-8 -*-



# Import Python Modules
import numpy as np


# Custom Modules
from risk_pylibrary.tools import charting as CH


def overshoots_vs_vaR(df, chart_fmt = {'model':'mc', 'distr':'t','qtl':0.99}, verbose = True):
    """
    Overshoot visualization. Value at Risk is plotted as a line, while daily returns as a scatter. Overshoot are
    highlighted by color and marker type
    @param df: dataframe, first column = realized pct changes, second column = value at risk  X,1D
    @param chart_fmt:
    @return: figure
    """
    # Format Data Input:
    df_plot = df.copy()
    vaR_col = 'VaR %s,1D'%str(int(chart_fmt['qtl']*100))
    df_plot.columns = ['Portfolio Returns', vaR_col]

    #Multiply by 100 for formatting purposes:
    df_plot *= 100

    # Build Chart Area
    fig = CH.figure(figsize=(12, 7), facecolor="white")
    gs = CH.gridspec.GridSpec(1, 1, wspace=0, hspace=1, bottom=0.30, left=0.15, right=0.90, top=0.89)
    ax = CH.subplot(gs[0])

    # Plot Value at Risk as line:
    df_plot[[vaR_col]].plot(ax=ax, legend=False)
    xl = ax.set_xlim(df_plot.index[0], df_plot.index[-1])

    # Check for Overshoots and store index information
    c = []
    for idx in df_plot.index:
        real_ret = np.round(df_plot.loc[idx, 'Portfolio Returns'],2)
        vaR = np.round(df_plot.loc[idx, vaR_col],2)
        if real_ret < vaR:
            c.append('#BB00BB')
            if verbose: print('%s: Return %s, %s %s'%(idx, real_ret, vaR_col , vaR))
        else:
            c.append('#000000')
    c = np.array(c, dtype='object')
    labels = {
        '#BB00BB': 'Daily Returns: %s Overshoot'%vaR_col,
        '#000000': 'Daily Returns: No Overshoot'}

    # Plot Returns as scatter
    markers = {'#BB00BB': 'x', '#000000': 'o'}
    for color in np.unique(c):
        sel = c == color
        ax.scatter(
            df_plot.index[sel],
            df_plot.loc[sel, 'Portfolio Returns'],
            marker=markers[color],
            c=c[sel],
            label=labels[color],s=2)

    # Format figure output
    ax.margins(x = 0.5)
    # Set title based on used model
    if chart_fmt['model'] == 'mc':
        tlt = 'MonteCarlo Value at Risk (distribution: %s)'%chart_fmt['distr']
    elif chart_fmt['model'] == 'gjr':
        tlt = 'GJR-GARCH Value at Risk (distribution: %s)'%chart_fmt['distr']
    ax.set_title(tlt)
    # Set legend
    leg0 = ax.legend(loc='best')
    leg0.get_frame().set_alpha(1)
    # Adjust axis labels
    CH.ylabel('Returns in %')
    CH.xlabel('Date')

    return fig
