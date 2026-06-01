"""
Fractional share reconciliation model.

Checks that the sum of all fractional entitlements in the internal ledger
matches the whole-share position held in custody for each instrument.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path


ASSUMPTIONS = yaml.safe_load(
    (Path(__file__).parent.parent / "data" / "assumptions.yaml").read_text()
)
TOLERANCE = ASSUMPTIONS["risk_limits"]["reconciliation_tolerance_shares"]


@dataclass
class InstrumentPosition:
    isin: str
    custody_shares: float          # whole shares held at CSD
    ledger_shares: float           # sum of all fractional entitlements in internal ledger
    last_price_eur: float


@dataclass
class ReconciliationResult:
    isin: str
    break_shares: float
    break_notional_eur: float
    within_tolerance: bool
    status: str                    # "OK" | "WARN" | "BREAK"


def reconcile(positions: list[InstrumentPosition]) -> list[ReconciliationResult]:
    results = []
    for pos in positions:
        diff = pos.custody_shares - pos.ledger_shares
        notional = abs(diff) * pos.last_price_eur
        within = abs(diff) <= TOLERANCE

        if abs(diff) == 0:
            status = "OK"
        elif within:
            status = "WARN"
        else:
            status = "BREAK"

        results.append(ReconciliationResult(
            isin=pos.isin,
            break_shares=diff,
            break_notional_eur=notional,
            within_tolerance=within,
            status=status,
        ))
    return results


def reconciliation_summary(results: list[ReconciliationResult]) -> dict:
    breaks = [r for r in results if r.status == "BREAK"]
    warns = [r for r in results if r.status == "WARN"]
    total_break_notional = sum(r.break_notional_eur for r in breaks)

    return {
        "total_instruments": len(results),
        "ok": len(results) - len(breaks) - len(warns),
        "warnings": len(warns),
        "breaks": len(breaks),
        "total_break_notional_eur": total_break_notional,
        "requires_escalation": len(breaks) > 0,
    }


if __name__ == "__main__":
    # Example / smoke test
    sample = [
        InstrumentPosition("DE0005140008", custody_shares=100.0, ledger_shares=99.9995, last_price_eur=12.50),
        InstrumentPosition("US0378331005", custody_shares=10.0,  ledger_shares=10.002,  last_price_eur=190.00),
        InstrumentPosition("IE00B4L5Y983", custody_shares=50.0,  ledger_shares=49.950,  last_price_eur=85.00),
    ]
    results = reconcile(sample)
    for r in results:
        print(f"{r.isin}: {r.status} | break={r.break_shares:.4f} shares | €{r.break_notional_eur:.2f}")
    print("\nSummary:", reconciliation_summary(results))
