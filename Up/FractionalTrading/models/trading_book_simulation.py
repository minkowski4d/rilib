"""
Trading book simulation — Upvest fractional trading.

Fixed parameters (from user input):
  - Total fractional order flow:  EUR 40m / day
  - Inventory thresholds:         min = 2 shares, max = 5 shares per instrument
  - Order throughput capacity:    10–20 trades / second
  - Price range:                  EUR 0.01 – 400
  - Instrument universe:          up to 5,000 instruments
  - Distribution:                 80% priced below EUR 50 (Tier A),
                                  20% priced above EUR 50 (Tier B)

Key insight: at very low prices, a fixed 3-share replenishment window creates
enormous throughput pressure. The simulation exposes this and recommends
price-adaptive replenishment sizes.
"""

import math
import yaml
from dataclasses import dataclass, field
from pathlib import Path

_ASSUMPTIONS = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "assumptions.yaml").read_text()
)

ORDER_FLOW_EUR_DAY       = 40_000_000
MIN_INVENTORY_SHARES     = 2
MAX_INVENTORY_SHARES     = 5
REPLENISHMENT_SIZE       = MAX_INVENTORY_SHARES - MIN_INVENTORY_SHARES   # 3
RESIDUAL_SELL_RATIO      = 0.08
TRADING_HOURS_PER_DAY    = 7
TRADING_SECONDS_PER_DAY  = TRADING_HOURS_PER_DAY * 3_600
K_DTF_CASH_RATE          = 0.001
K_NPR_EQUITY_RATE        = 0.16
CAPACITY_LOW             = 10
CAPACITY_HIGH            = 20


# ── Price-adaptive replenishment sizes ───────────────────────────────────────
# For cheap stocks a 3-share window generates unsustainable throughput.
# These tiers define the recommended replenishment size per price band.
PRICE_TIERS = [
    (0.01,   5,    500,   "< EUR 5     (micro-cap / penny)"),
    (5,      20,   100,   "EUR 5–20   (small)"),
    (20,     50,   30,    "EUR 20–50  (mid-small)"),
    (50,     150,  10,    "EUR 50–150 (mid)"),
    (150,    400,  3,     "EUR 150–400 (premium)"),
]

def adaptive_replenishment(price: float) -> int:
    for lo, hi, r, _ in PRICE_TIERS:
        if lo <= price < hi:
            return r
    return 3  # fallback for price ≥ 400


@dataclass
class ScenarioResult:
    label: str
    n_instruments: int
    avg_price_eur: float
    replenishment_size: int
    flow_per_instrument_eur: float
    shares_demanded_per_instrument_day: float
    replenishments_per_instrument_day: float
    total_replenishments_day: float
    trades_per_second: float
    buy_notional_day_eur: float
    sell_notional_day_eur: float
    total_dtf_day_eur: float
    k_dtf_eur: float
    avg_inventory_notional_eur: float
    k_npr_eur: float
    capacity_util_low_pct: float
    capacity_util_high_pct: float
    capacity_ok: bool


def simulate(n_instruments: int, avg_price_eur: float,
             replenishment_size: int = None,
             label: str = "") -> ScenarioResult:
    r = replenishment_size or REPLENISHMENT_SIZE
    flow_per_instr   = ORDER_FLOW_EUR_DAY / n_instruments
    shares_per_day   = flow_per_instr / avg_price_eur
    replenish_per_day = math.ceil(shares_per_day / r)
    total_replenishments = replenish_per_day * n_instruments
    trades_per_sec       = total_replenishments / TRADING_SECONDS_PER_DAY
    buy_notional         = ORDER_FLOW_EUR_DAY
    sell_notional        = ORDER_FLOW_EUR_DAY * RESIDUAL_SELL_RATIO
    total_dtf            = buy_notional + sell_notional
    k_dtf                = total_dtf * K_DTF_CASH_RATE
    avg_inv_shares       = (MAX_INVENTORY_SHARES + MIN_INVENTORY_SHARES) / 2
    avg_inv_notional     = n_instruments * avg_inv_shares * avg_price_eur
    k_npr                = avg_inv_notional * K_NPR_EQUITY_RATE
    return ScenarioResult(
        label=label, n_instruments=n_instruments,
        avg_price_eur=avg_price_eur, replenishment_size=r,
        flow_per_instrument_eur=flow_per_instr,
        shares_demanded_per_instrument_day=shares_per_day,
        replenishments_per_instrument_day=replenish_per_day,
        total_replenishments_day=total_replenishments,
        trades_per_second=trades_per_sec,
        buy_notional_day_eur=buy_notional,
        sell_notional_day_eur=sell_notional,
        total_dtf_day_eur=total_dtf,
        k_dtf_eur=k_dtf,
        avg_inventory_notional_eur=avg_inv_notional,
        k_npr_eur=k_npr,
        capacity_util_low_pct=trades_per_sec / CAPACITY_LOW * 100,
        capacity_util_high_pct=trades_per_sec / CAPACITY_HIGH * 100,
        capacity_ok=trades_per_sec <= CAPACITY_HIGH,
    )


