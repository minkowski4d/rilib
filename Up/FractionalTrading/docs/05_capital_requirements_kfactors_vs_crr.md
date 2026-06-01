# Capital Requirements — IFR K-Factors vs. CRR (Banks)

> **Sources:** IFR (EU) 2019/2033, consolidated 09.01.2024 (primary); CRR (EU) 575/2013 (primary); both available in `docs/regulation/`.

---

## 1. Why Two Different Capital Frameworks?

Upvest is regulated under **IFR (EU) 2019/2033** — the Investment Firms Regulation — not CRR (the Capital Requirements Regulation for banks). The EU introduced IFR/IFD in 2021 specifically because the CRR bank framework was poorly calibrated for investment firms: it over-capitalised some activities and under-capitalised others.

| Dimension | **IFR (Investment Firms)** | **CRR (Banks)** |
|-----------|--------------------------|-----------------|
| Framework logic | Activity-based K-factors aligned to actual risks posed | RWA-based (credit, market, operational risk) |
| Market risk | K-NPR = same CRR standardised approach for trading book | CRR Title IV Part Three (FRTB or standardised) |
| Credit risk | Not separately capitalised (no loan book) | Standardised or IRB; 8% × RWA |
| Operational risk | Implicit in Fixed Overhead Requirement (FOR) | BIA / Standardised / AMA; 8% × RWA |
| Custody/AUM | K-ASA (0.04%), K-AUM (0.02%) | Not separately treated (off-balance sheet) |
| Leverage ratio | **Not required** under IFR | Min 3% Tier 1 / total exposure (CRR Art. 92(1)(d)) |
| Liquidity | 1/3 of FOR in liquid assets (IFR Art. 43) | LCR (100%) + NSFR (100%) |
| Capital minimum | €750,000 for Eigenhandel (IFD Art. 9) | €5m for bank licence |
| Proportionality | Explicit: Class 1 (CRR), Class 2 (K-factors), Class 3 (FOR + minimum only) | Proportionality in Pillar 2 only |

**Key connection:** K-NPR directly uses the **CRR market risk standardised approach** (IFR Art. 22). This is the single most important bridge between the two frameworks. When computing K-NPR, Upvest applies the same market risk capital formula as a bank would for its trading book.

---

## 2. CRR Threshold — When Upvest Would Switch Frameworks

Under **IFR Art. 1(2)**, investment firms authorised to deal on own account (MiFID II Annex I Sec A pt 3) must apply **CRR (bank framework)** if:

- Consolidated total assets **≥ €15 billion**, OR
- The firm is part of a group where at least one entity doing dealing on own account has consolidated total assets ≥ €15 billion

If Upvest crosses this threshold, it would be supervised as a bank-equivalent under CRR, requiring:
- Full credit risk RWA (even without a loan book, securities and trading exposures attract RWA)
- Full operational risk RWA
- LCR and NSFR compliance
- Leverage ratio compliance
- Much higher minimum capital (€5m vs €750,000)

This threshold is the key strategic growth trigger to monitor.

---

## 3. Upvest's Own Funds Requirement — The Three Pillars

IFR Art. 11(1): Own funds must equal the **highest** of:

```
D = max( FOR,  Permanent Minimum Capital,  K-factor Requirement )
```

### Pillar A — Fixed Overhead Requirement (FOR) — IFR Art. 13

```
FOR = 1/4 × (prior year total fixed overhead expenses)
```

Fixed overheads exclude: variable staff bonuses, profit-sharing, discretionary variable remuneration, commission payable contingent on commission receivable, fees to tied agents, non-recurring extraordinary items.

**Practical implication for Upvest:** As a scaling fintech, fixed costs (staff, technology, regulatory) may grow faster than trading volume in the early phase. FOR may be the binding constraint before K-factors become material.

*Example:* Annual fixed overheads €12m → FOR = €3m. If K-factor total = €1.5m and minimum = €750,000 → FOR is the binding constraint.

### Pillar B — Permanent Minimum Capital — IFR Art. 14 / IFD Art. 9

For firms authorised to deal on own account: **€750,000**

This is the absolute floor regardless of activity levels. It cannot be offset by any calculation.

### Pillar C — K-Factor Requirement — IFR Art. 15

```
K-factor Requirement = RtC + RtM + RtF
```

