# Trading Book Strategy — Inventory Management Algorithm

## Overview

Upvest's fractional trading model requires an inventory management algorithm to determine when and how to buy/sell whole shares on the market to fulfil aggregated fractional orders. Two approaches are evaluated below.

**The core mechanics in both cases:**
- Fractional buy/sell orders from B2B customers accumulate in an aggregation engine
- Upvest's trading book holds a whole-share inventory to fill fractional orders without waiting for full aggregation
- The algorithm governs when to replenish or reduce that inventory

---

## Option A — Fixed Threshold Inventory Management

### How It Works

Simple rule-based inventory control per instrument:

```
For each instrument:
  if inventory < min_threshold   → trigger market buy (replenish to target)
  if inventory > max_threshold   → trigger market sell (reduce to target)
  else                           → hold

Example (Tesla):
  min_threshold  = 1 share   → rebuy trigger
  target         = 2 shares  → replenish to here
  max_threshold  = 4 shares  → sell trigger
```

Parameters are set statically per instrument, driven by historical fractional order flow and analyst judgement. No real-time market data inputs into the decision logic — only current inventory level.

---

### Regulatory Implications

| Area | Implication | Assessment |
|------|------------|------------|
| **Eigenhandel classification** | Purely principal dealing to maintain a service inventory — clean fit with § 2 Abs. 2 Nr. 10c WpIG and BaFin Merkblatt March 2022 | ✅ No ambiguity |
| **Algorithmic trading (MiFID II Art. 17 / WpHG § 80 Abs. 2)** | Rule-based automation, no latency-seeking, no market signal exploitation → does **not** trigger algorithmic trading classification. Equivalent to automating a manual process | ✅ No BaFin notification required |
| **RTS 6 (EU) 2017/589** | Not triggered if no algorithmic trading classification — confirm with Legal that threshold logic without market signal inputs does not qualify | ✅ Not applicable (confirm with Legal) |
| **HFT (§ 2 Abs. 2 Nr. 10d WpIG)** | No latency infrastructure, no high message rates → not HFT | ✅ Not applicable |
| **Systematic Internaliser (SI)** | Fixed threshold buying/selling is not systematic internalisation of client orders at own quotes → SI regime unlikely to apply | ✅ Low risk |
| **Market Abuse Regulation (MAR)** | No exploitation of price signals → no MAR concerns | ✅ Clean |
| **Best execution (§ 82 WpHG)** | Simple policy: execute at best available market price when threshold triggered. Easy to document and audit | ✅ Straightforward |
| **Conflicts of interest** | No P&L optimisation at client expense — inventory serves fractional orders only | ✅ Minimal |
| **K-NPR capital** | Inventory bounded by max_threshold per instrument → K-NPR predictable and limited | ✅ Capped and plannable |
| **K-DTF** | Trading flow is driven by threshold breaches → moderate, predictable | ✅ Predictable |
| **MaRisk BTR 2.2 (analogously)** | Simple trading book controls sufficient — position limits map directly to thresholds | ✅ Low governance burden |
| **Model risk (MaRisk Novelle AT 4.3.4)** | Rule-based logic with no statistical model — no model validation required | ✅ Not applicable |

---

### Implementation Complexity

**Overall: LOW**

| Component | Effort | Notes |
|-----------|--------|-------|
| Inventory monitoring | Low | Simple position counter per instrument |
| Threshold configuration | Low | Static table per instrument; manual update process |
| Order generation | Low | Trigger → market order to execution venue |
| Risk controls | Low | Hard position limits = threshold ceiling |
| Testing | Low | Deterministic logic; unit tests cover all cases |
| Regulatory documentation | Low | One-page inventory policy per instrument |
| Ongoing maintenance | Low | Review thresholds quarterly or on material flow change |
| Explainability to BaFin | Very easy | "If inventory < X, buy to Y" — no black box |

---

### Key KPIs

| KPI | Definition | Target / Alert |
|-----|-----------|----------------|
| **Fill rate** | % of fractional orders filled within SLA (e.g., within aggregation window) | > 99% |
| **Inventory utilisation** | Average inventory / max_threshold per instrument | 40–70% (too low = over-buying; too high = fill risk) |
| **Threshold breach frequency** | Number of min/max breaches per instrument per day | Monitor for instruments needing threshold recalibration |
| **Execution cost per share** | Spread + market impact cost on replenishment trades | Benchmark to VWAP; target < 5bps slippage |
| **Residual position at end-of-day** | Inventory remaining after all fractional allocations | Minimise; large residuals → K-NPR capital cost |
| **Order rejection rate** | Fractional orders rejected due to zero inventory | < 0.1% |
| **Threshold calibration staleness** | Days since last threshold review per instrument | Alert if > 90 days |
| **K-NPR intraday peak** | Max K-NPR capital requirement during the day | Must stay within capital headroom |

---

## Option B — Dynamic Algorithm Exploiting Market Signals

### How It Works

The algorithm uses real-time and historical market data to dynamically time inventory decisions, capturing spread income and minimising market impact:

```
Inputs:
  - Current inventory level
  - Bid-ask spread (real-time)
  - Order book depth / available liquidity
  - Intraday price momentum / mean-reversion signal
  - Predicted fractional order flow (time-of-day model)
  - ADV participation limit

Decision logic (illustrative):
  if inventory < min AND spread < threshold AND depth > threshold:
      buy NOW (favourable conditions)
  elif inventory < min AND spread wide:
      defer buy (wait for spread to tighten)
  if inventory > max AND momentum rising:
      hold (expect natural demand from fractional buys)
  if inventory > max AND momentum falling:
      sell aggressively
  if spread > X bps AND inventory in mid-range:
      opportunistically sell at ask, rebuy at bid (spread capture)
```

The algorithm may also **pre-position** ahead of predicted fractional demand (e.g., increase Tesla inventory before US market open when demand peaks).

---

### Regulatory Implications

