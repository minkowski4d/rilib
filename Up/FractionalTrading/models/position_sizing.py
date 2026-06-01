"""
Fractional order sizing and aggregation model.

Given a set of fractional buy/sell orders in EUR, calculates:
- How many whole shares to execute
- The residual (sub-share remainder Upvest holds)
- Whether the batch breaches ADV limits
"""

import yaml
from dataclasses import dataclass
from pathlib import Path


ASSUMPTIONS = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "assumptions.yaml").read_text()
)
MAX_ADV_PCT = ASSUMPTIONS["risk_limits"]["max_adv_pct"]
MAX_RESIDUAL_EUR = ASSUMPTIONS["risk_limits"]["max_residual_notional_eur"]


@dataclass
class FractionalOrder:
    order_id: str
    side: str                  # "buy" | "sell"
    notional_eur: float        # EUR amount the investor wants to invest
    price_eur: float           # current indicative price


@dataclass
class BatchResult:
    isin: str
    side: str
    gross_shares_requested: float    # sum of fractional entitlements
    whole_shares_to_execute: int     # floor for buys, ceil for sells (or vice versa)
    residual_shares: float           # what Upvest holds
    residual_notional_eur: float
    adv_30d_eur: float
    adv_pct: float
    adv_limit_breached: bool
    residual_limit_breached: bool


def size_batch(
    isin: str,
    orders: list[FractionalOrder],
    adv_30d_eur: float,
) -> BatchResult:
    side = orders[0].side
    avg_price = sum(o.price_eur for o in orders) / len(orders)

    gross_shares = sum(o.notional_eur / o.price_eur for o in orders)
    whole_shares = int(gross_shares)           # floor — Upvest retains the residual
    residual = gross_shares - whole_shares
    residual_notional = residual * avg_price

    batch_notional = whole_shares * avg_price
    adv_pct = batch_notional / adv_30d_eur if adv_30d_eur > 0 else float("inf")

    return BatchResult(
        isin=isin,
        side=side,
        gross_shares_requested=gross_shares,
        whole_shares_to_execute=whole_shares,
        residual_shares=residual,
        residual_notional_eur=residual_notional,
        adv_30d_eur=adv_30d_eur,
        adv_pct=adv_pct,
        adv_limit_breached=adv_pct > MAX_ADV_PCT,
        residual_limit_breached=residual_notional > MAX_RESIDUAL_EUR,
    )


def allocate_fills(
    orders: list[FractionalOrder],
    execution_price_eur: float,
) -> list[dict]:
    """Allocate whole-share fill back to fractional investors pro-rata."""
    total_notional = sum(o.notional_eur for o in orders)
    fills = []
    for o in orders:
        weight = o.notional_eur / total_notional
        shares_allocated = (o.notional_eur / execution_price_eur)
        fills.append({
            "order_id": o.order_id,
            "shares_allocated": round(shares_allocated, 8),
            "notional_eur": o.notional_eur,
            "execution_price_eur": execution_price_eur,
            "weight": round(weight, 6),
        })
    return fills


if __name__ == "__main__":
    orders = [
        FractionalOrder("O001", "buy", notional_eur=50.00,  price_eur=190.00),
        FractionalOrder("O002", "buy", notional_eur=200.00, price_eur=190.00),
        FractionalOrder("O003", "buy", notional_eur=95.00,  price_eur=190.00),
    ]

    result = size_batch("US0378331005", orders, adv_30d_eur=50_000_000)
    print(f"Gross shares: {result.gross_shares_requested:.6f}")
    print(f"Whole shares to execute: {result.whole_shares_to_execute}")
    print(f"Residual: {result.residual_shares:.6f} shares = €{result.residual_notional_eur:.2f}")
    print(f"ADV %: {result.adv_pct:.4%} | Limit breached: {result.adv_limit_breached}")

    print("\nFill allocation:")
    for fill in allocate_fills(orders, execution_price_eur=190.50):
        print(f"  {fill['order_id']}: {fill['shares_allocated']} shares @ €{fill['execution_price_eur']}")
