# Fractional Trading — Rollout Plan

## Phased Approach

### Phase 0 — Scoping & Design (Now → Q3 2026)

- [ ] Confirm instrument universe and minimum fraction size
- [ ] Legal opinion on regulatory classification
- [ ] Define custody model and client asset structure
- [ ] Risk framework v1 sign-off (Risk Committee)
- [ ] Technology architecture design (aggregation engine, ledger)
- [ ] Define B2B API contract changes
- [ ] BaFin pre-notification / regulatory engagement if required

**Exit criteria:** Legal sign-off, risk framework approved, architecture agreed

---

### Phase 1 — Internal Testing (Q3 2026)

- [ ] Aggregation engine built and unit tested
- [ ] Fractional ledger reconciliation tested
- [ ] Corporate action attribution tested (dividends, splits)
- [ ] FX handling validated
- [ ] UAT with internal stakeholders
- [ ] Dry-run reconciliation vs. simulated custody positions

**Exit criteria:** Zero critical bugs; reconciliation accuracy ≥99.99%; all risk controls operational

---

### Phase 2 — Pilot with 1-2 B2B Customers (Q4 2026)

- [ ] Select pilot B2B customers (controlled, cooperative partners)
- [ ] Restricted instrument universe (e.g., top 50 EU equities only)
- [ ] Daily manual oversight of reconciliation and residuals
- [ ] Weekly review of risk metrics vs. limits
- [ ] Incident runbook tested

**Exit criteria:** 4 weeks clean operation; no material reconciliation breaks; risk limits respected

---

### Phase 3 — General Availability (Q1 2027)

- [ ] Open to all B2B customers
- [ ] Expanded instrument universe
- [ ] Automated monitoring and alerting fully operational
- [ ] Risk reporting integrated into standard MI pack

---

## Go-Live Risk Checklist

| Item | Owner | Status |
|------|-------|--------|
| Legal opinion on instrument classification | Legal | TBD |
| Custody model confirmed | Operations | TBD |
| Risk framework approved | Risk Committee | TBD |
| Reconciliation engine tested | Technology | TBD |
| Corporate action logic validated | Operations + Tech | TBD |
| Best execution policy updated | Compliance | TBD |
| B2B customer agreements updated | Legal | TBD |
| BaFin engagement complete | Compliance | TBD |
| Incident runbook signed off | Risk + Ops | TBD |
| Risk limits set and loaded | Risk | TBD |

---

## Dependencies & Risks to Plan

| Dependency | Risk to timeline |
|------------|-----------------|
| BaFin regulatory clarity on fractional classification | High — could require product restructuring |
| Execution venue API support for fractional aggregation | Medium |
| B2B customer willingness to pilot | Low |
| Internal engineering capacity | Medium |