| Area | Implication | Assessment |
|------|------------|------------|
| **Algorithmic trading (MiFID II Art. 17 / WpHG § 80 Abs. 2)** | Automated decision-making using market signals → **algorithmic trading classification applies**. Full RTS 6 obligations triggered — see RTS 6 section below | ⚠️ Significant compliance build required |
| **RTS 6 (EU) 2017/589 — full obligations** | BaFin notification; annual self-assessment to Geschäftsleitung; pre-trade controls (price collar, max order value/quantity, position limits, fat-finger); post-trade controls (daily loss limits); kill switch (immediate, firm-wide); real-time monitoring (independent of trading desk); conformance testing at execution venue before go-live; per-order audit trail (5-year retention); full algorithm documentation and change log; compliance sign-off before each deployment | ⚠️ Full framework required before go-live |
| **HFT risk (§ 2 Abs. 2 Nr. 10d WpIG / MiFID II Art. 4(1)(40))** | If algorithm submits >4 orders/second per venue or >2/second aggregate (ESMA threshold), HFT classification applies → additional obligations, higher capital charge | ⚠️ Must monitor order rate; throttle if approaching threshold |
| **Systematic Internaliser (SI)** | If Upvest systematically quotes prices at which it transacts with B2B clients, SI regime (§ 2 Abs. 2 Nr. 10b WpIG) may apply → pre-trade transparency obligations, minimum quote sizes | ⚠️ Needs legal assessment; SI status changes MiFID II obligations materially |
| **Market Abuse Regulation (EU) 596/2014** | Exploiting intraday price momentum or pre-positioning ahead of expected client flow could be perceived as **front-running** or layering. Must demonstrate algorithm serves inventory management purpose, not price manipulation | ⚠️ High — requires clear documentation, compliance sign-off, audit trail per order |
| **Conflicts of interest (MiFID II Art. 23 / WpHG § 63)** | Spread capture and momentum exploitation generate P&L for Upvest's own account. If this is at the expense of fractional order pricing, it is a conflict. Must be disclosed in conflicts policy and managed | ⚠️ Must be disclosed to B2B clients; pricing methodology documented |
| **Best execution (§ 82 WpHG)** | Significantly more complex — must demonstrate algorithm achieves best execution for fractional order holders, not just optimal P&L for Upvest. ESMA Q&A on best execution for principal dealers applies | ⚠️ Policy and monitoring considerably more complex |
| **K-NPR capital** | Dynamic positioning may hold larger inventories during momentum phases → K-NPR peaks less predictable; requires intraday capital monitoring | ⚠️ Needs intraday K-NPR limit framework |
| **K-DTF** | Higher trading frequency → materially higher K-DTF capital charge | ⚠️ Model K-DTF impact at expected algo trading volumes |
| **Model risk (MaRisk Novelle AT 4.3.4)** | Statistical models for flow prediction, spread, momentum → full model governance required: validation, backtesting, sensitivity testing, approval, periodic review | ⚠️ Model risk framework must be built before go-live |
| **MaRisk BTO 2 (analogously)** | Complex algorithmic trading → stricter front/back office separation, intraday position monitoring, P&L reconciliation, independent risk oversight of algo performance | ⚠️ Stronger governance requirements |
| **Eigenhandel characterisation** | Spread capture and momentum trading may blur the "service for others" requirement. BaFin may scrutinise whether activity remains Eigenhandel or becomes Eigengeschäft (no licence required but also no client service character) | ⚠️ Proactive BaFin engagement recommended |

---

### Implementation Complexity

**Overall: HIGH**

| Component | Effort | Notes |
|-----------|--------|-------|
| Market data infrastructure | High | Real-time L1/L2 order book feed per venue; low-latency data pipeline |
| Signal development | High | Spread model, momentum signal, flow prediction model; each requires backtesting |
| Model validation | High | Independent validation of each model before deployment (model risk) |
| Order management system | High | Smart order routing, order type logic, throttling controls |
| Risk controls | High | Real-time K-NPR monitoring, kill switch, per-instrument position limits, algo circuit breakers |
| MiFID II algo trading compliance | High | BaFin notification, annual self-assessment framework, kill switch, testing documentation |
| MAR compliance | High | Surveillance framework; per-order audit trail; compliance pre-approval of strategy |
| Conflict of interest framework | Medium | Pricing policy documentation; client disclosure |
| Backtesting infrastructure | High | Historical market data, simulation environment, performance attribution |
| Ongoing monitoring | High | Daily algo performance review, model drift monitoring, spread/impact attribution |
| Explainability to BaFin | Complex | Requires model documentation, validation reports, audit trail |

---

### Key KPIs

**Execution quality:**

| KPI | Definition | Target |
|-----|-----------|--------|
| **Implementation shortfall** | Arrival price vs. actual execution price | < 5bps per trade |
| **VWAP slippage** | Execution price vs. intraday VWAP | < 3bps |
| **Spread capture rate** | Revenue from bid-ask spread per €m traded | Track vs. cost of capital tied up in inventory |
| **Adverse selection rate** | % of trades where price moved against Upvest immediately after execution | < 40% |
| **Market impact** | Price impact attributable to Upvest's own orders vs. 30d ADV | < 1bps per trade (well-managed) |
| **Fill rate** | % of fractional orders filled within SLA | > 99% |

**Risk and capital:**

| KPI | Definition | Target / Alert |
|-----|-----------|----------------|
| **Intraday K-NPR peak** | Max K-NPR capital requirement during day | Must stay < internal limit |
| **K-DTF rolling average** | 30-day rolling average of daily notional flow | Monitor for K-factor capital impact |
| **Inventory turnover** | Shares bought and sold per day / average inventory | Monitor for excessive churn |
| **Residual at end-of-day** | Unsettled inventory after all fractional allocations | Minimise — drives K-NPR overnight |

**Model and algo health:**

| KPI | Definition | Target |
|-----|-----------|--------|
| **Flow prediction accuracy** | Predicted vs. actual fractional order flow by instrument | MAPE < 20% |
| **Model drift** | Rolling prediction error trend | Alert if MAPE increases >5pp month-on-month |
| **Kill switch activations** | Number of emergency algo halts | Zero in normal operation; any activation triggers review |
| **Order rejection / error rate** | Orders rejected by venue or failed | < 0.01% |
| **Algo P&L attribution** | Spread income vs. adverse selection vs. market impact | Positive spread capture; negative adverse selection is a model failure signal |

---

## Algorithmic Trading Obligations Under RTS 6

### What Is RTS 6?

**Commission Delegated Regulation (EU) 2017/589** (RTS 6) supplements MiFID II Art. 17 and specifies the full organisational requirements for investment firms engaged in algorithmic trading. Transposed in Germany via **WpHG § 80 Abs. 2** and **§ 81**.

