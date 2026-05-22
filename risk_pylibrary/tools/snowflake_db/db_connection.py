#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import pandas as pd
from snowflake import connector
from snowflake.connector import connect
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from warnings import warn
from datetime import date
from datetime import datetime as _datetime
import numpy as np
import getpass as _getpass


# Loading .env information:
current_user = _getpass.getuser()
print("\n      Loading environment variables for Snowflake connection for user: %s" % current_user)
# Check if the user is 'root' or not, and load the appropriate .env file
# If the user is not 'root', load the .env file from the user's home directory
# If the user is 'root', use the environment variables directly
dotenv_loaded = False
if current_user != 'root':
    load_dotenv('/Users/' + current_user + '/TR_env/log_sf_role.env')
    print("     \t\tlog_sf_role.env file found. Picking up user credentials for Snowflake connection.\n")
    # Load config from risk_pylibrary
    from tools import config as CF
    dotenv_loaded = True
elif current_user == 'root':
    print("     \tNo log_sf_role.env file found. Falling back to environment variables.\n")
    account_sf = os.environ["SNOWFLAKE_ACCOUNT"]
    user_sf = os.environ["SNOWFLAKE_USERNAME"]
    password_sf = os.environ["SNOWFLAKE_PASSWORD"]
    database_sf = os.environ["SNOWFLAKE_DATABASE"]
    warehouse_sf = os.environ["SNOWFLAKE_WAREHOUSE"]



def _load_env_var(KEY):
    """
    Helper function to make variable import more transparent
    """

    value = os.environ.get(KEY)
    if not value:
        raise KeyError((f"No variable '{KEY}' found. " +
                         "Have you configured the log_sf_role.env file?"))

    return value


def get_frontend_db():

    FRONTEND_URI = (
        "postgresql+psycopg2://"
        f"{_load_env_var('TR_FRONTEND_USER')}"
        ":"
        "@"
        f"{_load_env_var('TR_FRONTEND_HOST')}"
        ":"
        f"{_load_env_var('TR_FRONTEND_PORT')}"
        "/"
        f"{_load_env_var('TR_FRONTEND_DATABASE')}"
    )

    return create_engine(FRONTEND_URI)


def load_query(query_path: str, verbose=False, load_as_string=True):
    """Allows to return the query as a SQLAlchemy object to avoid issues with the
    SQL wildcard '%'"""
    with open(query_path, "r") as f:
        query = f.read()
        if verbose:
            print(query)
        if load_as_string:
            return query
        else:
            return text(query)


def get_production_etl_v1():
    PRODUCTION_ETL_URI = (
        "postgresql+psycopg2://"
        f"{_load_env_var('PRODUCTION_DWH_V1_USER')}"
        ":"
        f"{_load_env_var('PRODUCTION_DWH_V1_PASSWORD')}"
        "@"
        f"{_load_env_var('PRODUCTION_DWH_V1_HOST')}"
        ":"
        f"{_load_env_var('PRODUCTION_DWH_V1_PORT')}"
        "/"
        f"{_load_env_var('PRODUCTION_DWH_V1_DATABASE')}"
    )
    return create_engine(PRODUCTION_ETL_URI)


def _set_snowflake_conn():
    """Defined a Snowflake connector"""
    warn(
        "This method will be deprecated in future releases due to SSO rollout. Please use '_set_snowflake_conn_sso()' instead!",
        DeprecationWarning,
    )
    conn = connect(
        user=_load_env_var("SNOWFLAKE_USER"),
        password=_load_env_var("SNOWFLAKE_PASSWORD"),
        account=_load_env_var("SNOWFLAKE_ACCOUNT"),
        warehouse=_load_env_var("SNOWFLAKE_WAREHOUSE"),
        database=_load_env_var("SNOWFLAKE_DATABASE"),
        role=_load_env_var("SNOWFLAKE_ROLE"),
    )
    return conn


def _set_snowflake_conn_sso(fmt_engine, **kwargs):
    """Defines a Snowflake connector with SSO auth"""
    email_address = None
    try:
        email_address = _load_env_var("%s_SNOWFLAKE_EMAIL_ADDRESS"%fmt_engine)
    except KeyError:
        print("Failed to retrieve the email address from the env vars")
        email_address = input('Please input your TR email address and press Enter to login to Snowflake via Okta: ')


    if email_address:
        from snowflake.connector import connect
        from snowflake.sqlalchemy import URL
        from sqlalchemy import create_engine

        conn = connect(
            account=_load_env_var("%s_SNOWFLAKE_ACCOUNT" % fmt_engine),
            user=email_address,
            authenticator="externalbrowser",
            database=_load_env_var("%s_SNOWFLAKE_DATABASE" % fmt_engine),
            warehouse=_load_env_var("%s_SNOWFLAKE_WAREHOUSE" % fmt_engine if kwargs['overwrite_role'] is None
                                    else kwargs['overwrite_role']),
            role=_load_env_var("%s_SNOWFLAKE_ROLE" % (fmt_engine if kwargs['overwrite_role'] is None
                                                      else kwargs['overwrite_role'])))

        return conn
    else:
        raise ValueError("Could not find an email address. Please set the 'SNOWFLAKE_EMAIL_ADDRESS' variable in ~/.data_team_utils/data_team_utils.env")


