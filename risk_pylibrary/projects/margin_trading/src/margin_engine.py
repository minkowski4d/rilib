"""
margin_engine.py — Trade Republic Margin Requirements Framework
==============================================================
Follows the Leveraged Purchase Customer End-to-End Flow (Sections D & E).

Input
-----
prices : pd.DataFrame
    Columns = instrument ISINs, index = dates (DatetimeIndex),
    at least 250 trading days of history.

Output
------
margin_rates : pd.Series
    Index = ISIN, values = IM as fraction of position value.
detail : dict
    Per-instrument breakdown: MRC, LC, CB, haircut, etc.

Phases
------
1  Collateral Assessment  (E.2)
2  Initial Margin         (D.2.1–D.2.6)
3  Trade Execution        (D.1.1 / E.3.2)   — stubs, needs customer data
4  Daily Monitoring       (D.1.3 / E.3.2–E.3.3) — stubs
5  LTV Limit Checks       (G.3.4)            — stubs
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

# ──────────────────────────────────────────────────────────────────────────────
# Constants (methodology defaults — override via MarginConfig)
# ──────────────────────────────────────────────────────────────────────────────

TRADING_DAYS_YEAR = 252
EWMA_LAMBDA = 0.94          # EWMA decay for current volatility estimate
LIQUIDATION_HORIZON = 5     # trading days (used in haircut scaling)

N_HIST_SCENARIOS = 750      # filtered historical scenarios (methodology)
N_STRESS_SCENARIOS = 250    # stressed (raw crisis) scenarios

RVAR_ALPHA_HIST = 0.95      # confidence level for the base VaR used in RVaR scaling
RVAR_ALPHA_STRESS = 0.90    # confidence level for stressed base VaR
RVAR_TARGET_CONF = 0.99     # target confidence for Robust VaR
STUDENT_T_DOF = 5           # degrees of freedom for Student-t scaling

W_STRESS = 0.5              # stress weight in MRC = max(RVaR_hist + CB, w_s * RVaR_stress)

# Correlation-Break clipping parameters (κ, Φ, ψ)
CB_KAPPA = 1.0
CB_PHI = 0.05               # floor: 5% of RVaR
CB_PSI = 0.30               # cap:  30% of RVaR

# Liquidity Component defaults
DIVERSITY_FACTOR_DEFAULT = 0.85   # DF(l) diversification factor for single-asset groups
LAMBDA_LIQUIDITY_DEFAULT = 1.0    # λ(i) days-to-liquidate scaling factor

# LTV monitoring thresholds (Section G.3.4)
LTV_MONITORING_LIMIT = 0.70
LTV_BREACH_LIMIT = 0.80
LTV_LIQUIDATION_LIMIT = 0.90


# ──────────────────────────────────────────────────────────────────────────────
# Configuration dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class MarginConfig:
    """Methodology parameters — all overridable."""
    trading_days_year: int = TRADING_DAYS_YEAR
    ewma_lambda: float = EWMA_LAMBDA
    liquidation_horizon: int = LIQUIDATION_HORIZON
    n_hist_scenarios: int = N_HIST_SCENARIOS
    n_stress_scenarios: int = N_STRESS_SCENARIOS
    rvar_alpha_hist: float = RVAR_ALPHA_HIST
    rvar_alpha_stress: float = RVAR_ALPHA_STRESS
    rvar_target_conf: float = RVAR_TARGET_CONF
    student_t_dof: float = STUDENT_T_DOF
    w_stress: float = W_STRESS
    cb_kappa: float = CB_KAPPA
    cb_phi: float = CB_PHI
    cb_psi: float = CB_PSI
    diversity_factor: float = DIVERSITY_FACTOR_DEFAULT
    lambda_liquidity: float = LAMBDA_LIQUIDITY_DEFAULT
    ltv_monitoring_limit: float = LTV_MONITORING_LIMIT
    ltv_breach_limit: float = LTV_BREACH_LIMIT
    ltv_liquidation_limit: float = LTV_LIQUIDATION_LIMIT
    # Target LTV used to compute max_leverage column: L = 1 / (1 − ltv_target + ltv_target × h_eff)
    ltv_target: float = 0.75
    # Concentration thresholds (Section E.2)
    concentration_threshold: float = 0.20   # portfolio weight above which H_conc kicks in
    h_conc_add_on: float = 0.01             # flat add-on when concentrated
    # Base haircut for equity (E.2) — if None, derived from volatility
    h_base_override: Optional[float] = None
    # Horizon used exclusively for collateral haircut (E.2).
    # Defaults to 1 day — collateral can be called intraday, unlike IM which
    # uses liquidation_horizon (5 days) for position wind-down.
    h_base_liquidation_horizon: int = 1
    # Student-t tail scaling in RVaR (D.2.4) — set False to use plain historical quantile
    use_student_t_scaling: bool = False
    # Include stressed scenarios in MRC = max(RVaR_hist + CB, w_s × RVaR_stress)
    # Set False to use MRC = RVaR_hist + CB only
    use_stress_scenarios: bool = False
    # Fraction of vol-excess above h_floor absorbed into h_base (0 = ignore vol, 1 = full vol)
    vol_buffer_weight: float = 0.5


# ──────────────────────────────────────────────────────────────────────────────
# Phase 1 — Collateral Assessment  (Section E.2)
# ──────────────────────────────────────────────────────────────────────────────

def phase1_collateral(
    prices: pd.DataFrame,
    market_values: Optional[pd.Series] = None,
    cash: float = 0.0,
    cfg: MarginConfig = MarginConfig(),
    instruments_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Compute Adjusted Collateral Value (ACV) per instrument and in total.

    Parameters
    ----------
    prices : pd.DataFrame
        Price history (rows=dates, cols=ISINs). Latest row used as current price.
    market_values : pd.Series, optional
        Current market value per ISIN (units × price).  If None, equal weights
        (MV = 1 per instrument) are assumed so that outputs are expressed as rates.
    cash : float
        Cash collateral (EUR), accepted at full value.
    cfg : MarginConfig
    instruments_df : pd.DataFrame, optional
        Instrument reference data indexed by ISIN.  If an ``h_floor`` column is
        present, haircuts are computed as:
            h_base = h_floor + max(0, vol_implied − h_floor) × vol_buffer_weight
        ISINs missing from instruments_df fall back to the pure vol-implied haircut.

    Returns
    -------
    dict with keys:
        h_floor  : pd.Series — asset-class floor per ISIN (NaN if not provided)
        h_base   : pd.Series — base haircut per ISIN
        h_conc   : pd.Series — concentration add-on per ISIN (0 if not concentrated)
        h_eff    : pd.Series — effective haircut = h_base + h_conc
        mv       : pd.Series — market value per ISIN
        acv      : pd.Series — adjusted collateral value per ISIN = MV × (1 − h_eff)
        acv_total: float     — sum(ACV) + cash
    """
    returns = prices.pct_change().dropna()

    # ── Vol-implied haircut (always computed as the base signal) ─────────────
    ann_vol = returns.std() * np.sqrt(cfg.trading_days_year)
    z = stats.norm.ppf(cfg.rvar_target_conf)
    h_vol = (1 - np.exp(
        -z * ann_vol * np.sqrt(cfg.h_base_liquidation_horizon / cfg.trading_days_year)
    )).clip(0, 1)

    # ── Base haircut ──────────────────────────────────────────────────────────
    if cfg.h_base_override is not None:
        h_base = pd.Series(cfg.h_base_override, index=prices.columns)
        h_floor = pd.Series(np.nan, index=prices.columns)
    elif instruments_df is not None and "h_floor" in instruments_df.columns:
        h_floor = instruments_df["h_floor"].reindex(prices.columns)  # NaN where missing
        # h_base = h_floor + vol_buffer_weight × max(0, h_vol − h_floor)
        # For ISINs without a floor, fall back to pure vol-implied
        excess = (h_vol - h_floor).clip(lower=0)
        h_base = h_floor + cfg.vol_buffer_weight * excess
        h_base = h_base.fillna(h_vol).clip(0, 1)
    else:
        h_base = h_vol
        h_floor = pd.Series(np.nan, index=prices.columns)

    # ── Market values ────────────────────────────────────────────────────────
    if market_values is None:
        mv = pd.Series(1.0, index=prices.columns)
    else:
        mv = market_values.reindex(prices.columns).fillna(0.0)

    total_mv = mv.sum()

    # ── Concentration add-on  (E.2) ──────────────────────────────────────────
    weights = mv / total_mv if total_mv > 0 else pd.Series(0.0, index=prices.columns)
    concentrated = weights > cfg.concentration_threshold
    h_conc = concentrated.astype(float) * cfg.h_conc_add_on

    h_eff = (h_base + h_conc).clip(0, 1)

    acv = mv * (1 - h_eff)
    acv_total = acv.sum() + cash

    return {
        "h_floor": h_floor,
        "h_base": h_base,
        "h_conc": h_conc,
        "h_eff": h_eff,
        "mv": mv,
        "acv": acv,
        "acv_total": acv_total,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 helpers  (Section D.2)
# ──────────────────────────────────────────────────────────────────────────────

def _ewma_vol(returns: pd.Series, lam: float) -> pd.Series:
    """Rolling EWMA variance → annualised std dev (252-day basis)."""
    sq = returns ** 2
    ewma_var = sq.ewm(com=lam / (1 - lam), adjust=False).mean()
    return np.sqrt(ewma_var * TRADING_DAYS_YEAR)


def _build_filtered_scenarios(
    returns: pd.DataFrame,
    cfg: MarginConfig,
) -> pd.DataFrame:
    """
    Construct filtered historical scenarios (D.2.2).

    r_filt(i, s) = r_hist(i, s) × σ̂_0(i) / σ̂_s(i)

    where σ̂_0 is the EWMA vol at the current date and σ̂_s is the EWMA vol
    on the historical scenario date s.

    Returns
    -------
    pd.DataFrame  shape (n_scenarios, n_ISINs)
        Filtered returns, one row per scenario day.
    """
    current_vol = returns.apply(lambda col: _ewma_vol(col, cfg.ewma_lambda)).iloc[-1]

    hist_vol = returns.apply(lambda col: _ewma_vol(col, cfg.ewma_lambda))

    scaling = hist_vol.apply(lambda col: current_vol[col.name] / col.replace(0, np.nan))
    scaling = scaling.fillna(1.0)

    filtered = returns * scaling

    # Take the last n_hist_scenarios rows (most recent history)
    n = min(cfg.n_hist_scenarios, len(filtered))
    return filtered.iloc[-n:]


def _identify_stress_period(
    returns: pd.DataFrame,
    n_stress: int,
) -> pd.DataFrame:
    """
    Identify stressed scenarios from the available price history.

    Strategy: rank all historical windows by average absolute return (a proxy
    for realised volatility / crisis severity) and pick the top `n_stress` days.

    Returns
    -------
    pd.DataFrame  shape (n_stress, n_ISINs)
        Raw (unscaled) returns for the stressed period.
    """
    row_intensity = returns.abs().mean(axis=1)
    top_idx = row_intensity.nlargest(n_stress).index
    return returns.loc[top_idx]


def _robust_var(
    pnl_series: np.ndarray,
    alpha_low: float,
    target_conf: float,
    dof: float,
    use_student_t_scaling: bool = True,
) -> float:
    """
    Robust VaR (D.2.4).

    With Student-t scaling (default):
        RVaR = VaR(α_low) × t_ν⁻¹(target_conf) / t_ν⁻¹(α_low)

    Without scaling (use_student_t_scaling=False):
        RVaR = VaR(target_conf)  — plain historical quantile at 99%

    Parameters
    ----------
    pnl_series           : 1-D array of scenario P&L values (losses are negative)
    alpha_low            : base quantile (0.95 for historical, 0.90 for stressed)
    target_conf          : target confidence level (0.99)
    dof                  : Student-t degrees of freedom
    use_student_t_scaling: if False, return the direct historical quantile at target_conf
    """
    if len(pnl_series) == 0:
        return 0.0
    if not use_student_t_scaling:
        return float(-np.quantile(pnl_series, 1 - target_conf))
    var_low = -np.quantile(pnl_series, 1 - alpha_low)  # loss is positive
    t_target = stats.t.ppf(target_conf, df=dof)
    t_low = stats.t.ppf(alpha_low, df=dof)
    if t_low <= 0:
        return var_low
    return var_low * t_target / t_low


def _correlation_break(
    rvar: float,
    pnl_scenarios: np.ndarray,
    alpha_low: float,
    cfg: MarginConfig,
) -> float:
    """
    Correlation Break adjustment  CB = clip(κ × RMSE(excess VaRs), Φ×RVaR, ψ×RVaR).

    Excess VaR for each scenario s: max(0, −PL(s) − RVaR).
    """
    exceedances = np.maximum(0, -pnl_scenarios - rvar)
    rmse = np.sqrt(np.mean(exceedances ** 2))
    cb_raw = cfg.cb_kappa * rmse
    return float(np.clip(cb_raw, cfg.cb_phi * rvar, cfg.cb_psi * rvar))


def _liquidity_component(
    pnl_per_instrument: dict[str, np.ndarray],
    rvar_per_instrument: dict[str, float],
    cfg: MarginConfig,
) -> float:
    """
    Liquidity Component  LC(l) = DF(l) × Σ_i RVaR_pos(i) × λ(i)   (D.2.5).

    For single-asset groups (no position sizes) we sum instrument-level RVaRs.
    """
    lc = cfg.diversity_factor * sum(
        rvar_per_instrument.get(isin, 0.0) * cfg.lambda_liquidity
        for isin in rvar_per_instrument
    )
    return float(lc)


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 — Initial Margin  (Section D.2.1–D.2.6)
# ──────────────────────────────────────────────────────────────────────────────

def _phase2_standalone(
    pnl_hist: pd.DataFrame,
    pnl_stress: pd.DataFrame,
    cfg: MarginConfig,
) -> dict:
    """
    Compute per-ISIN IM in standalone mode (each ISIN = its own liquidation group).

    MRC(i) = max(RVaR_hist(i) + CB(i),  w_s × RVaR_stress(i))
    LC(i)  = DF × RVaR_hist(i) × λ
    IM(i)  = MRC(i) + LC(i)
    """
    records: dict[str, dict] = {}
    for isin in pnl_hist.columns:
        isin_pnl_hist   = pnl_hist[isin].values
        isin_pnl_stress = pnl_stress[isin].values

        rv_hist   = _robust_var(isin_pnl_hist,   cfg.rvar_alpha_hist,   cfg.rvar_target_conf, cfg.student_t_dof, cfg.use_student_t_scaling)
        rv_stress = _robust_var(isin_pnl_stress, cfg.rvar_alpha_stress, cfg.rvar_target_conf, cfg.student_t_dof, cfg.use_student_t_scaling)
        cb_i      = _correlation_break(rv_hist, isin_pnl_hist, cfg.rvar_alpha_hist, cfg)
        mrc_i     = max(rv_hist + cb_i, cfg.w_stress * rv_stress) if cfg.use_stress_scenarios else rv_hist + cb_i
        lc_i      = cfg.diversity_factor * rv_hist * cfg.lambda_liquidity
        im_i      = mrc_i + lc_i

        records[isin] = {
            "rvar_hist":   rv_hist,
            "rvar_stress": rv_stress,
            "cb":          cb_i,
            "mrc":         mrc_i,
            "lc":          lc_i,
            "im_total":    im_i,
            "margin_rate": im_i,   # rate = IM on unit notional
        }

    per_isin = pd.DataFrame(records).T
    per_isin.index.name = "isin"
    return {
        "per_isin":    per_isin,
        "margin_rate": per_isin["margin_rate"],
        # group-level aggregates: sum across ISINs for reference
        "mrc":         per_isin["mrc"].sum(),
        "lc":          per_isin["lc"].sum(),
        "im_total":    per_isin["im_total"].sum(),
        "rvar_hist":   per_isin["rvar_hist"].sum(),
        "rvar_stress": per_isin["rvar_stress"].sum(),
        "cb":          per_isin["cb"].sum(),
        "rvar_per_isin": per_isin["rvar_hist"].to_dict(),
    }


def _phase2_portfolio(
    pnl_hist: pd.DataFrame,
    pnl_stress: pd.DataFrame,
    cfg: MarginConfig,
) -> dict:
    """
    Compute IM treating all ISINs as one liquidation group (portfolio / netting mode).

    MRC  = max(RVaR_hist_port + CB,  w_s × RVaR_stress_port)
    LC   = DF × Σ_i RVaR_hist(i) × λ
    IM   = MRC + LC   apportioned back to ISINs by RVaR_hist(i) share.
    """
    port_pnl_hist   = pnl_hist.sum(axis=1).values
    port_pnl_stress = pnl_stress.sum(axis=1).values

    rvar_hist   = _robust_var(port_pnl_hist,   cfg.rvar_alpha_hist,   cfg.rvar_target_conf, cfg.student_t_dof, cfg.use_student_t_scaling)
    rvar_stress = _robust_var(port_pnl_stress, cfg.rvar_alpha_stress, cfg.rvar_target_conf, cfg.student_t_dof, cfg.use_student_t_scaling)
    cb          = _correlation_break(rvar_hist, port_pnl_hist, cfg.rvar_alpha_hist, cfg)
    mrc         = max(rvar_hist + cb, cfg.w_stress * rvar_stress) if cfg.use_stress_scenarios else rvar_hist + cb

    rvar_per_isin: dict[str, float] = {
        isin: _robust_var(pnl_hist[isin].values, cfg.rvar_alpha_hist, cfg.rvar_target_conf, cfg.student_t_dof, cfg.use_student_t_scaling)
        for isin in pnl_hist.columns
    }
    lc          = _liquidity_component({}, rvar_per_isin, cfg)
    im_total    = mrc + lc

    total_rvar  = sum(rvar_per_isin.values()) or 1.0
    weight      = {isin: v / total_rvar for isin, v in rvar_per_isin.items()}
    per_isin    = pd.DataFrame({
        "rvar_hist":   rvar_per_isin,
        "mrc":         {isin: weight[isin] * mrc    for isin in pnl_hist.columns},
        "lc":          {isin: weight[isin] * lc     for isin in pnl_hist.columns},
        "im_total":    {isin: weight[isin] * im_total for isin in pnl_hist.columns},
        "margin_rate": {isin: weight[isin] * im_total for isin in pnl_hist.columns},
    })
    per_isin.index.name = "isin"

    return {
        "per_isin":    per_isin,
        "margin_rate": per_isin["margin_rate"],
        "mrc":         mrc,
        "lc":          lc,
        "im_total":    im_total,
        "rvar_hist":   rvar_hist,
        "rvar_stress": rvar_stress,
        "cb":          cb,
        "rvar_per_isin": rvar_per_isin,
    }


def phase2_initial_margin(
    prices: pd.DataFrame,
    cfg: MarginConfig = MarginConfig(),
    portfolio_mode: bool = False,
) -> dict:
    """
    Compute Initial Margin rates per instrument.

    Parameters
    ----------
    prices : pd.DataFrame
        Price history (rows = dates, cols = ISINs).
    cfg : MarginConfig
    portfolio_mode : bool, default False
        False (default) — standalone mode: each ISIN is its own liquidation
        group.  Use this for pre-trade customer-facing margin rates.
        True  — portfolio mode: all ISINs form one group with netting.
        Use this when you have a customer's full book and want margin relief
        from diversification.

    Returns
    -------
    dict with keys:
        margin_rate  : pd.Series  — IM rate per ISIN
        per_isin     : pd.DataFrame — full per-ISIN breakdown
        mrc, lc, im_total, rvar_hist, rvar_stress, cb : group-level scalars
        rvar_per_isin: dict       — per-ISIN RVaR_hist
        detail_scenarios : dict  — filtered & stressed return DataFrames
    """
    if len(prices) < 10:
        raise ValueError("Need at least 10 days of price history.")

    returns      = prices.pct_change().dropna()
    filtered_rets = _build_filtered_scenarios(returns, cfg)
    stressed_rets = _identify_stress_period(returns, cfg.n_stress_scenarios)

    if portfolio_mode:
        result = _phase2_portfolio(filtered_rets, stressed_rets, cfg)
    else:
        result = _phase2_standalone(filtered_rets, stressed_rets, cfg)

    result["detail_scenarios"] = {"filtered": filtered_rets, "stressed": stressed_rets}
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3 — Trade Execution  (stub — needs customer data)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LoanPosition:
    """Represents an active leveraged position for a single customer account."""
    isin: str
    quantity: float        # number of units held
    entry_price: float     # price at which position was opened
    loan_amount: float     # L_t — outstanding loan in EUR


def phase3_open_position(
    isin: str,
    quantity: float,
    entry_price: float,
    loan_amount: float,
) -> LoanPosition:
    """
    Phase 3 — Trade Execution  (D.1.1 / E.3.2).

    Records the opened leveraged position. In production, this would validate
    that ACV_total >= IM_total before approving the loan.

    Parameters
    ----------
    isin         : instrument ISIN
    quantity     : number of units purchased
    entry_price  : execution price (EUR)
    loan_amount  : loan extended by Trade Republic (EUR)

    Returns
    -------
    LoanPosition
    """
    return LoanPosition(
        isin=isin,
        quantity=quantity,
        entry_price=entry_price,
        loan_amount=loan_amount,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Phase 4 — Daily Monitoring Loop  (stub — needs customer data)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DailyMonitoringResult:
    date: pd.Timestamp
    isin: str
    current_price: float
    variation_margin: float   # VM = (P_t − P_{t-1}) × N
    mv_port: float            # current market value of position
    acv_total: float          # adjusted collateral value (from Phase 1)
    ltv: float                # LTV_t = L_t / ACV_total
    ltv_stress: float         # stress LTV using haircut-stressed prices


def phase4_daily_monitoring(
    position: LoanPosition,
    prices_today: pd.Series,    # index=ISIN, value=current price
    prices_yesterday: pd.Series,
    acv_result: dict,           # output of phase1_collateral
    cfg: MarginConfig = MarginConfig(),
) -> DailyMonitoringResult:
    """
    Phase 4 — Daily Monitoring  (D.1.3 / E.3.2–E.3.3).

    Computes:
    - Variation Margin: VM = (P_t − P_{t-1}) × N
    - Current LTV:      LTV_t = L_t / ACV_total_t
    - Stress LTV:       LTV_stress = L_t / ACV_stress_t  (stressed prices)
    """
    p_today = prices_today.get(position.isin, position.entry_price)
    p_yesterday = prices_yesterday.get(position.isin, position.entry_price)

    vm = (p_today - p_yesterday) * position.quantity
    mv_port = p_today * position.quantity
    acv_total = acv_result["acv_total"]
    h_eff = acv_result["h_eff"].get(position.isin, acv_result["h_base"].get(position.isin, 0.0))

    # Stressed ACV: apply additional stress haircut (use h_eff as floor approximation)
    acv_stress = mv_port * (1 - h_eff)
    ltv = position.loan_amount / acv_total if acv_total > 0 else np.inf
    ltv_stress = position.loan_amount / acv_stress if acv_stress > 0 else np.inf

    return DailyMonitoringResult(
        date=pd.Timestamp.today().normalize(),
        isin=position.isin,
        current_price=p_today,
        variation_margin=vm,
        mv_port=mv_port,
        acv_total=acv_total,
        ltv=ltv,
        ltv_stress=ltv_stress,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Phase 5 — LTV Limit Checks  (Section G.3.4)
# ──────────────────────────────────────────────────────────────────────────────

from enum import Enum

class LTVStatus(str, Enum):
    OK = "OK"
    MONITORING = "MONITORING"          # surveillance flag
    MARGIN_BREACH = "MARGIN_BREACH"    # alert to customer
    LIQUIDATION = "LIQUIDATION"        # auto-liquidate


def phase5_ltv_check(
    monitoring_result: DailyMonitoringResult,
    cfg: MarginConfig = MarginConfig(),
) -> LTVStatus:
    """
    Phase 5 — LTV Limit Checks  (G.3.4).

    Returns the appropriate action status based on current LTV.
    """
    ltv = monitoring_result.ltv
    if ltv >= cfg.ltv_liquidation_limit:
        return LTVStatus.LIQUIDATION
    if ltv >= cfg.ltv_breach_limit:
        return LTVStatus.MARGIN_BREACH
    if ltv >= cfg.ltv_monitoring_limit:
        return LTVStatus.MONITORING
    return LTVStatus.OK


# ──────────────────────────────────────────────────────────────────────────────
# Top-level orchestrator — follows the complete flowchart
# ──────────────────────────────────────────────────────────────────────────────

def compute_margin_requirements(
    prices: pd.DataFrame,
    market_values: Optional[pd.Series] = None,
    cash: float = 0.0,
    cfg: MarginConfig = MarginConfig(),
    portfolio_mode: bool = False,
    instruments_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.Series, dict]:
    """
    Full end-to-end margin engine (Phases 1 & 2 only — Phases 3–5 need
    customer loan data).

    Parameters
    ----------
    prices : pd.DataFrame
        Columns = ISINs, index = dates (at least 250 rows).
    market_values : pd.Series, optional
        Current MV per ISIN.  None → unit notional (rates output).
    cash : float
        Cash collateral in EUR.
    cfg : MarginConfig
        Methodology parameters.
    portfolio_mode : bool, default False
        False — standalone per-ISIN rates (correct for pre-trade display).
        True  — portfolio netting across all ISINs (for existing book margin).
    instruments_df : pd.DataFrame, optional
        Instrument reference data indexed by ISIN.  Must contain an ``h_floor``
        column (float) with the asset-class haircut floor.  Any other columns
        are ignored.  ISINs not present fall back to pure vol-implied haircuts.

    Returns
    -------
    margin_rates : pd.Series
        IM as fraction of position value, per ISIN.
    detail : dict
        Full breakdown from both phases, including ``instrument_summary``.
    """
    if len(prices) < 50:
        warnings.warn("Fewer than 50 days of history — results may be unreliable.")

    # Phase 1 — Collateral Assessment
    p1 = phase1_collateral(prices, market_values=market_values, cash=cash, cfg=cfg, instruments_df=instruments_df)

    # Phase 2 — Initial Margin
    p2 = phase2_initial_margin(prices, cfg=cfg, portfolio_mode=portfolio_mode)

    # Decision gate: ACV_total >= IM_total?
    collateral_sufficient = p1["acv_total"] >= p2["im_total"]

    # ── Per-ISIN summary DataFrame ────────────────────────────────────────────
    # p2["per_isin"] already contains rvar_hist, mrc, lc, im_total, margin_rate
    p2_per_isin = p2["per_isin"]

    # Parametric VaR benchmark: σ_daily × z × sqrt(holding_period)
    z_score = stats.norm.ppf(cfg.rvar_target_conf)
    daily_vol = prices.pct_change().dropna().std()
    parametric_var = daily_vol * z_score * np.sqrt(cfg.liquidation_horizon)

    instrument_summary = pd.DataFrame(
        {
            # Phase 1 — Collateral
            "h_floor":      p1["h_floor"],
            "h_base":       p1["h_base"],
            "h_conc":       p1["h_conc"],
            "h_eff":        p1["h_eff"],
            "market_value": p1["mv"],
            "acv":          p1["acv"],
            # Phase 2 — Initial Margin (per-ISIN breakdown)
            "student_t_scaling":    cfg.use_student_t_scaling,
            "rvar":         p2_per_isin["rvar_hist"],
            # Parametric VaR benchmark: σ_daily × z(99%) × sqrt(holding_period)
            "bmk_pvar":     parametric_var,
            "mrc":          p2_per_isin["mrc"],
            "lc":           p2_per_isin["lc"],
            "im_total":     p2_per_isin["im_total"],
            "margin_rate":  p2_per_isin["margin_rate"],
            # LTV for a 4x leveraged position: loan = 3/4 × MV, LTV = (3/4) / ACV
            "ltv_4x":               (3 / 4) / p1["acv"],
            # Max leverage at cfg.ltv_target: L = 1 / (1 − ltv_target + ltv_target × h_eff)
            "max_leverage":         1 / (1 - cfg.ltv_target + cfg.ltv_target * p1["h_eff"]),

        }
    )
    instrument_summary.index.name = "isin"

    detail = {
        "instrument_summary": instrument_summary,
        "portfolio_mode": portfolio_mode,
        "phase1": p1,
        "phase2": p2,
        "collateral_sufficient": collateral_sufficient,
        "acv_total": p1["acv_total"],
        "im_total": p2["im_total"],
    }

    return p2["margin_rate"], detail


# ──────────────────────────────────────────────────────────────────────────────
# Convenience: batch run across multiple rebalancing dates
# ──────────────────────────────────────────────────────────────────────────────

def rolling_margin_rates(
    prices: pd.DataFrame,
    window: int = 250,
    step: int = 1,
    cfg: MarginConfig = MarginConfig(),
) -> pd.DataFrame:
    """
    Compute margin rates on a rolling basis.

    Parameters
    ----------
    prices : pd.DataFrame
        Full price history.
    window : int
        Rolling window in trading days (default 250).
    step : int
        Step between recalculations (default 1 = daily).

    Returns
    -------
    pd.DataFrame
        Rows = evaluation dates, columns = ISINs.
    """
    results = {}
    dates = prices.index[window - 1 :: step]
    for date in dates:
        window_prices = prices.loc[:date].iloc[-window:]
        try:
            rates, _ = compute_margin_requirements(window_prices, cfg=cfg)
            results[date] = rates
        except Exception as exc:  # noqa: BLE001
            warnings.warn(f"Skipping {date}: {exc}")
    return pd.DataFrame(results).T