RTS 6 applies when a firm uses a **computer algorithm that automatically determines individual parameters of orders** — whether to initiate, timing, price, quantity, or how to manage the order after submission — with limited or no human intervention (MiFID II Art. 4(1)(39)).

### Does RTS 6 Apply to Each Option?

| | **Option A** | **Option B** | **Option C (Hybrid)** |
|---|---|---|---|
| **Algorithm auto-determines order initiation?** | Yes (threshold trigger) | Yes | Yes (threshold trigger) |
| **Algorithm uses market signals?** | No | Yes | Execution layer only |
| **Latency-seeking?** | No | Potentially | No |
| **RTS 6 classification** | **Grey area** — likely not algorithmic trading if threshold logic is simple and human oversight covers each decision; confirm with Legal | **Yes — algorithmic trading** | **Likely not** for the inventory decision; execution TWAP layer needs assessment |
| **BaFin notification required?** | Confirm with Legal | **Yes** | Confirm with Legal |

> **Key distinction (ESMA guidance):** Simple automation of a manual process (e.g., automatically placing a limit order when a condition is met) is generally NOT algorithmic trading if it merely automates what a human trader would do. Option A falls closer to this category. Option B — using market signals to optimise timing and quantity — is clearly algorithmic trading.

---

### The Classification Boundary — What ESMA Guidance and BaFin Practice Actually Say

#### What ESMA Has Said

ESMA's Q&A on MiFID II investor protection topics (ESMA35-43-349) addresses algorithmic trading classification through a central principle: the test is not the presence of automation, but whether the computer algorithm is **determining** order parameters versus **transmitting** parameters already determined by a human. A system that merely converts a human instruction into an electronic order — without adding discretion or intelligence — does not by itself constitute algorithmic trading. Pure order routing is the clearest application: if a trader decides to buy 100 shares and uses a system only to send that instruction to a venue, the system is not an algorithm in the MiFID II sense. ESMA has also stated that the assessment must be made case by case based on the specific system design — there is no categorical safe harbour.

This is the foundation of the interpretive argument for Option A: one could characterise a fixed-threshold system as a **standing human instruction** — the human has pre-determined "whenever inventory falls below 1 share, buy to 2 shares at market" — and the system is merely implementing that instruction when the condition arises. On that reading, the computer is not making a decision; it is executing a decision already made by a human at the time the threshold was programmed.

#### Why That Argument Is Weaker Than It Looks

The "standing instruction" argument faces three meaningful objections.

First, the definition in MiFID II Art. 4(1)(39) requires "limited or no human intervention" at the point the order is generated. A rule set once and then executed automatically without per-order human review is difficult to frame as involving meaningful intervention at the point of each individual trade. The human set the rule; the machine applies it. ESMA has not explicitly endorsed the standing-instruction interpretation for automated inventory management.

Second, the "without adding intelligence" formulation is more demanding than it appears. An Option A system does add something that a pure routing system does not: it determines *whether to initiate* an order on each cycle (inventory < min → yes; otherwise → no). This is a binary decision the machine makes autonomously. ESMA's comfort for routing systems specifically addresses situations where a human has already made the initiation decision; a threshold system is making that decision itself on each check.

Third, ESMA states explicitly that assessment is case by case. There is no Q&A, guideline or opinion that directly addresses fixed-threshold inventory management in a fractional trading context, and none that confirms such a system falls outside Art. 4(1)(39).

#### BaFin's Enforcement Posture

BaFin's supervisory focus on algorithmic trading has centred primarily on high-frequency trading, latency-minimising infrastructure and systems that exploit real-time market signals. BaFin has not, to publicly available knowledge, pursued enforcement action against simple automated inventory management systems operating without market data inputs. This enforcement focus creates a practical expectation that a straightforward threshold system is less likely to attract scrutiny than a dynamic signal-based algorithm.

However, enforcement posture and legal classification are different things. The absence of enforcement action against threshold systems does not mean BaFin has concluded they fall outside Art. 4(1)(39). It may simply reflect that such systems have not yet come before BaFin in a context requiring a formal determination, or that BaFin has exercised discretion not to pursue cases at the simpler end of the spectrum.

#### The Honest Assessment

The "comfort" for Option A is a plausible interpretive argument, not a safe harbour. It is strengthened by any human checkpoint in the process — even a daily review of executed orders with authority to suspend thresholds — because that supports the "limited human intervention" framing. It weakens materially the moment the system adds any market data input, execution timing logic or post-submission management, all of which tip it toward Option B territory.

**A formal legal opinion from a MiFID II specialist (Freshfields, Hengeler Mueller or equivalent with direct BaFin supervisory practice) is required before relying on this argument in production.** A proactive informal BaFin conversation is also advisable: regulators respond significantly better to firms that raise classification questions before launch than after.

---

### Consequences of BaFin Determining Upvest Is an Algorithmic Trader

If BaFin concludes — whether through proactive engagement, a notification review or a supervisory examination — that Upvest's inventory management system constitutes algorithmic trading, the consequences fall into two categories: **prospective obligations** that must be implemented immediately, and **retrospective breach** consequences for the period during which the system was operated without classification.

#### Immediate Prospective Obligations

The firm would be required to implement the full RTS 6 framework (detailed in the section below) on an expedited basis. In practice this means:

| Obligation | Timeline | Complexity |
|-----------|----------|-----------|
| Formal BaFin notification (WpHG § 80 Abs. 2) | Immediate | Low — administrative |
| Kill switch — build and test | Days to weeks | High — must be independent of the algo |
| Pre-trade controls (price collar, order limits, fat-finger) | Weeks | Medium — OMS changes |
| Real-time monitoring function | Weeks | Medium — staffing + tooling |
| Conformance testing at execution venues | 4–8 weeks | Medium — venue scheduling |
| Per-order audit trail, going forward | Immediate | Medium — logging infrastructure |
| Annual self-assessment framework | Before next review cycle | Low — process document |
| Compliance sign-off process | Immediate | Low — governance procedure |

BaFin would typically set a remediation timeline in a formal order (Anordnung). Non-compliance with that order is itself an additional breach.

#### Retrospective Breach — the Audit Trail Gap

