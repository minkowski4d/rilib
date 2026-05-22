"""
Total Margin Calculator — Prisma Methodology
=============================================
Calculates:
  - Mark-to-Market Margin (Premium, Variation, Current Liquidating)
  - Initial Margin
      └── Market Risk Component (Robust VaR, Correlation Break, Compression Error)
      └── Liquidity Risk Component (position-level + diversification)
  - Total Margin

Dependencies: numpy, scipy
"""

import numpy as np
from scipy.stats import t as student_t
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class Instrument:
    name: str
    current_price: float
    num_contracts: int              # negative = short
    trade_unit_value: float         # TUV
    instrument_type: str            # 'option', 'future', 'bond_equity'
    product_currency: str           # e.g. 'EUR'
    liquidity_class: str            # e.g. 'EOLC', 'EFLC', 'BF'
    market_capacity: float          # daily volume in contracts
    bid_price: float
    ask_price: float
    instrument_var: float           # single-contract VaR provided by clearing house
    compression_error_hist: list    # per sub-sample, historical
    compression_error_stress: list  # per sub-sample, stressed
    # Mark-to-market specific
    prev_price: Optional[float] = None          # for variation / CLM
    option_premium_paid: Optional[float] = None # for premium margin (buyer)
    is_option_writer: bool = False


@dataclass
class LiquidationGroupSplit:
    name: str
    instruments: list[Instrument]
    holding_period: int             # days
    hist_scenarios: np.ndarray      # shape: (n_scenarios, n_instruments)
    stress_scenarios: np.ndarray    # shape: (n_stress, n_instruments)
    # Risk measure config
    hist_confidence: float = 0.95
    stress_confidence: float = 0.90
    target_confidence: float = 0.99
    t_degrees_of_freedom: int = 3
    stress_scaling_factor: float = 0.70
    # Correlation break config
    cb_window_size: int = 60
    cb_confidence: float = 0.90
    cb_kappa: float = 1.0
    cb_floor_pct: float = 0.0       # as decimal
    cb_cap_pct: float = 0.80        # as decimal
    # Liquidity config
    alpha_floor: float = 0.10


@dataclass
class Portfolio:
    clearing_currency: str
    liquidation_group_splits: list[LiquidationGroupSplit]


# ─────────────────────────────────────────────
# MARK-TO-MARKET MARGIN
# ─────────────────────────────────────────────

def calc_premium_margin(instrument: Instrument) -> float:
    """
    Collected from option writers only.
    Covers cost of closing the position at current market price.
    """
    if instrument.instrument_type != 'option' or not instrument.is_option_writer:
        return 0.0
    return abs(instrument.current_price * instrument.trade_unit_value
               * instrument.num_contracts)


def calc_variation_margin(instrument: Instrument) -> float:
    """
    Daily cash P&L settlement for futures and options on futures.
    Positive = gain (received), negative = loss (paid).
    """
    if instrument.instrument_type != 'future' or instrument.prev_price is None:
        return 0.0
    return ((instrument.current_price - instrument.prev_price)
            * instrument.trade_unit_value * instrument.num_contracts)


def calc_current_liquidating_margin(instrument: Instrument) -> float:
    """
    For bonds and equities — covers immediate close-out loss.
    """
    if instrument.instrument_type != 'bond_equity' or instrument.prev_price is None:
        return 0.0
    mtm_pnl = ((instrument.current_price - instrument.prev_price)
                * instrument.trade_unit_value * instrument.num_contracts)
    return max(0.0, -mtm_pnl)


def calc_mark_to_market_margin(lgs: LiquidationGroupSplit) -> dict:
    premium   = sum(calc_premium_margin(i)            for i in lgs.instruments)
    variation = sum(calc_variation_margin(i)           for i in lgs.instruments)
    clm       = sum(calc_current_liquidating_margin(i) for i in lgs.instruments)
    return {
        "premium_margin":              round(premium,   2),
        "variation_margin":            round(variation, 2),
        "current_liquidating_margin":  round(clm,       2),
        "total_mtm_margin":            round(premium + max(0, -variation) + clm, 2)
    }


# ─────────────────────────────────────────────
# PROFIT & LOSS DISTRIBUTIONS
# ─────────────────────────────────────────────