where:
- **RtC** = Risk-to-Client = K-AUM + K-CMH + K-ASA + K-COH (IFR Art. 16)
- **RtM** = Risk-to-Market = K-NPR *or* K-CMG (IFR Art. 21)
- **RtF** = Risk-to-Firm = K-TCD + K-DTF + K-CON (IFR Art. 24)

---

## 4. K-Factors Applicable to Upvest — Detail

### 4.1 RtM — Risk-to-Market

#### K-NPR (Net Position Risk) — IFR Art. 22

This is the **direct link to CRR**. K-NPR for Upvest's proprietary equity positions (fractional trading inventory and residuals) is calculated using the **CRR market risk standardised approach** (CRR Part Three, Title IV, Chapters 2–4 or the alternative approaches under FRTB).

**Under the CRR standardised approach for equities in the trading book:**

| Risk component | Rate | Basis |
|---------------|------|-------|
| Specific risk | 8% | Gross long position per issuer |
| General market risk | 8% | Net overall equity position (long − short) |
| **Combined (pure long position)** | **~16%** | Net = gross for Upvest (no shorts in fractional model) |

*Example:* Upvest holds a residual inventory of €500,000 in equities at end of day:
- Specific risk: 8% × €500,000 = €40,000
- General risk: 8% × €500,000 = €40,000
- **K-NPR contribution: ~€80,000**

For FX positions (USD/EUR from US stock inventory) — additional general market risk charge applies.

**Three calculation approaches available (IFR Art. 22):**
1. **Standardised approach** (CRR Chapters 2–4, Title IV, Part Three) — most common; Upvest should default to this
2. Alternative standardised approach (CRR Chapter 1a) — FRTB sensitivities-based; more complex but potentially lower for diversified books
3. Alternative internal model approach (CRR Chapter 1b) — requires regulatory approval; not appropriate at this stage

#### K-CMG (Clearing Margin Given) — IFR Art. 23

```
K-CMG = 1.3 × (3rd highest daily margin called by clearing member over prior 3 months)
```

K-CMG is an **alternative** to K-NPR — a firm can only use one, not both. It is available only if:
- The firm is **not part of a group containing a credit institution** (Art. 23(1)(a))
- All positions clear through a qualifying central counterparty (QCCP) under a clearing member (Art. 23(1)(b))
- The clearing member is a credit institution or Art. 1(2) IFR firm
- BaFin has **assessed and explicitly approved** this approach (not just notified)
- The choice is not made for regulatory arbitrage purposes (Art. 23(1)(e))

**Implication for Upvest:** Unless Upvest centrally clears virtually all equity positions through a QCCP (Eurex, LCH) and has BaFin approval, **K-NPR is the applicable approach**. For a cash equity fractional business, K-NPR is the realistic path.

---

### 4.2 RtC — Risk-to-Client (IFR Art. 16)

```
RtC = K-AUM + K-CMH + K-ASA + K-COH
```

| K-factor | IFR Article | Coefficient | Applies to Upvest? | Notes |
|----------|------------|------------|-------------------|-------|
| **K-AUM** | Art. 17 | 0.02% | No | Only for portfolio managers — Upvest does not manage client portfolios |
| **K-CMH** | Art. 18 | 0.4% / 0.5% | **TBC** | If Upvest holds client cash money (even transiently for pre-funding fractional orders), CMH ≠ 0 → K-CMH applies. Segregated accounts: 0.4%; non-segregated: 0.5%. Verify with Finance. |
| **K-ASA** | Art. 19 | 0.04% | **Yes** | Depotgeschäft licence → Upvest safeguards and administers client financial instruments. Rolling 9-month average of daily values. |
| **K-COH** | Art. 20 | 0.1% / 0.01% | No | Only for firms receiving/transmitting client orders or executing in agent capacity. Eigenhandel = always principal → COH = 0 per IFR Art. 20. |

**K-ASA indicative calculation:**

| Client custody AUM | K-ASA = 0.04% × AUM |
|-------------------|---------------------|
| €100m | €40,000 |
| €500m | €200,000 |
| €1bn | €400,000 |
| €5bn | €2,000,000 |

K-ASA is measured as the rolling average of the value of total daily assets safeguarded and administered over the previous nine months, excluding the three most recent months (IFR Art. 19).

---

### 4.3 RtF — Risk-to-Firm (IFR Art. 24)

