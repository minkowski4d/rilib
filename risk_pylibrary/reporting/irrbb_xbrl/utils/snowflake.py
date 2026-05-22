import sys
import pandas as pd
import snowflake.connector


def _set_snowflake_conn_sso(username, **kwargs):
    '''
    Defines a Snowflake connector with SSO auth
    '''
    conn = snowflake.connector.connect(
            user=username,
            account='GM68377.EU-CENTRAL-1',
            role='RISK',
            authenticator='externalbrowser'
            )

    return conn


def run_query(query: str, username, chunksize=None, verbose=True, **kwargs) -> pd.DataFrame:
    '''
    Runs a query on the Snowflake connection
    '''

    with _set_snowflake_conn_sso(username) as conn:
            if chunksize:
                df = pd.DataFrame()
                for chunk in pd.read_sql(query, conn, chunksize=chunksize):
                    df = pd.concat([df, chunk])
            else:
                df = pd.read_sql(query, conn)

    df.columns = map(str.lower, df.columns)

    if verbose:
        return df


def _set_snowflake_sensitive_conn_sso(username, **kwargs):
    '''
    Defines a Snowflake connector with SSO auth
    '''
    conn = snowflake.connector.connect(
            user=username,
            account='GM68377.EU-CENTRAL-1',
            role='RISK',
            authenticator='externalbrowser'
            )

    return conn


def run_sensitive_query(query: str, username, chunksize=None, verbose=True, **kwargs) -> pd.DataFrame:
    '''
    Runs a query on the Snowflake connection
    '''

    with _set_snowflake_sensitive_conn_sso(username) as conn:
            if chunksize:
                df = pd.DataFrame()
                for chunk in pd.read_sql(query, conn, chunksize=chunksize):
                    df = pd.concat([df, chunk])
            else:
                df = pd.read_sql(query, conn)

    df.columns = map(str.lower, df.columns)

    if verbose:
        return df