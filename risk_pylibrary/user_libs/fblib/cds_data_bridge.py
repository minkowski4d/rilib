# investing_hist_fullrange.py
from __future__ import annotations
from curl_cffi import requests as cf_requests
from bs4 import BeautifulSoup
import pandas as pd
import re, time, random
from datetime import date, datetime, timedelta
from typing import Optional, Union, List

DATE_IN = Union[str, date, datetime]
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/123.0.0.0 Safari/537.36")

def _as_dt(d: DATE_IN) -> datetime:
    if isinstance(d, datetime): return d
    if isinstance(d, date): return datetime(d.year, d.month, d.day)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try: return datetime.strptime(d, fmt)
        except ValueError: pass
    raise ValueError(f"Unrecognized date: {d!r}")

def _fmt_mdy(d: datetime) -> str:
    return d.strftime("%m/%d/%Y")  # Ajax expects MM/DD/YYYY

def _retry_get(url: str, session=cf_requests, headers: Optional[dict]=None):
    headers = {"User-Agent": UA, **(headers or {})}
    for i in range(3):
        r = session.get(url, impersonate="chrome", headers=headers, timeout=30)
        if r.status_code == 200:
            return r
        if r.status_code == 403 and i < 2:
            time.sleep(1.1 + random.random())
            continue
        r.raise_for_status()
    raise RuntimeError("GET failed after retries")

def _retry_post(url: str, data: dict, referer: str, session=cf_requests):
    headers = {
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.investing.com",
        "Referer": referer,
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
    }
    for i in range(3):
        r = session.post(url, data=data, headers=headers, impersonate="chrome", timeout=30)
        if r.status_code == 200:
            return r
        if r.status_code == 403 and i < 2:
            time.sleep(1.2 + random.random())
            continue
        r.raise_for_status()
    raise RuntimeError("POST failed after retries")

