# Fractional Trading — Upvest Risk Management

## Overview

This repository contains documentation, risk frameworks, and quantitative models supporting the launch of Fractional Trading for Upvest's B2B customers.

**Owner:** Head of Risk Management  
**Status:** Pre-launch — scoping & framework design  
**Last updated:** 2026-05-30

---

## Contents

| Path | Purpose |
|------|---------|
| `docs/01_overview.md` | Product overview, B2B model, regulatory context |
| `docs/02_risk_framework.md` | Risk taxonomy and controls |
| `docs/03_rollout_plan.md` | Phased launch plan and go-live criteria |
| `docs/meetings/` | Per-meeting notes and action items |
| `models/` | Quantitative models (reconciliation, liquidity, sizing) |
| `data/assumptions.yaml` | Shared inputs and parameters across models |

---

## Key Open Questions

- [ ] Custody model: Upvest-held omnibus account vs. segregated per B2B client?
- [ ] Which instruments in scope for v1? (equities only, or ETFs too?)
- [ ] Minimum fraction size and rounding convention
- [ ] How are corporate actions (dividends, splits) attributed to fractional holders?
- [ ] Regulatory classification: shares vs. derivative instruments by jurisdiction
- [ ] B2B customer onboarding requirements and risk limits

---

## Contacts & Links

- Upvest regulatory entity: Upvest GmbH (BaFin regulated)
- Relevant regulation: MiFID II, WpHG, CSDR