```
RtF = K-TCD + K-DTF + K-CON
```

#### K-TCD (Trading Counterparty Default) — IFR Art. 25–26

Applies to **OTC derivative contracts (Annex II CRR), repos, and SFTs** in the trading book (IFR Art. 25).

**Does K-TCD apply to Upvest's cash equity fractional trading?**
- For **plain cash equity purchases/sales**: K-TCD does **not** apply — these are exchange-traded or settled on a DVP basis, not OTC derivative contracts
- K-TCD would apply only if Upvest hedges via **OTC equity swaps, total return swaps, or repos** — which is not the base-case fractional trading model
- **Conclusion:** K-TCD is likely minimal/zero for fractional cash equity operations unless derivatives are used for FX or position hedging

If K-TCD does apply (e.g., FX forward for USD exposure hedging):
```
K-TCD = α × Exposure Value × Risk Factor × CVA
where α = 1.2 (fixed), Risk Factor per counterparty type per IFR Art. 26
```

#### K-DTF (Daily Trading Flow) — IFR Art. 33

```
K-DTF = DTF × coefficient
where:
  DTF cash trades coefficient = 0.1%
  DTF derivatives coefficient = 0.01%
```

DTF = rolling average of the **daily value of transactions** entered through dealing on own account (and execution in own name for clients), measured as sum of absolute value of buys + absolute value of sells.

This directly measures Eigenhandel volume. As fractional trading scales, K-DTF grows proportionally.

**K-DTF indicative calculation (cash equity only):**

| Daily fractional trading flow (both sides) | K-DTF = 0.1% × flow |
|--------------------------------------------|---------------------|
| €10m/day | €10,000 |
| €50m/day | €50,000 |
| €100m/day | €100,000 |
| €500m/day | €500,000 |

Note: This is a rolling average, not a peak — the averaging period smooths daily volatility.

#### K-CON (Concentration Risk) — IFR Art. 35–39

K-CON applies when Upvest's **trading book exposure to a single client or group of connected clients** exceeds **25% of own funds** (IFR Art. 37(1)).

Here "client" in the trading book context means the **execution counterparty** (broker, prime broker, execution venue) — not the underlying issuer whose shares are held.

**Exposure limit per execution counterparty:**
```
Limit = 25% of own funds
If Own Funds = €5m → Limit = €1.25m per counterparty
If Own Funds = €20m → Limit = €5m per counterparty
```

If the limit is exceeded:
- K-CON capital add-on is calculated on the excess (IFR Art. 39, progressive factor)
- BaFin must be **notified** of any excess (IFR Art. 38)

**Implication:** If Upvest routes all Eigenhandel flow through a single prime broker, that broker is the counterparty. Concentration of execution in one venue could trigger K-CON even at moderate own funds levels. Multi-venue routing strategy is both a best execution and K-CON management tool.

---

## 5. Comparison: IFR K-Factors vs. CRR Bank Capital — Side by Side

