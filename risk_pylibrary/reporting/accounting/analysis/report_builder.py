#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import base64
import io
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from jinja2 import Template
from weasyprint import HTML

from reporting.accounting.analysis.month_end_perf import trading_book_summary

OUTPUT_DIR = Path(__file__).parent

# ----------------------------------------------------------------------
# Colour palette
# ----------------------------------------------------------------------

C_BLUE   = '#2e6fad'
C_GREEN  = '#2ecc71'
C_RED    = '#e74c3c'
C_ORANGE = '#e67e22'
C_DARK   = '#1a2744'

_COLORS = [C_BLUE, C_RED, C_GREEN, C_ORANGE, C_DARK, '#9b59b6', '#1abc9c', '#e67e22']

# ----------------------------------------------------------------------
# Matplotlib style defaults
# ----------------------------------------------------------------------

plt.rcParams.update({
    'font.family':      'sans-serif',
    'font.size':        9,
    'axes.spines.top':  False,
    'axes.spines.right':False,
    'axes.grid':        True,
    'grid.color':       '#eeeeee',
    'grid.linewidth':   0.6,
    'figure.facecolor': 'white',
    'axes.facecolor':   'white',
})


# ----------------------------------------------------------------------
# Rendering helpers
# ----------------------------------------------------------------------

def _b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()


def _fmt_eur(ax, axis='y'):
    fmt = mticker.FuncFormatter(lambda x, _: f'{x:,.0f}')
    if axis == 'y':
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)


def _tbl(df, max_rows=None):
    df = df.reset_index()
    if max_rows:
        df = df.head(max_rows)
    return df.to_html(index=False, classes='data-table', border=0,
                      float_format=lambda x: f'{x:,.2f}')


# ----------------------------------------------------------------------
# Chart builders
# ----------------------------------------------------------------------

def _chart_asset_class(breakdown, edate):
    accounts = breakdown['sec_acc_no'].unique()
    n = len(accounts)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 4), sharey=False)
    if n == 1:
        axes = [axes]

    for ax, acct in zip(axes, accounts):
        sub = breakdown[breakdown['sec_acc_no'] == acct].copy()
        x = range(len(sub))
        ax.bar(x, sub['mkt_eur_long'],  label='Long',  color=C_GREEN, alpha=0.9)
        ax.bar(x, sub['mkt_eur_short'], label='Short', color=C_RED,   alpha=0.9)
        ax.set_xticks(list(x))
        ax.set_xticklabels(sub['instrument_type'], rotation=30, ha='right', fontsize=8)
        ax.set_title(str(acct), fontsize=9, color=C_DARK)
        _fmt_eur(ax)
        if ax is axes[0]:
            ax.legend(fontsize=8)

    fig.suptitle(f'Long / Short by Asset Class — {edate}', fontsize=10, color=C_DARK, y=1.02)
    fig.tight_layout()
    return _b64(fig)


def _chart_book_size(book, avg_gross, avg_net):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(book['report_date'], book['gross_book'], color=C_BLUE,   label='Gross Book', linewidth=1.5)
    ax.plot(book['report_date'], book['net_book'],   color=C_ORANGE, label='Net Book',   linewidth=1.5, linestyle='--')
    ax.axhline(avg_gross, color=C_BLUE,   linestyle=':', linewidth=1, alpha=0.7)
    ax.axhline(avg_net,   color=C_ORANGE, linestyle=':', linewidth=1, alpha=0.7)
    ax.annotate('Avg Gross', xy=(book['report_date'].iloc[0], avg_gross),
                color=C_BLUE, fontsize=7.5, va='bottom')
    ax.annotate('Avg Net',   xy=(book['report_date'].iloc[0], avg_net),
                color=C_ORANGE, fontsize=7.5, va='top')
    ax.set_title('Daily Gross / Net Book Size (EUR)', fontsize=10, color=C_DARK)
    ax.legend(fontsize=8)
    _fmt_eur(ax)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    fig.autofmt_xdate()
    fig.tight_layout()
    return _b64(fig)


def _chart_instrument_count(count):
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.fill_between(count['report_date'], count['n_instruments'],
                    color=C_BLUE, alpha=0.15)
    ax.plot(count['report_date'], count['n_instruments'],
            color=C_DARK, linewidth=1.4)
    ax.set_title('Daily Instrument Count', fontsize=10, color=C_DARK)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    fig.autofmt_xdate()
    fig.tight_layout()
    return _b64(fig)