def simulate_two_tier(n_total: int, pct_cheap: float,
                      avg_price_cheap: float, avg_price_expensive: float,
                      flow_pct_cheap: float = 0.6) -> dict:
    """
    Realistic universe: two price tiers with separate flow allocation.
    n_total        — total instrument count
    pct_cheap      — fraction of instruments in cheap tier (e.g. 0.80)
    avg_price_cheap — average price in cheap tier (e.g. EUR 25)
    avg_price_expensive — average price in expensive tier (e.g. EUR 200)
    flow_pct_cheap — fraction of total flow allocated to cheap tier
    """
    n_cheap = round(n_total * pct_cheap)
    n_exp   = n_total - n_cheap
    flow_cheap = ORDER_FLOW_EUR_DAY * flow_pct_cheap
    flow_exp   = ORDER_FLOW_EUR_DAY * (1 - flow_pct_cheap)

    r_cheap = adaptive_replenishment(avg_price_cheap)
    r_exp   = adaptive_replenishment(avg_price_expensive)

    flow_per_cheap = flow_cheap / n_cheap if n_cheap else 0
    flow_per_exp   = flow_exp   / n_exp   if n_exp   else 0

    shares_cheap  = flow_per_cheap / avg_price_cheap if avg_price_cheap else 0
    shares_exp    = flow_per_exp   / avg_price_expensive if avg_price_expensive else 0

    rep_cheap = math.ceil(shares_cheap / r_cheap) if shares_cheap else 0
    rep_exp   = math.ceil(shares_exp   / r_exp)   if shares_exp   else 0

    total_trades_day = n_cheap * rep_cheap + n_exp * rep_exp
    trades_per_sec   = total_trades_day / TRADING_SECONDS_PER_DAY

    avg_s = (MAX_INVENTORY_SHARES + MIN_INVENTORY_SHARES) / 2
    inv_cheap = n_cheap * avg_s * avg_price_cheap
    inv_exp   = n_exp   * avg_s * avg_price_expensive
    total_inv = inv_cheap + inv_exp
    k_npr     = total_inv * K_NPR_EQUITY_RATE

    buy_notional = ORDER_FLOW_EUR_DAY
    k_dtf        = buy_notional * (1 + RESIDUAL_SELL_RATIO) * K_DTF_CASH_RATE
    weighted_avg_price = (n_cheap * avg_price_cheap + n_exp * avg_price_expensive) / n_total

    return {
        "n_total": n_total, "n_cheap": n_cheap, "n_expensive": n_exp,
        "pct_cheap": pct_cheap, "avg_price_cheap": avg_price_cheap,
        "avg_price_expensive": avg_price_expensive,
        "weighted_avg_price": weighted_avg_price,
        "r_cheap": r_cheap, "r_exp": r_exp,
        "flow_per_cheap_eur": flow_per_cheap, "flow_per_exp_eur": flow_per_exp,
        "trades_cheap_day": n_cheap * rep_cheap,
        "trades_exp_day":   n_exp   * rep_exp,
        "total_trades_day": total_trades_day,
        "trades_per_second": trades_per_sec,
        "capacity_ok": trades_per_sec <= CAPACITY_HIGH,
        "avg_inventory_notional_eur": total_inv,
        "k_npr_eur": k_npr,
        "k_dtf_eur": k_dtf,
    }


def min_avg_price_for_capacity(replenishment_size: int = REPLENISHMENT_SIZE,
                                capacity_per_sec: float = CAPACITY_HIGH) -> float:
    return ORDER_FLOW_EUR_DAY / (
        replenishment_size * capacity_per_sec * TRADING_SECONDS_PER_DAY
    )