The most serious consequence of misclassification is the **retroactive gap** in the audit trail. RTS 6 Art. 9 requires that every order generated by the algorithm carry a unique identifier linking it to the strategy version, parameter set and system state that triggered the decision, retained for five years. If the system was not logging at this level of granularity, that data cannot be reconstructed retroactively. Upvest would have operated, for the entire period since launch, without the mandatory record-keeping required by MiFID II Art. 17(2). This is a standalone regulatory breach independent of whether any harm occurred.

#### Enforcement Risk

The relevant enforcement provision is WpHG § 120, which empowers BaFin to impose administrative fines (Bußgelder) for violations of algorithmic trading obligations. The maximum fine for violations of § 80 WpHG (which implements MiFID II Art. 17) is **€5,000,000 or 10% of total annual turnover**, whichever is higher, for legal persons. Repeated or persistent non-compliance can trigger:

- A BaFin order requiring the cessation of automated order generation until controls are in place
- Publication of the enforcement measure (naming the firm publicly)
- In severe cases, suspension or restriction of the Eigenhandel licence
- Personal liability of Geschäftsleiter under § 120 WpHG for wilful or negligent violations

#### What Upvest Would Need to Do Immediately

Upon a BaFin determination of algorithmic trading classification, the response sequence would be:

1. **Halt automated order submission** (or accept ongoing breach risk) until kill switch and pre-trade controls are operational
2. **File formal BaFin notification** under WpHG § 80 Abs. 2 within the shortest possible timeframe
3. **Report to Geschäftsleitung and Risk Committee** — board-level awareness is both a governance requirement and evidence of good faith
4. **Engage external legal counsel** to assess breach scope and manage the BaFin relationship
5. **Reconstruct audit trail** to the extent possible from available system logs
6. **Implement RTS 6 controls** on an emergency basis, prioritising kill switch and pre-trade controls as the most operationally critical
7. **Consider voluntary disclosure** to BaFin of the historical gap — regulators consistently treat proactive disclosure as a significant mitigating factor in enforcement decisions

#### Why Early Clarity Is Worth the Effort

The cost of getting a legal opinion and, if needed, a BaFin pre-notification conversation before launch is negligible relative to the cost of a retroactive misclassification finding. The audit trail gap alone — five years of non-compliant record-keeping on all automated orders — is a liability that cannot be cured after the fact regardless of how quickly everything else is remediated. The decision on algorithm classification should therefore be treated as a legal and compliance gate, not an afterthought.

---

### RTS 6 Full Obligations — Applicable to Option B (and any classified algo)

#### 1. BaFin Notification — MiFID II Art. 17(2) / WpHG § 80 Abs. 2

Before commencing algorithmic trading:
- Notify BaFin that the firm is engaged in algorithmic trading
- Describe the nature of the algo strategies used
- Ongoing obligation to notify of material changes to strategies

#### 2. Annual Self-Assessment — RTS 6 Art. 1(2)

- Conduct an **annual self-assessment** of all algorithmic trading activities
- Report findings to **senior management (Geschäftsleitung)**
- Document that systems and controls remain fit for purpose
- Assessment must cover: governance, pre/post-trade controls, testing, monitoring, kill switch, compliance oversight

#### 3. Pre-Trade Controls — RTS 6 Art. 3

Must be in place before any order is submitted. For Upvest's equity inventory algorithm:

| Control | Description | Upvest Implementation |
|---------|------------|----------------------|
| **Price collar** | Block orders if price deviates > X% from reference price (e.g., last traded price, VWAP) | Per instrument; calibrated to normal intraday range |
| **Maximum order value** | Hard cap on EUR notional per single order | Linked to K-NPR capital limit per instrument |
| **Maximum order quantity** | Hard cap on shares per single order | Linked to max_threshold inventory limit |
| **Maximum position per instrument** | Total trading book position cannot exceed limit | = max_threshold for each instrument |
| **Repeated automated execution check** | Prevent runaway order loops (fat-finger protection) | Circuit breaker: halt if > N orders submitted in X seconds |
| **Trading halt / suspension check** | Must not trade in a suspended instrument | Real-time feed from execution venue |
| **Minimum tick size check** | Orders must comply with MiFID II tick size regime | Venue-level enforcement; cross-check in OMS |

#### 4. Post-Trade Controls — RTS 6 Art. 4

| Control | Description |
|---------|------------|
| **Maximum daily loss per instrument** | Auto-halt if P&L loss on a single instrument exceeds threshold in a day |
| **Maximum daily loss overall** | Auto-halt all algos if firm-wide daily trading loss exceeds threshold |
| **Maximum net position** | Alert if net position across all instruments approaches capital limit |

#### 5. Kill Switch — RTS 6 Art. 5 / MiFID II Art. 17(1)

- **Mandatory** — must be able to cancel all outstanding orders and halt all algo activity **immediately**
- Must work at multiple granularities: per instrument, per strategy, firm-wide
- Kill switch must function **independently** of the algo itself (separate system)
- Must be accessible to compliance and risk functions, not only technology
- Documented procedure: who can activate, escalation chain, post-activation review

#### 6. Real-Time Monitoring — RTS 6 Art. 5

- **Dedicated real-time monitoring function** — must observe algo activity during all trading hours
- Detect unusual order patterns (e.g., excessive order rates, repeated rejections, position build beyond limits)
- Alert and escalation procedure with defined response times
- Monitoring must be independent of the trading desk running the algo

#### 7. Testing Requirements — RTS 6 Art. 6 / Art. 7

Before deployment and after any **significant change** to the algorithm:

| Test type | Requirement |
|-----------|------------|
| **Development environment testing** | Full functionality test in isolated environment |
| **Conformance testing** | Test in the execution venue's conformance testing environment (CTE); most venues (Xetra, Euronext) provide this |
| **Stress testing** | Test under extreme market conditions (wide spreads, halted instruments, high volatility) |
| **Regression testing** | After any change — confirm existing controls still function |
| **Parallel running** | Run new algo alongside existing process before full switchover |

Significant changes that trigger re-testing include: changes to order generation logic, new instruments in scope, new execution venues, changes to pre-trade controls.

#### 8. Compliance Function Oversight — RTS 6 Art. 8

- Compliance must have **sufficient understanding** of all algo strategies to provide effective oversight
- Compliance signs off on each new strategy before deployment
- Regular review (at minimum annually, or after material changes)
- Compliance must be able to assess whether the algo creates MAR risk, conflicts of interest, or best execution failures