def load_sql(query, chunksize=None):
    warn(
        "This method will be deprecated in future releases. Please use 'run_query' instead!",
        DeprecationWarning,
    )
    return run_query(query, chunksize)


def run_query(query, chunksize=None, fmt_engine='RISK', overwrite_role=None, verbose=True):
    """
    Runs a query on the Snowflake connection
    """

    if dotenv_loaded is False:

        # Used for AirFlow Jobs
        conn = connector.connect(
                user=user_sf,
                password=password_sf,
                account=account_sf,
                database=database_sf,
                warehouse=warehouse_sf)

        try:
            cur = conn.cursor()
            cur.execute(query)
            df = pd.read_sql(query, conn)
        finally:
            cur.close()
            conn.close()

    else:
        if CF.sf_conn == {}:
            CF.sf_conn = _set_snowflake_conn_sso(fmt_engine, overwrite_role=overwrite_role)

        # Suppress pandas SQLAlchemy warning when using Snowflake connector
        import warnings

        if chunksize:
            df = pd.DataFrame()
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=UserWarning, message='.*SQLAlchemy.*')
                for chunk in pd.read_sql(query, CF.sf_conn, chunksize=chunksize):
                    df = pd.concat([df, chunk])
        else:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=UserWarning, message='.*SQLAlchemy.*')
                df = pd.read_sql(query, CF.sf_conn)


    df.columns = map(str.lower, df.columns)

    if verbose:
        return df


def pandas2db(df, table, merge=False, replace=False, ignore=False):
    """
    Inserts df into table. Reset the index!
    """

    cols = df.columns
    types = [a.kind for a in df.dtypes]
    table_dummy = table + '_DUMMY' if merge else table

    if merge:
        print('\n\t ***** Smart Merge Initialised *****')
        try:
            run_query(query='CREATE TABLE %s CLONE %s'%(table_dummy, table))
        except:
            print("WARNING: Potential Issue with merging Data. Check: %s"%table_dummy)
            pass

    sql_qry = (('''insert overwrite''' if replace else '''insert''') +
               (''' ignore ''' if ignore else '''''')+' into '+ table_dummy + \
              ' ('+''','''.join(cols)+') values ')

    # Add values string
    values_str = ''
    for row in range(0, len(df)):
        values_str = values_str + '(' + ''','''.join(['''%s''']*len(cols)) + '),'

    sql_qry = sql_qry+values_str[:-1] # -1 excludes last comma at the end

    values_tuple = tuple()
    temp = df.values.tolist()
    for i in range(len(temp)):
        for j in range(len(temp[i])):
            if types[j] == 'f':
                if np.isnan(temp[i][j]): temp[i][j] = None
            if types[j] in ['M', 'O']:
                # Datetime kind or Python Objects, convert pandas timestamp or datetime to string
                if isinstance(temp[i][j], pd.Timestamp): temp[i][j] = str(temp[i][j])
                elif isinstance(temp[i][j], date): temp[i][j] = str(temp[i][j])
                elif isinstance(temp[i][j], _datetime): temp[i][j] = str(temp[i][j])
                else:
                    pass

        # Wrap in a tuple
        values_tuple += tuple(["'%s'"%k for k in temp[i]])

    if merge:

        print('\n\t\t Parsing data into dummy table: %s'%table_dummy)
        try:
            df_parse = run_query(sql_qry%values_tuple, fmt_engine='RISK')
            print(df_parse)
        except:
            print('ERROR: Parsing data')
            pass

        merge_qry = '''
        MERGE INTO %s as tgt_table USING %s as src_table on(%s) WHEN NOT MATCHED THEN insert(%s) values(%s)
        '''


        conditions = [f"tgt_table.{tgt_col} = src_table.{src_col}" for tgt_col,src_col in zip(list(df.columns), list(df.columns))]
        on_string = ' AND '.join(conditions)
        insert_string = ', '.join(str(k) for k in list(df.columns))
        values_string = ', '.join('src_table.'+str(k) for k in list(df.columns))

        # Recompiling the String
        merge_qry_adj = merge_qry%(table, table_dummy, on_string, insert_string, values_string)

        print('\n\t\t Merging data into target table: %s'%table)
        try:
            df_merge = run_query(query=merge_qry_adj, fmt_engine='RISK')
        except:
            print('ERROR: Merging data')
            pass

        print('\n\t\t Dropping dummy table: %s' % table_dummy)
        try:
            df_delete = run_query(query='DROP TABLE %s'%table_dummy)
        except:
            print('ERROR: Dropping Table')
            pass

        return df_parse, df_merge, df_delete

    else:
        return run_query(sql_qry%values_tuple, fmt_engine='RISK')



def joinpad(obj, sep=",", lpad="'", rpad=None):
    """
    concatenates elements of a list into a string with specified separator,
    optionally padding each element with given pad characters
    """
    if rpad is None: rpad = lpad
    return sep.join([lpad+o+rpad for o in obj])


def sqldate(ddate):
    """
    formats date in appropriate way for sql
    """
    if isinstance(ddate, _datetime):
        ddate_new = ddate.strftime("'%Y-%m-%d %H:%M:%S'")
    else:
        ddate_new = ddate.strftime("'%Y-%m-%d'")

    return ddate_new



