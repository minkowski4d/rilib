"""
Liquidity risk model for fractional trading.

Estimates:
- Time to aggregate a whole share given expected order flow
- Market impact of the aggregated batch
- Whether an instrument meets minimum ADV eligibility
"""

import yaml
import math
from dataclasses import dataclass
from pathlib import Path


ASSUMPTIONS = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "assumptions.yaml").read_text()
)
MIN_ADV_EUR = ASSUMPTIONS["instrument_eligibility"]["adv_minimum_eur"]
MAX_ADV_PCT = ASSUMPTIONS["risk_limits"]["max_adv_pct"]
MAX_WINDOW_MIN = ASSUMPTIONS["trading"]["aggregation_window_minutes"]


@dataclass
class InstrumentLiquidityProfile:
    isin: str
    name: str
    last_price_eur: float
    adv_30d_eur: float           # 30-day average daily volume in EUR
    expected_daily_order_eur: float  # expected fractional flow from Upvest customers per day


@dataclass
class LiquidityAssessment:
    isin: str
    name: str
    eligible: bool
    ineligibility_reason: str | None
    minutes_to_whole_share: float    # expected time to aggregate one whole share
    daily_batches_estimate: int
    max_batch_notional_eur: float    # ADV-constrained max per batch
    market_impact_bps: float         # rough square-root impact estimate


SQRT_IMPACT_COEFFICIENT = 0.1       # simplified; calibrate to venue


def assess_liquidity(profile: InstrumentLiquidityProfile) -> LiquidityAssessment:
    eligible = True
    reason = None

    if profile.adv_30d_eur < MIN_ADV_EUR:
        eligible = False
        reason = f"ADV €{profile.adv_30d_eur:,.0f} below minimum €{MIN_ADV_EUR:,.0f}"

    max_batch_notional = profile.adv_30d_eur * MAX_ADV_PCT

    # Time to accumulate enough orders to fill one whole share
    eur_per_share = profile.last_price_eur
    daily_minutes = 7 * 60          # 7 trading hours
    eur_per_minute = profile.expected_daily_order_eur / daily_minutes
    minutes_per_share = eur_per_share / eur_per_minute if eur_per_minute > 0 else float("inf")

    if minutes_per_share > MAX_WINDOW_MIN and eligible:
        reason = (reason or "") + f" | Avg {minutes_per_share:.1f} min/share exceeds {MAX_WINDOW_MIN} min window"

    daily_batches = int(profile.expected_daily_order_eur / max_batch_notional) if max_batch_notional > 0 else 0

    # Simplified square-root market impact model
    participation_rate = max_batch_notional / profile.adv_30d_eur
    impact_bps = SQRT_IMPACT_COEFFICIENT * math.sqrt(participation_rate) * 10000

    return LiquidityAssessment(
        isin=profile.isin,
        name=profile.name,
        eligible=eligible,
        ineligibility_reason=reason,
        minutes_to_whole_share=minutes_per_share,
        daily_batches_estimate=daily_batches,
        max_batch_notional_eur=max_batch_notional,
        market_impact_bps=impact_bps,
    )


if __name__ == "__main__":
    instruments = [
        InstrumentLiquidityProfile("DE0005140008", "Deutsche Bank", 12.50, adv_30d_eur=80_000_000,  expected_daily_order_eur=50_000),
        InstrumentLiquidityProfile("US0378331005", "Apple",         190.0, adv_30d_eur=500_000_000, expected_daily_order_eur=200_000),
        InstrumentLiquidityProfile("DE000XYZ0001", "Small Cap",     45.00, adv_30d_eur=300_000,     expected_daily_order_eur=5_000),
    ]

    print(f"{'ISIN':<14} {'Name':<16} {'Eligible':<9} {'Min/Share':>10} {'Impact bps':>11} {'Reason'}")
    print("-" * 90)
    for p in instruments:
        a = assess_liquidity(p)
        print(
            f"{a.isin:<14} {a.name:<16} {'YES' if a.eligible else 'NO':<9} "
            f"{a.minutes_to_whole_share:>10.1f} {a.market_impact_bps:>11.2f} "
            f"{a.ineligibility_reason or ''}"
        )