def calc_pnl_distributions(lgs: LiquidationGroupSplit) -> tuple:
    """
    Returns P&L vectors split into sub-samples for both scenario types.
    Shape of each sub-sample list: list of arrays, one per sub-sample.
    """
    n = lgs.holding_period
    positions = np.array([i.num_contracts * i.trade_unit_value for i in lgs.instruments])
    current   = np.array([i.current_price for i in lgs.instruments])

    def split_pnl(scenarios):
        pnl = (current - scenarios) * positions          # (n_scen, n_inst)
        portfolio_pnl = pnl.sum(axis=1)                  # (n_scen,)
        return [portfolio_pnl[j::n] for j in range(n)]  # split into sub-samples

    return split_pnl(lgs.hist_scenarios), split_pnl(lgs.stress_scenarios)


# ─────────────────────────────────────────────
# VAR CALCULATION
# ─────────────────────────────────────────────

def calc_var(pnl_vector: np.ndarray, confidence: float) -> float:
    """
    VaR at given confidence level from a P&L vector.
    Positive VaR = loss. Bounded at zero.
    Uses linear interpolation between quantile points.
    """
    sorted_pnl = np.sort(pnl_vector)
    n = len(sorted_pnl)
    quantile_target = (1.0 - confidence) * 100
    quantiles = 100 * (0.5 + np.arange(n)) / n

    if quantile_target <= quantiles[0]:
        var = sorted_pnl[0]
    elif quantile_target >= quantiles[-1]:
        var = sorted_pnl[-1]
    else:
        idx = np.searchsorted(quantiles, quantile_target)
        q_lo, q_hi = quantiles[idx - 1], quantiles[idx]
        p_lo, p_hi = sorted_pnl[idx - 1], sorted_pnl[idx]
        var = p_lo + (p_hi - p_lo) * (quantile_target - q_lo) / (q_hi - q_lo)

    return max(0.0, -var)   # loss is positive


def robust_var_scaling_factor(confidence_low: float,
                               confidence_high: float,
                               df: int) -> float:
    """
    Scaling factor from lower to target confidence using Student-t quantiles.
    """
    t_high = abs(student_t.ppf(1 - confidence_high, df))
    t_low  = abs(student_t.ppf(1 - confidence_low,  df))
    return t_high / t_low


def calc_robust_var(pnl_vector: np.ndarray, lgs: LiquidationGroupSplit,
                    scenario_type: str) -> float:
    if scenario_type == 'hist':
        base_conf = lgs.hist_confidence
    else:
        base_conf = lgs.stress_confidence

    base_var = calc_var(pnl_vector, base_conf)
    scale    = robust_var_scaling_factor(base_conf, lgs.target_confidence,
                                         lgs.t_degrees_of_freedom)
    return base_var * scale


# ─────────────────────────────────────────────
# CORRELATION BREAK ADJUSTMENT
# ─────────────────────────────────────────────

def calc_correlation_break(pnl_subsample: np.ndarray,
                            full_var: float,
                            lgs: LiquidationGroupSplit) -> float:
    """
    Rolling window VaR vs full-sample VaR excess risk measure.
    Applied to historical scenarios only.
    """
    n = len(pnl_subsample)
    w = lgs.cb_window_size
    if n < w:
        return lgs.cb_floor_pct * full_var

    excess_sq = []
    for start in range(0, n - w + 1):
        window_pnl = pnl_subsample[start: start + w]
        window_var = calc_var(window_pnl, lgs.cb_confidence)
        full_var_cb = calc_var(pnl_subsample, lgs.cb_confidence)
        excess = max(0.0, window_var - full_var_cb)
        if excess > 0:
            excess_sq.append(excess ** 2)

    if not excess_sq:
        mer = 0.0
    else:
        mer = np.sqrt(np.mean(excess_sq)) * lgs.cb_kappa

    lower = lgs.cb_floor_pct * full_var
    upper = lgs.cb_cap_pct  * full_var
    return float(np.clip(mer, lower, upper))


# ─────────────────────────────────────────────
# COMPRESSION ERROR ADJUSTMENT
# ─────────────────────────────────────────────

def calc_compression_error(lgs: LiquidationGroupSplit,
                            scenario_type: str) -> list:
    """
    Aggregate absolute compression errors across all positions per sub-sample.
    Returns one value per sub-sample.
    """
    n_sub = lgs.holding_period
    totals = []
    for a in range(n_sub):
        total = 0.0
        for inst in lgs.instruments:
            errors = (inst.compression_error_hist if scenario_type == 'hist'
                      else inst.compression_error_stress)
            if a < len(errors):
                total += abs(inst.num_contracts * inst.trade_unit_value * errors[a])
        totals.append(total)
    return totals


