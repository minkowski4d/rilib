"""
Data connectors to be used in the flows and notebooks
"""
# pylint: disable=R0913
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

#from metaflow import S3
from snowflake import connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd
import getpass as _getpass
from dotenv import load_dotenv


class SnowflakeWriteModes(Enum):
    """Supported writing modes for Snowflake Connector"""

    WRITE = "write"
    APPEND = "append"


@dataclass
class SnowflakeInteractiveConfig:
    """Configuration object required to activate the interactive mode"""

    email_address: str
    role: str = "RISK"
    account: str = "gm68377.eu-central-1"


class SnowflakeConnector:
    """Connector to read from and write to Snowflake"""

    allowed_write_modes = [m.value for m in SnowflakeWriteModes]

    def __init__(
        self,
        database: str,
        warehouse: str = "COMPLIANCE_AND_RISK__PIPELINES",
        user_config: Optional[SnowflakeInteractiveConfig] = None,
    ):
        """Instantiates the connector. Hint: do not pickle this class, rather
            instantiate it in each step

        Args:
            database (str): The database you want to query (e.g. TEAMS_PRD)
            warehouse (str, optional): The warehouse to use for querying.
                Defaults to "COMPLIANCE_AND_RISK__PIPELINES".
            user_config (SnowflakeInteractiveConfig, optional): object containing
                the required credentials for the interactive (outside of metaflow) auth
                with Snowflake
        """
        self.database = database
        self.warehouse = warehouse
        self.conn = self._get_snowflake_connector(user_config=user_config)
        self.cursor = self.conn.cursor()
        self.cursor.execute(f"use warehouse {warehouse}")

    def _get_snowflake_connector(
        self, user_config: Optional[SnowflakeInteractiveConfig] = None
    ):
        """SnowFlake connector that uses credentials from the environment"""
        if user_config:
            # Loading .env information:
            current_user = _getpass.getuser()
            try:
                load_dotenv('/Users/' + current_user + '/TR_env/log_sf_role.env')
            except:  # noqa: E722
                print("No log_sf_role.env file found. Please create it in your TR_env folder.")
            # run snowflake connector in interactive mode
            return connector.connect(
                user=user_config.email_address,
                account=user_config.account,
                authenticator="externalbrowser",
                warehouse=self.warehouse,
                database=self.database,
                role=user_config.role,
            )

        try:
            return connector.connect(
                user=os.environ.get("SNOWFLAKE_USERNAME"),
                password=os.environ.get("SNOWFLAKE_PASSWORD"),
                account=os.environ.get("SNOWFLAKE_ACCOUNT"),
                database=self.database,
            )
        except KeyError as e:
            raise Exception(
                "Missing environment variables for Snowflake connection. "
                "Please set SNOWFLAKE_USERNAME, SNOWFLAKE_PASSWORD, and SNOWFLAKE_ACCOUNT."
            ) from e

    def read_snowflake(
        self, query: str, warehouse: Optional[str] = None
    ) -> pd.DataFrame:
        """Runs a SELECT query against snowflake

        Args:
            query (str): the query to be executed
            warehouse (Optional[str], optional): Warehouse to override . Defaults to None.

        Returns:
            pd.DataFrame: _description_
        """
        if warehouse:
            self.cursor.execute(f"use warehouse {warehouse}")
        else:
            self.cursor.execute(f"use warehouse {self.warehouse}")

        # self.cursor.execute(query)
        # df = pd.DataFrame(self.cursor.fetch_pandas_all())
        df = pd.read_sql(query, self.conn)
        df.columns = [col.lower() for col in df.columns]
        return df

    def write_snowflake(
        self,
        df: pd.DataFrame,
        table_name: str,
        mode: Optional[SnowflakeWriteModes] = SnowflakeWriteModes.APPEND,
        schema: Optional[str] = "DATA_PRODUCTS_DEV",
        database: Optional[str] = None,
        **kwargs,
    ):
        """Helper method to write a pandas DataFrame to Snowflake

        Args:
            df (pd.DataFrame): The Dataframe to write to Snowflake
            table_name (str): Name of the database table
            mode (Optional[SnowflakeWriteModes], optional): Similar to file opening modes,
                can be "write" or "append". Defaults to SnowflakeWriteModes.APPEND.
            schema (Optional[str], optional): Name of the schema to write to.
                Defaults to "DATA_PRODUCTS_DEV".
            database (Optional[str], optional): Name of the database to write to.
                Defaults to None - in which case the database used during initialization is used.
            kwargs
                auto_create_table (bool):
                    Defafaults to True. If True, the table will be
                    dropped and created.

        Raises:
            ValueError: When the mode provided is not "append" or "write"

        Returns:
            _type_: _description_
        """
        auto_create_table = kwargs.get("auto_create_table", True)

        df = df.copy(deep=False)

        if mode not in self.allowed_write_modes:
            raise ValueError(
                "Invalid 'mode' value: "
                + f"provided {mode} but must be one of {self.allowed_write_modes}"
            )

        write_database = database if database else self.database

        # Because SnowFlake default is uppercase
        df.columns = [column.upper() for column in df.columns]

        # TODO: check if we can remove this code
        self.cursor.execute(f"USE SCHEMA {schema}")

        # Write the data from the pd.DataFrame to the table named "customers".
        success, nchunks, nrows, _ = write_pandas(
            conn=self.conn,
            df=df,
            table_name=table_name,
            database=write_database,
            schema=schema,
            auto_create_table=auto_create_table,
            overwrite=mode == SnowflakeWriteModes.WRITE.value,
            quote_identifiers=False,
        )

        return success, nchunks, nrows

    def _run_query(self, query: str, warehouse: Optional[str] = None) -> None:
        """Utility to execute a query on the database and returns nothing."""
        if warehouse:
            self.cursor.execute(f"use warehouse {warehouse}")
        else:
            self.cursor.execute(f"use warehouse {self.warehouse}")

        self.cursor.execute(query)