| Risk type | **Upvest (IFR K-factor)** | **Bank (CRR)** | Key difference |
|-----------|--------------------------|---------------|----------------|
| **Market risk (trading book)** | K-NPR = CRR standardised market risk approach | 8% × market risk RWA (same CRR approach) | **Identical formula** — K-NPR IS the CRR market risk calc |
| **Counterparty credit risk** | K-TCD (simplified formula, OTC only) | SA-CCR or IMM for all derivatives/SFTs; 8% × CCR RWA | IFR much simpler; no credit valuation adjustment charge beyond K-TCD formula |
| **Credit risk (loans/assets)** | Not capitalised — investment firms don't take deposits or make loans | Standardised or IRB; 8% × credit risk RWA | IFR has no credit risk Pillar 1; major simplification |
| **Operational risk** | Implicit in FOR (1/4 of fixed overheads) | BIA/Standardised/AMA; 8% × op risk RWA | FOR acts as proxy; scales with firm size, not event history |
| **Concentration risk** | K-CON: 25% own funds limit per trading book counterparty | Large exposure limit: 25% of own funds per client (CRR Part Four, Art. 395) | Conceptually identical — IFR Art. 37 mirrors CRR Art. 395 |
| **Leverage** | No leverage ratio | 3% Tier 1 / total exposure (CRR Art. 92(1)(d)) | Banks constrained by leverage; investment firms under IFR are not |
| **Liquidity (short-term)** | ≥ 1/3 of FOR in liquid assets (IFR Art. 43) | LCR ≥ 100% (30-day stress outflow coverage) | IFR is much simpler — no liquidity coverage ratio |
| **Liquidity (structural)** | None | NSFR ≥ 100% | No NSFR equivalent under IFR |
| **Internal capital adequacy** | **ICARA** (IFD Art. 24 / WpIG § 39) — capital + liquidity combined, principles-based | **ICAAP** (CRD IV Art. 73 / KWG § 25a) — capital only, highly prescribed | ICARA replaces both ICAAP and ILAAP; less prescriptive, but wind-down plan is an additional hard requirement |
| **Internal liquidity adequacy** | Subsumed in ICARA — no standalone ILAAP | **ILAAP** (separate from ICAAP; detailed liquidity stress testing) | Banks must file separate ILAAP; Upvest covers liquidity in ICARA alongside capital |
| **Custody / safekeeping** | K-ASA: 0.04% × assets safeguarded | Off-balance sheet; risk-weighted at 0% or small % | IFR uniquely capitalises custody scale — not in CRR |
| **AUM (portfolio mgmt)** | K-AUM: 0.02% × AUM | Not separately capitalised | IFR captures fiduciary risk through K-AUM |
| **Client money** | K-CMH: 0.4–0.5% × client money held | Covered by deposit guarantee scheme / LCR | IFR charges capital for client money holding |
| **Trading volume** | K-DTF: 0.1% × daily trading notional | Not explicitly capitalised | Unique to IFR — captures operational risk of high-volume trading |
| **Capital minimum** | €750,000 (Eigenhandel, IFD Art. 9) | €5,000,000 (credit institution) | IFR much lower floor — appropriate for smaller firms |

---

## 6. Capital Planning Implications for Fractional Trading

### Which K-factor will be the binding constraint?

At different stages of Upvest's growth:

| Growth stage | Likely binding constraint | Reasoning |
|-------------|--------------------------|-----------|
| **Launch / early phase** | FOR or minimum (€750k) | Low trading volumes → K-DTF, K-NPR small; fixed costs may exceed K-factor total |
| **Scaling (€10–100m AUM, €5–50m/day flow)** | K-ASA and K-DTF growing | Custody AUM and daily flow scale with B2B customer adoption |
| **Mature (€500m+ AUM, €100m+/day flow)** | K-NPR + K-ASA + K-DTF combined | Market risk on inventory + custody scale + volume all material |

### Capital sensitivity to fractional trading parameters

| Parameter | K-factor driven | Capital sensitivity |
|-----------|----------------|---------------------|
| **Residual position size** | K-NPR | ~16% of position value (equity standardised) — incentive to minimise residuals |
| **Daily trading flow** | K-DTF | 0.1% of flow — linear scaling; €100m/day → €100k K-DTF capital |
| **Client AUM in custody** | K-ASA | 0.04% of AUM — €1bn AUM → €400k capital |
| **Aggregation window length** | K-NPR (intraday) | Longer windows → larger intraday positions → higher peak K-NPR |
| **Instrument universe** | K-NPR | Illiquid / small-cap stocks have higher specific risk weights under CRR standardised approach |
| **Number of execution venues** | K-CON | More venues → lower per-venue concentration → lower K-CON risk |

### K-NPR and aggregation window design

Since K-NPR charges ~16% on net equity inventory, the aggregation window directly drives capital:
- Short window (5 min): smaller residual at end of window, lower K-NPR charge
- Long window (60 min): larger aggregated position building up, higher intraday K-NPR
- **Risk management recommendation:** monitor intraday peak K-NPR, not just end-of-day; set internal limits on maximum inventory per instrument relative to available capital

### FX exposure and K-NPR

If Upvest holds unhedged USD positions from US stock fractional inventory:
- FX general market risk adds to K-NPR: **8% of net FX position**
- Hedging with FX forwards reduces K-NPR but introduces K-TCD (for the OTC derivative leg)
- Trade-off: compare K-NPR (FX component) vs K-TCD (hedge) to determine optimal hedging policy

---

## 7. Liquidity Requirements Under IFR

Unlike banks (LCR/NSFR), Upvest's liquidity requirement is straightforward:

**IFR Art. 43:** Liquid assets ≥ **1/3 of FOR** at all times.

