#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Import Python Modules
import numpy as np
from datetime import datetime as _datetime, date

# Custom Modules
import pandas as pd
from risk_pylibrary.tools import config as cf


def clean_prices(df, print_missing_prices=False, verbose=True):
    """
    Price Data Cleaner. Input Dictionary should contain a key "prices" and that DataFrame should be be built as:
    index -  date object
    columns - ISINs
    values - prices
    """

    # Output
    out_dict = dict()

    # **********************************************************************************
    if verbose: print("Cleaning Weekend Days")
    df_new = _clean_weekends(df)

    # Create return dataframe
    rets = df_new.pct_change()

    # **********************************************************************************
    # Eliminate potential bank holiday
    out_dict['df_new'] = df_new[rets.sum(axis = 1) != 0]

    # **********************************************************************************
    # Check for potential corporate actions
    # Set return threshold
    rets_new = _clean_splits(rets, verbose=verbose)
    out_dict['rets_new'] = rets_new #[rets_new.sum(axis = 1) != 0]

    # **********************************************************************************
    # Check for NaNs
    if verbose: print("Checking for NaNs")
    out_dict['df_nans'] = _check_for_nans(rets_new, verbose=verbose)

    # **********************************************************************************
    # Print Missing Prices. Input DataFrame should be small < 10 columns
    if verbose and print_missing_prices:
        _print_missing_prices(out_dict['df_nans'], verbose=verbose)


    print('\n------------------------------------------------\n')

    return out_dict



def fill_missing_returns(rets, df_nans):
    """
    Finding missing returns throughout regression based on sample Msci indices.
    """

    from sklearn import linear_model
    # Define cut day:
    cut_dd = date(2018, 1, 18)
    tmp_rets = rets[cut_dd:]

    # Load Prices for Msci Short List:
    msci_short = cf.cache_info['msci_short']
    tmp_rets_short = tmp_rets[msci_short.INSTRUMENT_ID]

    missing_columns = ['IE00BWZN1T31']
    deter_data = pd.DataFrame(columns = ["Det" + name for name in missing_columns])

    for feature in missing_columns:
        tmp_rets_short[feature + '_imp'] = tmp_rets_short[feature]
        rets_short = _random_imputation(tmp_rets_short, feature)

    for feature in missing_columns:

        deter_data["Det" + feature] = tmp_rets_short[feature + "_imp"]
        parameters = list(set(tmp_rets_short.columns) - set(missing_columns) - {feature + '_imp'})

        # Create a Linear Regression model to estimate the missing data
        model = linear_model.LinearRegression()
        model.fit(X = tmp_rets_short[parameters], y = tmp_rets_short[feature + '_imp'])

        # Preserving the index of the missing data from the original dataframe
        model_prediction = model.predict(tmp_rets_short[parameters])[tmp_rets_short[feature].isnull()]
        deter_data.loc[tmp_rets_short[feature].isnull(), "Det" + feature] = model_prediction


    return deter_data


def _plot_reg_comparison(deter_data, rets_short, missing_columns):
    """
    Control Plot for single, fitted return series
    """
    import seaborn as sns
    from risk_pylibrary.tools import charting as CH

    sns.set()
    fig, axes = CH.subplots(nrows = 2, ncols = 2)
    fig.set_size_inches(8, 8)

    for index, variable in enumerate(missing_columns):
        sns.histplot(rets_short[variable].dropna(), kde = True, ax = axes[index, 0], stat='density', element='step', fill=False)
        sns.histplot(deter_data["Det" + variable], kde = True, ax = axes[index+1, 0], color='red', stat='density', element='step', fill=False)

        sns.boxplot(data=rets_short[variable], ax=axes[index, 1])
        sns.boxplot(data=deter_data["Det" + variable], ax=axes[index+1, 1])

    CH.tight_layout()

    return fig


def _random_imputation(rets, feature):

    df = rets.copy()
    number_missing = df[feature].isnull().sum()
    observed_values = df.loc[df[feature].notnull(), feature]
    df.loc[df[feature].isnull(), feature + '_imp'] = np.random.choice(observed_values, number_missing, replace = True)

    return df


def _clean_weekends(df):
    """
    Support function to clean_prices()
    --> cleans weekends based on weekday() function
    """
    # **********************************************************************************
    # Check for Weekend Days
    df_new = df.copy()
    df_new['weekday'] = df_new.index
    df_new['weekday'] = df_new['weekday'].apply(lambda x: x.weekday())
    # Slice out weekend days 5 = saturday, 6 = sunday
    df_new = df_new[~df_new['weekday'].isin([5, 6])]
    df_new = df_new.drop('weekday', axis = 1)

    return df_new


def _check_for_nans(df, verbose=True):
    """
    Support function to clean_prices()
    --> Checks for NaNs. Output can be used with missingno:

    import missingno as mno
    mno.matrix(df_nans.iloc[:,2:4], figsize = (20, 6),color=(0.27, 0.52, 1.0))
    """

    # **********************************************************************************
    # Check for NaNs
    df_nans = pd.DataFrame(index = df.index, columns = df.columns)
    topic_count = 1
    print('**********************************************************\n')
    if verbose: print('%s. Searching for Missing prices\n'%topic_count)
    count = 0
    print("\t\t Reassigning NaN %s columns"%len(df.columns))
    for col in df.columns:
        if verbose:
            if count%250 == 0: print("\t\t\t Screened %s columns"%count)
        # Define first and last valid index
        first_idx = df[col].first_valid_index()
        last_idx = df[col].last_valid_index()

        tmp = df[[col]][first_idx:last_idx]
        # Assign zero where prices are present
        df_nans[col].loc[tmp[~tmp[col].isnull()].index] = 0
        # Assign zero prior to first index
        if first_idx: df_nans[col].loc[:first_idx].iloc[:-1] = 0
        count += 1

    return df_nans