#### 9. Audit Trail — RTS 6 Art. 9 / MiFID II Art. 17(2)

- Every order generated by the algorithm must carry a **unique identifier** linking it to:
  - The specific algorithm and strategy version
  - The specific parameter set active at time of order
  - The inventory/market state that triggered the decision
- Audit trail must be retained for **5 years** (MiFID II Art. 25(1))
- Must be producible to BaFin on request within a reasonable timeframe

#### 10. Documentation Requirements — RTS 6 Art. 10

| Document | Content |
|---------|---------|
| **Algorithm description** | Full description of strategy logic, inputs, outputs, decision rules |
| **Risk and controls documentation** | All pre/post-trade controls, calibration methodology, review process |
| **Testing documentation** | Test plans, results, sign-off by independent function |
| **Change management log** | Record of all changes to the algorithm with approval trail |
| **Annual self-assessment report** | Findings and sign-off by Geschäftsleitung |

#### 11. Staffing — RTS 6 Art. 1(3)

- Firm must have **sufficient staff** with technical knowledge of the algorithm and of the relevant trading venues
- Cannot rely solely on third-party vendors — internal understanding is required
- Must include: developers/quants who built it, risk staff who monitor it, compliance who oversee it

---

### RTS 6 Implementation Roadmap (for Option B / C if classified as algo trading)

| Phase | Timeline | Actions |
|-------|----------|---------|
| **Pre-development** | Before build starts | Legal classification opinion; BaFin pre-notification discussion; compliance framework design |
| **Development** | During build | Pre/post-trade controls embedded in OMS; kill switch; audit trail per order |
| **Pre-deployment testing** | 4–6 weeks before go-live | Development environment testing; CTE conformance testing at execution venue; stress test |
| **Regulatory notification** | Before go-live | Formal BaFin notification (WpHG § 80 Abs. 2) |
| **Go-live** | — | Real-time monitoring active; kill switch tested; compliance sign-off |
| **Year 1 review** | 12 months post go-live | Annual self-assessment; report to Geschäftsleitung; recalibrate controls |

---

## Risk Drivers — Trading Book

### 1. Market Risk — Position Risk

**What it is:** The risk of loss from adverse price moves on Upvest's whole-share inventory — both the planned inventory held to service fractional orders and unintended residual positions that arise when aggregated fractional demand doesn't sum to a whole share.

**Two distinct exposures:**

| Exposure | Description | Driver |
|----------|------------|--------|
| **Planned inventory** | Whole shares deliberately held to fill incoming fractional orders before enough demand aggregates | Size bounded by inventory target (Option A) or dynamic signal (Option B) |
| **Residual position** | Fractional remainder after fractional allocations — e.g., 2.73 shares held, 2 allocated, 0.73 remains | Accumulates continuously; must be managed or charged K-NPR capital |

**Capital charge:** ~16% of net equity position under K-NPR (CRR standardised, 8% specific + 8% general risk). FX component adds 8% of net currency exposure.

**Option A vs Option B:**

| | Option A | Option B |
|---|---|---|
| Max inventory | Hard ceiling (max_threshold) | Dynamic — can build larger during momentum phases |
| Position risk | Predictable and bounded | Variable; intraday peaks harder to forecast |
| Overnight risk | Configurable — hold or liquidate to target at close | Depends on algo state; needs explicit overnight policy |
| Single-name concentration | Risk of threshold being set too high for illiquid names | Must be managed dynamically; harder to control |

**Controls:**
- Per-instrument position limit (hard stop, independent of algo)
- Intraday K-NPR monitoring — alert at 80% of capital headroom
- Overnight position policy — define maximum permissible overnight inventory per instrument
- Single-name concentration limit — cap as % of 30-day ADV (e.g., max 0.5% of ADV held)

**Key metrics:**

| Metric | Definition | Alert threshold |
|--------|-----------|----------------|
| Net position per instrument (EUR) | Current inventory × last price | > internal limit |
| Intraday K-NPR peak | Max K-NPR charge during session | > 80% of capital headroom |
| Overnight residual (EUR) | End-of-day unsettled inventory | > agreed overnight limit |
| Single-name concentration | Position / 30d ADV | > 0.5% |
| Daily P&L on inventory | Mark-to-market gain/loss on held positions | Monitor for trend; large loss triggers review |

---

### 2. Market Risk — Stress

**What it is:** Tail-risk scenarios where normal price and liquidity assumptions break down, exposing Upvest to losses on its trading book that the K-NPR standardised capital charge may not fully cover.

**Relevant stress scenarios for fractional trading:**

| Scenario | Description | Impact on Upvest |
|----------|------------|-----------------|
| **Flash crash** | Instrument drops 20–40% intraday (e.g., Tesla -30% in 15 minutes) | Full inventory at loss; residual grows as demand collapses; K-NPR capital inadequate |
| **Single-name corporate event** | Profit warning, fraud, regulatory action (e.g., Wirecard) | Inventory loss + potential halt → unable to unwind; K-NPR charge on stale position |
| **Market-wide volatility spike** | VIX equivalent spikes; all positions move adversely simultaneously | Correlation between instruments; diversification benefit disappears |
| **Exchange outage / trading halt** | Venue goes down during intraday inventory accumulation | Cannot unwind; forced overnight hold of larger-than-intended positions |
| **FX dislocation** | USD/EUR moves 3–5% intraday (e.g., macro shock) | Unhedged US equity inventory takes both price loss and FX loss simultaneously |
| **Settlement failure cascade** | CSD or prime broker settles late; positions persist beyond T+2 | Capital tied up longer than expected; operational and market risk compound |
| **Demand reversal** | B2B customer suddenly cancels large fractional order after inventory pre-positioned | Upvest holds inventory with no matching fractional demand; forced liquidation at market |

**Stress testing for ICARA (§ 39 WpIG / IFD Art. 24):**

At minimum two stress scenarios must be modelled for the ICARA:
1. **Inventory stress:** Largest single-instrument position × 30% price drop. Capital required = stressed K-NPR. Compare to available capital buffer.
2. **Combined stress:** All instruments drop 15% simultaneously + exchange outage prevents unwind for 1 day. Models the worst-case overnight hold scenario.

**Option A advantage in stress:** hard max_threshold caps the maximum possible loss per instrument. Stress P&L is bounded.