*Example:* FOR = €3m → must hold ≥ €1m in liquid assets (cash, government bonds, high-quality liquid instruments).

This is a modest requirement relative to bank LCR (which requires 100% of 30-day net cash outflows). However, for fractional trading operations, intraday liquidity management is operationally critical even if not explicitly Pillar 1 regulated — pre-funding client orders, settlement float, and residual position funding all require liquid resources beyond the IFR minimum.

---

## 8. ICARA — Upvest's Internal Capital and Liquidity Adequacy Process

### No ICAAP or ILAAP — Upvest has ICARA

ICAAP and ILAAP are bank concepts under CRD IV / KWG. Upvest operates under WpIG and is subject to the **ICARA (Internal Capital Adequacy and Risk Assessment)** — IFD Art. 24 / WpIG § 39 — which replaces both in a single, proportionate process.

| | **Bank — ICAAP** | **Bank — ILAAP** | **Upvest — ICARA** |
|---|---|---|---|
| Legal basis | CRD IV Art. 73 / KWG § 25a | CRD IV Art. 86 | IFD Art. 24 / WpIG § 39 |
| Focus | Internal capital adequacy | Internal liquidity adequacy | Capital **and** liquidity — combined |
| Prescribed scenarios | Yes — ECB/BaFin mandated stress tests | Yes — prescribed liquidity stress horizons | No — proportionate, firm-designed |
| Separate document | Yes | Yes (separate from ICAAP) | One document covering both |
| Wind-down plan | Not explicitly required at same level | Not explicitly required | **Hard requirement** — § 45 Abs. 4 WpIG |
| Pillar 2 output | P2R (capital add-on) + P2G (guidance) | Liquidity add-on | BaFin SREP may impose capital add-on (§ 47 WpIG) |
| Frequency | Annual minimum | Annual minimum | Annual minimum |

### What the ICARA must contain

**(IFD Art. 24 / WpIG § 39 / MaRisk AT 4.1 analogously)**

| Element | Content | Notes for fractional trading |
|---------|---------|------------------------------|
| **Risk inventory** | All material risks identified and assessed (MaRisk AT 2.2) | Must include market risk on residuals, FX risk, reconciliation/operational risk, custody risk |
| **Capital adequacy** | Own funds vs. all material risks under base case and stress | Stress K-NPR at 2–3× residual positions; stress K-DTF at peak flow |
| **Liquidity adequacy** | Liquid assets ≥ 1/3 FOR (IFR Art. 43); intraday liquidity for pre-funding | Model T+2 settlement float, pre-funding requirements, FX settlement |
| **Stress testing** | Scenarios covering key risk drivers (MaRisk AT 4.3.3 analogously) | Scenario: large residual position + market dislocation + delayed settlement |
| **Business model sustainability** | Forward-looking capital projection over 1–3 years | Model K-factor growth vs. revenue growth; confirm capital sufficiency |
| **Wind-down plan** | Capital and liquidity required to wind down the business in an orderly way | Key for fractional trading: time and cost to unwind residual book; notify B2B clients; settle all positions |
| **Governance** | Management board approval; documented review process | Board must formally approve ICARA annually |

### ICARA vs. ICAAP/ILAAP — Key Differences

**Less prescribed — but still scrutinised by BaFin:**
- No mandatory scenario set (unlike ECB ICAAP guide for significant institutions)
- Proportionality applies — a simple equity residual book does not need the same depth as a complex bank trading book
- However, BaFin's SREP (§ 47 WpIG) reviews the ICARA and **can impose Pillar 2 capital add-ons** if the framework is judged inadequate

**Wind-down plan — unique to IFR (no direct bank equivalent):**
- § 45 Abs. 4 WpIG: Upvest must at all times hold sufficient capital and liquidity to execute an **orderly wind-down**
- For fractional trading this means:
  - Capital to absorb losses on residual inventory during unwind
  - Liquidity to cover settlement obligations while winding down
  - Operational plan: how are B2B customers notified, how are fractional positions transferred or closed, what is the timeline
- This should be documented, stress-tested, and updated annually

### When ICAAP / ILAAP Would Apply to Upvest

| Trigger | Consequence |
|---------|------------|
| Becomes **große Wertpapierfirma** (§ 2 Abs. 18 WpIG) | Must apply KWG §§ 25a/25b → ICAAP and ILAAP obligations arise |
| Crosses **€15bn consolidated assets** | Switches to CRR/CRD IV → full ICAAP + ILAAP required; SSM supervision possible |