def _extract_ids(html: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract curr_id (instrument id) and smlId if present.
    Either is enough, but curr_id is required for Ajax.
    """
    # Try multiple patterns for robustness
    patterns = [
        r'"curr_id"\s*:\s*"?(?P<curr>\d{3,10})"',
        r'curr_id\s*=\s*"?(?P<curr>\d{3,10})"',
        r'"pairId"\s*:\s*(?P<curr>\d{3,10})',
        r'pair_id\s*=\s*(?P<curr>\d{3,10})',
    ]
    curr_id = None
    for p in patterns:
        m = re.search(p, html)
        if m:
            curr_id = m.group("curr"); break

    sml_id = None
    for p in (r'"smlId"\s*:\s*"?(?P<sml>\d{3,10})"', r'smlId\s*=\s*"?(?P<sml>\d{3,10})"'):
        m = re.search(p, html)
        if m:
            sml_id = m.group("sml"); break

    # Hidden inputs fallback
    soup = BeautifulSoup(html, "html.parser")
    if not curr_id:
        for attr in ({"id": "curr_id"}, {"name": "curr_id"}, {"id": "pair_id"}, {"name": "pair_id"}):
            node = soup.find("input", attr)
            if node and node.get("value"):
                curr_id = node["value"]; break
    if not sml_id:
        node = soup.find("input", {"name": "smlID"}) or soup.find("input", {"id": "smlID"})
        if node and node.get("value"):
            sml_id = node["value"]

    return curr_id, sml_id

def _parse_hist_table(html_fragment: str) -> pd.DataFrame:
    soup = BeautifulSoup(html_fragment, "html.parser")
    # Pick the table with a Date header (ignore snapshot tables)
    target = None
    for t in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in t.find_all("th")]
        if any(h.lower() == "date" for h in headers):
            target = t; break
    if target is None:
        # Some responses may come as the new datatable DOM — reuse modern parser
        return _parse_modern_datatable(soup)

    headers = [th.get_text(strip=True) for th in target.find_all("th")]
    rows = []
    for tr in target.find_all("tr")[1:]:
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) == len(headers): rows.append(tds)

    df = pd.DataFrame(rows, columns=headers)
    return _clean_hist_df(df)

def _parse_modern_datatable(soup: BeautifulSoup) -> pd.DataFrame:
    container = soup.select_one("[class*='datatable_table__']")
    if not container:
        raise ValueError("No historical data table found in Ajax response.")
    # headers
    hdr = container.select("[role='columnheader']")
    headers = [h.get_text(strip=True) for h in hdr]
    if not headers or not any(h.lower() == "date" for h in headers):
        raise ValueError("Ajax/modern table without 'Date' header.")
    rows = []
    for rn in container.select("[role='row']"):
        cells = rn.select("[role='cell']")
        if not cells: continue
        vals = [c.get_text(strip=True) for c in cells]
        if len(vals) >= len(headers):
            rows.append(vals[:len(headers)])
    df = pd.DataFrame(rows, columns=headers)
    return _clean_hist_df(df)

def _clean_hist_df(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize typical columns: Date | Price | Open | High | Low | Change %
    colmap = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl == "date": colmap[c] = "date"
        elif "price" in cl or "yield" in cl: colmap[c] = "yield"
        elif cl == "open": colmap[c] = "open"
        elif cl == "high": colmap[c] = "high"
        elif cl == "low": colmap[c] = "low"
        elif "change" in cl and "%" in cl: colmap[c] = "change_pct"
        else: colmap[c] = c
    df = df.rename(columns=colmap)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    def num(x: str):
        if x is None: return None
        s = str(x).strip()
        if s in ("", "-", "—"): return None
        s = s.replace(",", "").replace("%", "")
        # handle EU decimals like 4,046
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})*,\d+", s):
            s = s.replace(".", "").replace(",", ".")
        return pd.to_numeric(s, errors="coerce")

    for c in df.columns:
        if c != "date":
            df[c] = df[c].map(num)

    order = [c for c in ("date", "yield", "open", "high", "low", "change_pct") if c in df.columns]
    df = df[order + [c for c in df.columns if c not in order]]
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df

class InvestingHistoricalClient:
    AJAX_URL = "https://www.investing.com/instruments/HistoricalDataAjax"

    def __init__(self, session=cf_requests):
        self.sess = session

    def _ajax_window(self, historical_url: str, curr_id: str,
                     start: datetime, end: datetime, interval: str) -> pd.DataFrame:
        payload = {
            "action": "historical_data",
            "curr_id": curr_id,
            "smlID": "0",
            "header": "",
            "st_date": _fmt_mdy(start),
            "end_date": _fmt_mdy(end),
            "interval": interval,      # Daily / Weekly / Monthly
            "sort_col": "date",
            "sort_ord": "ASC",
        }
        resp = _retry_post(self.AJAX_URL, payload, referer=historical_url, session=self.sess)
        return _parse_hist_table(resp.text)

    def get_history(self,
                    historical_url: str,
                    start_date: DATE_IN,
                    end_date: DATE_IN,
                    interval: str = "Daily",
                    chunk_days: int = 365) -> pd.DataFrame:
        """
        Pull full-range historical data using Ajax (with optional chunking).
        Falls back to parsing the on-page datatable if Ajax is unavailable.
        """
        sd, ed = _as_dt(start_date), _as_dt(end_date)
        if ed < sd:
            raise ValueError("end_date must be >= start_date")

        # Load page & extract IDs
        page = _retry_get(historical_url, session=self.sess)
        curr_id, _sml = _extract_ids(page.text)
        if not curr_id:
            # Fallback: parse only what’s visible on page (last N rows)
            soup = BeautifulSoup(page.text, "html.parser")
            container = soup.select_one("[class*='datatable_table__']") or soup.find("table")
            if not container:
                raise ValueError("Could not find instrument id nor a parseable table.")
            df = _parse_modern_datatable(soup) if container.name != "table" else _clean_hist_df(
                pd.read_html(str(container))[0]
            )
            return df[(df["date"] >= sd) & (df["date"] <= ed)].reset_index(drop=True)

        # Ajax path with chunking
        out: List[pd.DataFrame] = []
        cur_start = sd
        while cur_start <= ed:
            cur_end = min(cur_start + timedelta(days=chunk_days - 1), ed)
            df_chunk = self._ajax_window(historical_url, curr_id, cur_start, cur_end, interval)
            out.append(df_chunk)
            # polite pacing
            time.sleep(0.6 + random.random() * 0.4)
            cur_start = cur_end + timedelta(days=1)

        if not out:
            return pd.DataFrame(columns=["date"])
        df = pd.concat(out, ignore_index=True).drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        # Final clamp (just in case)
        return df[(df["date"] >= sd) & (df["date"] <= ed)].reset_index(drop=True)

if __name__ == "__main__":
    client = InvestingHistoricalClient()

    # Your CDS example (older than on-page table)
    cds_url = "https://www.investing.com/rates-bonds/jp-morgan-cds-5-year-usd-historical-data"
    cds = client.get_history(cds_url, "2015-01-01", "2020-12-31", interval="Daily", chunk_days=365)
    print(cds.head(), cds.tail(), len(cds), sep="\n\n")

    # Another example: U.S. 10Y yield
    u10y = "https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield-historical-data"
    df_u10y = client.get_history(u10y, "2025-01-01", "2025-12-31", interval="Daily", chunk_days=365)
    print(df_u10y.head(), df_u10y.tail(), len(df_u10y), sep="\n\n")