**Option B stress risk:** dynamic positioning may build large positions just before an adverse move (adverse selection / momentum reversal risk). Stress loss is unbounded without hard position limits.

**Controls:**
- Hard position limits independent of algo (mandatory circuit breaker)
- Stop-loss per instrument per day (post-trade control, RTS 6 Art. 4)
- ICARA stress scenarios updated annually; results drive capital buffer sizing
- Overnight position liquidation policy for high-volatility instruments
- Instrument eligibility review: exclude instruments with history of extreme intraday moves without liquidity

---

### 3. Market Risk — Market Liquidity

**What it is:** The risk that Upvest cannot execute inventory trades at expected prices due to insufficient market depth — either because the instrument is thinly traded or because Upvest's own order size moves the market.

**Two components:**

| Component | Description |
|-----------|------------|
| **Exogenous liquidity risk** | Market-wide thinning of liquidity (e.g., stress events, end-of-day, illiquid instruments) |
| **Endogenous / market impact risk** | Upvest's own orders consume available liquidity, moving the price against itself |

**Instrument eligibility — minimum liquidity floor:**

From `data/assumptions.yaml` — minimum ADV threshold of €1m/day. In practice, for fractional trading at scale, a higher floor is appropriate:

| Instrument tier | 30d ADV | Max order size vs. ADV | Aggregation window |
|----------------|---------|----------------------|-------------------|
| High liquidity (e.g., DAX 40, MSCI World ETF) | > €50m | ≤ 0.5% | 15 min |
| Mid liquidity (e.g., MDAX, S&P 500 mid-cap) | €5m–€50m | ≤ 0.3% | 30 min |
| Low liquidity | < €5m | Excluded from v1 | — |

**Market impact model (simplified square-root law):**
```
Market impact (bps) ≈ σ × √(Q / ADV)
where σ = daily volatility, Q = order size
```

*Example:* σ = 1.5% daily vol, Q = €200,000 order, ADV = €10m
→ Impact ≈ 150bps × √(0.02) ≈ **21bps** — significant; reduce order size or slice over time.

**Option A:** Fixed threshold orders are predictable in size. Market impact can be pre-modelled per instrument at threshold calibration time.

**Option B:** Dynamic algo can adapt order sizing to real-time liquidity. Better market impact management — but requires real-time order book depth feed.

**Liquidity stress:** In a stress event, ADV can drop 60–80% intraday. An instrument that normally has €20m ADV may have only €4m available — recalculate impact accordingly and hold if liquidation cost exceeds inventory P&L benefit.

**Controls and KPIs:**

| KPI | Definition | Alert |
|-----|-----------|-------|
| ADV participation rate | Order size / 30d ADV | > 1% per batch |
| Market impact estimate | Square-root model estimate before execution | > 10bps → reduce order size |
| Actual vs. estimated impact | Post-trade slippage vs. model | Persistent underestimate → recalibrate |
| Illiquid instrument flag | Instrument ADV < floor | Block from eligibility list |
| Liquidity stress indicator | Real-time ADV vs. 30d average | Alert if < 50% of 30d average |

---

### 4. Market Risk — Spread Crosses

**What it is:** The cost Upvest incurs from crossing the bid-ask spread every time it buys or sells whole shares for inventory management. This is the most direct and recurring drag on trading book P&L.

**Mechanics:**

```
Upvest buys inventory:  pays the ASK
Upvest sells inventory:  receives the BID
Round-trip cost per share = ASK - BID = spread

For a €200 stock with a 5bps spread:
  Spread per share = €200 × 0.0005 = €0.10
  Round-trip cost on 10 shares = €1.00
  On €2,000 notional = 5bps cost
```

**Spread varies significantly by:**
- Instrument (blue chip DAX < MDAX < small cap)
- Time of day (first/last 30 min: widest; midday: tightest)
- Market conditions (stress → spreads widen 3–10×)
- Venue (Xetra typically tighter than MTFs for German stocks)

**Option A — always a spread taker:**
- Market orders at threshold → always crosses the spread
- Spread cost is fully absorbed by Upvest
- Total annual spread cost = (number of replenishment trades × average notional) × average spread bps
- This is a direct P&L drag that must be covered by Upvest's fee income from B2B customers

**Option B — potential spread earner (with regulatory caveats):**
- Limit orders can attempt to earn the spread (post at bid, wait for fill)
- Risk: adverse selection — limit order gets filled when the price is moving away from you
- If Upvest earns spread on inventory, this is a benefit to Upvest but **must not come at the cost of worse fractional order pricing for end investors** → conflicts of interest obligation

**Adverse selection — the key risk in spread capture:**

```
Adverse selection occurs when:
  Upvest posts limit buy at bid price
  Price falls → limit order fills
  Price continues to fall → inventory is now underwater

The market "selected" Upvest's order because informed sellers
knew the price was falling. Upvest took the other side.
```

Adverse selection rate should be monitored as a primary algo health KPI for Option B.

**Spread cost as a P&L driver — indicative annual cost:**

| Daily fractional flow | Avg spread (bps) | Round-trips per day | Annual spread cost |
|----------------------|-----------------|--------------------|--------------------|
| €10m | 5 | ~10 | ~€125,000 |
| €50m | 5 | ~50 | ~€625,000 |
| €100m | 5 | ~100 | ~€1,250,000 |
| €100m | 10 (stressed) | ~100 | ~€2,500,000 |

**Controls and KPIs:**

| KPI | Definition | Target |
|-----|-----------|--------|
| Average spread paid (bps) | Weighted average spread cost per executed trade | Benchmark to EBBO (European Best Bid and Offer) |
| Spread vs. time-of-day | Spread paid by time bucket | Avoid first/last 15 min — use for Option A threshold scheduling |
| Adverse selection rate | % of limit order fills followed by price move against Upvest within 30 seconds | < 35% (benchmark: 50% = random; < 35% = good execution) |
| Spread capture P&L | Revenue from limit orders filled at mid vs. market orders | Track separately; must not influence fractional order pricing |
| Spread stress scenario | Spread × 5 on all instruments simultaneously | Model annual spread cost under stress; confirm fee income covers it |

---

### 5. Operational Risk

**What it is:** Risk of loss from failures in people, processes, systems, or external events — distinct from market risk, but highly relevant for a fractional trading business where operational accuracy is fundamental to legal ownership attribution.