---

## 9. Regulatory Capital Reporting

Upvest must report to BaFin under:

| Report | Frequency | Content |
|--------|-----------|---------|
| **COREP IF** (IFR) | Quarterly | Own funds, K-factors, liquidity |
| **K-factor monitoring** | Ongoing — IFR Art. 15(3) | Must notify BaFin of trends that would materially change own funds requirement |
| **K-CON notification** | Immediate | If exposure to single trading counterparty exceeds 25% of own funds |
| **Large exposures** | Quarterly | IFR Part Four |
| **ICARA output** | Annual (minimum) | Internal review; presented to BaFin in SREP |

---

## 10. Key Actions — Capital Framework for Fractional Trading

- [ ] **Confirm K-CMH applicability** — does any client cash transit Upvest's own accounts during the order cycle? If yes, calculate CMH and include K-CMH
- [ ] **Build K-factor model** — link to `models/` folder; should calculate all applicable K-factors quarterly with actuals and project forward
- [ ] **Set internal K-NPR limit per instrument** — intraday peak position limits based on available capital buffer
- [ ] **Multi-venue routing policy** — document as K-CON management measure (reduces concentration per single execution counterparty)
- [ ] **FOR calculation** — map fixed vs. variable costs; run FOR sensitivity to hiring plan
- [ ] **Binding constraint analysis** — model which pillar (FOR, minimum, K-factor) will bind at different AUM/flow scenarios
- [ ] **CRR threshold monitoring** — confirm consolidated total assets annually; flag if approaching €15bn (CRR would then apply)
- [ ] **FX hedging capital trade-off** — quantify K-NPR (FX component) vs K-TCD (hedge cost) for USD stock inventory
- [ ] **ICARA — initial draft** — produce first ICARA covering risk inventory, capital adequacy, liquidity adequacy, stress scenarios, and wind-down plan; present to management board for approval
- [ ] **ICARA stress scenarios** — design at minimum: (1) large residual position + market dislocation, (2) peak trading flow + operational outage, (3) B2B customer default with open fractional positions
- [ ] **Wind-down plan** — document orderly wind-down procedure: residual book unwind timeline, B2B customer notification process, settlement obligation coverage; quantify capital and liquidity needed
- [ ] **K-factor monitoring threshold** — set internal trigger to notify BaFin if K-factors trend materially higher (IFR Art. 15(3))
- [ ] **große Wertpapierfirma monitoring** — track whether Upvest approaches § 2 Abs. 18 WpIG threshold; if reached, ICAAP/ILAAP obligations arise

---

## 11. Reference: K-Factor Coefficients Summary (IFR Art. 15, Table 1)

| K-factor | Metric | Coefficient | Applicable to Upvest |
|---------|--------|------------|---------------------|
| K-AUM | AUM | 0.02% | No (no portfolio management) |
| K-CMH | Client money — segregated | 0.4% | TBC |
| K-CMH | Client money — non-segregated | 0.5% | TBC |
| K-ASA | Assets safeguarded/administered | 0.04% | **Yes** (Depotgeschäft) |
| K-COH | Client orders — cash | 0.1% | No (principal dealer) |
| K-COH | Client orders — derivatives | 0.01% | No (principal dealer) |
| K-DTF | Daily trading flow — cash | 0.1% | **Yes** (Eigenhandel) |
| K-DTF | Daily trading flow — derivatives | 0.01% | If OTC hedging used |
| K-NPR | Net position risk | CRR standardised (~16% for long equity) | **Yes** (all trading book positions) |
| K-CMG | Clearing margin given | 1.3 × 3rd-highest margin | Only with BaFin approval + QCCP clearing |
| K-TCD | Trading counterparty default | α × Exposure × Risk Factor | Only if OTC derivatives/repos |
| K-CON | Concentration (>25% own funds) | Progressive add-on on excess | **Yes** (monitor per execution counterparty) |

---

*Last updated: 2026-05-30. Based on IFR (EU) 2019/2033 (consolidated 09.01.2024), CRR (EU) 575/2013, IFD (EU) 2019/2034, and WpIG. Cross-reference with `docs/04_bafin_marisk_compliance.md` for governance and organisational requirements.*