def print_scenario(r: ScenarioResult) -> None:
    status = "✓" if r.capacity_ok else "✗ OVER"
    print(f"  {r.label or ''}")
    print(f"  {r.n_instruments:>5,} instruments | EUR {r.avg_price_eur:>7.2f} avg | "
          f"replenish={r.replenishment_size} shares | "
          f"{r.trades_per_second:>6.1f} trades/sec [{status}]")
    print(f"  K-DTF: EUR {r.k_dtf_eur:>8,.0f}  |  "
          f"K-NPR: EUR {r.k_npr_eur:>8,.0f}  |  "
          f"Inventory: EUR {r.avg_inventory_notional_eur:>10,.0f}")
    print()


def print_tier_table() -> None:
    print(f"\n{'═'*70}")
    print(f"  PRICE-ADAPTIVE REPLENISHMENT TIERS")
    print(f"{'═'*70}")
    print(f"  {'Price range':<20} {'Rep. size':>10} {'Min price@20/sec':>18}")
    print(f"  {'─'*20} {'─'*10} {'─'*18}")
    for lo, hi, r, label in PRICE_TIERS:
        p_min = min_avg_price_for_capacity(r, CAPACITY_HIGH)
        print(f"  {label:<20} {r:>10} shares   EUR {p_min:>8.2f}")


def print_two_tier(res: dict) -> None:
    status = "✓" if res["capacity_ok"] else "✗ OVER CAPACITY"
    print(f"  {res['n_total']:,} instruments  "
          f"({res['pct_cheap']:.0%} × EUR {res['avg_price_cheap']:.0f}  +  "
          f"{1-res['pct_cheap']:.0%} × EUR {res['avg_price_expensive']:.0f})  "
          f"weighted avg EUR {res['weighted_avg_price']:.1f}")
    print(f"  Replenishment: cheap={res['r_cheap']} shares, expensive={res['r_exp']} shares")
    print(f"  Trades/sec: {res['trades_per_second']:.1f}  [{status}]")
    print(f"  K-DTF: EUR {res['k_dtf_eur']:,.0f}  |  "
          f"K-NPR: EUR {res['k_npr_eur']:,.0f}  |  "
          f"Inventory: EUR {res['avg_inventory_notional_eur']:,.0f}")
    print()


if __name__ == "__main__":
    print(f"\n{'═'*70}")
    print(f"  UPVEST FRACTIONAL TRADING — TRADING BOOK SIMULATION")
    print(f"  Flow: EUR {ORDER_FLOW_EUR_DAY/1e6:.0f}m/day  |  "
          f"Thresholds: min={MIN_INVENTORY_SHARES}, max={MAX_INVENTORY_SHARES}  |  "
          f"Capacity: {CAPACITY_LOW}–{CAPACITY_HIGH} trades/sec")
    print(f"{'═'*70}")

    print("\n── Single-tier scenarios (fixed replenishment = 3 shares) ──")
    for n, p, lbl in [
        (100,  50,   "100 instruments, EUR 50  avg"),
        (100,  100,  "100 instruments, EUR 100 avg"),
        (500,  100,  "500 instruments, EUR 100 avg"),
        (5000, 25,   "5,000 instruments, EUR 25 avg (cheap-heavy)"),
        (5000, 60,   "5,000 instruments, EUR 60 avg (realistic weighted)"),
        (5000, 200,  "5,000 instruments, EUR 200 avg (premium-heavy)"),
    ]:
        print_scenario(simulate(n, p, label=lbl))

    print("\n── Price-adaptive replenishment tiers ──")
    print_tier_table()

    print(f"\n\n── Realistic 80/20 universe — 5,000 instruments ──")
    print(f"  Assumptions: 80% cheap (avg EUR 25), 20% expensive (avg EUR 200),")
    print(f"  flow allocation 60% to cheap tier / 40% to expensive tier\n")
    for flow_split in [0.60, 0.50, 0.40]:
        res = simulate_two_tier(
            n_total=5000, pct_cheap=0.80,
            avg_price_cheap=25, avg_price_expensive=200,
            flow_pct_cheap=flow_split
        )
        print(f"  Flow split {flow_split:.0%} cheap / {1-flow_split:.0%} expensive:")
        print_two_tier(res)

    print("\n── Capacity: minimum price per replenishment size ──")
    print(f"  (N cancels — minimum price depends only on flow, rep.size, capacity)\n")
    print(f"  {'Rep. size':>10} {'@ 10/sec':>14} {'@ 20/sec':>14}")
    for r in [3, 10, 30, 100, 500]:
        pl = min_avg_price_for_capacity(r, CAPACITY_LOW)
        ph = min_avg_price_for_capacity(r, CAPACITY_HIGH)
        print(f"  {r:>10} shares   EUR {pl:>8.2f}    EUR {ph:>8.2f}")