def _print_missing_prices(df_nans):
    """
    Support function to clean_prices()
    --> Simply prints missing prices. Convenient, if dataframe is small. Halts if DataFrame is to big.
    """
    # Print Results:
    print('**********************************************************\n')
    if len(df_nans.columns) <= 10:
        print('Missing Prices for these securities:\n')
        print(f"\t{'Symbol':16} {'Date':12}")
        for k_nan in df_nans.columns:
            tmp = df_nans[k_nan]
            tmp = tmp[tmp.isnull().values]
            count = 0
            for j in tmp.index:
                if count > 0:
                    print(f"\t{'':16} {str(j):12}")
                else:
                    print(f"\t{k_nan:16} {str(j):12}")
                count += 1

        print('\nSolution: front filling with prices as of T-1')
    else:
        print('Missing Prices exceed console printing capabilities. Check output\n')
    print('**********************************************************\n')


def _clean_splits(rets, verbose=True):
    """
    Support function to clean_prices()
    --> Checks for Splits and reverse splits
    """
    rets_new = rets.copy()
    rets_limit = 0.5
    if verbose:
        print('Check for potential corporate actions:\n')
        print(f"\t{'Symbol':16} {'Date':12} {'Price Return':12}")
    for k_corp in rets.columns:
        # Skipping Penny Stocks as those tend to have high price changes
        # if df[k_corp].mean() >= 1:
        tmp = rets_new[k_corp].dropna()
        tmp = tmp[(tmp.values <= -1 * rets_limit) | (tmp.values >= rets_limit)]
        if tmp.empty is False:
            count = 0
            for j in tmp.index:
                if count > 0:
                    print(f"\t{'':16} {str(j):12} {str(np.round(100*tmp.loc[tmp.index[0]],2))+'%':5}")
                else:
                    print(f"\t{k_corp:16} {str(j):12} {str(np.round(100*tmp.loc[tmp.index[0]],2))+'%':5}")

                # Setting outliers to 0
                if rets_new.loc[j, k_corp] <= -1*rets_limit or rets_new.loc[j, k_corp] >= rets_limit:
                    if verbose: print('\tSetting Return to Null for %s at %s'%(k_corp, j))
                    rets_new.loc[j, k_corp] = np.nan
                count += 1

    return rets_new




def map_secs_description(df, fld=''):
    """
    Mapping Function for Securities Description
    """

    # Import Modules:
    from tools.snowflake_db import db_connection as db

    df = pd.read_pickle(fld)
    df = df.dropna(how = 'all', axis = 1)
    df = df.set_index('index')
    df = df[['symbol_yahoo', 'name_short', 'country', 'currency', 'sector', 'industry']]

    # Get Current Mappings
    secs_map = db.run_query(query='SELECT * FROM TEAMS_PRD.RISK_DATA.SECURITY_DESCRIPTION')

    # Define Mapping Dictionary
    dict_map = {'Germany':'dax',
                'Italy':'ftse_mib',
                'Spain':'ibex35',
                'France':'cac40',
                'United Kingdom': 'ftse100',
                'Austria': 'msci_europe',
                'Belgium': 'msci_europe',
                'Netherlands': 'msci_europe',
                'Denmark': 'msci_europe',
                'Norway': 'msci_europe',
                'Liechtenstein': 'msci_europe',
                'Monaco': 'msci_europe',
                'Jersey': 'msci_europe',
                'Greece': 'msci_europe',
                'Portugal': 'msci_europe',
                'Finland': 'msci_europe',
                'Sweden': 'msci_europe',
                'Malta': 'msci_europe',
                'Czech Republic': 'msci_eastern_europe',
                'Poland': 'msci_eastern_europe',
                'Canada':'msci_canada',
                'United States':'sp500',
                'Australia':'msci_australia',
                'Switzerland':'msci_switzerland',
                'Argentina': 'msci_emerging',
                'Brazil': 'msci_emerging',
                'Chile': 'msci_emerging',
                'Colombia': 'msci_emerging',
                'Mexico': 'msci_emerging',
                'Peru': 'msci_emerging',
                'Uruguay': 'msci_emerging',
                'Emerging':'msci_emerging',
                'Pakistan': 'msci_emerging',
                'South Korea': 'msci_emerging',
                'Turkey': 'msci_emerging',
                'Indonesia': 'msci_emerging',
                'India': 'msci_emerging',
                'Singapore': 'msci_emerging',
                'Philippines': 'msci_emerging',
                'Thailand': 'msci_emerging',
                'Israel': 'msci_emerging',
                'South Africa': 'msci_emerging',
                'Cayman Islands': 'sp500',
                'Vietnam': 'msci_emerging',
                'Russia': 'msci_eastern_europe',
                'Japan': 'nikkei225',
                'Hong Kong': 'msci_emerging',
                'China': 'msci_emerging',
                'Taiwan': 'msci_emerging',
                'New Zealand': 'msci_emerging',
                'Bermuda': 'sp500',
                }
