"""
Simplified Rule-Based Margin Engine
====================================
Implements the framework described in margin_methodology_simple.tex:

  LTV_t = L_t / MV_t  <=  1 - h_phase

where h_phase is the applicable margin rate (IM / MM / overnight) for the
asset class.  The haircut IS the margin requirement — no separate ACV step.

Margin rate calibration via GBM Monte Carlo:

  h_im  — calibrated from close-to-close returns  (full overnight + intraday risk)
  h_mm  — calibrated from open-to-close returns   (intraday risk only; MM phase)
  h_on  — calibrated from close-to-open returns   (overnight gap risk; EOD add-on)

Rationale
---------
The close-to-close return decomposes as:

    r(C→C)  =  r(C→O)  +  r(O→C)
                overnight    intraday

At position open the customer is exposed to both components before the first
monitoring check → h_im uses C→C sigma.  Once in the MM phase, monitoring is
continuous from market open, so only the intraday component is a forward risk
→ h_mm uses O→C sigma.  The overnight add-on h_on covers the gap component and
is calibrated from C→O sigma.

Usage
-----
    from projects.margin_trading.src.margin_engine_simplified import (
        SimplifiedMarginEngine
    )

    params = pd.DataFrame({
        "mu_cc":      [0.05, 0.08],   # annualised drift (C→C)
        "sigma_cc":   [0.20, 0.35],   # annualised C→C volatility
        "sigma_oc":   [0.15, 0.27],   # annualised O→C volatility
        "sigma_co":   [0.13, 0.22],   # annualised C→O volatility
        "h_floor_im": [0.10, 0.20],   # minimum IM rate (optional)
        "h_floor_mm": [0.05, 0.10],   # minimum MM rate (optional)
        "h_floor_on": [0.02, 0.05],   # minimum overnight rate (optional)
    }, index=["AAPL", "TSLA"])

    engine = SimplifiedMarginEngine(confidence=0.99, n_sim=10_000)
    rates  = engine.calibrate(params)

    # Check opening (IM phase)
    check  = engine.check_opening(
        market_value=15_000, loan=10_000,
        h_im=rates.loc["TSLA", "h_im"],
        h_on=rates.loc["TSLA", "h_on"],
    )

    # Monitor intraday (MM phase)
    status = engine.monitor(
        market_value=13_500, loan=10_000,
        h_phase=rates.loc["TSLA", "h_mm"],
        h_on=rates.loc["TSLA", "h_on"],
        phase="mm",
    )
    print(status)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PositionStatus:
    """Result of a single LTV check."""
    ltv:       float
    ltv_limit: float
    phase:     str       # "im" | "mm"
    overnight: bool
    breach:    bool
    shortfall: float     # cash the customer must post to clear the breach

    def __str__(self) -> str:
        tag = "BREACH" if self.breach else "OK"
        return (
            f"[{tag}]  LTV={self.ltv:.1%}  limit={self.ltv_limit:.1%}  "
            f"phase={self.phase}{'(overnight)' if self.overnight else ''}  "
            f"shortfall={self.shortfall:,.2f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GBM Monte Carlo calibration
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_gbm(
    mu: float,
    sigma: float,
    n_sim: int,
    seed: Optional[int],
) -> np.ndarray:
    """
    Simulate N 1-day simple returns under GBM (Wiener process):

        ln(S_1/S_0) = (mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z,  Z ~ N(0,1)

    with dt = 1/252.  Returns simple returns: exp(log_return) - 1.

    sigma should be the annualised volatility of the relevant return window
    (C→C, O→C, or C→O) so the simulation captures the correct risk horizon.
    """
    dt = 1.0 / 252.0
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_sim)
    log_returns = (mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z
    return np.expm1(log_returns)


def simulate_gbm_batch(params: pd.DataFrame) -> pd.DataFrame:
    """
    Run GBM simulations for a batch of instruments.

    Parameters
    ----------
    params : DataFrame indexed by instrument_id with columns:
                mu     annualised drift
                sigma  annualised volatility
                n_sim  number of simulated paths
                seed   RNG seed (use NaN / None for non-deterministic)

    Returns
    -------
    DataFrame indexed by instrument_id with one column per simulation path
    (columns 0 … max(n_sim)-1).  Instruments with fewer paths have NaN in
    the extra columns.

    Example
    -------
        params = pd.DataFrame({
            "mu":    [0.05, 0.08],
            "sigma": [0.20, 0.35],
            "n_sim": [10_000, 10_000],
            "seed":  [42, 42],
        }, index=["AAPL", "TSLA"])

        sim = simulate_gbm_batch(params)
        # sim.loc["TSLA"] contains 10_000 simulated 1-day simple returns
    """
    required = {"mu", "sigma", "n_sim"}
    missing  = required - set(params.columns)
    if missing:
        raise ValueError(f"params DataFrame is missing columns: {missing}")

    max_paths = int(params["n_sim"].max())
    results   = {}

    for isin, row in params.iterrows():
        seed = None if pd.isna(row.get("seed", np.nan)) else int(row["seed"])
        returns = _simulate_gbm(
            mu=float(row["mu"]),
            sigma=float(row["sigma"]),
            n_sim=int(row["n_sim"]),
            seed=seed,
        )
        # pad shorter series with NaN so all rows have the same length
        padded = np.full(max_paths, np.nan)
        padded[:len(returns)] = returns
        results[isin] = padded

    return pd.DataFrame(results, index=range(max_paths)).T


def _var_from_mc(
    mu: float,
    sigma: float,
    confidence: float,
    n_sim: int,
    h_floor: float,
    seed: Optional[int],
    label: str,
) -> dict:
    """
    Run GBM simulation and extract the VaR quantile as a margin rate.

        h = max(h_floor,  -quantile(returns, 1 - confidence))

    Returns a dict with h, var_raw (before floor), sigma_1d, floor_binding.
    """
    returns  = _simulate_gbm(mu, sigma, n_sim, seed)
    var_raw  = float(-np.quantile(returns, 1.0 - confidence))
    h        = float(max(h_floor, var_raw))
    sigma_1d = sigma / np.sqrt(252.0)
    return {
        f"h_{label}":             round(h, 4),
        f"var_1d_{label}":        round(var_raw, 4),
        f"sigma_1d_{label}":      round(sigma_1d, 6),
        f"floor_binding_{label}": var_raw < h_floor,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class SimplifiedMarginEngine:
    """
    Simplified rule-based margin engine.

    Three margin rates are calibrated independently via GBM Monte Carlo,
    each using the volatility of the relevant return window:

        h_im  ← C→C sigma  (close-to-close; IM phase, day 0)
        h_mm  ← O→C sigma  (open-to-close;  MM phase, day 1+)
        h_on  ← C→O sigma  (close-to-open;  overnight add-on)

    The LTV limits follow directly:

        intraday IM  :  LTV ≤ 1 - h_im
        intraday MM  :  LTV ≤ 1 - h_mm
        overnight IM :  LTV ≤ 1 - h_im - h_on
        overnight MM :  LTV ≤ 1 - h_mm - h_on

    Parameters
    ----------
    confidence     : VaR confidence level for all three calibrations (default 0.99)
    n_sim          : GBM paths per instrument (default 10_000)
    seed           : RNG seed (default 42; None = non-deterministic)
    """

    def __init__(
        self,
        confidence: float = 0.99,
        n_sim:      int   = 10_000,
        seed:       Optional[int] = 42,
    ):
        self.confidence = confidence
        self.n_sim      = n_sim
        self.seed       = seed

    # ── 1. Calibrate all three rates ─────────────────────────────────────────

    def calibrate(self, params: pd.DataFrame) -> pd.DataFrame:
        """
        Calibrate h_im, h_mm and h_on for each instrument via GBM Monte Carlo.

        Parameters
        ----------
        params : DataFrame indexed by instrument_id.

            Required columns:
                sigma_cc   annualised close-to-close volatility
                sigma_oc   annualised open-to-close volatility
                sigma_co   annualised close-to-open volatility

            Optional columns (defaults shown):
                mu_cc      annualised drift for C→C simulation  (default 0.0)
                mu_oc      annualised drift for O→C simulation  (default 0.0)
                mu_co      annualised drift for C→O simulation  (default 0.0)
                h_floor_im minimum IM rate                      (default 0.10)
                h_floor_mm minimum MM rate                      (default 0.05)
                h_floor_on minimum overnight rate               (default 0.02)

        Returns
        -------
        DataFrame indexed by instrument_id with columns:
            sigma_cc, sigma_oc, sigma_co,
            h_im, var_1d_im, sigma_1d_im, floor_binding_im,
            h_mm, var_1d_mm, sigma_1d_mm, floor_binding_mm,
            h_on, var_1d_on, sigma_1d_on, floor_binding_on,
            ltv_limit_im, ltv_limit_mm,
            ltv_limit_im_overnight, ltv_limit_mm_overnight,
            max_leverage_intraday, max_leverage_overnight
        """
        required = {"sigma_cc", "sigma_oc", "sigma_co"}
        missing  = required - set(params.columns)
        if missing:
            raise ValueError(f"params DataFrame is missing columns: {missing}")

        records = []
        for isin, row in params.iterrows():
            mu_cc = float(row.get("mu_cc", 0.0))
            mu_oc = float(row.get("mu_oc", 0.0))
            mu_co = float(row.get("mu_co", 0.0))

            h_floor_im = float(row.get("h_floor_im", 0.10))
            h_floor_mm = float(row.get("h_floor_mm", 0.05))
            h_floor_on = float(row.get("h_floor_on", 0.02))

            # IM: calibrated from close-to-close volatility
            im = _var_from_mc(mu_cc, float(row["sigma_cc"]),
                               self.confidence, self.n_sim, h_floor_im, self.seed, "im")

            # MM: calibrated from open-to-close volatility
            mm = _var_from_mc(mu_oc, float(row["sigma_oc"]),
                               self.confidence, self.n_sim, h_floor_mm, self.seed, "mm")

            # Overnight: calibrated from close-to-open volatility
            on = _var_from_mc(mu_co, float(row["sigma_co"]),
                               self.confidence, self.n_sim, h_floor_on, self.seed, "on")

            h_im = im["h_im"]
            h_mm = mm["h_mm"]
            h_on = on["h_on"]

            rec = {
                "instrument_id": isin,
                "sigma_cc":      float(row["sigma_cc"]),
                "sigma_oc":      float(row["sigma_oc"]),
                "sigma_co":      float(row["sigma_co"]),
                **im,
                **mm,
                **on,
                "ltv_limit_im":           round(1.0 - h_im, 4),
                "ltv_limit_mm":           round(1.0 - h_mm, 4),
                "ltv_limit_im_overnight": round(1.0 - h_im - h_on, 4),
                "ltv_limit_mm_overnight": round(1.0 - h_mm - h_on, 4),
                "max_leverage_intraday":  round(1.0 / h_im, 2),
                "max_leverage_overnight": round(1.0 / (h_im + h_on), 2),
            }
            records.append(rec)

        return pd.DataFrame(records).set_index("instrument_id")

    # ── 2. Opening check ──────────────────────────────────────────────────────

    def check_opening(
        self,
        market_value:    float,
        loan:            float,
        h_im:            float,
        h_on:            float = 0.0,
        check_overnight: bool  = True,
    ) -> dict:
        """
        Check whether a new position may be opened (IM phase, t = 0).

        Returns LTV, pass/fail flags, minimum equity, maximum loan,
        max leverage, and overnight top-up required if h_on > 0.
        """
        ltv          = loan / market_value
        ltv_limit_im = 1.0 - h_im
        ltv_limit_on = 1.0 - h_im - h_on

        result = {
            "ltv":                   round(ltv,          4),
            "ltv_limit_im":          round(ltv_limit_im, 4),
            "passes_im":             bool(ltv <= ltv_limit_im),
            "min_equity":            round(h_im * market_value, 2),
            "max_loan_intraday":     round(ltv_limit_im * market_value, 2),
            "max_leverage_intraday": round(1.0 / h_im, 2),
        }
        if check_overnight and h_on > 0:
            result.update({
                "ltv_limit_im_overnight":  round(ltv_limit_on, 4),
                "passes_overnight":        bool(ltv <= ltv_limit_on),
                "min_equity_overnight":    round((h_im + h_on) * market_value, 2),
                "max_loan_overnight":      round(ltv_limit_on * market_value, 2),
                "max_leverage_overnight":  round(1.0 / (h_im + h_on), 2),
                "topup_required":          round(max(0.0, loan - ltv_limit_on * market_value), 2),
            })
        return result

    # ── 3. Intraday / overnight monitor ──────────────────────────────────────

    def monitor(
        self,
        market_value: float,
        loan:         float,
        h_phase:      float,
        h_on:         float = 0.0,
        phase:        str   = "mm",
        overnight:    bool  = False,
    ) -> PositionStatus:
        """
        Check LTV against the applicable limit for an open position.

        market_value : current MV_t = N * P_t  (MTM continuous)
        loan         : current outstanding loan L_t
        h_phase      : h_im (day 0) or h_mm (day 1+)
        h_on         : overnight add-on; pass 0.0 for intraday checks
        phase        : "im" or "mm" (label only)
        overnight    : True to apply h_on

            shortfall = max(0,  L - (1 - h_eff) * MV)
        """
        h_eff     = h_phase + (h_on if overnight else 0.0)
        ltv_limit = 1.0 - h_eff
        ltv       = loan / market_value
        breach    = bool(ltv > ltv_limit)
        shortfall = float(max(0.0, loan - ltv_limit * market_value))

        return PositionStatus(
            ltv=round(ltv, 4),
            ltv_limit=round(ltv_limit, 4),
            phase=phase,
            overnight=overnight,
            breach=breach,
            shortfall=round(shortfall, 2),
        )

    # ── 4. Liquidation price ──────────────────────────────────────────────────

    def liquidation_price(
        self,
        loan:      float,
        n_units:   float,
        h_phase:   float,
        h_on:      float = 0.0,
        overnight: bool  = False,
    ) -> float:
        """
        Price at which LTV equals the applicable limit — auto-liquidation trigger:

            P* = L / (N * (1 - h_eff))
        """
        h_eff = h_phase + (h_on if overnight else 0.0)
        return round(loan / (n_units * (1.0 - h_eff)), 4)

    # ── 5. Full position summary ──────────────────────────────────────────────

    def position_summary(
        self,
        market_value: float,
        loan:         float,
        n_units:      float,
        rates:        pd.Series,
    ) -> pd.DataFrame:
        """
        One-row DataFrame covering all LTV checks and liquidation prices
        for both phases, intraday and overnight.

        rates : a row from calibrate() output (must have h_im, h_mm, h_on)
        """
        h_im = float(rates["h_im"])
        h_mm = float(rates["h_mm"])
        h_on = float(rates["h_on"])
        ltv  = loan / market_value

        row = {
            "market_value":             market_value,
            "loan":                     loan,
            "equity":                   market_value - loan,
            "ltv":                      round(ltv, 4),
            # IM phase (C→C calibrated)
            "h_im":                     h_im,
            "ltv_limit_im":             round(1.0 - h_im, 4),
            "passes_im":                bool(ltv <= 1.0 - h_im),
            "liq_price_im":             self.liquidation_price(loan, n_units, h_im),
            "ltv_limit_im_overnight":   round(1.0 - h_im - h_on, 4),
            "passes_im_overnight":      bool(ltv <= 1.0 - h_im - h_on),
            "liq_price_im_overnight":   self.liquidation_price(loan, n_units, h_im, h_on, overnight=True),
            # MM phase (O→C calibrated)
            "h_mm":                     h_mm,
            "ltv_limit_mm":             round(1.0 - h_mm, 4),
            "passes_mm":                bool(ltv <= 1.0 - h_mm),
            "liq_price_mm":             self.liquidation_price(loan, n_units, h_mm),
            "ltv_limit_mm_overnight":   round(1.0 - h_mm - h_on, 4),
            "passes_mm_overnight":      bool(ltv <= 1.0 - h_mm - h_on),
            "liq_price_mm_overnight":   self.liquidation_price(loan, n_units, h_mm, h_on, overnight=True),
            # Overnight (C→O calibrated)
            "h_on":                     h_on,
            # Max leverage
            "max_leverage_intraday":    round(1.0 / h_im, 2),
            "max_leverage_overnight":   round(1.0 / (h_im + h_on), 2),
        }
        return pd.DataFrame([row])