#### 5.1 Reconciliation Failure

**Risk:** The internal fractional share ledger drifts from the actual whole-share position held in custody. This is the most critical operational risk — a persistent break means either over-allocation (Upvest owes more shares than it holds) or under-allocation (client entitlements are understated).

| Failure mode | Cause | Consequence |
|-------------|-------|------------|
| Rounding error accumulation | Floating-point arithmetic in fractional calculations | Sub-share break builds over time; undetected until audit |
| Missed corporate action | Dividend, split, or spin-off not processed in ledger | Fractional holders receive incorrect entitlement |
| Settlement break | T+2 settlement fails at CSD; whole share not received | Ledger credits fractional holders for shares not yet held |
| Allocation error | Fractional allocation algorithm bug | Wrong investor credited or debited |
| Dual processing | Order processed twice due to system retry | Over-allocation; potential regulatory breach |

**Controls:**
- **Daily automated reconciliation** — fractional ledger vs. custody position, per instrument, tolerance ±0.001 shares (per `data/assumptions.yaml`)
- **Break escalation:** any break > tolerance → immediate alert → Ops resolution within 24h → Risk notified
- **Intraday snap reconciliations** at key points (market open, pre-batch, market close)
- **Corporate action sweep** — automated daily check for pending CA events; fraction-aware attribution engine
- **Settlement monitor** — flag any T+2 fails at CSD before fractional allocation runs

**KPIs:**

| KPI | Definition | Alert |
|-----|-----------|-------|
| Daily reconciliation breaks | Instruments with ledger vs. custody break > tolerance | Any break |
| Break resolution time | Hours from detection to resolution | > 24h → escalate to Risk Committee |
| Corporate action processing rate | CAs correctly processed / total CAs | < 100% → immediate review |
| Settlement fail rate | Failed settlements / total settlements | > 0.1% → escalate |

---

#### 5.2 Algorithm / System Failure

**Risk:** The inventory management algorithm or aggregation engine fails, resulting in uncontrolled positions, missed fractional fills, or incorrect order generation.

| Failure mode | Cause | Consequence |
|-------------|-------|------------|
| Aggregation engine outage | Software crash, infrastructure failure | Fractional orders queue but are not executed; SLA breach |
| Runaway order loop | Bug in Option B algo; infinite retry | Excessive orders submitted; K-DTF spike; potential market disruption |
| Threshold misconfiguration (Option A) | Manual error in setting min/max thresholds | Wrong inventory level maintained; K-NPR breach or fill failure |
| Model error (Option B) | Bug in signal calculation | Wrong inventory decisions; losses accumulate before detection |
| Kill switch failure | Kill switch itself is defective | Cannot halt runaway algo — regulatory breach under RTS 6 Art. 5 |
| Data feed failure | Market data feed drops; algo operates on stale prices | Incorrect execution decisions; potential losses |
| OMS connectivity loss | Order management system loses venue connectivity | Orders not submitted; inventory gaps; fractional orders unfilled |

**Controls:**
- **Circuit breaker / kill switch** — mandatory for Option B (RTS 6); recommended for Option A
- **Heartbeat monitoring** — aggregation engine emits heartbeat every X seconds; alert if missed
- **Order rate limiter** — hard cap on orders per second per instrument, independent of algo
- **Stale price check** — reject any order if market data feed is > N seconds old
- **Dual environment** — hot standby for aggregation engine; failover < 1 minute
- **Manual override** — Ops can disable algo per instrument or firm-wide; documented procedure
- **Pre-trade simulation** — test any threshold or model change in staging environment before production

**KPIs:**

| KPI | Definition | Alert |
|-----|-----------|-------|
| System availability | Aggregation engine uptime during trading hours | < 99.9% → incident review |
| Order error rate | Orders rejected / errors / total orders submitted | > 0.01% |
| Kill switch test frequency | Scheduled kill switch tests | Monthly minimum |
| Stale data events | Times market data feed was > 5 seconds old during trading | Any event |
| Failover test success | Hot standby activation tests | Quarterly; must complete < 60 seconds |

---

#### 5.3 Settlement and Counterparty Operational Risk

**Risk:** Failure in the post-trade chain — CSD settlement, prime broker processing, or FX settlement — leaves Upvest holding positions or cash obligations it cannot resolve cleanly.

| Failure mode | Cause | Consequence |
|-------------|-------|------------|
| CSD settlement fail | Counterparty delivers late; system error | Whole share not received; fractional entitlements cannot be credited |
| Prime broker default | Execution broker becomes insolvent | Shares held in omnibus at failed broker; recovery process; market exposure continues |
| FX settlement fail | USD/GBP FX leg fails at correspondent bank | US/UK equity positions remain but currency hedge is open; unexpected FX exposure |
| DVP (delivery vs. payment) break | Payment and delivery not synchronised | Cash or securities exposure during settlement window |

**Controls:**
- **DVP settlement** — all trades settled on a delivery-vs-payment basis; no free delivery
- **Prime broker credit limit** — maximum exposure to single execution counterparty (linked to K-CON limit)
- **Multi-venue/prime broker policy** — no single counterparty handles > 50% of settlement flow
- **Settlement fail monitoring** — daily fails report; escalate any fail > T+3 to Risk
- **FX settlement netting** — aggregate FX payments to reduce number of FX settlement events

---

#### 5.4 Data and Pricing Operational Risk

**Risk:** Incorrect reference data or pricing feeds corrupt fractional allocations, resulting in investors receiving incorrect share quantities or valuations.

| Failure mode | Consequence |
|-------------|------------|
| Wrong ISIN / instrument mapping | Fractional order routed to wrong instrument |
| Stale closing price used for allocation | Investors allocated at incorrect price; restatement required |
| Corporate action price adjustment missed | Post-split price used without adjusting inventory; over/under-allocation |
| FX rate error | USD inventory valued at wrong EUR rate; K-NPR miscalculated |

**Controls:**
- **Reference data golden source** — single authoritative ISIN/instrument master; daily validation against venue reference data
- **Price validation** — any closing price > 5% different from intraday VWAP triggers manual review before allocation run
- **Corporate action price adjustment** — automated check: on ex-date, validate that instrument price reflects CA adjustment before allocation

---

#### 5.5 Operational Risk — Option A vs Option B