# ─────────────────────────────────────────────
# MARKET RISK COMPONENT
# ─────────────────────────────────────────────

def calc_market_risk_component(lgs: LiquidationGroupSplit,
                                hist_pnl_subs: list,
                                stress_pnl_subs: list) -> dict:
    hist_vars, stress_vars = [], []
    cb_adjustments, ce_hist, ce_stress = [], [], []

    ce_hist_list   = calc_compression_error(lgs, 'hist')
    ce_stress_list = calc_compression_error(lgs, 'stress')

    for a, pnl in enumerate(hist_pnl_subs):
        var   = calc_robust_var(pnl, lgs, 'hist')
        cb    = calc_correlation_break(pnl, var, lgs)
        hist_vars.append(var)
        cb_adjustments.append(cb)
        ce_hist.append(ce_hist_list[a] if a < len(ce_hist_list) else 0.0)

    for a, pnl in enumerate(stress_pnl_subs):
        var = calc_robust_var(pnl, lgs, 'stress')
        stress_vars.append(var)
        ce_stress.append(ce_stress_list[a] if a < len(ce_stress_list) else 0.0)

    # Aggregate sub-samples
    mean_hist   = np.mean([v + cb + ce
                           for v, cb, ce in zip(hist_vars, cb_adjustments, ce_hist)])
    mean_stress = np.mean([v + ce for v, ce in zip(stress_vars, ce_stress)])

    market_risk = max(mean_hist, lgs.stress_scaling_factor * mean_stress)

    return {
        "hist_var_per_subsample":     [round(v, 2) for v in hist_vars],
        "stress_var_per_subsample":   [round(v, 2) for v in stress_vars],
        "corr_break_per_subsample":   [round(v, 2) for v in cb_adjustments],
        "compression_error_hist":     [round(v, 2) for v in ce_hist],
        "compression_error_stress":   [round(v, 2) for v in ce_stress],
        "mean_hist_with_adjustments": round(mean_hist,   2),
        "mean_stress_scaled":         round(lgs.stress_scaling_factor * mean_stress, 2),
        "market_risk_component":      round(market_risk, 2),
    }


# ─────────────────────────────────────────────
# LIQUIDITY FACTOR INTERPOLATION
# ─────────────────────────────────────────────

LIQUIDITY_FACTOR_TABLE = {
    # liquidity_class: list of (lower_threshold_pct, upper_threshold_pct, lf_low, lf_high)
    "EOLC": [(0, 5, 0.00, 0.05), (5, 10, 0.05, 0.25), (10, 15, 0.25, 0.50),
             (15, 20, 0.50, 0.75), (20, 100, 0.75, 0.75)],
    "EFLC": [(0, 5, 0.00, 0.05), (5, 10, 0.05, 0.25), (10, 15, 0.25, 0.50),
             (15, 20, 0.50, 0.75), (20, 100, 0.75, 0.75)],
    "BF":   [(0, 5, 0.00, 0.05), (5, 10, 0.05, 0.25), (10, 15, 0.25, 0.50),
             (15, 20, 0.50, 0.75), (20, 100, 0.75, 0.75)],
}

def interpolate_liquidity_factor(liquidity_class: str, rel_size_pct: float) -> float:
    table = LIQUIDITY_FACTOR_TABLE.get(liquidity_class, [])
    for (l_th, u_th, lf_l, lf_u) in table:
        if l_th <= rel_size_pct < u_th:
            return lf_l + (lf_u - lf_l) * (rel_size_pct - l_th) / (u_th - l_th)
    if table:
        return table[-1][3]  # last bucket upper LF
    return 0.0


# ─────────────────────────────────────────────
# LIQUIDITY RISK COMPONENT
# ─────────────────────────────────────────────

