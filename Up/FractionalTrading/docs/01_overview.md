# Fractional Trading — Product Overview

## What Is Fractional Trading?

Fractional trading allows end investors to buy a fraction of a single share rather than a whole unit. For example, buying €50 of a €3,000 stock means owning ~0.0167 shares.

### Why It Matters for Upvest's B2B Customers

Upvest provides investment infrastructure to fintechs, neobanks, and brokers. Their B2B customers build retail investment products on top of Upvest's backend (order routing, custody, settlement, compliance). Fractional trading is a key feature for:

- **Democratisation** — retail investors with small ticket sizes can access high-priced stocks
- **Euro-based investing** — customers invest fixed EUR amounts, not share quantities
- **Portfolio diversification** — fractional access enables broad exposure on small budgets
- **Competitive parity** — most neo-brokers (Trade Republic, Scalable, Revolut) already offer it

---

## Upvest's B2B Operating Model

```
End Investor
    │  (app/UX)
    ▼
B2B Customer (neobank, fintech, broker)
    │  (API calls to Upvest)
    ▼
Upvest Infrastructure
    │  order aggregation, custody, settlement
    ▼
Execution Venue / Market
```

**Key implication for risk:** Upvest aggregates fractional orders across multiple B2B customers and their end users, executes whole shares in the market, and distributes fractional entitlements internally. Upvest bears the aggregation and reconciliation risk; B2B customers bear the relationship with end investors.

---

## Regulatory Context

| Topic | Detail |
|-------|--------|
| Jurisdiction | Germany (BaFin), EU (MiFID II/MiFIR) |
| Instrument classification | Fractional shares may not qualify as transferable securities under MiFID II — could be treated as contracts (derivative-like) depending on structure |
| Custody | CSDR / CRR — requires clear segregation of client assets |
| Settlement | T+2 standard; fractional internal bookkeeping must reconcile with whole-share settlement |
| Corporate actions | Dividends, splits, rights issues must be attributed proportionally to fractional holders |
| Reporting | MiFID II transaction reporting on the underlying whole-share execution |

---

## Instruments in Scope (v1 Proposal)

- [ ] EU-listed equities (Xetra, Euronext)
- [ ] US-listed equities (NYSE, NASDAQ) — FX risk applies
- [ ] ETFs
- [ ] Exclude: bonds, derivatives, crypto

---

## Open Questions

- Which instrument universe for v1?
- Minimum fraction size (e.g., 0.001 shares, or €1 minimum notional)?
- EUR-only or multi-currency in v1?
- Will Upvest use a single omnibus account or segregated accounts per B2B client?