def _chart_pnl(pnl):
    accounts = pnl['sec_acc_no'].unique()
    n = len(accounts)
    fig, axes = plt.subplots(n, 1, figsize=(10, 3.5 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, acct in zip(axes, accounts):
        sub = pnl[pnl['sec_acc_no'] == acct].sort_values('report_date')
        ax.bar(sub['report_date'], sub['rpnl'], color=C_GREEN, alpha=0.85, label='rPnL', width=0.8)
        ax2 = ax.twinx()
        ax2.plot(sub['report_date'], sub['upnl'].cumsum(),
                 color=C_RED, linewidth=1.4, label='uPnL (cum)')
        ax2.spines['top'].set_visible(False)
        _fmt_eur(ax)
        _fmt_eur(ax2)
        ax.set_title(f'Account {acct}', fontsize=9, color=C_DARK)
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc='upper left')

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    fig.autofmt_xdate()
    fig.suptitle('Realised PnL (bars) & Cumulative Unrealised PnL (line)',
                 fontsize=10, color=C_DARK, y=1.01)
    fig.tight_layout()
    return _b64(fig)


def _chart_risk(risk):
    accounts = risk['sec_acc_no'].unique()
    n = len(accounts)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 4), sharey=False)
    if n == 1:
        axes = [axes]

    for ax, acct in zip(axes, accounts):
        sub   = risk[risk['sec_acc_no'] == acct]
        codes = sub['code'].unique()
        for j, code in enumerate(codes):
            s = sub[sub['code'] == code].sort_values('report_date')
            ax.plot(s['report_date'], s['rm_value'],
                    label=code, color=_COLORS[j % len(_COLORS)], linewidth=1.2)
        ax.set_title(str(acct), fontsize=9, color=C_DARK)
        _fmt_eur(ax)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.legend(fontsize=7, ncol=2)

    fig.suptitle('Risk Metrics over Period', fontsize=10, color=C_DARK, y=1.02)
    fig.autofmt_xdate()
    fig.tight_layout()
    return _b64(fig)


def _chart_top_bottom(top_bottom):
    df = top_bottom.reset_index().sort_values('total_pnl')
    label  = df['name_short'].fillna(df['instrument_id'].astype(str))
    colors = [C_GREEN if v >= 0 else C_RED for v in df['total_pnl']]
    height = max(4, len(df) * 0.32)
    fig, ax = plt.subplots(figsize=(9, height))
    ax.barh(range(len(df)), df['total_pnl'], color=colors, alpha=0.9)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(label, fontsize=7.5)
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_title('Total PnL — Top / Bottom Performers (EUR)', fontsize=10, color=C_DARK)
    _fmt_eur(ax, axis='x')
    fig.tight_layout()
    return _b64(fig)


def _chart_volume(daily_vol):
    symbols = daily_vol['symbol'].unique()[:20]
    fig, ax = plt.subplots(figsize=(10, 4))
    for j, sym in enumerate(symbols):
        sub = daily_vol[daily_vol['symbol'] == sym].sort_values('booking_date')
        ax.plot(sub['booking_date'], sub['notional_volume'],
                label=str(sym), linewidth=1.1, color=_COLORS[j % len(_COLORS)])
    ax.set_title('Daily Notional Volume per Instrument (EUR)', fontsize=10, color=C_DARK)
    _fmt_eur(ax)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.legend(fontsize=7, ncol=2, loc='upper left')
    fig.autofmt_xdate()
    fig.tight_layout()
    return _b64(fig)


# ----------------------------------------------------------------------
# HTML template
# ----------------------------------------------------------------------

