import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import boto3
import requests
from IPython.display import HTML, Image, display
from snowflake import connector


class OAuth(ABC):
    DEFAULT_INTERVAL = 5
    device_code = None
    verification_uri_complete = None
    interval = DEFAULT_INTERVAL
    client_id = None
    client_secret = None
    user_prompt_message = "Click me to authenticate"

    def auth(self):
        self.start_flow()

        display(
            HTML(
                f"<a target='_blank' href='{self.verification_uri_complete}'>{self.user_prompt_message}</a>"
            )
        )

        return self.wait_for_user()

    @abstractmethod
    def start_flow(self) -> None:
        pass

    @abstractmethod
    def get_token(self) -> str:
        pass

    def wait_for_user(self) -> str:
        access_token = None

        while not access_token:
            try:
                access_token = self.get_token()
                display(
                    Image(url="https://media.giphy.com/media/12NUbkX6p4xOO4/giphy.gif")
                )
                print("Success!!!")
            except requests.exceptions.RequestException:
                time.sleep(self.interval)
                pass

        return access_token


class AWSOAuth(OAuth):
    BASE_URL = "https://oidc.eu-central-1.amazonaws.com"

    def get_session(self, role_name, account_id, region="eu-central-1"):
        access_token = self.auth()
        sso = boto3.session.Session(region_name=region).client("sso")
        response = sso.get_role_credentials(
            roleName=role_name, accountId=account_id, accessToken=access_token
        )
        creds = response.get("roleCredentials")

        session = boto3.session.Session(
            aws_access_key_id=creds.get("accessKeyId"),
            aws_secret_access_key=creds.get("secretAccessKey"),
            aws_session_token=creds.get("sessionToken"),
            region_name=region,
        )

        return session

    def start_flow(self) -> None:
        register_url = f"{self.BASE_URL}/client/register"
        register_form = {"clientName": "sagemaker", "clientType": "public"}
        register_response = requests.post(register_url, json=register_form)
        register_response.raise_for_status()

        self.client_id = register_response.json().get("clientId", None)
        self.client_secret = register_response.json().get("clientSecret", None)

        authorize_url = f"{self.BASE_URL}/device_authorization"
        authorize_form = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "startUrl": "https://traderepublic.awsapps.com/start",
        }
        authorize_response = requests.post(authorize_url, json=authorize_form)
        authorize_response.raise_for_status()

        self.interval = authorize_response.json().get("interval", self.DEFAULT_INTERVAL)

        self.device_code = authorize_response.json().get("deviceCode", None)

        if not self.device_code:
            raise ValueError("ERROR: No device")

        self.verification_uri_complete = authorize_response.json().get(
            "verificationUriComplete", None
        )

        if not self.verification_uri_complete:
            raise ValueError("ERROR: No user url")

    def get_token(self) -> str:
        token_url = f"{self.BASE_URL}/token"
        form = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "grantType": "urn:ietf:params:oauth:grant-type:device_code",
            "deviceCode": self.device_code,
        }
        response = requests.post(token_url, json=form)
        response.raise_for_status()

        return response.json().get("accessToken")


class SnowflakeOAuth(OAuth):
    BASE_URL = "https://traderepublic.okta.com/oauth2/aus2rdvxbpg37aOJ9417"
    CLIENT_ID = "0oa2ryadtgu7XnM80417"
    HEAD = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    def start_flow(self) -> None:
        form = {"client_id": self.CLIENT_ID, "scope": "offline_access session:role-any"}
        response = requests.post(
            f"{self.BASE_URL}/v1/device/authorize",
            data=form,
            headers=SnowflakeOAuth.HEAD,
        )
        response.raise_for_status()

        self.device_code = response.json().get("device_code", None)

        if not self.device_code:
            raise ValueError("ERROR: No device")

        self.verification_uri_complete = response.json().get(
            "verification_uri_complete", None
        )
        if not self.verification_uri_complete:
            raise ValueError("ERROR: No user url")

        self.interval = response.json().get("interval", self.DEFAULT_INTERVAL)

    def get_token(self) -> str:
        token_url = f"{self.BASE_URL}/v1/token"
        form = {
            "client_id": self.CLIENT_ID,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": self.device_code,
        }
        response = requests.post(token_url, data=form, headers=self.HEAD)
        response.raise_for_status()

        return response.json().get("access_token")


@dataclass
class Snowflake:
    user: str
    role: str
    warehouse: str
    database: str
    schema: str
    access_token: str

    def query(self, sql, warehouse=None, database=None, schema=None):
        with connector.connect(
            user=self.user,
            account="gm68377.eu-central-1",
            authenticator="oauth",
            token=self.access_token,
            warehouse=warehouse or self.warehouse,
            database=database or self.database,
            schema=schema or self.schema,
            role=self.role,
            region="eu-central-1",
        ) as con:
            # execute query, fetch all results from cursor and deliver as a pandas dataframe
            df = con.cursor().execute(sql).fetch_pandas_all()

            return df
