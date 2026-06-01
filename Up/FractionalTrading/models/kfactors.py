"""
K-factor capital requirement model — Upvest Wertpapierinstitut.

Implements IFR (EU) 2019/2033 own funds requirement (Art. 11):
  D = max(FOR, permanent minimum capital, K-factor requirement)

K-factor breakdown (Art. 15):
  RtC = K-ASA (Art. 19) + K-CMH (Art. 18)            [custody + client money]
  RtM = K-NPR (Art. 22)                                [market risk on trading book]
  RtF = K-DTF (Art. 33) + K-TCD (Art. 25-26) + K-CON (Art. 35-39)

K-NPR uses the CRR standardised market risk approach — the same formula as banks.
K-CON progressive factors per IFR Art. 39.

All monetary values in EUR unless otherwise noted.
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─── Load shared assumptions ─────────────────────────────────────────────────

_ASSUMPTIONS = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "assumptions.yaml").read_text()
)


# ─── IFR constants (from Art. 15 Table 1 and Art. 14 / IFD Art. 9) ──────────

PERMANENT_MINIMUM_CAPITAL_EUR = 750_000       # IFD Art. 9 / IFR Art. 14 — for Eigenhandel firms

K_ASA_RATE       = 0.0004    # 0.04%  — Art. 15 Table 1
K_CMH_SEG_RATE   = 0.0040    # 0.40%  — segregated client money
K_CMH_NONSEG_RATE = 0.0050   # 0.50%  — non-segregated client money
K_DTF_CASH_RATE  = 0.0010    # 0.10%  — Art. 15 Table 1
K_DTF_DERIV_RATE = 0.0001    # 0.01%  — Art. 15 Table 1
K_TCD_ALPHA      = 1.2       # Art. 26

# CRR standardised market risk rates (used in K-NPR, IFR Art. 22)
EQUITY_SPECIFIC_RISK_RATE  = 0.08   # 8% of gross position per issuer
EQUITY_GENERAL_RISK_RATE   = 0.08   # 8% of net position (long - short)
FX_GENERAL_RISK_RATE       = 0.08   # 8% of net FX position per currency pair

# K-CON: limit = 25% of own funds (IFR Art. 37(1))
K_CON_LIMIT_PCT = 0.25

# K-CON progressive capital factors on excess (IFR Art. 39, by excess band)
# Key: upper bound of excess as % of limit (None = no upper bound)
# Value: own funds factor applied to the excess in that band
K_CON_EXCESS_BANDS = [
    (0.40,  2.00),   # excess ≤ 40% of limit → 200%
    (0.60,  3.00),   # 40% < excess ≤ 60%   → 300%
    (0.80,  4.00),   # 60% < excess ≤ 80%   → 400%
    (1.00,  5.00),   # 80% < excess ≤ 100%  → 500%
    (2.50,  6.00),   # 100% < excess ≤ 250% → 600%
    (None,  9.00),   # excess > 250%         → 900%
]

# IFR Art. 26 — risk factors per counterparty type for K-TCD
COUNTERPARTY_RISK_FACTORS = {
    "central_government":          0.00,
    "central_bank":                0.00,
    "credit_institution":          0.016,
    "investment_firm_class2":      0.016,
    "corporate":                   0.05,
    "other":                       0.05,
}


# ─── Input dataclasses ───────────────────────────────────────────────────────

@dataclass
class EquityPosition:
    """Single-issuer equity position in the trading book."""
    isin: str
    name: str
    long_eur: float = 0.0    # gross long notional in EUR
    short_eur: float = 0.0   # gross short notional in EUR (positive number)


@dataclass
class FxPosition:
    """Net FX exposure per currency pair (vs EUR)."""
    currency_pair: str        # e.g. "USD/EUR"
    net_eur: float            # positive = long foreign, negative = short foreign


@dataclass
class TcdPosition:
    """OTC derivative / repo / SFT position for K-TCD (IFR Art. 25-26)."""
    counterparty: str
    counterparty_type: str    # key in COUNTERPARTY_RISK_FACTORS
    exposure_eur: float       # current market value of exposure (CVA already included)


@dataclass
class TradingCounterparty:
    """Execution counterparty exposure in the trading book for K-CON."""
    name: str
    trading_book_exposure_eur: float


@dataclass
class KFactorInputs:
    """All inputs required to compute the full K-factor requirement."""

    # ── RtC inputs ──────────────────────────────────────────────────────────
    # K-ASA: rolling 9-month avg of daily assets safeguarded (IFR Art. 19)
    asa_rolling_avg_eur: float = 0.0

    # K-CMH: rolling 9-month avg of daily client money held (IFR Art. 18)
    cmh_segregated_eur: float = 0.0
    cmh_nonsegregated_eur: float = 0.0

    # ── RtM inputs ──────────────────────────────────────────────────────────
    # K-NPR: trading book positions (IFR Art. 22 → CRR standardised approach)
    equity_positions: list[EquityPosition] = field(default_factory=list)
    fx_positions: list[FxPosition] = field(default_factory=list)

    # K-CMG (alternative to K-NPR — requires BaFin approval, IFR Art. 23)
    use_k_cmg: bool = False
    k_cmg_margin_history_eur: list[float] = field(default_factory=list)  # 3+ months daily

    # ── RtF inputs ──────────────────────────────────────────────────────────
    # K-DTF: rolling avg of daily notional trading flow (IFR Art. 33)
    dtf_cash_daily_avg_eur: float = 0.0
    dtf_deriv_daily_avg_eur: float = 0.0

    # K-TCD: OTC derivatives, repos, SFTs (IFR Art. 25-26)
    tcd_positions: list[TcdPosition] = field(default_factory=list)

    # K-CON: trading book exposures per execution counterparty (IFR Art. 35-39)
    counterparties: list[TradingCounterparty] = field(default_factory=list)
    current_own_funds_eur: float = PERMANENT_MINIMUM_CAPITAL_EUR  # used for K-CON limit

    # ── Firm-level inputs ────────────────────────────────────────────────────
    annual_fixed_overheads_eur: float = 0.0   # for FOR calculation (IFR Art. 13)


# ─── K-factor calculation functions ──────────────────────────────────────────

def calc_k_asa(inputs: KFactorInputs) -> float:
    """
    K-ASA = 0.04% × rolling 9-month average of daily ASA (IFR Art. 19).
    ASA = assets safeguarded and administered for clients (Depotgeschäft).
    """
    return inputs.asa_rolling_avg_eur * K_ASA_RATE


def calc_k_cmh(inputs: KFactorInputs) -> float:
    """
    K-CMH = 0.40% × segregated CMH + 0.50% × non-segregated CMH (IFR Art. 18).
    Rolling 9-month average of daily values.
    """
    return (
        inputs.cmh_segregated_eur * K_CMH_SEG_RATE
        + inputs.cmh_nonsegregated_eur * K_CMH_NONSEG_RATE
    )


def calc_k_npr(inputs: KFactorInputs) -> dict:
    """
    K-NPR = CRR standardised market risk approach (IFR Art. 22).

    Equity (per issuer):
      Specific risk  = 8% × gross long position
      General risk   = 8% × net position (long - short)

    FX (per currency pair):
      General risk = 8% × |net FX position|

    Returns breakdown dict and total.
    """
    specific_risk = 0.0
    general_equity_risk = 0.0
    breakdown = []

    for pos in inputs.equity_positions:
        sr = pos.long_eur * EQUITY_SPECIFIC_RISK_RATE
        net = pos.long_eur - pos.short_eur
        gr = abs(net) * EQUITY_GENERAL_RISK_RATE
        specific_risk += sr
        general_equity_risk += gr
        breakdown.append({
            "isin": pos.isin,
            "name": pos.name,
            "long_eur": pos.long_eur,
            "short_eur": pos.short_eur,
            "net_eur": net,
            "specific_risk_eur": sr,
            "general_risk_eur": gr,
        })

    fx_risk = sum(abs(fx.net_eur) * FX_GENERAL_RISK_RATE for fx in inputs.fx_positions)
    total = specific_risk + general_equity_risk + fx_risk

    return {
        "specific_risk_eur": specific_risk,
        "general_equity_risk_eur": general_equity_risk,
        "fx_risk_eur": fx_risk,
        "total_eur": total,
        "positions": breakdown,
    }


def calc_k_cmg(inputs: KFactorInputs) -> float:
    """
    K-CMG = 1.3 × 3rd-highest daily margin over prior 3 months (IFR Art. 23).
    Only used if inputs.use_k_cmg = True and BaFin has approved.
    Requires at least 3 daily margin observations.
    """
    if not inputs.use_k_cmg or len(inputs.k_cmg_margin_history_eur) < 3:
        return 0.0
    sorted_margins = sorted(inputs.k_cmg_margin_history_eur, reverse=True)
    return sorted_margins[2] * 1.3   # 3rd-highest × 1.3


def calc_k_dtf(inputs: KFactorInputs) -> float:
    """
    K-DTF = 0.10% × cash DTF + 0.01% × derivatives DTF (IFR Art. 33).
    DTF = rolling average of daily notional transaction value.
    """
    return (
        inputs.dtf_cash_daily_avg_eur * K_DTF_CASH_RATE
        + inputs.dtf_deriv_daily_avg_eur * K_DTF_DERIV_RATE
    )


def calc_k_tcd(inputs: KFactorInputs) -> dict:
    """
    K-TCD = α × Σ(Exposure × Risk Factor) per position (IFR Art. 26).
    α = 1.2 (fixed per IFR).
    Applies only to OTC derivatives, repos, SFTs (IFR Art. 25).
    """
    total = 0.0
    breakdown = []
    for pos in inputs.tcd_positions:
        risk_factor = COUNTERPARTY_RISK_FACTORS.get(pos.counterparty_type, 0.05)
        charge = K_TCD_ALPHA * pos.exposure_eur * risk_factor
        total += charge
        breakdown.append({
            "counterparty": pos.counterparty,
            "type": pos.counterparty_type,
            "exposure_eur": pos.exposure_eur,
            "risk_factor": risk_factor,
            "charge_eur": charge,
        })
    return {"total_eur": total, "positions": breakdown}


def calc_k_con(inputs: KFactorInputs) -> dict:
    """
    K-CON = progressive capital charge on trading book exposure exceeding
    25% of own funds per counterparty (IFR Art. 35-39).

    Progressive factors per IFR Art. 39 (% of excess × factor):
      ≤40% of limit → ×2.00  |  ≤60% → ×3.00  |  ≤80% → ×4.00
      ≤100% → ×5.00  |  ≤250% → ×6.00  |  >250% → ×9.00
    """
    limit = inputs.current_own_funds_eur * K_CON_LIMIT_PCT
    total_charge = 0.0
    results = []

    for cp in inputs.counterparties:
        excess = max(0.0, cp.trading_book_exposure_eur - limit)
        charge = _k_con_charge(excess, limit)
        total_charge += charge
        results.append({
            "counterparty": cp.name,
            "exposure_eur": cp.trading_book_exposure_eur,
            "limit_eur": limit,
            "excess_eur": excess,
            "charge_eur": charge,
            "breached": excess > 0,
        })

    return {"total_eur": total_charge, "limit_eur": limit, "counterparties": results}


def _k_con_charge(excess: float, limit: float) -> float:
    """Progressive K-CON charge on excess above limit (IFR Art. 39)."""
    if excess <= 0 or limit <= 0:
        return 0.0

    excess_pct_of_limit = excess / limit
    remaining = excess
    charge = 0.0
    prev_upper = 0.0

    for upper_pct, factor in K_CON_EXCESS_BANDS:
        if upper_pct is None:
            # top band — charge all remaining excess
            charge += remaining * factor
            break
        band_eur = (upper_pct - prev_upper) * limit
        in_band = min(remaining, band_eur)
        charge += in_band * factor
        remaining -= in_band
        prev_upper = upper_pct
        if remaining <= 0:
            break

    return charge


# ─── Own funds requirement (IFR Art. 11) ─────────────────────────────────────

def calc_for(inputs: KFactorInputs) -> float:
    """Fixed Overhead Requirement = 1/4 of prior year fixed overheads (IFR Art. 13)."""
    return inputs.annual_fixed_overheads_eur * 0.25


def calc_own_funds_requirement(inputs: KFactorInputs) -> dict:
    """
    Full IFR Art. 11 own funds requirement.
    Returns detailed breakdown of all K-factors and the binding pillar.
    """
    # ── K-factors ────────────────────────────────────────────────────────────
    k_asa = calc_k_asa(inputs)
    k_cmh = calc_k_cmh(inputs)
    rtc   = k_asa + k_cmh

    npr_detail = calc_k_npr(inputs)
    k_npr = npr_detail["total_eur"]
    k_cmg = calc_k_cmg(inputs)
    # Use K-CMG only if explicitly enabled and approved; otherwise K-NPR
    rtm = k_cmg if (inputs.use_k_cmg and k_cmg > 0) else k_npr

    k_dtf = calc_k_dtf(inputs)
    tcd_detail = calc_k_tcd(inputs)
    k_tcd = tcd_detail["total_eur"]
    con_detail = calc_k_con(inputs)
    k_con = con_detail["total_eur"]
    rtf   = k_dtf + k_tcd + k_con

    k_factor_total = rtc + rtm + rtf

    # ── Three pillars ────────────────────────────────────────────────────────
    for_ = calc_for(inputs)
    min_capital = PERMANENT_MINIMUM_CAPITAL_EUR
    requirement = max(for_, min_capital, k_factor_total)

    binding = (
        "FOR" if requirement == for_ and for_ >= k_factor_total and for_ >= min_capital
        else "K-factor" if requirement == k_factor_total and k_factor_total >= for_ and k_factor_total >= min_capital
        else "Permanent minimum"
    )

    return {
        "own_funds_requirement_eur": requirement,
        "binding_pillar": binding,
        "pillars": {
            "FOR_eur": for_,
            "permanent_minimum_eur": min_capital,
            "k_factor_total_eur": k_factor_total,
        },
        "k_factors": {
            "RtC_eur": rtc,
            "K_ASA_eur": k_asa,
            "K_CMH_eur": k_cmh,
            "RtM_eur": rtm,
            "K_NPR_eur": k_npr,
            "K_CMG_eur": k_cmg if inputs.use_k_cmg else None,
            "K_NPR_detail": npr_detail,
            "RtF_eur": rtf,
            "K_DTF_eur": k_dtf,
            "K_TCD_eur": k_tcd,
            "K_TCD_detail": tcd_detail,
            "K_CON_eur": k_con,
            "K_CON_detail": con_detail,
        },
        "inputs_summary": {
            "asa_rolling_avg_eur": inputs.asa_rolling_avg_eur,
            "dtf_cash_daily_avg_eur": inputs.dtf_cash_daily_avg_eur,
            "equity_positions": len(inputs.equity_positions),
            "annual_fixed_overheads_eur": inputs.annual_fixed_overheads_eur,
        },
    }


# ─── Reporting ───────────────────────────────────────────────────────────────

def print_report(result: dict, label: str = "") -> None:
    """Print a formatted own funds requirement report."""
    sep = "─" * 64
    if label:
        print(f"\n{'═' * 64}")
        print(f"  SCENARIO: {label}")
        print(f"{'═' * 64}")

    r = result
    p = r["pillars"]
    k = r["k_factors"]

    print(f"\n{sep}")
    print(f"  OWN FUNDS REQUIREMENT:  €{r['own_funds_requirement_eur']:>14,.0f}")
    print(f"  Binding pillar:          {r['binding_pillar']}")
    print(sep)

    print(f"\n  Pillar A — FOR:                  €{p['FOR_eur']:>12,.0f}")
    print(f"  Pillar B — Permanent minimum:    €{p['permanent_minimum_eur']:>12,.0f}")
    print(f"  Pillar C — K-factor total:       €{p['k_factor_total_eur']:>12,.0f}")

    print(f"\n  ┌─ RtC (Risk-to-Client)          €{k['RtC_eur']:>12,.0f}")
    print(f"  │   K-ASA                        €{k['K_ASA_eur']:>12,.0f}")
    print(f"  │   K-CMH                        €{k['K_CMH_eur']:>12,.0f}")

    rtm_label = "K-CMG" if r["k_factors"]["K_CMG_eur"] is not None else "K-NPR"
    print(f"  ├─ RtM (Risk-to-Market)          €{k['RtM_eur']:>12,.0f}")
    print(f"  │   {rtm_label:<32}  €{k['RtM_eur']:>12,.0f}")

    if k["K_NPR_detail"]["positions"]:
        print(f"  │     (equity positions)")
        for pos in k["K_NPR_detail"]["positions"]:
            print(
                f"  │       {pos['name']:<20} net €{pos['net_eur']:>10,.0f}  "
                f"charge €{pos['specific_risk_eur'] + pos['general_risk_eur']:>8,.0f}"
            )
        if k["K_NPR_detail"]["fx_risk_eur"] > 0:
            print(f"  │       FX risk               €{k['K_NPR_detail']['fx_risk_eur']:>10,.0f}")

    print(f"  └─ RtF (Risk-to-Firm)           €{k['RtF_eur']:>12,.0f}")
    print(f"      K-DTF                        €{k['K_DTF_eur']:>12,.0f}")
    print(f"      K-TCD                        €{k['K_TCD_eur']:>12,.0f}")
    print(f"      K-CON                        €{k['K_CON_eur']:>12,.0f}")

    con = k["K_CON_detail"]
    if con["counterparties"]:
        print(f"\n  K-CON counterparty breakdown (limit: €{con['limit_eur']:,.0f}):")
        for cp in con["counterparties"]:
            status = "⚠ BREACH" if cp["breached"] else "OK"
            print(
                f"    {cp['counterparty']:<25}  exposure €{cp['exposure_eur']:>10,.0f}  "
                f"excess €{cp['excess_eur']:>8,.0f}  [{status}]"
            )

    print(f"\n{sep}\n")


# ─── Scenario runner ─────────────────────────────────────────────────────────

def run_scenarios() -> None:
    """
    Illustrative scenarios for Upvest fractional trading at different growth stages.
    Values are illustrative — replace with actuals from Finance/Operations.
    """

    # ── Scenario 1: Launch phase ─────────────────────────────────────────────
    launch = KFactorInputs(
        # Custody: €50m AUM at launch
        asa_rolling_avg_eur=50_000_000,
        # No client money assumed (pre-funding model)
        cmh_segregated_eur=0,
        # Trading book: small residual positions
        equity_positions=[
            EquityPosition("DE0005140008", "Deutsche Bank", long_eur=15_000),
            EquityPosition("US0378331005", "Apple Inc",     long_eur=25_000),
        ],
        fx_positions=[
            FxPosition("USD/EUR", net_eur=20_000),  # USD Apple inventory unhedged
        ],
        # Daily fractional flow: €5m/day
        dtf_cash_daily_avg_eur=5_000_000,
        # Single execution broker
        counterparties=[
            TradingCounterparty("Prime Broker A", trading_book_exposure_eur=200_000),
        ],
        current_own_funds_eur=1_500_000,
        # Fixed costs: €4m/year
        annual_fixed_overheads_eur=4_000_000,
    )

    # ── Scenario 2: Scaling phase ─────────────────────────────────────────────
    scaling = KFactorInputs(
        # Custody: €500m AUM
        asa_rolling_avg_eur=500_000_000,
        cmh_segregated_eur=0,
        equity_positions=[
            EquityPosition("DE0005140008", "Deutsche Bank", long_eur=120_000),
            EquityPosition("US0378331005", "Apple Inc",     long_eur=300_000),
            EquityPosition("IE00B4L5Y983", "iShares Core MSCI World ETF", long_eur=200_000),
            EquityPosition("NL0009805522", "ASML",          long_eur=80_000),
        ],
        fx_positions=[
            FxPosition("USD/EUR", net_eur=350_000),
        ],
        # €40m/day trading flow
        dtf_cash_daily_avg_eur=40_000_000,
        # Two execution venues — split routing
        counterparties=[
            TradingCounterparty("Prime Broker A", trading_book_exposure_eur=2_500_000),
            TradingCounterparty("Venue B",         trading_book_exposure_eur=800_000),
        ],
        current_own_funds_eur=8_000_000,
        annual_fixed_overheads_eur=10_000_000,
    )

    # ── Scenario 3: Mature phase — K-CON breach illustration ─────────────────
    mature = KFactorInputs(
        # Custody: €2bn AUM
        asa_rolling_avg_eur=2_000_000_000,
        cmh_segregated_eur=5_000_000,   # some client cash in pre-funding pool
        equity_positions=[
            EquityPosition("DE0005140008", "Deutsche Bank", long_eur=500_000),
            EquityPosition("US0378331005", "Apple Inc",     long_eur=1_200_000),
            EquityPosition("IE00B4L5Y983", "iShares Core MSCI World ETF", long_eur=800_000),
            EquityPosition("NL0009805522", "ASML",          long_eur=300_000),
            EquityPosition("FR0000131104", "BNP Paribas",   long_eur=200_000),
        ],
        fx_positions=[
            FxPosition("USD/EUR", net_eur=1_400_000),
            FxPosition("GBP/EUR", net_eur=200_000),
        ],
        # €150m/day trading flow
        dtf_cash_daily_avg_eur=150_000_000,
        # OTC FX forward hedge (triggers K-TCD)
        tcd_positions=[
            TcdPosition("FX Counterparty Bank", "credit_institution", exposure_eur=800_000),
        ],
        # Single broker handles too much → K-CON breach
        counterparties=[
            TradingCounterparty("Prime Broker A", trading_book_exposure_eur=6_000_000),
            TradingCounterparty("Venue B",         trading_book_exposure_eur=1_000_000),
        ],
        current_own_funds_eur=20_000_000,
        annual_fixed_overheads_eur=20_000_000,
    )

    for label, inputs in [
        ("Launch phase  (€50m AUM, €5m/day flow)", launch),
        ("Scaling phase (€500m AUM, €40m/day flow)", scaling),
        ("Mature phase  (€2bn AUM, €150m/day flow) — K-CON breach illustration", mature),
    ]:
        result = calc_own_funds_requirement(inputs)
        print_report(result, label)


# ─── Sensitivity analysis ────────────────────────────────────────────────────

def sensitivity_asa_vs_dtf(
    asa_values_eur: list[float],
    dtf_values_eur: list[float],
    fixed_overheads_eur: float = 10_000_000,
    own_funds_eur: float = 5_000_000,
) -> None:
    """
    Show how K-ASA and K-DTF scale as AUM and daily trading flow grow.
    Useful for capital planning conversations.
    """
    print(f"\n{'═' * 72}")
    print(f"  SENSITIVITY: K-ASA vs K-DTF  (FOR={fixed_overheads_eur/1e6:.0f}m fixed costs/yr)")
    print(f"{'═' * 72}")
    print(f"  {'AUM (custody)':<18} {'K-ASA':>10}   {'Daily flow':>14} {'K-DTF':>10}   {'FOR':>10}")
    print(f"  {'─'*18} {'─'*10}   {'─'*14} {'─'*10}   {'─'*10}")

    for asa, dtf in zip(asa_values_eur, dtf_values_eur):
        k_asa = asa * K_ASA_RATE
        k_dtf = dtf * K_DTF_CASH_RATE
        for_ = fixed_overheads_eur * 0.25
        print(
            f"  €{asa/1e6:>7.0f}m custody    €{k_asa:>8,.0f}   "
            f"€{dtf/1e6:>6.0f}m/day       €{k_dtf:>8,.0f}   "
            f"€{for_:>8,.0f}"
        )
    print()


if __name__ == "__main__":
    run_scenarios()

    sensitivity_asa_vs_dtf(
        asa_values_eur=[50e6, 200e6, 500e6, 1e9, 2e9, 5e9],
        dtf_values_eur=[5e6,  20e6,  50e6,  100e6, 200e6, 500e6],
        fixed_overheads_eur=10_000_000,
    )