_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  @page {
    size: A4 landscape;
    margin: 2cm 1.5cm 1.5cm 1.5cm;
    @top-left   { content: element(page-header); }
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 7pt; color: #888; font-family: Helvetica, sans-serif;
    }
  }

  #page-header {
    position: running(page-header);
    background: #1a2744;
    color: white;
    padding: 5px 15px;
    font-size: 8pt;
    font-family: Helvetica, sans-serif;
    display: flex;
    justify-content: space-between;
  }

  body { font-family: Helvetica, Arial, sans-serif; color: #222; font-size: 9pt; }

  .cover {
    page-break-after: always;
    display: flex;
    flex-direction: column;
    justify-content: center;
    height: 14cm;
    padding: 2cm;
    border-left: 6px solid #1a2744;
  }
  .cover h1 { font-size: 28pt; color: #1a2744; margin: 0 0 12px; }
  .cover p  { font-size: 12pt; color: #2e6fad; margin: 4px 0; }

  .section { page-break-before: always; }
  .section:first-of-type { page-break-before: avoid; }

  h2 {
    font-size: 13pt; color: #1a2744; margin: 0 0 4px;
    border-bottom: 2px solid #2e6fad; padding-bottom: 4px;
  }
  h3 { font-size: 10pt; color: #2e6fad; margin: 14px 0 4px; }

  img { width: 100%; margin: 8px 0; }

  .data-table {
    width: 100%; border-collapse: collapse; font-size: 7.5pt; margin: 8px 0;
  }
  .data-table thead tr { background: #1a2744; color: white; }
  .data-table th { padding: 4px 6px; text-align: left; font-weight: bold; }
  .data-table td { padding: 3px 6px; }
  .data-table tbody tr:nth-child(even) { background: #f2f4f8; }
  .data-table tbody tr:hover            { background: #e3eaf5; }

  .two-col { display: flex; gap: 16px; }
  .two-col > div { flex: 1; }

  .caption { font-size: 7pt; color: #2e6fad; text-align: center; margin-top: -4px; }
</style>
</head>
<body>

<div id="page-header">
  <span>Trading Book Report</span>
  <span>{{ sdate }} → {{ edate }}</span>
</div>

<!-- COVER -->
<div class="cover">
  <h1>Trading Book Report</h1>
  <p>Period: {{ sdate }} — {{ edate }}</p>
  <p>Accounts: {{ accounts }}</p>
</div>

<!-- 1. ASSET CLASS BREAKDOWN -->
<div class="section">
  <h2>1. Asset Class Breakdown — {{ edate }}</h2>
  <img src="{{ chart_asset_class }}">
  <p class="caption">Market value in EUR — Long / Short by asset class per account</p>
  {{ tbl_breakdown }}
</div>

<!-- 2. BOOK SIZE -->
<div class="section">
  <h2>2. Daily Book Size</h2>
  <img src="{{ chart_book_size }}">
</div>

<!-- 3. INSTRUMENT COUNT -->
<div class="section">
  <h2>3. Daily Instrument Count</h2>
  <img src="{{ chart_count }}">
</div>

<!-- 4. P&L -->
<div class="section">
  <h2>4. Daily P&L</h2>
  <img src="{{ chart_pnl }}">
  <h3>P&L by ISIN (top 30 by rPnL)</h3>
  {{ tbl_pnl_isin }}
</div>

<!-- 5. RISK METRICS -->
<div class="section">
  <h2>5. Risk Metrics</h2>
  <img src="{{ chart_risk }}">
</div>

<!-- 6. TOP / BOTTOM PERFORMERS -->
<div class="section">
  <h2>6. Top / Bottom Performers</h2>
  <img src="{{ chart_top_bottom }}">
  <div class="two-col">
    <div>
      <h3>Top Performers</h3>
      {{ tbl_top }}
    </div>
    <div>
      <h3>Bottom Performers</h3>
      {{ tbl_bottom }}
    </div>
  </div>
</div>

{% if chart_volume %}
<!-- 7. TRADING VOLUME -->
<div class="section">
  <h2>7. Daily Trading Volume</h2>
  <img src="{{ chart_volume }}">
  {{ tbl_volume }}
</div>
{% endif %}

</body>
</html>
""")


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

def generate_report(sdate, edate, sec_acc_no=None, output_path=None,
                    fetch_cache=True, include_volume=True, verbose=True):
    """
    Generate an HTML → PDF trading book report.

    Args:
        sdate (date)          : Period start date
        edate (date)          : Period end date
        sec_acc_no (list)     : Account numbers (defaults to all in PARAMS_PNL)
        output_path (str)     : PDF output path (default: analysis/<edate>.pdf)
        fetch_cache (bool)    : Passed through to sub-functions
        include_volume (bool) : Include trading volume section
        verbose (bool)        : Print progress

    Returns:
        str: path to generated PDF
    """

    if sec_acc_no is None:
        sec_acc_no = []

    if output_path is None:
        output_path = str(OUTPUT_DIR / f'trading_book_{edate.strftime("%Y%m%d")}.pdf')

    if verbose:
        print('\n *** Fetching data ...')

    res = trading_book_summary(sdate, edate, sec_acc_no_list=sec_acc_no,
                               fetch_cache=fetch_cache, verbose=verbose)

    if verbose:
        print('\n *** Building charts ...')

    breakdown = res['asset_class_breakdown'].reset_index()
    book      = res['book_size']['daily'].reset_index()
    count     = res['instrument_count'].reset_index()
    pnl       = res['pnl_daily'].reset_index()
    pnl_isin  = res['pnl_by_isin'].reset_index()
    risk      = res['risk_metrics']
    top_bottom = res['top_bottom']

    daily_vol = res.get('daily_volume')
    if daily_vol is not None:
        daily_vol = daily_vol.reset_index()

    ctx = dict(
        sdate=sdate,
        edate=edate,
        accounts=', '.join(str(a) for a in (sec_acc_no or breakdown['sec_acc_no'].unique().tolist())),
        chart_asset_class = _chart_asset_class(breakdown, edate),
        chart_book_size   = _chart_book_size(book, res['book_size']['avg_gross'], res['book_size']['avg_net']),
        chart_count       = _chart_instrument_count(count),
        chart_pnl         = _chart_pnl(pnl),
        chart_risk        = _chart_risk(risk),
        chart_top_bottom  = _chart_top_bottom(top_bottom),
        chart_volume      = _chart_volume(daily_vol) if (include_volume and daily_vol is not None) else None,
        tbl_breakdown = _tbl(breakdown),
        tbl_pnl_isin  = _tbl(pnl_isin.sort_values('rpnl', ascending=False), max_rows=30),
        tbl_top       = _tbl(res['top'].reset_index()),
        tbl_bottom    = _tbl(res['bottom'].reset_index()),
        tbl_volume    = _tbl(
            daily_vol.groupby('symbol')[['notional_volume', 'n_trades', 'net_quantity']]
            .sum().sort_values('notional_volume', ascending=False).reset_index()
        ) if (include_volume and daily_vol is not None) else '',
    )

    if verbose:
        print('\n *** Rendering PDF ...')

    html = _TEMPLATE.render(**ctx)
    HTML(string=html, base_url=str(OUTPUT_DIR)).write_pdf(output_path)

    if verbose:
        print(f'\n *** Report saved → {output_path}')

    return output_path