def calc_liquidity_risk_component(lgs: LiquidationGroupSplit,
                                   hist_pnl_subs: list) -> dict:
    position_lc = []

    for inst in lgs.instruments:
        net_gross_ratio = 1.0  # simplified: each instrument in its own risk bucket
        net_eff_contracts = net_gross_ratio * inst.num_contracts
        rel_size_pct = (abs(net_eff_contracts) / inst.market_capacity) * 100

        lf = interpolate_liquidity_factor(inst.liquidity_class, rel_size_pct)

        pos_var = inst.instrument_var * abs(net_eff_contracts) * inst.trade_unit_value

        mid   = (inst.bid_price + inst.ask_price) / 2
        spread_pct = abs(inst.bid_price - inst.ask_price) / (inst.bid_price + inst.ask_price)
        pos_value = abs(net_eff_contracts) * inst.trade_unit_value * inst.current_price

        lc_pos = pos_var * lf + spread_pct * pos_value
        position_lc.append(lc_pos)

    # Diversification factor
    sum_pos_var = sum(inst.instrument_var * abs(inst.num_contracts) * inst.trade_unit_value
                      for inst in lgs.instruments)

    all_pnl = np.concatenate(hist_pnl_subs)
    port_var = calc_var(all_pnl, lgs.hist_confidence)

    alpha = max(lgs.alpha_floor,
                port_var / sum_pos_var if sum_pos_var > 0 else lgs.alpha_floor)
    alpha = min(alpha, 1.0)

    liquidity_risk = alpha * sum(position_lc)

    return {
        "position_liquidity_components": [round(v, 2) for v in position_lc],
        "sum_position_lc":               round(sum(position_lc), 2),
        "portfolio_var_for_alpha":        round(port_var, 2),
        "sum_positional_var":             round(sum_pos_var, 2),
        "diversification_factor_alpha":   round(alpha, 4),
        "liquidity_risk_component":       round(liquidity_risk, 2),
    }


# ─────────────────────────────────────────────
# INITIAL MARGIN
# ─────────────────────────────────────────────

def calc_initial_margin(lgs: LiquidationGroupSplit) -> dict:
    hist_pnl_subs, stress_pnl_subs = calc_pnl_distributions(lgs)
    mrc = calc_market_risk_component(lgs, hist_pnl_subs, stress_pnl_subs)
    lrc = calc_liquidity_risk_component(lgs, hist_pnl_subs)

    initial_margin = mrc["market_risk_component"] + lrc["liquidity_risk_component"]

    return {
        "market_risk_component_detail": mrc,
        "liquidity_risk_component_detail": lrc,
        "market_risk_component":  mrc["market_risk_component"],
        "liquidity_risk_component": lrc["liquidity_risk_component"],
        "initial_margin":         round(initial_margin, 2),
    }


# ─────────────────────────────────────────────
# TOTAL MARGIN
# ─────────────────────────────────────────────

def calc_total_margin(portfolio: Portfolio) -> dict:
    results = {}
    total_initial_margin = 0.0
    total_mtm_margin     = 0.0

    for lgs in portfolio.liquidation_group_splits:
        im_result  = calc_initial_margin(lgs)
        mtm_result = calc_mark_to_market_margin(lgs)

        total_initial_margin += im_result["initial_margin"]
        total_mtm_margin     += mtm_result["total_mtm_margin"]

        results[lgs.name] = {
            "initial_margin_detail":    im_result,
            "mark_to_market_detail":    mtm_result,
            "initial_margin":           im_result["initial_margin"],
            "mark_to_market_margin":    mtm_result["total_mtm_margin"],
            "total_margin_this_split":  round(
                im_result["initial_margin"] + mtm_result["total_mtm_margin"], 2),
        }

    results["portfolio_summary"] = {
        "total_initial_margin":     round(total_initial_margin, 2),
        "total_mtm_margin":         round(total_mtm_margin,     2),
        "total_margin":             round(total_initial_margin + total_mtm_margin, 2),
        "clearing_currency":        portfolio.clearing_currency,
    }

    return results


# ─────────────────────────────────────────────
# EXAMPLE USAGE
# ─────────────────────────────────────────────