| Operational risk dimension | Option A | Option B |
|---------------------------|----------|----------|
| **Reconciliation complexity** | Standard — inventory moves are predictable | Higher — more frequent trades; more allocation events |
| **Algorithm failure impact** | Low — simple rule stops; inventory static | High — model error → large position build before detection |
| **Threshold misconfiguration** | Moderate — wrong threshold → wrong inventory level | N/A (no static thresholds) |
| **Model/code complexity** | Low — few hundred lines; easy to audit | High — multiple models; harder to audit |
| **Runaway order risk** | Low — limited by inventory target | High — must have hard order rate limiter and kill switch |
| **Operational risk capital** | Captured in FOR | Captured in FOR — but actual operational losses may exceed FOR if algo malfunctions |
| **Key person risk** | Low — any Ops person can understand and override | Higher — requires quant/developer to diagnose and fix model issues |
| **Regulatory audit trail burden** | Low | High — RTS 6 audit trail per order |

---

### Risk Driver Summary — Comparison

| Risk driver | Option A severity | Option B severity | Primary control |
|-------------|------------------|------------------|-----------------|
| Position risk — inventory | Low (bounded by threshold) | Medium-High (dynamic) | Hard position limits |
| Position risk — residual | Medium (accumulates continuously) | Medium | EOD reconciliation + K-NPR capital |
| Stress loss | Low (max loss = max_threshold × price drop) | High (unbounded without hard limits) | Stop-loss per instrument + ICARA stress |
| Market liquidity — impact | Medium | Low-Medium (algo adapts) | ADV participation cap |
| Market liquidity — stress | High (same for both) | High | Instrument eligibility floor; order slicing |
| Spread cost | High (always taker) | Low-Medium (can earn spread) | Time-of-day scheduling (A); limit orders (B) |
| Adverse selection | N/A | Medium-High | Adverse selection rate KPI; fill strategy tuning |
| Reconciliation failure | Medium | Medium-High | Daily automated recon; intraday snaps |
| Algorithm failure | Low | High | Kill switch; heartbeat; dual environment |
| Settlement failure | Medium (same for both) | Medium | DVP; multi-prime; K-CON limit |
| Data / pricing error | Medium (same for both) | Medium | Reference data golden source; price validation |
| Key person risk | Low | High | Documentation; cross-training |

---

## Side-by-Side Comparison

| Dimension | **Option A — Fixed Threshold** | **Option B — Dynamic Algorithm** |
|-----------|-------------------------------|----------------------------------|
| **Logic** | Rule-based; inventory level only | Market data driven; spread, momentum, flow prediction |
| **Regulatory complexity** | Low — clean Eigenhandel, no algo classification | High — MiFID II algo trading, MAR risk, SI risk, conflict of interest |
| **BaFin notification** | Not required | Required (algorithmic trading per Art. 17 MiFID II) |
| **Model governance** | Not required | Full model risk framework required (MaRisk Novelle AT 4.3.4) |
| **Best execution** | Simple | Complex — must demonstrate client interest prioritised over Upvest P&L |
| **Conflicts of interest** | Minimal | Significant — spread capture must be disclosed and managed |
| **K-NPR predictability** | High — bounded by thresholds | Lower — dynamic positioning creates variable exposure |
| **K-DTF impact** | Moderate | Higher — more frequent trading |
| **Capital efficiency** | Lower — inventory may be suboptimal | Higher — smaller average inventory needed |
| **Execution cost** | Higher — market orders at threshold | Lower — timed to liquidity and spread |
| **Fill rate** | May suffer during volatility | Better maintained through dynamic positioning |
| **Time to implement** | 1–2 months | 6–12 months |
| **Ongoing maintenance** | Low | High — model monitoring, recalibration, compliance review |
| **Explainability** | Very easy | Requires documentation; black-box risk |

---

## Option C — Recommended Hybrid: Fixed Thresholds + Smart Execution

A practical middle ground for launch: use **fixed thresholds to trigger decisions** (low regulatory risk, simple governance), but execute the resulting trades intelligently (TWAP/VWAP slicing, spread-aware timing). This separates the **inventory decision** (simple, regulated as Option A) from **execution quality** (optimised without creating MAR or conflict of interest risk).

```
Step 1 — Inventory decision (Option A logic):
  if inventory < min → decision: buy N shares
  if inventory > max → decision: sell N shares

Step 2 — Execution (smart):
  slice the order over X minutes
  participate up to Y% of ADV per minute
  favour execution when spread < Z bps
  avoid first/last 5 minutes of session (wide spreads)
```

**Regulatory read:** The execution layer is TWAP/VWAP logic, not a market-signal-exploiting algorithm. MiFID II algo trading classification is unlikely if the execution timing is purely liquidity-seeking, not price-signal-seeking. Confirm with Legal/Compliance before deployment.

---

## Decision Framework

| If Upvest prioritises... | Recommendation |
|--------------------------|---------------|
| Fastest time to market, lowest regulatory risk | **Option A** |
| Optimal capital efficiency, best execution quality | **Option B** (with full compliance build) |
| Pragmatic balance — launch fast, upgrade later | **Option C** (hybrid) at launch → migrate to Option B post-stabilisation |

---

## Open Questions

- [ ] What is Upvest's risk appetite for spread capture P&L? (Drives Option B feasibility)
- [ ] Does Legal confirm no SI obligations arise under Option B?
- [ ] What is BaFin's expectation on algorithmic trading notification threshold — does Option C trigger it?
- [ ] What market data feeds are available (L1 only vs. full order book)?
- [ ] What is the execution venue API capability (order types, throttling limits)?
- [ ] Does the target instrument universe require different strategies (EU equities vs. US equities — different market microstructure)?

---

*Last updated: 2026-05-30. Key regulatory sources: MiFID II Art. 17 Art. 4(1)(39); RTS 6 — Commission Delegated Regulation (EU) 2017/589; WpHG §§ 80–81; WpIG § 2 Abs. 2 Nr. 10a–10d. Cross-reference: `docs/02_risk_framework.md` (risk limits), `docs/04_bafin_marisk_compliance.md` (Eigenhandel / algo trading obligations), `docs/05_capital_requirements_kfactors_vs_crr.md` (K-NPR, K-DTF capital implications), `models/kfactors.py` (K-factor model).*
