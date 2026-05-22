#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Import Modules
import pandas as pd
import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt


# Import Custom Modules
from tools.snowflake_db import db_connection as db





def get_data():
    """
    Function to retrieve bond data from Snowflake database
    :return: DataFrame with bond data
    """

    qry='''
    SELECT 
        b.report_date,
        b.instrument_id,
        b.name_short,
        b.close_mid_price_clean,
        p.close_ask_price_clean,
        p.close_bid_price_clean,
        b.maturity_date,
        b.years_to_maturity,
        b.coupon,
        b.yield_to_maturity as ytm_mid_price,
        CASE
            WHEN b.coupon IS NULL
            THEN DIV0((1 - p.close_ask_price_clean), b.years_to_maturity)
                / DIV0((1 + p.close_ask_price_clean), 2)
            WHEN b.coupon IS NOT NULL
            THEN (b.coupon + DIV0((1 - p.close_ask_price_clean), b.years_to_maturity))
                / DIV0((1 + p.close_ask_price_clean), 2)
            ELSE NULL
        END AS ytm_ask_price,
        IFF(ytm_mid_price<0,1,0) AS ytm_mid_filter,
        IFF(ytm_ask_price<0,1,0) AS ytm_ask_filter
    FROM
        teams_prd.risk_function_publish.pbl__risk_function_mrm_book_msl_bond_analytics AS b
    LEFT JOIN
        (SELECT 
            report_date,instrument_id,close_ask_price_clean,close_bid_price_clean 
        FROM teams_prd.risk_function_publish.pbl__risk_function_mrm_book_msl_prices) as p
    ON
        p.instrument_id = b.instrument_id  AND p.report_date = b.report_date
    WHERE
        DAYOFWEEK(p.report_date) not in (0,6,7)
    ORDER BY 1;
    '''

    df=db.run_query(query=qry)


    return df



def ytm_filter(df_orig):
    """
    Function to filter bonds with negative yields
    :param df: DataFrame with bond data
    :return: DataFrame with filters applied
    """

    # Convert to Polars DataFrame
    df=pl.from_pandas(df_orig)


    # Building Filters
    df_out = (
        df
        .sort(["instrument_id", "report_date"])

        # helper columns: previous value in time & first date with a '1'
        .with_columns([
            pl.col("ytm_ask_filter").shift(1).over("instrument_id").alias("prev_val"),
            (
                pl.when(pl.col("ytm_ask_filter") == 1)
                .then(pl.col("report_date"))
                .otherwise(None)
                .min()
                .over("instrument_id")
            ).alias("first_one_date"),
        ])

        # Highlight transitions where ytm_ask_filter goes from 1 to 0
        .with_columns([
            pl.when((pl.col("ytm_ask_filter") == 0) & (pl.col("prev_val") == 1))
            .then(1).otherwise(0)
            .alias("back_to_zero"),

        # Highlight all dates after the first occurrence of ytm_ask_filter == 1 per instrument
            pl.when(
                pl.col("first_one_date").is_not_null() &
                (pl.col("report_date") > pl.col("first_one_date"))   # use >= to drop T0 too
            ).then(1).otherwise(0)
            .alias("remove_after_first_one"),
        ])

        # keep or drop helpers as you prefer
        .drop("prev_val")
        .drop("first_one_date")
    )


    out = df_out.to_pandas()



    # Setting additional filters on years to maturity
    out['back_to_zero_3m'] = out[['years_to_maturity',
                                  'ytm_ask_filter']].apply(lambda row: 1 
                                                            if row['years_to_maturity'] <= 0.25 
                                                            and row['ytm_ask_filter'] == 1 
                                                            else 0, axis=1)
    out['back_to_zero_3m'] = out[['years_to_maturity',
                                  'ytm_ask_filter']].apply(lambda row: 1 
                                                            if row['years_to_maturity'] <= 0.5 
                                                            and row['ytm_ask_filter'] == 1 
                                                            else 0, axis=1)
    out['back_to_zero_3m'] = out[['years_to_maturity',
                                  'ytm_ask_filter']].apply(lambda row: 1 
                                                            if row['years_to_maturity'] <= 0.75 
                                                            and row['ytm_ask_filter'] == 1 
                                                            else 0, axis=1)

    return out



def plot_ytm_distribution(df_orig):
    """
    Function to plot the distribution of YTM mid and ask prices
    :param df: DataFrame with bond data
    :return: None
    """

    # Convert Polars -> Pandas (if not already)
    df_pd = df_orig[['ytm_mid_price','ytm_ask_price']].copy()

    # Create figure and axes
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot histograms on the same axes
    sns.histplot(df_pd["ytm_mid_price"], color="blue", label="ytm_mid_price",
                kde=True, bins=50, alpha=0.5, ax=ax)
    sns.histplot(df_pd["ytm_ask_price"], color="orange", label="ytm_ask_price",
                kde=True, bins=50, alpha=0.5, ax=ax)

    # Customize labels and layout
    ax.set_title("Distribution of YTM Mid and Ask Prices")
    ax.set_xlabel("Yield to Maturity (%)")
    ax.set_ylabel("Frequency")
    ax.legend()
    fig.tight_layout()

    return fig

def plot_ytm_kde(df):

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.kdeplot(df["ytm_mid_price"], label="ytm_mid_price", fill=True, alpha=0.4, bw_adjust=0.3, ax=ax)
    sns.kdeplot(df["ytm_ask_price"], label="ytm_ask_price", fill=True, alpha=0.4, bw_adjust=0.3, ax=ax)
    ax.set_title("KDE with Wider Bandwidth (bw_adjust=0.3)")
    ax.set_xlim(-0.5, 0.5) 
    ax.legend()
    plt.show()