if __name__ == "__main__":

    np.random.seed(42)
    n_hist, n_stress = 750, 250

    # Two instruments: DAX Option + DAX Future
    dax_option = Instrument(
        name="DAX Option",
        current_price=1487.00,
        num_contracts=1,
        trade_unit_value=25,
        instrument_type="option",
        product_currency="EUR",
        liquidity_class="EOLC",
        market_capacity=1000,
        bid_price=1485.00,
        ask_price=1489.00,
        instrument_var=4810.79,
        compression_error_hist=[17.84, 23.79],
        compression_error_stress=[11.90, 20.82],
        prev_price=1470.00,
        is_option_writer=True,
    )

    dax_future = Instrument(
        name="DAX Future",
        current_price=146925.00,
        num_contracts=1,
        trade_unit_value=1,
        instrument_type="future",
        product_currency="EUR",
        liquidity_class="EFLC",
        market_capacity=2000,
        bid_price=146920.00,
        ask_price=146930.00,
        instrument_var=4853.25,
        compression_error_hist=[0.0, 0.0],
        compression_error_stress=[0.0, 0.0],
        prev_price=146500.00,
    )

    # Simulated scenario prices (750 hist + 250 stress, 2 instruments)
    hist_scen = np.column_stack([
        np.random.normal(1487.00,   120, n_hist),
        np.random.normal(146925.00, 1500, n_hist),
    ])
    stress_scen = np.column_stack([
        np.random.normal(1487.00,   300, n_stress),
        np.random.normal(146925.00, 4000, n_stress),
    ])

    lgs1 = LiquidationGroupSplit(
        name="LG1_nonexpiring",
        instruments=[dax_option, dax_future],
        holding_period=2,
        hist_scenarios=hist_scen,
        stress_scenarios=stress_scen,
    )

    portfolio = Portfolio(
        clearing_currency="EUR",
        liquidation_group_splits=[lgs1],
    )

    results = calc_total_margin(portfolio)

    # ── Print Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  TOTAL MARGIN CALCULATION — PRISMA METHODOLOGY")
    print("=" * 60)

    for lgs_name, data in results.items():
        if lgs_name == "portfolio_summary":
            continue
        print(f"\n▶ Liquidation Group Split: {lgs_name}")
        print(f"  {'Initial Margin:':<40} EUR {data['initial_margin']:>12,.2f}")
        print(f"  {'Mark-to-Market Margin:':<40} EUR {data['mark_to_market_margin']:>12,.2f}")
        print(f"  {'Total Margin (this split):':<40} EUR {data['total_margin_this_split']:>12,.2f}")

        mrc = data["initial_margin_detail"]["market_risk_component_detail"]
        lrc = data["initial_margin_detail"]["liquidity_risk_component_detail"]

        print(f"\n  Market Risk Component Breakdown:")
        print(f"    {'Hist VaR (per sub-sample):':<38} {mrc['hist_var_per_subsample']}")
        print(f"    {'Stress VaR (per sub-sample):':<38} {mrc['stress_var_per_subsample']}")
        print(f"    {'Corr. Break Adjustment:':<38} {mrc['corr_break_per_subsample']}")
        print(f"    {'Compression Error (Hist):':<38} {mrc['compression_error_hist']}")
        print(f"    {'Mean Hist (incl. adjustments):':<38} EUR {mrc['mean_hist_with_adjustments']:>10,.2f}")
        print(f"    {'Mean Stress (scaled x0.70):':<38} EUR {mrc['mean_stress_scaled']:>10,.2f}")
        print(f"    {'Market Risk Component:':<38} EUR {mrc['market_risk_component']:>10,.2f}")

        print(f"\n  Liquidity Risk Component Breakdown:")
        print(f"    {'Position LC values:':<38} {lrc['position_liquidity_components']}")
        print(f"    {'Diversification Factor (alpha):':<38} {lrc['diversification_factor_alpha']:.4f}")
        print(f"    {'Liquidity Risk Component:':<38} EUR {lrc['liquidity_risk_component']:>10,.2f}")

        mtm = data["mark_to_market_detail"]
        print(f"\n  Mark-to-Market Breakdown:")
        print(f"    {'Premium Margin:':<38} EUR {mtm['premium_margin']:>10,.2f}")
        print(f"    {'Variation Margin:':<38} EUR {mtm['variation_margin']:>10,.2f}")
        print(f"    {'Current Liquidating Margin:':<38} EUR {mtm['current_liquidating_margin']:>10,.2f}")

    s = results["portfolio_summary"]
    print(f"\n{'=' * 60}")
    print(f"  PORTFOLIO SUMMARY ({s['clearing_currency']})")
    print(f"{'=' * 60}")
    print(f"  {'Total Initial Margin:':<40} EUR {s['total_initial_margin']:>12,.2f}")
    print(f"  {'Total Mark-to-Market Margin:':<40} EUR {s['total_mtm_margin']:>12,.2f}")
    print(f"  {'TOTAL MARGIN:':<40} EUR {s['total_margin']:>12,.2f}")
    print("=" * 60 + "\n")