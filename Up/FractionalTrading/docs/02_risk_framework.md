# Fractional Trading — Risk Framework

## Risk Taxonomy

### 1. Market Risk

| Risk | Description | Mitigation |
|------|-------------|------------|
| Price risk between order receipt and execution | Orders aggregate over a window; price moves during that window | Short aggregation windows; real-time price exposure monitoring |
| FX risk (non-EUR instruments) | EUR-denominated fractional orders in USD stocks; FX rate moves between order and settlement | Back-to-back FX hedge or define FX hedge policy; disclose to B2B customers |
| Rounding residual | Aggregated orders don't always sum to a whole share; Upvest holds the residual | Residual position policy — accumulate and net, or use market-maker facility |

### 2. Liquidity Risk

| Risk | Description | Mitigation |
|------|-------------|------------|
| Thin aggregation | Low volume instruments may take long to aggregate to a whole share | Minimum liquidity criteria for eligible instruments; ADV thresholds |
| Market impact | Large aggregated orders in illiquid names move the market | Order size caps relative to ADV (e.g., max 1% of 30-day ADV per batch) |
| Cancellation / withdrawal | Investor cancels after order is partially aggregated | Define cancellation cut-off policy; hold residual or unwind |

### 3. Operational Risk

| Risk | Description | Mitigation |
|------|-------------|------------|
| Reconciliation failure | Internal fractional ledger drifts from actual share position | Daily reconciliation; automated break detection with tolerance thresholds |
| Corporate action attribution | Dividends, splits, mergers must be correctly split across fractional holders | Automated CA processing with fraction-aware attribution engine |
| Settlement failure | Whole-share leg fails at CSD; fractional entitlements already credited | Fail management policy; internal credit/debit until settlement resolves |
| System/technology failure | Aggregation engine down during trading hours | DR/BCP; circuit breaker — halt new fractional orders if engine unavailable |

### 4. Credit & Counterparty Risk

| Risk | Description | Mitigation |
|------|-------------|------------|
| B2B customer default | Customer goes insolvent with open fractional positions | Client asset segregation; pre-funding requirement for fractional orders |
| Execution venue / broker default | Executing broker holds shares in omnibus; defaults | DVP settlement; multi-venue policy; credit limits per counterparty |

### 5. Regulatory & Legal Risk

| Risk | Description | Mitigation |
|------|-------------|------------|
| Instrument classification | Regulators treat fractional entitlements as derivatives → different capital/reporting requirements | Legal opinion on structure; proactive BaFin engagement |
| Best execution | MiFID II requires best execution on the aggregated whole-share order | Best execution policy covering aggregated fractional orders |
| Client asset protection | End investors' fractional entitlements must be protected | Omnibus account with sub-ledger; CSDR compliance |
| Tax | Fractional dividend withholding, capital gains attribution | Tax engine with fraction-aware logic |

---

## Risk Appetite & Limits (Draft)

> To be confirmed with Risk Committee

| Metric | Limit (proposed) | Review frequency |
|--------|------------------|-----------------|
| Max residual position per instrument | €10,000 notional | Daily |
| Max aggregation window | 15 minutes | Intraday |
| Max order size vs. 30d ADV | 1% | Per batch |
| Reconciliation break tolerance | ±0.001 shares | Daily |
| Max FX open exposure (USD/EUR) | €500,000 | Daily |

---

## Controls & Monitoring

- [ ] Pre-trade eligibility check (instrument in approved universe)
- [ ] Real-time position monitoring (residual, FX exposure)
- [ ] End-of-day reconciliation report (fractional ledger vs. custody)
- [ ] Daily corporate action sweep
- [ ] Monthly risk report to Risk Committee
- [ ] Incident escalation runbook for reconciliation breaks

---

## Key Decisions Required

- [ ] Who owns residual positions (Upvest treasury vs. dedicated facility)?
- [ ] Pre-funding vs. post-trade credit for B2B customers?
- [ ] Aggregation window length (balancing latency vs. netting efficiency)
- [ ] Instrument eligibility criteria (ADV, exchange, asset class)
