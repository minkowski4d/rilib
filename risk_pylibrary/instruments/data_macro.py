#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# cds_investing_curlcffi.py
from curl_cffi import requests as cf_requests
from bs4 import BeautifulSoup
import pandas as pd
import time

URL = "https://www.investing.com/rates-bonds/jp-morgan-cds-5-year-usd-historical-data"



def fetch_cds_spreads_wrapper(symbols=None, delay=20):


    df_cds_info = pd.DataFrame()
    
    return df_cds_info



def fetch_cds_investing_table(url: str, impersonate: str = "chrome") -> pd.DataFrame:
    """Fetch an Investing.com historical-data table via curl_cffi."""

    # Set the header for chrome
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    r = cf_requests.get(url, headers=headers, impersonate=impersonate, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Request failed ({r.status_code}): {r.text[:500]}")

    soup = BeautifulSoup(r.text, "html.parser")

    # Locate the main table
    table = soup.find("table")
    if table is None:
        raise ValueError("No table found. Cloudflare may still be blocking, or the structure changed.")

    # Parse rows
    data = []
    headers = [th.text.strip() for th in table.find_all("th")]
    for tr in table.find_all("tr")[1:]:
        cols = [td.text.strip() for td in tr.find_all("td")]
        if len(cols) == len(headers):
            data.append(cols)

    df = pd.DataFrame(data, columns=headers)

    # Clean columns
    for col in df.columns:
        if "Date" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            df[col] = (
                df[col]
                .replace({",": "", "%": ""}, regex=True)
                .replace("-", None)
            )
            df[col] = pd.to_numeric(df[col])

    return df







